"""Ephemeral speech input. Only a registered, verified offline Docker decoder."""
from __future__ import annotations

import base64
import json
from pathlib import Path
import re
import struct
import subprocess
import threading
import time
import uuid

from .errors import PolicyError, ConflictError
from .foundation.models import read_object

MAX_SECONDS = 30
MAX_AUDIO = 44 + 16000 * 2 * MAX_SECONDS
MAX_ENCODED = 4 * ((MAX_AUDIO + 2) // 3)


def validate_audio(encoded):
    if not isinstance(encoded, str) or not 1 <= len(encoded) <= MAX_ENCODED:
        raise PolicyError("Fale por até 30 segundos em cada mensagem.")
    try:
        audio = base64.b64decode(encoded, validate=True)
    except ValueError as exc:
        raise PolicyError("Áudio inválido.") from exc
    # A single canonical PCM chunk. No filenames, arbitrary codecs or metadata.
    if (not 44 + 9600 <= len(audio) <= MAX_AUDIO or audio[:4] != b"RIFF"
            or audio[8:16] != b"WAVEfmt " or audio[36:40] != b"data"
            or struct.unpack_from('<I', audio, 4)[0] != len(audio) - 8
            or struct.unpack_from('<IHHIIHH', audio, 16) != (16, 1, 1, 16000, 32000, 2, 16)
            or struct.unpack_from('<I', audio, 40)[0] != len(audio) - 44
            or (len(audio) - 44) % 2):
        raise PolicyError("Use áudio WAV PCM mono, 16 kHz, de 0,3 a 30 segundos.")
    samples = struct.iter_unpack('<h', audio[44:])
    rms = (sum(x[0] * x[0] for x in samples) / ((len(audio) - 44) / 2)) ** .5 / 32768
    if rms < .003:
        raise PolicyError("Não ouvi uma fala. Confira o microfone e tente novamente.")
    return audio


def validate_manifest(value):
    expected = {'schema', 'model', 'source', 'revision', 'license', 'license_accepted', 'sha256', 'image_id', 'volume'}
    if (not isinstance(value, dict) or set(value) != expected or value['schema'] != 1
            or value['model'] != 'whisper-small-q5_1' or value['license'] != 'MIT'
            or value['license_accepted'] is not True
            or value['source'] != 'https://huggingface.co/ggerganov/whisper.cpp'
            or not re.fullmatch(r'[a-f0-9]{40}', str(value['revision']))
            or not re.fullmatch(r'[a-f0-9]{64}', str(value['sha256']))
            or not re.fullmatch(r'sha256:[a-f0-9]{64}', str(value['image_id']))
            or not re.fullmatch(r'localauthor-voice-[a-z0-9-]{1,64}', str(value['volume']))):
        raise PolicyError("Registro de voz inválido. Instale e registre o modelo local com origem, licença e hashes.")
    return value


def verify_sandbox(info, spec):
    host = info.get('HostConfig', {})
    mounts = info.get('Mounts', [])
    if (info.get('Image') != spec['image_id'] or info.get('Config', {}).get('User') != '10001:10001'
            or host.get('NetworkMode') != 'none' or host.get('Privileged') or not host.get('ReadonlyRootfs')
            or host.get('CapDrop') != ['ALL'] or 'no-new-privileges' not in host.get('SecurityOpt', [])
            or host.get('Memory') != 2 * 1024 ** 3 or host.get('MemorySwap') != 2 * 1024 ** 3
            or host.get('NanoCpus') != 4_000_000_000 or host.get('PidsLimit') != 64
            or host.get('PortBindings') or host.get('DeviceRequests') or host.get('Devices')
            or host.get('Tmpfs') != {'/tmp': 'rw,nosuid,nodev,size=64m'} or len(mounts) != 1
            or mounts[0].get('Type') != 'volume' or mounts[0].get('Name') != spec['volume']
            or mounts[0].get('Destination') != '/weights' or mounts[0].get('RW')):
        raise PolicyError("Isolamento da voz não confere; nenhum fallback no host.")


class DockerSpeechRuntime:
    def __init__(self, spec):
        self.spec = spec
        self.container = None

    @staticmethod
    def docker(args, *, timeout=20):
        try:
            result = subprocess.run(['docker', *args], capture_output=True, timeout=timeout, shell=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PolicyError("Docker indisponível para reconhecimento de voz local.") from exc
        if result.returncode or len(result.stdout) > 65536:
            raise PolicyError("Reconhecimento de voz indisponível. Confira o Docker no servidor.")
        return result.stdout

    def transcribe(self, encoded, cancel):
        process = None
        try:
            command = ['create', '--pull', 'never', '--interactive', '--name', 'localauthor-voice-' + uuid.uuid4().hex,
                       '--network', 'none', '--read-only', '--user', '10001:10001', '--cap-drop', 'ALL',
                       '--security-opt', 'no-new-privileges', '--memory', '2g', '--memory-swap', '2g',
                       '--cpus', '4', '--pids-limit', '64', '--tmpfs', '/tmp:rw,nosuid,nodev,size=64m',
                       '--mount', f"type=volume,src={self.spec['volume']},dst=/weights,readonly",
                       self.spec['image_id'], '--sha256', self.spec['sha256']]
            ident = self.docker(command).decode('ascii').strip()
            if not re.fullmatch(r'[a-f0-9]{64}', ident):
                raise PolicyError("Identidade do runtime de voz inválida.")
            self.container = ident
            verify_sandbox(json.loads(self.docker(['inspect', ident]))[0], self.spec)
            process = subprocess.Popen(['docker', 'start', '--attach', '--interactive', ident], stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
            payload = (json.dumps({'audio': encoded}) + '\n').encode('ascii')
            output = None
            deadline = time.monotonic() + 100
            while output is None:
                if cancel.is_set() or time.monotonic() >= deadline:
                    raise PolicyError("Conversa por voz interrompida ou fora do prazo.")
                try:
                    stdout, _ = process.communicate(payload, timeout=.25)
                    output = stdout
                except subprocess.TimeoutExpired:
                    payload = None
            if process.returncode or not 1 <= len(output) <= 40000:
                raise PolicyError("Não consegui transcrever a fala localmente.")
            verify_sandbox(json.loads(self.docker(['inspect', ident]))[0], self.spec)
            result = json.loads(output)
            if (not isinstance(result, dict) or set(result) != {'text', 'offline'} or result['offline'] is not True
                    or not isinstance(result['text'], str) or len(result['text']) > 8000):
                raise PolicyError("Resposta de voz inválida.")
            if not result['text'].strip():
                raise PolicyError("Não reconheci uma fala. Tente falar mais perto do microfone.")
            return {'text': result['text'], 'model': self.spec['model'], 'offline': True, 'audio_retained': False}
        finally:
            try:
                if self.container:
                    # Only this uniquely owned container. Unverified containers are never started.
                    self.docker(['rm', '--force', self.container])
                    self.container = None
            finally:
                if process is not None:
                    if process.poll() is None:
                        process.kill()
                    process.communicate()


class VoiceService:
    def __init__(self, home: Path, store, *, factory=DockerSpeechRuntime):
        self.home, self.store, self.factory = Path(home), store, factory
        self.lock = threading.RLock()
        self.active = None
        self.closed = False

    def spec(self):
        return validate_manifest(read_object(self.home / 'voice/model.json'))

    def status(self):
        try:
            spec = self.spec()
            return {'registered': True, 'model': spec['model'], 'language': 'pt', 'max_seconds': MAX_SECONDS,
                    'offline': True, 'audio_retained': False, 'training_allowed': False}
        except PolicyError:
            return {'registered': False, 'max_seconds': MAX_SECONDS, 'offline': True, 'audio_retained': False,
                    'notice': 'Reconhecimento de voz não configurado no servidor.'}

    def transcribe(self, project_id, request_id, encoded):
        self.store.project(project_id)
        if not isinstance(request_id, str) or not re.fullmatch(r'[a-f0-9]{32}', request_id):
            raise PolicyError("Identificador de fala inválido.")
        validate_audio(encoded)
        spec = self.spec()
        cancel, done = threading.Event(), threading.Event()
        with self.lock:
            if self.closed:
                raise PolicyError("Servidor de voz em encerramento.")
            if self.active:
                raise ConflictError("Outro reconhecimento está em andamento; tente novamente em instantes.")
            self.active = (project_id, request_id, cancel, done)
        try:
            result = self.factory(spec).transcribe(encoded, cancel)
            if cancel.is_set():
                raise PolicyError("Fala cancelada.")
            return result
        finally:
            with self.lock:
                self.active = None
                done.set()

    def cancel(self, project_id, request_id):
        self.store.project(project_id)
        if not isinstance(request_id, str) or not re.fullmatch(r'[a-f0-9]{32}', request_id):
            raise PolicyError("Identificador de fala inválido.")
        with self.lock:
            if self.active and self.active[:2] == (project_id, request_id):
                self.active[2].set()
        return {'cancel_requested': True}

    def close(self):
        with self.lock:
            self.closed = True
            current = self.active
            if current:
                current[2].set()
        if current and not current[3].wait(15):
            raise PolicyError("Runtime de voz ainda ativo; encerramento não confirmado.")
