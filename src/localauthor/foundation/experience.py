"""Private candidate experiences and explicit human dataset curation. Never trains."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import uuid

from ..errors import PolicyError
from .models import identifier, local_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS experiences (
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL, kind TEXT NOT NULL,
 prompt TEXT NOT NULL, response TEXT NOT NULL, metadata TEXT NOT NULL,
 problem_hash TEXT NOT NULL, output_hash TEXT NOT NULL, created_at TEXT NOT NULL,
 accepted INTEGER NOT NULL DEFAULT 0, training_allowed INTEGER NOT NULL DEFAULT 0,
 rights_reviewed INTEGER NOT NULL DEFAULT 0, verified INTEGER NOT NULL DEFAULT 0,
 reviewer TEXT NOT NULL DEFAULT '', verification_note TEXT NOT NULL DEFAULT '',
 split TEXT NOT NULL DEFAULT 'train'
);
CREATE TABLE IF NOT EXISTS reviews (
 id INTEGER PRIMARY KEY, experience_id TEXT NOT NULL, created_at TEXT NOT NULL,
 decision TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExperienceStore:
    def __init__(self, home: Path):
        self.root = local_path(home / "foundation")
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = local_path(self.root / "experiences.sqlite3")
        if not self.path.exists():
            try:
                fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                local_path(self.path)
            else:
                os.close(fd)
        with self.connect() as db:
            db.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        local_path(self.path)
        for suffix in ("-journal", "-wal", "-shm"):
            local_path(Path(str(self.path) + suffix))
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def record(self, project_id: str, kind: str, prompt: str, response: str,
               metadata: dict, *, run_id: str | None = None) -> str:
        project_id = identifier(project_id)
        run_id = identifier(run_id or uuid.uuid4().hex)
        if kind not in {"text", "code", "image"}:
            raise PolicyError("Tipo de experiência inválido.")
        if not isinstance(prompt, str) or not isinstance(response, str):
            raise PolicyError("Experiência inválida.")
        serialized = json.dumps(metadata, ensure_ascii=False)
        if len((prompt + response + serialized).encode("utf-8")) > 250000:
            raise PolicyError("Experiência excede o limite de armazenamento.")
        problem = hashlib.sha256(" ".join(prompt.casefold().split()).encode("utf-8")).hexdigest()
        output_hash = hashlib.sha256((response + serialized).encode("utf-8")).hexdigest()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if self.path.stat().st_size > 32000000:
                raise PolicyError("Memória de experiências cheia; revise e arquive antes de continuar.")
            db.execute("INSERT INTO experiences(id,project_id,kind,prompt,response,metadata,problem_hash,output_hash,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                       (run_id, project_id, kind, prompt, response, serialized, problem, output_hash, now()))
        return run_id

    def get(self, project_id: str, run_id: str) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT * FROM experiences WHERE project_id=? AND id=?",
                             (identifier(project_id), identifier(run_id))).fetchone()
        if row is None:
            raise PolicyError("Experiência não encontrada neste projeto.")
        result = dict(row)
        result["metadata"] = json.loads(result["metadata"])
        return result

    def review(self, project_id: str, run_id: str, *, expected_hash: str,
               accepted: bool, training_allowed: bool, rights_reviewed: bool,
               verified: bool, reviewer: str, verification_note: str,
               split: str = "train") -> None:
        flags = (accepted, training_allowed, rights_reviewed, verified)
        if any(type(flag) is not bool for flag in flags):
            raise PolicyError("As decisões exigem booleanos explícitos.")
        if not isinstance(reviewer, str) or not reviewer.strip() or split not in {"train", "validation", "test"}:
            raise PolicyError("Revisor e partição obrigatórios.")
        if not isinstance(verification_note, str) or (verified and not verification_note.strip()):
            raise PolicyError("Descreva a verificação humana/externa; autoavaliação do modelo não basta.")
        if training_allowed and not all((accepted, rights_reviewed, verified)):
            raise PolicyError("Treino exige aceitação, revisão de direitos e verificação separadas.")
        decision = {"accepted": accepted, "training_allowed": training_allowed,
                    "rights_reviewed": rights_reviewed, "verified": verified,
                    "reviewer": reviewer, "verification_note": verification_note, "split": split}
        if len(json.dumps(decision)) > 12000:
            raise PolicyError("Revisão excessiva.")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT output_hash FROM experiences WHERE project_id=? AND id=?",
                             (identifier(project_id), identifier(run_id))).fetchone()
            if row is None or row["output_hash"] != expected_hash:
                raise PolicyError("A revisão não corresponde à saída registrada.")
            db.execute("UPDATE experiences SET accepted=?,training_allowed=?,rights_reviewed=?,verified=?,reviewer=?,verification_note=?,split=? WHERE id=?",
                       (*flags, reviewer.strip(), verification_note.strip(), split, run_id))
            db.execute("INSERT INTO reviews(experience_id,created_at,decision) VALUES(?,?,?)",
                       (run_id, now(), json.dumps(decision, ensure_ascii=False)))

    def training_rows(self, project_id: str, kind: str) -> list[dict]:
        if kind not in {"text", "code", "image"}:
            raise PolicyError("Tipo de corpus inválido.")
        with self.connect() as db:
            rows = db.execute("""SELECT * FROM experiences e WHERE project_id=? AND kind=?
                AND accepted=1 AND training_allowed=1 AND rights_reviewed=1 AND verified=1
                AND split='train' AND NOT EXISTS (SELECT 1 FROM experiences h
                    WHERE h.problem_hash=e.problem_hash AND h.split IN ('validation','test'))
                ORDER BY created_at,id""", (identifier(project_id), kind)).fetchall()
        seen, output = set(), []
        for row in rows:
            if row["problem_hash"] in seen:
                continue
            seen.add(row["problem_hash"])
            metadata = json.loads(row["metadata"])
            context = metadata.get("generation_context")
            if not isinstance(context, list) or not context:
                context = [{"role": "user", "content": row["prompt"]}]
            output.append({"id": row["id"], "kind": kind, "split": "train",
                "messages": [*context, {"role": "assistant", "content": row["response"]}],
                "metadata": metadata, "output_hash": row["output_hash"],
                "reviewer": row["reviewer"], "verification_note": row["verification_note"]})
        return output
