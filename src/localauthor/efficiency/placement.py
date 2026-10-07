"""Conservative placement arithmetic; a plan is NOT proof of runtime support."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from ..errors import PolicyError


def nonnegative(name: str, value: int) -> int:
    if type(value) is not int or value < 0:
        raise PolicyError(f"{name} deve ser inteiro não negativo.")
    return value


@dataclass(frozen=True)
class MemoryBudget:
    ram_bytes: int
    vram_bytes: int
    ram_reserve_bytes: int
    vram_reserve_bytes: int
    workspace_bytes: int

    def __post_init__(self):
        for name, value in asdict(self).items():
            nonnegative(name, value)
        if self.ram_reserve_bytes > self.ram_bytes or self.vram_reserve_bytes > self.vram_bytes:
            raise PolicyError("Reserva superior à memória disponível informada.")


@dataclass(frozen=True)
class Footprint:
    resident_bytes: int
    expert_bytes: int
    state_bytes: int
    largest_expert_bytes: int

    def __post_init__(self):
        for name, value in asdict(self).items():
            nonnegative(name, value)
        if self.largest_expert_bytes > self.expert_bytes:
            raise PolicyError("Maior bloco superior ao total de especialistas.")
        if self.expert_bytes and not self.largest_expert_bytes:
            raise PolicyError("Informe o maior bloco para reservar o staging.")


def plan_placement(budget: MemoryBudget, footprint: Footprint, *, device: str = "cpu") -> dict:
    """Reserve all non-streamable state and one staging block before caching.

    Estimates must come from the actual representation, NOT active parameter
    count. VRAM below is planning only: WeightStore implements CPU RAM + files.
    Kernel support, allocator overhead and OS paging require separate validation.
    """
    if device not in {"cpu", "cuda"}:
        raise PolicyError("Dispositivo deve ser cpu ou cuda.")
    ram = budget.ram_bytes - budget.ram_reserve_bytes
    vram = budget.vram_bytes - budget.vram_reserve_bytes
    fixed = footprint.resident_bytes + footprint.state_bytes + budget.workspace_bytes
    staging = footprint.largest_expert_bytes
    if device == "cpu":
        if fixed + staging > ram:
            raise PolicyError("RAM insuficiente para base, estado, workspace e staging; sem fallback.")
        ram -= fixed + staging
        gpu_cache = 0
    else:
        if fixed + staging > vram or staging > ram:
            raise PolicyError("Memória insuficiente para estado residente e staging CPU/GPU.")
        vram -= fixed + staging
        ram -= staging
        gpu_cache = min(footprint.expert_bytes, vram)
    ram_cache = min(footprint.expert_bytes - gpu_cache, ram)
    return {
        "schema": 1, "device": device,
        "fixed_bytes": fixed, "staging_bytes_per_device": staging,
        "gpu_expert_cache_bytes": gpu_cache, "ram_expert_cache_bytes": ram_cache,
        "uncached_expert_bytes": footprint.expert_bytes - gpu_cache - ram_cache,
        "weights_on_disk_bytes": footprint.resident_bytes + footprint.expert_bytes,
        "runtime_compatible": False, "estimated_only": True,
        "router_modified": False, "precision_modified": False,
    }
