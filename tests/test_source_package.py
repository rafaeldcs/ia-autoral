"""Source packaging tests, not model or deployment qualification."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

PATH = Path(__file__).resolve().parents[1] / "scripts" / "package-source.py"
SPEC = importlib.util.spec_from_file_location("package_source", PATH)
packager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(packager)


class SourcePackageTests(unittest.TestCase):
    def test_inventory_rejects_runtime_data_and_weights(self):
        for path in ("model.safetensors", ".env", "runtime-data/settings.json", "api.token", "private.key", "model.gguf"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                packager.check_inventory(("100644 blob " + "a" * 40 + "\t" + path + "\0").encode())

    def test_inventory_rejects_links_and_empty_tree(self):
        with self.assertRaises(ValueError): packager.check_inventory(b"")
        with self.assertRaises(ValueError): packager.check_inventory(b"120000 blob aaa\tlink\0")

    def test_inventory_accepts_source(self):
        packager.check_inventory(b"100644 blob aaa\tsrc/main.py\0")

    def repo(self, root):
        subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
        (root / "main.py").write_text("print('fixture')\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "main.py"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                        "-c", "commit.gpgsign=false", "commit", "-m", "synthetic source fixture"], check=True, capture_output=True)

    def test_clean_commit_archive_is_hash_bound_and_excludes_untracked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            self.repo(root)
            (root / "api.token").write_text("synthetic-not-a-credential", encoding="utf-8")
            output = Path(temp) / "output"
            result = packager.build(root, output)
            archive = output / result["archive"]
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), result["sha256"])
            self.assertEqual(result, json.loads((output / (archive.name + ".json")).read_text(encoding="utf-8")))
            with zipfile.ZipFile(archive) as zipped:
                self.assertIn("LocalAuthor/main.py", zipped.namelist())
                self.assertNotIn("LocalAuthor/api.token", zipped.namelist())
            self.assertFalse(result["models_trained"])
            with self.assertRaises(FileExistsError): packager.build(root, output)

    def test_dirty_tracked_source_refuses_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            self.repo(root)
            (root / "main.py").write_text("# modified\n", encoding="utf-8")
            with self.assertRaises(ValueError): packager.build(root, Path(temp) / "output")
