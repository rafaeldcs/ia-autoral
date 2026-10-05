"""Fail-closed Docker bridge doubles; no assertion of real model competence."""
import importlib.util
import json
import io
from pathlib import Path
import queue
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from localauthor.errors import PolicyError
from localauthor.foundation.gguf_bridge import ROOT, verify_sandbox, DockerGgufRuntime
from localauthor.foundation.models import ModelSpec, read_object, register_model, write_new

loader = importlib.util.spec_from_file_location("gguf_rpc", ROOT / "scripts/foundation-gguf-rpc.py")
worker = importlib.util.module_from_spec(loader)
loader.loader.exec_module(worker)


class GgufBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.weights = self.root / "weights"; self.weights.mkdir()
        (self.weights / "fixture.gguf").write_bytes(b"fixture-not-real-model")
        (self.weights / "LICENSE").write_text("fixture license")
        self.profile = {"image_id": "sha256:" + "a" * 64, "volume": "localauthor-fixture", "reasoning_budget": 32}
        self.manifest = self.root / "manifest.json"
        register_model(self.weights, self.manifest, model_id="fixture", revision="fixture", license="fixture",
            reviewed_by="fixture", capability="text", device="cuda", context_tokens=4096, output_tokens=192,
            backend="gguf-docker", runtime_profile=self.profile)
        self.model = ModelSpec.load(self.manifest, "text")

    def sandbox(self):
        return {"Image": self.profile["image_id"], "Config": {"User": "10001:10001"},
            "HostConfig": {"NetworkMode": "none", "ReadonlyRootfs": True, "Privileged": False,
                "CapDrop": ["ALL"], "SecurityOpt": ["no-new-privileges"], "Memory": 6 * 1024 ** 3,
                "MemorySwap": 6 * 1024 ** 3, "NanoCpus": 4_000_000_000, "PidsLimit": 128,
                "PortBindings": {}, "Tmpfs": {"/tmp": "rw,nosuid,nodev,size=256m"},
                "DeviceRequests": [{"Count": -1, "Capabilities": [["gpu"]]}]},
            "Mounts": [{"Destination": "/workspace", "Source": str(ROOT), "Type": "bind", "RW": False},
                       {"Destination": "/weights", "Name": self.profile["volume"], "Type": "volume", "RW": False}]}

    def test_gguf_inventory_hash_and_backend_are_explicit(self):
        self.model.verify()
        self.assertEqual(self.model.provenance()["backend"], "gguf-docker")
        (self.weights / "fixture.gguf").write_bytes(b"changed")
        with self.assertRaises(PolicyError): self.model.verify()

    def test_invalid_backend_or_runtime_profile_cannot_register(self):
        original = read_object(self.manifest)
        for changes in ({"backend": "remote"}, {"runtime_profile": {**self.profile, "image_id": "latest"}},
                        {"runtime_profile": {**self.profile, "volume": "../../secret"}},
                        {"runtime_profile": {**self.profile, "reasoning_budget": True}},
                        {"capability": "image"}, {"device": "auto"}, {"reviewed_local_code": True}):
            with self.subTest(changes=changes):
                # Unique explicit fixture files, not executable model artifacts.
                path = self.root / ("bad" + str(len(list(self.root.glob('bad*.json')))) + ".json")
                write_new(path, {**original, **changes})
                with self.assertRaises(PolicyError): ModelSpec.load(path, changes.get("capability", "text"))

    def test_mixed_weights_and_checkpoint_python_are_rejected(self):
        for name in ("second.gguf", "model.safetensors", "model.py"):
            with self.subTest(name=name):
                path = self.weights / name; path.write_bytes(b"fixture")
                with self.assertRaises(PolicyError):
                    register_model(self.weights, self.root / (name + ".json"), model_id="fixture", revision="fixture",
                        license="fixture", reviewed_by="fixture", capability="text", backend="gguf-docker",
                        device="cuda", runtime_profile=self.profile)
                path.unlink()

    def test_sandbox_rejects_network_rw_credentials_and_infrastructure_changes(self):
        verify_sandbox(self.sandbox(), self.model)
        for key, value in (("NetworkMode", "bridge"), ("ReadonlyRootfs", False), ("Privileged", True),
                           ("Memory", 0), ("NanoCpus", 0), ("PidsLimit", 0), ("DeviceRequests", []),
                           ("PortBindings", {"8080/tcp": []})):
            info = self.sandbox(); info["HostConfig"][key] = value
            with self.subTest(key=key), self.assertRaises(PolicyError): verify_sandbox(info, self.model)
        for change in ("rw", "extra", "image", "source"):
            info = self.sandbox()
            if change == "rw": info["Mounts"][1]["RW"] = True
            if change == "extra": info["Mounts"].append({"Destination": "/secrets", "RW": False})
            if change == "image": info["Image"] = "sha256:" + "b" * 64
            if change == "source": info["Mounts"][0]["Source"] = "/other"
            with self.subTest(change=change), self.assertRaises(PolicyError): verify_sandbox(info, self.model)

    def test_ipc_cannot_supply_shell_route_or_file_operations(self):
        value = {"id": "a" * 32, "operation": "count", "messages": [{"role": "user", "content": "fixture"}]}
        self.assertEqual(worker.validate_request(json.dumps(value).encode() + b"\n"), value)
        for changes in ({"operation": "shell"}, {"operation": "/health"}, {"id": "../outside"}, {"path": "/secret"}):
            with self.subTest(changes=changes), self.assertRaises(PolicyError):
                worker.validate_request(json.dumps({**value, **changes}).encode() + b"\n")
        with self.assertRaises(PolicyError): worker.validate_request(b"x" * 128001)

    def test_invalid_inspection_never_starts_container_or_host_inference(self):
        bad = self.sandbox(); bad["HostConfig"]["NetworkMode"] = "bridge"
        with patch.object(DockerGgufRuntime, "docker", side_effect=[b"a" * 64, json.dumps([bad]).encode()]), \
             patch.object(DockerGgufRuntime, "close") as close, \
             patch("localauthor.foundation.gguf_bridge.subprocess.Popen") as start:
            with self.assertRaises(PolicyError): DockerGgufRuntime(self.model, diagnostics=self.root / "diagnostics")
            start.assert_not_called(); close.assert_called_once()

    def engine(self):
        engine = object.__new__(DockerGgufRuntime)
        engine.closed = False; engine.lock = threading.RLock(); engine.frames = queue.Queue()
        engine.process = Mock(); engine.process.stdin = io.BytesIO(); engine.close = Mock()
        return engine

    def test_precancel_sends_nothing_and_closes_owned_runtime(self):
        engine = self.engine(); event = threading.Event(); event.set()
        with self.assertRaises(PolicyError): engine.generate([], event)
        self.assertEqual(engine.process.stdin.getvalue(), b""); engine.close.assert_called_once()

    def test_mismatched_response_and_boolean_count_fail_closed(self):
        engine = self.engine(); engine.frames.put({"id": "wrong", "result": "fixture"})
        with self.assertRaises(PolicyError): engine.count([])
        engine.close.assert_called_once()
        engine = self.engine(); engine.rpc = Mock(return_value=True)
        with self.assertRaises(PolicyError): engine.count([])
        engine.close.assert_called_once()

    def test_logging_failure_does_not_prevent_stop_and_failed_stop_can_be_retried(self):
        engine = object.__new__(DockerGgufRuntime)
        engine.closed = False; engine.stopped = False; engine.container = "a" * 64; engine.process = None
        engine.diagnostics = self.root; engine.diagnostic_snapshot = None
        engine.docker = Mock(side_effect=[PolicyError("fixture cp failed"), PolicyError("fixture stop failed")])
        with self.assertRaises(PolicyError): engine.close()
        self.assertTrue(engine.closed); self.assertFalse(engine.stopped)
        self.assertFalse(engine.diagnostic_snapshot["captured"])
        engine.docker = Mock(side_effect=[b"fixture stopped", json.dumps([{"State": {"Running": False}}]).encode()])
        engine.close()
        self.assertTrue(engine.stopped)
        self.assertEqual(engine.docker.call_args_list[0].args[0], ["stop", "--time", "5", "a" * 64])
