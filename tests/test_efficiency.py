"""Synthetic CPU contracts, not Nemotron benchmarks or evidence of training."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import math
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

from localauthor.errors import PolicyError
from localauthor.efficiency.learning_gate import assess_candidate, validate_report
from localauthor.efficiency.moe_reference import routed_swiglu
from localauthor.efficiency.placement import MemoryBudget, Footprint, plan_placement
from localauthor.efficiency.residency import dispose_runtime, release_tensors
from localauthor.efficiency.weight_store import WeightBlock, WeightStore


def sha(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


class WeightStoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / "weights.dat"
        self.path.write_bytes(b"aaaabbbbcccc")
        self.blocks = {key: WeightBlock("weights.dat", i * 4, 4, sha(raw))
                       for i, (key, raw) in enumerate((("a", b"aaaa"), ("b", b"bbbb"), ("c", b"cccc")))}

    def store(self, **kw):
        return WeightStore(self.root, self.blocks, cache_bytes=kw.pop("cache_bytes", 8),
                           max_block_bytes=kw.pop("max_block_bytes", 4), **kw)

    def test_hit_reuses_verified_bytes_without_writing(self):
        before = self.path.read_bytes()
        store = self.store()
        self.assertEqual(store.get("a"), b"aaaa")
        self.assertEqual(store.get("a"), b"aaaa")
        self.assertEqual(store.stats()["read_bytes"], 4)
        self.assertEqual(store.stats()["hits"], 1)
        self.assertEqual(store.stats()["write_bytes"], 0)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(set(p.name for p in self.root.iterdir()), {"weights.dat"})

    def test_no_cache_reads_again(self):
        store = self.store(cache_bytes=0)
        store.get("a"); store.get("a")
        self.assertEqual(store.stats()["read_bytes"], 8)
        self.assertEqual(store.stats()["resident_bytes"], 0)

    def test_lru_is_byte_bounded(self):
        store = self.store()
        for key in ("a", "b", "a", "c", "b"):
            store.get(key)
        self.assertEqual(store.stats()["read_bytes"], 16)
        self.assertEqual(store.stats()["evictions"], 2)
        self.assertEqual(store.stats()["peak_resident_bytes"], 8)

    def test_block_larger_than_cache_is_returned_not_retained(self):
        store = self.store(cache_bytes=3)
        self.assertEqual(store.get("a"), b"aaaa")
        self.assertEqual(store.stats()["resident_bytes"], 0)

    def test_clear_does_not_reset_lifetime_read_budget(self):
        store = self.store(read_budget_bytes=4)
        store.get("a"); store.clear()
        with self.assertRaises(PolicyError):
            store.get("a")
        self.assertEqual(store.stats()["resident_bytes"], 0)

    def test_demand_read_budget_refuses_without_substitution(self):
        store = self.store(read_budget_bytes=4)
        store.get("a")
        with self.assertRaises(PolicyError):
            store.get("b")
        self.assertEqual(store.get("a"), b"aaaa")
        self.assertEqual(store.stats()["read_bytes"], 4)

    def test_prefetch_does_not_evict_demand_data(self):
        store = self.store(cache_bytes=4)
        store.get("a")
        self.assertEqual(store.prefetch(["b", "c"], byte_budget=8), 0)
        store.get("a")
        self.assertEqual(store.stats()["evictions"], 0)
        self.assertEqual(store.stats()["read_bytes"], 4)

    def test_prefetch_deduplicates_and_obeys_both_budgets(self):
        store = self.store(read_budget_bytes=4)
        self.assertEqual(store.prefetch(["a", "a", "b"], byte_budget=8), 4)
        self.assertEqual(store.stats()["read_bytes"], 4)
        self.assertEqual(store.prefetch(["c"], byte_budget=3), 0)

    def test_prefetch_rejects_unknown_before_reading(self):
        store = self.store()
        with self.assertRaises(PolicyError):
            store.prefetch(["a", "unknown"], byte_budget=8)
        self.assertEqual(store.stats()["read_bytes"], 0)

    def test_bad_hash_is_never_cached(self):
        self.blocks["a"] = replace(self.blocks["a"], sha256="0" * 64)
        store = self.store()
        with self.assertRaises(PolicyError):
            store.get("a")
        self.assertEqual(store.stats()["resident_bytes"], 0)

    def test_file_change_invalidates_a_cache_hit(self):
        store = self.store()
        store.get("a")
        self.path.write_bytes(b"changed-size!")
        with self.assertRaises(PolicyError):
            store.get("a")
        self.assertEqual(store.stats()["resident_bytes"], 0)

    def test_removed_file_is_not_served_from_cache(self):
        store = self.store()
        store.get("a"); self.path.unlink()
        with self.assertRaises(PolicyError):
            store.get("a")

    def test_cancellation_before_io(self):
        store = self.store()
        cancel = threading.Event(); cancel.set()
        with self.assertRaises(PolicyError):
            store.get("a", cancel)
        self.assertEqual(store.stats()["read_bytes"], 0)

    def test_cancellation_after_io_does_not_cache(self):
        store = self.store()
        cancel = Mock(); cancel.is_set.side_effect = [False, True]
        with self.assertRaises(PolicyError):
            store.get("a", cancel)
        self.assertEqual(store.stats()["read_bytes"], 4)
        self.assertEqual(store.stats()["resident_bytes"], 0)

    def test_cancelled_prefetch(self):
        store = self.store()
        cancel = threading.Event(); cancel.set()
        with self.assertRaises(PolicyError):
            store.prefetch(["a"], byte_budget=8, cancel=cancel)

    def test_unknown_block_is_rejected(self):
        with self.assertRaises(PolicyError):
            self.store().get("no")

    def test_inventory_is_copied_and_read_only(self):
        store = self.store()
        self.blocks.clear()
        self.assertEqual(store.get("a"), b"aaaa")
        with self.assertRaises(TypeError):
            store.blocks["a"] = store.blocks["b"]

    def test_path_traversal_is_rejected(self):
        for path in ("../outside", "/absolute", "C:/model", "a\\b", "a//b"):
            with self.subTest(path=path), self.assertRaises(PolicyError):
                WeightStore(self.root, {"bad": WeightBlock(path, 0, 4, sha(b"aaaa"))}, cache_bytes=8)

    def test_symlinks_rejected_without_os_privilege_dependency(self):
        with patch.object(Path, "is_symlink", return_value=True), self.assertRaises(PolicyError):
            self.store()

    def test_out_of_range_and_buffer_limit(self):
        self.blocks["a"] = replace(self.blocks["a"], offset=100)
        with self.assertRaises(PolicyError):
            self.store()
        self.blocks.pop("a")
        with self.assertRaises(PolicyError):
            self.store(max_block_bytes=3)

    def test_invalid_numeric_configuration(self):
        for value in (-1, True, 1.5):
            with self.subTest(value=value), self.assertRaises(PolicyError):
                self.store(cache_bytes=value)
        for kw in ({"max_block_bytes": 0}, {"read_budget_bytes": -1}):
            with self.assertRaises(PolicyError):
                self.store(**kw)
        with self.assertRaises(PolicyError):
            WeightBlock("weights.dat", 0, 0, sha(b""))

    def test_concurrent_demand_has_one_initial_read(self):
        store = self.store()
        with ThreadPoolExecutor(max_workers=4) as pool:
            outputs = list(pool.map(lambda _: store.get("a"), range(20)))
        self.assertEqual(outputs, [b"aaaa"] * 20)
        self.assertEqual(store.stats()["read_bytes"], 4)
        self.assertEqual(store.stats()["hits"], 19)
        self.assertFalse(store.stats()["physical_disk_io_measured"])


class PlacementTests(unittest.TestCase):
    def test_cpu_reserves_fixed_and_staging(self):
        plan = plan_placement(MemoryBudget(100, 0, 20, 0, 10), Footprint(20, 100, 10, 8))
        self.assertEqual(plan["fixed_bytes"], 40)
        self.assertEqual(plan["ram_expert_cache_bytes"], 32)
        self.assertEqual(plan["uncached_expert_bytes"], 68)
        self.assertEqual(plan["weights_on_disk_bytes"], 120)
        self.assertFalse(plan["runtime_compatible"])

    def test_cuda_is_only_a_plan_and_preserves_accounting(self):
        plan = plan_placement(MemoryBudget(100, 100, 20, 10, 10), Footprint(20, 200, 10, 8), device="cuda")
        self.assertEqual(plan["gpu_expert_cache_bytes"], 42)
        self.assertEqual(plan["ram_expert_cache_bytes"], 72)
        self.assertEqual(plan["uncached_expert_bytes"], 86)
        self.assertFalse(plan["router_modified"])
        self.assertFalse(plan["precision_modified"])
        self.assertTrue(plan["estimated_only"])

    def test_insufficient_cpu_ram_fails(self):
        with self.assertRaises(PolicyError):
            plan_placement(MemoryBudget(40, 0, 1, 0, 10), Footprint(20, 100, 10, 8))

    def test_cuda_needs_cpu_and_gpu_staging(self):
        for budget in (MemoryBudget(7, 100, 0, 0, 0), MemoryBudget(100, 7, 0, 0, 0)):
            with self.subTest(budget=budget), self.assertRaises(PolicyError):
                plan_placement(budget, Footprint(0, 100, 0, 8), device="cuda")

    def test_dense_model_does_not_invent_experts(self):
        plan = plan_placement(MemoryBudget(100, 0, 20, 0, 10), Footprint(20, 0, 10, 0))
        self.assertEqual(plan["ram_expert_cache_bytes"], 0)
        self.assertEqual(plan["uncached_expert_bytes"], 0)

    def test_invalid_budget_and_footprint(self):
        with self.assertRaises(PolicyError): MemoryBudget(1, 0, 2, 0, 0)
        with self.assertRaises(PolicyError): MemoryBudget(True, 0, 0, 0, 0)
        with self.assertRaises(PolicyError): Footprint(0, 1, 0, 2)
        with self.assertRaises(PolicyError): Footprint(0, 1, 0, 0)
        with self.assertRaises(PolicyError):
            plan_placement(MemoryBudget(10, 0, 0, 0, 0), Footprint(1, 0, 0, 0), device="remote")


class OracleTests(unittest.TestCase):
    def test_swiglu_against_independent_scalar_calculation(self):
        raw = np.array([1, 2, 3], dtype="<f4").tobytes()
        calls = []
        def read(key):
            calls.append(key)
            return raw
        output = routed_swiglu([0.5], [("second", 2.0), ("first", 3.0)], intermediate=1, read=read)
        expected = 5 * 3 * (0.5 / (1 + math.exp(-0.5))) * 1.0
        np.testing.assert_allclose(output, [expected], rtol=1e-6)
        self.assertEqual(calls, ["second", "first"])

    def test_streamed_and_resident_synthetic_experts_match(self):
        rng = np.random.default_rng(31)
        raw = {f"e{i}": rng.normal(0, 0.1, 3 * 4 * 8).astype("<f4").tobytes() for i in range(3)}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            blocks = {}
            for key, value in raw.items():
                (root / key).write_bytes(value)
                blocks[key] = WeightBlock(key, 0, len(value), sha(value))
            size = len(raw["e0"])
            for capacity in (0, size, size * 2, size * 3):
                store = WeightStore(root, blocks, cache_bytes=capacity, max_block_bytes=size)
                for routes in ([('e0', 0.7), ('e1', 0.3)], [('e2', 1.0)], [('e0', 0.4), ('e2', 0.8)]):
                    x = rng.normal(size=4).astype(np.float32)
                    expected = routed_swiglu(x, routes, intermediate=8, read=raw.__getitem__)
                    actual = routed_swiglu(x, routes, intermediate=8, read=store.get)
                    np.testing.assert_array_equal(actual, expected)
                self.assertLessEqual(store.stats()["peak_resident_bytes"], capacity)

    def test_invalid_routes(self):
        for routes in ([], [("e", -1.0)], [("e", float("nan"))], [("e", True)], [("e", 1), ("e", 1)]):
            with self.subTest(routes=routes), self.assertRaises(PolicyError):
                routed_swiglu([1.0], routes, intermediate=1, read=lambda _: b"")

    def test_invalid_hidden_or_dimension(self):
        for hidden in ([], [[1.0]], [float("nan")]):
            with self.assertRaises(PolicyError):
                routed_swiglu(hidden, [("e", 1)], intermediate=1, read=lambda _: b"")
        with self.assertRaises(PolicyError):
            routed_swiglu([1.0], [("e", 1)], intermediate=0, read=lambda _: b"")

    def test_wrong_layout_or_nonfinite_weights(self):
        for raw in (b"bad", np.array([1, float("inf"), 1], dtype="<f4").tobytes()):
            with self.assertRaises(PolicyError):
                routed_swiglu([1], [("e", 1)], intermediate=1, read=lambda _: raw)


class LearningGateTests(unittest.TestCase):
    def report(self, candidate=False):
        return {"schema": 1, "checkpoint_sha256": sha("candidate" if candidate else "base"),
                "suite_sha256": sha("suite"), "runner_sha256": sha("runner"),
                "environment_sha256": sha("environment"), "dataset_sha256": sha("data"),
                "real_model_execution": True, "rights_reviewed": True, "human_reviewed": True,
                "reviewed_by": "test-fixture-not-a-real-evaluation", "safety_failures": 0,
                "elapsed_seconds": 100.0, "peak_ram_bytes": 1000,
                "outcomes": {sha(f"case{i}"): i < (42 if candidate else 40) for i in range(50)},
                "training_problem_hashes": [sha("different training problem")]}

    def assess(self, **updates):
        candidate = self.report(True); candidate.update(updates)
        return assess_candidate(self.report(), candidate)

    def test_eligible_still_does_not_promote_or_prove_significance(self):
        result = self.assess()
        self.assertTrue(result["eligible_for_human_promotion"])
        self.assertFalse(result["automatically_promoted"])
        self.assertFalse(result["weights_modified"])
        self.assertFalse(result["statistical_significance_established"])
        self.assertAlmostEqual(result["absolute_gain"], 0.04)

    def test_all_explicit_decisions_are_required(self):
        for field in ("real_model_execution", "rights_reviewed", "human_reviewed"):
            with self.subTest(field=field):
                self.assertFalse(self.assess(**{field: False})["eligible_for_human_promotion"])
                with self.assertRaises(PolicyError): self.assess(**{field: 1})

    def test_baseline_must_be_real_too(self):
        baseline = self.report(); baseline["real_model_execution"] = False
        self.assertFalse(assess_candidate(baseline, self.report(True))["eligible_for_human_promotion"])

    def test_matching_comparison_identity_required(self):
        for field in ("suite_sha256", "runner_sha256", "environment_sha256"):
            self.assertFalse(self.assess(**{field: sha("different")})["eligible_for_human_promotion"])

    def test_unchanged_checkpoint_is_not_learning(self):
        self.assertIn("candidate:checkpoint_unchanged", self.assess(checkpoint_sha256=sha("base"))["reasons"])

    def test_same_cases_and_minimum_count_required(self):
        outcomes = self.report(True)["outcomes"]
        outcomes.pop(next(iter(outcomes)))
        result = self.assess(outcomes=outcomes)
        self.assertIn("comparison:case_set_mismatch", result["reasons"])
        self.assertIn("candidate:insufficient_cases", result["reasons"])

    def test_training_contamination_rejected(self):
        self.assertFalse(self.assess(training_problem_hashes=[sha("case0")])["eligible_for_human_promotion"])

    def test_cross_run_contamination_rejected(self):
        baseline = self.report(); baseline["training_problem_hashes"] = [sha("case0")]
        result = assess_candidate(baseline, self.report(True))
        self.assertIn("comparison:cross_run_holdout_contamination", result["reasons"])

    def test_safety_latency_and_memory_regressions(self):
        for update in ({"safety_failures": 1}, {"elapsed_seconds": 121}, {"peak_ram_bytes": 1001}):
            self.assertFalse(self.assess(**update)["eligible_for_human_promotion"])

    def test_quality_gain_required(self):
        self.assertFalse(self.assess(outcomes=self.report()["outcomes"])["eligible_for_human_promotion"])

    def test_invalid_metrics_fail_closed(self):
        for value in (float("nan"), float("inf"), -1, 0, True):
            with self.subTest(value=value), self.assertRaises(PolicyError):
                self.assess(elapsed_seconds=value)

    def test_missing_invalid_hashes_and_empty_outcomes(self):
        for update in ({"checkpoint_sha256": "fake"}, {"outcomes": {}}, {"schema": True},
                       {"training_problem_hashes": None}, {"reviewed_by": ""}, {"safety_failures": True}):
            with self.subTest(update=update), self.assertRaises(PolicyError):
                self.assess(**update)

    def test_invalid_thresholds(self):
        for kw in ({"minimum_cases": 0}, {"minimum_gain": 1.1}, {"max_slowdown": 0}, {"max_ram_growth": True}):
            with self.subTest(kw=kw), self.assertRaises(PolicyError):
                assess_candidate(self.report(), self.report(True), **kw)


class ResidencyPrimitiveTests(unittest.TestCase):
    def test_owned_references_drop_before_allocator_release(self):
        owner = SimpleNamespace(model=object(), tokenizer=object(), torch=SimpleNamespace(cuda=Mock()))
        owner.torch.cuda.is_initialized.return_value = True
        def empty():
            self.assertIsNone(owner.model)
            self.assertIsNone(owner.tokenizer)
        owner.torch.cuda.empty_cache.side_effect = empty
        release_tensors(owner, ("model", "tokenizer"))
        owner.torch.cuda.empty_cache.assert_called_once()

    def test_uninitialized_cuda_is_not_created(self):
        cuda = Mock(); cuda.is_initialized.return_value = False
        owner = SimpleNamespace(torch=SimpleNamespace(cuda=cuda))
        release_tensors(owner, ("absent",))
        cuda.empty_cache.assert_not_called()

    def test_dispose_is_compatible_with_doubles_and_propagates_failure(self):
        dispose_runtime(object())
        runtime = Mock(); runtime.close.side_effect = RuntimeError("fixture")
        with self.assertRaises(RuntimeError): dispose_runtime(runtime)


if __name__ == "__main__":
    unittest.main()
