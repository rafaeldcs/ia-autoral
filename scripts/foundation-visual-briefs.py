#!/usr/bin/env python3
"""Capture local visual briefs for review; no automated human-quality verdict."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from localauthor.errors import PolicyError
from localauthor.foundation.isolation import require_isolated_process
from localauthor.foundation.models import digest, identifier, read_object, register_model, write_new
from localauthor.foundation.service import FoundationService


def validate_briefs(document):
    if (not isinstance(document, dict) or document.get("schema") != 1 or document.get("frozen") is not True
            or not isinstance(document.get("briefs"), list) or not 1 <= len(document["briefs"]) <= 20):
        raise PolicyError("Use um lote congelado de 1 a 20 briefings.")
    seen = set()
    for row in document["briefs"]:
        if not isinstance(row, dict) or set(row) != {"id", "prompt", "seed", "purpose"}:
            raise PolicyError("Briefing sem contrato completo.")
        ident = identifier(row["id"])
        if ident in seen or any(not isinstance(row[k], str) or not row[k].strip() or len(row[k]) > 2000 for k in ("prompt", "purpose")):
            raise PolicyError("Briefing duplicado, vazio ou excessivo.")
        if type(row["seed"]) is not int or not 0 <= row["seed"] <= 2147483647:
            raise PolicyError("Seed inválida.")
        seen.add(ident)
    return document["briefs"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--briefs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    isolation = require_isolated_process()
    rows = validate_briefs(read_object(args.briefs))
    if args.output.exists(): parser.error("Preserve as evidências: use uma pasta nova.")
    args.output.mkdir(parents=True)
    report = {"schema": 1, "briefs_sha256": digest(args.briefs), "isolation": isolation,
              "training": False, "production_activated": False, "quality_qualified": False,
              "human_quality_review": "pending", "results": [], "device": "cuda", "dtype": "float16"}
    service = FoundationService(args.output / "home")
    try:
        import torch
        if not torch.cuda.is_available() or (torch.arange(4, device="cuda") * 2).sum().item() != 12:
            raise PolicyError("Computação CUDA não comprovada; nenhum fallback CPU.")
        manifest = args.output / "home/foundation/image-model.json"
        register_model(args.weights, manifest, model_id="stable-diffusion-v1-5/stable-diffusion-v1-5",
            revision="451f4fe16113bff5a5d2269ed5ad43b0592e9a14", license="CreativeML-OpenRAIL-M",
            reviewed_by="Technical capture only; human quality pending", capability="image", device="cuda", dtype="float16")
        report["manifest_sha256"] = digest(manifest)
        report["runtime"] = {"torch": torch.__version__, "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(0)}
        for row in rows:
            started = time.monotonic()
            item = {"id": row["id"], "purpose": row["purpose"], "seed": row["seed"], "human_scores": None}
            try:
                result = service.create_image("marketing-briefs", row["prompt"], options={"width": 512, "height": 512, "steps": 20, "seed": row["seed"]})
                engine = service._cache["image"][2]
                if engine.pipeline.unet.device.type != "cuda" or engine.pipeline.safety_checker is None:
                    raise PolicyError("Pipeline CUDA/verificador não comprovado.")
                recovered = service.image("marketing-briefs", result["artifact_id"])
                if recovered["sha256"] != result["artifact_sha256"]: raise PolicyError("Hash de recuperação divergente.")
                item.update(result=result, retrieved_equal=True, delivered=True)
            except Exception as exc:
                item.update(delivered=False, error_type=type(exc).__name__, error=str(exc))
            item["seconds"] = time.monotonic() - started
            report["results"].append(item)
            write_new(args.output / (row["id"] + ".json"), item)
        report["gpu_peak_allocated_bytes"] = torch.cuda.max_memory_allocated()
        report["delivered"] = sum(r["delivered"] for r in report["results"])
        report["total"] = len(rows)
    except Exception as exc:
        report.update(error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        for kind in tuple(service._cache): service._evict(kind)
        write_new(args.output / "report.json", report)
    print(json.dumps({"delivered": report["delivered"], "total": report["total"], "quality_qualified": False}))
    return 0 if report["delivered"] == report["total"] else 1


if __name__ == "__main__": raise SystemExit(main())
