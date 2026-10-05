#!/usr/bin/env python3
"""Real, opt-in GGUF development replay. No training, repair, activation or execution of output."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from localauthor.foundation.gguf_lab import GgufLabRuntime
from localauthor.foundation.models import digest, read_object, write_new, identifier


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--context", type=int, default=2048)
    parser.add_argument("--tokens", type=int, default=192)
    parser.add_argument("--gpu", action="store_true", help="Require full CUDA0 offload; reject CPU fallback.")
    args = parser.parse_args()
    if args.output.exists(): parser.error("Use pasta nova.")
    cases = read_object(args.cases)
    rows = cases.get("cases")
    if cases.get("schema") != 1 or cases.get("frozen") is not True or not isinstance(rows, list) or not 1 <= len(rows) <= 50:
        parser.error("Casos devem ser congelados e limitados antes de carregar pesos.")
    seen = set()
    for row in rows:
        ident = identifier(row.get("id"))
        if ident in seen or row.get("oracle") not in {"exact", "json", "capture"} or "expected" not in row or type(row.get("critical")) is not bool:
            parser.error("Caso duplicado/inválido.")
        if row["oracle"] == "capture" and row["critical"]:
            parser.error("Captura sem oráculo não pode verificar uma regra crítica.")
        seen.add(ident)
    args.output.mkdir(parents=True)
    started = time.monotonic()
    runtime = None
    results = []
    try:
        runtime = GgufLabRuntime(args.weights, args.sha256, args.output / "engine.log", context=args.context, output=args.tokens, gpu=args.gpu)
        loaded = time.monotonic() - started
        for row in rows:
            before = time.monotonic(); answer = ""; truncated = False; error = None; passed = False
            try:
                answer, truncated = runtime.generate(row["messages"])
                if row["oracle"] != "capture":
                    passed = not truncated and (json.loads(answer) == row["expected"] if row["oracle"] == "json" else answer == row["expected"])
            except Exception as exc: error = type(exc).__name__
            results.append({"id": row["id"], "family": row.get("family"), "critical": row["critical"],
                "oracle": row["oracle"], "captured_not_verified": row["oracle"] == "capture" and not error and not truncated and bool(answer),
                "passed": passed, "output": answer, "possibly_truncated": truncated, "error": error,
                "seconds": time.monotonic() - before})
        report = {"schema": 1, "model_id": args.model_id, "revision": args.revision,
            "weights_sha256": args.sha256, "runtime": "llama.cpp b11429 Q4_K_M", "compute": runtime.compute, "load_seconds": loaded,
            "executor_sources_sha256": {str(p.relative_to(ROOT)): digest(p) for p in
                (Path(__file__), ROOT / "src/localauthor/foundation/gguf_lab.py", ROOT / "src/localauthor/foundation/isolation.py")},
            "real_checkpoint": True, "checkpoint_trained": False, "qualification_suite": False,
            "production_activated": False, "cases_sha256": digest(args.cases), "context_tokens": args.context,
            "output_tokens": args.tokens, "decoding": "temperature0-seed31-thinking-disabled",
            "passed": sum(r["passed"] for r in results), "total": len(rows), "omitted": 0,
            "results": results, "isolation": runtime.isolation,
            "scope": "development examples; literal/json oracles; captures are not passes; no final qualification",
            "independence": cases.get("independence", "not demonstrated"),
            "capture_count": sum(r["captured_not_verified"] for r in results)}
        write_new(args.output / "report.json", report)
        print(json.dumps({k: report[k] for k in ("passed", "total", "qualification_suite", "load_seconds")}))
        return 0 if report["passed"] == report["total"] else 1
    except Exception as exc:
        write_new(args.output / "failure.json", {"error": type(exc).__name__, "detail": str(exc), "seconds": time.monotonic() - started})
        raise
    finally:
        if runtime is not None: runtime.close()


if __name__ == "__main__": raise SystemExit(main())
