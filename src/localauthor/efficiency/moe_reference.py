"""Tiny CPU numerical oracle, NOT a Nemotron implementation.

Synthetic experts are stored as three contiguous little-endian float32 matrices:
gate [intermediate, hidden], up [intermediate, hidden], down [hidden, intermediate].
Routes and coefficients come from the caller and are never altered by caching.
"""
from __future__ import annotations

import math
from typing import Callable, Sequence

from ..errors import PolicyError


def routed_swiglu(hidden, routes: Sequence[tuple[str, float]], *, intermediate: int,
                   read: Callable[[str], bytes]):
    import numpy as np

    x = np.asarray(hidden, dtype=np.float32)
    if x.ndim != 1 or not x.size or not np.isfinite(x).all():
        raise PolicyError("Vetor de entrada inválido.")
    if type(intermediate) is not int or not 0 < intermediate <= 65536 or not routes:
        raise PolicyError("Dimensões/roteamento inválidos.")
    keys = set()
    for key, weight in routes:
        if (not isinstance(key, str) or not key or key in keys
                or type(weight) not in {int, float} or not math.isfinite(weight) or weight < 0):
            raise PolicyError("Seleção de especialistas inválida; não será corrigida silenciosamente.")
        keys.add(key)
    result = np.zeros_like(x)
    size = intermediate * x.size
    for key, weight in routes:
        raw = read(key)
        if len(raw) != 3 * size * 4:
            raise PolicyError("Bloco não corresponde ao layout sintético SwiGLU.")
        values = np.frombuffer(raw, dtype="<f4")
        if not np.isfinite(values).all():
            raise PolicyError("Pesos não finitos.")
        gate = values[:size].reshape(intermediate, x.size) @ x
        up = values[size:2 * size].reshape(intermediate, x.size) @ x
        down = values[2 * size:].reshape(x.size, intermediate)
        # Stable sigmoid without clipping or modifying the expert coefficients.
        exp = np.exp(-np.abs(gate))
        sigmoid = np.where(gate >= 0, 1 / (1 + exp), exp / (1 + exp))
        result += np.float32(weight) * (down @ (gate * sigmoid * up))
    if not np.isfinite(result).all():
        raise PolicyError("Saída não finita do teste numérico.")
    return result
