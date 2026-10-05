"""GGUF lab control contracts using explicit doubles; not model qualification."""
from pathlib import Path
import threading
import unittest
from unittest.mock import patch, Mock

from localauthor.errors import PolicyError
from localauthor.foundation.gguf_lab import GgufLabRuntime, completion, valid_profile, verify_gpu_offload


class GgufLabTests(unittest.TestCase):
    def test_device_visibility_and_partial_offload_do_not_prove_gpu_inference(self):
        for log in ("CUDA0: RTX2060", "CUDA0: RTX2060 offloaded 2/37 layers to GPU", "offloaded 37/37 layers to GPU", "CUDA0 offloaded 0/0 layers to GPU"):
            with self.subTest(log=log), self.assertRaises(PolicyError): verify_gpu_offload(log)
        self.assertEqual(verify_gpu_offload("CUDA0 offloaded 37/37 layers to GPU")["offloaded_layers"], 37)
    def test_cannot_start_inference_outside_verified_sandbox(self):
        with patch("localauthor.foundation.gguf_lab.require_isolated_process", side_effect=PolicyError("fixture blocked")), \
             patch("localauthor.foundation.gguf_lab.digest") as hash_file:
            with self.assertRaises(PolicyError): GgufLabRuntime(Path("fixture.gguf"), "a" * 64, Path("fixture.log"))
            hash_file.assert_not_called()

    def test_rejects_unbounded_or_boolean_generation_profiles(self):
        valid_profile(2048, 192, 4)
        for profile in ((True, 192, 4), (2048, 2048, 4), (8193, 192, 4), (2048, 192, 5), (2048, 0, 1)):
            with self.subTest(profile=profile), self.assertRaises(PolicyError): valid_profile(*profile)

    def test_keeps_length_stop_distinct_and_discards_no_reasoning_as_answer(self):
        for reason, truncated in (("stop", False), ("length", True)):
            self.assertEqual(completion({"choices": [{"message": {"content": "answer", "reasoning_content": "fixture internal"},
                                                     "finish_reason": reason}]}), ("answer", truncated))
        with self.assertRaises(PolicyError): completion({"choices": [{"message": {"content": "", "reasoning_content": "only reasoning"}, "finish_reason": "stop"}]})

    def test_malformed_and_multiple_completions_never_pass(self):
        for value in ({}, {"choices": []}, {"choices": [None]}, {"choices": [{"message": "invalid"}]},
                      {"choices": [{"message": {"content": "yes"}, "finish_reason": "tool_calls"}]},
                      {"choices": [{}, {}]}):
            with self.subTest(value=value), self.assertRaises(PolicyError): completion(value)

    def engine(self):
        runtime = object.__new__(GgufLabRuntime)
        runtime.context = 256; runtime.output = 32
        return runtime

    def test_context_overflow_does_not_call_generation(self):
        runtime = self.engine(); runtime.count = Mock(return_value=225); runtime.request = Mock()
        with self.assertRaises(PolicyError): runtime.generate([{"role": "user", "content": "fixture"}])
        runtime.request.assert_not_called()

    def test_pre_cancel_never_tokenizes_or_generates(self):
        runtime = self.engine(); runtime.count = Mock(); runtime.request = Mock()
        event = threading.Event(); event.set()
        with self.assertRaises(PolicyError): runtime.generate([], event)
        runtime.count.assert_not_called(); runtime.request.assert_not_called()

    def test_count_requires_real_template_and_integer_tokens(self):
        runtime = self.engine()
        runtime.request = Mock(side_effect=[{"prompt": "fixture"}, {"tokens": [1, 2, 3]}])
        self.assertEqual(runtime.count([{"role": "user", "content": "fixture"}]), 3)
        runtime.request = Mock(side_effect=[{"prompt": "fixture"}, {"tokens": [True]}])
        with self.assertRaises(PolicyError): runtime.count([{"role": "user", "content": "fixture"}])
        runtime.request = Mock(return_value={})
        with self.assertRaises(PolicyError): runtime.count([{"role": "user", "content": "fixture"}])

    def test_transport_timeout_does_not_turn_into_busy_retry_until_deadline(self):
        runtime = self.engine()
        runtime.url = "http://127.0.0.1:1"
        runtime.key = "fixture-not-a-real-token"
        runtime.opener = Mock()
        runtime.opener.open.side_effect = TimeoutError("fixture transport timeout")
        runtime.close = Mock()
        with self.assertRaises(TimeoutError): runtime.request("/health", None, seconds=2)
        runtime.close.assert_not_called()
