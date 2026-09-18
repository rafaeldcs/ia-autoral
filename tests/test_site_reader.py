import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np

from localauthor.site_reader import SiteReader, PURPOSES, features, describe_site
from qa.site_reader_course import make_splits


class SiteReaderTests(unittest.TestCase):
    def test_all_categories_have_disjoint_evaluation(self):
        splits = make_splits(corrective=True)
        signatures = {s: {(r['kind'], r['title'], tuple(r['elements'])) for r in rows}
                      for s, rows in splits.items()}
        self.assertFalse(signatures['train'] & signatures['test'])
        self.assertFalse(signatures['train'] & signatures['validation'])
        for kind, labels in PURPOSES.items():
            for rows in splits.values():
                self.assertEqual(set(labels), {r['label'] for r in rows if r['kind'] == kind})

    def test_title_and_body_have_distinct_channels(self):
        self.assertFalse(np.array_equal(features('Histórico', ['Vídeos']), features('Vídeos', ['Histórico'])))
        for title, elements in [('x'*601, []), ('Título', ['a']*101), ('Título', [''])]:
            with self.assertRaises(ValueError): features(title, elements)

    def test_current_and_historical_checkpoints_reload(self):
        with tempfile.TemporaryDirectory() as folder:
            for version in (1, 2):
                model = SiteReader('screen', encoder=version)
                path = Path(folder)/f'{version}.npz'
                model.save(path)
                loaded = SiteReader.load(path, 'screen')
                self.assertEqual(model.predict('Produtos', []), loaded.predict('Produtos', []))
                with self.assertRaises(ValueError): SiteReader.load(path, 'site')
                model.parameters['b2'].data[0] = float('nan'); model.save(path)
                with self.assertRaises(ValueError): SiteReader.load(path, 'screen')

    def test_site_name_cannot_choose_the_answer_and_unobserved_stays_pending(self):
        site, screen = SiteReader('site'), SiteReader('screen')
        bundle = {'name': 'Marca A', 'screens': [
            {'id': '1', 'name': 'Produtos', 'url': 'https://example.test/', 'state': 'observed',
             'observedAt': '2026-09-18T00:00:00Z', 'sourceKind': 'synthetic-test', 'elements': ['Catálogo'], 'reason': ''},
            {'id': '2', 'name': 'Área privada', 'url': 'https://example.test/private', 'state': 'blocked',
             'observedAt': None, 'sourceKind': 'synthetic-test', 'elements': [], 'reason': 'Login necessário'},
        ]}
        before = copy.deepcopy(bundle)
        a = describe_site(bundle, site, screen)
        self.assertEqual(before, bundle)
        bundle['name'] = 'Uma marca completamente diferente'
        b = describe_site(bundle, site, screen)
        self.assertEqual(a['purpose'], b['purpose'])
        self.assertEqual(a['screens'], b['screens'])
        self.assertIsNone(a['screens'][1]['prediction'])
        self.assertFalse(a['allSitesQualified'])
        self.assertTrue(a['authoredDescriptions'])

    def test_real_audit_refuses_omissions_and_changed_evidence(self):
        path = Path(__file__).resolve().parents[1]/'scripts/audit-site-responses.py'
        spec = importlib.util.spec_from_file_location('audit_site_test', path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        expected = {'observationsHash': 'abc', 'expected': {'1':'catalog'},
                    'expectedSite':'commerce', 'gradeLevel':'coarse purpose'}
        result = {'inputHash':'abc', 'screens':[], 'purpose':{'label':'commerce'}}
        with self.assertRaises(ValueError): module.assess(result, expected)
        result['inputHash']='changed'
        with self.assertRaises(ValueError): module.assess(result, expected)
        result['inputHash']='abc'
        case = {'id':'1', 'name':'Items', 'state':'observed', 'prediction':{'label':'catalog'}}
        result['screens'] = [case, copy.deepcopy(case)]
        result['screens'][0]['prediction']['label'] = 'unknown'
        with self.assertRaises(ValueError): module.assess(result, expected)


if __name__ == '__main__': unittest.main()
