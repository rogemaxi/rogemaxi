"""Construction QA loops (Power Tool + Explainer), Concept Tiles Assembler, Revenue & Media Division."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import builders  # noqa: E402
import construction  # noqa: E402
import concepttiles as ct  # noqa: E402
import powerhouse  # noqa: E402
import salesintel as si  # noqa: E402
from browsertest import playwright_available  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PT = json.loads((ROOT / 'samples' / 'SAMPLE_power_tool_blueprint.json').read_text())


def mastery_blueprint():
    bp = json.loads(json.dumps(PT))
    m = bp['modules'][0]
    for q in m['practice']:
        q['hint'] = 'Undo the operations in reverse order, doing the same thing to both sides.'
    m['generators'] = [{'skill': 'Two-step equations', 'template': 'Solve {a}x + {b} = {c}',
                        'params': {'a': [2, 9], 'x': [-9, 9], 'b': [-9, 9]}, 'compute': {'c': 'a*x + b'}, 'answer': '{x}',
                        'verify': {'type': 'solve', 'equation': '{a}*x + ({b}) = {c}', 'var': 'x'}}]
    return bp


class ConstructionLoop(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.ws = self.d / 'ws'

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_wrong_answer_is_repaired_reverified_and_rebuilt(self):
        bp = mastery_blueprint()
        bp['modules'][0]['practice'][0]['answer'] = 'x = 5'          # planted: 2x + 3 = 11 -> 4
        b = builders.Build.create(self.ws, bp, 'power_tool')
        u = construction.construct_unit(self.ws, b.id, 'm1-one-step', run_browser=False)
        r = u['construction']['rounds']
        self.assertGreaterEqual(len(r), 2)
        self.assertTrue(any('m1-one-step[0]' in f for f in r[0]['failed']))
        fix = r[0]['repairs'][0]
        self.assertEqual((fix['old'], fix['new']), ('x = 5', 'x = 4'))
        self.assertTrue(fix['reviewer'].startswith('ACCEPTED'))
        self.assertFalse(any('m1-one-step[0]' in f for f in r[-1]['failed']))
        self.assertEqual(builders.Build(self.ws, b.id).blueprint['modules'][0]['practice'][0]['answer'], 'x = 4')

    def test_missing_mastery_items_send_the_unit_back_with_the_exact_list(self):
        b = builders.Build.create(self.ws, json.loads(json.dumps(PT)), 'power_tool')
        u = construction.construct_unit(self.ws, b.id, 'm1-one-step', run_browser=False)
        failed = ' '.join(u['construction']['rounds'][-1]['failed'])
        self.assertEqual(u['status'], 'SENT_BACK_BY_CHIEF_JUDGE')
        for item in ('mastery.3_feedback_and_hints', 'mastery.7_unlimited_verified_practice', 'design.approved_template'):
            self.assertIn(item, failed)
        self.assertIn('100 %', u['construction']['chief_judge']['rule'])

    def test_generated_practice_is_verified_and_a_wrong_generator_fails(self):
        g = mastery_blueprint()['modules'][0]['generators'][0]
        items = construction.generator_instances(g, 10)
        self.assertEqual(len(items), 10)
        from academic import verify_item, CORRECT
        self.assertTrue(all(verify_item(i)['status'] == CORRECT for i in items))
        bad = dict(g, compute={'c': 'a*x + b + 1'})
        self.assertFalse(all(verify_item(i)['status'] == CORRECT for i in construction.generator_instances(bad, 10)))

    @unittest.skipUnless(playwright_available(), 'Playwright not installed')
    def test_mastery_experience_works_in_the_browser(self):
        bp = mastery_blueprint()
        b = builders.Build.create(self.ws, bp, 'power_tool')
        u = builders.build_power_tool_module(self.ws, b.id, 'm1-one-step')
        data = construction._page_data(Path(u['output']).read_text(encoding='utf-8'))
        res = {c['check']: c for c in construction.mastery_browser_checks(u['output'], data)}
        for k in ('mastery.browser.placement_path', 'mastery.browser.hint_on_wrong', 'mastery.browser.gate_locked',
                  'mastery.browser.gate_unlocks_at_mastery', 'mastery.browser.generator_makes_problems',
                  'mastery.browser.report', 'mastery.browser.progress_saved_offline', 'mastery.browser.no_js_errors'):
            self.assertTrue(res[k]['passed'], (k, res[k]))

    def test_explainer_chapter_goes_through_document_qa(self):
        bp = json.loads((ROOT / 'samples' / 'SAMPLE_lil_dr_byrd_physics_blueprint.json').read_text())
        b = builders.Build.create(self.ws, bp, 'lil_dr_byrd')
        u = construction.construct_unit(self.ws, b.id, 'ch01')
        checks = {c['check']: c for c in u['construction']['checks']}
        self.assertTrue(checks['document.text_layer']['passed'])
        self.assertFalse(checks['asset.lil_dr_byrd']['passed'])    # no approved mascot registered -> never substituted
        self.assertEqual(u['status'], 'SENT_BACK_BY_CHIEF_JUDGE')


class Assembler(unittest.TestCase):
    def test_refuses_units_that_did_not_pass(self):
        toc = [{'unit': 1, 'title': 'A', 'tiles': [{'title': 't', 'honors': False}]}]
        with self.assertRaises(PermissionError):
            ct.assemble_product(toc, [{'unit': 1, 'decision': 'FAIL', 'pdf': None}], 'x.png', 'out.pdf')

    def test_refuses_a_unit_changed_after_qa(self):
        d = Path(tempfile.mkdtemp())
        try:
            pdf = d / 'u.pdf'
            pdf.write_bytes(b'%PDF-1.4 changed')
            toc = [{'unit': 1, 'title': 'A', 'tiles': [{'title': 't', 'honors': False}]}]
            rep = [{'unit': 1, 'decision': 'PASS', 'pdf': str(pdf), 'pdf_sha256': '0' * 64}]
            with self.assertRaises(PermissionError):
                ct.assemble_product(toc, rep, str(d / 'm.png'), d / 'out.pdf')
        finally:
            shutil.rmtree(d, ignore_errors=True)


class RevenueMedia(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_targets_are_125_then_10_to_17_percent_to_1000(self):
        t = si.weekly_targets(30)
        self.assertEqual((t[0]['minimum'], t[0]['stretch']), (125, 125))
        self.assertEqual(t[1]['minimum'], 138)               # 125 x 1.10 = 137.5 -> 138
        self.assertEqual(t[1]['stretch'], 147)               # 125 x 1.17 = 146.25 -> 147
        self.assertEqual(si.milestone_week(0.10), 23)
        self.assertEqual(si.milestone_week(0.17), 15)
        self.assertGreaterEqual(t[22]['minimum'], 1000)
        self.assertLess(t[21]['minimum'], 1000)
        o = powerhouse.organization()
        self.assertIn('99.997 %', o['quality_target'])
        self.assertIn('100 % of mandatory', o['quality_target'])
        self.assertEqual(len(o['revenue']), 10)

    def test_library_is_source_linked_and_referral_incentives_excluded(self):
        lib = si.library()
        self.assertGreaterEqual(len(lib['methods']), 30)
        for m in lib['methods']:
            self.assertTrue(m['source']['citation'] and m['metric'] and m['roles'])
        experts = {m['expert'].split(' (')[0] for m in lib['methods']}
        for e in ('Alex Hormozi', 'Leila Hormozi', 'Myron Golden', 'Grant Cardone', 'Zig Ziglar', 'Jim Rohn'):
            self.assertIn(e, experts)
        self.assertTrue(all(c[1] for c in si.library_qa()), [c for c in si.library_qa() if not c[1]])
        self.assertEqual([m['status'] for m in lib['methods'] if 'referral' in m['method'].lower()], ['EXCLUDED'])
        self.assertTrue(all(si.methods_for(r[0]) for r in si.ROLES))

    def test_only_verified_and_approved_products_are_marketed(self):
        cat = [{'title': 'A', 'course': 'Physics', 'price': 10, 'qa': 'PASS', 'owner_approved': False},
               {'title': 'B', 'course': 'Physics', 'price': 10, 'qa': 'NOT YET CHECKED', 'owner_approved': True},
               {'title': 'C', 'course': 'Physics', 'price': 10, 'qa': 'PASS', 'owner_approved': True}]
        self.assertEqual([p['title'] for p in si.marketable(cat)], ['C'])
        si.save_settings(self.d, {'catalog': cat, 'prospects': [{'name': 'SAMPLE', 'segment': 'school', 'course': 'Physics'}]})
        rep, out = si.run_daily(self.d)
        self.assertEqual(rep['sales_qa']['blocked'], [])
        self.assertEqual({m['product'] for m in out['media']}, {'C'})
        self.assertTrue(all('DRAFT' in d['status'] for d in out['followups']))

    def test_sales_qa_blocks_fabrication_endorsement_guarantee_and_referrals(self):
        cat = [{'title': 'C', 'course': 'Physics', 'price': 10, 'qa': 'PASS', 'owner_approved': True}]
        base = si.followup_drafts({'name': 'x'}, cat[0])[0]
        bad = [dict(base, body='Guaranteed to raise your grade!'), dict(base, body='Rated 5 stars by teachers'),
               dict(base, body='Endorsed by Alex Hormozi'), dict(base, body='Get a referral bonus for every friend'),
               dict(base, body='2,000 teachers love this'), dict(base, product='Unverified thing')]
        _, blocked = si.sales_qa({'followups': bad}, cat)
        self.assertEqual(len(blocked), len(bad))
        _, ok = si.sales_qa({'followups': [base]}, cat)
        self.assertEqual(ok, [])

    def test_ledger_excludes_test_rows_and_dashboard_measures_real_sales(self):
        p = self.d / 'sales.csv'
        p.write_text('Date,Product,Quantity,Price,Fee,Buyer\n2026-11-02,Physics Tiles,2,20.00,4.00,b1\n'
                     '2026-11-03,TEST order,1,9.99,0,t\n2026-11-10,Physics Tiles,1,10.00,2.00,b1\n', encoding='utf-8')
        si.save_settings(self.d, {'week1_start': '2026-11-02', 'catalog': [], 'prospects': []})
        self.assertEqual(si.import_sales_csv(self.d, p)['imported'], 3)
        self.assertEqual(si.import_sales_csv(self.d, p)['imported'], 0)          # idempotent
        import datetime as dt
        d = si.dashboard(self.d, dt.date(2026, 11, 16))
        self.assertEqual((d['real_rows'], d['test_rows_excluded'], d['units_total']), (2, 1, 3))
        self.assertEqual(d['net_total'], 24.0)
        self.assertEqual(d['repeat_purchase_rate'], '1/1')
        self.assertTrue(d['weeks'][0]['status'].startswith('BELOW MINIMUM'))

    def test_experiments_are_judged_only_at_minimum_sample(self):
        e = si.add_experiment(self.d, 'script_storyboard', ['AH-07'], 'h', 'purchases/visits', 100, 'a', 'b')
        self.assertEqual(si.record_result(self.d, e['id'], 'A', 50, 2)['status'], 'RUNNING')
        si.record_result(self.d, e['id'], 'A', 60, 3)
        r = si.record_result(self.d, e['id'], 'B', 110, 20)
        self.assertEqual(r['status'], 'CLOSED')
        self.assertEqual(r['result']['winner'], 'B')
        self.assertEqual(si.method_scorecard(self.d)['AH-07']['wins_for_B'], 1)

    def test_van_westendorp_needs_real_sample(self):
        self.assertEqual(si.van_westendorp([{'too_cheap': 1, 'bargain': 2, 'expensive': 3, 'too_expensive': 4}])['status'],
                         'NOT ENOUGH DATA')
        resp = [{'too_cheap': 5 + i % 3, 'bargain': 12 + i % 4, 'expensive': 25 + i % 5, 'too_expensive': 40 + i % 6}
                for i in range(30)]
        r = si.van_westendorp(resp)
        self.assertEqual(r['status'], 'OK')
        self.assertLessEqual(r['point_of_marginal_cheapness'], r['point_of_marginal_expensiveness'])


if __name__ == '__main__':
    unittest.main()
