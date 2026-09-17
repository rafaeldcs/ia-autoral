import json
import os
import zipfile
from pathlib import Path
from unittest.mock import patch
from localauthor import backup
from localauthor.errors import PolicyError
from localauthor.safety import PathPolicy
from localauthor.util import sha256
from tests.helpers import WorkspaceCase


class BackupTests(WorkspaceCase):
    def archive(self, entries):
        path = self.root / 'crafted.zip'
        manifest = {name: sha256(data) for name, data in entries.items()}
        with zipfile.ZipFile(path, 'w') as archive:
            for name, data in entries.items():
                archive.writestr(name, data)
            archive.writestr('BACKUP_MANIFEST.json', json.dumps(manifest))
        return path

    def test_windows_names_and_case_collisions_rejected_everywhere(self):
        for names in [('CON.txt',), ('folder./x',), ('a:b',), ('a\\b',), ('x', 'X'), ('a', 'a/b'), ('API.TOKEN',), ('a/server.lock',), ('.',)]:
            with self.subTest(names=names):
                archive = self.archive({name: b'data' for name in names})
                with self.assertRaises(PolicyError):
                    backup.restore_home(archive, self.root / 'restore')
                self.assertFalse((self.root / 'restore').exists())

    def test_streaming_backup_and_restore_do_not_read_whole_files(self):
        payload = self.settings.home / 'models' / 'test.bin'
        payload.write_bytes(b'bounded-stream-test' * 100_000)
        path = self.root / 'backup.zip'
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('unbounded file read')):
            self.assertTrue(backup.backup_home(self.settings, path)['streaming'])
            self.assertTrue(backup.restore_home(path, self.root / 'restored')['streaming'])
        self.assertEqual(payload.read_bytes(), (self.root / 'restored/models/test.bin').read_bytes())

    def test_failed_backup_preserves_previous_archive(self):
        path = self.root / 'backup.zip'
        path.write_bytes(b'previous-good-backup')
        with patch.object(backup, 'copy_hash', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                backup.backup_home(self.settings, path)
        self.assertEqual(path.read_bytes(), b'previous-good-backup')
        self.assertFalse(list(self.root.glob('.localai-*')))

    def test_hash_failure_leaves_empty_destination_unchanged(self):
        path = self.root / 'backup.zip'
        backup.backup_home(self.settings, path)
        with zipfile.ZipFile(path) as archive:
            entries = {name: archive.read(name) for name in archive.namelist()}
        entries['settings.json'] = b'{}'
        with zipfile.ZipFile(path, 'w') as archive:
            for name, value in entries.items():
                archive.writestr(name, value)
        destination = self.root / 'restored'
        destination.mkdir()
        with self.assertRaisesRegex(PolicyError, 'corrompido'):
            backup.restore_home(path, destination)
        self.assertEqual(list(destination.iterdir()), [])
        self.assertFalse(list(self.root.glob('.localai-restore-*')))

    def test_invalid_settings_do_not_publish_partial_restore(self):
        (self.settings.home / 'settings.json').write_text('{"unknown_setting": true}')
        path = self.root / 'backup.zip'
        backup.backup_home(self.settings, path)
        with self.assertRaises(PolicyError):
            backup.restore_home(path, self.root / 'restored')
        self.assertFalse((self.root / 'restored').exists())

    def test_corrupt_database_is_rejected_even_with_matching_hash(self):
        path = self.archive({'memory.sqlite3': b'not SQLite', 'settings.json': b'{}'})
        with self.assertRaises(PolicyError):
            backup.restore_home(path, self.root / 'restored')
        self.assertFalse((self.root / 'restored').exists())

    def test_quota_failure_preserves_previous_archive(self):
        path = self.root / 'backup.zip'
        path.write_bytes(b'previous')
        with patch.object(backup, 'MAX_BYTES', 10), self.assertRaises(PolicyError):
            backup.backup_home(self.settings, path)
        self.assertEqual(path.read_bytes(), b'previous')

    def test_backup_rejects_hardlinks(self):
        source = self.root / 'private.txt'
        source.write_text('outside')
        os.link(source, self.settings.home / 'linked.txt')
        with self.assertRaises(PolicyError):
            backup.backup_home(self.settings, self.root / 'backup.zip')

    def make_directory_alias(self, target, alias):
        if os.name == 'nt':
            import _winapi
            _winapi.CreateJunction(str(target), str(alias))
            self.addCleanup(alias.rmdir)
        else:
            alias.symlink_to(target, target_is_directory=True)
            self.addCleanup(alias.unlink)

    def tearDown(self):
        # Remove only the aliases before TemporaryDirectory removes its targets.
        self.doCleanups()
        super().tearDown()

    def test_directory_alias_blocked_as_project_root_and_child(self):
        alias = self.project_root / 'alias'
        self.make_directory_alias(self.settings.home, alias)
        with self.assertRaises(PolicyError):
            PathPolicy(alias)
        with self.assertRaises(PolicyError):
            PathPolicy(self.project_root).read('alias/settings.json')
        self.assertFalse(any(name.startswith('alias/') for name in PathPolicy(self.project_root).files()))

    def test_backup_rejects_directory_alias(self):
        self.make_directory_alias(self.project_root, self.settings.home / 'alias')
        with self.assertRaises(PolicyError):
            backup.backup_home(self.settings, self.root / 'backup.zip')

    def test_restore_rejects_directory_alias_destination(self):
        alias = self.root / 'alias'
        self.make_directory_alias(self.project_root, alias)
        with self.assertRaises(PolicyError):
            backup.restore_home(self.root / 'missing.zip', alias / 'restored')
