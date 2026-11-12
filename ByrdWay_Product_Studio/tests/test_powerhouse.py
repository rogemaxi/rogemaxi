"""Byrd Powerhouse: agent organization, Observer lessons from real repair jobs, timeline."""
import sys, tempfile, unittest, warnings
from pathlib import Path
warnings.filterwarnings('ignore')
sys.path.insert(0, str(Path(__file__).parent))
import powerhouse
import fixtures


class Organization(unittest.TestCase):
    def test_twelve_engineering_agents_in_six_groups_with_honest_status(self):
        org = powerhouse.organization()
        agents = [a for g in org['engineering'].values() for a in g]
        self.assertEqual(len(agents), 12)
        self.assertEqual(len(org['engineering']), 6)
        for a in agents:
            self.assertEqual(set(a['status']), set(powerhouse.FAMILIES))
            self.assertTrue(set(a['status'].values()) <= {'WORKING', 'PARTIAL', 'MISSING'})
            self.assertTrue(a['code'])
        self.assertTrue(any(r['status'] == 'MISSING' for r in org['revenue']), 'missing parts are shown, never hidden')


class ObserverLearnsFromRepairs(unittest.TestCase):
    def test_repair_job_teaches_lessons_and_timeline_names_the_agents(self):
        from controller import Studio
        with tempfile.TemporaryDirectory() as d:
            s = Studio(Path(d) / 'ws')
            m = s.import_product(fixtures.broken_power_tool_zip(Path(d) / 'tool.zip'))
            j = s.run_job(m['id'], run_browser=False)
            self.assertTrue(j.get('lessons_recorded'), 'the Observer recorded lessons from the job')
            lessons = s.lessons()
            self.assertTrue(lessons and all(l['guarded_by'] for l in lessons))
            names = [a for a, _ in s.job_timeline(j['id'])]
            for agent in ('Diagnostician', 'Repair Engineer', 'Release QA', 'Observer'):
                self.assertIn(agent, names)


if __name__ == '__main__':
    unittest.main()
