from unittest.mock import Mock
from tests.helpers import WorkspaceCase
from tests.test_leads import event
from localauthor.errors import PolicyError
from localauthor.foundation.leads import LeadService
from localauthor.lead_connections import LeadConnections
from localauthor.lead_relay import RelayQueue


class LeadConnectionTests(WorkspaceCase):
    def setUp(self):
        super().setUp();self.queue = RelayQueue(self.root/'relay.sqlite3', 'a'*32)
        self.queue.put(event());self.model = Mock();self.vault = Mock()
        self.vault.seal.return_value = 'encrypted-fixture';self.vault.open.return_value = 'r'*40
        self.service = LeadService(self.store, self.model)
        outer = self
        class Transport:
            def call(self, path, body=None):return outer.queue.pending() if path=='/pending' else outer.queue.ack(**body)
        self.connection = LeadConnections(self.store, self.service, self.settings, vault=self.vault,
                                          transport_factory=lambda url, key: Transport())
    def tearDown(self):self.connection.close();super().tearDown()
    def save(self):return self.connection.save(self.project['id'], 'https://example.com/', 'a'*32, 'r'*40, True)
    def test_secrets_never_returned_or_sent_to_jobs_and_offline_prevents_transport(self):
        result = self.save();self.assertNotIn('encrypted-fixture', str(result));self.assertNotIn('r'*40, str(result))
        result = self.connection.sync(self.project['id']);self.assertEqual(result['connection']['state'], 'offline')
        self.vault.open.assert_not_called();self.assertEqual(len(self.service.list(self.project['id'])['items']), 0)
    def test_enabled_sync_persists_and_pause_prevents_further_reads(self):
        self.settings.offline = False;self.save()
        result = self.connection.sync(self.project['id']);self.assertEqual(result['connection']['state'], 'ok')
        self.assertEqual(result['connection']['received'], 1)
        self.assertEqual(len(self.service.list(self.project['id'])['items']), 1)
        self.connection.disable(self.project['id'])
        with self.assertRaises(PolicyError):self.connection.sync(self.project['id'])
    def test_transport_failure_records_only_sanitized_status(self):
        self.settings.offline = False;self.save()
        self.connection.transport_factory = Mock(side_effect=RuntimeError('secret response body'))
        result = self.connection.sync(self.project['id'])
        self.assertEqual(result['connection']['state'], 'error');self.assertNotIn('secret response body', str(result))
    def test_worker_lifecycle_stops_cooperatively_without_model_execution(self):
        self.connection.start();self.connection.close()
        self.assertFalse(self.connection.thread.is_alive());self.model.answer.assert_not_called()
