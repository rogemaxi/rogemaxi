"""Acquisition.com $100M Scaling Roadmap -> ByrdWay implementation matrix, stage diagnosis and daily plan.

VERIFIED from the official pages (https://www.acquisition.com/training/scalingstart, retrieved 2026-11-13): the stage
names, their order and the team-size band shown beside each stage, and the official course pages (Scaling, Offers,
Leads, Money Models). The lessons are videos without captions; the official worksheets are delivered as a
"Personalized Roadmap" after the owner submits business details on acquisition.com/roadmap. Those materials were NOT
retrieved, so every 'purpose' below is an IMPLEMENTATION SUMMARY (owner's wording), not a quotation, and the official
decision criteria are marked NOT RETRIEVED until the owner supplies the personalized guide.

Stage diagnosis never places ByrdWay in a later stage than the evidence supports: it takes the LOWEST stage implied by
verified revenue, customer acquisition, operating capacity and team size.
"""
import datetime as dt

SRC = 'https://www.acquisition.com/training/'
OFFICIAL = {
    'scaling_course': SRC + 'scalingstart', 'offers_course': SRC + 'offers', 'leads_course': SRC + 'leads',
    'money_models_course': SRC + 'money/context', 'personalized_roadmap': 'https://www.acquisition.com/roadmap',
}
NOT_RETRIEVED = ('NOT RETRIEVED: the official lesson is a video without captions and the worksheets come with the '
                 'personalized roadmap (owner sign-up). Load the owner-supplied guide to fill this field.')

# (n, name, team band as shown on the official page, url slug, implementation summary (owner wording, not a quotation),
#  ByrdWay constraint, owning role, daily actions, metrics, verification before adoption)
STAGES = [
    (0, 'Improvise', '0-1', 'improvise', 'Establish a workable business foundation.',
     'Products exist; prove a real buyer wants a specific ByrdWay product.', 'market_research',
     ['Find 5 TpT search terms with demand for one verified course', 'Compare 3 competitor listings for that course (free pages only)'],
     ['search terms with visible demand', 'listings reviewed'], 'demand evidence recorded from public pages'),
    (1, 'Monetize', '0-1', 'monetize', 'Validate offers and generate paying customers.',
     'Verified paid units are not yet measured; listings may not convert.', 'offer_pricing',
     ['Run the listing checklist on the top 5 products (AH-16)', 'Draft one offer for a verified product using the value equation (AH-06)'],
     ['paid units per week (imported, TEST excluded)', 'listing conversion'], 'at least 4 weeks of imported real sales data'),
    (2, 'Advertise', '0-1', 'advertise', 'Develop repeatable customer acquisition.',
     'No single organic channel yet produces customers every week.', 'social_publisher',
     ['Owner publishes one proof-based Lil Dr. Byrd short on ONE channel (AH-08, AH-09)', 'Track clicks to the listing'],
     ['weekly paid units from the chosen channel', 'cost (owner hours) per customer'],
     'channel judged only at its minimum sample (AH-14)'),
    (3, 'Stabilize', '1-4', 'stabilize', 'Establish reliable operating processes.',
     'Delivery and QA depend on the owner; the Studio must keep quality without him.', 'sales_qa',
     ['Every product through Studio QA before listing', 'Daily workflow run and logged (JR-01)'],
     ['products listed with QA PASS', 'days the full workflow ran'], 'QA evidence on file for every listed product'),
    (4, 'Prioritize', '5-9', 'prioritize', 'Identify and address the highest-impact bottleneck.',
     'Effort is spread across 133 planned products instead of the one constraint.', 'revenue_tracker',
     ['Name the weekly constraint (demand vs supply, AH-31)', 'Stop work that does not address it'],
     ['constraint named weekly with evidence', 'change in the constraint metric'], 'before/after measurement of the fix'),
    (5, 'Productize', '10-19', 'productize', 'Standardize valuable, repeatable offerings.',
     'Course families must become standard bundles (tiles + explainer + power tool).', 'offer_pricing',
     ['Assemble one complete course family from verified products (AH-05, AH-13)'],
     ['bundle share of revenue', 'average order value'], 'owner-approved bundle with QA PASS components'),
    (6, 'Optimize', '20-49', 'optimize', 'Improve operating efficiency and performance.',
     'Conversion, retention and margin per product need measured improvement.', 'revenue_tracker',
     ['A/B one listing element at a time (experiments, minimum sample)'], ['conversion lift', 'net revenue per unit'],
     'closed experiment at or above minimum sample'),
    (7, 'Categorize', '50-99', 'categorize', 'Organize operations for greater scale.',
     'Not applicable yet: requires a multi-department team.', 'sales_qa', [], [], 'team size and revenue evidence'),
    (8, 'Specialize', '100-249', 'specialize', 'Develop focused expertise and responsibilities.',
     'Not applicable yet.', 'sales_qa', [], [], 'team size and revenue evidence'),
    (9, 'Capitalize', '250-500', 'capitalize', 'Allocate resources toward sustainable growth.',
     'Not applicable yet: reinvest only after operating needs are covered.', 'revenue_tracker', [], [],
     'audited financials'),
]


def matrix():
    return [{'stage': n, 'name': name, 'team_band_official': band, 'source': SRC + slug, 'verified': ['name', 'order', 'team band', 'source URL'],
             'purpose_summary': purpose, 'purpose_is_quotation': False, 'official_worksheets_and_criteria': NOT_RETRIEVED,
             'byrdway_constraint': constraint, 'owner_role': role, 'daily_actions': actions, 'metrics': metrics,
             'verification_before_adoption': verify}
            for n, name, band, slug, purpose, constraint, role, actions, metrics, verify in STAGES]


def _band_max_stage(team):
    """Highest stage whose official team band contains this team size (team size alone never lifts the stage)."""
    best = 0
    for n, _, band, *_ in STAGES:
        lo, hi = (int(x) for x in band.split('-'))
        if lo <= team <= hi:
            best = max(best, n)
    return best


def diagnose(evidence):
    """evidence: weekly_units (list of real paid units per week, oldest first), team_size, products_qa_pass,
    products_listed, repeat_rate (0-1 or None), reviews (int or None), channel_weeks_with_sales (int).
    Returns the LOWEST stage the evidence supports, the reasons, and what is unverified."""
    w = evidence.get('weekly_units') or []
    reasons, unverified = [], []
    if not w:
        unverified.append('no imported real sales data: revenue and acquisition are UNVERIFIED')
    paid = sum(w)
    caps = []
    if paid == 0:
        caps.append((0 if w else 1, 'no verified paid sale recorded' if w else
                     'stage cannot be confirmed above Monetize without sales data (provisional)'))
    consistent = len(w) >= 4 and all(x > 0 for x in w[-4:])
    if paid and not consistent:
        caps.append((1, 'paid sales exist but not in 4 consecutive weeks'))
    if consistent and evidence.get('channel_weeks_with_sales', 0) < 4:
        caps.append((2, 'sales are consistent but no single channel is proven repeatable'))
    if evidence.get('products_qa_pass', 0) < evidence.get('products_listed', 0):
        reasons.append(f'{evidence.get("products_listed", 0) - evidence.get("products_qa_pass", 0)} listed products are not yet Studio QA PASS '
                       f'(operating capacity / Stabilize work)')
    team_cap = _band_max_stage(int(evidence.get('team_size', 1)))
    caps.append((team_cap, f'team size {evidence.get("team_size", 1)} is inside the official band of stage {team_cap}'))
    stage = min(c[0] for c in caps)
    reasons = [c[1] for c in caps if c[0] == stage] + reasons
    if evidence.get('reviews') == 0:
        reasons.append('store shows no ratings yet (perceived likelihood of achievement is low: AH-06)')
    return {'stage': stage, 'name': STAGES[stage][1], 'provisional': bool(unverified), 'reasons': reasons, 'unverified': unverified,
            'rule': 'lowest stage supported by revenue, acquisition, capacity and team evidence'}


def bottleneck(diag, evidence):
    """The ONE constraint to work on (AH-31, Prioritize): measurement first, then demand, then capacity."""
    if diag['provisional']:
        return {'constraint': 'MEASUREMENT', 'why': 'without real sales data no growth decision can be verified',
                'fix': 'import the TpT sales report and set the Week 1 start date', 'owner_role': 'revenue_tracker',
                'then': 'DEMAND' if evidence.get('products_qa_pass', 0) else 'SUPPLY'}
    if evidence.get('products_qa_pass', 0) == 0:
        return {'constraint': 'SUPPLY', 'why': 'no product is Studio QA PASS and owner-approved, so nothing may be marketed',
                'fix': 'approve the verified products waiting in the Jobs tab', 'owner_role': 'sales_qa'}
    w = evidence.get('weekly_units') or []
    target = 125
    if not w or w[-1] < target:
        return {'constraint': 'DEMAND', 'why': f'last week {w[-1] if w else 0} paid units vs the week-1 target of {target}',
                'fix': 'more qualified buyers reaching verified listings (organic discovery + conversion)', 'owner_role': 'social_publisher'}
    return {'constraint': 'RETENTION', 'why': 'acquisition meets target; growth now depends on repeat purchases (AH-01)',
            'fix': 'next-step paths and bundles for existing buyers', 'owner_role': 'retention'}


def daily_plan(diag, neck):
    """Prioritized, measurable actions for the 10 roles. More content volume is added ONLY if the constraint is reach."""
    P = []
    add = lambda prio, role, action, metric, methods: P.append({'priority': prio, 'role': role, 'action': action,
                                                               'metric': metric, 'methods': methods})
    if neck['constraint'] == 'MEASUREMENT':
        add(1, 'revenue_tracker', 'Import the latest TpT sales report; set Week 1; record units, gross, fees, refunds, net',
            'real sales rows > 0', ['AH-18', 'JR-02'])
    if neck['constraint'] in ('MEASUREMENT', 'SUPPLY'):
        add(2, 'sales_qa', 'Owner reviews the QA PASS products waiting for approval (Jobs tab)', 'products QA PASS + owner approved', ['AH-22'])
    add(3, 'offer_pricing', 'Listing checklist on the 5 best verified products: title, previews, what is included, answer keys, bundle link',
        'checklist pass rate; listing conversion (when data exists)', ['AH-16', 'AH-06'])
    add(4, 'market_research', 'Record 5 search terms teachers already use for one verified course (free public pages)',
        'terms with visible demand', ['AH-11', 'AH-12'])
    add(5, 'script_storyboard', 'One proof-based Lil Dr. Byrd script from a verified product (credential in the first 3 s)',
        '3-second hold rate (when posted)', ['AH-08', 'AH-09'])
    add(6, 'video_producer', 'Generate the approved Lil Dr. Byrd commercial on Blotato (owner confirms credits) and run the Reviewer', 'videos passing review', ['AH-19'])
    add(7, 'social_publisher', 'Publish the approved commercial via Blotato (owner approval); judge each channel at its minimum sample', 'clicks to listing per post', ['AH-11', 'AH-14'])
    add(8, 'prospector', 'List 5 warm contacts (teachers/tutors the owner already knows) for one verified course', 'warm contacts listed', ['AH-12', 'AH-27'])
    add(9, 'sales_followup', 'Question-first drafts for those contacts; the owner decides and sends', 'reply rate', ['ZZ-02', 'GC-02'])
    add(10, 'retention', 'Ask satisfied buyers once whether a colleague might benefit (voluntary, unpaid, no contact collection)',
        'introductions per buyer asked', ['AH-28', 'AH-01'])
    P.sort(key=lambda x: x['priority'])
    return {'constraint': neck, 'actions': P, 'stop_rules': [
        'Do not add content volume, agents or API spend unless the measured constraint is reach (AH-31).',
        'Judge any change only at its minimum sample (AH-14); keep sowing until then (JR-03).',
        'No referral rewards, no paid ads, no new subscriptions, nothing sent or published without the owner.']}


def assess(evidence):
    d = diagnose(evidence)
    n = bottleneck(d, evidence)
    return {'date': dt.date.today().isoformat(), 'diagnosis': d, 'bottleneck': n, 'plan': daily_plan(d, n), 'matrix': matrix(),
            'official_sources': OFFICIAL}
