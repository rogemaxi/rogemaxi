"""Owner-editable settings stored in <workspace>/settings.json.

API keys are NEVER stored here (see costs.get_api_key).
Prices: copied on 2026-11-09 from https://developers.openai.com/api/docs/pricing
(Standard tier, short-context, USD per 1M tokens). Prices change: the owner must
re-check that page and edit settings.json. A model with no price entry cannot
be called (the budget guard refuses to estimate an unknown price).
"""
import copy, json
from engine import workspace, write_json

PRICING_SOURCE = 'https://developers.openai.com/api/docs/pricing'
PRICING_COPIED_ON = '2026-11-09'

DEFAULTS = {
    'version': 2,
    'repair': {
        'max_iterations': 6,
        'max_runtime_seconds': 900,
        'no_progress_limit': 2,            # identical defect signature N times -> stop
        'repeat_failure_limit': 2,         # same fix failing N times -> escalate
        'quality_target': 99.9,
    },
    'budget': {
        'funded_usd': 0.0,                 # owner sets this after adding funds; 0 = AI disabled
        'reserve_usd': 1.00,               # never spend into the reserve
        'max_job_usd': 0.50,
        'max_daily_usd': 2.00,
        'estimate_safety_factor': 1.5,     # over-estimate before calls
    },
    'models': {                            # model selection by task complexity
        'simple': 'gpt-6-luna',
        'standard': 'gpt-6.1-terra',
        'complex': 'gpt-6.1-sol',
    },
    'pricing': {
        'gpt-6-astra':   {'input_per_1m': 10.00, 'output_per_1m': 50.00},
        'gpt-6.1-sol':   {'input_per_1m': 2.00,  'output_per_1m': 10.00},
        'gpt-6.1-terra': {'input_per_1m': 1.00,  'output_per_1m': 5.00},
        'gpt-6-luna':    {'input_per_1m': 0.10,  'output_per_1m': 0.50},
    },
    'pricing_source': PRICING_SOURCE,
    'pricing_copied_on': PRICING_COPIED_ON,
    'ai': {'max_input_chars': 12000, 'max_output_tokens': 1500, 'timeout_seconds': 45},
    'browser': {'timeout_ms': 15000, 'max_clicks': 80, 'chromium_path': ''},
}


def _merge(base, override):
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_settings(root):
    p = workspace(root) / 'settings.json'
    if not p.exists():
        write_json(p, DEFAULTS)
        return copy.deepcopy(DEFAULTS)
    try:
        user = json.loads(p.read_text(encoding='utf-8'))
    except ValueError:
        raise ValueError(f'settings.json is not valid JSON: {p}')
    s = _merge(DEFAULTS, user)
    validate_settings(s)
    return s


def save_settings(root, settings):
    validate_settings(settings)
    s = json.loads(json.dumps(settings))
    for k in list(s):
        if 'key' in k.lower() and k not in ('pricing',):
            raise ValueError('API keys must not be stored in settings.json')
    write_json(workspace(root) / 'settings.json', s)


def validate_settings(s):
    r, b = s['repair'], s['budget']
    if not 1 <= int(r['max_iterations']) <= 25:
        raise ValueError('max_iterations must be 1..25')
    if not 10 <= int(r['max_runtime_seconds']) <= 7200:
        raise ValueError('max_runtime_seconds must be 10..7200')
    for k in ('funded_usd', 'reserve_usd', 'max_job_usd', 'max_daily_usd'):
        if float(b[k]) < 0:
            raise ValueError(f'{k} cannot be negative')
    if float(b['max_job_usd']) > 20:
        raise ValueError('max_job_usd above $20 requires editing the code limit deliberately')
    if float(b['estimate_safety_factor']) < 1:
        raise ValueError('estimate_safety_factor must be >= 1')
    for m, p in s['pricing'].items():
        if float(p['input_per_1m']) <= 0 or float(p['output_per_1m']) <= 0:
            raise ValueError(f'pricing for {m} must be positive')
    return True
