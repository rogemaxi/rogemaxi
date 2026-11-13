"""MASTER SSOI Directives 1, 2, 4, 5: labels, acquisition plan, capital allocation, segments, offer test."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bizintel as bi  # noqa: E402


class Labels(unittest.TestCase):
    def test_targets_never_shown_as_actuals(self):
        dash = {'units_total': 0, 'net_total': 0, 'real_rows': 0,
                'weeks': [{'week': 1, 'units': 0, 'minimum': 125, 'stretch': 125, 'net': 0, 'status': 'BELOW'}]}
        f = bi.financials(dash)
        self.assertEqual(f['weekly'][0]['actual_units']['label'], bi.FACT)
        self.assertEqual(f['weekly'][0]['target_minimum']['label'], bi.TARGET)
        self.assertTrue(all(x['label'] == bi.TARGET for x in f['long_term']))

    def test_acquisition_plan_is_assumption_until_measured(self):
        a = bi.acquisition_plan(125)
        self.assertEqual(a['posts_needed_per_week']['label'], bi.ASSUMPTION)
        self.assertEqual(a['listing_visits_needed']['value'], 6250)
        m = bi.acquisition_plan(125, measured={'visit_to_buy': 0.05, 'view_to_visit': 0.02, 'views_per_post': 500})
        self.assertEqual(m['posts_needed_per_week']['label'], bi.INFERENCE)
        self.assertEqual(m['listing_visits_needed']['value'], 2500)


class Capital(unittest.TestCase):
    def test_no_allocation_without_verified_profit(self):
        self.assertIn('NO ALLOCATION', bi.capital_allocation(None)['recommendation'])
        self.assertIn('NO ALLOCATION', bi.capital_allocation(-10)['recommendation'])

    def test_allocation_sums_to_net(self):
        r = bi.capital_allocation(1000, monthly_operating_cost=100)
        self.assertAlmostEqual(sum(b['amount']['value'] for b in r['buckets']), 1000, delta=0.05)
        self.assertEqual(r['tax_rate']['label'], bi.ASSUMPTION)


class Segments(unittest.TestCase):
    def test_eleven_segments_ranked_with_cited_evidence(self):
        r = bi.rank_segments()
        self.assertEqual(len(r), 11)
        self.assertEqual([x['score']['value'] for x in r], sorted((x['score']['value'] for x in r), reverse=True))
        facts = [e for x in r for e in x['evidence'] if e['label'] == bi.FACT]
        self.assertTrue(facts and all(e.get('source', '').startswith('https://') for e in facts))
        for x in r:
            for k in ('buyer', 'learner', 'problem', 'alternatives', 'willingness', 'advantage', 'products', 'channel'):
                self.assertTrue(x[k], f'{x["id"]} missing {k}')
        buyers = {x['buyer'] for x in r}
        self.assertTrue(any('educator' in b for b in buyers) and any('parent' in b for b in buyers) and any('institution' in b for b in buyers))

    def test_segment_without_fact_demand_is_capped(self):
        g = next(x for x in bi.rank_segments() if x['id'] == 'graduate')
        self.assertLess(g['score']['value'], 50)


class Offer(unittest.TestCase):
    def test_eleven_checks_and_missing_evidence_flagged(self):
        t = bi.offer_test({'title': 'X', 'qa': 'PASS', 'answer_keys': True, 'scope': 'full course'})
        self.assertEqual(len(t['checks']), 11)
        self.assertEqual(t['checks']['proof_of_function']['status'], 'PASS')
        self.assertEqual(t['checks']['post_purchase']['status'], 'NEEDS EVIDENCE')
        self.assertEqual(t['checks']['licensing']['status'], 'NEEDS OWNER')


if __name__ == '__main__':
    unittest.main()
