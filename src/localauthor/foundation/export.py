"""Merge a verified local LoRA checkpoint into a NEW complete Safetensors base."""
from pathlib import Path
import importlib.metadata
import shutil

from ..errors import PolicyError
from .dataset import validate_dataset, validate_experiment
from .isolation import require_isolated_process
from .models import ModelSpec, child, digest, local_path, read_object, register_model, write_new
from .runtime import offline_environment


def export_candidate(experiment: Path, base_manifest: Path, dataset: Path, checkpoint: Path,
                     output: Path, *, model_id: str, reviewed_by: str,
                     output_bytes: int = 10_000_000_000) -> dict:
    if type(output_bytes) is not int or not 1 <= output_bytes <= 10_000_000_000:
        raise PolicyError("Declare orçamento de exportação entre 1 byte e 10 GB.")
    isolation = require_isolated_process()
    offline_environment()
    config = validate_experiment(experiment)
    if {p: importlib.metadata.version(p) for p in config["runtime_versions"]} != config["runtime_versions"]:
        raise PolicyError("Exportação exige o runtime congelado do treino.")
    validated = validate_dataset(dataset)
    spec = ModelSpec.load(base_manifest, "text"); spec.verify()
    contract = read_object(checkpoint / "contract.json")
    receipt = read_object(checkpoint / "checkpoint.json")
    if (contract.get("experiment_sha256") != digest(experiment)
            or contract.get("dataset_sha256") != validated["sha256"]
            or contract.get("base_manifest_sha256") != digest(base_manifest)
            or config["base_manifest_sha256"] != digest(base_manifest)
            or config["dataset_sha256"] != validated["sha256"]
            or receipt.get("status") != "completed" or not receipt.get("changed_parameters")
            or receipt.get("frozen_parameters_unchanged") is not True
            or receipt.get("adapter_tensors_reloaded_equal") is not True
            or not isinstance(receipt.get("files"), dict)):
        raise PolicyError("Exporte somente treino completo e comprovado da base/dados exatos.")
    if not {"adapter/adapter_config.json", "adapter/adapter_model.safetensors", "contract.json"} <= set(receipt["files"]):
        raise PolicyError("Checkpoint sem arquivos essenciais.")
    for name, expected in receipt["files"].items():
        if digest(child(checkpoint, name)) != expected:
            raise PolicyError("Checkpoint foi alterado após o treino.")
    output = local_path(output)
    if output.exists() or output.is_relative_to(spec.directory) or output.is_relative_to(local_path(checkpoint)):
        raise PolicyError("Exportação exige pasta nova fora da base e checkpoint.")
    if spec.device != "cpu" or spec.dtype != "float32" or spec.reviewed_local_code:
        raise PolicyError("Exportação homologada somente em CPU/f32 nativo.")
    output.mkdir(parents=True)
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    torch.set_num_threads(2)
    base = AutoModelForCausalLM.from_pretrained(str(spec.directory), local_files_only=True,
                       trust_remote_code=False, use_safetensors=True, dtype=torch.float32)
    model = PeftModel.from_pretrained(base, str(checkpoint / "adapter"), local_files_only=True)
    tokenizer = AutoTokenizer.from_pretrained(str(spec.directory), local_files_only=True, trust_remote_code=False)
    projected_bytes = sum(p.numel() * p.element_size() for p in base.parameters())
    projected_bytes += sum(p.stat().st_size for p in spec.directory.iterdir()
                           if p.is_file() and p.suffix != ".safetensors") + 1_000_000
    if projected_bytes > output_bytes or shutil.disk_usage(output).free < projected_bytes:
        raise PolicyError("Exportação completa não cabe no orçamento/espaço disponível; nenhum peso foi escrito.")
    probe = tokenizer.apply_chat_template(validated["dataset"]["examples"][0]["messages"][:-1],
               tokenize=True, return_dict=False, enable_thinking=False, add_generation_prompt=True)
    model.eval()
    with torch.inference_mode():
        before = model(input_ids=torch.tensor([probe])).logits[:, -1, :].clone()
        model = model.merge_and_unload(safe_merge=True)
        after = model(input_ids=torch.tensor([probe])).logits[:, -1, :]
    if not torch.allclose(before, after, atol=1e-4, rtol=1e-4):
        raise PolicyError("Fusão alterou logits além da tolerância congelada.")
    weights = output / "weights"
    model.save_pretrained(str(weights), safe_serialization=True)
    tokenizer.save_pretrained(str(weights))
    for name in ("LICENSE", "LICENSE.txt", "NOTICE"):
        original = spec.directory / name
        if original.is_file(): shutil.copyfile(original, weights / name)
    derivation = {"base_model": spec.model_id, "base_revision": spec.revision, "base_license": spec.license,
                  "base_manifest_sha256": digest(base_manifest), "dataset_sha256": validated["sha256"],
                  "experiment_sha256": digest(experiment), "checkpoint_sha256": digest(checkpoint / "checkpoint.json"),
                  "technique": "Qwen3 CPU LoRA q_proj/v_proj merged", "created_from_scratch": False}
    write_new(weights / "DERIVATION.json", derivation)
    written_bytes = sum(p.stat().st_size for p in weights.rglob("*") if p.is_file())
    if written_bytes > output_bytes:
        raise PolicyError("Exportação excedeu orçamento; candidato incompleto não é registrado nem promovido.")
    # A fresh native model load exercises the exported weights, not the live PEFT wrapper.
    del model, base
    reloaded = AutoModelForCausalLM.from_pretrained(str(weights), local_files_only=True,
                   trust_remote_code=False, use_safetensors=True, dtype=torch.float32).eval()
    with torch.inference_mode():
        recovered = reloaded(input_ids=torch.tensor([probe])).logits[:, -1, :]
    if not torch.equal(after, recovered):
        raise PolicyError("Recarga da base fundida diverge dos logits salvos.")
    manifest = output / "model-manifest.json"
    register_model(weights, manifest, model_id=model_id, revision=digest(checkpoint / "checkpoint.json"),
                   license=spec.license, reviewed_by=reviewed_by, capability="text", device=spec.device,
                   dtype=spec.dtype, context_tokens=spec.context_tokens, output_tokens=spec.output_tokens,
                   derivation=derivation)
    report = {"status": "exported-not-promoted", "candidate_manifest_sha256": digest(manifest),
              "merged_logits_close": True, "reloaded_logits_identical": True, "isolation": isolation,
              "derivation": derivation, "promotion": False,
              "output_bytes_limit": output_bytes, "weights_bytes": written_bytes}
    write_new(output / "export-report.json", report)
    return report
