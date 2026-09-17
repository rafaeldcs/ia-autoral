from __future__ import annotations
from dataclasses import dataclass, asdict
import numpy as np
from .tensor import Tensor, layer_norm, gelu, cross_entropy, no_grad


@dataclass
class ModelConfig:
    vocab_size: int = 258
    context_length: int = 32
    dimension: int = 32
    heads: int = 4
    layers: int = 2
    expansion: int = 4
    seed: int = 42

    def validate(self):
        for k, v in asdict(self).items():
            if type(v) is not int or (v <= 0 and k != "seed"):
                raise ValueError(f"Configuração inválida: {k}")
        if not 258 <= self.vocab_size <= 1024 or self.context_length > 256 or self.dimension > 256 or self.layers > 8 or self.expansion > 4:
            raise ValueError("Configuração excede os limites do motor CPU de referência.")
        if self.dimension % self.heads:
            raise ValueError("Dimensão deve ser divisível pelo número de cabeças.")
        d = self.dimension
        params = self.vocab_size * d + self.context_length * d + self.layers * ((4 + 2 * self.expansion) * d * d + (9 + self.expansion) * d) + 2*d
        if params > 2_000_000:
            raise ValueError("Motor CPU limitado a 2 milhões de parâmetros; GPU/escala maior ainda não implementada.")


class Transformer:
    """Decoder causal pre-LayerNorm, pesos de saída compartilhados com os embeddings."""
    def __init__(self, config: ModelConfig):
        config.validate()
        self.config = config
        self.parameters: dict[str, Tensor] = {}
        rng = np.random.default_rng(config.seed)
        d = config.dimension
        def weight(name, shape, mode="normal"):
            data = np.ones(shape) if mode == "ones" else np.zeros(shape) if mode == "zeros" else rng.normal(0, 0.02, shape)
            self.parameters[name] = Tensor(data, requires_grad=True)
        weight("token", (config.vocab_size, d))
        weight("position", (config.context_length, d))
        for block in range(config.layers):
            base = f"block.{block}."
            for norm in ("ln1", "ln2"):
                weight(base+norm+".gain", (d,), "ones")
                weight(base+norm+".bias", (d,), "zeros")
            for name in ("q", "k", "v", "out"):
                weight(base+name+".weight", (d, d))
                weight(base+name+".bias", (d,), "zeros")
            weight(base+"ff1.weight", (d, d*config.expansion))
            weight(base+"ff1.bias", (d*config.expansion,), "zeros")
            weight(base+"ff2.weight", (d*config.expansion, d))
            weight(base+"ff2.bias", (d,), "zeros")
        weight("final.gain", (d,), "ones")
        weight("final.bias", (d,), "zeros")

    @property
    def parameter_count(self) -> int:
        return sum(p.data.size for p in self.parameters.values())

    def forward(self, token_ids: np.ndarray) -> Tensor:
        ids = np.asarray(token_ids, dtype=np.int64)
        if ids.ndim != 2 or ids.shape[1] > self.config.context_length or ids.shape[1] < 1:
            raise ValueError("Entrada deve ser [batch, tempo], dentro do contexto.")
        p, c = self.parameters, self.config
        batch, length = ids.shape
        x = p["token"].embedding(ids) + p["position"].embedding(np.arange(length)[None, :])
        head_dim = c.dimension // c.heads
        mask = Tensor(np.triu(np.full((length, length), -1e9), k=1))
        for block in range(c.layers):
            base = f"block.{block}."
            h = layer_norm(x, p[base+"ln1.gain"], p[base+"ln1.bias"])
            q, k, v = [(h @ p[base+name+".weight"] + p[base+name+".bias"]).reshape(batch, length, c.heads, head_dim).transpose(0, 2, 1, 3) for name in ("q", "k", "v")]
            attention = ((q @ k.transpose(0, 1, 3, 2)) / np.sqrt(head_dim) + mask).softmax()
            mixed = (attention @ v).transpose(0, 2, 1, 3).reshape(batch, length, c.dimension)
            x = x + mixed @ p[base+"out.weight"] + p[base+"out.bias"]
            h = layer_norm(x, p[base+"ln2.gain"], p[base+"ln2.bias"])
            x = x + gelu(h @ p[base+"ff1.weight"] + p[base+"ff1.bias"]) @ p[base+"ff2.weight"] + p[base+"ff2.bias"]
        h = layer_norm(x, p["final.gain"], p["final.bias"])
        return h @ p["token"].transpose(1, 0)

    def loss(self, inputs: np.ndarray, targets: np.ndarray) -> Tensor:
        return cross_entropy(self.forward(inputs), targets)

    def generate(self, ids: list[int], max_tokens: int = 64, temperature: float = 0.8, seed: int = 42) -> list[int]:
        if not 1 <= max_tokens <= 256 or not 0.05 <= temperature <= 2:
            raise ValueError("Limites de geração excedidos.")
        sequence = list(ids) or [256]
        rng = np.random.default_rng(seed)
        generated = []
        with no_grad():
            for _ in range(max_tokens):
                logits = self.forward(np.array([sequence[-self.config.context_length:]])).data[0, -1] / temperature
                logits[256] = -1e9  # BOS is not a text completion token.
                prob = np.exp(logits-logits.max())
                prob /= prob.sum()
                token = int(rng.choice(len(prob), p=prob))
                if token == 257: break
                generated.append(token)
                sequence.append(token)
        return generated
