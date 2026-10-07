"""Learning/promotion contracts using explicit fixtures, not model benchmarks."""
from copy import deepcopy
from pathlib import Path
import json
from unittest.mock import patch

from tests.helpers import WorkspaceCase
from tests.test_foundation import register_fixture
from localauthor.errors import PolicyError
from localauthor.foundation.dataset import canonical_hash, validate_dataset, validate_experiment
from localauthor.foundation.models import digest, read_object, write_new
from localauthor.foundation.promotion import promote, rollback
from localauthor.foundation.training import completion_tokens, training_configuration
from localauthor.foundation.isolation import require_isolated_process
from localauthor.foundation.conversion import convert_jsonl


class DatasetContractTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        approval = dict(accepted=True, verified=True, rights_reviewed=True, training_allowed=True,
                        reviewer="fixture-human-not-an-actual-review", receipt_sha256="a" * 64)
        self.rows = []
        for index, (prompt, response, split) in enumerate([
            ("Retorne um objeto JSON contendo uma lista vazia de evidências.", '{"evidence":[]}', "train"),
            ("Explique o cancelamento assíncrono de uma requisição interrompida.", "A tarefa foi cancelada, sem resultado de sucesso.", "validation")]):
            messages = [{"role": "user", "content": prompt}, {"role": "assistant", "content": response}]
            self.rows.append(dict(example_id=f"example-{index}", task_family=f"family-{index}",
                project_group=f"project-{index}", leakage_group=f"origin-{index}", modality="text", source_ids=["original"],
                messages=messages, split=split, approval=approval, truncated=False,
                context_hash=canonical_hash(messages[:-1]), target_hash=canonical_hash(messages[-1])))
        source = self.root / "source.jsonl"
        source.write_text("\n".join(json.dumps(row["messages"], ensure_ascii=False, sort_keys=True) for row in self.rows), encoding="utf-8")
        receipt = self.root / "receipt.json"
        write_new(receipt, {**approval, "schema": 1, "bindings": [
            {"source_id": "original", "sha256": digest(source)},
            *[{"example_id": r["example_id"], "context_hash": r["context_hash"], "target_hash": r["target_hash"]} for r in self.rows]]})
        approval.update(receipt_file="receipt.json", receipt_sha256=digest(receipt))
        self.data = dict(schema=1, purpose="foundation-development", sources={"original": {
            "file": "source.jsonl", "sha256": digest(source), "license": "test-fixture-only", "revoked": False,
            "approval": approval}}, examples=self.rows, reserved_target_hashes=[])
        self.path = self.root / "dataset.json"

    def validate(self):
        self.path.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
        return validate_dataset(self.path)

    def test_approved_fixture_has_separate_train_validation_and_complete_sources(self):
        self.assertEqual(self.validate()["split_counts"], {"train": 1, "validation": 1})

    def test_each_independent_approval_is_required(self):
        for flag in ("accepted", "verified", "rights_reviewed", "training_allowed"):
            with self.subTest(flag=flag):
                self.data["sources"]["original"]["approval"][flag] = False
                with self.assertRaises(PolicyError): self.validate()
                self.data["sources"]["original"]["approval"][flag] = True

    def test_receipt_must_exist_and_bind_exact_content(self):
        self.assertEqual(self.validate()["split_counts"]["train"], 1)
        receipt = self.root / "receipt.json"
        data = read_object(receipt); data["bindings"] = []
        receipt.write_text(json.dumps(data), encoding="utf-8")
        self.data["sources"]["original"]["approval"]["receipt_sha256"] = digest(receipt)
        with self.assertRaises(PolicyError): self.validate()

    def test_unknown_revoked_or_modified_source_fails_closed(self):
        self.rows[0]["source_ids"] = ["unknown"]
        with self.assertRaises(PolicyError): self.validate()
        self.rows[0]["source_ids"] = ["original"]
        self.data["sources"]["original"]["revoked"] = True
        with self.assertRaises(PolicyError): self.validate()
        self.data["sources"]["original"]["revoked"] = False
        (self.root / "source.jsonl").write_text("modified", encoding="utf-8")
        with self.assertRaises(PolicyError): self.validate()

    def test_duplicate_ids_and_group_leakage_are_rejected(self):
        self.rows[1]["example_id"] = self.rows[0]["example_id"]
        with self.assertRaises(PolicyError): self.validate()
        self.rows[1]["example_id"] = "another"
        self.rows[1]["leakage_group"] = self.rows[0]["leakage_group"]
        with self.assertRaises(PolicyError): self.validate()

    def test_empty_unicode_truncated_and_wrong_hash_fail(self):
        for change in ("empty", "unicode", "truncated", "hash"):
            with self.subTest(change=change):
                saved = deepcopy(self.rows[0])
                if change == "empty": self.rows[0]["messages"][-1]["content"] = ""
                if change == "unicode": self.rows[0]["messages"][-1]["content"] = "\ud800"
                if change == "truncated": self.rows[0]["truncated"] = True
                if change == "hash": self.rows[0]["context_hash"] = "wrong"
                with self.assertRaises((PolicyError, UnicodeError)): self.validate()
                self.rows[0] = saved
                self.data["examples"] = self.rows

    def test_reserved_target_in_history_cannot_enter_training(self):
        self.data["reserved_target_hashes"] = [canonical_hash(self.rows[0]["messages"][0])]
        with self.assertRaises(PolicyError): self.validate()

    def test_shared_system_rules_do_not_make_distinct_tasks_duplicates(self):
        for row in self.rows:
            row["messages"].insert(0, {"role": "system", "content": "Shared product safety rules. " * 40})
            row["context_hash"] = canonical_hash(row["messages"][:-1])
        source = self.root / "source.jsonl"
        source.write_text('\n'.join(json.dumps(r["messages"], ensure_ascii=False, sort_keys=True)
                                    for r in self.rows), encoding="utf-8")
        item = self.data["sources"]["original"]
        item["sha256"] = digest(source)
        receipt = self.root / "receipt.json"
        approved = read_object(receipt)
        approved["bindings"] = [{"source_id": "original", "sha256": digest(source)},
            *[{"example_id": r["example_id"], "context_hash": r["context_hash"], "target_hash": r["target_hash"]}
              for r in self.rows]]
        receipt.write_text(json.dumps(approved), encoding="utf-8")
        item["approval"]["receipt_sha256"] = digest(receipt)
        self.assertEqual(self.validate()["split_counts"], {"train": 1, "validation": 1})

    def test_final_evaluation_cannot_be_dataset_and_test_split_is_denied(self):
        self.data["purpose"] = "final-evaluation"
        with self.assertRaises(PolicyError): self.validate()
        self.data["purpose"] = "foundation-development"
        self.rows[0]["split"] = "test"
        with self.assertRaises(PolicyError): self.validate()

    def test_missing_fields_and_unbounded_experiment_are_rejected(self):
        path = self.root / "experiment.json"
        path.write_text('{}')
        with self.assertRaises(PolicyError): validate_experiment(path)

    def test_converter_preserves_context_groups_and_requires_exact_export(self):
        import hashlib
        exported = []
        assignments = {}
        for row in self.rows:
            metadata = {"generation_context": row["messages"][:-1], "possibly_truncated": False}
            hashed = hashlib.sha256((row["messages"][-1]["content"] + json.dumps(metadata, ensure_ascii=False)).encode()).hexdigest()
            exported.append({"id": row["example_id"], "project_id": "fixture-project", "kind": "text",
                             "split": row["split"], "messages": row["messages"], "metadata": metadata, "output_hash": hashed})
            assignments[row["example_id"]] = {**row, "project_id": "fixture-project", "output_hash": hashed}
        export = self.root / "export.jsonl"
        export.write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in exported), encoding="utf-8")
        curation = self.root / "curation.json"
        write_new(curation, {"schema": 1, "export_sha256": digest(export), "assignments": assignments,
                            "sources": self.data["sources"], "reserved_target_hashes": []})
        result = convert_jsonl(export, curation, self.root / "converted.json")
        self.assertEqual(result["split_counts"], {"train": 1, "validation": 1})
        self.assertEqual(read_object(self.root / "converted.json")["examples"][0]["messages"], self.rows[0]["messages"])
        export.write_text('changed')
        with self.assertRaises(PolicyError): convert_jsonl(export, curation, self.root / "denied.json")
        self.assertFalse((self.root / "denied.json").exists())

    def test_masks_only_completion_and_eos_and_rejects_truncation(self):
        class Tokenizer:
            eos_token_id = 9
            def apply_chat_template(self, messages, **kwargs):
                assert kwargs["return_dict"] is False and kwargs["enable_thinking"] is False
                return [1, 2, 3]
            def __call__(self, text, **kwargs): return {"input_ids": [4, 5] if text else []}
        result = completion_tokens(Tokenizer(), self.rows[0], 6)
        self.assertEqual(result["input_ids"], [1, 2, 3, 4, 5, 9])
        self.assertEqual(result["labels"], [-100, -100, -100, 4, 5, 9])
        with self.assertRaises(PolicyError): completion_tokens(Tokenizer(), self.rows[0], 5)
        self.rows[0]["messages"][-1]["content"] = ""
        with self.assertRaises(PolicyError): completion_tokens(Tokenizer(), self.rows[0], 6)

    def test_training_configuration_denies_nan_unknown_targets_and_architecture(self):
        config = dict(architecture="qwen3", sequence_tokens=256, learning_rate=0.0001,
                      rank=4, alpha=8, target_modules=["q_proj", "v_proj"], clip_norm=1)
        self.assertEqual(training_configuration({"configuration": config}), config)
        for key, value in (("learning_rate", float("nan")), ("target_modules", ["all"]), ("architecture", "unknown")):
            with self.subTest(key=key), self.assertRaises(PolicyError):
                training_configuration({"configuration": {**config, key: value}})

    def test_isolation_has_no_windows_or_root_fallback(self):
        with patch("localauthor.foundation.isolation.os.name", "nt"), self.assertRaises(PolicyError): require_isolated_process()


class PromotionContractTests(WorkspaceCase):
    def setup_candidate(self):
        base = register_fixture(self.settings.home, self.root / "base")
        candidate_home = self.root / "candidate-home"
        register_fixture(candidate_home, self.root / "candidate-weights")
        candidate = candidate_home / "foundation/text-model.json"
        evaluation = self.root / "evaluation.json"
        write_new(evaluation, dict(status="passed", candidate_manifest_sha256=digest(candidate), critical_failures=0,
                                  omitted=0, criteria_frozen=True, real_checkpoint=True,
                                  kind="base-candidate-comparison", same_conditions=True, regressions=[],
                                  total=1, passed=1, baseline_passed=1, qualification_suite=True,
                                  base_manifest_sha256=base.manifest_sha256,
                                  results=[dict(id="fixture-only", passed=True, critical=True)]))
        approval = self.root / "approval.json"
        write_new(approval, dict(decision="approved", human="fixture-human", scope="contract-test-only",
                                candidate_manifest_sha256=digest(candidate), evaluation_sha256=digest(evaluation)))
        return base, candidate, evaluation, approval

    def test_promotion_and_rollback_preserve_model_and_data(self):
        base, candidate, evaluation, approval = self.setup_candidate()
        marker = self.settings.home / "conversation-preserved.txt"; marker.write_text("unchanged")
        result = promote(self.settings.home, candidate, evaluation, approval)
        active = self.settings.home / "foundation/text-model.json"
        self.assertEqual(digest(active), digest(candidate))
        journal = Path(result["journal"])
        rollback(self.settings.home, journal)
        self.assertEqual(digest(active), base.manifest_sha256)
        self.assertEqual(marker.read_text(), "unchanged")
        self.assertTrue(rollback(self.settings.home, journal)["rolled_back"])

    def test_missing_human_or_critical_failure_denies_promotion(self):
        _, candidate, evaluation, approval = self.setup_candidate()
        for key, value in (("decision", "pending"), ("evaluation_sha256", "bad")):
            decision = read_object(approval); original = dict(decision); decision[key] = value
            approval.write_text(json.dumps(decision))
            with self.assertRaises(PolicyError): promote(self.settings.home, candidate, evaluation, approval)
            approval.write_text(json.dumps(original))
        result = read_object(evaluation); result["critical_failures"] = 1
        evaluation.write_text(json.dumps(result))
        with self.assertRaises(PolicyError): promote(self.settings.home, candidate, evaluation, approval)

    def test_interruption_after_atomic_pointer_is_recoverable(self):
        base, candidate, evaluation, approval = self.setup_candidate()
        from localauthor.foundation import promotion
        original = promotion.replace_json
        def crash(path, data):
            if path.parent.name == "promotions": raise OSError("fixture interruption after replace")
            return original(path, data)
        with patch.object(promotion, "replace_json", side_effect=crash), self.assertRaises(OSError):
            promote(self.settings.home, candidate, evaluation, approval)
        journal = next((self.settings.home / "foundation/promotions").glob("*.json"))
        self.assertEqual(read_object(journal)["state"], "prepared")
        rollback(self.settings.home, journal)
        self.assertEqual(digest(self.settings.home / "foundation/text-model.json"), base.manifest_sha256)

    def test_busy_server_denies_promotion(self):
        _, candidate, evaluation, approval = self.setup_candidate()
        (self.settings.home / "server.lock").write_text("fixture")
        with self.assertRaises(PolicyError): promote(self.settings.home, candidate, evaluation, approval)

    def test_smoke_partial_regressed_or_stale_comparison_cannot_promote(self):
        _, candidate, evaluation, approval = self.setup_candidate()
        original = read_object(evaluation)
        for field, value in (("qualification_suite", False), ("results", []), ("regressions", ["broken"]),
                             ("baseline_passed", 2), ("base_manifest_sha256", "a" * 64)):
            with self.subTest(field=field):
                evaluation.write_text(json.dumps({**original, field: value}))
                decision = read_object(approval); decision["evaluation_sha256"] = digest(evaluation)
                approval.write_text(json.dumps(decision))
                with self.assertRaises(PolicyError): promote(self.settings.home, candidate, evaluation, approval)
