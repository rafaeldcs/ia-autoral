from __future__ import annotations
import ctypes
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from .util import utcnow


def diagnose(home: Path) -> dict:
    disk = shutil.disk_usage(home)
    memory = None
    if os.name == "nt":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total_phys", ctypes.c_ulonglong), ("avail_phys", ctypes.c_ulonglong), ("total_page", ctypes.c_ulonglong), ("avail_page", ctypes.c_ulonglong), ("total_virtual", ctypes.c_ulonglong), ("avail_virtual", ctypes.c_ulonglong), ("avail_extended", ctypes.c_ulonglong)]
        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            memory = {"total_bytes": status.total_phys, "available_bytes": status.avail_phys}
    elif Path("/proc/meminfo").exists():
        values = {line.split(":")[0]: int(line.split()[1])*1024 for line in Path("/proc/meminfo").read_text().splitlines() if len(line.split()) >= 2 and line.split()[1].isdigit()}
        memory = {"total_bytes": values.get("MemTotal"), "available_bytes": values.get("MemAvailable")}
    gpu = {"available": False, "details": None}
    nvidia = shutil.which("nvidia-smi")
    if nvidia:
        try:
            result = subprocess.run([nvidia, "--query-gpu=name,memory.total,memory.free,temperature.gpu,driver_version", "--format=csv,noheader"], capture_output=True, text=True, timeout=5, check=False)
            gpu = {"available": result.returncode == 0, "details": result.stdout.strip()[:2000]}
        except (OSError, subprocess.TimeoutExpired):
            pass
    return {"at": utcnow(), "system": platform.platform(), "processor": platform.processor(), "logical_cpus": os.cpu_count(), "python": sys.version.split()[0], "memory": memory, "disk_total_bytes": disk.total, "disk_free_bytes": disk.free, "gpu": gpu, "docker_installed": shutil.which("docker") is not None, "dotnet_installed": shutil.which("dotnet") is not None, "trained_programming_model": False, "gpu_backend_implemented": False}
