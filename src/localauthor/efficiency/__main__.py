"""Offline diagnostics: python -m localauthor.efficiency --help."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

from ..errors import PolicyError
from .learning_gate import assess_candidate
from .placement import Footprint, MemoryBudget, plan_placement
from .weight_store import WeightBlock, WeightStore
from .moe_reference import routed_swiglu


def self_check() -> dict:
    """Generate only tiny synthetic weights in a temporary directory."""
    import numpy as np

    rng = np.random.default_rng(31)
    hidden, intermediate, experts = 16, 32, 4
    with tempfile.TemporaryDirectory(prefix="localauthor-efficiency-") as temp:
        root = Path(temp)
        blocks, offset = {}, 0
        with (root / "synthetic.weights").open("wb") as stream:
            for expert in range(experts):
                raw = (rng.standard_normal(3 * hidden * intermediate) * 0.05).astype("<f4").tobytes()
                stream.write(raw)
                blocks[f"e{expert}"] = WeightBlock("synthetic.weights", offset, len(raw), hashlib.sha256(raw).hexdigest())
                offset += len(raw)
        block_bytes = blocks["e0"].length
        trace = [[("e0", 0.7), ("e1", 0.3)]] * 24 + [[("e2", 0.4), ("e3", 0.6)]] * 8
        x = rng.standard_normal(hidden).astype(np.float32)
        results = {}
        outputs = {}
        for label, capacity in (("uncached", 0), ("cached", 2 * block_bytes)):
            store = WeightStore(root, blocks, cache_bytes=capacity, max_block_bytes=block_bytes)
            start = time.perf_counter()
            outputs[label] = [routed_swiglu(x, routes, intermediate=intermediate, read=store.get) for routes in trace]
            results[label] = {**store.stats(), "elapsed_seconds": time.perf_counter() - start}
        equal = all(np.array_equal(a, b) for a, b in zip(outputs["uncached"], outputs["cached"]))
        return {"schema": 1, "classification": "synthetic_cpu_contract",
                "equal_outputs": equal, "tasks": len(trace), "seed": 31,
                "results": results, "nemotron_executed": False,
                "weights_trained": False, "network_required": False,
                "limitations": ["Tiny generated SwiGLU experts, not a language model.",
                    "File reads are logical bytes; OS page cache and physical NVMe I/O are not measured.",
                    "Fixture creation writes temporary data; write_bytes counts only the read-only store.",
                    "No GPU, energy, SSD endurance, training or coding-quality measurement."]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-check", help="Execute um oráculo CPU sintético, sem downloads.")
    plan = sub.add_parser("plan", help="Calcule uma estimativa, não uma homologação.")
    plan.add_argument("--budget", type=Path, required=True)
    plan.add_argument("--footprint", type=Path, required=True)
    plan.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    assess = sub.add_parser("assess", help="Avalie relatórios de um executor confiável; não promove pesos.")
    assess.add_argument("--baseline", type=Path, required=True)
    assess.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "self-check":
            result = self_check()
            code = 0 if result["equal_outputs"] else 1
        else:
            from ..foundation.models import read_object
            if args.command == "plan":
                result = plan_placement(MemoryBudget(**read_object(args.budget)),
                                        Footprint(**read_object(args.footprint)), device=args.device)
                code = 0
            else:
                result = assess_candidate(read_object(args.baseline), read_object(args.candidate))
                code = 0 if result["eligible_for_human_promotion"] else 1
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return code
    except (PolicyError, OSError, TypeError, ValueError, ImportError) as exc:
        print(json.dumps({"error": str(exc), "weights_modified": False}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
