"""Arithmetic and data boundaries; not a model/marketing quality assessment."""
import unittest
from localauthor.errors import PolicyError
from localauthor.foundation.marketing import compare_campaigns


def row(name="A", impressions=3000, clicks=60, conversions=6, spend_cents=12000):
    return dict(name=name,impressions=impressions,clicks=clicks,conversions=conversions,spend_cents=spend_cents)


class CampaignMetricsTests(unittest.TestCase):
    def test_best_rate_does_not_follow_absolute_clicks(self):
        result=compare_campaigns([row(),row("B",1000,30,3,6000)])
        self.assertEqual(result["best_ctr"],["B"])
        self.assertEqual(result["campaigns"][0]["ctr_percent"],"2.00")
        self.assertEqual(result["campaigns"][1]["cpa_brl"],"20.00")
        self.assertFalse(result["published"]);self.assertFalse(result["real_spend_verified"])

    def test_zero_denominator_is_unknown_and_ties_are_preserved(self):
        result=compare_campaigns([row("none",0,0,0,0),row("first",100,2,0,0),row("second",200,4,0,0)])
        self.assertIsNone(result["campaigns"][0]["ctr_percent"])
        self.assertIsNone(result["campaigns"][1]["cpa_brl"])
        self.assertEqual(result["best_ctr"],["first","second"])
        self.assertEqual(compare_campaigns([row("none",0,0,0,0)])["best_ctr"],[])

    def test_exact_rates_choose_before_display_rounding(self):
        result=compare_campaigns([row("lower",10**12,20000000001,0,0),row("higher",10**12,20000000002,0,0)])
        self.assertEqual(result["campaigns"][0]["ctr_percent"],result["campaigns"][1]["ctr_percent"])
        self.assertEqual(result["best_ctr"],["higher"])

    def test_invalid_counts_schema_and_attribution_fail_closed(self):
        for rows in ([row(clicks=True)],[row(clicks=-1)],[row(conversions=61)],[row(impressions=10**12+1)],
                     [row(),row()],[{**row(),"publish":True}],[],[row(impressions=0)]):
            with self.subTest(rows=rows),self.assertRaises(PolicyError):compare_campaigns(rows)
