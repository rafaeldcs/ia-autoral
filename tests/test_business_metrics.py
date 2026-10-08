"""Independent arithmetic/boundary oracles; not a model-intelligence certificate."""
import copy
import itertools
import random
import unittest

from localauthor.errors import PolicyError
from localauthor.foundation.business_metrics import analyze_business_metrics


def expected_ratio(numerator, denominator, units=1):
    if denominator == 0:
        return None
    sign = '-' if numerator < 0 else ''
    value = abs(numerator) * units
    rounded = (2 * value + denominator) // (2 * denominator)
    return f'{sign}{rounded // 100}.{rounded % 100:02d}'


def payload(kind, **data):
    return {'kind': kind, 'data': data}


CAMPAIGN = payload('campaign', impressions=12500, clicks=250, leads=50,
                   new_clients=5, spend_cents=125000)
FUNNEL = payload('funnel', registrations=200, started=50, completed=20)
CASH = payload('cash', opening_cents=880000, incoming_cents=320000, outgoing_cents=470000)


class BusinessMetricsTests(unittest.TestCase):
    def test_campaign_money_units_and_distinct_denominators(self):
        report = analyze_business_metrics(CAMPAIGN)
        self.assertEqual(report['metrics'], {'ctr_percent': '2.00', 'cpl_brl': '25.00',
                                             'media_per_client_brl': '250.00'})
        self.assertIn('CAC', report['notice'])
        self.assertIn('ROI', report['notice'])

    def test_funnel_keeps_all_denominators_and_losses(self):
        self.assertEqual(analyze_business_metrics(FUNNEL)['metrics'], {
            'start_percent': '25.00', 'completion_started_percent': '40.00',
            'activation_percent': '10.00', 'not_started': 150,
            'started_not_completed': 30, 'not_completed': 180})

    def test_cash_is_not_profit_and_negative_cash_is_allowed(self):
        self.assertEqual(analyze_business_metrics(CASH)['metrics'],
                         {'balance_cents': 730000, 'balance_brl': '7300.00'})
        report = analyze_business_metrics(payload('cash', opening_cents=0,
                                                  incoming_cents=1, outgoing_cents=101))
        self.assertEqual(report['metrics'], {'balance_cents': -100, 'balance_brl': '-1.00'})
        self.assertIn('lucro', report['notice'])

    def test_zero_denominator_is_unknown_not_zero_or_infinity(self):
        for original in (CAMPAIGN, FUNNEL):
            case = copy.deepcopy(original)
            case['data'] = dict.fromkeys(case['data'], 0)
            report = analyze_business_metrics(case)
            for name, value in report['metrics'].items():
                if 'percent' in name or name.endswith('_brl'):
                    self.assertIsNone(value)

    def test_supplied_numbers_do_not_authorize_spending_or_training(self):
        original = copy.deepcopy(CAMPAIGN)
        result = analyze_business_metrics(original)
        self.assertEqual(original, CAMPAIGN)
        self.assertEqual(result['data_origin'], 'user_supplied_unverified')
        self.assertIs(result['published'], False)
        self.assertIs(result['weights_trained'], False)
        result['inputs']['clicks'] = 0
        self.assertEqual(original, CAMPAIGN)

    def test_invalid_schema_kind_and_extra_fields_fail_with_policy_error(self):
        bad = [None, [], 'campaign', {}, {'kind': 'campaign'},
               {**CAMPAIGN, 'publish': True},
               {**CAMPAIGN, 'data': []}, {**CAMPAIGN, 'data': {}},
               {**CAMPAIGN, 'data': {**CAMPAIGN['data'], 'token': 'synthetic'}}]
        # Comprehensions stay separate so malformed/unhashable kinds are covered.
        bad.extend({**CAMPAIGN, 'kind': kind} for kind in
                   ([], {}, None, True, 1, 'CAMPAIGN', 'unknown'))
        for case in bad:
            with self.subTest(case=case), self.assertRaises(PolicyError):
                analyze_business_metrics(case)

    def test_every_field_rejects_bool_float_string_negative_and_overflow(self):
        for original in (CAMPAIGN, FUNNEL, CASH):
            for field in original['data']:
                for invalid in (True, False, 1.0, '1', None, [], {}, -1, 10**12+1,
                                float('nan'), float('inf')):
                    case = copy.deepcopy(original)
                    case['data'][field] = invalid
                    with self.subTest(kind=case['kind'], field=field, value=invalid), self.assertRaises(PolicyError):
                        analyze_business_metrics(case)

    def test_invalid_ordering_is_rejected_without_inventing_attribution(self):
        for case in (payload('campaign', impressions=1, clicks=2, leads=1, new_clients=1, spend_cents=0),
                     payload('campaign', impressions=2, clicks=1, leads=2, new_clients=1, spend_cents=0),
                     payload('campaign', impressions=2, clicks=2, leads=1, new_clients=2, spend_cents=0),
                     payload('funnel', registrations=1, started=2, completed=1),
                     payload('funnel', registrations=2, started=1, completed=2)):
            with self.subTest(case=case), self.assertRaises(PolicyError):
                analyze_business_metrics(case)

    def test_exhaustive_small_campaigns_against_integer_oracle(self):
        count = 0
        for impressions in range(11):
            for clicks in range(impressions+1):
                for leads in range(clicks+1):
                    for clients in range(leads+1):
                        for spend in (0, 1, 99, 100, 101, 10**12-1, 10**12):
                            report = analyze_business_metrics(payload('campaign', impressions=impressions,
                                clicks=clicks, leads=leads, new_clients=clients, spend_cents=spend))['metrics']
                            self.assertEqual(report['ctr_percent'], expected_ratio(clicks, impressions, 10000))
                            self.assertEqual(report['cpl_brl'], expected_ratio(spend, leads))
                            self.assertEqual(report['media_per_client_brl'], expected_ratio(spend, clients))
                            count += 1
        self.assertEqual(count, 7007)

    def test_exhaustive_small_funnels_against_integer_oracle(self):
        count = 0
        for registered in range(21):
            for started in range(registered+1):
                for completed in range(started+1):
                    report = analyze_business_metrics(payload('funnel', registrations=registered,
                                                            started=started, completed=completed))['metrics']
                    self.assertEqual(report['start_percent'], expected_ratio(started, registered, 10000))
                    self.assertEqual(report['completion_started_percent'], expected_ratio(completed, started, 10000))
                    self.assertEqual(report['activation_percent'], expected_ratio(completed, registered, 10000))
                    self.assertEqual(report['not_started'], registered-started)
                    self.assertEqual(report['started_not_completed'], started-completed)
                    self.assertEqual(report['not_completed'], registered-completed)
                    count += 1
        self.assertEqual(count, 1771)

    def test_cash_boundary_and_random_cases_against_integer_oracle(self):
        rng = random.Random(27183)
        cases = list(itertools.product((0, 1, 100, 10**12), repeat=3))
        cases.extend(tuple(rng.randrange(10**12+1) for _ in range(3)) for _ in range(5000))
        for opening, incoming, outgoing in cases:
            result = analyze_business_metrics(payload('cash', opening_cents=opening,
                incoming_cents=incoming, outgoing_cents=outgoing))['metrics']
            balance = opening+incoming-outgoing
            self.assertEqual(result['balance_cents'], balance)
            self.assertEqual(result['balance_brl'], expected_ratio(balance, 1))

