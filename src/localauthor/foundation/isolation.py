"""Execution canaries for opt-in learning/evaluation; never a host fallback."""
from pathlib import Path
import os

from ..errors import PolicyError


def require_isolated_process() -> dict:
    if os.name != "posix" or os.getuid() == 0:
        raise PolicyError("Aprendizado exige processo Linux isolado sem root; nenhum fallback no host.")
    try:
        status = Path("/proc/self/status").read_text()
        interfaces = sorted(p.name for p in Path("/sys/class/net").iterdir())
        mounts = Path("/proc/mounts").read_text().splitlines()
    except OSError as exc:
        raise PolicyError("Canários de isolamento indisponíveis.") from exc
    fields = dict(line.split(":", 1) for line in status.splitlines() if ":" in line)
    root_readonly = any(line.split()[1] == "/" and "ro" in line.split()[3].split(",") for line in mounts)
    if (interfaces != ["lo"] or fields.get("CapEff", "").strip() != "0000000000000000"
            or fields.get("NoNewPrivs", "").strip() != "1" or fields.get("Seccomp", "").strip() != "2"
            or not root_readonly):
        raise PolicyError("Rede, capabilities, seccomp ou raiz da sandbox não conferem.")
    return {"uid": os.getuid(), "interfaces": interfaces, "capabilities": "none",
            "no_new_privileges": True, "seccomp": True, "readonly_root": True,
            "limitation": "Inspecionar também mounts, limites e imagem no Docker antes de iniciar."}
