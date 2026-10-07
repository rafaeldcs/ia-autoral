#!/usr/bin/env python3
"""Actual numerical trainer test on an ORIGINAL random tiny Qwen3 fixture.

Not training/homologation of the acquired Qwen checkpoint, not a dataset review.
The local licensed Qwen tokenizer is reused to exercise the exact chat prefix.
"""
import argparse
import json
import importlib.metadata
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from localauthor.foundation.dataset import canonical_hash
from localauthor.foundation.isolation import require_isolated_process
from localauthor.foundation.models import digest, register_model, write_new
from localauthor.foundation.models import read_object
from localauthor.errors import PolicyError
from localauthor.foundation.training import train
from localauthor.foundation.export import export_candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--code-revision", required=True)
    args = parser.parse_args()
    require_isolated_process()
    if args.output.exists(): parser.error("Use pasta nova.")
    args.output.mkdir(parents=True)
    import torch
    from transformers import AutoTokenizer, Qwen3Config, Qwen3ForCausalLM
    from safetensors.torch import load_file
    torch.manual_seed(17)
    tokenizer = AutoTokenizer.from_pretrained(str(args.tokenizer), local_files_only=True)
    base = args.output / "fixture-base"
    model = Qwen3ForCausalLM(Qwen3Config(vocab_size=len(tokenizer), hidden_size=32, intermediate_size=64,
                    num_hidden_layers=1, num_attention_heads=2, num_key_value_heads=2, head_dim=16,
                    max_position_embeddings=256, eos_token_id=tokenizer.eos_token_id,
                    pad_token_id=tokenizer.pad_token_id, tie_word_embeddings=True))
    model.save_pretrained(str(base), safe_serialization=True)
    tokenizer.save_pretrained(str(base))
    register_model(base, args.output / "base-manifest.json", model_id="LocalAuthor/original-random-numerical-fixture",
                   revision="fixture-1", license="original-test-fixture; tokenizer Apache-2.0 Qwen",
                   reviewed_by="test-author: numerical fixture, no human model promotion", capability="text")
    approval = dict(accepted=True, verified=True, rights_reviewed=True, training_allowed=True,
                    reviewer="test-author-owned-fixture-not-production-curation", receipt_sha256="b" * 64)
    rows = []
    for index, (prompt, target, split) in enumerate([
        ("Responda somente com uma lista JSON vazia.", "[]", "train"),
        ("Confirme em português que esta fixture não demonstra competência de programação.", "É uma fixture numérica.", "validation")]):
        messages = [{"role": "user", "content": prompt}, {"role": "assistant", "content": target}]
        rows.append(dict(example_id=f"fixture-{index}", task_family=f"family-{index}", project_group=f"project-{index}",
                         leakage_group=f"origin-{index}", modality="text", split=split, source_ids=["original-fixture"],
                         messages=messages, approval=approval, truncated=False,
                         context_hash=canonical_hash(messages[:-1]), target_hash=canonical_hash(messages[-1])))
    source = args.output / "source.jsonl"
    source.write_text("\n".join(json.dumps(r["messages"], ensure_ascii=False, sort_keys=True) for r in rows), encoding="utf-8")
    receipt = args.output / "fixture-receipt.json"
    write_new(receipt, {**approval, "schema": 1, "scope": "original-numerical-test-only",
              "bindings": [{"source_id": "original-fixture", "sha256": digest(source)},
                  *[{"example_id": r["example_id"], "context_hash": r["context_hash"], "target_hash": r["target_hash"]} for r in rows]]})
    approval.update(receipt_file="fixture-receipt.json", receipt_sha256=digest(receipt))
    dataset = args.output / "dataset.json"
    write_new(dataset, dict(schema=1, purpose="foundation-development", examples=rows, reserved_target_hashes=[],
              sources={"original-fixture": {"file": "source.jsonl", "sha256": digest(source),
                       "license": "original-numerical-test-fixture", "revoked": False, "approval": approval}}))
    experiment = args.output / "experiment.json"
    write_new(experiment, dict(schema=1, experiment_id="numerical-fixture", code_revision=args.code_revision,
              code_dirty=True, code_inventory={p.relative_to(ROOT).as_posix(): digest(p) for p in
                      [*(ROOT / "src/localauthor/foundation").glob("*.py"),
                       *[ROOT / "src/localauthor" / name for name in ("safety.py", "errors.py", "util.py")]]},
              runtime_versions={p: importlib.metadata.version(p) for p in ("torch", "transformers", "peft", "safetensors")},
              base_manifest_sha256=digest(args.output / "base-manifest.json"), dataset_sha256=digest(dataset),
              tokenizer_hashes={"tokenizer.json": digest(base / "tokenizer.json")}, seed=31,
              limits={"steps": 3, "seconds": 180, "output_bytes": 10000000},
              configuration={"architecture": "qwen3", "sequence_tokens": 128, "learning_rate": 0.001,
                             "rank": 2, "alpha": 4, "target_modules": ["q_proj", "v_proj"], "clip_norm": 1},
              hypothesis="Numerical update/reload/resume, NOT learned competence",
              criteria={"finite_gradients": True, "base_unchanged": True, "resume_tensors_equal": True}))
    class CancelAfterOneStep(threading.Event):
        calls = 0
        def is_set(self):
            self.calls += 1
            return self.calls > 1
    cancelled = train(experiment, args.output / "base-manifest.json", dataset, args.output / "cancelled", cancel=CancelAfterOneStep())
    assert cancelled["status"] == "cancelled" and cancelled["step"] == 1
    resumed = train(experiment, args.output / "base-manifest.json", dataset, args.output / "resumed", resume=args.output / "cancelled")
    uninterrupted = train(experiment, args.output / "base-manifest.json", dataset, args.output / "uninterrupted")
    a = load_file(str(args.output / "resumed/adapter/adapter_model.safetensors"))
    b = load_file(str(args.output / "uninterrupted/adapter/adapter_model.safetensors"))
    equal = set(a) == set(b) and all(torch.equal(a[key], b[key]) for key in a)
    assert equal, "Retomada difere da execução contínua."
    divergent = args.output / "divergent-experiment.json"
    write_new(divergent, {**read_object(experiment), "hypothesis": "Different experiment; must not resume"})
    try:
        train(divergent, args.output / "base-manifest.json", dataset,
              args.output / "divergent-rejected", resume=args.output / "cancelled")
    except PolicyError as exc:
        assert "Retomada diverge" in str(exc)
    else: raise AssertionError("Divergent resume was accepted")
    assert read_object(args.output / "divergent-rejected/failure.json")["status"] == "failed"
    exported = export_candidate(experiment, args.output / "base-manifest.json", dataset,
                args.output / "uninterrupted", args.output / "exported",
                model_id="LocalAuthor/numerical-fixture-derived", reviewed_by="test-author; no promotion")
    try:
        export_candidate(experiment, args.output / "base-manifest.json", dataset,
                args.output / "uninterrupted", args.output / "quota-rejected",
                model_id="LocalAuthor/quota-negative-fixture", reviewed_by="numerical test author", output_bytes=1)
    except PolicyError as exc:
        assert "orçamento" in str(exc)
    else: raise AssertionError("Oversized export was accepted")
    assert not (args.output / "quota-rejected/model-manifest.json").exists()
    assert not (args.output / "quota-rejected/weights").exists()
    # Actual non-finite forward rejection, using an independent ORIGINAL fixture.
    nan_base = args.output / "nan-base"
    broken = Qwen3ForCausalLM(model.config)
    with torch.no_grad(): next(broken.parameters()).fill_(float("nan"))
    broken.save_pretrained(str(nan_base), safe_serialization=True)
    tokenizer.save_pretrained(str(nan_base))
    nan_manifest = args.output / "nan-manifest.json"
    register_model(nan_base, nan_manifest, model_id="LocalAuthor/nan-negative-fixture", revision="fixture-negative",
                   license="original test fixture; tokenizer Apache-2.0 Qwen", reviewed_by="numerical test author", capability="text")
    nan_experiment = args.output / "nan-experiment.json"
    write_new(nan_experiment, {**read_object(experiment), "base_manifest_sha256": digest(nan_manifest)})
    try:
        train(nan_experiment, nan_manifest, dataset, args.output / "nan-rejected")
    except PolicyError as exc:
        assert "NaN/Inf" in str(exc)
    else: raise AssertionError("Non-finite fixture was accepted")
    assert read_object(args.output / "nan-rejected/failure.json")["status"] == "failed"
    write_new(args.output / "numerical-report.json", {"success": True, "kind": "original-random-numerical-fixture",
              "actual_acquired_checkpoint_trained": False, "cancelled": cancelled, "resumed": resumed,
              "uninterrupted": uninterrupted, "resumed_tensors_identical": equal, "exported": exported,
              "actual_nan_fixture_rejected": True, "actual_export_quota_rejected_before_write": True,
              "divergent_resume_rejected_with_receipt": True})
    print(json.dumps({"success": True, "resumed_tensors_identical": equal, "actual_acquired_checkpoint_trained": False}))


if __name__ == "__main__": main()
