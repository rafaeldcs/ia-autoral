"""Single-owner lifecycle helper shared by LocalAuthor's local runtimes."""
from __future__ import annotations

import gc


def dispose_runtime(engine) -> None:
    """Drop owned tensors before releasing unused allocator blocks.

    Does not move tensors to CPU (which could exhaust RAM). Does not promise that
    third-party global references, CUDA contexts or arbitrary native code unload.
    Full process isolation remains a separate integration requirement.
    """
    close = getattr(engine, "close", None)
    if callable(close):
        close()


def release_tensors(owner, attributes: tuple[str, ...]) -> None:
    for name in attributes:
        if hasattr(owner, name):
            setattr(owner, name, None)
    gc.collect()
    cuda = getattr(getattr(owner, "torch", None), "cuda", None)
    if cuda is not None and cuda.is_initialized():
        cuda.empty_cache()
