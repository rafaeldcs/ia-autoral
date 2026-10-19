import http.client
import json
from pathlib import Path
import threading
from tests.helpers import WorkspaceCase
from tests.test_leads import context, event
from localauthor.application import Application
from localauthor.server import create_server


class LeadHttpTests(WorkspaceCase):
    def setUp(self):
        super().setUp();self.app = Application(self.settings)
        self.server = create_server(self.app, Path(__file__).resolve().parents[1]/'ui', port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True);self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.app.close();super().tearDown()
    def request(self, path, body=None, auth=True):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        headers = {'Content-Type':'application/json'}
        if auth:headers['Authorization'] = 'Bearer '+self.settings.token
        connection.request('POST' if body is not None else 'GET', path, json.dumps(body) if body is not None else None, headers)
        response = connection.getresponse();raw = response.read();connection.close()
        return response.status, raw, response.getheader('Content-Security-Policy')
    def test_authenticated_ingress_and_static_csp(self):
        for route in ('/api/leads', '/api/leads/context', '/api/leads/item'):
            self.assertEqual(self.request(route+'?project_id='+self.project['id'], auth=False)[0], 401)
        self.assertEqual(self.request('/api/leads/ingest', {'project_id':self.project['id'],'event':event()}, auth=False)[0], 401)
        for path in ('/leads','/leads.js','/leads.css'):
            status, _, csp = self.request(path, auth=False);self.assertEqual(status, 200);self.assertIn("script-src 'self'", csp)
    def test_ingress_strict_payload_and_blocked_contact_before_job_queue(self):
        pid = self.project['id'];self.app.leads.save_context(pid, '', context())
        status, raw, _ = self.request('/api/leads/ingest', {'project_id':pid,'event':event(opt_out=True)})
        self.assertEqual(status, 200);item = self.app.leads.get(pid, json.loads(raw)['id'])
        body = {'project_id':pid,'id':item['id'],'version':item['version'],'context_digest':self.app.leads.context(pid)['digest']}
        self.assertEqual(self.request('/api/leads/qualify', body)[0], 400)
        self.assertEqual(self.request('/api/leads/qualify', {**body,'token':'never-queue'})[0], 400)
        self.assertFalse(self.app.jobs.list())
    def test_conflicts_are_409_and_project_is_required(self):
        pid = self.project['id'];self.app.leads.ingest(pid, event())
        status, _, _ = self.request('/api/leads/ingest', {'project_id':pid,'event':event(message='different')})
        self.assertEqual(status, 409);self.assertEqual(self.request('/api/leads')[0], 400)
