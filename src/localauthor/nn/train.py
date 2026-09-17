from __future__ import annotations
import threading
import time
from pathlib import Path
import numpy as np
from .transformer import Transformer, ModelConfig
from .optimizer import AdamW
from .tokenizer import ByteTokenizer, BPETokenizer
from .tensor import no_grad
from .checkpoint import save_checkpoint, load_checkpoint
from ..dataset import validate_dataset
from ..util import write_json, utcnow


def sample_batch(tokens: np.ndarray, context: int, batch_size: int, rng: np.random.Generator):
    if len(tokens) <= context:
        raise ValueError("Partição muito curta para o contexto configurado.")
    starts = rng.integers(0, len(tokens)-context, size=batch_size)
    inputs = np.stack([tokens[s:s+context] for s in starts])
    targets = np.stack([tokens[s+1:s+context+1] for s in starts])
    return inputs, targets


def train(manifest_path: Path, output_dir: Path, config: ModelConfig | None = None, *, steps: int = 100, batch_size: int = 2, learning_rate: float = 0.003, tokenizer_kind: str = "byte", resume: Path | None = None, cancel: threading.Event | None = None, callback=None) -> dict:
    if type(steps) is not int or not 1 <= steps <= 1_000_000 or not 1 <= batch_size <= 8:
        raise ValueError("Steps/batch fora dos limites.")
    dataset = validate_dataset(manifest_path)
    if resume:
        model, optimizer, tokenizer, rng, meta = load_checkpoint(resume)
        if meta["provenance"].get("manifest_hash") != dataset["manifest_hash"]:
            raise ValueError("Retomada requer o mesmo corpus; crie outro experimento para mudar dados.")
        if config is not None and model.config != config:
            raise ValueError("Configuração fornecida diverge do checkpoint.")
    else:
        if tokenizer_kind not in {"byte", "bpe"}:
            raise ValueError("Tokenizador deve ser byte ou bpe.")
        train_texts = [r["text"] for r in dataset["splits"]["train"]]
        tokenizer = ByteTokenizer() if tokenizer_kind == "byte" else BPETokenizer.train(train_texts)
        config = config or ModelConfig()
        config.vocab_size = tokenizer.vocab_size
        model = Transformer(config)
        optimizer = AdamW(model.parameters, lr=learning_rate)
        rng = np.random.default_rng(config.seed+1)
    tokens = {s: np.array([token for r in dataset["splits"][s] for token in tokenizer.encode(r["text"], special=True)], dtype=np.int64) for s in ("train", "validation")}
    output_dir.mkdir(parents=True, exist_ok=True)
    eval_rng = np.random.default_rng(1701)
    eval_x, eval_y = sample_batch(tokens["validation"], model.config.context_length, batch_size, eval_rng)
    with no_grad():
        initial_validation = float(model.loss(eval_x, eval_y).data)
    history, start, start_step = [], time.monotonic(), optimizer.step_count
    cancelled = False
    for local_step in range(steps):
        if cancel and cancel.is_set():
            cancelled = True
            break
        x, y = sample_batch(tokens["train"], model.config.context_length, batch_size, rng)
        loss = model.loss(x, y)
        if not np.isfinite(loss.data): raise FloatingPointError("Perda não finita.")
        loss.backward()
        norm = optimizer.step()
        if local_step == 0 or (local_step+1) % 10 == 0 or local_step == steps-1:
            with no_grad():
                val = float(model.loss(eval_x, eval_y).data)
            metric = {"step": optimizer.step_count, "train_loss": float(loss.data), "validation_loss": val, "gradient_norm": norm}
            history.append(metric)
            if callback: callback(metric)
        if (local_step+1) % 50 == 0:
            save_checkpoint(output_dir/"latest.npz", model, optimizer, tokenizer, rng, {"manifest_hash": dataset["manifest_hash"], "dataset_id": dataset["dataset_id"]})
    elapsed = time.monotonic() - start
    digest = save_checkpoint(output_dir/"latest.npz", model, optimizer, tokenizer, rng, {"manifest_hash": dataset["manifest_hash"], "dataset_id": dataset["dataset_id"], "created_at": utcnow()})
    with no_grad():
        final_validation = float(model.loss(eval_x, eval_y).data)
    processed = (optimizer.step_count-start_step)*batch_size*model.config.context_length
    report = {"kind": "experimental_cpu_training", "programming_qualified": False, "cancelled": cancelled, "parameter_count": model.parameter_count, "steps_this_run": optimizer.step_count-start_step, "total_steps": optimizer.step_count, "tokens_processed_this_run": processed, "train_tokens_in_memory": len(tokens["train"]), "validation_tokens_in_memory": len(tokens["validation"]), "test_records_never_used_by_trainer": len(dataset["splits"]["test"]), "elapsed_seconds": elapsed, "tokens_per_second": processed/max(elapsed,1e-12), "initial_validation_loss": initial_validation, "final_validation_loss": final_validation, "checkpoint_sha256": digest, "manifest_hash": dataset["manifest_hash"], "history": history, "notice": "Perda numérica não mede competência de programação. Não é modelo aprovado para o agente."}
    write_json(output_dir/"report.json", report)
    return report
