"""Opt-in isolated GGUF qualification lab; never activates the production service."""
from concurrent.futures import Future, TimeoutError
import json
import re
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import threading
import time
from urllib.request import Request, build_opener, ProxyHandler

from ..errors import PolicyError
from .isolation import require_isolated_process
from .models import digest, local_path
from .runtime import check_cancel

BINARY = Path("/opt/llama-b11429/llama-server")
MAX_RESPONSE_BYTES = 1_000_000
MAX_DIAGNOSTIC_BYTES = 64_000_000


def private_diagnostic(raw, key):
    if len(raw) > MAX_RESPONSE_BYTES: raise PolicyError("Linha de diagnóstico excede orçamento.")
    return raw.replace(key.encode("ascii"), b"[private-api-key]")


def diagnostic_line_allowed(raw: bytes, after_startup: bool) -> bool:
    if not after_startup:
        return True
    match = re.match(rb"^\d+(?:\.\d+)*\s+([DIWE])\s", raw)
    if not match:
        return True
    severity = match.group(1)
    if severity == b'D':
        return False
    if severity == b'I' and b'all slots are idle' in raw:
        return False
    return True

def verify_gpu_offload(log_text):
    """A visible device is insufficient: every requested model layer must load."""
    matches = re.findall(r"offloaded (\d+)/(\d+) layers to GPU", log_text)
    if not matches or "CUDA0" not in log_text:
        raise PolicyError("GPU não comprovada; fallback CPU não autorizado.")
    loaded, total = map(int, matches[-1])
    if total < 1 or loaded != total:
        raise PolicyError("Offload GPU incompleto; fallback CPU não autorizado.")
    return {"device": "CUDA0", "offloaded_layers": loaded, "total_layers": total}


def valid_profile(context, output, threads):
    if (any(type(v) is not int for v in (context, output, threads))
            or not 256 <= context <= 8192 or not 1 <= output < min(context, 2049)
            or not 1 <= threads <= 4):
        raise PolicyError("Perfil GGUF CPU fora do orçamento homologável.")


def valid_decoding(output, reasoning_budget, json_output):
    if (type(reasoning_budget) is not int or not 0 <= reasoning_budget <= 1024
            or reasoning_budget >= output or type(json_output) is not bool):
        raise PolicyError("Perfil de raciocínio/JSON fora do orçamento.")


def completion(response):
    choices = response.get("choices") if isinstance(response, dict) else None
    if not isinstance(choices, list) or len(choices) != 1:
        raise PolicyError("Resposta GGUF sem exatamente uma conclusão.")
    row = choices[0]
    if not isinstance(row, dict) or not isinstance(row.get("message"), dict):
        raise PolicyError("Mensagem GGUF inválida.")
    text = row["message"].get("content")
    reason = row.get("finish_reason")
    if not isinstance(text, str) or not text.strip() or reason not in {"stop", "length"}:
        raise PolicyError("Conclusão GGUF ausente ou término não verificado.")
    return text.strip(), reason == "length"


class GgufLabRuntime:
    def __init__(self, weights: Path, expected_sha256: str, log: Path, *, context=2048, output=192, threads=4, gpu=False,
                 reasoning_budget=0, json_output=False):
        valid_profile(context, output, threads)
        valid_decoding(output, reasoning_budget, json_output)
        if type(gpu) is not bool: raise PolicyError("Seleção GPU inválida.")
        self.isolation = require_isolated_process()
        self.weights = local_path(weights)
        if self.weights.suffix != ".gguf" or not self.weights.is_file() or digest(self.weights) != expected_sha256:
            raise PolicyError("Pesos GGUF locais divergentes do hash adquirido/revisado.")
        if not BINARY.is_file():
            raise PolicyError("Runtime fixado ausente; não existe fallback nem download.")
        self.context, self.output = context, output
        self.reasoning_budget, self.json_output = reasoning_budget, json_output
        self.template_options = {"enable_thinking": reasoning_budget > 0}
        self.process = None
        self.key_dir = tempfile.TemporaryDirectory(prefix="localauthor-gguf-")
        self.log_path = local_path(log)
        self.log = self.log_path.open("xb")
        self.compute = {"device": "CPU", "offloaded_layers": 0}
        self.reader = None
        self._diagnostics_ready = False
        self.suppressed_diagnostic_lines = 0
        self.key = secrets.token_hex(32)
        key_file = Path(self.key_dir.name) / "api.key"
        key_file.write_text(self.key, encoding="ascii"); key_file.chmod(0o600)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]
        self.url = f"http://127.0.0.1:{port}"
        self.opener = build_opener(ProxyHandler({}))
        try:
            command = [str(BINARY), "--model", str(self.weights),
                "--ctx-size", str(context), "--n-predict", str(output), "--threads", str(threads),
                "--threads-batch", str(threads), "--parallel", "1", "--batch-size", "256",
                "--ubatch-size", "128", "--gpu-layers", "99" if gpu else "0", "--host", "127.0.0.1",
                "--port", str(port), "--offline", "--jinja", "--no-context-shift", "--no-webui",
                "--api-key-file", str(key_file), "--reasoning-format", "deepseek",
                "--reasoning-budget", str(reasoning_budget)]
            if gpu: command.extend(["--device", "CUDA0", "--split-mode", "none", "--log-verbosity", "5"])
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                shell=False)
            def record_diagnostics():
                written = 0
                while True:
                    raw = self.process.stdout.readline(MAX_RESPONSE_BYTES + 1)
                    if not raw: break
                    try: safe = private_diagnostic(raw, self.key)
                    except PolicyError:
                        self.process.terminate()
                        safe = b"Diagnostic exceeded budget; owned process stopped.\n"
                    if not diagnostic_line_allowed(safe, self._diagnostics_ready):
                        self.suppressed_diagnostic_lines += 1
                        continue
                    if written + len(safe) > MAX_DIAGNOSTIC_BYTES:
                        self.process.terminate()
                        self.log.write(b"Total diagnostic budget reached; owned process stopped.\n"); self.log.flush()
                        break
                    self.log.write(safe); self.log.flush()
                    written += len(safe)
            self.reader = threading.Thread(target=record_diagnostics, daemon=True)
            self.reader.start()
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise PolicyError("Runtime GGUF encerrou no carregamento; conferir log privado.")
                try:
                    self.request("/health", None, seconds=2)
                    break
                except (OSError, PolicyError): time.sleep(0.2)
            else: raise PolicyError("GGUF não carregou dentro de 120 segundos.")
            if gpu: self.compute = verify_gpu_offload(self.log_path.read_text(encoding="utf-8", errors="replace"))
            self._diagnostics_ready = True
        except Exception:
            self.close(); raise

    def request(self, route, payload, *, cancel=None, seconds=300):
        if route not in {"/health", "/apply-template", "/tokenize", "/v1/chat/completions"}:
            raise PolicyError("Rota do laboratório não autorizada.")
        check_cancel(cancel)
        request = Request(self.url + route,
            data=None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.key})
        future = Future()
        def read():
            try:
                with self.opener.open(request, timeout=seconds) as response:
                    raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES: raise PolicyError("Resposta GGUF excede orçamento.")
                value = json.loads(raw)
                if not isinstance(value, dict): raise PolicyError("Resposta GGUF precisa ser objeto.")
                future.set_result(value)
            except Exception as exc: future.set_exception(exc)
        threading.Thread(target=read, daemon=True).start()
        deadline = time.monotonic() + seconds
        while True:
            try:
                check_cancel(cancel, deadline)
            except PolicyError:
                self.close(); raise
            try: return future.result(timeout=0.1)
            except TimeoutError:
                if future.done(): raise

    def count(self, messages):
        if not isinstance(messages, list) or not messages or len(messages) > 200 or any(
            not isinstance(m, dict) or set(m) != {"role", "content"}
            or m["role"] not in {"system", "user", "assistant"}
            or not isinstance(m["content"], str) or not m["content"].strip() for m in messages):
            raise PolicyError("Mensagens GGUF inválidas.")
        if len(json.dumps(messages, ensure_ascii=False).encode("utf-8")) > 128000:
            raise PolicyError("Contexto GGUF excessivo.")
        template = self.request("/apply-template", {"messages": messages, "chat_template_kwargs": self.template_options})
        prompt = template.get("prompt")
        if not isinstance(prompt, str): raise PolicyError("Template GGUF ausente.")
        tokens = self.request("/tokenize", {"content": prompt, "add_special": True}).get("tokens")
        if not isinstance(tokens, list) or any(type(t) is not int for t in tokens):
            raise PolicyError("Contagem real GGUF indisponível.")
        return len(tokens)

    def generate(self, messages, cancel=None):
        check_cancel(cancel)
        if self.count(messages) + self.output > self.context:
            raise PolicyError("Contexto GGUF excedido; nenhuma fonte truncada silenciosamente.")
        payload = {"messages": messages, "max_tokens": self.output,
            "temperature": 0, "seed": 31, "stream": False, "chat_template_kwargs": self.template_options}
        if self.json_output: payload["response_format"] = {"type": "json_object"}
        response = self.request("/v1/chat/completions", payload, cancel=cancel)
        check_cancel(cancel)
        return completion(response)

    def close(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try: self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill(); self.process.wait(timeout=5)
        if self.reader is not None:
            self.reader.join(timeout=5)
        if self.process is not None and self.process.stdout is not None:
            self.process.stdout.close()
        if self.suppressed_diagnostic_lines and not self.log.closed:
            self.log.write((f"Suppressed redundant diagnostic lines: {self.suppressed_diagnostic_lines}\n").encode("ascii"))
        self.log.close()
        self.key_dir.cleanup()
