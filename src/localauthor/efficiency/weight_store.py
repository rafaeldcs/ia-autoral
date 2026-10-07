"""Read-only, integrity-checked block streaming with a byte-bounded CPU cache.

Original LocalAuthor implementation, inspired by hierarchical weight placement.
No tensor decoder, CUDA backend, checkpoint conversion, or implicit quantization.
The operator must own the root and its ancestors; this is not an OS sandbox.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, asdict
import hashlib
import os
from pathlib import Path
import re
import stat
import threading
from types import MappingProxyType

from ..errors import PolicyError
from .placement import nonnegative


def safe_child(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise PolicyError("Caminho de bloco inválido.")
    parts = relative.split("/")
    if any(p in {"", ".", ".."} or ":" in p for p in parts):
        raise PolicyError("Bloco fora do diretório autorizado.")
    root = Path(os.path.abspath(root))
    path = root.joinpath(*parts)
    for part in (path, *path.parents):
        if part.is_symlink() or getattr(part, "is_junction", lambda: False)():
            raise PolicyError("Links não são permitidos no armazenamento de pesos.")
    return path


def signature(info: os.stat_result) -> tuple:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


@dataclass(frozen=True)
class WeightBlock:
    path: str
    offset: int
    length: int
    sha256: str

    def __post_init__(self):
        nonnegative("offset", self.offset)
        nonnegative("length", self.length)
        if not self.length or not isinstance(self.sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", self.sha256):
            raise PolicyError("Comprimento ou hash do bloco inválido.")


@dataclass
class Counters:
    hits: int = 0
    misses: int = 0
    read_bytes: int = 0
    write_bytes: int = 0
    evictions: int = 0
    resident_bytes: int = 0
    peak_resident_bytes: int = 0


class WeightStore:
    """Serialized reads. Cache <= cache_bytes; one read buffer <= max_block_bytes.

    Returned immutable bytes may be retained by callers; their references and
    decoded tensors are NOT included in cache accounting. Reserve them separately.
    A returned block is hash-verified. Every cache hit rechecks file metadata.
    Concurrent hostile writers are out of scope; files must remain operator-owned.
    """
    def __init__(self, root: Path, blocks: dict[str, WeightBlock], *,
                 cache_bytes: int, max_block_bytes: int = 64 * 1024 * 1024,
                 read_budget_bytes: int | None = None):
        self.root = Path(root)
        self.cache_bytes = nonnegative("cache_bytes", cache_bytes)
        self.max_block_bytes = nonnegative("max_block_bytes", max_block_bytes)
        if not self.max_block_bytes or not isinstance(blocks, dict) or not blocks or len(blocks) > 100000:
            raise PolicyError("Inventário vazio/excessivo ou buffer inválido.")
        if read_budget_bytes is not None:
            nonnegative("read_budget_bytes", read_budget_bytes)
        self.read_budget_bytes = read_budget_bytes
        if any(not isinstance(k, str) or not k or not isinstance(v, WeightBlock) for k, v in blocks.items()):
            raise PolicyError("Inventário de blocos inválido.")
        self.blocks = MappingProxyType(dict(blocks))
        self._signatures = {}
        self._cache = OrderedDict()
        self._counters = Counters()
        self._lock = threading.RLock()
        for block in self.blocks.values():
            path = safe_child(self.root, block.path)
            try:
                info = path.stat()
            except OSError as exc:
                raise PolicyError("Arquivo de pesos indisponível.") from exc
            if not stat.S_ISREG(info.st_mode) or block.offset + block.length > info.st_size:
                raise PolicyError("Bloco fora de um arquivo regular.")
            if block.length > self.max_block_bytes:
                raise PolicyError("Bloco excede o buffer reservado.")
            current = signature(info)
            if block.path in self._signatures and self._signatures[block.path] != current:
                raise PolicyError("Arquivo mudou durante a abertura do inventário.")
            self._signatures[block.path] = current

    def _check_path(self, block: WeightBlock) -> Path:
        path = safe_child(self.root, block.path)
        try:
            current = signature(path.stat())
        except OSError as exc:
            self.clear()
            raise PolicyError("Arquivo de pesos removido.") from exc
        if current != self._signatures[block.path]:
            self.clear()
            raise PolicyError("Pesos mudaram; reabra apenas após revisão do inventário.")
        return path

    def get(self, key: str, cancel=None) -> bytes:
        with self._lock:
            if cancel is not None and cancel.is_set():
                raise PolicyError("Leitura cancelada.")
            if key not in self.blocks:
                raise PolicyError("Bloco não registrado.")
            block = self.blocks[key]
            path = self._check_path(block)
            if key in self._cache:
                self._counters.hits += 1
                self._cache.move_to_end(key)
                return self._cache[key]
            if self.read_budget_bytes is not None and self._counters.read_bytes + block.length > self.read_budget_bytes:
                raise PolicyError("Orçamento de leitura esgotado; nenhum especialista foi substituído.")
            self._counters.misses += 1
            raw = b""
            try:
                with path.open("rb", buffering=0) as stream:
                    if signature(os.fstat(stream.fileno())) != self._signatures[block.path]:
                        raise PolicyError("Pesos mudaram antes da leitura.")
                    stream.seek(block.offset)
                    raw = stream.read(block.length)
                    self._counters.read_bytes += len(raw)
                    if signature(os.fstat(stream.fileno())) != self._signatures[block.path]:
                        raise PolicyError("Pesos mudaram durante a leitura.")
            except OSError as exc:
                raise PolicyError("Falha de leitura dos pesos locais.") from exc
            self._check_path(block)
            if cancel is not None and cancel.is_set():
                raise PolicyError("Leitura cancelada.")
            if len(raw) != block.length or hashlib.sha256(raw).hexdigest() != block.sha256:
                self.clear()
                raise PolicyError("Integridade do bloco divergente.")
            if len(raw) <= self.cache_bytes:
                while self._cache and self._counters.resident_bytes + len(raw) > self.cache_bytes:
                    _, old = self._cache.popitem(last=False)
                    self._counters.resident_bytes -= len(old)
                    self._counters.evictions += 1
                self._cache[key] = raw
                self._counters.resident_bytes += len(raw)
                self._counters.peak_resident_bytes = max(self._counters.peak_resident_bytes, self._counters.resident_bytes)
            return raw

    def prefetch(self, keys: list[str], *, byte_budget: int, cancel=None) -> int:
        """Explicit synchronous warming, not speculative model routing.

        Do not displace cached demand data to speculate. Refuse oversize blocks.
        A real asynchronous prefetcher needs separate bandwidth/cancellation tests.
        """
        nonnegative("byte_budget", byte_budget)
        with self._lock:
            for key in keys:
                if key not in self.blocks:
                    raise PolicyError("Prefetch contém bloco não registrado.")
            loaded = 0
            for key in dict.fromkeys(keys):
                if cancel is not None and cancel.is_set():
                    raise PolicyError("Prefetch cancelado.")
                block = self.blocks[key]
                if key in self._cache:
                    self._check_path(block)
                    continue
                if loaded + block.length > byte_budget or self._counters.resident_bytes + block.length > self.cache_bytes:
                    continue
                if self.read_budget_bytes is not None and self._counters.read_bytes + block.length > self.read_budget_bytes:
                    continue
                self.get(key, cancel)
                loaded += block.length
            return loaded

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._counters.resident_bytes = 0

    def stats(self) -> dict:
        with self._lock:
            return {**asdict(self._counters), "cache_capacity_bytes": self.cache_bytes,
                    "max_read_buffer_bytes": self.max_block_bytes,
                    "physical_disk_io_measured": False, "gpu_implemented": False}
