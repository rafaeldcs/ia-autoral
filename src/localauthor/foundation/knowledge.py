"""Versioned consultation sources; imports never confer training rights."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import uuid

from ..errors import PolicyError
from ..safety import reject_secrets
from .models import child, identifier, local_path, read_object, write_new


def _manifest(home: Path, project_id: str):
    identifier(project_id)
    if (home / "server.lock").exists():
        raise PolicyError("Encerre o servidor antes de alterar conhecimento pelo CLI.")
    root = local_path(home / "foundation" / "knowledge" / project_id)
    root.mkdir(parents=True, exist_ok=True)
    path = local_path(root / "sources.json")
    data = read_object(path) if path.exists() else {"schema": 1, "sources": []}
    if data.get("schema") != 1 or not isinstance(data.get("sources"), list) or len(data["sources"]) > 200:
        raise PolicyError("Manifesto de conhecimento inválido.")
    return root, path, data


def _commit(path: Path, data: dict):
    temporary = path.parent / (uuid.uuid4().hex + ".json")
    try:
        write_new(temporary, data)
        os.replace(temporary, local_path(path))
    finally:
        temporary.unlink(missing_ok=True)


def import_markdown(home: Path, project_id: str, file: Path, title: str,
                    source_id: str | None = None) -> dict:
    file = local_path(file)
    if file.suffix.lower() != ".md" or not isinstance(title, str) or not title.strip() or len(title) > 500:
        raise PolicyError("Selecione Markdown e título válido.")
    source_id = identifier(source_id or hashlib.sha256(str(file).encode("utf-8")).hexdigest())
    with file.open("rb") as stream:
        raw = stream.read(200001)
    if not raw or len(raw) > 200000:
        raise PolicyError("Markdown vazio ou excede 200 KB.")
    text = raw.decode("utf-8")
    reject_secrets(text)
    sha = hashlib.sha256(raw).hexdigest()
    root, manifest, data = _manifest(home, project_id)
    previous = [entry for entry in data["sources"] if entry.get("identity") == source_id]
    for entry in previous:
        if entry.get("active", True) and entry.get("sha256") == sha:
            stored = child(root, entry["path"])
            if hashlib.sha256(stored.read_bytes()).hexdigest() != sha:
                raise PolicyError("Fonte registrada foi alterada.")
            if entry.get("title") != title:
                entry["title"] = title
                _commit(manifest, data)
            return {**entry, "reused": True}
    if len(data["sources"]) >= 200:
        raise PolicyError("Limite de versões de conhecimento atingido; arquive com revisão.")
    name = uuid.uuid4().hex + ".md"
    destination = child(root, name)
    entry = {"path": name, "scope": project_id, "title": title, "sha256": sha,
             "identity": source_id, "version": max((e.get("version", 1) for e in previous), default=0) + 1,
             "active": True, "training_allowed": False}
    # Invalidate dependent experiences first: partial failure denies reuse rather
    # than accidentally allowing an experience backed by an obsolete source.
    from .experience import ExperienceStore
    for old in previous:
        if old.get("active", True):
            ExperienceStore(home).invalidate_source(project_id, old["path"], old["sha256"])
            old["active"] = False
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
        data["sources"].append(entry)
        _commit(manifest, data)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return {**entry, "reused": False}


def revoke_source(home: Path, project_id: str, source_id: str) -> dict:
    source_id = identifier(source_id)
    _, path, data = _manifest(home, project_id)
    entries = [entry for entry in data["sources"] if entry.get("identity") == source_id]
    if not entries:
        raise PolicyError("Fonte não encontrada neste projeto.")
    from .experience import ExperienceStore
    affected = 0
    for entry in entries:
        if entry.get("active", True):
            affected += ExperienceStore(home).invalidate_source(project_id, entry["path"], entry["sha256"])
            entry["active"] = False
    _commit(path, data)
    return {"identity": source_id, "revoked": True, "experiences_invalidated": affected,
            "previous_checkpoints_unlearned": False}
