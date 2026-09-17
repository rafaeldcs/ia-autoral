from __future__ import annotations
import io
import json
import zipfile
from dataclasses import asdict
from pathlib import Path
import numpy as np
from .transformer import Transformer, ModelConfig
from .optimizer import AdamW
from .tokenizer import tokenizer_from_dict
from ..util import atomic_write, canonical_json, sha256


def save_checkpoint(path: Path, model: Transformer, optimizer: AdamW, tokenizer, rng: np.random.Generator, provenance: dict) -> str:
    metadata = {"format_version": 1, "architecture": "local-author-causal-transformer-cpu", "config": asdict(model.config), "tokenizer": tokenizer.to_dict(), "optimizer": {"lr": optimizer.lr, "weight_decay": optimizer.weight_decay, "clip_norm": optimizer.clip_norm, "step_count": optimizer.step_count}, "rng_state": rng.bit_generator.state, "provenance": provenance, "programming_qualified": False}
    arrays = {"metadata": np.frombuffer(canonical_json(metadata), dtype=np.uint8)}
    for name, p in model.parameters.items():
        arrays["weight:"+name] = p.data
        arrays["moment1:"+name] = optimizer.m[name]
        arrays["moment2:"+name] = optimizer.v[name]
    output = io.BytesIO()
    np.savez(output, **arrays)
    raw = output.getvalue()
    digest = sha256(raw)
    atomic_write(path, raw)
    atomic_write(Path(str(path)+".sha256"), digest.encode("ascii"))
    return digest


def load_checkpoint(path: Path):
    if path.stat().st_size > 128_000_000:
        raise ValueError("Checkpoint excede o limite do motor CPU.")
    raw = path.read_bytes()
    expected = Path(str(path)+".sha256").read_text(encoding="ascii").strip()
    if sha256(raw) != expected:
        raise ValueError("Hash do checkpoint inválido.")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        if len(entries) > 1000 or sum(i.file_size for i in entries) > 128_000_000:
            raise ValueError("Arquivo de checkpoint excede os limites de descompressão.")
    with np.load(io.BytesIO(raw), allow_pickle=False) as archive:
        if "metadata" not in archive.files or archive["metadata"].dtype != np.uint8 or archive["metadata"].size > 100_000:
            raise ValueError("Metadados inválidos.")
        meta = json.loads(archive["metadata"].tobytes())
        if meta.get("format_version") != 1 or meta.get("architecture") != "local-author-causal-transformer-cpu":
            raise ValueError("Formato de checkpoint não suportado.")
        model = Transformer(ModelConfig(**meta["config"]))
        tokenizer = tokenizer_from_dict(meta["tokenizer"])
        if tokenizer.vocab_size != model.config.vocab_size:
            raise ValueError("Vocabulário incompatível.")
        opt_info = meta["optimizer"]
        optimizer = AdamW(model.parameters, opt_info["lr"], opt_info["weight_decay"], opt_info["clip_norm"])
        optimizer.step_count = opt_info["step_count"]
        if type(optimizer.step_count) is not int or optimizer.step_count < 0:
            raise ValueError("Estado do otimizador inválido.")
        allowed = {"metadata"}
        for name, param in model.parameters.items():
            for prefix, dest in [("weight:", param.data), ("moment1:", optimizer.m[name]), ("moment2:", optimizer.v[name])]:
                key = prefix + name
                allowed.add(key)
                if key not in archive.files:
                    raise ValueError("Parâmetro ausente no checkpoint.")
                array = archive[key]
                if array.shape != dest.shape or array.dtype != np.float64 or not np.all(np.isfinite(array)):
                    raise ValueError("Shape, precisão ou valores de parâmetro inválidos.")
                dest[...] = array
        if set(archive.files) != allowed:
            raise ValueError("Checkpoint contém campos desconhecidos.")
    rng = np.random.default_rng()
    rng.bit_generator.state = meta["rng_state"]
    return model, optimizer, tokenizer, rng, meta
