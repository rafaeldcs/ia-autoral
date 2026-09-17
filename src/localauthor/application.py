from __future__ import annotations
from pathlib import Path
import uuid
from .config import Settings
from .store import Store
from .knowledge import KnowledgeService
from .research import ResearchService
from .tasks import TaskService
from .runner import SandboxRunner
from .jobs import JobQueue
from .safety import PathPolicy
from .errors import PolicyError


class Application:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.store = Store(settings.home / "memory.sqlite3", settings.max_store_bytes)
        self.knowledge = KnowledgeService(self.store, settings)
        self.research = ResearchService(self.store, settings)
        self.tasks = TaskService(self.store, settings)
        self.runner = SandboxRunner(settings, self.tasks)
        self.jobs = JobQueue(self.store, {
            "index": lambda p, c: self.knowledge.index_project(p["project_id"], c),
            "research": lambda p, c: self.research.collect(p["urls"], p["scope"], c),
            "verify": lambda p, c: self.runner.run(p["task_id"], p["kind"], p.get("project_file", ""), c),
            "train": self._train,
        })

    def _train(self, payload, cancel):
        try:
            from .nn.train import train
            from .nn.transformer import ModelConfig
        except ImportError as exc:
            raise PolicyError("NumPy não instalado. Instale a dependência local descrita no README, sem baixar modelos.") from exc
        manifest = PathPolicy(self.settings.home / "corpus", 4_000_000).resolve(payload["manifest"])
        if manifest.name != "manifest.json":
            raise PolicyError("Selecione um manifest.json dentro da pasta corpus.")
        if not manifest.is_file():
            raise PolicyError("Manifesto não encontrado na pasta corpus.")
        out = self.settings.home / "models" / uuid.uuid4().hex
        config = ModelConfig(**payload.get("config", {}))
        result = train(manifest, out, config, steps=payload.get("steps", 100), batch_size=payload.get("batch_size", 2), tokenizer_kind=payload.get("tokenizer", "byte"), cancel=cancel)
        return {**result, "model_directory": out.name}

    def start(self):
        self.jobs.start()

    def close(self):
        self.jobs.close()
