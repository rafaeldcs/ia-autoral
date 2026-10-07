"""Local Qwen3 LoRA pilot, bounded and opt-in; separate from the NumPy lab."""
from __future__ import annotations

import importlib.metadata
import json
import math
from pathlib import Path
import signal
import threading
import time

from ..errors import PolicyError
from .dataset import validate_dataset, validate_experiment
from .isolation import require_isolated_process
from .models import ModelSpec, digest, local_path, read_object, write_new
from .runtime import offline_environment


def completion_tokens(tokenizer, row: dict, maximum: int) -> dict:
    """Match the inference prefix exactly; loss only on response and EOS."""
    messages = row["messages"]
    prefix = tokenizer.apply_chat_template(messages[:-1], tokenize=True, return_dict=False,
                add_generation_prompt=True, enable_thinking=False)
    target = tokenizer(messages[-1]["content"], add_special_tokens=False)["input_ids"]
    if not target or tokenizer.eos_token_id is None:
        raise PolicyError("Máscara sem tokens-alvo ou EOS ausente.")
    ids = [*prefix, *target, tokenizer.eos_token_id]
    if len(ids) > maximum:
        raise PolicyError("Exemplo excede contexto; treino não trunca silenciosamente.")
    return {"input_ids": ids, "labels": [-100] * len(prefix) + target + [tokenizer.eos_token_id],
            "prefix_tokens": len(prefix), "target_tokens": len(target) + 1}


def training_configuration(experiment: dict) -> dict:
    config = experiment["configuration"]
    required = {"architecture", "sequence_tokens", "learning_rate", "rank", "alpha", "target_modules", "clip_norm"}
    if not isinstance(config, dict) or set(config) != required or config.get("architecture") != "qwen3":
        raise PolicyError("Este trainer homologa somente Qwen3 e configuração explícita.")
    for key, low, high in (("sequence_tokens", 32, 2048), ("rank", 1, 32), ("alpha", 1, 64)):
        value = config[key]
        if type(value) is not int or not low <= value <= high:
            raise PolicyError("Configuração de treino fora do limite.")
    for key, low, high in (("learning_rate", 0, 0.01), ("clip_norm", 0, 10)):
        value = config[key]
        if type(value) not in (float, int) or not math.isfinite(value) or not low < value <= high:
            raise PolicyError("Parâmetro numérico inválido.")
    if config["target_modules"] != ["q_proj", "v_proj"]:
        raise PolicyError("Homologue outros módulos antes de escolhê-los.")
    return config


def _tensor_hash(tensor, torch):
    import hashlib
    value = tensor.detach().cpu().contiguous().view(torch.uint8).numpy()
    return hashlib.sha256(memoryview(value).cast("B")).hexdigest()


def train(experiment_path: Path, base_manifest: Path, dataset_path: Path, output: Path,
          *, resume: Path | None = None, cancel=None) -> dict:
    state = {}
    try:
        return _train(experiment_path, base_manifest, dataset_path, output, resume=resume, cancel=cancel, state=state)
    except BaseException as exc:
        owned = state.get("output_created")
        if owned and not (owned / "failure.json").exists() and not (owned / "checkpoint.json").exists():
            write_new(owned / "failure.json", {"status": "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
                      "exception_type": type(exc).__name__, "step": None, "promoted": False,
                      "stage": "initialization-or-save; no completed checkpoint"})
        raise


def _train(experiment_path: Path, base_manifest: Path, dataset_path: Path, output: Path,
           *, resume: Path | None, cancel, state: dict) -> dict:
    isolation = require_isolated_process()
    offline_environment()
    experiment = validate_experiment(experiment_path)
    versions = {p: importlib.metadata.version(p) for p in experiment["runtime_versions"]}
    if versions != experiment["runtime_versions"]:
        raise PolicyError("Runtime diverge do experimento congelado; não retomar em ambiente diferente.")
    configuration = training_configuration(experiment)
    validated = validate_dataset(dataset_path)
    if digest(base_manifest) != experiment["base_manifest_sha256"] or validated["sha256"] != experiment["dataset_sha256"]:
        raise PolicyError("Base/dataset divergem do manifesto congelado.")
    spec = ModelSpec.load(base_manifest, "text")
    spec.verify()
    if spec.backend != "transformers" or spec.reviewed_local_code or spec.device != "cpu" or spec.dtype != "float32":
        raise PolicyError("Primeiro perfil de treinamento: CPU/float32 nativo, sem código de checkpoint.")
    for name, expected in experiment["tokenizer_hashes"].items():
        if name not in spec.files or spec.files[name] != expected:
            raise PolicyError("Tokenizador mudou.")
    if read_object(spec.directory / "config.json").get("model_type") != configuration["architecture"]:
        raise PolicyError("Arquitetura do checkpoint incompatível com o trainer.")
    output = local_path(output)
    if output.exists() or output.is_relative_to(spec.directory):
        raise PolicyError("Candidato exige pasta nova, fora da base.")
    output.mkdir(parents=True)
    state["output_created"] = output
    contract = {"schema": 1, "experiment_sha256": digest(experiment_path),
                "base_manifest_sha256": digest(base_manifest), "dataset_sha256": validated["sha256"],
                "configuration": configuration, "seed": experiment["seed"]}
    if resume is not None:
        resume = local_path(resume)
        if read_object(resume / "contract.json") != contract:
            raise PolicyError("Retomada diverge dos dados, base, configuração ou revisão.")
    write_new(output / "contract.json", contract)
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, PeftModel, get_peft_model
    from safetensors.torch import load_file, save_file
    torch.set_num_threads(2)
    torch.manual_seed(experiment["seed"])
    tokenizer = AutoTokenizer.from_pretrained(str(spec.directory), local_files_only=True, trust_remote_code=False)
    encoded = {split: [completion_tokens(tokenizer, row, configuration["sequence_tokens"])
                      for row in validated["dataset"]["examples"] if row["split"] == split]
               for split in ("train", "validation")}
    write_new(output / "mask-audit.json", {split: rows[:3] for split, rows in encoded.items()})
    model = AutoModelForCausalLM.from_pretrained(str(spec.directory), local_files_only=True,
                use_safetensors=True, trust_remote_code=False, dtype=torch.float32).to("cpu")
    targets = [name for name, _ in model.named_modules() if name.rsplit(".", 1)[-1] in configuration["target_modules"]]
    if not targets or any(not any(n.endswith("." + target) for n in targets) for target in configuration["target_modules"]):
        raise PolicyError("Projeções LoRA não encontradas.")
    if resume is None:
        model = get_peft_model(model, LoraConfig(r=configuration["rank"], lora_alpha=configuration["alpha"],
                    target_modules=configuration["target_modules"], lora_dropout=0, bias="none", task_type="CAUSAL_LM"))
        start_step = 0
    else:
        checkpoint = read_object(resume / "checkpoint.json")
        for name, expected in checkpoint["files"].items():
            from .models import child
            if digest(child(resume, name)) != expected:
                raise PolicyError("Checkpoint de retomada corrompido.")
        model = PeftModel.from_pretrained(model, str(resume / "adapter"), local_files_only=True, is_trainable=True)
        start_step = checkpoint["step"]
    model.config.use_cache = False
    params = dict(model.named_parameters())
    trainable = {name: value for name, value in params.items() if value.requires_grad}
    if not trainable or any("lora_" not in name for name in trainable):
        raise PolicyError("Treino modificaria parâmetros fora dos adaptadores homologados.")
    if sum(value.numel() * value.element_size() for value in trainable.values()) * 4 + 100000 > experiment["limits"]["output_bytes"]:
        raise PolicyError("Orçamento de disco não comporta adaptadores/otimizador previstos.")
    before = {name: _tensor_hash(value, torch) for name, value in params.items()}
    optimizer = torch.optim.AdamW(list(trainable.values()), lr=configuration["learning_rate"], weight_decay=0)
    if resume is not None:
        tensors = load_file(str(resume / "optimizer.safetensors"))
        state = read_object(resume / "optimizer.json")
        optimizer.load_state_dict({"param_groups": state["param_groups"], "state": {
            int(index): {name: tensors[key] for name, key in values.items()} for index, values in state["state"].items()}})
        torch.set_rng_state(tensors["rng"])
    cancel = cancel or threading.Event()
    started = time.monotonic()
    previous_handler = signal.signal(signal.SIGTERM, lambda *_: cancel.set())
    metrics, status, step = [], "completed", start_step
    gradients_checked = 0
    def loss(sample):
        batch = {k: torch.tensor([sample[k]], dtype=torch.long) for k in ("input_ids", "labels")}
        return model(**batch).loss
    try:
        model.train()
        while step < experiment["limits"]["steps"]:
            if cancel.is_set(): status = "cancelled"; break
            if time.monotonic() - started >= experiment["limits"]["seconds"]:
                status = "budget_exhausted"; break
            optimizer.zero_grad(set_to_none=True)
            value = loss(encoded["train"][step % len(encoded["train"])])
            if not torch.isfinite(value): raise PolicyError("Loss NaN/Inf; candidato rejeitado.")
            value.backward()
            grads = [p.grad for p in trainable.values() if p.grad is not None]
            if not grads or any(not torch.isfinite(g).all() for g in grads):
                raise PolicyError("Gradientes ausentes ou NaN/Inf.")
            gradients_checked += len(grads)
            torch.nn.utils.clip_grad_norm_(list(trainable.values()), configuration["clip_norm"], error_if_nonfinite=True)
            optimizer.step()
            step += 1
            metrics.append({"step": step, "loss": value.item(), "seconds": time.monotonic() - started})
        model.eval()
        with torch.inference_mode():
            validation_loss = sum(loss(sample).item() for sample in encoded["validation"]) / len(encoded["validation"])
        if not math.isfinite(validation_loss): raise PolicyError("Validação NaN/Inf.")
        after = {name: _tensor_hash(value, torch) for name, value in params.items()}
        changed = [name for name in params if before[name] != after[name]]
        if any(name not in trainable for name in changed):
            raise PolicyError("Pesos congelados da base foram modificados.")
        if status == "completed" and step > start_step and not changed:
            raise PolicyError("Nenhum adaptador foi atualizado.")
        adapter = output / "adapter"
        model.save_pretrained(str(adapter), safe_serialization=True)
        # Trusted local optimizer only; no pickle, torch.load or remote tracker.
        optimizer_data = optimizer.state_dict()
        tensors, state_map = {"rng": torch.get_rng_state()}, {}
        for index, values in optimizer_data["state"].items():
            state_map[str(index)] = {}
            for name, value in values.items():
                if not isinstance(value, torch.Tensor): raise PolicyError("Estado de otimizador não suportado.")
                key = f"optimizer.{index}.{name}"
                tensors[key] = value.detach().cpu().contiguous()
                state_map[str(index)][name] = key
        save_file(tensors, str(output / "optimizer.safetensors"))
        write_new(output / "optimizer.json", {"param_groups": optimizer_data["param_groups"], "state": state_map})
        files = {p.relative_to(output).as_posix(): digest(p) for p in output.rglob("*") if p.is_file()}
        if sum(p.stat().st_size for p in output.rglob("*") if p.is_file()) > experiment["limits"]["output_bytes"]:
            raise PolicyError("Checkpoint excede orçamento de disco.")
        # Reload adapter bytes independently and compare all serialized tensors.
        saved = load_file(str(adapter / "adapter_model.safetensors"))
        from peft import get_peft_model_state_dict
        live = get_peft_model_state_dict(model)
        if set(saved) != set(live) or any(not torch.equal(saved[name], live[name].cpu()) for name in saved):
            raise PolicyError("Recarga do adaptador não corresponde aos tensores treinados.")
        report = {"schema": 1, "status": status, "step": step, "resumed_from_step": start_step,
                  "changed_parameters": changed, "frozen_parameters_unchanged": True,
                  "trainable_parameter_count": sum(p.numel() for p in trainable.values()),
                  "gradients_checked": gradients_checked, "metrics": metrics, "validation_loss": validation_loss,
                  "adapter_tensors_reloaded_equal": True, "files": files, "isolation": isolation,
                  "versions": versions,
                  "effective_configuration": {**configuration, "batch_size": 1, "gradient_accumulation": 1,
                      "precision": "float32", "device": "cpu", "optimizer": "AdamW", "weight_decay": 0,
                      "schedule": "constant", "lora_dropout": 0},
                  "seconds": time.monotonic() - started, "promoted": False,
                  "limitation": "Loss e recarga não demonstram competência; export/inferência/avaliação ainda exigidos."}
        write_new(output / "checkpoint.json", report)
        return report
    except Exception as exc:
        write_new(output / "failure.json", {"status": "failed", "step": step,
                  "exception_type": type(exc).__name__, "promoted": False})
        raise
    finally:
        signal.signal(signal.SIGTERM, previous_handler)
