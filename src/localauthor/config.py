from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
import os
import secrets
from .errors import PolicyError
from .util import read_json, write_json, atomic_write


def default_home() -> Path:
    override = os.environ.get("LOCALAI_HOME")
    if override:
        return Path(override).expanduser().absolute()
    parent = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
    return parent / ("LocalAuthor" if os.name == "nt" else ".localauthor")


@dataclass
class Settings:
    home: Path
    port: int = 8765
    offline: bool = True
    allowed_domains: list[str] = field(default_factory=lambda: ["learn.microsoft.com", "docs.python.org"])
    max_file_bytes: int = 512_000
    max_project_files: int = 1500
    max_snapshot_bytes: int = 32_000_000
    max_store_bytes: int = 256_000_000
    cache_ttl_seconds: int = 86400
    docker_image: str = ""
    max_runner_seconds: int = 90

    def initialize(self) -> None:
        self.home = self.home.expanduser().absolute()
        self.home.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            self.home.chmod(0o700)
        for folder in ("workspaces", "journals", "corpus", "models", "exports"):
            (self.home / folder).mkdir(exist_ok=True)
        token_file = self.home / "api.token"
        if not token_file.exists():
            atomic_write(token_file, secrets.token_urlsafe(32).encode("ascii"))

    @property
    def token(self) -> str:
        return (self.home / "api.token").read_text(encoding="ascii").strip()

    @classmethod
    def load(cls, home: Path | None = None) -> "Settings":
        home = (home or default_home()).expanduser().absolute()
        file = home / "settings.json"
        raw = read_json(file) if file.exists() else {}
        valid = set(cls.__dataclass_fields__) - {"home"}
        unknown = set(raw) - valid
        if unknown:
            raise PolicyError(f"Configurações desconhecidas: {sorted(unknown)}")
        result = cls(home, **raw)
        if type(result.port) is not int or not 1024 <= result.port <= 65535:
            raise PolicyError("A porta deve estar entre 1024 e 65535.")
        if type(result.offline) is not bool:
            raise PolicyError("offline deve ser booleano.")
        for field_name in ("max_file_bytes", "max_project_files", "max_snapshot_bytes", "max_store_bytes", "cache_ttl_seconds", "max_runner_seconds"):
            val = getattr(result, field_name)
            if type(val) is not int or val <= 0:
                raise PolicyError(f"{field_name} deve ser inteiro positivo.")
        if not isinstance(result.allowed_domains, list) or any(not isinstance(x, str) or "/" in x or ":" in x or not x for x in result.allowed_domains):
            raise PolicyError("allowed_domains deve conter nomes DNS exatos, sem protocolo.")
        result.initialize()
        if not file.exists():
            write_json(file, {k: v for k, v in asdict(result).items() if k != "home"})
        return result
