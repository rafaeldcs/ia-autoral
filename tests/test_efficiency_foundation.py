"""Lifecycle/profile integration contracts with explicit non-model fixtures."""
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from localauthor.errors import PolicyError
from localauthor.foundation.models import ModelSpec, register_model
from localauthor.foundation.runtime import TextRuntime
from localauthor.foundation.service import FoundationService
from localauthor.foundation.__main__ import main as foundation_cli
from localauthor.efficiency.__main__ import self_check


class EfficiencyFoundationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home"
        self.events = []
        for kind in ("text", "image"):
            folder = self.root / kind
            folder.mkdir()
            (folder / "config.json").write_text('{"model_type":"test_double"}', encoding="utf-8")
            (folder / "model.safetensors").write_bytes(b"not-real-weights")
            register_model(folder, self.manifest(kind), model_id="test-double", revision="fixture",
                           license="test-fixture", reviewed_by="tests", capability=kind)
        self.service = FoundationService(self.home, text_factory=self.factory, image_factory=self.factory)
        self.addCleanup(self.service.unload)

    def manifest(self, kind):
        return self.home / "foundation" / f"{kind}-model.json"

    def factory(self, spec):
        self.events.append("load:" + spec.capability)
        return SimpleNamespace(spec=spec, close=lambda: self.events.append("close:" + spec.capability))

    def test_switch_releases_previous_before_allocating(self):
        self.service._engine("text")
        self.service._engine("image")
        self.assertEqual(self.events, ["load:text", "close:text", "load:image"])
        status = self.service.status()
        self.assertFalse(status["capabilities"]["text"]["loaded"])
        self.assertTrue(status["capabilities"]["image"]["loaded"])
        self.assertEqual(status["residency_policy"], "single_model")

    def test_repeated_model_reuses_instance(self):
        first = self.service._engine("text")[1]
        self.assertIs(self.service._engine("text")[1], first)
        self.assertEqual(self.events, ["load:text"])

    def test_explicit_unload_is_idempotent(self):
        self.service._engine("text")
        self.service.unload(); self.service.unload()
        self.assertEqual(self.events, ["load:text", "close:text"])
        self.assertFalse(self.service.status()["capabilities"]["text"]["loaded"])

    def test_invalid_candidate_does_not_evict_valid_model(self):
        original = self.service._engine("text")[1]
        (self.root / "image" / "model.safetensors").write_bytes(b"tampered")
        with self.assertRaises(PolicyError):
            self.service._engine("image")
        self.assertIs(self.service._engine("text")[1], original)
        self.assertEqual(self.events, ["load:text"])

    def test_factory_failure_leaves_no_old_model_loaded(self):
        self.service._engine("text")
        self.service.factories["image"] = Mock(side_effect=PolicyError("fixture"))
        with self.assertRaises(PolicyError): self.service._engine("image")
        self.assertEqual(self.events, ["load:text", "close:text"])
        self.assertFalse(any(value["loaded"] for value in self.service.status()["capabilities"].values()))

    def test_cancellation_during_loading_disposes_candidate(self):
        cancel = threading.Event()
        def factory(spec):
            engine = self.factory(spec)
            cancel.set()
            return engine
        self.service.factories["text"] = factory
        with self.assertRaises(PolicyError): self.service._engine("text", cancel)
        self.assertEqual(self.events, ["load:text", "close:text"])
        self.assertFalse(self.service.status()["capabilities"]["text"]["loaded"])

    def test_changes_during_loading_dispose_candidate(self):
        def factory(spec):
            engine = self.factory(spec)
            (spec.directory / "model.safetensors").write_bytes(b"changed-during-load")
            return engine
        self.service.factories["text"] = factory
        with self.assertRaises(PolicyError): self.service._engine("text")
        self.assertEqual(self.events, ["load:text", "close:text"])

    def test_unload_failure_blocks_next_allocation(self):
        engine = self.service._engine("text")[1]
        engine.close = Mock(side_effect=RuntimeError("fixture close failure"))
        replacement = Mock()
        self.service.factories["image"] = replacement
        with self.assertRaises(PolicyError): self.service._engine("image")
        with self.assertRaises(PolicyError): self.service._engine("image")
        replacement.assert_not_called()
        self.assertTrue(self.service.status()["unload_failed"])
        engine.close = Mock()

    def test_cached_model_mutation_releases_and_refuses(self):
        self.service._engine("text")
        (self.root / "text" / "model.safetensors").write_bytes(b"changed-size")
        with self.assertRaises(PolicyError): self.service._engine("text")
        self.assertEqual(self.events, ["load:text", "close:text"])

    def test_original_manifest_profile_defaults(self):
        path = self.manifest("text")
        data = json.loads(path.read_text(encoding="utf-8"))
        data.pop("enable_thinking"); data.pop("generation_seconds")
        path.write_text(json.dumps(data), encoding="utf-8")
        spec = ModelSpec.load(path, "text")
        self.assertFalse(spec.enable_thinking)
        self.assertEqual(spec.generation_seconds, 300)

    def test_profile_types_and_ranges_fail_closed(self):
        path = self.manifest("text")
        original = json.loads(path.read_text(encoding="utf-8"))
        for change in ({"enable_thinking": 1}, {"generation_seconds": True},
                       {"generation_seconds": 0}, {"generation_seconds": 3601}):
            path.write_text(json.dumps({**original, **change}), encoding="utf-8")
            with self.subTest(change=change), self.assertRaises(PolicyError):
                ModelSpec.load(path, "text")

    def test_image_does_not_accept_text_reasoning_flag(self):
        path = self.manifest("image")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["enable_thinking"] = True
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(PolicyError): ModelSpec.load(path, "image")

    def test_count_and_generation_template_use_same_profile(self):
        runtime = TextRuntime.__new__(TextRuntime)
        runtime.spec = replace(ModelSpec.load(self.manifest("text"), "text"), enable_thinking=True)
        runtime.model = object()
        runtime.tokenizer = Mock()
        runtime.tokenizer.apply_chat_template.return_value = [1, 2, 3]
        messages = [{"role": "user", "content": "teste"}]
        self.assertEqual(runtime.count(messages), 3)
        runtime._template(messages, return_tensors="pt", return_dict=True)
        for call in runtime.tokenizer.apply_chat_template.call_args_list:
            self.assertTrue(call.kwargs["enable_thinking"])
            self.assertTrue(call.kwargs["add_generation_prompt"])
        runtime.model = None
        with self.assertRaises(PolicyError): runtime.count(messages)

    def test_cli_registers_explicit_profile_without_downloads(self):
        candidate_home = self.root / "candidate-home"
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = foundation_cli(["--home", str(candidate_home), "register-model", "text",
                str(self.root / "text"), "--model-id", "test-double", "--revision", "fixture",
                "--license", "test-fixture", "--reviewed-by", "tests", "--enable-thinking",
                "--generation-seconds", "120"])
        self.assertEqual(code, 0)
        spec = ModelSpec.load(candidate_home / "foundation" / "text-model.json", "text")
        self.assertTrue(spec.enable_thinking)
        self.assertEqual(spec.generation_seconds, 120)

    def test_self_check_is_labeled_synthetic_and_preserves_results(self):
        result = self_check()
        self.assertTrue(result["equal_outputs"])
        self.assertFalse(result["nemotron_executed"])
        self.assertFalse(result["weights_trained"])
        self.assertEqual(result["results"]["uncached"]["read_bytes"], 393216)
        self.assertEqual(result["results"]["cached"]["read_bytes"], 24576)
        self.assertFalse(result["results"]["cached"]["physical_disk_io_measured"])

    def test_close_failure_blocks_future_allocation(self):
        engine = self.service._engine('text')[1]
        engine.close = Mock(side_effect=RuntimeError('fixture close failure'))
        with self.assertRaises(PolicyError):
            self.service.close()
        replacement = Mock()
        self.service.factories['image'] = replacement
        with self.assertRaises(PolicyError):
            self.service._engine('image')
        replacement.assert_not_called()
        self.assertTrue(self.service.status()['unload_failed'])
        engine.close = Mock()

    def test_merged_model_profile_preserves_backend_provenance(self):
        path = self.manifest('text')
        data = json.loads(path.read_text(encoding='utf-8'))
        data['enable_thinking'] = True
        data['generation_seconds'] = 120
        path.write_text(json.dumps(data), encoding='utf-8')
        spec = ModelSpec.load(path, 'text')
        self.assertTrue(spec.enable_thinking)
        self.assertEqual(spec.generation_seconds, 120)
        self.assertEqual(spec.backend, 'transformers')
        self.assertEqual(spec.derivation, {})
        self.assertEqual(spec.runtime_profile, {})
        self.assertFalse(spec.provenance()['derived_checkpoint'])



if __name__ == "__main__":
    unittest.main()
