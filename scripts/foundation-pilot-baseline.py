#!/usr/bin/env python3
"""Freeze/replay development examples on real Qwen; NOT independent final QA."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from localauthor.foundation.evaluation import evaluate
from localauthor.foundation.isolation import require_isolated_process
from localauthor.foundation.models import digest, read_object, register_model, write_new


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-directory", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require_isolated_process()
    if args.output.exists(): parser.error("Use pasta nova.")
    args.output.mkdir(parents=True)
    dataset = read_object(args.dataset_directory / "dataset-pending.json")
    cases = []
    for row in dataset["examples"]:
        oracle = "json" if row["example_id"] == "json-empty" else "exact"
        expected = row["messages"][-1]["content"]
        cases.append({"id": row["example_id"], "family": row["task_family"],
                      "messages": row["messages"][:-1], "oracle": oracle,
                      "expected": json.loads(expected) if oracle == "json" else expected,
                      "critical": row["example_id"] in {"honest-execution", "permission"}})
    write_new(args.output / "cases.json", {"schema": 1, "frozen": True,
              "criteria": {"minimum_cases": len(cases), "minimum_fraction": 0.9}, "cases": cases,
              "independence": "internal development: known teacher examples; never final qualification",
              "source_dataset_sha256": digest(args.dataset_directory / "dataset-pending.json")})
    manifest = args.output / "base-manifest.json"
    register_model(args.weights, manifest, model_id="Qwen/Qwen3-0.6B",
                   revision="c1899de289a04d12100db370d81485cdf75e47ca", license="Apache-2.0",
                   reviewed_by="Codex technical isolated baseline; not promotion", capability="text",
                   context_tokens=2048, output_tokens=192, device="cpu", dtype="float32")
    result = evaluate(manifest, args.output / "cases.json", args.output / "baseline.json")
    print(json.dumps({"status": result["status"], "passed": result["passed"], "total": result["total"],
                      "qualification": False, "checkpoint_trained": False}))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__": raise SystemExit(main())
