"""Descriptor metadata regression; also runs on Linux to model Windows #157671."""
import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from localauthor.efficiency.weight_store import WeightBlock, WeightStore


class DescriptorMetadataTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / "weights.dat"
        self.path.write_bytes(b"aaaa")

    def store(self):
        block = WeightBlock("weights.dat", 0, 4, hashlib.sha256(b"aaaa").hexdigest())
        return WeightStore(self.root, {"a": block}, cache_bytes=4, max_block_bytes=4)

    def test_path_and_descriptor_timestamps_are_not_mixed(self):
        original = Path.stat
        target = self.path
        def altered_path_stat(path, *args, **kwargs):
            info = original(path, *args, **kwargs)
            if path != target:
                return info
            values = {name: getattr(info, name) for name in dir(info) if name.startswith("st_")}
            values["st_ctime_ns"] += 123456789
            return SimpleNamespace(**values)
        with patch.object(Path, "stat", altered_path_stat):
            store = self.store()
            self.assertEqual(store.get("a"), b"aaaa")
            self.assertEqual(store.get("a"), b"aaaa")
            self.assertEqual(store.stats()["read_bytes"], 4)


if __name__ == "__main__":
    unittest.main()
