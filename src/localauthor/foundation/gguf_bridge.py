"""Optional host-to-local-Docker inference. No ports, shell or generated-code tools."""
import json
from pathlib import Path
import queue
import re
import subprocess
import tempfile
import threading
import time
import uuid

from ..errors import PolicyError
from .runtime import check_cancel
from .models import local_path, write_new

ROOT = Path(__file__).resolve().parents[3]
MAX_FRAME = 1_000_000


def verify_sandbox(info, spec):
    host = info.get("HostConfig", {})
    mounts = info.get("Mounts", [])
    sources = {m.get("Destination"): m for m in mounts}
    code, weights = sources.get("/workspace", {}), sources.get("/weights", {})
    expected_code = str(ROOT).replace("\\", "/").rstrip("/").lower()
    actual_code = str(code.get("Source", "")).replace("\\", "/").rstrip("/").lower()
    # Docker Desktop may report the same Windows path through its WSL bind prefix.
    if expected_code[1:3] == ":/":
        alternative = "/run/desktop/mnt/host/" + expected_code[0] + expected_code[2:]
    else: alternative = expected_code
    if (info.get("Image") != spec.runtime_profile["image_id"] or info.get("Config", {}).get("User") != "10001:10001"
            or host.get("NetworkMode") != "none" or not host.get("ReadonlyRootfs") or host.get("Privileged")
            or host.get("CapDrop") != ["ALL"] or "no-new-privileges" not in host.get("SecurityOpt", [])
            or host.get("Memory") != 6 * 1024 ** 3 or host.get("MemorySwap") != 6 * 1024 ** 3
            or host.get("NanoCpus") != 4_000_000_000 or host.get("PidsLimit") != 128
            or host.get("PortBindings") or len(mounts) != 2 or any(m.get("RW") for m in mounts)
            or code.get("Type") != "bind" or actual_code not in {expected_code, alternative}
            or weights.get("Type") != "volume" or weights.get("Name") != spec.runtime_profile["volume"]
            or host.get("Tmpfs") != {"/tmp": "rw,nosuid,nodev,size=256m"}):
        raise PolicyError("Sandbox GGUF diverge do perfil revisado; não iniciar.")
    requests = host.get("DeviceRequests") or []
    if spec.device == "cuda":
        if len(requests) != 1 or requests[0].get("Count") != -1 or ["gpu"] not in requests[0].get("Capabilities", []):
            raise PolicyError("GPU Docker não solicitada no perfil explícito.")
    elif requests: raise PolicyError("GPU não autorizada no perfil CPU.")


class DockerGgufRuntime:
    def __init__(self, spec, *, diagnostics=None):
        if spec.backend != "gguf-docker": raise PolicyError("Backend incompatível.")
        self.spec = spec
        self.container = None
        self.process = None
        self.closed = False
        self.stopped = False
        self.frames = queue.Queue(maxsize=2)
        self.lock = threading.RLock()
        self.diagnostics = local_path(diagnostics or Path(tempfile.gettempdir()) / "LocalAuthor-GGUF-diagnostics")
        self.diagnostics.mkdir(parents=True, exist_ok=True)
        used = sum(local_path(p).stat().st_size for p in self.diagnostics.iterdir() if p.is_file())
        if used + 65_000_000 > 512_000_000:
            raise PolicyError("Quota privada de diagnósticos GGUF atingida; revise os arquivos antes de continuar.")
        self.diagnostic_snapshot = None
        weights = [name for name in spec.files if name.endswith(".gguf")]
        if len(weights) != 1: raise PolicyError("Inventário GGUF inválido.")
        command = ["create", "--pull", "never", "--interactive", "--name", "localauthor-chat-" + uuid.uuid4().hex,
            "--network", "none", "--read-only", "--user", "10001:10001", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--memory", "6g", "--memory-swap", "6g",
            "--cpus", "4", "--pids-limit", "128", "--tmpfs", "/tmp:rw,nosuid,nodev,size=256m",
            "--mount", f"type=bind,src={ROOT},dst=/workspace,readonly",
            "--mount", f"type=volume,src={spec.runtime_profile['volume']},dst=/weights,readonly",
            "--workdir", "/workspace", "--env", "PYTHONDONTWRITEBYTECODE=1"]
        if spec.device == "cuda": command += ["--gpus", "all"]
        command += [spec.runtime_profile["image_id"], "scripts/foundation-gguf-rpc.py",
            "--weights", "/weights/" + weights[0], "--sha256", spec.files[weights[0]],
            "--context", str(spec.context_tokens), "--tokens", str(spec.output_tokens),
            "--reasoning-budget", str(spec.runtime_profile["reasoning_budget"])]
        if spec.device == "cuda": command += ["--gpu"]
        try:
            ident = self.docker(command).decode("ascii").strip()
            if not re.fullmatch(r"[a-f0-9]{64}", ident): raise PolicyError("Docker não retornou identidade válida.")
            self.container = ident
            verify_sandbox(json.loads(self.docker(["inspect", ident]))[0], spec)
            self.process = subprocess.Popen(["docker", "start", "--attach", "--interactive", ident],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
            threading.Thread(target=self.read_frames, daemon=True).start()
            # Drain diagnostic stderr to avoid deadlock; no raw persistence or UI output.
            threading.Thread(target=self.drain_errors, daemon=True).start()
            ready = self.receive(seconds=150)
            if not isinstance(ready, dict) or set(ready) != {"ready", "compute", "isolation"} or ready["ready"] is not True:
                raise PolicyError("Handshake de inferência local inválido.")
            self.compute = ready["compute"]
            if spec.device == "cuda" and (not isinstance(self.compute, dict) or self.compute.get("device") != "CUDA0"
                    or type(self.compute.get("total_layers")) is not int or self.compute["total_layers"] < 1
                    or self.compute.get("offloaded_layers") != self.compute["total_layers"]):
                raise PolicyError("Offload completo não comprovado pelo runtime.")
        except Exception:
            self.close()
            raise

    @staticmethod
    def docker(arguments, *, max_bytes=MAX_FRAME):
        try:
            result = subprocess.run(["docker", *arguments], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=20, shell=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PolicyError("Docker local indisponível; nenhum fallback no host.") from exc
        if result.returncode or len(result.stdout) > max_bytes:
            raise PolicyError("Comando Docker local rejeitado; conferir Docker Desktop.")
        return result.stdout

    def drain_errors(self):
        try:
            while self.process.stderr.read(4096): pass
        except (OSError, ValueError): pass

    def read_frames(self):
        try:
            while True:
                raw = self.process.stdout.readline(MAX_FRAME + 1)
                if not raw: raise PolicyError("Runtime isolado encerrou a comunicação.")
                if len(raw) > MAX_FRAME or not raw.endswith(b"\n"): raise PolicyError("Frame GGUF excede o orçamento.")
                self.frames.put_nowait(json.loads(raw))
        except Exception as exc:
            try: self.frames.put_nowait(exc)
            except queue.Full: pass

    def receive(self, *, seconds, cancel=None):
        deadline = time.monotonic() + seconds
        while True:
            check_cancel(cancel, deadline)
            try:
                value = self.frames.get(timeout=0.1)
                if isinstance(value, Exception): raise PolicyError("Comunicação GGUF inválida.") from value
                return value
            except queue.Empty: pass

    def rpc(self, operation, messages, cancel=None):
        with self.lock:
            try:
                check_cancel(cancel)
                if self.closed: raise PolicyError("Runtime GGUF já foi encerrado.")
                ident = uuid.uuid4().hex
                raw = json.dumps({"id": ident, "operation": operation, "messages": messages}, ensure_ascii=False).encode("utf-8") + b"\n"
                if len(raw) > 128000: raise PolicyError("Pedido GGUF excede o orçamento.")
                self.process.stdin.write(raw); self.process.stdin.flush()
                result = self.receive(seconds=30 if operation == "count" else 310, cancel=cancel)
                if not isinstance(result, dict) or result.get("id") != ident or set(result) != {"id", "result"}:
                    raise PolicyError("Resposta GGUF ausente ou rejeitada pelo worker isolado.")
                return result["result"]
            except Exception:
                self.close()
                raise

    def count(self, messages):
        result = self.rpc("count", messages)
        if type(result) is not int or result < 1:
            self.close(); raise PolicyError("Contagem real de tokens GGUF inválida.")
        return result

    def generate(self, messages, cancel=None):
        result = self.rpc("generate", messages, cancel)
        if (not isinstance(result, list) or len(result) != 2 or not isinstance(result[0], str)
                or not result[0].strip() or type(result[1]) is not bool):
            self.close(); raise PolicyError("Conclusão GGUF inválida.")
        return result[0], result[1]

    def close(self):
        if self.closed and self.stopped: return
        self.closed = True
        failure = None
        if self.container:
            if self.diagnostic_snapshot is None:
                ident = uuid.uuid4().hex
                target = local_path(self.diagnostics / (ident + ".log"))
                snapshot = {"container_id": self.container, "snapshot_before_stop": True, "captured": False}
                try:
                    # tmpfs disappears at stop; this snapshot cannot contain post-stop events.
                    # Docker archive/cp cannot reliably see tmpfs on every Desktop version.
                    # Fixed trusted reader only: no caller-supplied path or shell command.
                    reader = "import sys;from pathlib import Path;r=Path('/tmp/gguf-engine.log').open('rb').read(65000001);sys.exit(2) if len(r)>65000000 else sys.stdout.buffer.write(r)"
                    raw = self.docker(["exec", self.container, "python3", "-c", reader], max_bytes=65_000_000)
                    with target.open("xb") as stream: stream.write(raw)
                    snapshot.update(captured=True, bytes=len(raw), file=target.name)
                except Exception as exc: snapshot["error_type"] = type(exc).__name__
                self.diagnostic_snapshot = snapshot
                # Failure to archive must not prevent stopping the owned process.
                try: write_new(self.diagnostics / (ident + ".json"), snapshot)
                except (OSError, PolicyError): pass
            try:
                self.docker(["stop", "--time", "5", self.container])
                state = json.loads(self.docker(["inspect", self.container]))[0]["State"]
                if state.get("Running") is not False: raise PolicyError("Runtime GGUF não confirmou encerramento.")
                self.stopped = True
            except Exception as exc: failure = exc
        else: self.stopped = True
        if self.process:
            try: self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill(); self.process.wait(timeout=5)
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                if stream: stream.close()
        if failure: raise PolicyError("Não foi possível confirmar a parada da inferência Docker local.") from failure
