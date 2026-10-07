"""Real text checkpoint evaluator; exact structured oracles, no repairs."""
import time
from pathlib import Path

from ..errors import PolicyError
from .isolation import require_isolated_process
from .models import ModelSpec, digest, identifier, read_object, write_new
from .runtime import TextRuntime


def evaluate(model_manifest: Path, cases_path: Path, report_path: Path) -> dict:
    if report_path.exists(): raise PolicyError("Use relatório novo; preservar avaliações anteriores.")
    isolation = require_isolated_process()
    cases = read_object(cases_path)
    criteria = cases.get("criteria")
    rows = cases.get("cases")
    if (cases.get("schema") != 1 or cases.get("frozen") is not True
            or not isinstance(rows, list) or not rows or len(rows) > 200
            or not isinstance(criteria, dict) or set(criteria) != {"minimum_cases", "minimum_fraction"}
            or type(criteria["minimum_cases"]) is not int or criteria["minimum_cases"] < 1
            or type(criteria["minimum_fraction"]) not in (int, float)
            or not 0 < criteria["minimum_fraction"] <= 1):
        raise PolicyError("Congele casos e limiares antes da avaliação.")
    ids = set()
    for row in rows:
        ident = identifier(row.get("id"))
        if ident in ids or row.get("oracle") not in {"exact", "json"} or type(row.get("critical")) is not bool:
            raise PolicyError("Caso duplicado ou oráculo não suportado.")
        ids.add(ident)
        messages = row.get("messages")
        if (not isinstance(messages, list) or not messages or any(not isinstance(m, dict)
                or set(m) != {"role", "content"} or m["role"] not in {"system", "user", "assistant"}
                or not isinstance(m["content"], str) or not m["content"].strip() for m in messages)):
            raise PolicyError("Contexto de avaliação inválido.")
        if "expected" not in row:
            raise PolicyError("Oráculo precisa de expectativa congelada.")
    spec = ModelSpec.load(model_manifest, "text")
    spec.verify()
    if spec.backend != "transformers":
        raise PolicyError("Avaliador Safetensors não executa GGUF. Use o probe GGUF em sandbox; não é qualificação final.")
    engine = TextRuntime(spec)
    results = []
    for row in rows:
        started = time.monotonic()
        output, error, truncated = "", None, False
        try:
            output, truncated = engine.generate(row["messages"])
            if row["oracle"] == "json":
                import json
                passed = json.loads(output) == row["expected"]
            else:
                passed = output == row["expected"]
            passed = bool(passed and not truncated and output.strip())
        except Exception as exc:
            passed, error = False, type(exc).__name__
        results.append({"id": row["id"], "family": row.get("family"), "critical": row["critical"],
                        "passed": passed, "output": output, "error": error,
                        "possibly_truncated": truncated, "seconds": time.monotonic() - started})
    passed = sum(r["passed"] for r in results)
    critical = sum(not r["passed"] and r["critical"] for r in results)
    report = {"status": "passed" if (len(results) >= criteria["minimum_cases"] and passed / len(results) >= criteria["minimum_fraction"] and not critical) else "rejected",
              "candidate_manifest_sha256": digest(model_manifest), "cases_sha256": digest(cases_path),
              "criteria": criteria, "criteria_frozen": True, "critical_failures": critical, "omitted": 0,
              "real_checkpoint": True, "passed": passed, "total": len(results), "results": results,
              "conditions": {"device": spec.device, "dtype": spec.dtype, "context_tokens": spec.context_tokens,
                             "output_tokens": spec.output_tokens, "decoding": "greedy-no-thinking"},
              "qualification_suite": False,
              "isolation": isolation, "scope": "oráculos textuais exact/json; não executa código nem julga imagens",
              "independence": cases.get("independence", "not_demonstrated")}
    write_new(report_path, report)
    return report


def compare(base_manifest: Path, candidate: Path, cases: Path, output: Path) -> dict:
    """Same frozen inputs and generation budgets; no resetting criteria on failure."""
    base, new = ModelSpec.load(base_manifest, "text"), ModelSpec.load(candidate, "text")
    for key in ("device", "dtype", "context_tokens", "output_tokens", "backend", "runtime_profile"):
        if getattr(base, key) != getattr(new, key):
            raise PolicyError("Comparação exige condições iguais de dispositivo, precisão e tokens.")
    if output.exists(): raise PolicyError("Use pasta nova para preservar avaliação anterior.")
    output.mkdir(parents=True)
    baseline = evaluate(base_manifest, cases, output / "base.json")
    result = evaluate(candidate, cases, output / "candidate.json")
    regressions = [a["id"] for a, b in zip(baseline["results"], result["results"], strict=True)
                   if a["passed"] and not b["passed"]]
    report = {**result, "kind": "base-candidate-comparison", "schema": 1,
              "base_manifest_sha256": digest(base_manifest), "baseline_report_sha256": digest(output / "base.json"),
              "candidate_report_sha256": digest(output / "candidate.json"), "baseline_passed": baseline["passed"],
              "regressions": regressions, "same_conditions": True,
              "status": "passed" if result["status"] == "passed" and not regressions else "rejected"}
    write_new(output / "comparison.json", report)
    return report
