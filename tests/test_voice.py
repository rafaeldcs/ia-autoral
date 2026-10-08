import base64
import copy
import io
import json
import math
import struct
import threading
import wave
from unittest.mock import Mock, patch

from tests.helpers import WorkspaceCase
from localauthor.errors import PolicyError, ConflictError, NotFoundError
from localauthor.voice import validate_audio, validate_manifest, verify_sandbox, VoiceService, DockerSpeechRuntime


def audio_fixture(seconds=1, silence=False):
    stream = io.BytesIO()
    with wave.open(stream, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(b''.join(struct.pack('<h', 0 if silence else round(3000 * math.sin(i * .1))) for i in range(round(seconds * 16000))))
    return base64.b64encode(stream.getvalue()).decode('ascii')


def spec_fixture():
    return {'schema': 1, 'model': 'whisper-small-q5_1', 'source': 'https://huggingface.co/ggerganov/whisper.cpp',
            'revision': '1' * 40, 'license': 'MIT', 'license_accepted': True, 'sha256': '2' * 64,
            'image_id': 'sha256:' + '3' * 64, 'volume': 'localauthor-voice-test'}


def sandbox_fixture():
    spec = spec_fixture()
    return {'Image': spec['image_id'], 'Config': {'User': '10001:10001'},
            'Mounts': [{'Type': 'volume', 'Name': spec['volume'], 'Destination': '/weights', 'RW': False}],
            'HostConfig': {'NetworkMode': 'none', 'ReadonlyRootfs': True, 'Privileged': False, 'CapDrop': ['ALL'],
                           'SecurityOpt': ['no-new-privileges'], 'Memory': 2 * 1024 ** 3, 'MemorySwap': 2 * 1024 ** 3,
                           'NanoCpus': 4_000_000_000, 'PidsLimit': 64, 'PortBindings': {}, 'DeviceRequests': [],
                           'Tmpfs': {'/tmp': 'rw,nosuid,nodev,size=64m'}}}


class VoiceTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.spec = spec_fixture()
        target = self.settings.home / 'voice/model.json'; target.parent.mkdir(); target.write_text(json.dumps(self.spec))

    def test_canonical_pcm_is_preserved(self):
        value = audio_fixture(); self.assertEqual(validate_audio(value), base64.b64decode(value))

    def test_silence_empty_short_oversize_and_corrupt_audio_rejected(self):
        for value in [None, '', [], 'not-base64!', audio_fixture(.1), audio_fixture(30.1), audio_fixture(silence=True)]:
            with self.subTest(kind=type(value).__name__), self.assertRaises(PolicyError): validate_audio(value)
        raw = bytearray(base64.b64decode(audio_fixture())); raw[22] = 2
        with self.assertRaises(PolicyError): validate_audio(base64.b64encode(raw).decode())

    def test_wrong_length_or_extra_chunks_rejected(self):
        raw = base64.b64decode(audio_fixture())
        for altered in [raw + b'private-metadata', raw[:-1], b'RIFF' + b'\0' * 4 + raw[8:]]:
            with self.assertRaises(PolicyError): validate_audio(base64.b64encode(altered).decode())

    def test_manifest_needs_license_origin_pinned_image_and_safe_volume(self):
        validate_manifest(self.spec)
        for key, value in [('license_accepted', False), ('source', 'https://other.invalid'), ('model', 'remote'),
                           ('image_id', 'latest'), ('volume', '../../private'), ('sha256', 'broken'), ('revision', 'latest')]:
            with self.subTest(key=key), self.assertRaises(PolicyError): validate_manifest({**self.spec, key: value})

    def test_no_configuration_means_unavailable_without_download(self):
        (self.settings.home / 'voice/model.json').unlink()
        service = VoiceService(self.settings.home, self.store, factory=Mock())
        self.assertFalse(service.status()['registered'])
        with self.assertRaises(PolicyError): service.transcribe(self.project['id'], 'a' * 32, audio_fixture())
        service.factory.assert_not_called()

    def test_transcription_is_ephemeral_and_never_a_persistent_job(self):
        before = self.store.stats()
        runtime = Mock(); runtime.transcribe.return_value = {'text': 'Olá', 'offline': True, 'audio_retained': False}
        service = VoiceService(self.settings.home, self.store, factory=lambda spec: runtime)
        result = service.transcribe(self.project['id'], 'a' * 32, audio_fixture())
        self.assertEqual(result['text'], 'Olá'); self.assertEqual(self.store.stats(), before)
        self.assertIsNone(service.active); service.close()

    def test_bad_project_and_request_are_rejected_before_decoder(self):
        runtime = Mock(); service = VoiceService(self.settings.home, self.store, factory=runtime)
        with self.assertRaises(NotFoundError): service.transcribe('missing', 'a' * 32, audio_fixture())
        for request in [None, [], '../path', 'a' * 33]:
            with self.assertRaises(PolicyError): service.transcribe(self.project['id'], request, audio_fixture())
            with self.assertRaises(PolicyError): service.cancel(self.project['id'], request)
        runtime.assert_not_called()

    def test_cancellation_cannot_cross_project_or_request(self):
        service = VoiceService(self.settings.home, self.store)
        cancel = threading.Event(); service.active = (self.project['id'], 'a' * 32, cancel, threading.Event())
        service.cancel(self.project['id'], 'b' * 32); self.assertFalse(cancel.is_set())
        service.cancel(self.project['id'], 'a' * 32); self.assertTrue(cancel.is_set())

    def test_concurrent_request_rejected_and_close_cancels_active_decoder(self):
        started = threading.Event(); errors = []
        class Runtime:
            def transcribe(inner, encoded, cancel):
                started.set(); cancel.wait(5); raise PolicyError('cancelled')
        service = VoiceService(self.settings.home, self.store, factory=lambda spec: Runtime())
        def request():
            try: service.transcribe(self.project['id'], 'a' * 32, audio_fixture())
            except Exception as exc: errors.append(exc)
        thread = threading.Thread(target=request); thread.start(); self.assertTrue(started.wait(2))
        with self.assertRaises(ConflictError): service.transcribe(self.project['id'], 'b' * 32, audio_fixture())
        service.close(); thread.join(2); self.assertFalse(thread.is_alive()); self.assertEqual(len(errors), 1)
        with self.assertRaises(PolicyError): service.transcribe(self.project['id'], 'c' * 32, audio_fixture())

    def test_runtime_error_clears_activity_without_fallback(self):
        runtime = Mock(); runtime.transcribe.side_effect = PolicyError('bad decoder')
        service = VoiceService(self.settings.home, self.store, factory=lambda spec: runtime)
        with self.assertRaises(PolicyError): service.transcribe(self.project['id'], 'a' * 32, audio_fixture())
        self.assertIsNone(service.active)

    def test_sandbox_rejects_network_write_mounts_root_and_missing_limits(self):
        good = sandbox_fixture(); verify_sandbox(good, self.spec)
        for key, value in [('NetworkMode', 'bridge'), ('ReadonlyRootfs', False), ('Privileged', True),
                           ('CapDrop', []), ('Memory', 0), ('PidsLimit', 0), ('SecurityOpt', []),
                           ('DeviceRequests', [{'Count': -1}]), ('PortBindings', {'80': [{}]})]:
            altered = copy.deepcopy(good); altered['HostConfig'][key] = value
            with self.subTest(key=key), self.assertRaises(PolicyError): verify_sandbox(altered, self.spec)
        for key, value in [('User', '0:0')]:
            altered = copy.deepcopy(good); altered['Config'][key] = value
            with self.assertRaises(PolicyError): verify_sandbox(altered, self.spec)
        altered = copy.deepcopy(good); altered['Mounts'][0]['RW'] = True
        with self.assertRaises(PolicyError): verify_sandbox(altered, self.spec)

    def test_unverified_runtime_is_removed_but_never_started(self):
        runtime = DockerSpeechRuntime(self.spec); calls = []
        def docker(args, **kwargs):
            calls.append(args)
            if args[0] == 'create': return ('a' * 64).encode()
            if args[0] == 'inspect': return json.dumps([{}]).encode()
            return b''
        runtime.docker = docker
        with patch('localauthor.voice.subprocess.Popen') as launch:
            with self.assertRaises(PolicyError): runtime.transcribe(audio_fixture(), threading.Event())
            launch.assert_not_called()
        self.assertEqual(calls[-1], ['rm', '--force', 'a' * 64])
