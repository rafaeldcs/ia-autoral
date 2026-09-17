import json
from unittest.mock import patch
from localauthor.tasks import TaskService
from localauthor.runner import SandboxRunner
from localauthor.errors import PolicyError, ConflictError
from localauthor.util import sha256, read_json, atomic_write
from tests.helpers import WorkspaceCase


class TaskTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.tasks = TaskService(self.store, self.settings)
        self.original = (self.project_root/"Product.cs").read_bytes()
        self.task = self.tasks.create(self.project["id"], "Alterar a quantidade inicial.")

    def stage(self, content="public class Product { public int Quantity = 2; }\r\n", path="Product.cs", before=None):
        return self.tasks.propose(self.task["id"], [{"path": path, "before_sha256": before or sha256(self.original), "content": content}])

    def test_snapshot_preserves_crlf_and_original(self):
        copy = self.tasks.base(self.task["id"])/"tree"/"Product.cs"
        self.assertEqual(copy.read_bytes(), self.original)
        self.assertEqual(self.task["model_status"], "not_qualified")

    def test_staging_does_not_modify_original(self):
        result = self.stage()
        self.assertEqual((self.project_root/"Product.cs").read_bytes(), self.original)
        self.assertIn("Quantity = 2", result["diff"])

    def test_wrong_baseline_hash_rejected(self):
        with self.assertRaises(ConflictError): self.stage(before="0"*64)

    def test_outside_write_rejected(self):
        with self.assertRaises(PolicyError): self.stage(path="../escape.cs")
        self.assertFalse((self.root/"escape.cs").exists())

    def test_requires_test_or_explicit_untested_approval(self):
        result = self.stage()
        with self.assertRaises(PolicyError): self.tasks.apply(self.task["id"], result["proposal_hash"])
        self.assertEqual((self.project_root/"Product.cs").read_bytes(), self.original)

    def test_explicit_approval_applies_crlf(self):
        result = self.stage()
        task = self.tasks.apply(self.task["id"], result["proposal_hash"], accept_without_tests=True)
        self.assertEqual(task["state"], "applied")
        self.assertTrue((self.project_root/"Product.cs").read_bytes().endswith(b"\r\n"))
        self.assertIn(b"Quantity = 2", (self.project_root/"Product.cs").read_bytes())

    def test_stale_proposal_approval_rejected(self):
        first = self.stage()
        self.stage("public class Product { public int Quantity = 3; }\r\n")
        with self.assertRaises(ConflictError): self.tasks.apply(self.task["id"], first["proposal_hash"], accept_without_tests=True)

    def test_human_change_after_snapshot_preserved(self):
        result = self.stage()
        (self.project_root/"Product.cs").write_text("human edit")
        with self.assertRaises(ConflictError): self.tasks.apply(self.task["id"], result["proposal_hash"], accept_without_tests=True)
        self.assertEqual((self.project_root/"Product.cs").read_text(), "human edit")

    def test_staged_tampering_is_detected(self):
        result = self.stage()
        (self.tasks.base(self.task["id"])/"tree"/"Product.cs").write_text("tampered")
        with self.assertRaises(ConflictError): self.tasks.apply(self.task["id"], result["proposal_hash"], accept_without_tests=True)

    def test_new_file_has_null_baseline(self):
        result = self.tasks.propose(self.task["id"], [{"path": "New.cs", "before_sha256": None, "content": "public class New {}\n"}])
        self.tasks.apply(self.task["id"], result["proposal_hash"], accept_without_tests=True)
        self.assertTrue((self.project_root/"New.cs").exists())

    def test_reject_leaves_original_untouched(self):
        self.stage()
        self.assertEqual(self.tasks.reject(self.task["id"])["state"], "rejected")
        self.assertEqual((self.project_root/"Product.cs").read_bytes(), self.original)

    def test_duplicate_paths_rejected(self):
        change = {"path": "Product.cs", "before_sha256": sha256(self.original), "content": "public class Product {}"}
        with self.assertRaises(PolicyError): self.tasks.propose(self.task["id"], [change, change])

    def test_failure_on_second_file_rolls_back_first(self):
        notes = (self.project_root/"notes.md").read_bytes()
        result = self.tasks.propose(self.task["id"], [
            {"path": "Product.cs", "before_sha256": sha256(self.original), "content": "public class Product {}\n"},
            {"path": "notes.md", "before_sha256": sha256(notes), "content": "changed note\n"},
        ])
        failed = False
        def fail_once(path, data, mode=0o600):
            nonlocal failed
            if path == self.project_root/"notes.md" and not failed:
                failed = True
                raise OSError("Injected disk failure")
            atomic_write(path, data, mode)
        with patch("localauthor.tasks.atomic_write", side_effect=fail_once):
            with self.assertRaises(OSError): self.tasks.apply(self.task["id"], result["proposal_hash"], accept_without_tests=True)
        self.assertEqual((self.project_root/"Product.cs").read_bytes(), self.original)
        self.assertEqual((self.project_root/"notes.md").read_bytes(), notes)
        self.assertEqual(self.tasks.get(self.task["id"])["state"], "rolled_back")

    def test_revised_proposal_restores_removed_staged_file(self):
        notes = (self.project_root/"notes.md").read_bytes()
        self.stage()
        self.tasks.propose(self.task["id"], [{"path": "notes.md", "before_sha256": sha256(notes), "content": "new note"}])
        self.assertEqual((self.tasks.base(self.task["id"])/"tree"/"Product.cs").read_bytes(), self.original)

    def test_feedback_does_not_train(self):
        result = self.tasks.feedback(self.task["id"], "attempted", "Ainda não validado.")
        self.assertFalse(result["weights_updated"])
        self.assertFalse(result["training_candidate_approved"])

    def test_runner_disabled_without_pinned_image(self):
        self.stage()
        runner = SandboxRunner(self.settings, self.tasks)
        with self.assertRaises(PolicyError): runner.run(self.task["id"], "python-tests", "")

    def test_runner_command_has_os_isolation_flags(self):
        self.settings.docker_image = "local/test@sha256:" + "a"*64
        runner = SandboxRunner(self.settings, self.tasks)
        cmd = runner.command(self.task["id"], "python-tests", "", "localai-test")
        for flag in ["--network=none", "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges", "--pull=never", "--user=65534:65534"]:
            self.assertIn(flag, cmd)
        self.assertNotIn("/var/run/docker.sock", " ".join(cmd))

    def test_runner_rejects_arbitrary_command(self):
        self.settings.docker_image = "local/test@sha256:"+"a"*64
        with self.assertRaises(PolicyError): SandboxRunner(self.settings, self.tasks).command(self.task["id"], "shell", "rm -rf /", "localai-test")

    def test_recovery_not_available_for_applied_task(self):
        p = self.stage(); self.tasks.apply(self.task["id"], p["proposal_hash"], accept_without_tests=True)
        with self.assertRaises(ConflictError): self.tasks.recover(self.task["id"])

    def test_build_success_not_equivalent_to_tests(self):
        proposal = self.stage()
        with self.store.connect() as db:
            db.execute("UPDATE tasks SET test_result=? WHERE id=?", (json.dumps({"exit_code":0,"kind":"dotnet-build","proposal_hash":proposal["proposal_hash"]}), self.task["id"]))
        with self.assertRaises(PolicyError):
            self.tasks.apply(self.task["id"], proposal["proposal_hash"])

    def test_runner_mount_is_readonly_and_work_is_temporary(self):
        self.settings.docker_image="local/test@sha256:"+"a"*64
        cmd=SandboxRunner(self.settings,self.tasks).command(self.task["id"],"python-tests","","localai-test")
        self.assertTrue(any("target=/workspace,readonly" in part for part in cmd))
        self.assertIn("--workdir=/tmp",cmd)
        self.assertIn('exec "$@"',cmd[-6] if False else SandboxRunner.bootstrap_script("python-tests"))
