#!/usr/bin/env python3
"""Opt-in real visual pipeline probe; pixels are not a human quality verdict."""
import argparse
import json
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from localauthor.errors import PolicyError
from localauthor.foundation.isolation import require_isolated_process
from localauthor.foundation.models import digest, register_model, write_new
from localauthor.foundation.service import FoundationService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--dtype", choices=["float32"], default="float32")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use uma pasta nova para preservar as evidências.")
    args.output.mkdir(parents=True)
    isolation = require_isolated_process()
    report = {"kind": "real-visual-probe-not-qualification", "isolation": isolation,
              "training": False, "promotion": False, "human_quality_review": "pending", "checks": []}
    manifest = args.output / "home/foundation/image-model.json"
    try:
        register_model(args.weights, manifest,
                       model_id="stable-diffusion-v1-5/stable-diffusion-v1-5",
                       revision="451f4fe16113bff5a5d2269ed5ad43b0592e9a14",
                       license="CreativeML-OpenRAIL-M", reviewed_by="Codex technical probe; not human promotion",
                       capability="image", device="cpu", dtype=args.dtype)
        report["manifest_sha256"] = digest(manifest)
        service = FoundationService(args.output / "home")
        profiles = [
            ("simple", "A yellow ceramic vase on a white table, studio photograph", 512, 20, 31),
            ("same-seed", "A yellow ceramic vase on a white table, studio photograph", 512, 20, 31),
            ("detailed", "A blue glass vase with three white flowers on a wooden table, soft natural light, realistic still life, plain beige background", 512, 20, 42),
        ]
        for name, prompt, size, steps, seed in profiles:
            started = time.monotonic()
            result = service.create_image("visual-probe", prompt,
                      options={"width": size, "height": size, "steps": steps, "seed": seed})
            recovered = FoundationService(args.output / "home").image("visual-probe", result["artifact_id"])
            if recovered["sha256"] != result["artifact_sha256"]:
                raise AssertionError("Recovery hash mismatch")
            report["checks"].append({"name": name, "result": result, "retrieved_equal": True,
                                     "seconds": time.monotonic() - started})
            write_new(args.output / (name + ".json"), report["checks"][-1])
        report["same_seed_identical"] = report["checks"][0]["result"]["artifact_sha256"] == report["checks"][1]["result"]["artifact_sha256"]
        if not report["same_seed_identical"]:
            raise AssertionError("Same CPU seed produced different pixels")
        # Cancellation before work and during the actual scheduler callback.
        cancel = threading.Event(); cancel.set()
        try:
            service.create_image("visual-probe", "A green cube", cancel)
        except PolicyError:
            report["cancel_before_generation"] = True
        else:
            raise AssertionError("Pre-cancel ignored")
        engine = service._cache["image"][2]
        # The pipeline is real; an event is set by a separate timer while it runs.
        cancel.clear()
        timer = threading.Timer(0.2, cancel.set); timer.start()
        try:
            engine.generate("A green cube", cancel, options={"width": 256, "height": 256, "steps": 20})
        except PolicyError:
            report["cancel_during_generation"] = True
        else:
            raise AssertionError("Running generation ignored cancellation")
        finally:
            timer.cancel()
        try:
            engine.generate("a vase " * 200)
        except PolicyError:
            report["token_limit_rejected"] = True
        else:
            raise AssertionError("Oversized prompt accepted")
        report["status"] = "passed-functional-probe"
    except Exception as exc:
        report["status"] = "failed"
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)
        raise
    finally:
        write_new(args.output / "report.json", report)
        print(json.dumps({"report": str(args.output / "report.json"), "status": report["status"]}))


if __name__ == "__main__":
    main()
