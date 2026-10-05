"""Explicit, checksum-bound local model registration. No automatic downloads."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from ..errors import PolicyError

MAX_JSON = 2_000_000
PICKLE_SUFFIXES = {".bin", ".pt", ".pth", ".ckpt", ".pkl", ".pickle", ".pyc"}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def local_path(path: Path) -> Path:
    """Reject symlink/junction components before resolving; operator owns the root."""
    path = Path(os.path.abspath(path))
    if any(part.is_symlink() or getattr(part, "is_junction", lambda: False)()
           for part in (path, *path.parents)):
        raise PolicyError("Links simbólicos não são permitidos neste armazenamento.")
    return path


def child(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise PolicyError("Caminho relativo inválido.")
    parts = relative.split("/")
    if any(p in {"", ".", ".."} or ":" in p for p in parts):
        raise PolicyError("Caminho fora do armazenamento autorizado.")
    base = local_path(root)
    candidate = local_path(base.joinpath(*parts))
    if not candidate.is_relative_to(base):
        raise PolicyError("Caminho fora do armazenamento autorizado.")
    return candidate


def identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise PolicyError("Identificador inválido.")
    return value


def read_object(path: Path) -> dict[str, Any]:
    path = local_path(path)
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_JSON + 1)
        if len(raw) > MAX_JSON:
            raise PolicyError("Documento JSON excede o limite.")
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise PolicyError("Documento local ausente ou inválido: " + path.name) from exc
    if not isinstance(value, dict):
        raise PolicyError("O documento JSON deve ser um objeto.")
    return value


def write_new(path: Path, value: dict) -> None:
    """Never overwrite an existing registration or follow a pre-created link."""
    path = local_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
    if len(raw) > MAX_JSON:
        raise PolicyError("Documento JSON excede o limite.")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)


def inventory(directory: Path) -> list[Path]:
    directory = local_path(directory)
    if not directory.is_dir():
        raise PolicyError("Informe uma pasta local existente de modelo, não um ID do Hub.")
    paths = []
    def fail_walk(error):
        raise PolicyError("Não foi possível inventariar todos os arquivos do modelo.") from error
    for current, folders, files in os.walk(directory, followlinks=False, onerror=fail_walk):
        for name in folders + files:
            entry = local_path(Path(current) / name)
            if name == ".git" or entry.suffix.lower() in PICKLE_SUFFIXES:
                raise PolicyError("Modelo contém Git ou formato executável/pickle não autorizado.")
            if entry.is_file():
                paths.append(entry)
            elif not entry.is_dir():
                raise PolicyError("Arquivo especial não permitido no modelo.")
        if len(paths) > 10000:
            raise PolicyError("Inventário excessivo.")
    if not paths:
        raise PolicyError("Inventário vazio.")
    return sorted(paths)


@dataclass(frozen=True)
class ModelSpec:
    directory: Path
    model_id: str
    revision: str
    license: str
    capability: str
    files: dict[str, str]
    manifest_sha256: str
    reviewed_local_code: bool = False
    context_tokens: int = 4096
    output_tokens: int = 768
    device: str = "cpu"
    dtype: str = "float32"
    derivation: dict = field(default_factory=dict)

    @classmethod
    def load(cls, manifest: Path, capability: str) -> "ModelSpec":
        data = read_object(manifest)
        required = ("model_id", "revision", "license", "reviewed_by", "directory")
        if capability not in {"text", "image"} or data.get("schema") != 1 or data.get("capability") != capability:
            raise PolicyError("Manifesto ausente ou capacidade incompatível.")
        if any(not isinstance(data.get(k), str) or not data[k].strip() for k in required):
            raise PolicyError("Registre origem, revisão, licença, revisor e diretório do modelo.")
        if not Path(data["directory"]).is_absolute():
            raise PolicyError("O diretório de modelo precisa ser absoluto e local.")
        files = data.get("files")
        if not isinstance(files, dict) or not files or len(files) > 10000:
            raise PolicyError("O manifesto precisa do inventário completo de hashes.")
        for name, value in files.items():
            child(Path(data["directory"]), name)
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
                raise PolicyError("Hash de modelo inválido.")
        context, output = data.get("context_tokens", 4096), data.get("output_tokens", 768)
        if (type(context) is not int or type(output) is not int
                or not 256 <= context <= 1048576 or not 1 <= output < context):
            raise PolicyError("Orçamento de tokens inválido.")
        device, dtype = data.get("device", "cpu"), data.get("dtype", "float32")
        if device not in {"cpu", "cuda", "auto"} or dtype not in {"float32", "float16", "bfloat16"}:
            raise PolicyError("Dispositivo ou precisão não suportados.")
        if type(data.get("reviewed_local_code", False)) is not bool:
            raise PolicyError("A revisão de código local deve ser um booleano explícito.")
        derived = data.get("derivation", {})
        if not isinstance(derived, dict) or (derived and (
                derived.get("created_from_scratch") is not False or not derived.get("base_model")
                or any(not re.fullmatch(r"[a-f0-9]{64}", str(derived.get(k, ""))) for k in
                       ("base_manifest_sha256", "dataset_sha256", "experiment_sha256", "checkpoint_sha256")))):
            raise PolicyError("Procedência de modelo derivado incompleta.")
        return cls(local_path(Path(data["directory"])), data["model_id"], data["revision"],
                   data["license"], capability, files, digest(manifest),
                   data.get("reviewed_local_code", False), context, output, device, dtype, data.get("derivation", {}))

    def verify(self) -> tuple:
        paths = inventory(self.directory)
        actual = {p.relative_to(self.directory).as_posix(): p for p in paths}
        if set(actual) != set(self.files):
            raise PolicyError("Inventário do modelo mudou; revise e registre novamente.")
        if self.derivation and read_object(self.directory / "DERIVATION.json") != self.derivation:
            raise PolicyError("Procedência diverge da derivação conservada com os pesos.")
        if any(p.suffix.lower() == ".py" for p in paths) and (not self.reviewed_local_code or self.capability != "text"):
            raise PolicyError("Código Python do checkpoint exige revisão local explícita; imagens não aceitam código customizado.")
        for name, path in actual.items():
            if path.name == "adapter_config.json":
                raise PolicyError("Adaptador isolado não é um checkpoint completo. Exporte/funda a base revisada antes de registrar.")
            if path.name.endswith("config.json"):
                config = read_object(path)
                if "--" in json.dumps(config.get("auto_map", {})):
                    raise PolicyError("auto_map externo não é permitido; use código local revisado.")
            if path.name.endswith(".safetensors.index.json"):
                weights = read_object(path).get("weight_map", {})
                if not isinstance(weights, dict):
                    raise PolicyError("Índice de pesos inválido.")
                for target in weights.values():
                    shard = child(path.parent, target)
                    relative = shard.relative_to(self.directory).as_posix()
                    if relative not in self.files or shard.suffix != ".safetensors":
                        raise PolicyError("Shard de pesos fora do inventário revisado.")
            if digest(path) != self.files[name]:
                raise PolicyError("Hash do modelo divergente: " + name)
        if not any(p.suffix == ".safetensors" for p in paths):
            raise PolicyError("Este runtime requer pesos Safetensors locais.")
        return self.signature()

    def signature(self) -> tuple:
        """Full hashes at load; reject disk changes between generations."""
        return tuple((p.relative_to(self.directory).as_posix(), p.stat().st_size,
                      p.stat().st_mtime_ns, p.stat().st_ctime_ns) for p in inventory(self.directory))

    def provenance(self) -> dict:
        return {"model_id": self.model_id, "revision": self.revision, "license": self.license,
                "manifest_sha256": self.manifest_sha256, "capability": self.capability,
                "weights_modified_by_this_run": False, "derived_checkpoint": bool(self.derivation), "derivation": self.derivation,
                "created_from_scratch": False if self.derivation else None}


def register_model(directory: Path, target: Path, *, model_id: str, revision: str,
                   license: str, reviewed_by: str, capability: str,
                   reviewed_local_code: bool = False, device: str = "cpu",
                   dtype: str = "float32", context_tokens: int = 4096,
                   output_tokens: int = 768, derivation: dict | None = None) -> None:
    """Operator attests origin/rights; hashes do not establish model competence."""
    directory, target = local_path(directory), local_path(target)
    if target.is_relative_to(directory):
        raise PolicyError("Guarde o manifesto fora da pasta imutável de pesos.")
    if capability not in {"text", "image"}:
        raise PolicyError("Capacidade deve ser text ou image.")
    paths = inventory(directory)
    data = {"schema": 1, "directory": str(directory), "model_id": model_id,
            "revision": revision, "license": license, "reviewed_by": reviewed_by,
            "capability": capability, "reviewed_local_code": reviewed_local_code,
            "device": device, "dtype": dtype, "context_tokens": context_tokens,
            "output_tokens": output_tokens,
            "derivation": derivation or {},
            "files": {p.relative_to(directory).as_posix(): digest(p) for p in paths}}
    import tempfile
    with tempfile.TemporaryDirectory() as temp:
        candidate = Path(temp) / "manifest.json"
        write_new(candidate, data)
        ModelSpec.load(candidate, capability).verify()
    write_new(target, data)
