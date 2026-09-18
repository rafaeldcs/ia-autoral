import copy
import tempfile
import unittest
from pathlib import Path

import numpy as np

from localauthor.browser_investigation import BrowserInvestigation
from localauthor.errors import PolicyError
from localauthor.investigation_text import (
    InvestigationText, encode, segments, annotate_observation,
)
from qa.investigation_text_course import make_splits


class InvestigationTextTests(unittest.TestCase):
    def test_split_integrity_and_contrasts_are_not_training_rows(self):
        splits = make_splits(corrective=True)
        keys = {s: {(r['kind'], r['text'].casefold()) for r in rows}
                for s, rows in splits.items()}
        self.assertFalse(keys['train'] & keys['test'])
        self.assertFalse(keys['train'] & keys['validation'])
        self.assertFalse(keys['test'] & keys['validation'])
        self.assertEqual(len(splits['test']), 64)
        self.assertEqual(sum(r['id'].startswith('fresh-') for r in splits['test']), 12)

    def test_encoding_preserves_negation_and_unicode(self):
        self.assertFalse(np.array_equal(encode('Excluir relatório'), encode('Não excluir relatório')))
        np.testing.assert_array_equal(encode('AÇÃO'), encode('ac\u0327a\u0303o'))
        self.assertAlmostEqual(np.linalg.norm(encode('Informações')), 1)
        for invalid in ('', '  ', None, 'x' * 601):
            with self.assertRaises(ValueError):
                encode(invalid)

    def test_segmentation_is_lossless_including_long_lines_and_whitespace(self):
        text = 'Ação\r\n\n' + 'ç' * 1400 + '\n\t  \n' + 'Fim'
        blocks = list(segments(text))
        self.assertEqual(''.join(b['text'] for b in blocks), text)
        for block in blocks:
            self.assertEqual(text[block['start']:block['end']], block['text'])
            self.assertLessEqual(len(block['text']), 600)
        with self.assertRaises(ValueError):
            list(segments('x' * 12001))

    def test_checkpoint_reload_and_wrong_head_rejection(self):
        model = InvestigationText('control')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'model.npz'
            model.save(path)
            loaded = InvestigationText.load(path, 'control')
            self.assertEqual(model.predict('Ver detalhes'), loaded.predict('Ver detalhes'))
            with self.assertRaises(ValueError):
                InvestigationText.load(path, 'status')
            model.parameters['w1'].data[0, 0] = float('nan')
            model.save(path)
            with self.assertRaises(ValueError):
                InvestigationText.load(path, 'control')

    def test_invalid_weights_never_produce_a_hypothesis(self):
        model = InvestigationText('status')
        model.parameters['b2'].data[0] = float('nan')
        with self.assertRaises(ValueError):
            model.predict('Carregando dados')

    def test_learned_navigation_hypothesis_cannot_authorize_a_click(self):
        status, control = InvestigationText('status'), InvestigationText('control')
        # Even a deliberately overconfident wrong model cannot change authority.
        for parameter in control.parameters.values():
            parameter.data[:] = 0
        control.parameters['b2'].data[0] = 100
        session = BrowserInvestigation('https://qa.example.test')
        observation = session.observe({
            'url': 'https://qa.example.test/', 'title': 'Laboratório',
            'text': 'Resumo do projeto\n' * 40 + '\n',
            'controls': [{'id': 'delete', 'name': 'Excluir projeto', 'role': 'button',
                          'navigation': False, 'href': None}],
        })
        original = copy.deepcopy(observation)
        result = annotate_observation(observation, status, control)
        self.assertEqual(observation, original)
        self.assertEqual(result['controls'][0]['hypothesis']['label'], 'navigation')
        self.assertFalse(result['authorizesAction'])
        self.assertFalse(result['crossSegmentReasoning'])
        self.assertEqual(''.join(b['text'] for b in result['blocks']), observation['text'])
        self.assertIsNone(result['blocks'][-1]['hypothesis'])
        with self.assertRaises(PolicyError):
            session.propose({'action': 'click', 'snapshot': observation['snapshot'],
                             'target': 'delete', 'quote': '', 'reason': 'Modelo sugeriu navegação.'},
                            observation['snapshot'])
        self.assertIsNone(session.outstanding)
        with self.assertRaises(ValueError):
            annotate_observation(observation, control, status)


if __name__ == '__main__':
    unittest.main()
