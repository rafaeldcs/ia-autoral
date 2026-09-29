import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'qa'))
from terreiro_simulation_review import observations, required_action, COMMANDS, HTTP_STAGES
from terreiro_qa_policy import curriculum, reinforcement_curriculum, teacher


class SimulationEvidenceTests(unittest.TestCase):
    def sandbox(self):
        return dict(syntheticOnly=True, origin='http://localhost:3180', verified=True,
                    readOnly=True, user='10001:10001', capDrop=['ALL'], security=['no-new-privileges'])

    def receipts(self):
        good = dict(success=True, checks=[dict(passed=True)])
        return dict(sandbox=self.sandbox(), builds=dict(success=True, complete=True,
            results=[dict(name=n, passed=True, exitCode=0) for n in COMMANDS]),
            http=dict(success=True, checks=[dict(stage=s, passed=True) for s in HTTP_STAGES]),
            followup=good, browser=good, interactions=good)

    def test_missing_receipts_cannot_be_inferred_from_plan(self):
        self.assertEqual(required_action(observations(self.sandbox())), 'CHECK_BUILD')

    def test_unverified_sandbox_stops(self):
        sandbox = self.sandbox(); sandbox['verified'] = False
        self.assertEqual(required_action(observations(sandbox)), 'STOP_SCOPE')

    def test_empty_successful_http_is_failure(self):
        receipts = self.receipts(); receipts['http'] = dict(success=True, checks=[])
        self.assertEqual(required_action(observations(**receipts)), 'INVESTIGATE_FAILURE')

    def test_missing_unit_command_never_counts_as_build_or_unit(self):
        receipts = self.receipts(); receipts['builds']['results'].pop()
        self.assertEqual(required_action(observations(**receipts)), 'CHECK_BUILD')

    def test_failed_case_overrides_top_level_success(self):
        receipts = self.receipts(); receipts['http']['checks'][0]['passed'] = False
        self.assertEqual(required_action(observations(**receipts)), 'INVESTIGATE_FAILURE')

    def test_missing_stage_requires_it(self):
        receipts = self.receipts()
        receipts['http']['checks'] = [c for c in receipts['http']['checks'] if c['stage'] != 'stock']
        self.assertEqual(required_action(observations(**receipts)), 'CHECK_STOCK')

    def test_missing_interactions_is_not_browser_completion(self):
        receipts = self.receipts(); receipts.pop('interactions')
        self.assertEqual(required_action(observations(**receipts)), 'CHECK_BROWSER')

    def test_missing_followup_is_not_evidence_completion(self):
        receipts = self.receipts(); receipts.pop('followup')
        self.assertEqual(required_action(observations(**receipts)), 'CHECK_EVIDENCE')

    def test_all_observed_can_report(self):
        self.assertEqual(required_action(observations(**self.receipts())), 'REPORT')

    def test_reinforcement_excludes_reserved_and_keeps_partitions_disjoint(self):
        legacy = curriculum()
        reserved = {r['id'] for r in legacy['validation'] + legacy['test']}
        splits = reinforcement_curriculum(reserved)
        seen = set(reserved)
        for split in ('train', 'validation', 'test'):
            self.assertEqual(len(splits[split]), 2048 if split == 'train' else 512)
            for row in splits[split]:
                self.assertNotIn(row['id'], seen)
                seen.add(row['id'])
                self.assertEqual(row['action'], teacher(row['state']))
        self.assertTrue(any(not row['state']['authorized'] and all(row['state'][s] for s in HTTP_STAGES)
                            for row in splits['train']))
