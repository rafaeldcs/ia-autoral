"""Independent supervisor QA of LocalAuthor's proposed matrix-block adapter.

Tiny fixtures test contracts only. Real pretrained parity has a separate receipt.
LocalAuthor's rejected test drafts are not counted as successful autonomous work.
"""
import json
from pathlib import Path
import struct
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import numpy as np

from localauthor.errors import PolicyError
from localauthor.efficiency.safetensor_store import (
    build_matrix_store, decode_matrix, read_header, selected_blocks,
)
from localauthor.efficiency.weight_store import WeightStore


class MatrixStoreTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.path = self.root / "model.safetensors"

    def fixture(self, entries=None, raw=None):
        if raw is None:
            raw = struct.pack("<f", 1.0)
        if entries is None:
            entries = {"w": {"dtype": "F32", "shape": [1, 1], "data_offsets": [0, 4]}}
        header = json.dumps(entries).encode("utf-8")
        self.path.write_bytes(struct.pack("<Q", len(header)) + header + raw)
        return read_header(self.path)

    def store(self, entries=None, raw=None, **options):
        header, offset = self.fixture(entries, raw)
        blocks, metadata = selected_blocks(self.path, header, offset, ["w"], 64)
        return WeightStore(self.root, blocks, cache_bytes=64, max_block_bytes=64, **options), metadata

    def test_f32_bf16_exact_decoding_and_cache_accounting(self):
        cases = [("F32", struct.pack("<4f", 1, 2, -1, 0)),
                 ("BF16", struct.pack("<4H", 0x3f80, 0x4000, 0xbf80, 0))]
        for dtype, raw in cases:
            with self.subTest(dtype=dtype):
                store, metadata = self.store({"w": {"dtype": dtype, "shape": [2, 2],
                                                      "data_offsets": [0, len(raw)]}}, raw)
                for _ in range(2):
                    np.testing.assert_array_equal(decode_matrix(store, metadata, "w"), [[1, 2], [-1, 0]])
                self.assertEqual(store.stats()["hits"], 1)
                self.assertEqual(store.stats()["read_bytes"], len(raw))
                self.assertLessEqual(store.stats()["resident_bytes"], 64)
                store.clear()
                self.assertEqual(store.stats()["resident_bytes"], 0)

    def test_cancel_and_read_budget_prevent_reads(self):
        for cancellation in (True, False):
            with self.subTest(cancellation=cancellation):
                store, metadata = self.store(read_budget_bytes=None if cancellation else 0)
                event = threading.Event()
                if cancellation:
                    event.set()
                with self.assertRaises(PolicyError):
                    decode_matrix(store, metadata, "w", event)
                self.assertEqual(store.stats()["read_bytes"], 0)

    def test_nonfinite_values_are_rejected(self):
        for value in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=value):
                store, metadata = self.store(raw=struct.pack("<f", value))
                with self.assertRaises(PolicyError):
                    decode_matrix(store, metadata, "w")

    def test_invalid_headers(self):
        for raw in (b"bad", struct.pack("<Q", 0), struct.pack("<Q", 2000001),
                    struct.pack("<Q", 20) + b"{}", struct.pack("<Q", 1) + b"\xff",
                    struct.pack("<Q", 2) + b"[]"):
            with self.subTest(raw=raw):
                self.path.write_bytes(raw)
                with self.assertRaises(PolicyError):
                    read_header(self.path)

    def test_invalid_metadata(self):
        variants = [{"shape": shape} for shape in ([True, 1], [0, 1], [-1, 1], [1.0, 1], [1])]
        variants += [{"data_offsets": offsets} for offsets in
                     ([False, 4], [-1, 3], [0, 8], [4, 8], [0.0, 4], [0, 0], [0])]
        variants += [{"dtype": "I64"}, {"dtype": "F16"}]
        for variant in variants:
            with self.subTest(variant=variant):
                entry = {"dtype": "F32", "shape": [1, 1], "data_offsets": [0, 4], **variant}
                header, offset = self.fixture({"w": entry})
                with self.assertRaises(PolicyError):
                    selected_blocks(self.path, header, offset, ["w"], 64)

    def test_invalid_names_and_block_budgets(self):
        header, offset = self.fixture()
        for names, budget in [([], 64), ([""], 64), (["w", "w"], 64), ([True], 64),
                              (["missing"], 64), (["w"], True), (["w"], 0), (["w"], 3)]:
            with self.subTest(names=names, budget=budget), self.assertRaises(PolicyError):
                selected_blocks(self.path, header, offset, names, budget)
        blocks, _ = selected_blocks(self.path, header, offset, ["w"], 4)
        self.assertEqual(blocks["w"].length, 4)

    def test_overlapping_selected_matrices_rejected(self):
        entry = {"dtype": "F32", "shape": [1, 1], "data_offsets": [0, 4]}
        header, offset = self.fixture({"w": entry, "z": entry})
        with self.assertRaises(PolicyError):
            selected_blocks(self.path, header, offset, ["w", "z"], 64)

    def test_changed_file_invalidates_cache(self):
        store, metadata = self.store()
        decode_matrix(store, metadata, "w")
        self.path.write_bytes(self.path.read_bytes() + b"changed-size")
        with self.assertRaises(PolicyError):
            decode_matrix(store, metadata, "w")
        self.assertEqual(store.stats()["resident_bytes"], 0)

    def test_builder_requires_verification_before_inventory(self):
        self.fixture()
        verify = Mock(side_effect=PolicyError("synthetic rejected provenance"))
        spec = SimpleNamespace(directory=self.root, verify=verify)
        with self.assertRaises(PolicyError):
            build_matrix_store(spec, ["w"], cache_bytes=64, max_block_bytes=64)
        verify.assert_called_once_with()
        verify.reset_mock(side_effect=True)
        store, metadata = build_matrix_store(spec, ["w"], cache_bytes=64, max_block_bytes=64)
        verify.assert_called_once_with()
        np.testing.assert_array_equal(decode_matrix(store, metadata, "w"), [[1]])
