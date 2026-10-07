"""Process/validation contracts. No real checkpoint or GPU is used by this suite."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from localauthor.errors import PolicyError
from localauthor.foundation.smoke import _worker, run_smoke


def fixture_report(connection, home, kind):
    connection.send_bytes(json.dumps({"schema": 1, "success": True,
                                     "test_double": True}).encode("utf-8"))
    connection.close()


def fixture_hang(connection, home, kind):
    time.sleep(30)


def fixture_invalid(connection, home, kind):
    connection.send_bytes(b'{"schema":1,"success":"true"}')
    connection.close()


class FoundationSmokeTests(unittest.TestCase):
    def test_invalid_arguments_fail_before_start(self):
        for value in (0, -1, True, float("nan"), float("inf"), 3601, "1"):
            with self.subTest(value=value), self.assertRaises(PolicyError):
                run_smoke(Path("."), timeout=value)
        with self.assertRaises(PolicyError): run_smoke(Path("."), "audio")

    def test_spawn_result_and_process_exit_are_both_required(self):
        result = run_smoke(Path("."), timeout=15, _target=fixture_report)
        self.assertTrue(result["success"])
        self.assertTrue(result["test_double"])
        self.assertTrue(result["process_exit_confirmed"])
        self.assertFalse(result["quality_certified"])
        self.assertFalse(result["weights_trained"])

    def test_timeout_terminates_child(self):
        result = run_smoke(Path("."), timeout=0.2, _target=fixture_hang)
        self.assertFalse(result["success"])
        self.assertTrue(result["process_exit_confirmed"])
        self.assertLess(result["elapsed_seconds"], 10)

    def test_invalid_process_protocol_fails(self):
        result = run_smoke(Path("."), timeout=15, _target=fixture_invalid)
        self.assertFalse(result["success"])
        self.assertTrue(result["process_exit_confirmed"])

    def test_missing_checkpoint_is_not_success(self):
        with tempfile.TemporaryDirectory() as home:
            result = run_smoke(Path(home), timeout=15)
        self.assertFalse(result["success"])
        self.assertTrue(result["process_exit_confirmed"])
        self.assertFalse(result["remote_fallback"])

    def test_worker_verifies_before_and_after_and_closes_model(self):
        spec = Mock(context_tokens=4096, output_tokens=32)
        spec.verify.return_value = ("immutable",)
        spec.provenance.return_value = {"model_id": "fixture-not-real"}
        engine = Mock()
        engine.count.return_value = 10
        engine.generate.return_value = ("Test double response.", False)
        channel = Mock()
        with patch("localauthor.foundation.models.ModelSpec.load", return_value=spec), \
             patch("localauthor.foundation.runtime.TextRuntime", return_value=engine):
            _worker(channel, "unused", "text")
        report = json.loads(channel.send_bytes.call_args.args[0])
        self.assertTrue(report["success"])
        self.assertEqual(spec.verify.call_count, 2)
        engine.close.assert_called_once()
        self.assertFalse(report["quality_certified"])
        self.assertFalse(report["network_isolation_verified"])
        self.assertNotIn("Test double response.", json.dumps(report))

    def test_worker_does_not_approve_truncated_response(self):
        spec = Mock(context_tokens=4096, output_tokens=32)
        spec.verify.return_value = ()
        spec.provenance.return_value = {}
        engine = Mock()
        engine.count.return_value = 1
        engine.generate.return_value = ("partial", True)
        channel = Mock()
        with patch("localauthor.foundation.models.ModelSpec.load", return_value=spec), \
             patch("localauthor.foundation.runtime.TextRuntime", return_value=engine):
            _worker(channel, "unused", "text")
        self.assertFalse(json.loads(channel.send_bytes.call_args.args[0])["success"])
        engine.close.assert_called_once()
