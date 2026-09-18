import http.client
import json
import threading
import zipfile
from pathlib import Path
from localauthor.application import Application
from localauthor.server import create_server
from localauthor.jobs import JobQueue
from localauthor.backup import backup_home, restore_home
from localauthor.errors import PolicyError
from localauthor.util import utcnow
from tests.helpers import WorkspaceCase, wait_until


class RuntimeTests(WorkspaceCase):
    def test_job_completes_and_result_persists(self):
        queue = JobQueue(self.store, {"sum": lambda p,c: {"sum": p["a"]+p["b"]}})
        queue.start()
        try:
            job = queue.submit("sum", {"a": 2, "b": 3})
            wait_until(lambda: queue.get(job["id"])["state"] == "completed")
            self.assertEqual(queue.get(job["id"])["result"]["sum"], 5)
        finally: queue.close()

    def test_cancel_running_job(self):
        entered = threading.Event()
        def work(p,c):
            entered.set(); c.wait(3); return {"cancelled": c.is_set()}
        queue = JobQueue(self.store, {"work": work}); queue.start()
        try:
            job = queue.submit("work", {})
            self.assertTrue(entered.wait(2))
            queue.cancel(job["id"])
            wait_until(lambda: queue.get(job["id"])["state"] == "cancelled")
        finally: queue.close()

    def test_restart_marks_running_job_interrupted(self):
        now = utcnow()
        with self.store.connect() as db:
            db.execute("INSERT INTO jobs VALUES('abc','work','{}','running',NULL,NULL,?,?)", (now,now))
        queue = JobQueue(self.store, {"work":lambda p,c:None})
        self.assertEqual(queue.get("abc")["state"], "interrupted")

    def test_unknown_job_not_queued(self):
        queue = JobQueue(self.store, {})
        with self.assertRaises(PolicyError): queue.submit("shell", {"command":"anything"})

    def test_full_backup_restore_regenerates_token(self):
        self.store.ingest("global", "x", "Memory", "Persistent knowledge")
        token = self.settings.token
        dest = self.root/"backup.zip"
        backup_home(self.settings, dest)
        target = self.root/"restored"
        result = restore_home(dest, target)
        from localauthor.config import Settings
        from localauthor.store import Store
        settings = Settings.load(target)
        self.assertNotEqual(token, settings.token)
        self.assertTrue(settings.offline)
        self.assertEqual(len(Store(target/"memory.sqlite3").search("Persistent")), 1)

    def test_backup_rejects_running_server(self):
        (self.settings.home/"server.lock").write_text("123")
        with self.assertRaises(PolicyError): backup_home(self.settings, self.root/"backup.zip")

    def test_restore_rejects_zip_slip(self):
        file = self.root/"malicious.zip"
        with zipfile.ZipFile(file,"w") as z:
            z.writestr("../escape.txt", "no")
            z.writestr("BACKUP_MANIFEST.json", "{}")
        with self.assertRaises(PolicyError): restore_home(file, self.root/"restore")
        self.assertFalse((self.root/"escape.txt").exists())

    def test_restore_does_not_overwrite_existing_data(self):
        self.settings.home.mkdir(exist_ok=True)
        with self.assertRaises(PolicyError): restore_home(self.root/"nonexistent.zip", self.settings.home)


class HttpTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.app = Application(self.settings)
        self.server = create_server(self.app, Path(__file__).resolve().parents[1]/"ui", port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.app.close()
        super().tearDown()
    def request(self, method, path, data=None, auth=True, extra=None):
        headers = {"Content-Type":"application/json"}
        if auth: headers["Authorization"] = "Bearer "+self.settings.token
        if extra: headers.update(extra)
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            conn.request(method, path, body=json.dumps(data) if data is not None else None, headers=headers)
            response = conn.getresponse()
            raw = response.read()
            content = json.loads(raw) if "application/json" in response.getheader("Content-Type", "") else raw
            return response.status, dict(response.getheaders()), content
        finally: conn.close()

    def test_api_requires_token(self):
        self.assertEqual(self.request("GET", "/api/health", auth=False)[0], 401)

    def test_browser_endpoints_require_auth_and_explicit_network_permission(self):
        for path in ('/api/browser/sessions','/api/browser/session','/api/browser/image'):
            self.assertEqual(self.request('GET',path,auth=False)[0],401)
        self.assertEqual(self.request('POST','/api/browser/start',{'project_id':self.project['id'],
                         'url':'https://example.org/'})[0],400)
        status, _, result=self.request('GET','/api/browser/sessions?project_id='+self.project['id'])
        self.assertEqual((status,result),(200,[]))

    def test_health_is_explicit_about_model(self):
        status, headers, data = self.request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertFalse(data["model_qualified"])
        self.assertTrue(data["offline"])

    def test_cross_origin_even_with_token_rejected(self):
        status, _, _ = self.request("POST", "/api/import", {"title":"x","content":"y"}, extra={"Origin":"https://evil.test"})
        self.assertEqual(status, 400)

    def test_dns_rebinding_host_rejected(self):
        self.assertEqual(self.request("GET", "/api/health", extra={"Host":"evil.test"})[0], 400)

    def test_options_cannot_enable_cors(self):
        status, headers, _ = self.request("OPTIONS", "/api/health", auth=False)
        self.assertEqual(status, 403)
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_static_ui_has_csp(self):
        status, headers, body = self.request("GET", "/", auth=False)
        self.assertEqual(status, 200)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertIn(b"LocalAuthor", body)

    def test_http_ingest_then_retrieve(self):
        self.assertEqual(self.request("POST", "/api/import", {"title":"Minha fonte", "content":"Regra de estoque disponível"})[0], 200)
        status, _, data = self.request("POST", "/api/consult", {"query":"estoque"})
        self.assertEqual(status, 200)
        self.assertEqual(len(data["evidence"]), 1)

    def test_http_path_traversal_rejected(self):
        task = self.app.tasks.create(self.project["id"], "Review")
        status, _, _ = self.request("GET", "/api/tasks/"+task["id"]+"/file?path=../secrets.txt")
        self.assertEqual(status, 400)

    def test_train_requires_explicit_dataset_approval(self):
        status, _, _ = self.request("POST", "/api/jobs/train", {"manifest":"x/manifest.json"})
        self.assertEqual(status, 400)

    def test_ui_does_not_use_unsafe_html_insertion(self):
        script = (Path(__file__).resolve().parents[1]/"ui"/"app.js").read_text()
        for dangerous in ["innerHTML", "document.write", "eval("]:
            self.assertNotIn(dangerous, script)
