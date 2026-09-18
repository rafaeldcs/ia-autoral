import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('investigation_course', ROOT / 'qa/investigation_course.py')
course = importlib.util.module_from_spec(spec)
spec.loader.exec_module(course)


class InvestigationCourseTests(unittest.TestCase):
    def test_holdout_changes_wording_and_keeps_closed_scope_explicit(self):
        splits = {name: course.examples(name) for name in ('train', 'validation', 'test')}
        self.assertEqual([len(splits[s]) for s in splits], [36, 12, 12])
        seen = set()
        for rows in splits.values():
            prompts = {row['prompt'] for row in rows}
            self.assertFalse(seen & prompts)
            seen |= prompts
            self.assertEqual({row['family'] for row in rows}, set(course.LESSONS))
            self.assertTrue(all(len((r['prompt'] + r['answer']).encode()) + 2 <= 256 for r in rows))

    def test_response_loss_gradient_ignores_prompt_positions(self):
        import numpy as np
        from localauthor.nn.tensor import Tensor
        spec = importlib.util.spec_from_file_location('train_investigation', ROOT / 'scripts/train-investigation.py')
        training = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(training)
        values = np.array([[[.3, -.2, .7], [.1, .4, -.1]]])
        logits = Tensor(values.copy(), requires_grad=True)
        target, mask = np.array([[1, 2]]), np.array([[0., 1.]])
        loss = training.response_loss(logits, target, mask)
        loss.backward()
        self.assertTrue(np.all(logits.grad[0, 0] == 0))
        delta = 1e-5
        plus, minus = values.copy(), values.copy()
        plus[0, 1, 2] += delta; minus[0, 1, 2] -= delta
        numeric = (training.response_loss(Tensor(plus), target, mask).data -
                   training.response_loss(Tensor(minus), target, mask).data) / (2 * delta)
        self.assertAlmostEqual(float(logits.grad[0, 1, 2]), float(numeric), places=6)

    def test_evaluation_never_repairs_model_output(self):
        from localauthor.nn.tokenizer import ByteTokenizer
        spec = importlib.util.spec_from_file_location('train_investigation', ROOT / 'scripts/train-investigation.py')
        training = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(training)
        tokenizer = ByteTokenizer()
        case = course.examples('test')[0]
        class Candidate:
            def generate(self, *args, **kwargs):
                return tokenizer.encode('Explanation: ' + case['answer'])
        result = training.evaluate(Candidate(), tokenizer, [case])[0]
        self.assertFalse(result['passed'])
        self.assertTrue(result['generated'].startswith('Explanation:'))
