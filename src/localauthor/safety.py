from __future__ import annotations
import os
import re
from pathlib import Path, PureWindowsPath
from .errors import PolicyError

IGNORED = {".git", ".github", ".svn", "node_modules", "bin", "obj", ".venv", "venv", "__pycache__", ".idea", ".vs", "checkpoints", ".localauthor"}
READ_EXT = {".md", ".txt", ".html", ".htm", ".cs", ".csproj", ".sln", ".py", ".json", ".ts", ".tsx", ".js", ".css", ".xml", ".yml", ".yaml"}
EDIT_EXT = {".md", ".txt", ".cs", ".py", ".ts", ".tsx", ".js", ".css", ".html"}
SENSITIVE_NAMES = {"credentials", "secrets.json", "id_rsa", "id_ed25519", "api.token", "nuget.config", ".npmrc"}
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{25,}\b"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"(?i)(?:api[_-]?key|password|client[_-]?secret|access[_-]?token)\s*[:=]\s*[\"'][^\"'\s]{8,}[\"']"),
]


def reject_secrets(text: str) -> None:
    if any(pattern.search(text) for pattern in SECRET_PATTERNS):
        raise PolicyError("Conteúdo com possível segredo bloqueado; revise-o antes da importação.")


def validate_relative(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise PolicyError("Caminho relativo inválido.")
    if "\x00" in value or "\\" in value or ":" in value or value.startswith("/") or PureWindowsPath(value).drive:
        raise PolicyError("Caminhos absolutos, alternativos ou Windows não são permitidos nesta operação.")
    parts = value.split("/")
    if any(p in {"", ".", ".."} or p.endswith((" ", ".")) for p in parts):
        raise PolicyError("Caminho não canônico.")
    if any(p.casefold() in IGNORED or p.casefold() in SENSITIVE_NAMES or p.casefold().startswith(".env") for p in parts):
        raise PolicyError("Arquivo ou diretório excluído pela política.")
    reserved = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}
    if any(p.split(".")[0].casefold() in reserved for p in parts):
        raise PolicyError("Nome reservado do sistema.")
    return value


class PathPolicy:
    def __init__(self, root: Path, max_file_bytes: int = 512_000):
        root = root.expanduser().absolute()
        # Reject reparse points in every ancestor, including a selected symlink root.
        for part in [root, *root.parents]:
            if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
                raise PolicyError("Links simbólicos/junctions não são permitidos no caminho autorizado.")
        self.root = root.resolve(strict=True)
        if not self.root.is_dir():
            raise PolicyError("O projeto precisa ser um diretório existente.")
        self.max_file_bytes = max_file_bytes

    def resolve(self, relative: str, *, write: bool = False, allow_tests: bool = False) -> Path:
        relative = validate_relative(relative)
        target = self.root.joinpath(*relative.split("/"))
        allowed = EDIT_EXT if write else READ_EXT
        if target.suffix.lower() not in allowed:
            raise PolicyError("Extensão não permitida para esta operação.")
        if write and not allow_tests and (any("test" in p.casefold() for p in target.relative_to(self.root).parts)):
            raise PolicyError("Alterações em testes exigem autorização específica.")
        cursor = self.root
        for part in relative.split("/"):
            cursor /= part
            if cursor.is_symlink() or (hasattr(cursor, "is_junction") and cursor.is_junction()):
                raise PolicyError("Link simbólico/junction bloqueado.")
        try:
            target.resolve(strict=False).relative_to(self.root)
        except ValueError as exc:
            raise PolicyError("Tentativa de sair da pasta autorizada.") from exc
        return target

    def read(self, relative: str) -> bytes:
        path = self.resolve(relative)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            info = os.fstat(fd)
            import stat
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise PolicyError("Somente arquivos regulares sem hardlinks são aceitos.")
            if info.st_size > self.max_file_bytes:
                raise PolicyError("Arquivo excede o limite de tamanho.")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                data = stream.read(self.max_file_bytes + 1)
            if len(data) > self.max_file_bytes or b"\x00" in data:
                raise PolicyError("Arquivo grande ou binário bloqueado.")
            text = data.decode("utf-8", errors="strict")
            reject_secrets(text)
            return data
        finally:
            os.close(fd)

    def files(self, max_files: int = 1500):
        count = 0
        for directory, dirs, names in os.walk(self.root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d.casefold() not in IGNORED and not d.startswith(".") and not (Path(directory) / d).is_symlink() and not (hasattr(Path(directory) / d, "is_junction") and (Path(directory) / d).is_junction()))
            for name in sorted(names):
                relative = (Path(directory) / name).relative_to(self.root).as_posix()
                try:
                    self.resolve(relative)
                except PolicyError:
                    continue
                count += 1
                if count > max_files:
                    raise PolicyError("Quantidade de arquivos excede a quota do projeto.")
                yield relative
