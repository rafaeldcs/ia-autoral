#!/usr/bin/env python3
"""Bounded inference-only IPC worker; no arbitrary routes, file access or code tools."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from localauthor.errors import PolicyError
from localauthor.foundation.gguf_lab import GgufLabRuntime
from localauthor.foundation.isolation import require_isolated_process


def validate_request(raw):
    if len(raw) > 128000 or not raw.endswith(b"\n"): raise PolicyError("Pedido IPC fora do orçamento.")
    value = json.loads(raw)
    if (not isinstance(value, dict) or set(value) != {"id", "operation", "messages"}
            or not re.fullmatch(r"[a-f0-9]{32}", str(value.get("id", "")))
            or value.get("operation") not in {"count", "generate"}):
        raise PolicyError("Operação IPC não autorizada.")
    return value


def emit(value):
    raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
    if len(raw) > 1_000_000: raise PolicyError("Conclusão IPC excessiva.")
    sys.stdout.buffer.write(raw + b"\n"); sys.stdout.buffer.flush()


def main():
    require_isolated_process()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--context", type=int, required=True)
    parser.add_argument("--tokens", type=int, required=True)
    parser.add_argument("--reasoning-budget", type=int, default=0)
    parser.add_argument("--gpu", action="store_true")
    args = parser.parse_args()
    runtime = GgufLabRuntime(args.weights, args.sha256, Path("/tmp/gguf-engine.log"), context=args.context,
                             output=args.tokens, gpu=args.gpu, reasoning_budget=args.reasoning_budget)
    try:
        emit({"ready": True, "compute": runtime.compute, "isolation": runtime.isolation})
        for _ in range(10000):
            raw = sys.stdin.buffer.readline(128001)
            if not raw: break
            request = validate_request(raw)
            try:
                result = runtime.count(request["messages"]) if request["operation"] == "count" else runtime.generate(request["messages"])
                emit({"id": request["id"], "result": result})
            except Exception:
                emit({"id": request["id"], "error": "Inference rejected; no fallback."})
                break
    finally: runtime.close()


if __name__ == "__main__": main()
