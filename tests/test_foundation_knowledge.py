"""Source lifecycle and revision matching; no real model qualification."""
import json
from unittest.mock import patch

from tests.helpers import WorkspaceCase
from localauthor.errors import PolicyError
from localauthor.foundation.context import markdown_evidence
from localauthor.foundation.experience import ExperienceStore
from localauthor.foundation.knowledge import import_markdown, revoke_source


class KnowledgeLifecycleTests(WorkspaceCase):
    def note(self, text="CancellationToken propaga cancelamento assíncrono.", scope="laboratory"):
        file = self.root / "knowledge-note.md"
        file.write_text(text, encoding="utf-8")
        return import_markdown(self.settings.home, scope, file, "Cancelamento", "cancellation")

    def test_repeated_import_is_idempotent_and_hash_checked(self):
        first, second = self.note(), self.note()
        self.assertEqual(first["path"], second["path"])
        self.assertTrue(second["reused"])
        stored = self.settings.home / "foundation/knowledge/laboratory" / first["path"]
        stored.write_text("changed", encoding="utf-8")
        with self.assertRaises(PolicyError):
            self.note()

    def test_version_update_preserves_old_bytes_and_filters_old_source(self):
        first = self.note()
        second = self.note("CancellationToken permite interrupção cooperativa.")
        self.assertEqual(second["version"], 2)
        root = self.settings.home / "foundation/knowledge/laboratory"
        self.assertTrue((root / first["path"]).is_file())
        evidence = markdown_evidence(root, "CancellationToken", "laboratory")
        self.assertEqual([e["source_id"] for e in evidence], [second["path"]])
        self.assertFalse(second["training_allowed"])

    def test_revocation_is_idempotent_and_cross_project_isolation_holds(self):
        self.note()
        other = self.note(scope="other")
        revoke_source(self.settings.home, "laboratory", "cancellation")
        revoke_source(self.settings.home, "laboratory", "cancellation")
        self.assertEqual(markdown_evidence(self.settings.home / "foundation/knowledge/laboratory", "CancellationToken", "laboratory"), [])
        self.assertEqual(markdown_evidence(self.settings.home / "foundation/knowledge/other", "CancellationToken", "other")[0]["source_id"], other["path"])

    def test_source_update_invalidates_experience_and_cannot_be_reapproved(self):
        source = self.note()
        store = ExperienceStore(self.settings.home)
        ident = store.record("laboratory", "text", "cancelamento", "CancellationToken",
                             {"evidence": [{"source_id": source["path"], "sha256": source["sha256"]}], "code_revision": "revision-a"})
        row = store.get("laboratory", ident)
        decision = dict(expected_hash=row["output_hash"], accepted=True, verified=True, rights_reviewed=True,
                        training_allowed=True, reviewer="fixture-human", verification_note="fixture only")
        store.review("laboratory", ident, **decision)
        self.assertEqual(len(store.recall("laboratory", "cancelamento", code_revision="revision-a")), 1)
        self.note("CancellationToken revised.")
        self.assertEqual(store.training_rows("laboratory", "text"), [])
        self.assertEqual(store.recall("laboratory", "cancelamento", code_revision="revision-a"), [])
        with self.assertRaises(PolicyError):
            store.review("laboratory", ident, **decision)

    def test_recall_requires_accepted_verified_and_matching_revision(self):
        store = ExperienceStore(self.settings.home)
        ident = store.record("laboratory", "text", "cancelamento", "token", {"code_revision": "revision-a"})
        self.assertEqual(store.recall("laboratory", "cancelamento", code_revision="revision-a"), [])
        store.review("laboratory", ident, expected_hash=store.get("laboratory", ident)["output_hash"],
                     accepted=True, verified=True, rights_reviewed=False, training_allowed=False,
                     reviewer="fixture-human", verification_note="fixture verification")
        self.assertEqual(store.recall("other", "cancelamento", code_revision="revision-a"), [])
        self.assertEqual(store.recall("laboratory", "cancelamento", code_revision="revision-b"), [])
        self.assertFalse(store.recall("laboratory", "cancelamento", code_revision="revision-a")[0]["training_allowed"])

    def test_import_denies_running_server_empty_invalid_unicode_and_symlink(self):
        lock = self.settings.home / "server.lock"
        lock.write_text("1")
        with self.assertRaises(PolicyError): self.note()
        lock.unlink()
        with self.assertRaises(PolicyError): self.note("")
        file = self.root / "bad.md"; file.write_bytes(b"\xff")
        with self.assertRaises(UnicodeError): import_markdown(self.settings.home, "laboratory", file, "Bad")
        with patch.object(type(file), "is_symlink", return_value=True), self.assertRaises(PolicyError): self.note()

    def test_failed_commit_does_not_erase_prior_version(self):
        original = self.note()
        with patch("localauthor.foundation.knowledge._commit", side_effect=OSError("fixture failure")), self.assertRaises(OSError):
            self.note("new CancellationToken version")
        root = self.settings.home / "foundation/knowledge/laboratory"
        manifest = json.loads((root / "sources.json").read_text())
        self.assertEqual(manifest["sources"][0]["path"], original["path"])
        self.assertEqual(len(list(root.glob("*.md"))), 1)
