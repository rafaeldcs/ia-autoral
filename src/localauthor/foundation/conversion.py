"""Convert approved JSONL using separately curated groups/rights, never infer them."""
import hashlib
import json
from pathlib import Path

from ..errors import PolicyError
from .dataset import canonical_hash, validate_dataset
from .models import digest, identifier, local_path, read_object, write_new


def convert_jsonl(export: Path, curation: Path, output: Path) -> dict:
    export, curation, output = map(local_path, (export, curation, output))
    plan = read_object(curation)
    if plan.get("schema") != 1 or plan.get("export_sha256") != digest(export) or output.exists():
        raise PolicyError("Conversão exige export imutável, curadoria vinculada e destino novo.")
    if output.parent != curation.parent:
        raise PolicyError("Dataset deve manter os caminhos relativos da curadoria aprovada.")
    with export.open("rb") as stream: raw = stream.read(2000001)
    if len(raw) > 2000000: raise PolicyError("Export excessivo.")
    assignments = plan.get("assignments")
    if not isinstance(assignments, dict) or not assignments:
        raise PolicyError("Agrupe/particione e revise cada experiência antes de converter.")
    rows, seen = [], set()
    for line in raw.decode("utf-8").splitlines():
        if not line.strip(): continue
        original = json.loads(line)
        if not isinstance(original, dict): raise PolicyError("Linha JSONL inválida.")
        key = identifier(original.get("id")); scope = identifier(original.get("project_id"))
        if key in seen or key not in assignments: raise PolicyError("ID duplicado ou não revisado.")
        seen.add(key)
        review = assignments[key]
        if not isinstance(review, dict) or review.get("project_id") != scope:
            raise PolicyError("Curadoria de outro projeto.")
        messages, metadata = original.get("messages"), original.get("metadata")
        if (not isinstance(messages, list) or not messages or not isinstance(metadata, dict)
                or original.get("kind") not in {"text", "code"} or original.get("split") not in {"train", "validation"}
                or metadata.get("possibly_truncated") is not False or metadata.get("generation_context") != messages[:-1]):
            raise PolicyError("Export não contém contexto/integridade de desenvolvimento comprovados.")
        expected = hashlib.sha256((messages[-1]["content"] + json.dumps(metadata, ensure_ascii=False)).encode("utf-8")).hexdigest()
        if original.get("output_hash") != expected or review.get("output_hash") != expected:
            raise PolicyError("Resposta/metadata divergem da experiência revisada.")
        refs = review.get("source_ids", [])
        sources = plan.get("sources", {})
        for evidence in metadata.get("evidence", []):
            if not any(s in sources and sources[s].get("original_source_id") == evidence.get("source_id")
                       and sources[s].get("sha256") == evidence.get("sha256") for s in refs):
                raise PolicyError("Fonte transitiva do contexto sem autorização/hash na curadoria.")
        rows.append({"example_id": key, "modality": original["kind"], "split": original["split"],
            "messages": messages, "context_hash": canonical_hash(messages[:-1]), "target_hash": canonical_hash(messages[-1]),
            "truncated": False, **{k: review.get(k) for k in
                ("task_family", "project_group", "leakage_group", "source_ids", "approval")}})
    if seen != set(assignments): raise PolicyError("Curadoria contém experiências omitidas.")
    # Validate before publishing the requested dataset, even on rights/leakage failures.
    candidate = output.parent / (output.name + ".validation.json")
    data = {"schema": 1, "purpose": "foundation-development", "examples": rows,
            "sources": plan.get("sources"), "reserved_target_hashes": plan.get("reserved_target_hashes")}
    write_new(candidate, data)
    try:
        verified = validate_dataset(candidate)
        write_new(output, data)
    finally:
        candidate.unlink(missing_ok=True)
    return {"status": "completed", "dataset_sha256": digest(output), "export_sha256": digest(export),
            "curation_sha256": digest(curation), "split_counts": verified["split_counts"], "approved_by_converter": False}
