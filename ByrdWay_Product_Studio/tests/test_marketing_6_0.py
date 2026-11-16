"""Powerhouse 6.0: Marketing Skills integration, email compliance, duplicate prevention, pressure tests."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import compliance as cp  # noqa: E402
import marketingskills as ms  # noqa: E402
import salesintel  # noqa: E402

URL = 'https://www.teacherspayteachers.com/Product/Algebra-1-Power-Tool-123'
CAT = [{'title': 'Algebra 1 Power Tool', 'qa': 'PASS', 'owner_approved': True, 'url': URL, 'price': 79.99}]
SENDER = {'name': 'Dr. Byrd, ByrdWay Mathematics & Science', 'email': 'owner@example.com',
          'postal_address': '123 Example St, Example City, FL 00000'}


def draft(**kw):
    d = {'recipient_email': 'teacher@school.example.org', 'recipient_name': 'Ms. Lee',
         'recipient_verified_source': 'school website staff page (public)', 'campaign': 'alg1-fall',
         'subject': 'A verified Algebra 1 resource for your Honors class',
         'body': f'Hello Ms. Lee, a resource offer for your class: {URL} at $79.99.\n'
                 f'{SENDER["postal_address"]}\nReply STOP or click unsubscribe to opt out.',
         'product_title': 'Algebra 1 Power Tool', 'product_url': URL, 'price_mentioned': 79.99,
         'relationship': 'business_cold'}
    d.update(kw)
    return d


class Skills(unittest.TestCase):
    def test_53_installed_discoverable_with_provenance(self):
        r = ms.report()
        self.assertEqual(r['installed'], 53)
        self.assertEqual(r['discovery_problems'], [])
        self.assertEqual(r['commit'], '1f837447b20bb6f0e72d87b80ece1c221c362c7d')
        self.assertIn('MIT', r['license'])
        self.assertEqual(r['active'] + len(r['not_activated']), 53)

    def test_no_executable_code_installed(self):
        bad = [p for p in ms.skills_dir().rglob('*') if p.suffix in ('.js', '.mjs', '.py', '.sh', '.ps1', '.exe')]
        self.assertEqual(bad, [])

    def test_every_activated_skill_maps_to_an_existing_role(self):
        keys = {k for k, *_ in salesintel.ROLES}
        self.assertEqual(set(ms.ROLE_SKILLS) - keys, set())
        installed = {s['skill'] for s in ms.inventory()}
        for sk in sum(ms.ROLE_SKILLS.values(), []):
            self.assertIn(sk, installed)
        for k in keys:
            self.assertTrue(ms.ROLE_SKILLS.get(k), f'role {k} has no skill')

    def test_run_sheet_invocation_applies_guardrails(self):
        r = ms.run_sheet('referrals', {'product': 'Algebra 1 Power Tool'})
        self.assertTrue(r['steps'])
        self.assertTrue(any('No referral payments' in g for g in r['guardrails']))
        self.assertTrue(any('Zero additional spend' in g for g in r['guardrails']))
        with self.assertRaises(PermissionError):
            ms.run_sheet('sms')

    def test_ai_run_refused_without_funding_and_output_passes_sales_qa(self):
        d = tempfile.mkdtemp()
        try:
            from engine import workspace
            from config import load_settings, save_settings
            root = workspace(Path(d) / 'ws')
            fake = SimpleNamespace(responses=SimpleNamespace(create=lambda **k: SimpleNamespace(
                output_text='Guaranteed results! #1 best seller', usage=None)))
            with self.assertRaises(Exception):          # budget.funded_usd = 0 by default: refused before any call
                ms.ai_run(root, 'copywriting', 'headline', approver=lambda e: True, client=fake)
            s = load_settings(root)
            s['budget'].update(funded_usd=5, reserve_usd=0, max_job_usd=1, max_daily_usd=1)
            save_settings(root, s)
            out = ms.ai_run(root, 'copywriting', 'headline', approver=lambda e: True, client=fake)
            self.assertEqual(out['sales_qa'], 'BLOCKED')     # banned claims caught
            with self.assertRaises(Exception):          # owner declines -> no call
                ms.ai_run(root, 'copywriting', 'headline 2', approver=lambda e: False, client=fake, job_id='j2')
        finally:
            shutil.rmtree(d, ignore_errors=True)


class Compliance(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        from engine import workspace
        self.root = workspace(Path(self.d) / 'ws')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_compliant_draft_ready_and_duplicate_blocked_after_send(self):
        r = cp.presend_check(self.root, draft(), CAT, SENDER)
        self.assertTrue(r['ready'], r['problems'])
        self.assertFalse(r['sends_email'])
        cp.record_sent(self.root, draft(), 'owner', r)
        again = cp.presend_check(self.root, draft(), CAT, SENDER)
        self.assertIn('this campaign was already sent to this recipient', again['problems'])
        with self.assertRaises(PermissionError):
            cp.record_sent(self.root, draft(), 'owner', r)

    def test_each_violation_is_caught(self):
        cases = {
            'recipient not verified': draft(recipient_verified_source=None),
            'postal address': draft(body=f'Offer {URL}. Reply STOP to opt out.'),
            'opt-out': draft(body=f'Offer {URL} {SENDER["postal_address"]}'),
            'fakes a reply': draft(subject='Re: your class'),
            'price in the message': draft(price_mentioned=49.99),
            'exact TpT listing': draft(product_url='https://example.com/x'),
            'Sales QA': draft(body=f'Guaranteed results! {URL} {SENDER["postal_address"]} unsubscribe'),
        }
        for need, dr in cases.items():
            r = cp.presend_check(self.root, dr, CAT, SENDER)
            self.assertFalse(r['ready'], need)
            self.assertTrue(any(need in p for p in r['problems']), (need, r['problems']))

    def test_opt_out_is_permanent(self):
        cp.opt_out(self.root, 'Teacher@School.example.org')
        r = cp.presend_check(self.root, draft(campaign='other'), CAT, SENDER)
        self.assertIn('recipient opted out - never contact again', r['problems'])

    def test_unapproved_product_cannot_be_promoted(self):
        cat = [dict(CAT[0], owner_approved=False)]
        self.assertFalse(cp.presend_check(self.root, draft(), cat, SENDER)['ready'])


class PressureTests(unittest.TestCase):
    def test_unmeasured_numbers_stay_not_measured_and_sources_required(self):
        d = tempfile.mkdtemp()
        try:
            from engine import workspace
            root = workspace(Path(d) / 'ws')
            cp.pressure_test(root, {'hypothesis': 'Honors teachers buy after a 30-s demo', 'audience': 'HS math teachers',
                                    'offer': 'Algebra 1 Power Tool', 'product_url': URL, 'secret': 'verified answers'})
            t = cp.pressure_tests(root)[0]
            self.assertEqual(t['paid_units'], 'NOT MEASURED')
            self.assertEqual(t['decision'], 'PENDING')
            with self.assertRaises(ValueError):
                cp.pressure_test(root, {'id': t['id'], 'product_url': URL, 'paid_units': 12})   # no source
            cp.pressure_test(root, {'id': t['id'], 'product_url': URL, 'exposure': 1000, 'clicks': 40, 'paid_units': 3,
                                    'sources': {'exposure': 'Blotato analytics', 'clicks': 'TpT stats', 'paid_units': 'TpT sales report'},
                                    'decision': 'CONTINUE'})
            t = cp.pressure_tests(root)[0]
            self.assertEqual((t['click_rate'], t['decision']), (0.04, 'CONTINUE'))
            with self.assertRaises(ValueError):
                cp.pressure_test(root, {'product_url': 'https://example.com'})
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
