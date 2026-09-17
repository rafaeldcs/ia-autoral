import json
import tempfile
import time
import unittest
from pathlib import Path
from localauthor.config import Settings
from localauthor.store import Store
from localauthor.util import sha256, write_json


class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.settings = Settings.load(self.root/"data")
        self.project_root = self.root/"project"
        self.project_root.mkdir()
        (self.project_root/"Product.cs").write_bytes(b"public class Product { public int Quantity = 1; }\r\n")
        (self.project_root/"notes.md").write_text("Estoque negativo deve ser bloqueado.\nDocumentação de validação.\n", encoding="utf-8")
        self.store = Store(self.settings.home/"memory.sqlite3")
        self.project = self.store.add_project("Laboratório", str(self.project_root))

    def tearDown(self):
        self.temp.cleanup()


def wait_until(check, seconds=4):
    deadline = time.monotonic()+seconds
    while time.monotonic() < deadline:
        value = check()
        if value: return value
        time.sleep(0.01)
    raise AssertionError("Condição não foi atingida no tempo do teste.")


def make_dataset(root: Path, train="abcd"*80, validation="dcba"*80):
    root.mkdir(parents=True, exist_ok=True)
    records = []
    for split, text in [("train", train), ("validation", validation), ("test", "held out test material unrelated to the training record")]:
        filename = split+".txt"
        raw = text.encode("utf-8")
        (root/filename).write_bytes(raw)
        records.append({"path": filename, "split": split, "group": "group-"+split, "sha256": sha256(raw), "training_allowed": split!="test", "provenance": {"kind": "human-authored", "owner": "numerical-unit-test-fixture", "license_or_permission": "Fixture numérica de teste, não corpus de programação."}})
    manifest = root/"manifest.json"
    write_json(manifest, {"schema_version": 1, "dataset_id": "unit-test-only", "records": records})
    return manifest
