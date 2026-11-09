"""OpenAI integration safeguards using a MOCK client (no network, no charges):
spending limits, reserve, approval, unknown price, API failures, usage ledger,
AI-assisted repair within budget, and budget stop inside the repair loop."""
import json, os, sys, tempfile, unittest, warnings
from pathlib import Path
warnings.filterwarnings('ignore')
sys.path.insert(0, str(Path(__file__).parent))
import fixtures
from config import load_settings, save_settings, DEFAULTS
from costs import (BudgetGuard, BudgetExceeded, SpendNotApproved, PriceUnknown, Ledger, estimate_cost)
from engine import import_product
import ai_roles


class Usage:
    def __init__(self, i, o):
        self.input_tokens, self.output_tokens = i, o


class Resp:
    def __init__(self, text, usage=Usage(1000, 200)):
        self.output_text, self.usage = text, usage


class MockClient:
    def __init__(self, text='[]', fail=None):
        self.calls = []
        self.text, self.fail = text, fail
        self.responses = self

    def create(self, **kw):
        self.calls.append(kw)
        if self.fail:
            raise self.fail
        return Resp(self.text)


YES = lambda info: True
NO = lambda info: False


class Base(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.ws = Path(self.t.name) / 'ws'
        self.s = load_settings(self.ws)

    def tearDown(self):
        for p in Path(self.t.name).rglob('*'):
            try:
                os.chmod(p, 0o777 if p.is_dir() else 0o666)
            except OSError:
                pass
        self.t.cleanup()

    def fund(self, funded=10.0, reserve=1.0, job=0.5, daily=2.0):
        self.s['budget'].update(funded_usd=funded, reserve_usd=reserve, max_job_usd=job, max_daily_usd=daily)
        save_settings(self.ws, self.s)
        return BudgetGuard(self.ws, load_settings(self.ws))


class Guard(Base):
    def test_unfunded_means_no_call(self):
        g = BudgetGuard(self.ws, self.s)
        sent = []
        with self.assertRaises(BudgetExceeded):
            g.paid_call('j', 'r', 'gpt-6-luna', 1000, 500, YES, lambda: sent.append(1))
        self.assertEqual(sent, [])

    def test_owner_must_approve_each_call(self):
        g = self.fund()
        sent = []
        with self.assertRaises(SpendNotApproved):
            g.paid_call('j', 'r', 'gpt-6-luna', 1000, 500, NO, lambda: sent.append(1))
        with self.assertRaises(SpendNotApproved):
            g.paid_call('j', 'r', 'gpt-6-luna', 1000, 500, None, lambda: sent.append(1))
        self.assertEqual(sent, [])

    def test_unknown_model_price_refused(self):
        g = self.fund()
        with self.assertRaises(PriceUnknown):
            g.paid_call('j', 'r', 'some-new-model', 1000, 500, YES, lambda: Resp('x'))

    def test_usage_recorded_from_response(self):
        g = self.fund()
        g.paid_call('j1', 'r', 'gpt-6.1-terra', 1000, 500, YES, lambda: Resp('ok', Usage(2000, 400)))
        e = Ledger(self.ws).entries()[0]
        self.assertEqual(e['status'], 'OK')
        self.assertAlmostEqual(e['charged_usd'], 2000 * 1.00 / 1e6 + 400 * 5.00 / 1e6)
        self.assertEqual(e['input_tokens'], 2000)

    def test_estimate_is_conservative(self):
        est = estimate_cost(self.s, 'gpt-6.1-sol', 35000, 1000)
        raw = (35000 / 4) * 2.0 / 1e6 + 1000 * 10.0 / 1e6
        self.assertGreater(est, raw)

    def test_per_job_cap(self):
        g = self.fund(job=0.01)
        with self.assertRaises(BudgetExceeded):
            g.paid_call('j', 'r', 'gpt-6-astra', 40000, 4000, YES, lambda: Resp('x'))

    def test_daily_cap_accumulates_and_is_never_exceeded(self):
        # realistic usage: input tokens <= bytes, output tokens <= max_output_tokens (here 1000)
        g = self.fund(job=5, daily=0.02)
        with self.assertRaises(BudgetExceeded):
            for i in range(10):
                g.paid_call(f'b{i}', 'r', 'gpt-6.1-terra', 1000, 1000, YES, lambda: Resp('x', Usage(1000, 1000)),
                            input_bytes=1000)
        self.assertLessEqual(Ledger(self.ws).spent(), 0.02, 'recorded spend crossed the daily cap')

    def test_every_denial_makes_no_call_and_records_nothing(self):
        cases = {
            'unfunded': (dict(funded=0), YES, 'gpt-6-luna'),
            'reserve': (dict(funded=1.0, reserve=1.0), YES, 'gpt-6-luna'),
            'job cap': (dict(job=0.000001), YES, 'gpt-6-luna'),
            'daily cap': (dict(daily=0.000001), YES, 'gpt-6-luna'),
            'owner said no': ({}, NO, 'gpt-6-luna'),
            'no approver': ({}, None, 'gpt-6-luna'),
            'truthy but not True': ({}, lambda i: 'yes', 'gpt-6-luna'),
            'unknown price': ({}, YES, 'model-without-price'),
        }
        for name, (limits, approver, model) in cases.items():
            with self.subTest(name):
                led = self.ws / 'logs' / 'api_ledger.jsonl'
                if led.exists():
                    led.unlink()
                g = self.fund(**limits) if limits.get('funded', 1) else self.fund(funded=0)
                sent = []
                with self.assertRaises((BudgetExceeded, SpendNotApproved, PriceUnknown)):
                    g.paid_call('j', 'r', model, 1000, 500, approver, lambda: sent.append(1) or Resp('x'))
                self.assertEqual(sent, [], f'{name}: request was sent')
                self.assertEqual(Ledger(self.ws).entries(), [], f'{name}: ledger entry written')

    def test_recorded_charge_never_exceeds_authorized_maximum(self):
        g = self.fund(job=5, daily=5)
        text = 'Solve 2x + 3 = 11 × ÷ √ π ² ³ ∫ ≤ ≥ ' * 40          # symbol-heavy, many bytes per char
        b = len(text.encode('utf-8'))
        g.paid_call('j', 'r', 'gpt-6.1-sol', len(text), 800, YES, lambda: Resp('x', Usage(b, 800)), input_bytes=b)
        e = Ledger(self.ws).entries()[-1]
        self.assertLessEqual(e['charged_usd'], e['estimate_usd'])
        self.assertTrue(e['confirmed_charge'])

    def test_usage_above_maximum_halts_ai_for_the_job(self):
        g = self.fund(job=5, daily=5)
        g.paid_call('j', 'r', 'gpt-6-luna', 100, 100, YES, lambda: Resp('x', Usage(10_000, 10_000)), input_bytes=100)
        self.assertTrue(Ledger(self.ws).entries()[-1]['exceeded_authorized'])
        sent = []
        with self.assertRaises(BudgetExceeded):
            g.paid_call('j', 'r', 'gpt-6-luna', 100, 100, YES, lambda: sent.append(1) or Resp('x'))
        self.assertEqual(sent, [])

    def test_reserve_never_spent(self):
        g = self.fund(funded=1.02, reserve=1.0, job=5, daily=5)
        with self.assertRaises(BudgetExceeded):
            g.paid_call('j', 'r', 'gpt-6-astra', 20000, 2000, YES, lambda: Resp('x'))

    def test_api_failure_conservatively_charged_and_raised(self):
        g = self.fund()
        with self.assertRaises(TimeoutError):
            g.paid_call('j', 'r', 'gpt-6-luna', 1000, 500, YES, lambda: (_ for _ in ()).throw(TimeoutError('t')))
        e = Ledger(self.ws).entries()[0]
        self.assertEqual(e['status'], 'FAILED_ASSUMED_MAX')
        self.assertGreater(e['charged_usd'], 0, 'authorized maximum stays reserved against the caps')
        self.assertFalse(e['confirmed_charge'], 'a failed call is not reported as a confirmed charge')

    def test_summary_never_claims_verified_balance(self):
        self.assertIn('NOT verified', Ledger(self.ws).summary(self.s)['balance_note'])

    def test_settings_validation(self):
        bad = json.loads(json.dumps(DEFAULTS))
        bad['budget']['max_job_usd'] = 50
        with self.assertRaises(ValueError):
            save_settings(self.ws, bad)
        bad = json.loads(json.dumps(DEFAULTS))
        bad['repair']['max_iterations'] = 0
        with self.assertRaises(ValueError):
            save_settings(self.ws, bad)


class AIRoles(Base):
    def test_review_requires_key_or_client(self):
        os.environ.pop('OPENAI_API_KEY', None)
        p = Path(self.t.name) / 'a.html'
        p.write_text('<p>2+2=4</p>')
        m = import_product(p, self.ws)
        with self.assertRaises(RuntimeError):
            ai_roles.run_review(self.ws, m['id'], 'Academic Verifier', approver=YES)

    def test_review_through_guard(self):
        self.fund()
        p = Path(self.t.name) / 'a.html'
        p.write_text('<p>2+2=4</p>')
        m = import_product(p, self.ws)
        c = MockClient('1. No defects found.')
        out = ai_roles.run_review(self.ws, m['id'], 'Academic Verifier', approver=YES, client=c)
        self.assertIn('No defects', out)
        self.assertEqual(c.calls[0]['model'], DEFAULTS['models']['complex'])
        self.assertEqual(len(Ledger(self.ws).entries()), 1)

    def test_patch_json_parsing_rejects_garbage(self):
        self.assertEqual(ai_roles.parse_patch_json('no json'), [])
        self.assertEqual(ai_roles.parse_patch_json('{"patches":[{"file":1}]}'), [])
        ok = ai_roles.parse_patch_json('Sure! {"patches":[{"file":"a.js","find":"x","replace":"y","reason":"r"}]}')
        self.assertEqual(ok[0]['source'], 'ai_suggestion')


class AIInLoop(Base):
    BUG = ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
           'content="width=device-width, initial-scale=1"><title>t</title></head><body>'
           '<button onclick="go()">Go</button><p id="out"></p>'
           '<script>function go(){ document.getElementById("out").textContent = totl; } var total = 3;</script>'
           '<script>var items=[{q:"What is 2 + 2?", answer:"4"}];</script></body></html>')

    def _job(self, client, approver, fund=True, browser=True):
        from orchestrator import Orchestrator
        from browsertest import playwright_available
        if browser and not playwright_available():
            self.skipTest('Playwright not installed')
        if fund:
            self.fund()
        p = Path(self.t.name) / 'bug.html'
        p.write_text(self.BUG)
        m = import_product(p, self.ws)
        return Orchestrator(self.ws).run_repair_job(m['id'], ai_enabled=True, approver=approver, ai_client=client,
                                                    run_browser=browser)

    def test_ai_suggestion_applied_then_independently_verified(self):
        patch = json.dumps({'patches': [{'file': 'bug.html', 'find': 'textContent = totl;',
                                         'replace': 'textContent = total;', 'reason': 'typo in variable name'}]})
        c = MockClient(patch)
        job = self._job(c, YES)
        self.assertEqual(len(c.calls), 1)
        self.assertEqual(job['qa']['decision'], 'PASS', job['qa']['reasons'])
        self.assertEqual(job['history'][0]['source'], 'ai_suggestion')

    def test_bad_ai_suggestion_cannot_pass_qa(self):
        patch = json.dumps({'patches': [{'file': 'bug.html', 'find': 'textContent = totl;',
                                         'replace': 'textContent = totalz;', 'reason': 'wrong fix'}]})
        job = self._job(MockClient(patch), YES)
        self.assertNotEqual(job['qa']['decision'], 'PASS')

    def test_budget_stop_inside_loop(self):
        c = MockClient('{"patches":[]}')
        job = self._job(c, YES, fund=False)
        self.assertEqual(job['stop_reason'], 'BUDGET_LIMIT')
        self.assertEqual(c.calls, [])
        self.assertEqual(Ledger(self.ws).entries(), [], 'denied spending must leave no ledger charge')

    def test_declined_spend_stops_without_call(self):
        c = MockClient('{"patches":[]}')
        job = self._job(c, NO)
        self.assertEqual(job['stop_reason'], 'SPEND_NOT_APPROVED')
        self.assertEqual(c.calls, [])
        self.assertEqual(Ledger(self.ws).entries(), [], 'denied spending must leave no ledger charge')

    def test_api_error_handled(self):
        c = MockClient(fail=ConnectionError('network down'))
        job = self._job(c, YES)
        self.assertEqual(job['stop_reason'], 'AI_ERROR')
        self.assertNotEqual(job['status'], 'ERROR')


if __name__ == '__main__':
    unittest.main()
