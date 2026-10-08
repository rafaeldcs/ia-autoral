import http.client
import json
from pathlib import Path
import threading
from unittest.mock import Mock

from tests.helpers import WorkspaceCase
from tests.test_voice import audio_fixture, spec_fixture
from localauthor.application import Application
from localauthor.server import create_server


class VoiceHttpTests(WorkspaceCase):
    def setUp(self):
        super().setUp(); self.app = Application(self.settings)
        target = self.settings.home / 'voice/model.json'; target.parent.mkdir(); target.write_text(json.dumps(spec_fixture()))
        self.runtime = Mock(); self.runtime.transcribe.return_value = {'text': 'Olá', 'offline': True, 'audio_retained': False}
        self.app.voice.factory = lambda spec: self.runtime
        self.server = create_server(self.app, Path(__file__).resolve().parents[1] / 'ui', port=0)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True); self.worker.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.worker.join(); self.app.close(); super().tearDown()

    def request(self, path, body=None, auth=True, origin=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        headers = {'Authorization': 'Bearer ' + self.settings.token} if auth else {}
        if body is not None: headers['Content-Type'] = 'application/json'
        if origin: headers['Origin'] = origin
        conn.request('POST' if body is not None else 'GET', path, json.dumps(body) if body is not None else None, headers)
        response = conn.getresponse(); raw = response.read(); conn.close()
        return response.status, json.loads(raw)

    def test_authentication_and_same_origin_are_required(self):
        body = {'project_id': self.project['id'], 'request_id': 'a' * 32, 'audio': audio_fixture()}
        self.assertEqual(self.request('/api/voice/status', auth=False)[0], 401)
        self.assertEqual(self.request('/api/voice/transcribe', body, auth=False)[0], 401)
        self.assertEqual(self.request('/api/voice/transcribe', body, origin='https://other.invalid')[0], 400)
        self.runtime.transcribe.assert_not_called()

    def test_real_route_does_not_save_audio_transcript_or_a_job(self):
        before = self.app.store.stats()
        status, result = self.request('/api/voice/transcribe', {'project_id': self.project['id'], 'request_id': 'a' * 32, 'audio': audio_fixture()})
        self.assertEqual(status, 200); self.assertFalse(result['audio_retained']); self.assertEqual(result['text'], 'Olá')
        self.assertEqual(self.app.store.stats(), before); self.assertFalse(self.app.jobs.list())

    def test_extra_fields_credentials_and_invalid_audio_rejected_before_decoder(self):
        base = {'project_id': self.project['id'], 'request_id': 'a' * 32, 'audio': audio_fixture()}
        for body in [{**base, 'password': 'synthetic-test-only'}, {**base, 'audio': 'invalid'}, {**base, 'request_id': '../../path'}]:
            status, result = self.request('/api/voice/transcribe', body)
            self.assertEqual(status, 400); self.assertNotIn('synthetic-test-only', json.dumps(result))
        self.runtime.transcribe.assert_not_called()

    def test_status_hides_paths_and_cancel_is_scoped(self):
        status, result = self.request('/api/voice/status'); self.assertEqual(status, 200)
        self.assertTrue(result['registered']); self.assertNotIn(str(self.settings.home), json.dumps(result))
        self.assertFalse(result['training_allowed'])
        status, result = self.request('/api/voice/cancel', {'project_id': self.project['id'], 'request_id': 'a' * 32})
        self.assertEqual(status, 200); self.assertTrue(result['cancel_requested'])
