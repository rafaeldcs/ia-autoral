from __future__ import annotations
import base64
import difflib
import json
import os
import threading
import uuid
from pathlib import Path
from .config import Settings
from .errors import PolicyError, NotFoundError, ConflictError
from .safety import PathPolicy, reject_secrets
from .store import Store
from .util import utcnow, sha256, write_json, read_json, canonical_json, atomic_write


class TaskService:
    """Fluxo de revisão humana. Não finge que propostas manuais vieram de um modelo."""
    def __init__(self, store: Store, settings: Settings):
        self.store, self.settings = store, settings
        self.lock = threading.RLock()
        with store.connect() as db:
            db.execute("UPDATE tasks SET state='recovery_required' WHERE state='applying'")

    def get(self, task_id: str) -> dict:
        with self.store.connect() as db:
            row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise NotFoundError("Tarefa não encontrada.")
        result = dict(row)
        if result["test_result"]:
            result["test_result"] = json.loads(result["test_result"])
        return result

    def list(self) -> list[dict]:
        with self.store.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 100")]

    def base(self, task_id: str) -> Path:
        self.get(task_id)  # No caller-controlled path without a database lookup.
        return self.settings.home / "workspaces" / task_id

    def create(self, project_id: str, instruction: str) -> dict:
        if not isinstance(instruction, str) or not instruction.strip() or len(instruction) > 4000:
            raise PolicyError("Instrução inválida ou maior que 4000 caracteres.")
        reject_secrets(instruction)
        project = self.store.project(project_id)
        policy = PathPolicy(Path(project["root"]), self.settings.max_file_bytes)
        task_id, now = uuid.uuid4().hex, utcnow()
        folder = self.settings.home / "workspaces" / task_id
        tree = folder / "tree"
        tree.mkdir(parents=True)
        manifest = {}
        skipped = []
        total = 0
        try:
            for relative in policy.files(self.settings.max_project_files):
                try:
                    data = policy.read(relative)
                except (PolicyError, UnicodeError, OSError) as exc:
                    skipped.append({"path": relative, "reason": str(exc)})
                    continue
                total += len(data)
                if total > self.settings.max_snapshot_bytes:
                    raise PolicyError("Snapshot excede quota de bytes.")
                dest = tree / relative
                atomic_write(dest, data, 0o644)
                manifest[relative] = sha256(data)
            write_json(folder / "snapshot.json", {"files": manifest, "created_at": now, "skipped": skipped})
            with self.store.connect() as db:
                db.execute("INSERT INTO tasks(id,project_id,instruction,state,created_at,updated_at) VALUES(?,?,?,?,?,?)", (task_id, project_id, instruction, "awaiting_proposal", now, now))
        except Exception:
            import shutil
            shutil.rmtree(folder, ignore_errors=True)
            raise
        self.store.audit("task.created", {"task_id": task_id, "files": len(manifest), "skipped": len(skipped)})
        return {**self.get(task_id), "snapshot_files": len(manifest), "skipped": skipped, "model_status": "not_qualified", "notice": "Proposta manual/importada; agente generativo autônomo não liberado."}

    def propose(self, task_id: str, changes: list[dict], *, allow_test_changes: bool = False) -> dict:
        with self.lock:
            task = self.get(task_id)
            if task["state"] not in {"awaiting_proposal", "awaiting_review"}:
                raise ConflictError("Esta tarefa não aceita novas propostas nesse estado.")
            if not isinstance(changes, list) or not 1 <= len(changes) <= 8:
                raise PolicyError("A proposta deve conter de 1 a 8 arquivos.")
            folder = self.base(task_id)
            snapshot = read_json(folder / "snapshot.json")["files"]
            project = self.store.project(task["project_id"])
            source = PathPolicy(Path(project["root"]), self.settings.max_file_bytes)
            workspace = PathPolicy(folder / "tree", self.settings.max_file_bytes)
            normalized, diffs, seen = [], [], set()
            # A revision replaces the old proposal; unchanged staged files are restored first below.
            previous = read_json(folder / "proposal.json") if (folder / "proposal.json").exists() else None
            for item in changes:
                if not isinstance(item, dict) or set(item) != {"path", "before_sha256", "content"}:
                    raise PolicyError("Cada alteração requer path, before_sha256 e content, sem outros campos.")
                path, before, content = item["path"], item["before_sha256"], item["content"]
                if not isinstance(path, str) or not isinstance(content, str) or path in seen:
                    raise PolicyError("Caminho duplicado ou conteúdo inválido.")
                seen.add(path)
                workspace.resolve(path, write=True, allow_tests=allow_test_changes)
                source.resolve(path, write=True, allow_tests=allow_test_changes)
                expected = snapshot.get(path)
                if before != expected:
                    raise ConflictError(f"Hash anterior não corresponde ao snapshot: {path}")
                data = content.encode("utf-8")
                if len(data) > self.settings.max_file_bytes or b"\x00" in data:
                    raise PolicyError("Conteúdo binário ou grande demais.")
                reject_secrets(content)
                if expected is None:
                    if source.resolve(path).exists():
                        raise ConflictError(f"O arquivo já existe e não estava no snapshot: {path}")
                    original = b""
                else:
                    # Keep an immutable copy when a proposal is first staged.
                    saved = folder / "originals" / path
                    if saved.exists():
                        original = saved.read_bytes()
                    else:
                        original = workspace.read(path)
                    if sha256(original) != expected:
                        raise ConflictError(f"Snapshot alterado: {path}")
                normalized.append({"path": path, "before_sha256": before, "after_sha256": sha256(data), "content": content})
                diffs.append("".join(difflib.unified_diff(original.decode("utf-8").splitlines(keepends=True), content.splitlines(keepends=True), fromfile="a/" + path, tofile="b/" + path)))
            # Validate everything before changing the copy. Originals are never changed here.
            if previous:
                for item in previous["changes"]:
                    path = item["path"]
                    if path not in seen:
                        dest = workspace.resolve(path, write=True, allow_tests=previous["allow_test_changes"])
                        old = folder / "originals" / path
                        if item["before_sha256"] is None:
                            if dest.exists(): dest.unlink()
                        else:
                            atomic_write(dest, old.read_bytes(), 0o644)
            for item in normalized:
                path = item["path"]
                backup = folder / "originals" / path
                dest = workspace.resolve(path, write=True, allow_tests=allow_test_changes)
                if item["before_sha256"] is not None and not backup.exists():
                    atomic_write(backup, workspace.read(path))
                atomic_write(dest, item["content"].encode("utf-8"), 0o644)
            proposal = {"task_id": task_id, "origin": "human_import", "allow_test_changes": allow_test_changes, "changes": normalized}
            digest = sha256(canonical_json(proposal))
            write_json(folder / "proposal.json", proposal)
            with self.store.connect() as db:
                db.execute("UPDATE tasks SET state='awaiting_review',proposal_hash=?,test_result=NULL,updated_at=? WHERE id=?", (digest, utcnow(), task_id))
            self.store.audit("proposal.staged", {"task_id": task_id, "proposal_hash": digest, "files": len(normalized)})
            return {"task_id": task_id, "proposal_hash": digest, "diff": "\n".join(diffs), "changes": normalized, "original_untouched": True}

    def preview(self, task_id: str) -> dict:
        task = self.get(task_id)
        file = self.base(task_id) / "proposal.json"
        if not file.exists():
            return {"task": task, "proposal": None}
        proposal = read_json(file)
        diffs = []
        for change in proposal["changes"]:
            path = change["path"]
            old = self.base(task_id) / "originals" / path
            old_text = old.read_bytes().decode("utf-8") if old.exists() else ""
            diffs.append("".join(difflib.unified_diff(old_text.splitlines(keepends=True), change["content"].splitlines(keepends=True), fromfile="a/" + path, tofile="b/" + path)))
        return {"task": task, "proposal": proposal, "diff": "\n".join(diffs)}

    def apply(self, task_id: str, proposal_hash: str, *, accept_without_tests: bool = False) -> dict:
        with self.lock:
            task = self.get(task_id)
            if task["state"] != "awaiting_review":
                raise ConflictError("Tarefa não está aguardando revisão.")
            folder = self.base(task_id)
            proposal = read_json(folder / "proposal.json")
            digest = sha256(canonical_json(proposal))
            if digest != proposal_hash or digest != task["proposal_hash"]:
                raise ConflictError("A proposta mudou; revise-a novamente.")
            tested = task["test_result"] and task["test_result"].get("exit_code") == 0 and task["test_result"].get("kind") in {"dotnet-test", "python-tests"} and task["test_result"].get("proposal_hash") == digest
            if not tested and not accept_without_tests:
                raise PolicyError("Não há verificação aprovada dessa proposta. Teste-a ou aprove explicitamente sem testes.")
            project = self.store.project(task["project_id"])
            original = PathPolicy(Path(project["root"]), self.settings.max_file_bytes)
            staged = PathPolicy(folder / "tree", self.settings.max_file_bytes)
            entries = []
            for item in proposal["changes"]:
                path = item["path"]
                dest = original.resolve(path, write=True, allow_tests=proposal["allow_test_changes"])
                existing = original.read(path) if dest.exists() else None
                if (sha256(existing) if existing is not None else None) != item["before_sha256"]:
                    raise ConflictError(f"O original mudou desde o snapshot: {path}")
                after = staged.read(path)
                if sha256(after) != item["after_sha256"]:
                    raise ConflictError(f"A cópia foi alterada depois da proposta: {path}")
                entries.append({"path": path, "before": base64.b64encode(existing).decode("ascii") if existing is not None else None, "before_sha256": item["before_sha256"], "after_sha256": item["after_sha256"], "mode": (dest.stat().st_mode & 0o777) if dest.exists() else 0o644})
            journal_file = self.settings.home / "journals" / (task_id + ".json")
            journal = {"task_id": task_id, "state": "prepared", "allow_test_changes": proposal["allow_test_changes"], "entries": entries}
            write_json(journal_file, journal)
            with self.store.connect() as db:
                db.execute("UPDATE tasks SET state='applying',updated_at=? WHERE id=?", (utcnow(), task_id))
            try:
                for item, entry in zip(proposal["changes"], entries):
                    dest = original.resolve(item["path"], write=True, allow_tests=proposal["allow_test_changes"])
                    # Recheck just before replacing each file; hostile concurrent local processes remain outside this threat model.
                    current = original.read(item["path"]) if dest.exists() else None
                    if (sha256(current) if current is not None else None) != item["before_sha256"]:
                        raise ConflictError("Arquivo alterado durante a aprovação; operação interrompida.")
                    atomic_write(dest, item["content"].encode("utf-8"), entry["mode"])
                journal["state"] = "completed"
                write_json(journal_file, journal)
                with self.store.connect() as db:
                    db.execute("UPDATE tasks SET state='applied',updated_at=? WHERE id=?", (utcnow(), task_id))
            except Exception:
                with self.store.connect() as db:
                    db.execute("UPDATE tasks SET state='recovery_required',updated_at=? WHERE id=?", (utcnow(), task_id))
                self.recover(task_id)
                raise
            self.feedback(task_id, "approved", "Aplicação humana; verificação aprovada." if tested else "Aprovação humana explícita sem testes.")
            self.store.audit("proposal.applied", {"task_id": task_id, "tested": bool(tested)})
            return self.get(task_id)

    def recover(self, task_id: str) -> dict:
        with self.lock:
            task = self.get(task_id)
            if task["state"] not in {"applying", "recovery_required"}:
                raise ConflictError("Não há aplicação interrompida a recuperar.")
            file = self.settings.home / "journals" / (task_id + ".json")
            journal = read_json(file)
            policy = PathPolicy(Path(self.store.project(task["project_id"])["root"]), self.settings.max_file_bytes)
            if journal["state"] == "completed":
                with self.store.connect() as db:
                    db.execute("UPDATE tasks SET state='applied',updated_at=? WHERE id=?", (utcnow(), task_id))
                return self.get(task_id)
            # Validate all destinations first. Never overwrite an intervening human change.
            for entry in journal["entries"]:
                dest = policy.resolve(entry["path"], write=True, allow_tests=journal["allow_test_changes"])
                current = policy.read(entry["path"]) if dest.exists() else None
                digest = sha256(current) if current is not None else None
                if digest not in {entry["before_sha256"], entry["after_sha256"]}:
                    raise ConflictError("Recuperação bloqueada por alteração externa; consulte o diário sem sobrescrever os arquivos.")
            for entry in journal["entries"]:
                dest = policy.resolve(entry["path"], write=True, allow_tests=journal["allow_test_changes"])
                if entry["before"] is None:
                    if dest.exists(): dest.unlink()
                else:
                    atomic_write(dest, base64.b64decode(entry["before"]), entry["mode"])
            journal["state"] = "rolled_back"
            write_json(file, journal)
            with self.store.connect() as db:
                db.execute("UPDATE tasks SET state='rolled_back',updated_at=? WHERE id=?", (utcnow(), task_id))
            self.store.audit("task.recovered", {"task_id": task_id})
            return self.get(task_id)

    def reject(self, task_id: str) -> dict:
        with self.lock:
            task = self.get(task_id)
            if task["state"] not in {"awaiting_proposal", "awaiting_review"}:
                raise ConflictError("Tarefa não pode ser rejeitada neste estado.")
            with self.store.connect() as db:
                db.execute("UPDATE tasks SET state='rejected',updated_at=? WHERE id=?", (utcnow(), task_id))
            self.feedback(task_id, "rejected", "Rejeitada na revisão humana; original não alterado.")
            return self.get(task_id)

    def feedback(self, task_id: str, status: str, note: str):
        self.get(task_id)
        if status not in {"attempted", "approved", "rejected", "regression", "obsolete"} or not isinstance(note, str) or len(note) > 2000:
            raise PolicyError("Feedback inválido.")
        reject_secrets(note)
        with self.store.connect() as db:
            db.execute("INSERT INTO experiences VALUES(?,?,?,?,?)", (uuid.uuid4().hex, task_id, status, note, utcnow()))
        return {"stored": True, "weights_updated": False, "training_candidate_approved": False}
