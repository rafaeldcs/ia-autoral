import ast
import unittest
from pathlib import Path


class EvaluateComprovantesSafetyTests(unittest.TestCase):
    def test_script_has_no_host_fallback_and_no_training_call(self):
        source = Path(__file__).parents[1] / 'scripts/evaluate-comprovantes.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        text = source.read_text(encoding='utf-8')
        self.assertIn("Reviewed Docker sandbox required", text)
        self.assertNotIn('train(', text)
        self.assertNotIn('write_checkpoint', text)
        self.assertTrue(any(isinstance(node, ast.Call) and getattr(node.func, 'attr', '') == 'generate'
                            for node in ast.walk(tree)))
