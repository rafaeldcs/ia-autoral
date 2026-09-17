"""Teaching imports must not leak held-out examples into searchable memory."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest

spec = importlib.util.spec_from_file_location('teach_local', Path(__file__).resolve().parents[1] / 'scripts' / 'teach-local.py')
teaching = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teaching)


class TeachingTests(unittest.TestCase):
    def test_only_training_examples_imported_and_project_reused(self):
        root = Path(__file__).resolve().parent
        client = Mock()
        client.request.side_effect = [[{'id': 'existing', 'root': str(root)}], {'id': 'source'}]
        dataset = {'dataset_id': 'demo', 'splits': {
            'train': [{'path': 'train.txt', 'text': 'allowed', 'sha256': 'hash'}],
            'validation': [{'path': 'val.txt', 'text': 'held out'}],
            'test': [{'path': 'test.txt', 'text': 'secret test'}]}}
        project, imported = teaching.import_lessons(client, dataset, root, 'Demo')
        self.assertEqual(project['id'], 'existing')
        self.assertEqual(len(imported), 1)
        self.assertEqual(client.request.call_count, 2)
        client.request.assert_called_with('/api/import', {'scope': 'existing', 'title': 'demo / train.txt', 'content': 'allowed'})

    def test_missing_authorization_fails_before_loading_settings(self):
        with patch.object(teaching.Settings, 'load') as load:
            with self.assertRaisesRegex(ValueError, 'approved-dataset'):
                teaching.main(SimpleNamespace(approved_dataset=False))
            load.assert_not_called()

    def test_project_created_when_missing(self):
        root = Path(__file__).resolve().parent
        client = Mock()
        client.request.side_effect = [[], {'id': 'new', 'root': str(root)}]
        project, imported = teaching.import_lessons(client, {'dataset_id': 'empty', 'splits': {'train': []}}, root, 'New')
        self.assertEqual(project['id'], 'new')
        self.assertEqual(imported, [])
        client.request.assert_called_with('/api/projects', {'name': 'New', 'root': str(root)})
