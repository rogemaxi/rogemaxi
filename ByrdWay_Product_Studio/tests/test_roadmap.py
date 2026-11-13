"""Scaling-roadmap matrix, evidence-based stage diagnosis, bottleneck and daily plan."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import roadmap  # noqa: E402
import salesintel as si  # noqa: E402


class Roadmap(unittest.TestCase):
    def test_ten_stages_with_official_names_order_bands_and_sources(self):
        m = roadmap.matrix()
        self.assertEqual([s['name'] for s in m], ['Improvise', 'Monetize', 'Advertise', 'Stabilize', 'Prioritize', 'Productize',
                                                 'Optimize', 'Categorize', 'Specialize', 'Capitalize'])
        self.assertEqual([s['team_band_official'] for s in m],
                         ['0-1', '0-1', '0-1', '1-4', '5-9', '10-19', '20-49', '50-99', '100-249', '250-500'])
        roles = {r[0] for r in si.ROLES}
        for s in m:
            self.assertTrue(s['source'].startswith('https://www.acquisition.com/training/'))
            self.assertFalse(s['purpose_is_quotation'])
            self.assertIn('NOT RETRIEVED', s['official_worksheets_and_criteria'])
            self.assertIn(s['owner_role'], roles)

    def test_no_sales_data_is_provisional_monetize_with_measurement_bottleneck(self):
        a = roadmap.assess({'weekly_units': [], 'team_size': 1, 'products_listed': 25, 'products_qa_pass': 1, 'reviews': 0})
        self.assertEqual((a['diagnosis']['stage'], a['diagnosis']['provisional']), (1, True))
        self.assertEqual(a['bottleneck']['constraint'], 'MEASUREMENT')
        self.assertEqual(a['plan']['actions'][0]['role'], 'revenue_tracker')
        self.assertEqual(len({x['role'] for x in a['plan']['actions']}), 10)

    def test_never_promoted_beyond_evidence(self):
        d = roadmap.diagnose({'weekly_units': [0, 0, 0], 'team_size': 40, 'products_listed': 30, 'products_qa_pass': 30})
        self.assertEqual(d['stage'], 0)                       # a big team does not lift a business with no sales
        d = roadmap.diagnose({'weekly_units': [3, 0, 5, 2], 'team_size': 1})
        self.assertEqual(d['stage'], 1)
        d = roadmap.diagnose({'weekly_units': [5, 6, 7, 9], 'team_size': 1, 'channel_weeks_with_sales': 1})
        self.assertEqual(d['stage'], 2)                       # consistent sales but no proven channel -> Advertise
        d = roadmap.diagnose({'weekly_units': [5, 6, 7, 9], 'team_size': 3, 'channel_weeks_with_sales': 6})
        self.assertEqual(d['stage'], 3)

    def test_demand_and_retention_bottlenecks(self):
        ev = {'weekly_units': [10, 12, 15, 20], 'team_size': 1, 'products_qa_pass': 5, 'channel_weeks_with_sales': 4}
        self.assertEqual(roadmap.assess(ev)['bottleneck']['constraint'], 'DEMAND')
        ev['weekly_units'] = [130, 140, 150, 160]
        self.assertEqual(roadmap.assess(ev)['bottleneck']['constraint'], 'RETENTION')

    def test_plan_keeps_owner_constraints(self):
        p = roadmap.assess({'weekly_units': [], 'team_size': 1})['plan']
        text = ' '.join(a['action'] for a in p['actions']) + ' '.join(p['stop_rules'])
        self.assertIn('unpaid', text)
        self.assertIn('No referral rewards', text)
        self.assertFalse(si.qa_text(' '.join(a['action'] for a in p['actions'])))


if __name__ == '__main__':
    unittest.main()
