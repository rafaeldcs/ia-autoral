from __future__ import annotations
import json
import math
import threading
import uuid
from .errors import NotFoundError, PolicyError
from .store import Store
from .util import utcnow


class JobQueue:
    """Persistent single worker. Shutdown is cooperative and explicitly reported."""
    def __init__(self, store: Store, handlers: dict):
        self.store, self.handlers = store, handlers
        self.stop_event, self.wakeup = threading.Event(), threading.Event()
        self.current_id = None
        self.current_cancel = threading.Event()
        self._lifecycle = threading.RLock()
        self._started = False
        with store.connect() as db:
            db.execute("UPDATE jobs SET state='interrupted',error='Processo anterior interrompido.',updated_at=? WHERE state='running'", (utcnow(),))
        self.thread = threading.Thread(target=self._run, daemon=True, name="localai-worker")

    def start(self):
        with self._lifecycle:
            if self.stop_event.is_set():
                raise PolicyError("Fila encerrada; crie uma nova instância para reiniciar.")
            if not self._started:
                self.thread.start()
                self._started = True

    def submit(self, kind: str, payload: dict) -> dict:
        if kind not in self.handlers:
            raise PolicyError("Tipo de job não permitido.")
        raw = json.dumps(payload, ensure_ascii=False)
        if len(raw) > 20_000:
            raise PolicyError("Payload grande demais.")
        ident, now = uuid.uuid4().hex, utcnow()
        with self._lifecycle:
            if self.stop_event.is_set():
                raise PolicyError("Fila em encerramento; nenhum novo job foi aceito.")
            with self.store.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                if db.execute("SELECT COUNT(*) FROM jobs WHERE state IN ('queued','running')").fetchone()[0] >= 20:
                    raise PolicyError("Fila cheia.")
                db.execute("INSERT INTO jobs VALUES(?,?,?,'queued',NULL,NULL,?,?)", (ident, kind, raw, now, now))
            self.wakeup.set()
        return self.get(ident)

    def get(self, ident: str) -> dict:
        with self.store.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (ident,)).fetchone()
        if row is None:
            raise NotFoundError("Job não encontrado.")
        result = dict(row)
        result["payload"] = json.loads(result["payload"])
        result["result"] = json.loads(result["result"]) if result["result"] else None
        return result

    def list(self):
        with self.store.connect() as db:
            ids = [r[0] for r in db.execute("SELECT id FROM jobs ORDER BY created_at DESC LIMIT 50")]
        return [self.get(i) for i in ids]

    def cancel(self, ident: str):
        with self._lifecycle:
            self.get(ident)
            with self.store.connect() as db:
                db.execute("UPDATE jobs SET state='cancelled',updated_at=? WHERE id=? AND state='queued'", (utcnow(), ident))
            if self.current_id == ident:
                self.current_cancel.set()
        return self.get(ident)

    def close(self, timeout: float = 15) -> bool:
        if type(timeout) not in {int, float} or not math.isfinite(timeout) or not 0 <= timeout <= 300:
            raise PolicyError("Prazo de encerramento inválido.")
        with self._lifecycle:
            self.stop_event.set()
            self.current_cancel.set()
            self.wakeup.set()
        if self.thread.is_alive() and threading.current_thread() is not self.thread:
            self.thread.join(timeout=timeout)
        # Pending jobs remain queued for an explicit process restart. Do not
        # pretend an uncooperative native operation has stopped.
        return not self.thread.is_alive()

    def _run(self):
        while True:
            with self._lifecycle:
                if self.stop_event.is_set():
                    return
                with self.store.connect() as db:
                    db.execute("BEGIN IMMEDIATE")
                    row = db.execute("SELECT * FROM jobs WHERE state='queued' ORDER BY created_at LIMIT 1").fetchone()
                    if row:
                        db.execute("UPDATE jobs SET state='running',updated_at=? WHERE id=?", (utcnow(), row["id"]))
                        self.current_cancel = threading.Event()
                        self.current_id = row["id"]
            if not row:
                self.wakeup.wait(0.25)
                self.wakeup.clear()
                continue
            try:
                if self.current_cancel.is_set():
                    raise PolicyError("Job cancelado antes da execução.")
                result = self.handlers[row["kind"]](json.loads(row["payload"]), self.current_cancel)
                state = "cancelled" if self.current_cancel.is_set() else "completed"
                with self.store.connect() as db:
                    db.execute("UPDATE jobs SET state=?,result=?,updated_at=? WHERE id=?", (state, json.dumps(result, ensure_ascii=False), utcnow(), row["id"]))
            except Exception as exc:
                with self.store.connect() as db:
                    db.execute("UPDATE jobs SET state=?,error=?,updated_at=? WHERE id=?", ("cancelled" if self.current_cancel.is_set() else "failed", str(exc)[:2000], utcnow(), row["id"]))
            finally:
                with self._lifecycle:
                    self.current_id = None
