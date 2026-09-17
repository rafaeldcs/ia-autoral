from __future__ import annotations
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path
from .config import Settings
from .errors import PolicyError, ConflictError
from .safety import PathPolicy
from .tasks import TaskService
from .util import utcnow, sha256, canonical_json, read_json


class SandboxRunner:
    def __init__(self, settings: Settings, tasks: TaskService):
        self.settings, self.tasks = settings, tasks

    def command(self, task_id: str, kind: str, project_file: str, container_name: str) -> list[str]:
        image = self.settings.docker_image
        if not re.fullmatch(r"[a-zA-Z0-9._/:-]+@sha256:[0-9a-f]{64}", image):
            raise PolicyError("Runner desabilitado: configure imagem local fixada por digest em docker_image.")
        tree = self.tasks.base(task_id) / "tree"
        policy = PathPolicy(tree, self.settings.max_file_bytes)
        if kind in {"dotnet-build", "dotnet-test"}:
            policy.resolve(project_file)
            if not project_file.endswith(".csproj") or not (tree / project_file).is_file():
                raise PolicyError("Selecione um .csproj presente no snapshot.")
            tool = ["dotnet", "build" if kind == "dotnet-build" else "test", project_file, "--no-restore", "--disable-build-servers", "-v", "minimal"]
        elif kind == "python-tests":
            if project_file not in {"", "tests"}:
                raise PolicyError("Python permite somente unittest discover em tests.")
            tool = ["python", "-I", "-m", "unittest", "discover", "-s", "tests", "-v"]
        else:
            raise PolicyError("Comando de ferramenta não autorizado.")
        if "," in str(tree):
            raise PolicyError("A pasta de dados não pode conter vírgula para este runner.")
        return ["docker", "run", "--name", container_name, "--pull=never", "--network=none", "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges", "--pids-limit=128", "--memory=2g", "--cpus=2", "--user=65534:65534", "--tmpfs", "/tmp:rw,nosuid,nodev,size=256m", "--mount", f"type=bind,source={tree},target=/workspace,readonly", "--workdir=/tmp", "--env", "HOME=/tmp", "--env", "DOTNET_CLI_HOME=/tmp", "--env", "DOTNET_CLI_TELEMETRY_OPTOUT=1", "--env", "DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1", "--env", "DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE=true", "--entrypoint=/bin/sh", image, "-c", self.bootstrap_script(kind), "localauthor-runner", *tool]

    @staticmethod
    def bootstrap_script(kind: str) -> str:
        # Trusted fixed script. Arguments remain separate; the project is never interpolated into shell code.
        prepare = 'mkdir -p /tmp/build && cp -R /workspace/. /tmp/build/ && cd /tmp/build && '
        if kind in {"dotnet-build", "dotnet-test"}:
            # Snapshot excludes obj/bin. Recreate assets OFFLINE in the sandbox from an explicit local feed.
            prepare += 'dotnet restore "$3" --source /opt/localai/offline-nuget --ignore-failed-sources -p:NuGetAudit=false && '
        return prepare + 'exec "$@"'

    def run(self, task_id: str, kind: str, project_file: str, cancel: threading.Event | None = None) -> dict:
        task = self.tasks.get(task_id)
        if task["state"] != "awaiting_review":
            raise ConflictError("Prepare uma proposta antes da verificação.")
        name = "localauthor-" + uuid.uuid4().hex
        command = self.command(task_id, kind, project_file, name)
        docker = shutil.which("docker")
        if not docker:
            raise PolicyError("Docker não instalado; não há execução alternativa no host.")
        command[0] = docker
        folder = self.tasks.base(task_id)
        digest = sha256(canonical_json(read_json(folder / "proposal.json")))
        if digest != task["proposal_hash"]:
            raise ConflictError("Proposta divergente.")
        env = {k: v for k, v in os.environ.items() if k in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME"}}
        # No pull, no registry credentials, no Docker socket mount inside the sandbox.
        started = time.monotonic()
        reason = None
        output = bytearray()
        with tempfile.TemporaryDirectory(prefix="localai-docker-config-") as tmp:
            env["DOCKER_CONFIG"] = tmp
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env)
            def drain():
                assert process.stdout is not None
                while True:
                    chunk = process.stdout.read(4096)
                    if not chunk: break
                    if len(output) < 100_000:
                        output.extend(chunk[:100_000-len(output)])
            reader = threading.Thread(target=drain, daemon=True)
            reader.start()
            try:
                while process.poll() is None:
                    if cancel and cancel.is_set(): reason = "cancelled"
                    elif time.monotonic() - started > self.settings.max_runner_seconds: reason = "timeout"
                    if reason:
                        subprocess.run([docker, "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, env=env, check=False)
                        if process.poll() is None: process.kill()
                        break
                    time.sleep(0.1)
                process.wait(timeout=10)
                reader.join(timeout=2)
            finally:
                if process.poll() is None: process.kill()
                subprocess.run([docker, "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, env=env, check=False)
        result = {"exit_code": process.returncode if not reason else -1, "reason": reason, "output": output.decode("utf-8", errors="replace"), "proposal_hash": digest, "duration_seconds": time.monotonic()-started, "isolation": "docker", "kind": kind, "at": utcnow()}
        with self.tasks.store.connect() as db:
            db.execute("UPDATE tasks SET test_result=?,updated_at=? WHERE id=? AND proposal_hash=?", (json.dumps(result), utcnow(), task_id, digest))
        self.tasks.store.audit("task.verified", {"task_id": task_id, "exit_code": result["exit_code"], "kind": kind})
        return result
