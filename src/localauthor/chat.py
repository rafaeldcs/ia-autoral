from __future__ import annotations
import json
import hashlib
import threading
import uuid
from pathlib import Path
from .engineering import DONE, QUALITY, SOURCES, guidance
from .errors import PolicyError, NotFoundError
from .safety import PathPolicy, reject_secrets
from .util import utcnow, read_json
from .investigation import InvestigationService

CHAT_SCHEMA = """
CREATE TABLE IF NOT EXISTS project_preferences(
 project_id TEXT PRIMARY KEY REFERENCES projects(id), method TEXT NOT NULL,
 wip_limit INTEGER NOT NULL, definition_of_done TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS conversations(
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
 title TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS messages(
 id INTEGER PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
 role TEXT NOT NULL, content TEXT NOT NULL, metadata TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_conversations_project ON conversations(project_id,updated_at);
CREATE INDEX IF NOT EXISTS ix_messages_conversation ON messages(conversation_id,id);
"""

# Keep the application at the same output budget as the evaluated code course.
# The model context is a rolling window, not an output-length limit.
MODEL_OUTPUT_TOKENS = 220


class ChatService:
    def __init__(self, store, settings, knowledge):
        self.store, self.settings, self.knowledge = store, settings, knowledge
        self.investigations = InvestigationService(store, settings)
        self.lock = threading.Lock()
        with store.connect() as db:
            db.executescript(CHAT_SCHEMA)

    def preferences(self, project_id):
        self.store.project(project_id)
        with self.store.connect() as db:
            row = db.execute("SELECT * FROM project_preferences WHERE project_id=?", (project_id,)).fetchone()
        return {**(dict(row) if row else {"project_id": project_id, "method": "kanban", "wip_limit": 3, "definition_of_done": DONE}), "quality": QUALITY, "sources": SOURCES}

    def save_preferences(self, project_id, method, wip_limit, definition_of_done):
        self.store.project(project_id)
        if method not in {"scrum", "kanban"} or type(wip_limit) is not int or not 1 <= wip_limit <= 100:
            raise PolicyError("Selecione Scrum ou Kanban e um limite de 1 a 100 itens.")
        if not isinstance(definition_of_done, str) or not 1 <= len(definition_of_done.strip()) <= 2000:
            raise PolicyError("Definição de pronto deve ter de 1 a 2.000 caracteres.")
        reject_secrets(definition_of_done)
        with self.store.connect() as db:
            db.execute("INSERT INTO project_preferences VALUES(?,?,?,?) ON CONFLICT(project_id) DO UPDATE SET method=excluded.method,wip_limit=excluded.wip_limit,definition_of_done=excluded.definition_of_done", (project_id, method, wip_limit, definition_of_done.strip()))
        return self.preferences(project_id)

    def conversations(self, project_id):
        self.store.project(project_id)
        with self.store.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM conversations WHERE project_id=? ORDER BY updated_at DESC", (project_id,))]

    def create(self, project_id, title):
        self.store.project(project_id)
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 100:
            raise PolicyError("Título deve ter de 1 a 100 caracteres.")
        reject_secrets(title)
        if self.settings.token in title:
            raise PolicyError("Não use o token local como título.")
        now = utcnow()
        result = {"id": uuid.uuid4().hex, "project_id": project_id, "title": title.strip(), "created_at": now, "updated_at": now}
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT count(*) FROM conversations WHERE project_id=?", (project_id,)).fetchone()[0] >= 200:
                raise PolicyError("Limite de 200 conversas neste projeto.")
            db.execute("INSERT INTO conversations VALUES(:id,:project_id,:title,:created_at,:updated_at)", result)
        return result

    def get(self, project_id, conversation_id):
        self.store.project(project_id)
        with self.store.connect() as db:
            row = db.execute("SELECT * FROM conversations WHERE id=? AND project_id=?", (conversation_id, project_id)).fetchone()
            if row is None:
                raise NotFoundError("Conversa não encontrada neste projeto.")
            messages = [{**dict(r), "metadata": json.loads(r["metadata"])} for r in db.execute("SELECT * FROM messages WHERE conversation_id=? ORDER BY id", (conversation_id,))]
        return {**dict(row), "messages": messages}

    def validate_message(self, message, mode, input_format="text"):
        if not isinstance(message, str) or not 1 <= len(message.strip()) <= 8000:
            raise PolicyError("Mensagem deve ter de 1 a 8.000 caracteres.")
        if mode not in {"guide", "knowledge", "model", "investigation"}:
            raise PolicyError("Modo de conversa inválido.")
        if input_format not in {"text", "code"}:
            raise PolicyError("Formato deve ser texto ou código.")
        try:
            raw = message.encode("utf-8")
        except UnicodeError as exc:
            raise PolicyError("A mensagem contém uma sequência Unicode inválida. O texto não foi alterado nem salvo.") from exc
        if mode == "model" and len(raw) > 180:
            raise PolicyError("O modelo experimental aceita até 180 bytes por pedido. O texto não foi cortado; reduza o pedido ou escolha outro modo.")
        reject_secrets(message)
        if self.settings.token in message:
            raise PolicyError("Não envie o token local na conversa.")

    def respond(self, project_id, conversation_id, message, mode="guide", cancel=None, input_format="text"):
        self.validate_message(message, mode, input_format)
        # One turn at a time preserves chronological pairs, including model jobs.
        with self.lock:
            if cancel and cancel.is_set():
                raise PolicyError("Geração cancelada.")
            conversation = self.get(project_id, conversation_id)
            if len(conversation["messages"]) >= 200:
                raise PolicyError("Conversa cheia. Inicie outra conversa.")
            project = self.store.project(project_id)
            if mode == "model":
                response = self._generate(message)
            elif mode == "investigation":
                response = self.investigations.answer(project_id, message)
            elif mode == "knowledge":
                result = self.knowledge.consult(message[:1000], project_id, False)
                response = {"origin": "retrieval_only", "content": "\n\n".join(f"{e['title']} — linhas {e['start_line']}–{e['end_line']}\n{e['text']}" for e in result["evidence"])[:12000] or "Ainda não encontrei fontes locais para esse pedido. Importe notas ou indexe a pasta nas ferramentas avançadas.", "evidence": result["evidence"], "sources": [], "researched_now": False}
            else:
                preferences = self.preferences(project_id)
                response = guidance(message, preferences["method"], project["name"])
                response["content"] += "\n\nCritério de pronto deste projeto: " + preferences["definition_of_done"]
            if cancel and cancel.is_set():
                raise PolicyError("Geração cancelada; nenhuma mensagem foi salva.")
            now = utcnow()
            metadata = json.dumps({k: v for k, v in response.items() if k != "content"}, ensure_ascii=False)
            with self.store.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                used = db.execute("SELECT coalesce(sum(length(CAST(content AS BLOB))+length(CAST(metadata AS BLOB))),0) FROM messages").fetchone()[0]
                if used + len((message + response["content"] + metadata).encode()) > min(self.settings.max_store_bytes, 32_000_000):
                    raise PolicyError("Limite de armazenamento das conversas atingido.")
                db.execute("INSERT INTO messages(conversation_id,role,content,metadata,created_at) VALUES(?, 'user', ?, ?, ?)", (conversation_id, message, json.dumps({"format": input_format}), now))
                db.execute("INSERT INTO messages(conversation_id,role,content,metadata,created_at) VALUES(?, 'assistant', ?, ?, ?)", (conversation_id, response["content"], metadata, now))
                db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, conversation_id))
            return self.get(project_id, conversation_id)

    def _generate(self, message):
        # This tiny model has no qualified general conversation or tool use capability.
        if len(message.encode("utf-8")) > 180:
            raise PolicyError("O experimento neural aceita pedidos curtos de até 180 bytes. Use os outros modos para mensagens longas.")
        report_file = self.settings.home / "exports" / "engineering-report.json"
        communication_file = self.settings.home / "exports" / "communication-report.json"
        if communication_file.exists() and read_json(communication_file).get("chatEnabled") is True:
            report_file = communication_file
        functional = message.startswith("Teste JS h:")
        if functional:
            report_file = self.settings.home / "exports" / "functional-testing-report.json"
            if not report_file.exists():
                raise PolicyError("O modelo de testes funcionais ainda não foi aprovado no laboratório.")
            certification = read_json(report_file)
            checks = certification.get("functionalTests", {})
            if not (certification.get("chatEnabled") is True
                    and certification.get("scope") == "orbit-functional-lab"
                    and checks.get("total") == checks.get("passed") == checks.get("faultsDetected") == 36):
                raise PolicyError("O modelo de testes funcionais ainda não foi aprovado no laboratório.")
        if not report_file.exists():
            report_file = self.settings.home / "exports/jira-experimental/generalization-report.json"
        if not report_file.exists():
            raise PolicyError("Nenhum candidato local avaliado disponível.")
        report = read_json(report_file)
        if report.get("state") != "evaluated":
            raise PolicyError("O candidato ainda não concluiu sua avaliação.")
        checkpoint = Path(report["selectedCheckpoint"])
        relative = checkpoint.relative_to(self.settings.home / "models")
        if checkpoint.is_symlink() or not checkpoint.resolve().is_relative_to((self.settings.home / "models").resolve()):
            raise PolicyError("Checkpoint fora da pasta de modelos.")
        if functional and hashlib.sha256(checkpoint.read_bytes()).hexdigest() != report.get("checkpointHash"):
            raise PolicyError("O modelo funcional foi alterado depois da avaliação.")
        from .nn.checkpoint import load_checkpoint
        model, _, tokenizer, _, _ = load_checkpoint(checkpoint)
        prompt = [tokenizer.bos_id] + tokenizer.encode(message)
        if len(prompt) > model.config.context_length:
            raise PolicyError("Pedido excede o contexto do modelo.")
        generated = model.generate(prompt, max_tokens=MODEL_OUTPUT_TOKENS, temperature=.05, seed=31)
        try:
            content = tokenizer.decode(generated)
        except UnicodeError as exc:
            raise PolicyError("O modelo produziu texto UTF-8 inválido. Nenhum caractere foi substituído e nenhuma resposta foi salva.") from exc
        truncated = len(generated) >= MODEL_OUTPUT_TOKENS
        notice = "Geração experimental só desta mensagem; histórico e arquivos não foram enviados ao modelo. Não executada nem aplicada."
        if functional:
            notice = "Teste Playwright para o laboratório Orbit; requer os auxiliares h documentados. A resposta ainda precisa passar pela sandbox. " + notice
        if truncated:
            notice = "Saída possivelmente incompleta: atingiu o limite de geração. Não use como código pronto. " + notice
        return {"origin": "local_model", "content": content or "[O modelo encerrou sem produzir texto.]", "model": str(relative), "sources": [], "history_used": False, "possibly_truncated": truncated, "skill": "orbit_functional_tests" if functional else "experimental_general", "notice": notice}
