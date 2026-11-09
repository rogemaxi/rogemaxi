"""Local token/cost accounting and spending guard for OpenAI calls.

Rules enforced here (SSOI section 5):
  * key only from OPENAI_API_KEY env var or the OS keyring (optional `keyring`);
    never from settings, never logged;
  * every call is estimated BEFORE it is sent, using configured prices and a
    safety factor; unknown price -> refused;
  * per-job cap, daily cap, owner-funded amount minus reserve;
  * owner confirmation callback must return True for every paid call;
  * actual usage recorded from the API response when available; failed calls
    are conservatively charged at their estimate (the API may have billed);
  * the account balance is NEVER claimed as verified: the ledger only knows
    what this application itself sent.
"""
import json, os, time, uuid
from engine import workspace, utcnow
from config import load_settings

KEYRING_SERVICE = 'ByrdWay_Product_Studio'


class BudgetExceeded(Exception):
    pass


class SpendNotApproved(Exception):
    pass


class PriceUnknown(Exception):
    pass


def get_api_key():
    key = os.environ.get('OPENAI_API_KEY', '').strip()
    if key:
        return key
    try:
        import keyring  # optional
        return (keyring.get_password(KEYRING_SERVICE, 'OPENAI_API_KEY') or '').strip()
    except Exception:
        return ''


def store_api_key(key):
    """Store in the OS secret store (Windows Credential Manager via keyring)."""
    try:
        import keyring
    except ImportError:
        raise RuntimeError('Install keyring (pip install keyring) or set the OPENAI_API_KEY '
                           'Windows user environment variable.')
    if not key or len(key) < 20:
        raise ValueError('That does not look like an API key')
    keyring.set_password(KEYRING_SERVICE, 'OPENAI_API_KEY', key.strip())


def estimate_tokens(chars):
    # ~4 chars/token for English; round up and never under-count
    return int(chars / 3.5) + 50


def price_for(settings, model):
    p = settings['pricing'].get(model)
    if not p:
        raise PriceUnknown(f'No configured price for model {model!r}; refusing to call. '
                           f'Add it to settings.json from {settings.get("pricing_source")}')
    return float(p['input_per_1m']), float(p['output_per_1m'])


def estimate_cost(settings, model, input_chars, max_output_tokens, input_bytes=None):
    """GUARANTEED maximum cost of one call (not a guess).

    * input: every token is at least one UTF-8 byte, so tokens <= bytes. When only a character count is
      known, 4 bytes/char (the UTF-8 maximum) is assumed.
    * output: the API never returns more than max_output_tokens (reasoning tokens included).
    Authorizing against this bound means a recorded charge can never cross a cap.
    """
    pin, pout = price_for(settings, model)
    tin_max = int(input_bytes) if input_bytes is not None else 4 * int(input_chars)
    raw = tin_max * pin / 1e6 + int(max_output_tokens) * pout / 1e6
    return round(raw * float(settings['budget']['estimate_safety_factor']) + 1e-6, 6)


def actual_cost(settings, model, usage):
    pin, pout = price_for(settings, model)
    def field(name):
        if usage is None:
            return 0
        if isinstance(usage, dict):
            return int(usage.get(name) or 0)
        return int(getattr(usage, name, 0) or 0)
    tin, tout = field('input_tokens'), field('output_tokens')
    return round(tin * pin / 1e6 + tout * pout / 1e6, 6), tin, tout


class Ledger:
    def __init__(self, root):
        self.root = workspace(root)
        self.path = self.root / 'logs' / 'api_ledger.jsonl'

    def entries(self):
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding='utf-8').splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return out

    def record(self, **rec):
        rec.setdefault('id', uuid.uuid4().hex[:10])
        rec.setdefault('ts', utcnow())
        rec.setdefault('day', time.strftime('%Y-%m-%d', time.gmtime()))
        with open(self.path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec) + '\n')
        return rec

    def spent(self, job_id=None, day=None):
        total = 0.0
        for e in self.entries():
            if job_id and e.get('job_id') != job_id:
                continue
            if day and e.get('day') != day:
                continue
            total += float(e.get('charged_usd', 0))
        return round(total, 6)

    def summary(self, settings):
        today = time.strftime('%Y-%m-%d', time.gmtime())
        b = settings['budget']
        total = self.spent()
        return {'total_recorded_usd': total, 'today_usd': self.spent(day=today),
                'funded_usd': float(b['funded_usd']), 'reserve_usd': float(b['reserve_usd']),
                'remaining_authorized_usd': round(max(0.0, float(b['funded_usd']) -
                                                      float(b['reserve_usd']) - total), 6),
                'calls': len(self.entries()),
                'balance_note': 'Locally recorded estimate only; OpenAI account balance NOT verified.'}


class BudgetGuard:
    def __init__(self, root, settings=None):
        self.root = workspace(root)
        self.settings = settings or load_settings(root)
        self.ledger = Ledger(root)

    def authorize(self, job_id, estimate_usd):
        b = self.settings['budget']
        if any(e.get('job_id') == job_id and e.get('exceeded_authorized') for e in self.ledger.entries()):
            raise BudgetExceeded('A previous call in this job reported more usage than its authorized maximum; '
                                 'AI is stopped for this job. No API call made.')
        today = time.strftime('%Y-%m-%d', time.gmtime())
        funded = float(b['funded_usd'])
        if funded <= 0:
            raise BudgetExceeded('No owner-authorized API funding configured (budget.funded_usd = 0). '
                                 'No API call made.')
        total = self.ledger.spent()
        if total + estimate_usd > funded - float(b['reserve_usd']):
            raise BudgetExceeded(f'Call would cross the spending reserve: recorded ${total:.4f} + '
                                 f'estimate ${estimate_usd:.4f} > funded ${funded:.2f} - reserve '
                                 f'${float(b["reserve_usd"]):.2f}')
        if self.ledger.spent(job_id=job_id) + estimate_usd > float(b['max_job_usd']):
            raise BudgetExceeded(f'Per-job cap ${float(b["max_job_usd"]):.2f} would be exceeded')
        if self.ledger.spent(day=today) + estimate_usd > float(b['max_daily_usd']):
            raise BudgetExceeded(f'Daily cap ${float(b["max_daily_usd"]):.2f} would be exceeded')
        return True

    def paid_call(self, job_id, role, model, input_chars, max_output_tokens, approver, send, input_bytes=None):
        """Run `send()` only if estimated, authorized and owner-approved.

        approver(dict) -> bool : owner confirmation (UI dialog). Required.
        send() -> response with optional .usage
        """
        # Every refusal below happens BEFORE send(): no request, no ledger entry, no charge.
        est = estimate_cost(self.settings, model, input_chars, max_output_tokens, input_bytes)
        self.authorize(job_id, est)
        info = {'job_id': job_id, 'role': role, 'model': model, 'estimate_usd': est,
                'input_chars': input_chars, 'max_output_tokens': max_output_tokens}
        if approver is None or approver(info) is not True:
            raise SpendNotApproved('Owner did not approve this paid API call. No API call made.')
        try:
            resp = send()
        except Exception as e:
            # The request may or may not have reached OpenAI. Count the authorized maximum against the
            # caps (safe side) but label it as ASSUMED, not as a confirmed charge.
            self.ledger.record(job_id=job_id, role=role, model=model, status='FAILED_ASSUMED_MAX',
                               estimate_usd=est, charged_usd=est, confirmed_charge=False,
                               note='Call failed. Authorized maximum is reserved against your caps; OpenAI may '
                                    'not have billed anything. Check the OpenAI usage page.',
                               error=f'{type(e).__name__}: {str(e)[:200]}')
            raise
        usage = getattr(resp, 'usage', None)
        if usage is not None:
            cost, tin, tout = actual_cost(self.settings, model, usage)
            over = cost > est + 1e-9
            self.ledger.record(job_id=job_id, role=role, model=model, status='OK' if not over else 'OK_EXCEEDED_MAX',
                               estimate_usd=est, charged_usd=cost, input_tokens=tin, confirmed_charge=True,
                               output_tokens=tout, basis='response.usage x configured price',
                               exceeded_authorized=over)
        else:
            self.ledger.record(job_id=job_id, role=role, model=model, status='OK_NO_USAGE',
                               estimate_usd=est, charged_usd=est, confirmed_charge=False,
                               basis='authorized maximum (API returned no usage)')
        return resp
