import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from localauthor.cli import main
from localauthor.config import Settings


class CaptureCliTests(unittest.TestCase):
    def test_offline_requires_job_permission_and_does_not_change_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            settings = Settings.load(home)
            self.assertTrue(settings.offline)
            args = ['--home', str(home), 'capture', 'https://example.org/',
                    '--policy-report', str(home / 'policy.json')]
            with patch('localauthor.browser_capture.capture', return_value={'captured': 1}) as run:
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(args), 2)
                run.assert_not_called()
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(args + ['--allow-network']), 0)
                run.assert_called_once_with(['https://example.org/'], home / 'policy.json', home, [])
            self.assertTrue(Settings.load(home).offline)

    def test_unavailable_sandbox_is_failure_not_host_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch('localauthor.browser_capture.capture', side_effect=RuntimeError('Sandbox unavailable')) as run:
                with contextlib.redirect_stderr(io.StringIO()) as error:
                    result = main(['--home', folder, 'capture', 'https://example.org/',
                                   '--policy-report', 'policy.json', '--allow-network'])
                self.assertEqual(result, 2)
                self.assertIn('sem alternativa no host', error.getvalue())
                run.assert_called_once()
