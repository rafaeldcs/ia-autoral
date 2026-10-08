"""Explicit, project-scoped conversational memory. Never weight training."""
from __future__ import annotations

import json
import re
import uuid

from .errors import PolicyError
from .util import utcnow

MEMORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversation_memory(
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
 content TEXT NOT NULL, active INTEGER NOT NULL,
 source_message_id INTEGER NOT NULL REFERENCES messages(id),
 forgotten_message_id INTEGER REFERENCES messages(id),
 updated_at TEXT NOT NULL, UNIQUE(project_id,content));
"""


def conversation_bytes(db):
    messages = db.execute("SELECT coalesce(sum(length(CAST(content AS BLOB))+length(CAST(metadata AS BLOB))),0) FROM messages").fetchone()[0]
    notes = db.execute("SELECT coalesce(sum(length(CAST(content AS BLOB))),0) FROM conversation_memory").fetchone()[0]
    return messages + notes


class ConversationMemoryMixin:
    def memories(self, project_id):
        self.store.project(project_id)
        with self.store.connect() as db:
            return [dict(row) for row in db.execute(
                "SELECT id,project_id,content,source_message_id FROM conversation_memory "
                "WHERE project_id=? AND active=1 ORDER BY updated_at DESC,rowid DESC", (project_id,))]

    def _memory_turn(self, project_id, conversation_id, message, cancel, input_format):
        # Only an entire human text turn can make a persistent change. Quoted
        # documents, model output, code and research are never parsed as commands.
        if input_format != "text":
            return None
        match = re.fullmatch(r"\s*(Lembre-se|Esqueça):\s*(.*?)\s*", message, re.I | re.S)
        listing = message.strip().casefold() == "o que você lembra deste projeto?"
        if not match and not listing:
            return None
        operation = "list" if listing else ("remember" if match[1].casefold() == "lembre-se" else "forget")
        content = "" if listing else match[2]
        if not listing and not 1 <= len(content) <= 600:
            raise PolicyError("Memória deve ter de 1 a 600 caracteres; nada foi cortado.")
        with self.lock:
            self._check_memory_cancel(cancel)
            conversation = self.get(project_id, conversation_id)
            if len(conversation["messages"]) >= 200:
                raise PolicyError("Conversa cheia. Inicie outra conversa.")
            now = utcnow()
            with self.store.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                active = list(db.execute("SELECT * FROM conversation_memory WHERE project_id=? AND active=1 "
                    "ORDER BY updated_at DESC,rowid DESC", (project_id,)))
                existing = None if listing else db.execute(
                    "SELECT * FROM conversation_memory WHERE project_id=? AND content=?", (project_id, content)).fetchone()
                if operation == "remember":
                    if (not existing or not existing["active"]) and len(active) >= 20:
                        raise PolicyError("Limite de 20 memórias ativas neste projeto. Esqueça uma antes de acrescentar outra.")
                    if not existing and db.execute("SELECT count(*) FROM conversation_memory WHERE project_id=?", (project_id,)).fetchone()[0] >= 200:
                        raise PolicyError("Limite de registros de memória neste projeto atingido.")
                    reply = "Já tenho essa preferência registrada." if existing and existing["active"] else "Guardei esta preferência para as próximas conversas deste projeto: " + content
                elif operation == "forget":
                    reply = "Deixei de usar esta memória: " + content if existing and existing["active"] else "Não encontrei essa memória ativa. Para consultar, escreva: O que você lembra deste projeto?"
                else:
                    reply = "Memórias ativas deste projeto:\n" + "\n".join("• " + row["content"] for row in active) if active else "Ainda não há memórias guardadas neste projeto."
                reply += "\n\nPara guardar: Lembre-se: sua preferência. Para deixar de usar: Esqueça: o texto exato da memória. Isso não treina os pesos nem autoriza ações. O histórico original permanece nas conversas."
                active_count = len(active)
                if operation == "remember" and (not existing or not existing["active"]): active_count += 1
                if operation == "forget" and existing and existing["active"]: active_count -= 1
                metadata = json.dumps({"origin": "project_memory", "operation": operation,
                    "weights_trained": False, "active_memories": active_count}, ensure_ascii=False)
                size = len((message + reply + metadata + json.dumps({"format": input_format})).encode("utf-8"))
                if conversation_bytes(db) + size + (len(content.encode("utf-8")) if operation == "remember" and not existing else 0) > min(self.settings.max_store_bytes, 32_000_000):
                    raise PolicyError("Limite de armazenamento das conversas atingido.")
                self._check_memory_cancel(cancel)
                source = db.execute("INSERT INTO messages(conversation_id,role,content,metadata,created_at) VALUES(?,'user',?,?,?)",
                    (conversation_id, message, json.dumps({"format": input_format}), now)).lastrowid
                if operation == "remember" and (not existing or not existing["active"]):
                    db.execute("INSERT INTO conversation_memory VALUES(?,?,?,1,?,NULL,?) "
                        "ON CONFLICT(project_id,content) DO UPDATE SET active=1,source_message_id=excluded.source_message_id,forgotten_message_id=NULL,updated_at=excluded.updated_at",
                        (uuid.uuid4().hex, project_id, content, source, now))
                elif operation == "forget" and existing and existing["active"]:
                    db.execute("UPDATE conversation_memory SET active=0,forgotten_message_id=?,updated_at=? WHERE id=?", (source, now, existing["id"]))
                db.execute("INSERT INTO messages(conversation_id,role,content,metadata,created_at) VALUES(?,'assistant',?,?,?)", (conversation_id, reply, metadata, now))
                db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, conversation_id))
                self._check_memory_cancel(cancel)
            return self.get(project_id, conversation_id)

    @staticmethod
    def _check_memory_cancel(cancel):
        if cancel and cancel.is_set():
            raise PolicyError("Geração cancelada; nenhuma mensagem ou memória foi salva.")
