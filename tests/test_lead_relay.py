"""Real loopback relay HTTP + durable inbox; not Meta/WhatsApp integration tests."""
import http.client
import json
from http.server import ThreadingHTTPServer
import threading

from tests.helpers import WorkspaceCase
from tests.test_leads import event
from localauthor.errors import ConflictError, PolicyError
from localauthor.foundation.leads import LeadService
from localauthor.lead_relay import RelayQueue, relay_handler, sync_once, RelayTransport


class LeadRelayTests(WorkspaceCase):
    def setUp(self):
        super().setUp();self.queue_id = 'a'*32
        self.queue = RelayQueue(self.root/'relay.sqlite3', self.queue_id)
        self.write_key, self.read_key = 'w'*40, 'r'*40
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), relay_handler(self.queue, self.write_key, self.read_key))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True);self.thread.start()
        self.leads = LeadService(self.store, None)
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();super().tearDown()
    def http(self, path, body=None, key=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        headers = {'Content-Type':'application/json'}
        if key:headers['Authorization'] = 'Bearer '+key
        connection.request('POST' if body is not None else 'GET', path, json.dumps(body) if body is not None else None, headers)
        response = connection.getresponse();raw = response.read();connection.close();return response.status, json.loads(raw)
    def transport(self, fail_ack=False):
        outer = self
        class Transport:
            def call(self, path, body=None):
                if fail_ack and path=='/ack':raise OSError('Fixture disconnect before receipt')
                status, result = outer.http(path, body, outer.read_key)
                if status!=200:raise PolicyError('Fixture HTTP rejected')
                return result
        return Transport()
    def test_read_write_keys_are_separate_and_secret_is_not_returned(self):
        self.assertEqual(self.http('/events', event())[0], 401)
        self.assertEqual(self.http('/events', event(), self.read_key)[0], 401)
        self.assertEqual(self.http('/pending', key=self.write_key)[0], 401)
        self.assertEqual(self.http('/events', event(), self.write_key)[0], 200)
        data = self.http('/pending', key=self.read_key)[1]
        self.assertNotIn(self.write_key, json.dumps(data));self.assertNotIn(self.read_key, json.dumps(data))
    def test_repeated_event_payload_and_wrong_ack_cannot_overwrite(self):
        self.assertEqual(self.http('/events', event(), self.write_key)[0], 200)
        self.assertTrue(self.http('/events', event(), self.write_key)[1]['deduplicated'])
        self.assertEqual(self.http('/events', event(message='changed'), self.write_key)[0], 409)
        self.assertEqual(self.http('/ack', {'source':'website','event_id':'test-001','digest':'0'*64}, self.read_key)[0], 409)
        self.assertEqual(len(self.queue.pending()['events']), 1)
    def test_crash_after_local_commit_retries_without_duplicate_or_lost_event(self):
        self.http('/events', event(), self.write_key)
        with self.assertRaises(OSError):sync_once(self.leads, self.project['id'], self.queue_id, self.transport(True))
        self.assertEqual(len(self.leads.list(self.project['id'])['items']), 1)
        self.assertEqual(len(self.queue.pending()['events']), 1)
        result = sync_once(self.leads, self.project['id'], self.queue_id, self.transport())
        self.assertTrue(result['receipts'][0]['deduplicated']);self.assertEqual(len(self.queue.pending()['events']), 0)
        self.assertEqual(len(self.leads.list(self.project['id'])['items']), 1)
    def test_queue_identity_and_project_binding_prevent_retargeting(self):
        with self.assertRaises(PolicyError):sync_once(self.leads, self.project['id'], 'b'*32, self.transport())
        sync_once(self.leads, self.project['id'], self.queue_id, self.transport())
        folder = self.root/'another';folder.mkdir();other = self.store.add_project('Outro', str(folder))['id']
        with self.assertRaises(ConflictError):sync_once(self.leads, other, self.queue_id, self.transport())
        with self.assertRaises(ConflictError):RelayQueue(self.root/'relay.sqlite3', 'b'*32)
    def test_payload_validation_prevents_ack_and_contact_permission_forgery(self):
        bad = event(source='research', permission='marketing_opt_in', source_url='https://example.com/')
        self.assertEqual(self.http('/events', bad, self.write_key)[0], 400)
        class Corrupt:
            def call(self, path, body=None):return {'queue_id':'a'*32,'events':[{'event':event(),'digest':'0'*64}]}
        with self.assertRaises(PolicyError):sync_once(self.leads, self.project['id'], self.queue_id, Corrupt())
        self.assertEqual(len(self.leads.list(self.project['id'])['items']), 0)
    def test_production_transport_requires_public_https_and_strong_keys(self):
        for url in ('http://example.com/', 'https://127.0.0.1/', 'https://localhost/', 'https://example.com/?secret=1', 'https://example.com/path'):
            with self.assertRaises(PolicyError):RelayTransport(url, 'r'*40)
        with self.assertRaises(PolicyError):RelayTransport('https://example.com/', 'weak')
        with self.assertRaises(PolicyError):relay_handler(self.queue, 'x'*40, 'x'*40)
    def test_restart_preserves_pending_events(self):
        self.queue.put(event());reopened = RelayQueue(self.root/'relay.sqlite3', self.queue_id)
        self.assertEqual(reopened.pending(), self.queue.pending())
