from __future__ import annotations
import contextlib
import json
import re
import sqlite3
import uuid
from pathlib import Path
from .errors import PolicyError, NotFoundError
from .safety import PathPolicy, reject_secrets
from .util import utcnow, sha256

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version(version INTEGER NOT NULL);
INSERT INTO schema_version SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM schema_version);
CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT NOT NULL,root TEXT NOT NULL UNIQUE,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY,scope TEXT NOT NULL,locator TEXT NOT NULL,title TEXT NOT NULL,kind TEXT NOT NULL,current_version TEXT,checked_at TEXT NOT NULL,etag TEXT,last_modified TEXT,training_allowed INTEGER NOT NULL DEFAULT 0,UNIQUE(scope,locator));
CREATE TABLE IF NOT EXISTS versions(id TEXT PRIMARY KEY,source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,sha256 TEXT NOT NULL,content TEXT NOT NULL,created_at TEXT NOT NULL,UNIQUE(source_id,sha256));
CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY,version_id TEXT NOT NULL REFERENCES versions(id) ON DELETE CASCADE,start_line INTEGER NOT NULL,end_line INTEGER NOT NULL,text TEXT NOT NULL);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(text,content='chunks',content_rowid='id',tokenize='unicode61 remove_diacritics 2');
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN INSERT INTO chunks_fts(rowid,text) VALUES(new.id,new.text); END;
CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN INSERT INTO chunks_fts(chunks_fts,rowid,text) VALUES('delete',old.id,old.text); END;
CREATE TABLE IF NOT EXISTS relations(id TEXT PRIMARY KEY,scope TEXT NOT NULL,subject TEXT NOT NULL,predicate TEXT NOT NULL,object TEXT NOT NULL,evidence_chunk INTEGER NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,status TEXT NOT NULL,origin TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id),instruction TEXT NOT NULL,state TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,proposal_hash TEXT,test_result TEXT);
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,kind TEXT NOT NULL,payload TEXT NOT NULL,state TEXT NOT NULL,result TEXT,error TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS experiences(id TEXT PRIMARY KEY,task_id TEXT NOT NULL REFERENCES tasks(id),status TEXT NOT NULL,note TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,at TEXT NOT NULL,event TEXT NOT NULL,details TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_sources_scope ON sources(scope);
CREATE INDEX IF NOT EXISTS ix_versions_source ON versions(source_id);
CREATE INDEX IF NOT EXISTS ix_chunks_version ON chunks(version_id);
"""


class Store:
    def __init__(self, path: Path, max_store_bytes: int = 256_000_000):
        self.path = path
        self.max_store_bytes = max_store_bytes
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript(SCHEMA)
            if db.execute("SELECT version FROM schema_version").fetchone()[0] != 1:
                raise PolicyError("Versão de banco não suportada.")

    @contextlib.contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def audit(self, event: str, details: dict):
        with self.connect() as db:
            db.execute("INSERT INTO audit(at,event,details) VALUES(?,?,?)", (utcnow(), event, json.dumps(details, ensure_ascii=False)))

    def check_scope(self, scope: str):
        if scope != "global":
            self.project(scope)

    def project(self, project_id: str) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if row is None:
            raise NotFoundError("Projeto não encontrado.")
        return dict(row)

    def projects(self) -> list[dict]:
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM projects ORDER BY created_at DESC")]

    def add_project(self, name: str, root: str) -> dict:
        if not isinstance(name, str) or not name.strip() or len(name) > 120:
            raise PolicyError("Nome do projeto inválido.")
        policy = PathPolicy(Path(root))
        root_path = policy.root
        data_root = self.path.parent.resolve()
        if root_path == Path(root_path.anchor) or root_path == Path.home().resolve():
            raise PolicyError("Selecione um projeto específico, não o disco ou sua pasta pessoal.")
        if root_path.is_relative_to(data_root) or data_root.is_relative_to(root_path):
            raise PolicyError("A pasta de dados e os projetos devem estar separados.")
        item = dict(id=uuid.uuid4().hex, name=name.strip(), root=str(root_path), created_at=utcnow())
        try:
            with self.connect() as db:
                db.execute("INSERT INTO projects VALUES(:id,:name,:root,:created_at)", item)
        except sqlite3.IntegrityError as exc:
            raise PolicyError("Essa pasta já está cadastrada.") from exc
        self.audit("project.registered", {"id": item["id"]})
        return item

    def source(self, scope: str, locator: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT s.*,v.content,v.sha256 FROM sources s LEFT JOIN versions v ON v.id=s.current_version WHERE scope=? AND locator=?", (scope, locator)).fetchone()
            return dict(row) if row else None

    def ingest(self, scope: str, locator: str, title: str, content: str, *, kind: str = "file", training_allowed: bool = False, etag: str | None = None, last_modified: str | None = None) -> dict:
        self.check_scope(scope)
        if kind not in {"file", "web", "note"} or not content.strip() or len(content.encode("utf-8")) > 2_000_000:
            raise PolicyError("Fonte vazia, tipo inválido ou conteúdo muito grande.")
        if len(locator) > 2048 or len(title) > 240:
            raise PolicyError("Metadados de fonte muito longos.")
        reject_secrets(content)
        digest = sha256(content.encode("utf-8"))
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            source = db.execute("SELECT * FROM sources WHERE scope=? AND locator=?", (scope, locator)).fetchone()
            if source:
                sid = source["id"]
                existing = db.execute("SELECT id FROM versions WHERE source_id=? AND sha256=?", (sid, digest)).fetchone()
                if existing:
                    vid = existing["id"]
                    db.execute("UPDATE sources SET current_version=?,checked_at=?,etag=?,last_modified=?,title=? WHERE id=?", (vid, utcnow(), etag, last_modified, title, sid))
                    return {"id": sid, "version_id": vid, "changed": source["current_version"] != vid, "deduplicated": True}
            else:
                sid = uuid.uuid4().hex
                db.execute("INSERT INTO sources(id,scope,locator,title,kind,checked_at,training_allowed) VALUES(?,?,?,?,?,?,?)", (sid, scope, locator, title, kind, utcnow(), int(training_allowed)))
            used = db.execute("SELECT COALESCE(SUM(length(CAST(content AS BLOB))),0) FROM versions").fetchone()[0]
            if used + len(content.encode("utf-8")) > self.max_store_bytes:
                raise PolicyError("Quota lógica de conteúdo atingida; remova fontes ou aumente-a conscientemente.")
            vid = uuid.uuid4().hex
            db.execute("INSERT INTO versions VALUES(?,?,?,?,?)", (vid, sid, digest, content, utcnow()))
            lines = content.splitlines(keepends=True)
            for start in range(0, len(lines), 32):
                end = min(start + 40, len(lines))
                text = "".join(lines[start:end])
                if text.strip():
                    db.execute("INSERT INTO chunks(version_id,start_line,end_line,text) VALUES(?,?,?,?)", (vid, start + 1, end, text))
            db.execute("UPDATE sources SET current_version=?,checked_at=?,etag=?,last_modified=?,title=? WHERE id=?", (vid, utcnow(), etag, last_modified, title, sid))
            return {"id": sid, "version_id": vid, "changed": True, "deduplicated": False}

    def touch_source(self, sid: str):
        with self.connect() as db:
            db.execute("UPDATE sources SET checked_at=? WHERE id=?", (utcnow(), sid))

    def delete_source(self, sid: str, scope: str):
        self.check_scope(scope)
        with self.connect() as db:
            count = db.execute("DELETE FROM sources WHERE id=? AND scope=?", (sid, scope)).rowcount
        if not count:
            raise NotFoundError("Fonte não encontrada nesse escopo.")
        self.audit("source.deleted", {"id": sid, "scope": scope, "weights_unlearned": False})

    def search(self, query: str, scope: str = "global", *, include_global: bool = False, limit: int = 5) -> list[dict]:
        self.check_scope(scope)
        if not isinstance(query, str) or len(query) > 1000:
            raise PolicyError("Consulta inválida ou longa demais.")
        terms = list(dict.fromkeys(re.findall(r"[^\W_]{2,}", query, re.UNICODE)))[:12]
        if not terms:
            return []
        # Expressions are constructed from quoted tokens, never raw FTS syntax.
        match = " OR ".join('"' + t.replace('"', '""') + '"' for t in terms)
        scopes = [scope] if not include_global or scope == "global" else [scope, "global"]
        slots = ",".join("?" for _ in scopes)
        sql = f"""SELECT c.id AS chunk_id,c.start_line,c.end_line,c.text,s.id AS source_id,s.title,s.locator,s.scope,s.kind,s.checked_at,v.sha256 AS document_hash,bm25(chunks_fts) AS rank
                  FROM chunks_fts JOIN chunks c ON c.id=chunks_fts.rowid JOIN versions v ON v.id=c.version_id JOIN sources s ON s.current_version=v.id
                  WHERE chunks_fts MATCH ? AND s.scope IN ({slots}) ORDER BY rank LIMIT ?"""
        with self.connect() as db:
            return [dict(r) for r in db.execute(sql, [match, *scopes, min(max(int(limit), 1), 20)])]

    def sources(self, scope: str) -> list[dict]:
        self.check_scope(scope)
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT id,title,kind,locator,checked_at,training_allowed,current_version FROM sources WHERE scope=? ORDER BY checked_at DESC", (scope,))]

    def add_relation(self, scope: str, subject: str, predicate: str, obj: str, chunk_id: int, status: str = "proposed", origin: str = "human") -> dict:
        self.check_scope(scope)
        if status not in {"proposed", "verified", "contradicted", "superseded"} or origin not in {"human", "deterministic", "model"}:
            raise PolicyError("Estado ou origem da relação inválido.")
        if origin == "model" and status == "verified":
            raise PolicyError("O modelo não pode verificar sua própria hipótese.")
        if predicate not in {"defines", "uses", "depends_on", "fixes", "applies_to_version", "contradicts"}:
            raise PolicyError("Tipo de relação não suportado.")
        if any(not isinstance(s, str) or not s.strip() or len(s) > 240 for s in [subject, obj]):
            raise PolicyError("Conceitos inválidos.")
        item = dict(id=uuid.uuid4().hex, scope=scope, subject=subject, predicate=predicate, object=obj, evidence_chunk=chunk_id, status=status, origin=origin, created_at=utcnow())
        with self.connect() as db:
            source = db.execute("SELECT s.scope FROM chunks c JOIN sources s ON s.current_version=c.version_id WHERE c.id=?", (chunk_id,)).fetchone()
            if not source or source[0] != scope:
                raise PolicyError("A evidência deve estar no mesmo escopo e na versão atual.")
            db.execute("INSERT INTO relations VALUES(:id,:scope,:subject,:predicate,:object,:evidence_chunk,:status,:origin,:created_at)", item)
        return item

    def relations(self, scope: str) -> list[dict]:
        self.check_scope(scope)
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT r.*, CASE WHEN s.current_version=c.version_id THEN 1 ELSE 0 END AS current_evidence FROM relations r JOIN chunks c ON c.id=r.evidence_chunk JOIN versions v ON v.id=c.version_id JOIN sources s ON s.id=v.source_id WHERE r.scope=? ORDER BY r.created_at DESC", (scope,))]

    def stats(self) -> dict:
        with self.connect() as db:
            counts = {table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("projects", "sources", "versions", "chunks", "relations", "tasks")}
        counts["database_bytes"] = sum(p.stat().st_size for p in self.path.parent.glob(self.path.name + "*") if p.is_file())
        return counts

    def backup(self, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        # sqlite3's transaction context commits/rolls back but does not close
        # the connection. Windows keeps the snapshot locked until it is closed.
        with self.connect() as db, contextlib.closing(sqlite3.connect(destination)) as backup:
            with backup:
                db.backup(backup)
