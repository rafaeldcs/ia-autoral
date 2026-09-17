from __future__ import annotations
import json
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from .config import Settings
from .errors import PolicyError
from .store import Store
from .util import sha256, canonical_json, atomic_write, read_json, write_json


def backup_home(settings: Settings, output: Path):
    if (settings.home/"server.lock").exists():
        raise PolicyError("Encerre o servidor antes do backup consistente de banco e arquivos.")
    if output.absolute().is_relative_to(settings.home):
        raise PolicyError("Salve o backup fora da pasta de dados, preferencialmente em outro dispositivo.")
    files = {}
    with tempfile.TemporaryDirectory() as tmp:
        snapshot = Path(tmp)/"memory.sqlite3"
        Store(settings.home/"memory.sqlite3").backup(snapshot)
        for path in [snapshot, *(p for p in settings.home.rglob("*") if p.is_file())]:
            if path == snapshot:
                rel = "memory.sqlite3"
            else:
                if path.is_symlink(): raise PolicyError("Link simbólico encontrado no backup.")
                rel = path.relative_to(settings.home).as_posix()
                if rel.startswith("exports/") or rel in {"api.token", "server.lock"} or rel.startswith("memory.sqlite3"):
                    continue
            files[rel] = path.read_bytes()
            if sum(map(len, files.values())) > 512_000_000:
                raise PolicyError("Backup de referência limitado a 512 MB; exportação streaming maior é pendência.")
        manifest = {name: sha256(raw) for name, raw in files.items()}
        temp_zip = Path(tmp)/"backup.zip"
        with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, raw in files.items(): archive.writestr(name, raw)
            archive.writestr("BACKUP_MANIFEST.json", canonical_json(manifest))
        atomic_write(output, temp_zip.read_bytes())
    return {"files": len(files), "path": str(output), "token_included": False}


def restore_home(archive_path: Path, destination: Path):
    destination = destination.expanduser().absolute()
    for part in [destination, *destination.parents]:
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise PolicyError("Destino de restauração não pode usar links ou junctions.")
    if destination.exists() and any(destination.iterdir()):
        raise PolicyError("Restauração exige diretório vazio; não sobrescreve uma instalação existente.")
    if archive_path.stat().st_size > 520_000_000:
        raise PolicyError("Backup grande demais.")
    with zipfile.ZipFile(archive_path) as archive:
        entries = archive.infolist()
        names = [e.filename for e in entries]
        if len(set(names)) != len(names) or len(names) > 20_000 or sum(e.file_size for e in entries) > 512_000_000:
            raise PolicyError("Backup duplicado ou excedendo limites.")
        for entry in entries:
            p = PurePosixPath(entry.filename)
            if entry.filename != p.as_posix() or entry.filename in {"", "."} or p.is_absolute() or ".." in p.parts or "\\" in entry.filename or ":" in entry.filename or entry.filename.startswith("/") or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise PolicyError("Caminho inseguro no backup.")
            if entry.filename in {"api.token", "server.lock"}:
                raise PolicyError("Backup não deve importar credenciais ou locks.")
        if "BACKUP_MANIFEST.json" not in names: raise PolicyError("Manifesto do backup ausente.")
        manifest = json.loads(archive.read("BACKUP_MANIFEST.json"))
        if set(manifest) != set(names) - {"BACKUP_MANIFEST.json"}:
            raise PolicyError("Manifesto do backup divergente.")
        contents = {name: archive.read(name) for name in manifest}
        if any(sha256(contents[name]) != digest for name, digest in manifest.items()):
            raise PolicyError("Backup corrompido.")
    destination.mkdir(parents=True, exist_ok=True)
    for name, content in contents.items(): atomic_write(destination/name, content)
    config_path = destination/"settings.json"
    if config_path.exists():
        config = read_json(config_path)
        config["offline"] = True
        config["docker_image"] = ""
        write_json(config_path, config)
    settings = Settings.load(destination)
    # Paths to registered projects retain their original location: review before use on another machine.
    return {"restored": True, "files": len(contents), "offline": True, "token_regenerated": True, "review_project_roots": True}
