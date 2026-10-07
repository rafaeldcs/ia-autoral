"""Operator-invoked local checkpoint smoke test, not a quality certificate.

A disposable spawn process contains loading/generation lifetimes. It is NOT an
OS sandbox. Reviewed checkpoint code still needs operator trust and OS egress
controls. This command neither downloads nor trains nor activates any model.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import multiprocessing
from pathlib import Path
import sys
import time

from ..errors import PolicyError


def _worker(connection, home: str, kind: str) -> None:
    from .models import ModelSpec
    from .runtime import ImageRuntime, TextRuntime, offline_environment
    offline_environment()
    engine = None
    report = {"schema": 1, "kind": kind, "success": False,
              "weights_trained": False, "quality_certified": False,
              "network_isolation_verified": False, "remote_fallback": False}
    try:
        spec = ModelSpec.load(Path(home) / "foundation" / f"{kind}-model.json", kind)
        before = spec.verify()
        report["model"] = spec.provenance()
        engine = (TextRuntime if kind == "text" else ImageRuntime)(spec)
        if kind == "text":
            messages = [{"role": "user", "content": "Responda em uma frase curta sobre programação."}]
            if engine.count(messages) + spec.output_tokens > spec.context_tokens:
                raise PolicyError("Contexto insuficiente para a verificação.")
            text, truncated = engine.generate(messages)
            if not isinstance(text, str) or not text.strip() or truncated:
                raise PolicyError("Resposta vazia ou truncada; verificação inconclusiva.")
            report["output_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
            report["output_characters"] = len(text)
        else:
            image = engine.generate("A simple blue square on a white background")
            if image.size != (512, 512):
                raise PolicyError("Dimensões visuais inesperadas.")
            report["output_sha256"] = hashlib.sha256(image.tobytes()).hexdigest()
            report["dimensions"] = list(image.size)
        engine.close()
        engine = None
        if spec.verify() != before:
            raise PolicyError("Pesos alterados durante a verificação.")
        report["success"] = True
    except Exception as exc:
        # Do not export loader messages, prompts, filenames, or credentials.
        report["error_type"] = type(exc).__name__
        report["error"] = "Modelo local ausente, incompatível ou verificação inconclusiva. Confira o manifesto e as dependências."
    finally:
        if engine is not None:
            try:
                engine.close()
            except Exception:
                report["success"] = False
                report["error"] = "Não foi possível liberar o modelo no processo de verificação."
        try:
            connection.send_bytes(json.dumps(report, ensure_ascii=False, allow_nan=False).encode("utf-8"))
        finally:
            connection.close()


def run_smoke(home: Path, kind: str = "text", *, timeout: float = 300, _target=None) -> dict:
    if kind not in {"text", "image"} or type(timeout) not in {int, float} or not math.isfinite(timeout) or not 0 < timeout <= 3600:
        raise PolicyError("Capacidade ou prazo de verificação inválidos.")
    started = time.monotonic()
    context = multiprocessing.get_context("spawn")
    reader, writer = context.Pipe(duplex=False)
    process = context.Process(target=_target or _worker, args=(writer, str(home), kind), daemon=True)
    report = {"schema": 1, "kind": kind, "success": False, "quality_certified": False,
              "weights_trained": False, "network_isolation_verified": False, "remote_fallback": False}
    launched = False
    try:
        process.start()
        launched = True
        writer.close()
        remaining = max(0, timeout - (time.monotonic() - started))
        if not reader.poll(remaining):
            report["error"] = "Prazo de carregamento, geração ou liberação excedido."
        else:
            payload = json.loads(reader.recv_bytes(65536).decode("utf-8"))
            if not isinstance(payload, dict) or type(payload.get("success")) is not bool or payload.get("schema") != 1:
                raise ValueError("Resposta do processo inválida.")
            report.update(payload)
        process.join(timeout=max(0, timeout - (time.monotonic() - started)))
        if process.is_alive() or process.exitcode != 0:
            report["success"] = False
            report["error"] = "Processo não terminou normalmente dentro do prazo."
    except (EOFError, OSError, ValueError, UnicodeError) as exc:
        report["success"] = False
        report["error_type"] = type(exc).__name__
        report["error"] = "Falha de comunicação com o processo local de verificação."
    finally:
        writer.close()
        reader.close()
        if launched and process.is_alive():
            process.terminate()
            process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join(timeout=2)
        stopped = not launched or not process.is_alive()
        report["process_exit_confirmed"] = stopped
        report["elapsed_seconds"] = time.monotonic() - started
        if not stopped:
            report["success"] = False
        if launched and stopped:
            process.close()
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", required=True, type=Path)
    parser.add_argument("--kind", choices=("text", "image"), default="text")
    parser.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args(argv)
    try:
        result = run_smoke(args.home, args.kind, timeout=args.timeout)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0 if result["success"] else 1
    except (PolicyError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
