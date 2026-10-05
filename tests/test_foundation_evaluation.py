"""Evaluator failure contracts with explicit doubles; NOT a checkpoint benchmark."""
from pathlib import Path
from unittest.mock import patch

from tests.helpers import WorkspaceCase
from tests.test_foundation import register_fixture
from localauthor.errors import PolicyError
from localauthor.foundation.evaluation import evaluate, compare
from localauthor.foundation.models import write_new


class EvaluationTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        register_fixture(self.settings.home, self.root / "base")
        self.manifest = self.settings.home / "foundation/text-model.json"
        self.cases = self.root / "cases.json"
        write_new(self.cases, {"schema": 1, "frozen": True,
                  "criteria": {"minimum_cases": 3, "minimum_fraction": 1}, "independence": "fixture-only",
                  "cases": [{"id": str(i), "oracle": oracle, "critical": i == 2,
                             "messages": [{"role": "user", "content": "fixture"}], "expected": target}
                            for i, (oracle, target) in enumerate([( "exact", "yes"), ("json", {"value": 1}), ("exact", "safe")])]})

    def run_fake(self, outputs):
        class Engine:
            def __init__(self, spec): self.iterator = iter(outputs)
            def generate(self, messages):
                result = next(self.iterator)
                if isinstance(result, Exception): raise result
                return result
        with patch("localauthor.foundation.evaluation.require_isolated_process", return_value={"fixture": True}), \
             patch("localauthor.foundation.evaluation.TextRuntime", Engine):
            return evaluate(self.manifest, self.cases, self.root / "report.json")

    def test_all_cases_count_even_when_generation_fails_or_truncates(self):
        result = self.run_fake([("yes", True), ("", False), RuntimeError("fixture")])
        self.assertEqual((result["total"], result["passed"], result["critical_failures"]), (3, 0, 1))
        self.assertEqual(result["status"], "rejected")
        self.assertFalse(result["qualification_suite"])

    def test_malformed_json_is_not_repaired_and_critical_failure_overrides_fraction(self):
        result = self.run_fake([("yes", False), ('```json\n{"value":1}\n```', False), ("unsafe", False)])
        self.assertEqual(result["passed"], 1)
        self.assertEqual(result["results"][1]["error"], "JSONDecodeError")
        self.assertEqual(result["status"], "rejected")

    def test_success_is_only_text_oracle_success(self):
        result = self.run_fake([("yes", False), ('{"value":1}', False), ("safe", False)])
        self.assertEqual(result["status"], "passed")
        self.assertFalse(result["qualification_suite"])

    def test_comparison_rejects_changed_conditions_before_loading(self):
        import json
        data = json.loads(self.manifest.read_text()); data["output_tokens"] += 1
        candidate = self.root / "candidate.json"; write_new(candidate, data)
        with self.assertRaises(PolicyError): compare(self.manifest, candidate, self.cases, self.root / "comparison")
        self.assertFalse((self.root / "comparison").exists())
