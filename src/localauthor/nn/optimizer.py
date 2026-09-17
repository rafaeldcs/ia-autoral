from __future__ import annotations
import numpy as np
from .tensor import Tensor


class AdamW:
    def __init__(self, parameters: dict[str, Tensor], lr: float = 0.003, weight_decay: float = 0.01, clip_norm: float = 1.0):
        if not 0 < lr <= 0.1 or not 0 <= weight_decay <= 1 or clip_norm <= 0:
            raise ValueError("Hiperparâmetros inválidos.")
        self.parameters, self.lr, self.weight_decay, self.clip_norm = parameters, lr, weight_decay, clip_norm
        self.step_count = 0
        self.m = {k: np.zeros_like(p.data) for k, p in parameters.items()}
        self.v = {k: np.zeros_like(p.data) for k, p in parameters.items()}

    def step(self) -> float:
        if any(p.grad is None or not np.all(np.isfinite(p.grad)) for p in self.parameters.values()):
            raise FloatingPointError("Gradientes ausentes ou não finitos.")
        norm = np.sqrt(sum(float(np.sum(p.grad*p.grad)) for p in self.parameters.values()))
        scale = min(1.0, self.clip_norm/(norm + 1e-12))
        self.step_count += 1
        for name, p in self.parameters.items():
            grad = p.grad * scale
            self.m[name] *= 0.9
            self.m[name] += 0.1 * grad
            self.v[name] *= 0.999
            self.v[name] += 0.001 * grad * grad
            m_hat = self.m[name] / (1 - 0.9**self.step_count)
            v_hat = self.v[name] / (1 - 0.999**self.step_count)
            # Decay only matrix weights, not bias or normalization parameters.
            if p.data.ndim >= 2:
                p.data *= 1 - self.lr*self.weight_decay
            p.data -= self.lr * m_hat / (np.sqrt(v_hat) + 1e-8)
            if not np.all(np.isfinite(p.data)):
                raise FloatingPointError("Parâmetros não finitos; treinamento interrompido.")
        return float(norm)
