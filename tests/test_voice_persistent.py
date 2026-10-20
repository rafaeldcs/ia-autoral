"""Persistent voice lifecycle contracts with doubles, not recognition-quality evidence."""
import json
import importlib.util
from pathlib import Path
import threading
from unittest.mock import Mock, patch
from tests.helpers import WorkspaceCase
from tests.test_voice import audio_fixture, sandbox_fixture, spec_fixture
from localauthor.voice import PersistentSpeechRuntime, VoiceService, validate_manifest, verify_sandbox
from localauthor.errors import PolicyError


class PersistentVoiceTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.spec = {**spec_fixture(), 'schema': 2, 'protocol': 'persistent-v1'}
        self.path = self.settings.home / 'voice/model.json'
        self.path.parent.mkdir(); self.path.write_text(json.dumps(self.spec))

    def test_protocol_must_be_explicit_and_legacy_manifest_still_valid(self):
        validate_manifest(self.spec); validate_manifest(spec_fixture())
        for change in [{'schema': True}, {'protocol': 'remote'}, {'schema': 1}, {'url': 'http://outside.invalid'}, {'threads':True}, {'threads':12}]:
            with self.subTest(change=change), self.assertRaises(PolicyError): validate_manifest({**self.spec, **change})

    def test_audio_window_covers_every_sample_at_all_supported_durations(self):
        path=Path(__file__).resolve().parents[1]/'scripts/voice-persistent-worker.py'
        loader=importlib.util.spec_from_file_location('voice_worker_contract',path)
        module=importlib.util.module_from_spec(loader);loader.loader.exec_module(module)
        for samples in range(4800,480001,131):
            window=module.audio_context_size(44+samples*2)
            self.assertGreaterEqual(window,(samples+319)//320)
            self.assertLessEqual(window,1500)
        self.assertEqual(module.audio_context_size(960044),1500)
        for count in [44,9643,960045]:
            with self.assertRaises(ValueError):module.audio_context_size(count)

    def test_persistent_runtime_disables_docker_transcript_logs(self):
        sandbox=sandbox_fixture();sandbox['HostConfig']['LogConfig']={'Type':'none','Config':{}}
        verify_sandbox(sandbox,self.spec)
        sandbox['HostConfig']['LogConfig']['Type']='json-file'
        with self.assertRaises(PolicyError):verify_sandbox(sandbox,self.spec)

    def test_six_threads_require_the_corresponding_cpu_budget(self):
        spec=validate_manifest({**self.spec,'threads':6})
        sandbox=sandbox_fixture();sandbox['HostConfig']['LogConfig']={'Type':'none','Config':{}}
        with self.assertRaises(PolicyError):verify_sandbox(sandbox,spec)
        sandbox['HostConfig']['NanoCpus']=6_000_000_000;verify_sandbox(sandbox,spec)

    def runtime(self):
        runtime=Mock()
        runtime.transcribe.return_value={'text':'Olá','offline':True,'audio_retained':False}
        return runtime

    def test_reuses_only_weights_and_closes_on_shutdown_without_persistent_audio(self):
        runtime=self.runtime(); factory=Mock(return_value=runtime)
        service=VoiceService(self.settings.home,self.store,factory=factory)
        before=self.store.stats()
        for ident in ['a','b']: service.transcribe(self.project['id'],ident*32,audio_fixture())
        self.assertEqual(factory.call_count,1); self.assertEqual(runtime.transcribe.call_count,2)
        self.assertEqual(self.store.stats(),before)
        service.close(); runtime.close.assert_called_once()

    def test_manifest_change_evicts_before_loading_another_runtime(self):
        first,second=self.runtime(),self.runtime()
        service=VoiceService(self.settings.home,self.store,factory=Mock(side_effect=[first,second]))
        service.transcribe(self.project['id'],'a'*32,audio_fixture())
        self.path.write_text(json.dumps({**self.spec,'image_id':'sha256:'+'8'*64}))
        service.transcribe(self.project['id'],'b'*32,audio_fixture())
        first.close.assert_called_once(); self.assertIs(service.runtime,second); service.close()

    def test_failed_runtime_is_removed_and_next_request_constructs_a_fresh_one(self):
        first,second=self.runtime(),self.runtime();first.transcribe.side_effect=PolicyError('decoder interrupted')
        service=VoiceService(self.settings.home,self.store,factory=Mock(side_effect=[first,second]))
        with self.assertRaises(PolicyError): service.transcribe(self.project['id'],'a'*32,audio_fixture())
        first.close.assert_called_once(); self.assertIsNone(service.runtime)
        self.assertEqual(service.transcribe(self.project['id'],'b'*32,audio_fixture())['text'],'Olá');service.close()

    def test_unconfirmed_shutdown_blocks_reuse_instead_of_loading_another_engine(self):
        runtime=self.runtime();runtime.transcribe.side_effect=PolicyError('decoder interrupted')
        runtime.close.side_effect=PolicyError('shutdown unconfirmed')
        service=VoiceService(self.settings.home,self.store,factory=Mock(return_value=runtime))
        for ident in ['a','b']:
            with self.assertRaises(PolicyError):service.transcribe(self.project['id'],ident*32,audio_fixture())
        self.assertTrue(service.runtime_failed);self.assertEqual(service.factory.call_count,1)

    def test_unverified_container_is_never_started(self):
        runtime=PersistentSpeechRuntime(self.spec)
        runtime.docker=Mock(side_effect=[('a'*64).encode(),b'[{}]',b''])
        with patch('localauthor.voice.subprocess.Popen') as launch:
            with self.assertRaises(PolicyError):runtime.transcribe(audio_fixture(),threading.Event())
            launch.assert_not_called()
        self.assertTrue(runtime.closed);self.assertIsNone(runtime.container)

    def test_changed_sandbox_on_reuse_is_rejected_and_container_removed(self):
        runtime=PersistentSpeechRuntime(self.spec);runtime.container='a'*64
        runtime.docker=Mock(side_effect=[b'[{}]',b''])
        with self.assertRaises(PolicyError):runtime.transcribe(audio_fixture(),threading.Event())
        runtime.docker.assert_any_call(['rm','--force','a'*64]);self.assertTrue(runtime.closed)

    def test_cancellation_releases_only_the_owned_container(self):
        runtime=PersistentSpeechRuntime(self.spec);runtime.container='a'*64;runtime.docker=Mock(return_value=b'')
        cancel=threading.Event();cancel.set()
        with self.assertRaises(PolicyError):runtime.transcribe(audio_fixture(),cancel)
        runtime.docker.assert_called_once_with(['rm','--force','a'*64])
