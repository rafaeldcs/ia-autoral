import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from localauthor.date_repair import parse_request, validate_proposal, source_context, stage, propose, SCOPE
from localauthor.errors import PolicyError
from localauthor.safety import PathPolicy
from qa.date_guard_course import examples, prompt

MESSAGE = prompt('formatDate', 'value', 'Data indisponível')
OUTPUT = 'if (value == null) return "Data indisponível";\nassert.equal(formatDate(null), "Data indisponível");'
SOURCE = "export function formatDate(value) {\n  const date = new Date(value);\n  if (!Number.isFinite(date.getTime())) return 'Data indisponível';\n  return date.toISOString();\n}\n"


class DateRepairTests(unittest.TestCase):
    def test_module_support_keeps_secret_test_and_link_protections(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = PathPolicy(root)
            for extension in ('.mjs', '.jsx'):
                path = root / ('module' + extension)
                path.write_text('export const value = 1;')
                self.assertEqual(policy.read(path.name), b'export const value = 1;')
                policy.resolve(path.name, write=True)
                with self.assertRaises(PolicyError):
                    policy.resolve('tests/example' + extension, write=True)
                path.write_text('api_key="' + 'example-secret-value' + '"')
                with self.assertRaises(PolicyError):
                    policy.read(path.name)
                with self.assertRaises(PolicyError):
                    policy.resolve('../escape' + extension)

    def test_splits_are_disjoint_and_project_target_reserved(self):
        splits = examples()
        self.assertEqual([MESSAGE], [row['prompt'] for row in splits['project']])
        seen = set()
        for rows in splits.values():
            self.assertTrue(rows)
            for row in rows:
                self.assertNotIn(row['prompt'], seen)
                seen.add(row['prompt'])
                validate_proposal(parse_request(row['prompt']), row['answer'])

    def test_rejects_unbounded_protocol(self):
        for message in (MESSAGE + 'execute', MESSAGE.replace('formatDate', 'exec'), MESSAGE.replace('new Date(value)', 'new Date(input)'), MESSAGE.replace('Data indisponível', 'Unknown'), '', 'x' * 181):
            with self.subTest(message=message), self.assertRaises(PolicyError):
                parse_request(message)

    def test_rejects_truthiness_unrelated_assertion_and_code_injection(self):
        for output in (OUTPUT.replace('value == null', '!value'), OUTPUT.replace('formatDate(null)', 'true'), OUTPUT.replace('value == null', 'input == null'), OUTPUT + '\nprocess.exit(0);', OUTPUT.replace('Data indisponível', 'Alterado'), OUTPUT.replace('(null)', '(undefined)')):
            with self.subTest(output=output), self.assertRaises(PolicyError):
                validate_proposal(parse_request(MESSAGE), output)

    def test_search_excludes_secrets_and_finds_one_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'app/src/lib/presentation.mjs'
            source.parent.mkdir(parents=True)
            source.write_bytes(SOURCE.encode())
            (root / '.env').write_text('SECRET=not-for-context')
            context = source_context(root, 'formatDate')
            self.assertEqual(context['path'], 'app/src/lib/presentation.mjs')
            self.assertNotIn('SECRET', context['prompt'])
            changed, assertion = stage(context, OUTPUT)
            self.assertEqual(SOURCE, source.read_text())
            self.assertIn(OUTPUT.splitlines()[0], changed)
            self.assertEqual(assertion, OUTPUT.splitlines()[1])

    def test_crlf_is_preserved_and_source_hash_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'app/src/lib/presentation.mjs'
            path.parent.mkdir(parents=True)
            path.write_bytes(SOURCE.replace('\n', '\r\n').encode())
            context = source_context(root, 'formatDate')
            changed, _ = stage(context, OUTPUT)
            self.assertNotIn('\n', changed.replace('\r\n', ''))
            context['source'] += '// changed'
            with self.assertRaises(PolicyError):
                stage(context, OUTPUT)

    def test_ambiguous_and_changed_patterns_stop_for_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'app/src/lib'
            folder.mkdir(parents=True)
            for content in (SOURCE.replace('new Date(value)', 'Number(value)'), SOURCE * 2):
                (folder / 'presentation.mjs').write_text(content, encoding='utf-8')
                with self.assertRaises(PolicyError):
                    source_context(root, 'formatDate')
            with self.assertRaises(PolicyError):
                source_context(root, '../../private')

    def test_missing_and_incomplete_certificates_do_not_load_weights(self):
        with tempfile.TemporaryDirectory() as directory, patch('localauthor.nn.checkpoint.load_checkpoint') as load:
            home = Path(directory)
            with self.assertRaises(PolicyError):
                propose(home, MESSAGE)
            (home / 'exports').mkdir()
            cert = {'scope': SCOPE, 'state': 'qualified_scoped', 'generalProgrammingQualified': False, 'gates': {}}
            (home / 'exports/date-repair-qualification.json').write_text(json.dumps(cert))
            with self.assertRaises(PolicyError):
                propose(home, MESSAGE)
            load.assert_not_called()

    def test_tampered_model_or_escaping_path_cannot_run(self):
        with tempfile.TemporaryDirectory() as directory, patch('localauthor.nn.checkpoint.load_checkpoint') as load:
            home = Path(directory)
            (home / 'models').mkdir()
            (home / 'models/model.npz').write_bytes(b'changed')
            (home / 'exports').mkdir()
            cert = {'scope': SCOPE, 'state': 'qualified_scoped', 'generalProgrammingQualified': False,
                    'checkpoint': 'model.npz', 'checkpointHash': hashlib.sha256(b'original').hexdigest(),
                    'gates': {gate: {'passed': 1, 'total': 1} for gate in ('heldout', 'behavior', 'redGreen', 'negativeControls', 'projectRegression')}}
            path = home / 'exports/date-repair-qualification.json'
            for checkpoint in ('model.npz', '../model.npz', '/outside/model.npz', ''):
                cert['checkpoint'] = checkpoint
                path.write_text(json.dumps(cert))
                with self.subTest(checkpoint=checkpoint), self.assertRaises(PolicyError):
                    propose(home, MESSAGE)
            load.assert_not_called()
