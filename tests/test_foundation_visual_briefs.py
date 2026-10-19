"""Brief schema contracts; do not prove image quality or model competence."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch
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

    def test_failed_real_capture_contract_closes_service_and_preserves_report(self):
        # Lifecycle doubles prove cleanup, not CUDA/model/image capability.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); briefs = root / 'briefs.json'; output = root / 'capture'
            briefs.write_text(json.dumps(self.document()), encoding='utf-8')
            service = SimpleNamespace(create_image=Mock(side_effect=PolicyError('fixture failure')),
                                      close=Mock(), _cache={'image': object()})
            tensor = MagicMock(); tensor.__mul__.return_value.sum.return_value.item.return_value = 12
            torch = SimpleNamespace(arange=Mock(return_value=tensor), __version__='test-double',
                version=SimpleNamespace(cuda='test-double'), cuda=SimpleNamespace(
                    is_available=lambda: True, get_device_name=lambda _: 'test-double', max_memory_allocated=lambda: 0))
            def register(weights, manifest, **kwargs):
                manifest.parent.mkdir(parents=True); manifest.write_text('{}', encoding='utf-8')
            with patch.object(sys, 'argv', ['worker', '--weights', str(root / 'weights'), '--briefs', str(briefs), '--output', str(output)]), \
                 patch.dict(sys.modules, {'torch': torch}), patch.object(module, 'require_isolated_process', return_value={'test_double': True}), \
                 patch.object(module, 'register_model', side_effect=register), patch.object(module, 'FoundationService', return_value=service):
                self.assertEqual(module.main(), 1)
            service.close.assert_called_once()
            report = json.loads((output / 'report.json').read_text(encoding='utf-8'))
            self.assertEqual(report['delivered'], 0)
            self.assertEqual(report['results'][0]['error'], 'fixture failure')
            self.assertFalse(report['quality_qualified'])
