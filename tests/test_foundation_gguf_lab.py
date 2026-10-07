"""GGUF lab control contracts using explicit doubles; not model qualification."""
from pathlib import Path
import threading
import unittest
from unittest.mock import patch, Mock

from localauthor.errors import PolicyError
from localauthor.foundation.gguf_lab import GgufLabRuntime, completion, valid_profile, valid_decoding, verify_gpu_offload, private_diagnostic


class GgufLabTests(unittest.TestCase):
    def test_diagnostics_redact_internal_key_before_persistence_and_are_bounded(self):
        key="fixture-not-a-real-key"
        safe=private_diagnostic(("Authorization: Bearer "+key+"\nCUDA0 offloaded 37/37 layers to GPU").encode(),key)
        self.assertNotIn(key.encode(),safe)
        self.assertIn(b"offloaded 37/37",safe)
        with self.assertRaises(PolicyError):private_diagnostic(b"x"*1000001,key)
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
        runtime.template_options = {"enable_thinking": False}
        runtime.json_output = False
        return runtime

    def test_reasoning_cannot_consume_entire_answer_budget_or_be_unbounded(self):
        valid_decoding(1536, 512, True)
        for budget, json_mode in ((True, False), (-1, False), (1025, False), (1536, False), (0, 1)):
            with self.subTest(budget=budget), self.assertRaises(PolicyError): valid_decoding(1536, budget, json_mode)

    def test_thinking_template_count_matches_generation_and_json_contains_no_expected_values(self):
        runtime = self.engine(); runtime.template_options = {"enable_thinking": True}; runtime.json_output = True
        runtime.request = Mock(side_effect=[{"prompt": "fixture thinking"}, {"tokens": [1, 2]},
            {"choices": [{"message": {"content": '{"proposal":"fixture"}', "reasoning_content": "private"}, "finish_reason": "stop"}]}])
        result = runtime.generate([{"role": "user", "content": "fixture"}])
        calls = runtime.request.call_args_list
        self.assertEqual(calls[0].args[1]["chat_template_kwargs"], calls[2].args[1]["chat_template_kwargs"])
        self.assertEqual(calls[2].args[1]["response_format"], {"type": "json_object"})
        self.assertEqual(result, ('{"proposal":"fixture"}', False))

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
