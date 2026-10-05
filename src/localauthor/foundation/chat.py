"""Optional foundation integration; existing laboratory behavior stays unchanged."""
from __future__ import annotations

import json
import logging

from ..chat import ChatService
from ..errors import PolicyError
from ..util import utcnow
from .experience import ExperienceStore
from .models import child, identifier
from .runtime import check_cancel
from .service import FoundationService


class FoundationChatService(ChatService):
    def __init__(self, store, settings, knowledge):
        super().__init__(store, settings, knowledge)
        self.foundation = FoundationService(settings.home)

    def validate_message(self, message, mode, input_format="text"):
        if mode in {"foundation", "image"}:
            # Keep Unicode, secret and format checks; do not use the tiny model cap.
            super().validate_message(message, "guide", input_format)
            if len(message) > 8000:
                raise PolicyError("Mensagem excede 8.000 caracteres; o texto não foi cortado.")
        else:
            super().validate_message(message, mode, input_format)

    def _discard_undelivered(self, project_id, response):
        """Compensate a failed chat write, but never remove a human-reviewed record."""
        run_id = response.get("experience_id")
        if not run_id:
            return
        run_id = identifier(run_id)
        store = ExperienceStore(self.settings.home)
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            removed = db.execute("DELETE FROM experiences WHERE id=? AND project_id=? "
                "AND accepted=0 AND training_allowed=0 AND verified=0 "
                "AND NOT EXISTS (SELECT 1 FROM reviews WHERE experience_id=?)",
                (run_id, project_id, run_id)).rowcount
        if removed and response.get("origin") == "foundation_image":
            child(self.settings.home / "foundation" / "artifacts", f"{project_id}/{run_id}.png").unlink(missing_ok=True)

    def respond(self, project_id, conversation_id, message, mode="guide", cancel=None, input_format="text", image_options=None):
        if image_options is not None and mode != "image":
            raise PolicyError("Parâmetros visuais exigem modo imagem.")
        if mode not in {"foundation", "image"}:
            return super().respond(project_id, conversation_id, message, mode, cancel, input_format)
        self.validate_message(message, mode, input_format)
        with self.lock:
            check_cancel(cancel)
            conversation = self.get(project_id, conversation_id)
            if len(conversation["messages"]) >= 200:
                raise PolicyError("Conversa cheia. Inicie outra conversa.")
            if mode == "image":
                response = self.foundation.create_image(project_id, message, cancel, options=image_options)
            else:
                found = self.knowledge.consult(message[:1000], project_id, False)
                evidence = [{**item, "scope": project_id} for item in found["evidence"]]
                response = self.foundation.answer(project_id, message, conversation["messages"],
                    evidence, cancel, input_format=input_format)
            try:
                check_cancel(cancel)
                metadata = json.dumps({k: v for k, v in response.items() if k != "content"}, ensure_ascii=False)
                with self.store.connect() as db:
                    db.execute("BEGIN IMMEDIATE")
                    used = db.execute("SELECT coalesce(sum(length(CAST(content AS BLOB))+length(CAST(metadata AS BLOB))),0) FROM messages").fetchone()[0]
                    size = len((message + response["content"] + metadata).encode("utf-8"))
                    if used + size > min(self.settings.max_store_bytes, 32_000_000):
                        raise PolicyError("Limite de armazenamento das conversas atingido.")
                    check_cancel(cancel)
                    now = utcnow()
                    db.execute("INSERT INTO messages(conversation_id,role,content,metadata,created_at) VALUES(?,'user',?,?,?)",
                        (conversation_id, message, json.dumps({"format": input_format}), now))
                    db.execute("INSERT INTO messages(conversation_id,role,content,metadata,created_at) VALUES(?,'assistant',?,?,?)",
                        (conversation_id, response["content"], metadata, now))
                    db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, conversation_id))
            except Exception:
                try:
                    self._discard_undelivered(project_id, response)
                except Exception:
                    logging.error("Falha na limpeza de resultado foundation não entregue; revisão local necessária.")
                raise
            return self.get(project_id, conversation_id)
