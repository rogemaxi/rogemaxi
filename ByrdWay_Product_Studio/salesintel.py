"""Revenue & Media Division: 10 specialist roles, source-linked method library, daily sales workflow,
revenue dashboard, Lil Dr. Byrd media packages, independent Sales QA and measured experiments.

Hard rules (enforced in code, checked by role 10 Sales QA on every output):
  * nothing is published, sent, priced live or paid for by the app - it produces DRAFTS that wait for the owner;
  * only products whose Studio QA = PASS and that the owner approved may be marketed;
  * no invented testimonials, sales figures, reviews or expert endorsements; experts' METHODS are applied,
    experts are never quoted as endorsing ByrdWay and never impersonated;
  * no referral incentives (owner constraint); no guarantees of grades or income;
  * a method is promoted or retired only from measured results at or above the experiment's minimum sample.
All data lives in the private workspace (revenue/), never in the public repository.
"""
import csv
import datetime as dt
import json
import math
import re
from pathlib import Path

import sys as _sys
LIB_PATH = (Path(getattr(_sys, '_MEIPASS', '')) / 'sales_library.json') if getattr(_sys, 'frozen', False) \
    else Path(__file__).with_name('sales_library.json')
START_UNITS, MIN_GROWTH, STRETCH_GROWTH, MILESTONE = 125, 0.10, 0.17, 1000

ROLES = [
    # key, name, job, methods it applies (library ids)
    ('market_research', 'Market Researcher', 'Free research: what teachers search for, competitor prices and formats',
     ['AH-11', 'AH-12', 'AH-03', 'AH-30']),
    ('offer_pricing', 'Offer & Pricing Strategist', 'Bundles, value-equation scoring, price PROPOSALS (never live changes)',
     ['AH-06', 'AH-05', 'AH-02', 'AH-26', 'MG-01', 'AH-16', 'AH-24', 'AH-29']),
    ('prospector', 'Prospector', 'Segments and ranks schools, teachers, tutors, homeschool groups (local data, no paid lookups)',
     ['AH-12', 'AH-24', 'ZZ-02', 'AH-15']),
    ('script_storyboard', 'Script & Storyboard Writer', 'Lil Dr. Byrd video scripts and posts from VERIFIED products',
     ['AH-09', 'AH-08', 'AH-17', 'AH-07', 'ZZ-01', 'MG-02']),
    ('video_producer', 'Video Producer', '30-45 s Lil Dr. Byrd commercials on Blotato (or Google Flow / Firefly shot lists); owner approves',
     ['AH-08', 'AH-19']),
    ('social_publisher', 'Social Publisher', 'Publishes approved commercials to Facebook / Instagram / TikTok / YouTube via Blotato after owner approval',
     ['AH-11', 'AH-15', 'AH-27', 'GC-01', 'JR-03']),
    ('sales_followup', 'Sales & Follow-up', 'Outreach and follow-up DRAFTS awaiting owner approval',
     ['GC-02', 'GC-03', 'ZZ-02', 'AH-17', 'MG-02', 'AH-28']),
    ('retention', 'Retention & Ascension', 'Repeat purchases: next unit, bundle and license paths for existing buyers',
     ['AH-01', 'MG-03', 'AH-13', 'AH-20', 'AH-28']),
    ('revenue_tracker', 'Revenue Tracker', 'Paid units, gross, fees, refunds, net vs targets; pipeline stages',
     ['AH-18', 'AH-04', 'AH-25', 'JR-02', 'GC-01', 'AH-29', 'AH-31']),
    ('sales_qa', 'Sales QA & Compliance', 'Independent check of every draft and every claim; experiment discipline',
     ['AH-22', 'AH-14', 'AH-10', 'AH-09', 'JR-01', 'LH-01', 'AH-31']),
]


# ------------------------------------------------------------------ library
def library():
    return json.loads(LIB_PATH.read_text(encoding='utf-8'))


def methods_for(role_key):
    lib = {m['id']: m for m in library()['methods']}
    ids = next(r[3] for r in ROLES if r[0] == role_key)
    return [lib[i] for i in ids if i in lib and lib[i]['status'] == 'ACTIVE']


def library_qa():
    """Independent check of the library itself."""
    lib = library()
    out = []
    for m in lib['methods']:
        s = m['source']
        out.append((f'library.{m["id"]}.source', bool(s.get('citation')), s.get('citation')))
        out.append((f'library.{m["id"]}.metric', bool(m.get('metric')), m.get('metric')))
        if s.get('quote'):
            out.append((f'library.{m["id"]}.quote_short', len(s['quote'].split()) <= 25, f'{len(s["quote"].split())} words'))
            out.append((f'library.{m["id"]}.quote_verified', 'verified verbatim' in s.get('verification', ''), s.get('verification')))
    out.append(('library.referral_incentives_excluded',
                all(m['status'] == 'EXCLUDED' for m in lib['methods'] if 'referral' in m['method'].lower()), 'owner constraint'))
    used = {i for r in ROLES for i in r[3]}
    out.append(('library.every_role_equipped', all(methods_for(r[0]) for r in ROLES), f'{len(used)} methods assigned'))
    return out


# ------------------------------------------------------------------ workspace data
def _dir(root):
    d = Path(root) / 'revenue'
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load(root, name, default):
    p = _dir(root) / name
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def _save(root, name, data):
    p = _dir(root) / name
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding='utf-8')
    tmp.replace(p)


def settings(root):
    return _load(root, 'settings.json', {'week1_start': None, 'catalog': [], 'prospects': []})


def save_settings(root, s):
    _save(root, 'settings.json', s)


# ------------------------------------------------------------------ revenue ledger + targets (role 9)
_COLS = {'date': ('date', 'order date', 'sale date', 'transaction date'),
         'product': ('product', 'product name', 'item', 'title', 'resource'),
         'units': ('units', 'quantity', 'qty', 'licenses'),
         'gross': ('gross', 'price', 'sale price', 'amount', 'item total'),
         'fees': ('fees', 'fee', 'transaction fee', 'tpt fee'),
         'refund': ('refund', 'refunds', 'refunded'),
         'buyer': ('buyer', 'buyer id', 'customer', 'customer id', 'order id')}


def import_sales_csv(root, path, source='TpT sales report'):
    """Import a sales CSV (column names matched flexibly). Rows marked TEST are kept for audit but excluded."""
    with open(path, encoding='utf-8-sig', newline='') as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return {'imported': 0}
    hdr = {h.lower().strip(): h for h in rows[0]}
    col = {k: next((hdr[a] for a in alts if a in hdr), None) for k, alts in _COLS.items()}
    if not col['date'] or not col['gross']:
        raise ValueError(f'CSV needs at least a date and an amount column; found {list(rows[0])}')
    num = lambda v: float(re.sub(r'[^0-9.\-]', '', str(v)) or 0)
    led = _load(root, 'ledger.json', [])
    seen = {json.dumps(r['raw'], sort_keys=True) for r in led}
    n = 0
    for r in rows:
        if json.dumps(r, sort_keys=True) in seen:
            continue
        d = _date(r[col['date']])
        text = ' '.join(str(v) for v in r.values()).upper()
        led.append({'date': d.isoformat() if d else None, 'product': r.get(col['product'] or '', ''),
                    'units': int(num(r[col['units']])) if col['units'] and r.get(col['units']) else 1,
                    'gross': num(r[col['gross']]), 'fees': num(r[col['fees']]) if col['fees'] else 0.0,
                    'refund': num(r[col['refund']]) if col['refund'] else 0.0,
                    'buyer': r.get(col['buyer'] or '', ''), 'test': 'TEST' in text, 'source': source, 'raw': r})
        n += 1
    _save(root, 'ledger.json', led)
    return {'imported': n, 'columns': col}


def _date(s):
    for f in ('%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%d %b %Y', '%b %d, %Y', '%Y-%m-%d %H:%M:%S'):
        try:
            return dt.datetime.strptime(str(s).strip()[:len(dt.date.today().strftime(f)) + 9].strip(), f).date()
        except ValueError:
            continue
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def weekly_targets(n_weeks=26):
    out = []
    for w in range(1, n_weeks + 1):
        out.append({'week': w, 'minimum': math.ceil(START_UNITS * (1 + MIN_GROWTH) ** (w - 1)),
                    'stretch': math.ceil(START_UNITS * (1 + STRETCH_GROWTH) ** (w - 1))})
    return out


def milestone_week(growth):
    return 1 + math.ceil(math.log(MILESTONE / START_UNITS) / math.log(1 + growth))


def dashboard(root, today=None):
    """Weekly actuals vs targets, real sales only (TEST rows excluded but counted for audit)."""
    s = settings(root)
    led = _load(root, 'ledger.json', [])
    real = [r for r in led if not r['test'] and r['date']]
    today = today or dt.date.today()
    start = dt.date.fromisoformat(s['week1_start']) if s.get('week1_start') else None
    weeks = []
    if start:
        n = max(1, (today - start).days // 7 + 1)
        tg = {t['week']: t for t in weekly_targets(max(n, 1))}
        for w in range(1, n + 1):
            a, b = start + dt.timedelta(days=7 * (w - 1)), start + dt.timedelta(days=7 * w)
            rs = [r for r in real if a <= dt.date.fromisoformat(r['date']) < b]
            units = sum(r['units'] for r in rs)
            gross, fees, ref = sum(r['gross'] for r in rs), sum(r['fees'] for r in rs), sum(r['refund'] for r in rs)
            status = ('MET STRETCH' if units >= tg[w]['stretch'] else 'MET MINIMUM' if units >= tg[w]['minimum']
                      else 'IN PROGRESS' if b > today else 'BELOW MINIMUM - corrective action required')
            weeks.append({'week': w, 'from': a.isoformat(), 'units': units, 'minimum': tg[w]['minimum'],
                          'stretch': tg[w]['stretch'], 'gross': round(gross, 2), 'fees': round(fees, 2),
                          'refunds': round(ref, 2), 'net': round(gross - fees - ref, 2), 'status': status})
    buyers = {}
    for r in real:
        if r['buyer']:
            buyers.setdefault(r['buyer'], set()).add(r['date'])
    repeat = sum(1 for v in buyers.values() if len(v) > 1)
    return {'week1_start': s.get('week1_start'), 'weeks': weeks, 'real_rows': len(real),
            'test_rows_excluded': sum(1 for r in led if r['test']),
            'units_total': sum(r['units'] for r in real),
            'net_total': round(sum(r['gross'] - r['fees'] - r['refund'] for r in real), 2),
            'repeat_purchase_rate': f'{repeat}/{len(buyers)}' if buyers else 'no buyer IDs in the data yet',
            'milestone_1000': {'minimum_path_week': milestone_week(MIN_GROWTH), 'stretch_path_week': milestone_week(STRETCH_GROWTH)},
            'corrective_actions': _load(root, 'actions.json', [])}


def record_corrective_action(root, week, action, owner):
    a = _load(root, 'actions.json', [])
    a.append({'week': week, 'action': action, 'by': owner, 'at': dt.datetime.now().isoformat(timespec='seconds')})
    _save(root, 'actions.json', a)


# ------------------------------------------------------------------ catalog (verified + approved gate)
def marketable(catalog):
    return [p for p in catalog if p.get('qa') == 'PASS' and p.get('owner_approved') is True]


# ------------------------------------------------------------------ role 2: offers (value equation, stacking, ladder)
def value_score(p):
    """Value equation (AH-06) on a 1-10 scale per factor, from FACTS about the product only."""
    outcome = 9 if p.get('scope') == 'full course' else 7 if p.get('scope') == 'unit set' else 5
    likelihood = min(10, 5 + (2 if p.get('qa') == 'PASS' else 0) + (2 if p.get('answer_keys') else 0) + (1 if p.get('preview') else 0))
    delay = 3 if p.get('first_win_minutes', 60) <= 20 else 5
    effort = 2 if p.get('no_prep') else 5
    return {'outcome': outcome, 'likelihood': likelihood, 'time_delay': delay, 'effort': effort,
            'score': round(outcome * likelihood / (delay * effort), 2)}


def offer_proposals(catalog):
    """Bundles by course family (AH-05 anchor high, MG-01 offer stack, AH-13 cut once sell twice), PROPOSALS only."""
    ok = marketable(catalog)
    by_course = {}
    for p in ok:
        by_course.setdefault(p.get('course') or p['title'], []).append(p)
    out = []
    for course, items in sorted(by_course.items()):
        total = round(sum(i['price'] for i in items), 2)
        price_txt = lambda i: f'${i["price"]:.2f}' if i.get('price') else 'price: OWNER TO SET'
        prop = {'course': course, 'components': [f'{i["title"]} ({price_txt(i)})' for i in items],
                'sum_of_individual_prices': total, 'status': 'PROPOSAL - owner decides; live prices are never changed by the app',
                'methods': ['AH-05', 'MG-01', 'AH-13', 'AH-06'],
                'value_equation': [dict(value_score(i), product=i['title']) for i in items]}
        if len(items) >= 2 and all(i.get('price') for i in items):
            prop['proposed_bundle_price'] = round(total * 0.8, 2)
            prop['stack_note'] = f'Stack shows each component at its real individual price; total ${total:.2f}.'
        else:
            prop['next_step'] = 'Single verified product: build the companion formats for this course to form a bundle (AH-13).'
        out.append(prop)
    return out


def van_westendorp(responses):
    """AH-03. responses: [{'too_cheap','bargain','expensive','too_expensive'}...] from REAL survey answers.
    Returns the acceptable range (point of marginal cheapness .. point of marginal expensiveness) and optimal price."""
    if len(responses) < 20:
        return {'status': 'NOT ENOUGH DATA', 'n': len(responses), 'need': 20}
    prices = sorted({float(r[k]) for r in responses for k in ('too_cheap', 'bargain', 'expensive', 'too_expensive')})
    n = len(responses)
    share = lambda k, p, ge: sum(1 for r in responses if (float(r[k]) >= p if ge else float(r[k]) <= p)) / n
    def cross(f, g):
        best = min(prices, key=lambda p: abs(f(p) - g(p)))
        return best
    tc = lambda p: share('too_cheap', p, True)
    te = lambda p: share('too_expensive', p, False)
    ch = lambda p: share('bargain', p, True)
    ex = lambda p: share('expensive', p, False)
    return {'status': 'OK', 'n': n, 'point_of_marginal_cheapness': cross(tc, ex),
            'point_of_marginal_expensiveness': cross(ch, te), 'optimal_price_point': cross(tc, te)}


# ------------------------------------------------------------------ role 3: prospects
SEGMENT_FIT = {'homeschool': 3, 'teacher': 4, 'tutoring': 4, 'school': 5, 'district': 5}


def rank_prospects(prospects):
    """AH-12 who-we-serve + AH-24 upmarket. Local list only (no paid lookups)."""
    def sc(p):
        return SEGMENT_FIT.get(p.get('segment', '').lower(), 1) * 2 + (2 if p.get('course_match') else 0) + \
               (1 if p.get('warm') else 0)
    return sorted(({**p, 'fit_score': sc(p)} for p in prospects), key=lambda x: -x['fit_score'])


# ------------------------------------------------------------------ roles 4-6: media package
PLATFORMS = {'TikTok / Reels / Shorts': {'aspect': '9:16', 'max_s': 60}, 'YouTube': {'aspect': '16:9', 'max_s': 180},
             'Pinterest': {'aspect': '2:3', 'max_s': 0}}


def media_package(product, credential):
    """Lil Dr. Byrd script + storyboard + posts for ONE verified product. Uses the product's own verified example."""
    ex = product.get('sample_example') or {}
    hook = f'{credential}: here is {product["title"]} - every answer machine-checked.'
    scenes = [
        {'t': '0-3 s', 'shot': 'Lil Dr. Byrd points at camera', 'on_screen': credential, 'voice': hook, 'method': 'AH-09'},
        {'t': '3-12 s', 'shot': 'Problem card', 'on_screen': ex.get('problem', product['title']),
         'voice': 'Students get stuck right here.', 'method': 'ZZ-01'},
        {'t': '12-35 s', 'shot': 'Step-by-step on the tile', 'on_screen': ' -> '.join(ex.get('steps', [])[:3]),
         'voice': f'Step by step: {ex.get("answer", "")}', 'method': 'AH-08'},
        {'t': '35-45 s', 'shot': 'Real QA evidence screen', 'on_screen': product.get('proof', 'Verified by the ByrdWay Studio'),
         'voice': 'Every page checked before you ever see it.', 'method': 'AH-08'},
        {'t': '45-55 s', 'shot': 'Product preview pages', 'on_screen': product['title'],
         'voice': 'Less prep for you, more wins for them. Link in bio.', 'method': 'AH-17', 'also': 'MG-02'}]
    caption = (f'{product["title"]}: {product.get("promise", "one idea per tile, worked examples, answer keys")}. '
               f'Every answer verified. #ByrdWay #LilDrByrd #{re.sub(r"[^A-Za-z]", "", product.get("course", "math"))}')
    return {'product': product['title'], 'status': 'DRAFT - Video Producer renders on Blotato (or Google Flow / Firefly); owner approves every post',
            'hook': hook, 'scenes': scenes, 'caption': caption, 'platforms': PLATFORMS,
            'production_brief': {'tool': 'Blotato (API) or Google Flow / Adobe Firefly (shot list)', 'mascot': 'approved Lil Dr. Byrd asset only',
                                 'length_s': 55, 'captions': 'burned-in, high contrast'},
            'methods': sorted({s['method'] for s in scenes} | {s['also'] for s in scenes if s.get('also')})}


def followup_drafts(prospect, product):
    """Roles 7/3: question-first outreach (ZZ-02), help-first (ZZ-01), plus/minus copy (AH-17), follow-up cadence (GC-02)."""
    name = prospect.get('contact') or 'there'
    q = f'Hi {name}, what is the hardest topic for your {product.get("course", "students")} students this term?'
    body = (f'{q}\nWe built {product["title"]}: {product.get("promise", "one idea per page with worked examples and answer keys")}. '
            f'Every answer is checked by our verification Studio before release, so you spend less time correcting keys '
            f'and more time teaching. If it helps, here is the preview: {product.get("url", "[listing link]")}')
    return [{'day': d, 'to': prospect.get('name'), 'product': product['title'], 'subject': s, 'body': b, 'status': 'DRAFT - owner sends',
             'methods': m} for d, s, b, m in (
        (0, f'A quick question about {product.get("course", "your course")}', body, ['ZZ-02', 'ZZ-01', 'AH-17']),
        (3, 'Following up', f'Hi {name}, following up on my note about {product["title"]}. Happy to send two sample pages.', ['GC-02']),
        (7, 'Last note for now', f'Hi {name}, I will not keep filling your inbox. If {product.get("course", "this course")} is ever on your plate, the preview is here: {product.get("url", "[listing link]")}', ['GC-02', 'JR-03']))]


def retention_paths(catalog):
    """Role 8: the next verified product for a buyer of each product (AH-01, MG-03, AH-13)."""
    ok = marketable(catalog)
    paths = []
    for p in ok:
        nxt = [q for q in ok if q is not p and q.get('course') == p.get('course')]
        up = [q for q in ok if q.get('family') == p.get('family') and q.get('course') != p.get('course')]
        paths.append({'bought': p['title'], 'next_same_course': [q['title'] for q in nxt][:2],
                      'next_course_same_format': [q['title'] for q in up][:2], 'methods': ['AH-01', 'MG-03', 'AH-13']})
    return paths


# ------------------------------------------------------------------ role 10: independent Sales QA
BANNED = [
    (r'\bguarantee[sd]?\b.*\b(grade|score|pass|income|money|result)', 'outcome guarantee'),
    (r'\b(testimonial|five[- ]star|5[- ]star|rated \d|reviews? say)', 'testimonial / review claim (only real, permissioned ones)'),
    (r'\b(\d[\d,]*)\s*(teachers|students|schools|customers|sales)\s+(love|use|bought|trust)', 'invented social-proof number'),
    (r'\b(alex|leila)\s+hormozi\b|\bmyron golden\b|\bgrant cardone\b|\bzig ziglar\b|\bjim rohn\b', 'named expert in customer-facing copy'),
    (r'\b(endorsed|recommended|approved) by\b', 'endorsement claim'),
    (r'\breferral\b.*\b(reward|bonus|credit|commission|incentive)', 'referral incentive (owner constraint)'),
    (r'\b(best|#1|number one)\b.*\b(in the world|on tpt|ever)\b', 'unverifiable superlative'),
]


def qa_text(text):
    hits = [why for pat, why in BANNED if re.search(pat, text, re.I)]
    return hits


def sales_qa(outputs, catalog):
    """Check every draft the division produced today. Returns (checks, blocked_items)."""
    approved = {p['title'] for p in marketable(catalog)}
    lib_ids = {m['id'] for m in library()['methods'] if m['status'] == 'ACTIVE'}
    checks, blocked = [], []
    for kind, items in outputs.items():
        for i, it in enumerate(items):
            text = json.dumps(it, ensure_ascii=False)
            prod = it.get('product') or it.get('bought') or it.get('course')
            problems = qa_text(text)
            if kind in ('media', 'followups') and prod not in approved:
                problems.append(f'product "{prod}" is not QA PASS + owner approved')
            meths = set(it.get('methods') or [])
            if not meths or not meths <= lib_ids:
                problems.append(f'methods not in the active library: {sorted(meths - lib_ids) or "none cited"}')
            if kind == 'media' and not any(s.get('method') == 'AH-09' and s['t'].startswith('0-') for s in it.get('scenes', [])):
                problems.append('opening does not answer "why listen?" in the first seconds (AH-09)')
            if 'DRAFT' not in str(it.get('status', '')) and 'PROPOSAL' not in str(it.get('status', '')) and kind != 'retention':
                problems.append('item is not marked as a draft/proposal awaiting the owner')
            cid = f'sales_qa.{kind}.{i + 1}'
            checks.append((cid, not problems, '; '.join(problems) or 'compliant'))
            if problems:
                blocked.append({'item': cid, 'problems': problems})
    return checks, blocked


# ------------------------------------------------------------------ experiments (continuous improvement)
def add_experiment(root, role, method_ids, hypothesis, metric, min_sample, variant_a, variant_b):
    ex = _load(root, 'experiments.json', [])
    e = {'id': f'EXP-{len(ex) + 1:03d}', 'role': role, 'methods': method_ids, 'hypothesis': hypothesis, 'metric': metric,
         'min_sample': min_sample, 'variants': {'A': {'desc': variant_a, 'n': 0, 'wins': 0}, 'B': {'desc': variant_b, 'n': 0, 'wins': 0}},
         'status': 'RUNNING', 'started': dt.date.today().isoformat()}
    ex.append(e)
    _save(root, 'experiments.json', ex)
    return e


def record_result(root, exp_id, variant, n, wins):
    """Record MEASURED results (e.g. visitors and purchases). Closes the experiment only at minimum sample (AH-14)."""
    ex = _load(root, 'experiments.json', [])
    e = next(x for x in ex if x['id'] == exp_id)
    v = e['variants'][variant]
    v['n'] += int(n)
    v['wins'] += int(wins)
    A, B = e['variants']['A'], e['variants']['B']
    if A['n'] >= e['min_sample'] and B['n'] >= e['min_sample']:
        ra, rb = A['wins'] / A['n'], B['wins'] / B['n']
        p = (A['wins'] + B['wins']) / (A['n'] + B['n'])
        se = math.sqrt(max(p * (1 - p) * (1 / A['n'] + 1 / B['n']), 1e-12))
        z = (rb - ra) / se
        e['result'] = {'rate_A': round(ra, 4), 'rate_B': round(rb, 4), 'z': round(z, 2),
                       'winner': 'B' if z > 1.96 else 'A' if z < -1.96 else 'no significant difference'}
        e['status'] = 'CLOSED'
    _save(root, 'experiments.json', ex)
    return e


def method_scorecard(root):
    """Which methods have measured wins. Never inferred: only CLOSED experiments count."""
    card = {}
    for e in _load(root, 'experiments.json', []):
        for m in e['methods']:
            c = card.setdefault(m, {'closed': 0, 'wins_for_B': 0, 'running': 0})
            if e['status'] == 'CLOSED':
                c['closed'] += 1
                c['wins_for_B'] += e['result']['winner'] == 'B'
            else:
                c['running'] += 1
    return card


# ------------------------------------------------------------------ the daily workflow
def run_daily(root, credential='Dr. Rogé J. Byrd, ByrdWay Mathematics & Science', today=None):
    """One day of the Revenue & Media Division. Produces drafts and measures; sends and spends nothing."""
    today = today or dt.date.today()
    s = settings(root)
    cat = s.get('catalog', [])
    ok = marketable(cat)
    out = {'offers': offer_proposals(cat),
           'media': [media_package(p, credential) for p in ok[:3]],
           'followups': [d for pr in rank_prospects(s.get('prospects', []))[:5] for d in
                         (followup_drafts(pr, next((p for p in ok if p.get('course') == pr.get('course')), ok[0]))[:1] if ok else [])],
           'retention': retention_paths(cat)}
    checks, blocked = sales_qa({k: v for k, v in out.items() if k in ('media', 'followups', 'offers', 'retention')}, cat)
    checks += library_qa()
    dash = dashboard(root, today)
    import roadmap
    evidence = {'weekly_units': [w['units'] for w in dash['weeks'] if w['status'] != 'IN PROGRESS'],
                'team_size': s.get('team_size', 1), 'products_listed': len(cat), 'products_qa_pass': len(ok),
                'reviews': s.get('store_reviews'), 'channel_weeks_with_sales': s.get('channel_weeks_with_sales', 0)}
    road = roadmap.assess(evidence)
    passed = sum(1 for c in checks if c[1])
    report = {
        'date': today.isoformat(),
        'roles': [{'role': n, 'job': j, 'methods_applied': [m['id'] for m in methods_for(k)]} for k, n, j, _ in ROLES],
        'catalog': {'products': len(cat), 'marketable (QA PASS + owner approved)': len(ok),
                    'held back (not verified or not approved)': len(cat) - len(ok)},
        'outputs': {'offer_proposals': len(out['offers']), 'media_packages': len(out['media']),
                    'followup_drafts': len(out['followups']), 'retention_paths': len(out['retention'])},
        'sales_qa': {'checks': len(checks), 'passed': passed, 'blocked': blocked},
        'measured': {'real_sales_rows': dash['real_rows'], 'test_rows_excluded': dash['test_rows_excluded'],
                     'units_total': dash['units_total'], 'net_total': dash['net_total'],
                     'repeat_purchase_rate': dash['repeat_purchase_rate'], 'weeks': dash['weeks'][-2:],
                     'experiments': method_scorecard(root)},
        'owner_queue': [f'approve {len(out["media"])} video package(s) for Blotato / Google Flow',
                        f'review {len(out["followups"])} outreach draft(s) - the app never sends',
                        f'decide on {sum(1 for o in out["offers"] if "proposed_bundle_price" in o)} bundle proposal(s) - live prices unchanged',
                        'import the latest TpT sales report so results are measured, not assumed'],
        'rules': library()['rules'],
        'roadmap': {'stage': road['diagnosis'], 'bottleneck': road['bottleneck'], 'daily_plan': road['plan'],
                    'evidence': evidence}}
    days = _load(root, 'daily_runs.json', [])
    days.append({'date': report['date'], 'outputs': report['outputs'], 'qa_passed': passed, 'qa_checks': len(checks),
                 'blocked': len(blocked)})
    _save(root, 'daily_runs.json', days)
    _save(root, f'day_{report["date"]}.json', {'report': report, 'outputs': out, 'checks': checks})
    report['discipline'] = f'{len({d["date"] for d in days})} day(s) with the full workflow run (JR-01)'
    return report, out
