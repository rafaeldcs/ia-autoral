from __future__ import annotations
import threading
from datetime import datetime, timezone
from pathlib import Path
from .config import Settings
from .errors import PolicyError
from .safety import PathPolicy
from .store import Store


class KnowledgeService:
    def __init__(self, store: Store, settings: Settings):
        self.store, self.settings = store, settings

    def index_project(self, project_id: str, cancel: threading.Event | None = None) -> dict:
        project = self.store.project(project_id)
        policy = PathPolicy(Path(project["root"]), self.settings.max_file_bytes)
        result = {"indexed": 0, "unchanged": 0, "skipped": [], "cancelled": False}
        total = 0
        for relative in policy.files(self.settings.max_project_files):
            if cancel and cancel.is_set():
                result["cancelled"] = True
                break
            try:
                raw = policy.read(relative)
                total += len(raw)
                if total > self.settings.max_snapshot_bytes:
                    raise PolicyError("Quota de bytes do índice por execução atingida.")
                entry = self.store.ingest(project_id, relative, relative, raw.decode("utf-8"))
                result["indexed" if entry["changed"] else "unchanged"] += 1
            except (PolicyError, UnicodeError, OSError) as exc:
                result["skipped"].append({"path": relative, "reason": str(exc)})
        self.store.audit("project.indexed", {"project_id": project_id, **result})
        return result

    def consult(self, query: str, scope: str, include_global: bool = False) -> dict:
        hits = self.store.search(query, scope, include_global=include_global)
        now = datetime.now(timezone.utc)
        stale = [h["source_id"] for h in hits if h["kind"] == "web" and (now - datetime.fromisoformat(h["checked_at"])).total_seconds() > self.settings.cache_ttl_seconds]
        need = not hits or bool(stale)
        reason = "no_local_evidence" if not hits else "stale_web_evidence" if stale else "local_evidence_available"
        return {"mode": "retrieval_only", "generated_answer": None, "evidence": hits, "research_needed": need, "reason": reason, "offline": self.settings.offline, "notice": "Trechos recuperados, não resposta de um modelo treinado. Correspondência textual não é garantia de verdade."}
