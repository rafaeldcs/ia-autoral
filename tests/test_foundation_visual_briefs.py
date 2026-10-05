"""Brief schema contracts; do not prove image quality or model competence."""
import importlib.util
from pathlib import Path
import unittest
from localauthor.errors import PolicyError

spec = importlib.util.spec_from_file_location("visual_briefs", Path(__file__).resolve().parents[1] / "scripts/foundation-visual-briefs.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class VisualBriefTests(unittest.TestCase):
    def document(self):
        return {"schema": 1, "frozen": True, "briefs": [{"id": "fixture", "prompt": "Original fixture", "purpose": "Review", "seed": 31}]}

    def test_requires_frozen_bounded_and_nonempty_lot(self):
        for document in ({}, {**self.document(), "frozen": False}, {**self.document(), "briefs": []}, {**self.document(), "briefs": self.document()["briefs"] * 21}):
            with self.assertRaises(PolicyError): module.validate_briefs(document)
        self.assertEqual(len(module.validate_briefs(self.document())), 1)

    def test_rejects_duplicate_ids_path_escape_and_boolean_seed(self):
        for changes in ({"id": "../outside"}, {"seed": True}, {"seed": -1}, {"prompt": " "}, {"purpose": "x" * 2001}):
            document = self.document(); document["briefs"][0].update(changes)
            with self.assertRaises(PolicyError): module.validate_briefs(document)
        document = self.document(); document["briefs"] *= 2
        with self.assertRaises(PolicyError): module.validate_briefs(document)
