from __future__ import annotations
from contextlib import contextmanager
from contextvars import ContextVar
import numpy as np

_GRAD = ContextVar("localai_grad", default=True)


@contextmanager
def no_grad():
    token = _GRAD.set(False)
    try:
        yield
    finally:
        _GRAD.reset(token)


def sum_to_shape(gradient: np.ndarray, shape: tuple) -> np.ndarray:
    while gradient.ndim > len(shape):
        gradient = gradient.sum(axis=0)
    for axis, size in enumerate(shape):
        if size == 1 and gradient.shape[axis] != 1:
            gradient = gradient.sum(axis=axis, keepdims=True)
    return gradient.reshape(shape)


class Tensor:
    """Autodiff reverse-mode CPU, float64, deliberadamente simples e verificável."""
    def __init__(self, data, requires_grad: bool = False):
        self.data = np.asarray(data, dtype=np.float64)
        self.requires_grad = bool(requires_grad and _GRAD.get())
        self.grad = np.zeros_like(self.data) if self.requires_grad else None
        self.parents: tuple[Tensor, ...] = ()
        self._backward = lambda: None

    @staticmethod
    def wrap(value) -> "Tensor":
        return value if isinstance(value, Tensor) else Tensor(value)

    def _result(self, data, parents: tuple["Tensor", ...], backward):
        out = Tensor(data, any(p.requires_grad for p in parents))
        if out.requires_grad:
            out.parents = parents
            out._backward = lambda: backward(out.grad)
        return out

    def _add_grad(self, gradient):
        if self.requires_grad:
            self.grad += sum_to_shape(np.asarray(gradient), self.data.shape)

    def __add__(self, other):
        other = Tensor.wrap(other)
        return self._result(self.data + other.data, (self, other), lambda g: (self._add_grad(g), other._add_grad(g)))
    __radd__ = __add__

    def __neg__(self):
        return self * -1.0

    def __sub__(self, other):
        return self + -Tensor.wrap(other)

    def __rsub__(self, other):
        return Tensor.wrap(other) - self

    def __mul__(self, other):
        other = Tensor.wrap(other)
        return self._result(self.data * other.data, (self, other), lambda g: (self._add_grad(g * other.data), other._add_grad(g * self.data)))
    __rmul__ = __mul__

    def __truediv__(self, other):
        return self * (Tensor.wrap(other) ** -1.0)

    def __pow__(self, exponent: float):
        value = self.data ** exponent
        return self._result(value, (self,), lambda g: self._add_grad(g * exponent * self.data ** (exponent - 1)))

    def __matmul__(self, other):
        other = Tensor.wrap(other)
        if self.data.ndim < 2 or other.data.ndim < 2:
            raise ValueError("Matmul requer dimensões >= 2; use reshape explícito para vetores.")
        return self._result(self.data @ other.data, (self, other), lambda g: (self._add_grad(g @ np.swapaxes(other.data, -1, -2)), other._add_grad(np.swapaxes(self.data, -1, -2) @ g)))

    def reshape(self, *shape):
        return self._result(self.data.reshape(*shape), (self,), lambda g: self._add_grad(g.reshape(self.data.shape)))

    def transpose(self, *axes):
        if not axes:
            axes = tuple(reversed(range(self.data.ndim)))
        inverse = tuple(np.argsort(axes))
        return self._result(self.data.transpose(*axes), (self,), lambda g: self._add_grad(g.transpose(*inverse)))

    def sum(self, axis=None, keepdims: bool = False):
        def backward(g):
            if axis is not None and not keepdims:
                axes = (axis,) if isinstance(axis, int) else axis
                for a in sorted(x % self.data.ndim for x in axes):
                    g = np.expand_dims(g, a)
            self._add_grad(np.broadcast_to(g, self.data.shape))
        return self._result(self.data.sum(axis=axis, keepdims=keepdims), (self,), backward)

    def mean(self, axis=None, keepdims: bool = False):
        axes = tuple(range(self.data.ndim)) if axis is None else ((axis,) if isinstance(axis, int) else axis)
        count = int(np.prod([self.data.shape[a] for a in axes]))
        return self.sum(axis=axis, keepdims=keepdims) / count

    def tanh(self):
        value = np.tanh(self.data)
        return self._result(value, (self,), lambda g: self._add_grad(g * (1.0 - value ** 2)))

    def softmax(self, axis: int = -1):
        shifted = self.data - self.data.max(axis=axis, keepdims=True)
        exponent = np.exp(shifted)
        value = exponent / exponent.sum(axis=axis, keepdims=True)
        return self._result(value, (self,), lambda g: self._add_grad(value * (g - (g * value).sum(axis=axis, keepdims=True))))

    def embedding(self, ids: np.ndarray):
        ids = np.asarray(ids, dtype=np.int64)
        if self.data.ndim != 2 or ids.min(initial=0) < 0 or ids.max(initial=0) >= self.data.shape[0]:
            raise ValueError("Índices de embedding inválidos.")
        def backward(g):
            if self.requires_grad:
                np.add.at(self.grad, ids, g)
        return self._result(self.data[ids], (self,), backward)

    def backward(self):
        if not self.requires_grad or self.data.size != 1:
            raise ValueError("backward requer uma perda escalar com gradientes.")
        # Iterative postorder avoids Python recursion limits for a deep graph.
        ordered, visited, stack = [], set(), [(self, False)]
        while stack:
            node, exiting = stack.pop()
            if exiting:
                ordered.append(node)
            elif id(node) not in visited:
                visited.add(id(node))
                stack.append((node, True))
                stack.extend((parent, False) for parent in node.parents)
        for node in ordered:
            if node.requires_grad:
                node.grad.fill(0.0)
        self.grad.fill(1.0)
        for node in reversed(ordered):
            node._backward()


def cross_entropy(logits: Tensor, targets: np.ndarray) -> Tensor:
    targets = np.asarray(targets, dtype=np.int64)
    if targets.shape != logits.data.shape[:-1]:
        raise ValueError("Shape dos alvos incompatível.")
    if targets.min(initial=0) < 0 or targets.max(initial=0) >= logits.data.shape[-1]:
        raise ValueError("Token alvo fora do vocabulário.")
    flat = logits.data.reshape(-1, logits.data.shape[-1])
    centered = flat - flat.max(axis=1, keepdims=True)
    exp = np.exp(centered)
    probs = exp / exp.sum(axis=1, keepdims=True)
    rows = np.arange(targets.size)
    loss = (-centered[rows, targets.ravel()] + np.log(exp.sum(axis=1))).mean()
    def backward(g):
        grad = probs.copy()
        grad[rows, targets.ravel()] -= 1
        logits._add_grad(grad.reshape(logits.data.shape) * float(g) / targets.size)
    return logits._result(loss, (logits,), backward)


def layer_norm(x: Tensor, gain: Tensor, bias: Tensor, epsilon: float = 1e-5) -> Tensor:
    centered = x - x.mean(axis=-1, keepdims=True)
    return centered * ((centered * centered).mean(axis=-1, keepdims=True) + epsilon) ** -0.5 * gain + bias


def gelu(x: Tensor) -> Tensor:
    return x * 0.5 * (1 + (np.sqrt(2.0 / np.pi) * (x + 0.044715 * x ** 3)).tanh())
