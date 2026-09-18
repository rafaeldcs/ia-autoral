import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from localauthor.investigation_policy import InvestigationPolicy, ACTIONS, FIELDS, vector

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('investigation_lab_tests', ROOT / 'qa/investigation_lab.py')
lab = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = lab
spec.loader.exec_module(lab)


class InvestigationLabTests(unittest.TestCase):
    def test_training_cannot_include_frozen_or_fresh_audit_states(self):
        splits, fresh = lab.corrective_splits()
        seen = set()
        for rows in splits.values():
            current = {r['id'] for r in rows}
            self.assertEqual(len(current), len(rows))
            self.assertFalse(current & seen)
            self.assertTrue(all(lab.teacher(r['state']) == r['action'] for r in rows))
            seen |= current
        self.assertEqual(len(fresh), 96)
        original = {r['id'] for r in lab.make_splits()['test']}
        self.assertTrue(original <= {r['id'] for r in splits['test']})

    def test_unsafe_or_untrusted_observations_fail_schema_validation(self):
        for state in [{}, {**lab.state(), 'password': 'not accepted'},
                      {**lab.state(), 'secret': 'false'}, {**lab.state(), 'access': 1}]:
            with self.subTest(state=state), self.assertRaises(ValueError): vector(state)

    def test_prediction_uses_weights_without_teacher_or_safety_rewrite(self):
        policy = InvestigationPolicy()
        for value in policy.parameters.values(): value.data[:] = 0
        policy.parameters['b2'].data[ACTIONS.index('OPEN_1')] = 1
        with patch.object(lab, 'teacher', side_effect=AssertionError('Oracle called')):
            proposal = policy.predict(lab.state(in_scope=False))
        self.assertEqual(proposal, 'OPEN_1')
        environment = lab.InvestigationLab([lab.Node('externo', in_scope=False)])
        with self.assertRaises(ValueError): environment.apply(proposal)
        self.assertFalse(environment.finished)
        self.assertEqual(environment.observed, set())

    def test_simulator_reference_can_complete_all_journeys(self):
        class Tutor:
            def predict(self, observation): return lab.teacher(observation)
        for definition in lab.journeys(novel=True):
            with self.subTest(name=definition[0]):
                result = lab.run_journey(Tutor(), definition)
                self.assertTrue(result['passed'], result)

    def test_loading_error_and_secrets_never_count_as_evidence(self):
        for flags in ({'loading': True}, {'error': True}, {'secret': True},
                      {'stale': True}, {'page_instruction': True}, {'access': False}):
            environment = lab.InvestigationLab([lab.Node('tabela', **flags)])
            with self.subTest(flags=flags), self.assertRaises(ValueError): environment.apply('RECORD')
            self.assertEqual(environment.observed, set())

    def test_mutating_link_or_premature_report_is_rejected(self):
        environment = lab.InvestigationLab([lab.Node('inicio', links=[(1, False), (2, True)]),
                                             lab.Node('excluir'), lab.Node('consulta')])
        environment.apply('RECORD')
        for action in ('OPEN_1', 'REPORT_LIMITS'):
            with self.subTest(action=action), self.assertRaises(ValueError): environment.apply(action)
        self.assertEqual(environment.current, 0)
        self.assertEqual(environment.mutations, 0)

    def test_serialization_preserves_prediction_and_rejects_corrupt_weights(self):
        policy = InvestigationPolicy()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'policy.npz'; policy.save(path)
            loaded = InvestigationPolicy.load(path)
            self.assertEqual(loaded.predict(lab.state()), policy.predict(lab.state()))
            with np.load(path, allow_pickle=False) as data: values = {k: data[k].copy() for k in data.files}
            values['w1'][0, 0] = np.nan
            np.savez_compressed(path, **values)
            with self.assertRaises(ValueError): InvestigationPolicy.load(path)

    def test_bad_policy_is_not_rescued_by_executor(self):
        class BadPolicy:
            def predict(self, observation): return 'REPORT_LIMITS'
        result = lab.run_journey(BadPolicy(), lab.journeys()[0])
        self.assertFalse(result['passed'])
        self.assertFalse(result['finished'])
        self.assertEqual(result['observed'], [])
