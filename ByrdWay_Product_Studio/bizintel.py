"""Business intelligence for the Revenue & Media Division (MASTER SSOI Directives 1, 2, 4, 5).

Every figure carries an evidence label:
  FACT        verified record (imported sales, a cited public statistic)
  INFERENCE   analysis built on facts (stated reasoning)
  TARGET      a desired result (never shown as achieved)
  ASSUMPTION  an unverified input the owner must confirm or replace with measured data
Targets and projections are never presented as revenue. Capital is allocated only from FACT net profit.
"""
import datetime as dt

FACT, INFERENCE, TARGET, ASSUMPTION = 'FACT', 'INFERENCE', 'TARGET', 'ASSUMPTION'


def L(value, label, source=None, note=None):
    r = {'value': value, 'label': label}
    if source:
        r['source'] = source
    if note:
        r['note'] = note
    return r


# ------------------------------------------------------------------ Directive 4: market segments (cited, 2026-11-13)
SRC = {
    'naep12': 'https://www.nagb.gov/news-and-events/news-releases/2025/declines-in-8th-grade-science-and-12th-grade-math-and-reading.html',
    'naep8': 'https://usafacts.org/answers/what-percentage-of-students-in-the-us-are-proficient-in-math/',
    'apphys': 'https://apcentral.collegeboard.org/media/pdf/ap25-physics-1-score-distributions.pdf',
    'apcalc': 'https://apcentral.collegeboard.org/media/pdf/ap25-calculus-ab-score-distributions.pdf',
    'nheri': 'https://nheri.org/?p=309582',
    'pew_home': 'https://www.pewresearch.org/short-reads/2025/02/20/a-look-at-homeschooling-in-the-us/',
    'tpt': 'https://www.k12dive.com/news/ixl-learning-acquires-teachers-pay-teachers/644562/',
    'edchoice': 'https://www.edchoice.org/2025-a-kaleidoscope-view-of-k12-tutoring-in-america/',
    'tutor_mkt': 'https://www.kenresearch.com/us-online-tutoring-services-market',
    'ftce': 'https://nctq.org/dmsView/NCTQ_Driven_by_Data_Standout_Institutions_Socioeconomic_Diversity',
    'byrdway_store': 'https://www.teacherspayteachers.com/store/byrdway-mathematics-and-science',
}

# buyer type: classroom educator / parent (individual learner) / institution (multi-license) / adult self-buyer
SEGMENTS = [
    {'id': 'hs_math_teacher', 'segment': 'High-school mathematics (Algebra 1 to Calculus, Honors)', 'buyer': 'classroom educator',
     'learner': 'grades 9-12', 'problem': 'students below proficiency need step-by-step visual re-teaching the teacher has no time to build',
     'evidence': [L('22 % of 12th graders at or above NAEP Proficient in math (2024); 45 % below Basic', FACT, SRC['naep12']),
                  L('TpT used by 7M+ teachers, incl. 85 % of pre-K-12 educators (IXL, 2023)', FACT, SRC['tpt'])],
     'alternatives': 'free videos (Khan Academy, YouTube), textbook ancillaries, other TpT sellers',
     'willingness': L('teachers already buy on TpT; ByrdWay sells 30 products there', FACT, SRC['byrdway_store']),
     'advantage': 'complete courses with verified answers, Honors depth, Lil Dr. Byrd visual explainers + interactive Power Tools',
     'products': ['Power Tools', 'Lil Dr. Byrd Explainers', 'Concept Tiles', 'course bundles'],
     'channel': 'TpT search + listing optimisation; owner social (YouTube Shorts / TikTok) linking to TpT',
     'scores': {'demand': 5, 'margin': 4, 'cost': 5, 'time': 5, 'risk': 4}},
    {'id': 'ms_accelerated', 'segment': 'Middle-school accelerated math (7th-8th grade Algebra 1 / Geometry Honors)', 'buyer': 'classroom educator',
     'learner': 'grades 7-8', 'problem': 'accelerated students need high-school content at a middle-school reading level',
     'evidence': [L('about 28 % of 8th graders proficient in math (2024, secondary source - verify on NAEP)', INFERENCE, SRC['naep8'])],
     'alternatives': 'district curriculum, free videos', 'willingness': L('TpT teacher purchasing (same marketplace)', INFERENCE, SRC['tpt']),
     'advantage': 'existing Algebra 1 Honors and Geometry Honors products', 'products': ['Algebra 1 Honors', 'Geometry Honors bundles'],
     'channel': 'TpT search terms "algebra 1 honors", "geometry honors"', 'scores': {'demand': 4, 'margin': 4, 'cost': 5, 'time': 5, 'risk': 4}},
    {'id': 'ap_physics', 'segment': 'Physics + Honors / AP Physics 1', 'buyer': 'classroom educator and parent',
     'learner': 'grades 10-12', 'problem': 'physics reasoning and multi-step calculations; low first-time success',
     'evidence': [L('174,992 AP Physics 1 students in 2025; 67.3 % scored 3+', FACT, SRC['apphys'])],
     'alternatives': 'AP review books, free videos, other TpT physics sellers',
     'willingness': L('AP families buy review books and tutoring (category), not yet measured for ByrdWay', INFERENCE),
     'advantage': 'Physics + Honors Concept Tiles already built (100 tiles + Honors, 2973/2973 checks) awaiting owner approval',
     'products': ['Physics + Honors Concept Tiles', 'Physics Power Tool (next)'], 'channel': 'TpT + YouTube Shorts demos',
     'scores': {'demand': 4, 'margin': 4, 'cost': 5, 'time': 5, 'risk': 3}},
    {'id': 'ap_calc', 'segment': 'AP / College Calculus', 'buyer': 'classroom educator, parent, college student',
     'learner': 'grades 11-12 and college', 'problem': 'limits, derivatives and integrals without conceptual pictures',
     'evidence': [L('286,722 AP Calculus AB students in 2025; 64.2 % scored 3+', FACT, SRC['apcalc'])],
     'alternatives': 'AP review books, Khan Academy, tutoring', 'willingness': L('same AP review category', INFERENCE),
     'advantage': 'existing Calculus product line', 'products': ['Calculus Power Tool / Explainer bundles'],
     'channel': 'TpT + Shorts', 'scores': {'demand': 4, 'margin': 4, 'cost': 4, 'time': 4, 'risk': 3}},
    {'id': 'homeschool', 'segment': 'Homeschool families (math and science)', 'buyer': 'parent (individual learner)',
     'learner': 'K-12 at home', 'problem': 'parents must teach upper-level math/science they may not know',
     'evidence': [L('about 3.4M K-12 homeschool students in 2024-25 (NHERI estimate, range 3.07-3.75M)', FACT, SRC['nheri']),
                  L('3.4 % of K-12 students homeschooled in 2022-23 (Pew analysis of NCES)', FACT, SRC['pew_home'])],
     'alternatives': 'boxed curricula, online courses, co-ops',
     'willingness': L('parents report willingness to pay for tutoring (avg $357/month stated, July 2025)', FACT, SRC['edchoice']),
     'advantage': 'self-teaching visual explainers + answer keys a parent can follow',
     'products': ['full-course bundles with answer keys'], 'channel': 'TpT (parents buy there too) + Facebook/Instagram homeschool content',
     'scores': {'demand': 4, 'margin': 5, 'cost': 4, 'time': 4, 'risk': 3}},
    {'id': 'tutoring', 'segment': 'Tutors and tutoring centers', 'buyer': 'institution / independent tutor',
     'learner': 'grades 6-college', 'problem': 'tutors need ready, accurate, visual lesson material',
     'evidence': [L('19 % of parents report a child receiving tutoring; 24 % more looking (Oct 2025)', FACT, SRC['edchoice']),
                  L('US online tutoring market about $4.3B (2024, research-firm estimate)', INFERENCE, SRC['tutor_mkt'])],
     'alternatives': 'tutors make their own; commercial curricula', 'willingness': L('not measured for ByrdWay', ASSUMPTION),
     'advantage': 'licensable verified content', 'products': ['multi-license bundles (owner to price)'],
     'channel': 'warm network first (owner contacts), then direct outreach with owner approval',
     'scores': {'demand': 3, 'margin': 4, 'cost': 3, 'time': 3, 'risk': 3}},
    {'id': 'college_math', 'segment': 'College mathematics and statistics', 'buyer': 'college student (adult self-buyer), instructor',
     'learner': 'undergraduates', 'problem': 'gateway courses (College Algebra, Statistics) with high failure rates',
     'evidence': [L('ByrdWay College Statistics Visual Guide listed at $49.99 on TpT', FACT, SRC['byrdway_store'])],
     'alternatives': 'textbook platforms, free videos, Chegg-type services', 'willingness': L('not measured', ASSUMPTION),
     'advantage': 'anime-style visual guides', 'products': ['College Algebra', 'College Statistics'], 'channel': 'TikTok/YouTube Shorts',
     'scores': {'demand': 3, 'margin': 4, 'cost': 4, 'time': 4, 'risk': 3}},
    {'id': 'teacher_cert', 'segment': 'Teacher certification exams (FTCE, Praxis math)', 'buyer': 'adult self-buyer (teacher candidate)',
     'learner': 'teacher candidates', 'problem': 'high first-attempt failure on content exams',
     'evidence': [L('FTCE Elementary Education first-attempt state pass rate 34 % (NCTQ; not math-specific)', FACT, SRC['ftce'])],
     'alternatives': 'official prep guides, prep courses', 'willingness': L('candidates pay retake fees (category inference)', INFERENCE),
     'advantage': 'owner is a 30-year math educator with an M.S. in mathematics and an existing FTCE product',
     'products': ['FTCE math prep'], 'channel': 'TpT + education-candidate communities',
     'scores': {'demand': 3, 'margin': 5, 'cost': 4, 'time': 4, 'risk': 3}},
    {'id': 'bio_chem', 'segment': 'High-school Biology and Chemistry', 'buyer': 'classroom educator', 'learner': 'grades 9-12',
     'problem': 'abstract processes need visual explanation', 'evidence': [], 'alternatives': 'textbook, free videos',
     'willingness': L('existing Biology and Chemistry products on TpT', FACT, SRC['byrdway_store']), 'advantage': 'same visual format',
     'products': ['Biology', 'Chemistry'], 'channel': 'TpT', 'scores': {'demand': 3, 'margin': 4, 'cost': 4, 'time': 4, 'risk': 3}},
    {'id': 'college_ready', 'segment': 'College readiness / SAT-ACT math', 'buyer': 'parent, student', 'learner': 'grades 10-12',
     'problem': 'math gaps before college placement', 'evidence': [L('45 % of 12th graders below NAEP Basic in math (2024)', FACT, SRC['naep12'])],
     'alternatives': 'test-prep companies, free practice tests', 'willingness': L('not measured', ASSUMPTION), 'advantage': 'gap-repair visuals',
     'products': ['review bundles (proposed)'], 'channel': 'Shorts + TpT', 'scores': {'demand': 3, 'margin': 3, 'cost': 3, 'time': 3, 'risk': 3}},
    {'id': 'graduate', 'segment': 'Graduate mathematics / advanced physics', 'buyer': 'adult self-buyer', 'learner': 'graduate students',
     'problem': 'proof-based courses lack visual intuition', 'evidence': [],
     'alternatives': 'textbooks, lecture notes, free courseware', 'willingness': L('not measured', ASSUMPTION),
     'advantage': 'none proven yet; graduate proofs are never labeled machine-verified', 'products': ['future (expansion blueprint)'],
     'channel': 'not chosen', 'scores': {'demand': 2, 'margin': 3, 'cost': 2, 'time': 1, 'risk': 2}},
]
WEIGHTS = {'demand': 0.30, 'margin': 0.25, 'cost': 0.15, 'time': 0.15, 'risk': 0.15}   # contribution profit first


def rank_segments():
    """Rank by expected contribution profit (margin x demand), implementation cost, time and risk (5 = best).
    Scores are INFERENCE from the cited evidence; a segment without cited demand evidence is capped."""
    out = []
    for s in SEGMENTS:
        sc = dict(s['scores'])
        if not any(e['label'] == FACT for e in s['evidence']):
            sc['demand'] = min(sc['demand'], 2)
        total = round(sum(sc[k] * w for k, w in WEIGHTS.items()) / 5 * 100, 1)
        out.append(dict(s, score=L(total, INFERENCE, note='weighted 0-100: demand 30 %, margin 25 %, cost/time/risk 15 % each')))
    return sorted(out, key=lambda x: -x['score']['value'])


# ------------------------------------------------------------------ Directive 1: labeled financials + acquisition plan
def financials(dash):
    """Dashboard numbers with labels. Imported, non-TEST sales are FACT; week targets are TARGET."""
    weeks = dash.get('weeks', [])
    return {'units_total': L(dash.get('units_total', 0), FACT, 'imported TpT sales report (TEST rows excluded)'),
            'net_total': L(dash.get('net_total', 0), FACT, 'imported TpT sales report'),
            'real_rows': L(dash.get('real_rows', 0), FACT),
            'weekly': [{'week': w['week'], 'actual_units': L(w['units'], FACT), 'target_minimum': L(w['minimum'], TARGET),
                        'target_stretch': L(w['stretch'], TARGET), 'net': L(w['net'], FACT), 'status': w['status']} for w in weeks],
            'long_term': [L(f'${v:,} per month', TARGET, note='aspiration, not a forecast') for v in (10_000, 100_000, 1_000_000, 10_000_000)]}


def acquisition_plan(target_units_week=125, avg_price=None, measured=None):
    """What it takes to reach a unit target. Conversion inputs are ASSUMPTIONS until real numbers are measured
    (measured = {'visit_to_buy': x, 'view_to_visit': y, 'views_per_post': z} from imported data -> FACT)."""
    m = measured or {}
    v2b = L(m['visit_to_buy'], FACT) if 'visit_to_buy' in m else L(0.02, ASSUMPTION, note='2 % listing visit -> purchase; replace with TpT stats')
    v2v = L(m['view_to_visit'], FACT) if 'view_to_visit' in m else L(0.01, ASSUMPTION, note='1 % video view -> listing visit')
    vpp = L(m['views_per_post'], FACT) if 'views_per_post' in m else L(1000, ASSUMPTION, note='views per short; measure from Blotato analytics')
    visits = target_units_week / v2b['value']
    views = visits / v2v['value']
    posts = views / vpp['value']
    lab = INFERENCE if all(x['label'] == FACT for x in (v2b, v2v, vpp)) else ASSUMPTION
    return {'target_units_week': L(target_units_week, TARGET), 'visit_to_buy': v2b, 'view_to_visit': v2v, 'views_per_post': vpp,
            'listing_visits_needed': L(round(visits), lab), 'video_views_needed': L(round(views), lab),
            'posts_needed_per_week': L(round(posts, 1), lab),
            'capacity_check': L(f'{round(posts / 7, 1)} posts/day across channels; Blotato publishes, the owner approves each',
                                lab, note='operating-capacity check: approval time is the owner constraint'),
            'avg_price': L(avg_price, FACT) if avg_price else L(None, ASSUMPTION, note='set from imported sales'),
            'rule': 'scale content volume only when the measured constraint is reach (AH-31)'}


# ------------------------------------------------------------------ Directive 2: capital allocation (shared service)
def capital_allocation(net_last_30d, monthly_operating_cost=None, reserve_months=3, cash_on_hand=None):
    """Recommendation only; the owner decides. Allocates only FACT net profit; nothing when net <= 0 or unknown.
    Tax set-aside % is an ASSUMPTION to confirm with the owner's tax professional."""
    if net_last_30d is None:
        return {'recommendation': 'NO ALLOCATION - net profit not measured (import TpT sales first)', 'buckets': [],
                'label': FACT}
    if net_last_30d <= 0:
        return {'recommendation': 'NO ALLOCATION - last 30 days not profitable; spend $0 beyond existing subscriptions',
                'buckets': [], 'label': FACT, 'net_last_30d': L(net_last_30d, FACT)}
    net = net_last_30d
    tax = L(0.25, ASSUMPTION, note='confirm with tax professional')
    after_tax = net * (1 - tax['value'])
    reserve_needed = (monthly_operating_cost or 0) * reserve_months - (cash_on_hand or 0)
    to_reserve = max(0.0, min(after_tax * 0.5, reserve_needed)) if monthly_operating_cost else after_tax * 0.3
    rest = after_tax - to_reserve
    b = [('taxes (set aside)', net * tax['value'], 'assumption rate'),
         ('operating reserve', to_reserve, f'until {reserve_months} months of operating cost are covered'),
         ('reinvest in the measured bottleneck only', rest * 0.5, 'e.g. the one channel with proven sales; no unproven channels'),
         ('owner pay / giving (owner decides)', rest * 0.5, 'owner discretion')]
    return {'recommendation': 'ALLOCATE FROM VERIFIED NET ONLY (owner approves every payment)', 'net_last_30d': L(net, FACT),
            'tax_rate': tax, 'buckets': [{'bucket': n, 'amount': L(round(a, 2), INFERENCE), 'why': w} for n, a, w in b],
            'rule': 'no new spending until a channel shows repeatable sales at its minimum sample'}


# ------------------------------------------------------------------ Directive 5: per-product offer test
OFFER_CHECKS = ['customer_problem', 'promised_outcome', 'proof_of_function', 'demonstration', 'perceived_value',
                'price_vs_alternatives', 'licensing', 'bundles', 'objections', 'purchase_friction', 'post_purchase']


def offer_test(p):
    """11 offer checks per product, each PASS / NEEDS EVIDENCE / NEEDS OWNER, from product FACTS only."""
    r = {}
    r['customer_problem'] = ('PASS', f"problem stated: {p['problem']}") if p.get('problem') else ('NEEDS EVIDENCE', 'state the learner problem')
    r['promised_outcome'] = ('PASS', p['outcome']) if p.get('outcome') else ('NEEDS EVIDENCE', 'state a specific educational outcome (no guarantees)')
    r['proof_of_function'] = ('PASS', 'Studio QA PASS') if p.get('qa') == 'PASS' else ('NEEDS EVIDENCE', 'run Studio QA')
    r['demonstration'] = ('PASS', 'preview pages / demo video') if p.get('preview') or p.get('demo_video') else ('NEEDS EVIDENCE', 'add preview pages or a 30-s demo')
    r['perceived_value'] = ('PASS', 'answer keys + full scope') if p.get('answer_keys') and p.get('scope') == 'full course' else ('NEEDS EVIDENCE', 'show answer keys and full scope')
    r['price_vs_alternatives'] = ('PASS', f"${p['price']} vs comparables {p['comparable_prices']}") if p.get('price') and p.get('comparable_prices') else ('NEEDS EVIDENCE', 'record 3 comparable TpT prices (free public pages)')
    r['licensing'] = ('PASS', 'multi-license offered') if p.get('multi_license') else ('NEEDS OWNER', 'decide on a multi-license price')
    r['bundles'] = ('PASS', f"bundle: {p['bundle']}") if p.get('bundle') else ('NEEDS OWNER', 'approve a course-family bundle')
    r['objections'] = ('PASS', '; '.join(p['objections'])) if p.get('objections') else ('NEEDS EVIDENCE', 'collect objections from reviews/questions')
    r['purchase_friction'] = ('PASS', 'single-file, no account needed') if p.get('no_prep') else ('NEEDS EVIDENCE', 'check how fast a buyer gets a first win')
    r['post_purchase'] = ('PASS', f"rating {p['rating']}") if p.get('rating') else ('NEEDS EVIDENCE', 'no ratings yet: ask satisfied buyers (voluntary, unpaid)')
    passed = sum(1 for v in r.values() if v[0] == 'PASS')
    return {'product': p.get('title'), 'checks': {k: {'status': s, 'detail': d} for k, (s, d) in r.items()},
            'passed': f'{passed}/{len(OFFER_CHECKS)}', 'rule': 'no fabricated testimonials, urgency, scarcity, credentials or outcomes'}


def report(dash, catalog=None, net_last_30d=None, monthly_operating_cost=None):
    return {'date': dt.date.today().isoformat(), 'segments': rank_segments(), 'financials': financials(dash),
            'acquisition_plan': acquisition_plan(), 'capital_allocation': capital_allocation(net_last_30d, monthly_operating_cost),
            'offer_tests': [offer_test(p) for p in (catalog or [])],
            'labels': {FACT: 'verified record', INFERENCE: 'evidence-based analysis', TARGET: 'desired result (not achieved)',
                       ASSUMPTION: 'unverified input - confirm or measure'}}
