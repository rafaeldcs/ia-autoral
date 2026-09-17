from __future__ import annotations
import json
import re
from pathlib import Path
from .errors import PolicyError
from .safety import PathPolicy
from .util import read_json, canonical_json, sha256


def validate_dataset(manifest_path: Path) -> dict:
    if manifest_path.stat().st_size > 4_000_000:
        raise PolicyError("Manifesto grande demais.")
    data = read_json(manifest_path)
    if data.get("schema_version") != 1 or not isinstance(data.get("records"), list) or not 2 <= len(data["records"]) <= 2000:
        raise PolicyError("Manifesto requer schema_version=1 e de 2 a 2000 registros.")
    policy = PathPolicy(manifest_path.parent, max_file_bytes=1_000_000)
    groups, hashes, used_paths, splits = {}, {}, set(), {"train": [], "validation": [], "test": []}
    fingerprints = []
    total_bytes = 0
    for record in data["records"]:
        required = {"path", "split", "group", "sha256", "training_allowed", "provenance"}
        if not isinstance(record, dict) or set(record) != required:
            raise PolicyError("Campos de registro inválidos.")
        split = record["split"]
        if split not in splits or not isinstance(record["group"], str) or not record["group"]:
            raise PolicyError("Partição ou grupo inválido.")
        if record["path"] in used_paths:
            raise PolicyError("Arquivo repetido no manifesto.")
        used_paths.add(record["path"])
        if split in {"train", "validation"} and record["training_allowed"] is not True:
            raise PolicyError("Treinamento/validação requer permissão explícita de uso.")
        provenance = record["provenance"]
        if not isinstance(provenance, dict) or not all(isinstance(provenance.get(k), str) and provenance[k].strip() for k in ("kind", "owner", "license_or_permission")):
            raise PolicyError("Proveniência incompleta; nenhuma licença é presumida.")
        if provenance["kind"] not in {"human-authored", "licensed", "synthetic-authorized"}:
            raise PolicyError("Origem de dados não aprovada.")
        raw = policy.read(record["path"])
        total_bytes += len(raw)
        if total_bytes > 8_000_000:
            raise PolicyError("Corpus de referência limitado a 8 MB incluindo holdout.")
        digest = sha256(raw)
        if digest != record["sha256"]:
            raise PolicyError("Hash de corpus divergente.")
        if record["group"] in groups and groups[record["group"]] != split:
            raise PolicyError("Um grupo não pode atravessar partições.")
        groups[record["group"]] = split
        if digest in hashes and hashes[digest] != split:
            raise PolicyError("Duplicação exata entre partições.")
        hashes[digest] = split
        text = raw.decode("utf-8")
        tokens = re.findall(r"\w+|[^\w\s]", text.lower())
        shingles = {tuple(tokens[i:i+5]) for i in range(max(0, len(tokens)-4))}
        if len(shingles) >= 20:
            for other_split, other in fingerprints:
                if split != other_split and len(shingles & other)/max(1, len(shingles | other)) >= 0.90:
                    raise PolicyError("Possível duplicação próxima entre partições; revise os grupos.")
            fingerprints.append((split, shingles))
        # Validate test integrity but never return its content to a training caller.
        if split != "test":
            splits[split].append({"path": record["path"], "text": text, "sha256": digest})
        else:
            splits[split].append({"path": record["path"], "sha256": digest})
    if not splits["train"] or not splits["validation"]:
        raise PolicyError("É necessário separar treino e validação.")
    if sum(len(r["text"].encode("utf-8")) for s in ("train", "validation") for r in splits[s]) > 8_000_000:
        raise PolicyError("Loader CPU de referência limitado a 8 MB; streaming de corpus grande é pendência.")
    return {"manifest_hash": sha256(canonical_json(data)), "dataset_id": data.get("dataset_id", manifest_path.parent.name), "splits": splits}
