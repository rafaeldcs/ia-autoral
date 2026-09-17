import threading
from datetime import datetime, timedelta, timezone
from localauthor.errors import PolicyError
from localauthor.knowledge import KnowledgeService
from localauthor.store import Store
from tests.helpers import WorkspaceCase


class StoreTests(WorkspaceCase):
    def note(self, text="Estoque negativo exige validação.", scope="global", locator="note:stock"):
        return self.store.ingest(scope, locator, "Estoque", text, kind="note")

    def test_ingest_and_search_has_lines_and_hash(self):
        self.note()
        results = self.store.search("estoque negativo")
        self.assertEqual(results[0]["start_line"], 1)
        self.assertEqual(len(results[0]["document_hash"]), 64)
        self.assertIn("Estoque", results[0]["text"])

    def test_ingest_idempotent(self):
        first = self.note(); second = self.note()
        self.assertEqual(first["id"], second["id"])
        self.assertTrue(second["deduplicated"])
        self.assertEqual(self.store.stats()["versions"], 1)

    def test_current_version_only_in_search(self):
        self.note("Temaantigo removido")
        self.note("Temanovo adicionado")
        self.assertEqual(self.store.search("Temaantigo"), [])
        self.assertEqual(len(self.store.search("Temanovo")), 1)
        self.assertEqual(self.store.stats()["versions"], 2)

    def test_reverting_content_reuses_historical_version(self):
        a = self.note("Primeiro conteúdo")
        self.note("Segundo conteúdo")
        again = self.note("Primeiro conteúdo")
        self.assertEqual(again["version_id"], a["version_id"])
        self.assertEqual(self.store.stats()["versions"], 2)

    def test_project_scope_not_leaked_to_global(self):
        self.note(scope=self.project["id"])
        self.assertEqual(self.store.search("Estoque"), [])
        self.assertEqual(len(self.store.search("Estoque", self.project["id"])), 1)

    def test_global_scope_requires_explicit_inclusion(self):
        self.note()
        self.assertEqual(self.store.search("Estoque", self.project["id"]), [])
        self.assertEqual(len(self.store.search("Estoque", self.project["id"], include_global=True)), 1)

    def test_global_scope_does_not_include_another_project(self):
        other = self.root/"other"; other.mkdir()
        project2 = self.store.add_project("Outro", str(other))
        self.note(scope=project2["id"])
        self.assertEqual(self.store.search("Estoque", self.project["id"], include_global=True), [])

    def test_no_fts_syntax_injection(self):
        self.note()
        self.store.search('" OR * NEAR(estoque) NOT secret; DROP TABLE sources; --')
        self.assertEqual(self.store.stats()["sources"], 1)

    def test_empty_search(self):
        self.assertEqual(self.store.search("! % *"), [])

    def test_add_relation_requires_same_scope(self):
        self.note()
        chunk = self.store.search("Estoque")[0]["chunk_id"]
        with self.assertRaises(PolicyError): self.store.add_relation(self.project["id"], "A", "uses", "B", chunk)

    def test_model_relation_not_self_verified(self):
        self.note(); chunk = self.store.search("Estoque")[0]["chunk_id"]
        with self.assertRaises(PolicyError): self.store.add_relation("global", "A", "uses", "B", chunk, "verified", "model")

    def test_relation_stale_evidence_flag(self):
        self.note(); chunk = self.store.search("Estoque")[0]["chunk_id"]
        self.store.add_relation("global", "A", "uses", "B", chunk, "verified")
        self.note("Regra substituída por outra versão")
        self.assertEqual(self.store.relations("global")[0]["current_evidence"], 0)

    def test_delete_cascades_evidence(self):
        note = self.note(); chunk = self.store.search("Estoque")[0]["chunk_id"]
        self.store.add_relation("global", "A", "uses", "B", chunk)
        self.store.delete_source(note["id"], "global")
        self.assertEqual(self.store.search("Estoque"), [])
        self.assertEqual(self.store.relations("global"), [])
        self.assertEqual(self.store.stats()["versions"], 0)

    def test_content_quota_rolls_back(self):
        small = Store(self.settings.home/"small.sqlite3", 10)
        with self.assertRaises(PolicyError): small.ingest("global", "x", "x", "Content larger than quota")
        self.assertEqual(small.stats()["sources"], 0)

    def test_index_twice_and_skip_secret(self):
        (self.project_root/"secret.txt").write_text('password="'+'q'*20+'"')
        knowledge = KnowledgeService(self.store, self.settings)
        first = knowledge.index_project(self.project["id"])
        second = knowledge.index_project(self.project["id"])
        self.assertEqual(first["indexed"], 2)
        self.assertEqual(second["unchanged"], 2)
        self.assertTrue(first["skipped"])

    def test_index_cancel(self):
        cancel = threading.Event(); cancel.set()
        result = KnowledgeService(self.store, self.settings).index_project(self.project["id"], cancel)
        self.assertTrue(result["cancelled"])
        self.assertEqual(result["indexed"], 0)

    def test_consult_is_not_fabricated_model_answer(self):
        self.note()
        data = KnowledgeService(self.store, self.settings).consult("estoque", "global")
        self.assertIsNone(data["generated_answer"])
        self.assertFalse(data["research_needed"])
        self.assertEqual(data["mode"], "retrieval_only")

    def test_stale_source_requests_update(self):
        result = self.store.ingest("global", "https://example.com/doc", "Doc", "Estoque e validação", kind="web")
        with self.store.connect() as db:
            db.execute("UPDATE sources SET checked_at=? WHERE id=?", ((datetime.now(timezone.utc)-timedelta(days=2)).isoformat(), result["id"]))
        result = KnowledgeService(self.store, self.settings).consult("Estoque", "global")
        self.assertTrue(result["research_needed"])
        self.assertEqual(result["reason"], "stale_web_evidence")

    def test_sqlite_backup_restores_search(self):
        self.note()
        dest = self.root/"backup.sqlite3"
        self.store.backup(dest)
        restored = Store(dest)
        self.assertEqual(len(restored.search("Estoque")), 1)
