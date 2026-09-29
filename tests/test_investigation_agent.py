import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from localauthor.errors import PolicyError
from localauthor.investigation_agent import inspect_source, validate_action, observation, Investigation, NeuralPolicy
from qa.investigation_agent_course import lessons, challenges, observation as training_observation

SOURCE = b"export function showDate(value) {\n  const date = new Date(value);\n  if (!Number.isFinite(date.getTime())) return 'Sem data';\n  return date.toISOString();\n}\n"


class InvestigationAgentTests(unittest.TestCase):
    def test_evaluation_report_is_not_in_training_and_all_case_kinds_present(self):
        course = lessons()
        train = {r['prompt'] for r in course['train']}
        validation = {r['prompt'] for r in course['validation']}
        self.assertFalse(train & validation)
        for case in challenges():
            if case['partition'] == 'fresh':
                self.assertNotIn(observation('inicio', case['report']), train | validation)
            self.assertNotIn('path', case)
            self.assertNotIn('symbol', case)
        self.assertEqual({c['kind'] for c in challenges()}, {'bug', 'clean', 'unknown', 'error', 'failed-tests'})
        self.assertEqual({c['position'] for c in challenges() if c['kind'] == 'bug'}, {0, 1, 2, 3})

    def test_training_and_runtime_observations_agree(self):
        self.assertEqual(observation('inicio', 'relato'), training_observation('inicio', 'relato'))
        for group in lessons().values():
            for row in group:
                stage = row['prompt'].split('\n')[1].removeprefix('Etapa: ')
                validate_action(stage, row['answer'])

    def test_tool_injection_and_out_of_order_apply_are_rejected(self):
        for stage, action in [('inicio', 'BUSCAR .env'), ('inicio', 'ENTREGAR_REVISAO'), ('busca', 'LER ../../private'),
                              ('leitura', 'CORRIGIR_AUSENCIA'), ('testes', 'TESTAR; rm -rf /'), ('erro', 'ENTREGAR_REVISAO')]:
            with self.subTest(stage=stage, action=action), self.assertRaises(PolicyError):
                validate_action(stage, action)

    def test_inspection_discovers_symbol_from_source_not_teacher_argument(self):
        context = inspect_source('app/src/lib/neutral.mjs', SOURCE)
        self.assertEqual(context['request']['name'], 'showDate')
        self.assertEqual(context['beforeHash'], hashlib.sha256(SOURCE).hexdigest())
        self.assertIn('showDate(value)', context['prompt'])
        with self.assertRaises(PolicyError):
            inspect_source('a.mjs', SOURCE + SOURCE)
        with self.assertRaises(PolicyError):
            inspect_source('a.mjs', SOURCE.replace(b'Sem data', b'unknown'))

    def test_changed_checkpoint_never_loads_model(self):
        with tempfile.TemporaryDirectory() as directory, patch('localauthor.nn.checkpoint.load_checkpoint') as load:
            checkpoint = Path(directory) / 'test.npz'
            checkpoint.write_bytes(b'changed')
            with self.assertRaises(PolicyError):
                NeuralPolicy(checkpoint, 'not-the-hash')
            load.assert_not_called()

    def agent(self, root, policy):
        # Only tool stubs are exercised in these tests, never project code on host.
        guard = patch('localauthor.investigation_agent.Path.is_file', return_value=True)
        with guard:
            return Investigation(root, root / 'evidence', root / 'home', policy)

    def make_source(self, root):
        file = root / 'app/src/lib/neutral.mjs'
        file.parent.mkdir(parents=True)
        file.write_bytes(SOURCE)
        return file

    def test_unsafe_policy_cannot_claim_success_or_run_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = self.make_source(root)
            agent = self.agent(root, lambda _: 'ENTREGAR_REVISAO')
            with patch.object(agent, 'run_node') as execute:
                result = agent.execute('A tela mostra 1969 sem data.')
            self.assertEqual(result['state'], 'needs_help')
            self.assertEqual(file.read_bytes(), SOURCE)
            execute.assert_not_called()

    def test_observed_bug_cannot_be_skipped_and_reported_clean(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = self.make_source(root)
            actions = iter(['BUSCAR new Date', 'LER 0', 'PROVAR null', 'PROXIMO'])
            agent = self.agent(root, lambda _: next(actions))
            with patch.object(agent, 'run_node', return_value=(0, '"1970-01-01"')):
                result = agent.execute('A tela mostra 1969 sem data.')
            self.assertEqual(result['state'], 'needs_help')
            self.assertEqual(result['changed'], [])
            self.assertEqual(file.read_bytes(), SOURCE)
            self.assertTrue(any(e['event'] == 'blocked' for e in agent.events))

    def test_clean_probe_requires_exhausted_search_to_close(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_source(root)
            actions = iter(['BUSCAR new Date', 'LER 0', 'PROVAR null', 'PROXIMO', 'SEM_REPRODUCAO'])
            agent = self.agent(root, lambda _: next(actions))
            with patch.object(agent, 'run_node', return_value=(0, '"Sem data"')):
                result = agent.execute('A tela mostra 1969 sem data.')
            self.assertEqual(result['state'], 'not_reproduced')
            self.assertFalse(result['appliedToOriginal'])

    def test_execution_failure_does_not_trigger_a_patch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_source(root)
            actions = iter(['BUSCAR new Date', 'LER 0', 'PROVAR null', 'PEDIR_AJUDA'])
            agent = self.agent(root, lambda _: next(actions))
            with patch.object(agent, 'run_node', return_value=(1, 'TypeError')):
                result = agent.execute('A tela mostra 1969 sem data.')
            self.assertEqual(result['state'], 'needs_help')
            self.assertEqual(result['changed'], [])

    def test_no_host_fallback(self):
        with tempfile.TemporaryDirectory() as directory, patch('localauthor.investigation_agent.Path.is_file', return_value=False):
            root = Path(directory)
            with self.assertRaises(PolicyError):
                Investigation(root, root / 'out', root / 'home', lambda _: 'PEDIR_AJUDA')
