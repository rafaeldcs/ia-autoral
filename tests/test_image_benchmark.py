import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('image_benchmark', Path(__file__).resolve().parents[1] / 'scripts/foundation-image-benchmark.py')
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


class ImageBenchmarkTests(unittest.TestCase):
    def document(self):
        return {'schema': 1, 'frozen': True, 'cases': [
            {'id': 'shopair', 'prompt': 'A blue shipping box', 'options': {'seed': 1101}}]}

    def test_frozen_case_preserves_exact_prompt_and_options(self):
        document = self.document()
        self.assertEqual(benchmark.validate_cases(document), document['cases'])

    def test_duplicate_unfrozen_excessive_and_injected_cases_are_rejected(self):
        for change in ['duplicate', 'unfrozen', 'path', 'excessive', 'field', 'blank', 'boolean-schema']:
            document = self.document()
            if change == 'duplicate': document['cases'] *= 2
            if change == 'unfrozen': document['frozen'] = False
            if change == 'path': document['cases'][0]['id'] = '../escape'
            if change == 'excessive': document['cases'] *= 21
            if change == 'field': document['cases'][0]['expected_image'] = 'answer'
            if change == 'blank': document['cases'][0]['prompt'] = ' '
            if change == 'boolean-schema': document['schema'] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                benchmark.validate_cases(document)
