"""Actual threaded queue/SQLite tests; lifecycle doubles do not certify models."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from localauthor.application import Application
from localauthor.errors import PolicyError
from localauthor.jobs import JobQueue


class QueueStore:
    def __init__(self, path):
        self.path = path
        with self.connect() as db:
            db.execute("CREATE TABLE jobs(id TEXT PRIMARY KEY,kind TEXT,payload TEXT,state TEXT,result TEXT,error TEXT,created_at TEXT,updated_at TEXT)")

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()


class ShutdownTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = QueueStore(Path(self.temp.name) / "jobs.sqlite3")

    def queue(self, handler):
        queue = JobQueue(self.store, {"test": handler})
        self.addCleanup(queue.close)
        return queue

    def test_closed_queue_neither_starts_nor_accepts_work(self):
        queue = self.queue(lambda p, c: None)
        self.assertTrue(queue.close())
        self.assertTrue(queue.close())
        with self.assertRaises(PolicyError): queue.start()
        with self.assertRaises(PolicyError): queue.submit("test", {})
        self.assertEqual(queue.list(), [])

    def test_start_is_idempotent(self):
        queue = self.queue(lambda p, c: None)
        queue.start(); queue.start()
        self.assertTrue(queue.close())

    def test_shutdown_cancels_the_active_operation_before_returning(self):
        entered, cancelled = threading.Event(), threading.Event()
        def handler(payload, cancel):
            entered.set()
            if cancel.wait(5): cancelled.set()
            return {"done": True}
        queue = self.queue(handler)
        item = queue.submit("test", {})
        queue.start()
        self.assertTrue(entered.wait(5))
        self.assertTrue(queue.close(5))
        self.assertTrue(cancelled.is_set())
        self.assertEqual(queue.get(item["id"])["state"], "cancelled")

    def test_uncooperative_operation_is_not_reported_stopped(self):
        entered, release = threading.Event(), threading.Event()
        def handler(payload, cancel):
            entered.set(); release.wait(5)
            return {}
        queue = self.queue(handler)
        self.addCleanup(release.set)
        queue.submit("test", {})
        queue.start()
        self.assertTrue(entered.wait(5))
        try:
            self.assertFalse(queue.close(0))
            with self.assertRaises(PolicyError): queue.submit("test", {})
        finally:
            release.set()
        self.assertTrue(queue.close(5))

    def test_pending_work_is_not_started_after_shutdown(self):
        handler = Mock()
        queue = self.queue(handler)
        item = queue.submit("test", {})
        self.assertTrue(queue.close())
        handler.assert_not_called()
        self.assertEqual(queue.get(item["id"])["state"], "queued")

    def test_invalid_timeout_does_not_shutdown_queue(self):
        queue = self.queue(lambda p, c: None)
        for value in (True, -1, float("nan"), float("inf"), 301, "15"):
            with self.subTest(value=value), self.assertRaises(PolicyError): queue.close(value)
        self.assertFalse(queue.stop_event.is_set())

    def application(self):
        app = Application.__new__(Application)
        app.voice = SimpleNamespace(close=Mock())
        app.jobs = SimpleNamespace(close=Mock(return_value=True))
        app.browser = SimpleNamespace(close=Mock())
        app.chat = SimpleNamespace(foundation=SimpleNamespace(unload=Mock()))
        return app

    def test_application_stops_jobs_before_browser_and_models(self):
        app = self.application()
        sequence = []
        app.voice.close.side_effect = lambda: sequence.append("voice")
        app.jobs.close.side_effect = lambda: sequence.append("jobs") or True
        app.browser.close.side_effect = lambda: sequence.append("browser")
        app.chat.foundation.unload.side_effect = lambda: sequence.append("models")
        app.close()
        self.assertEqual(sequence, ["voice", "jobs", "browser", "models"])

    def test_active_voice_prevents_other_resources_from_disposal(self):
        app = self.application()
        app.voice.close.side_effect = PolicyError("Voice runtime still active")
        with self.assertRaises(PolicyError): app.close()
        app.jobs.close.assert_not_called()
        app.browser.close.assert_not_called()
        app.chat.foundation.unload.assert_not_called()

    def test_active_worker_prevents_resource_disposal(self):
        app = self.application()
        app.jobs.close.return_value = False
        with self.assertRaises(PolicyError): app.close()
        app.browser.close.assert_not_called()
        app.chat.foundation.unload.assert_not_called()

    def test_browser_cleanup_failure_still_releases_models(self):
        app = self.application()
        app.browser.close.side_effect = RuntimeError("fixture")
        with self.assertRaises(RuntimeError): app.close()
        app.chat.foundation.unload.assert_called_once()
