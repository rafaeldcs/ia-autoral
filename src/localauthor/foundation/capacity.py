"""Offline resource preflight. Capacity is neither runtime qualification nor approval."""
from pathlib import Path
import re
from urllib.parse import urlsplit

from ..errors import PolicyError
from .models import digest, read_object, write_new


def integer(value, name, *, positive=False):
    if type(value) is not int or value < (1 if positive else 0):
        raise PolicyError("Informe bytes/contagens inteiros válidos: " + name)
    return value


def assess(requirements: dict, hardware: dict) -> dict:
    """Never add RAM to VRAM or use active MoE parameters as weight footprint."""
    if type(requirements.get("schema")) is not int or requirements["schema"] != 1:
        raise PolicyError("Schema de requisitos inválido.")
    if type(hardware.get("schema")) is not int or hardware["schema"] != 1:
        raise PolicyError("Schema de hardware inválido.")
    model = requirements.get("model_id")
    revision = requirements.get("revision")
    if (not isinstance(model, str) or not model or len(model) > 200
            or not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision)):
        raise PolicyError("Identidade e revisão imutável do modelo são obrigatórias.")
    sources = requirements.get("sources")
    if (not isinstance(sources, list) or not 1 <= len(sources) <= 20
            or any(not isinstance(s, str) or not s.startswith("https://") or len(s) > 2000 for s in sources)):
        raise PolicyError("Registre as fontes técnicas dos requisitos.")
    for source in sources:
        try:
            url = urlsplit(source)
            if not url.hostname or url.username is not None or url.password is not None or any(c.isspace() for c in source):
                raise ValueError("URL inválida")
        except ValueError as exc:
            raise PolicyError("URL técnica inválida ou contendo credenciais.") from exc
    weights = integer(requirements.get("weights_bytes"), "weights_bytes", positive=True)
    copies = integer(requirements.get("additional_weight_copies"), "additional_weight_copies")
    overhead = integer(requirements.get("additional_disk_overhead_bytes"), "additional_disk_overhead_bytes")
    ram = integer(requirements.get("required_ram_bytes"), "required_ram_bytes")
    available_ram = integer(hardware.get("available_ram_bytes"), "available_ram_bytes")
    total_ram = integer(hardware.get("total_ram_bytes"), "total_ram_bytes", positive=True)
    disk = integer(hardware.get("free_disk_bytes"), "free_disk_bytes")
    if available_ram > total_ram:
        raise PolicyError("RAM disponível não pode exceder RAM total.")
    gpus = hardware.get("gpus")
    profiles = requirements.get("gpu_profiles")
    if (not isinstance(gpus, list) or len(gpus) > 64
            or not isinstance(profiles, list) or len(profiles) > 20):
        raise PolicyError("Inventário/perfis GPU inválidos.")
    for gpu in gpus:
        if not isinstance(gpu, dict) or not isinstance(gpu.get("family"), str) or not gpu["family"]:
            raise PolicyError("Família de GPU obrigatória.")
        integer(gpu.get("memory_bytes"), "GPU memory_bytes", positive=True)
    matched = []
    for profile in profiles:
        if not isinstance(profile, dict) or not isinstance(profile.get("family"), str) or not profile["family"]:
            raise PolicyError("Família do perfil GPU obrigatória.")
        count = integer(profile.get("count"), "GPU count", positive=True)
        memory = integer(profile.get("minimum_memory_bytes_each"), "GPU minimum_memory_bytes_each", positive=True)
        if sum(g["family"] == profile["family"] and g["memory_bytes"] >= memory for g in gpus) >= count:
            matched.append(profile)
    disk_needed = weights * copies + overhead
    blockers = []
    if disk < disk_needed:
        blockers.append("insufficient_disk")
    if available_ram < ram:
        blockers.append("insufficient_available_ram")
    if profiles and not matched:
        blockers.append("no_matching_gpu_profile")
    return {"schema": 1, "status": "blocked" if blockers else "capacity-only",
            "model_id": model, "revision": revision, "sources": sources,
            "weights_bytes": weights, "additional_disk_bytes_required": disk_needed,
            "free_disk_bytes": disk, "required_ram_bytes": ram,
            "available_ram_bytes": available_ram, "gpu_profile_matches": matched,
            "blockers": blockers, "acquisition_authorized": False, "qualification_suite": False,
            "limitations": ["Requisitos declarados pelo operador; verificar fontes e validade da medição.",
                            "Não comprova licença, suporte de arquitetura, driver, velocidade ou qualidade.",
                            "RAM e VRAM não são somadas; pesos MoE incluem todos os especialistas.",
                            "Não baixa, instala, treina nem promove modelos."]}


def preflight(requirements_path: Path, hardware_path: Path, report: Path) -> dict:
    requirements = read_object(requirements_path)
    hardware = read_object(hardware_path)
    result = assess(requirements, hardware)
    result["requirements_sha256"] = digest(requirements_path)
    result["hardware_sha256"] = digest(hardware_path)
    write_new(report, result)
    return result
