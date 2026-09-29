import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from qa.terreiro_qa_policy import TerreiroQaPolicy, FIELDS, curriculum

class TerreiroPolicyTests(unittest.TestCase):
    def test_invalid_observation_fails_closed(self):
        model=TerreiroQaPolicy()
        with self.assertRaises(ValueError): model.predict({'authorized':True})
        with self.assertRaises(ValueError): model.predict({key:1 for key in FIELDS})

    def test_saved_inference_does_not_call_teacher(self):
        model=TerreiroQaPolicy();state={key:False for key in FIELDS}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'model.npz';model.save(path)
            with patch('qa.terreiro_qa_policy.teacher',side_effect=AssertionError('Oracle leak')):
                self.assertEqual(model.predict(state),TerreiroQaPolicy.load(path).predict(state))

    def test_training_and_assessment_inputs_are_disjoint(self):
        splits=curriculum()
        sets=[{tuple(row['state'][key] for key in FIELDS) for row in rows} for rows in splits.values()]
        self.assertTrue(all(not left.intersection(right) for i,left in enumerate(sets) for right in sets[i+1:]))
