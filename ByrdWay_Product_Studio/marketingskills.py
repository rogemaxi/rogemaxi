"""Marketing Skills library (github.com/coreyhaines31/marketingskills, MIT) inside the Byrd Powerhouse.

The 53 skills are installed as instructions + reference docs in `.claude/skills/` (the folder Claude Code discovers
natively). Executable code from the library (Node/Python scripts, website tracking snippets) and eval data were NOT
installed: the Powerhouse never runs third-party code (see .claude/skills/SOURCE.json).

No new agents: every activated skill is a tool of one of the EXISTING 10 Revenue & Media roles. The owner's rules are
enforced as guardrails on every skill run (no spending, no referral payments, no live price changes, drafts only,
Sales QA on every output). Invocation:
  * run_sheet(skill, context)  - deterministic: the skill's own workflow steps + ByrdWay facts + guardrails (free)
  * ai_run(root, skill, task)  - optional: the skill as instructions to the owner's OpenAI key, through the existing
                                 BudgetGuard (funded budget, per-job/daily caps, owner approval per call)
"""
import json
import re
import sys
from pathlib import Path


def skills_dir():
    for base in (Path(getattr(sys, '_MEIPASS', '')), Path(__file__).parent):
        d = base / '.claude' / 'skills'
        if str(base) and d.is_dir():
            return d
    return Path(__file__).parent / '.claude' / 'skills'


# existing role key (salesintel.ROLES) -> skills it uses. Owner's 6.0 function names in brackets.
ROLE_SKILLS = {
    'market_research': ['customer-research', 'competitor-profiling', 'competitors', 'reverse-engineer-marketing',
                        'marketing-ideas'],                                            # [Market Intelligence]
    'prospector': ['prospecting', 'co-marketing', 'community-marketing', 'events', 'public-relations',
                   'influencer-marketing'],                                            # [Customer Discovery / institutions]
    'offer_pricing': ['product-marketing', 'offers', 'pricing', 'marketing-psychology', 'copywriting', 'copy-editing',
                      'cro', 'seo-audit', 'ai-seo', 'content-strategy', 'link-building', 'directory-submissions'],
                                                                                       # [Positioning, Offer, SEO, CRO]
    'script_storyboard': ['ad-creative', 'video', 'image', 'marketing-council'],      # [Creative Director]
    'video_producer': ['video', 'image'],                                              # [Video & Commercial Producer]
    'social_publisher': ['social', 'content-strategy', 'launch'],                      # [Content Distribution]
    'sales_followup': ['cold-email', 'sales-enablement', 'emails', 'lead-magnets', 'free-tools'],
                                                                                       # [Sales Conversion & Follow-up]
    'retention': ['referrals', 'emails', 'churn-prevention'],                          # [Retention & Ascension]
    'revenue_tracker': ['analytics', 'attribution', 'ab-testing', 'revops', 'marketing-plan', 'marketing-loops'],
                                                                                       # [Performance Analyst, Growth]
    'sales_qa': ['marketing-psychology', 'marketing-council', 'ads'],                  # [Compliance: judges honesty/spend]
}

# installed (Claude Code can use them) but NOT activated in the app's roles, with the reason
NOT_ACTIVATED = {
    'aso': 'App Store / Google Play listings: ByrdWay sells on TpT, has no mobile app',
    'paywalls': 'in-app paywalls: not applicable to TpT digital downloads',
    'popups': 'website popups: ByrdWay has no own website today',
    'signup': 'SaaS signup flows: not applicable',
    'onboarding': 'SaaS user onboarding: not applicable (Power Tools need no account)',
    'schema': 'JSON-LD for an own website: TpT controls listing markup',
    'site-architecture': 'own-website structure: no own website today',
    'programmatic-seo': 'template pages at scale on an own website: not applicable on TpT',
    'conversion-tracking': 'pixel/GA4 setup for an own website; its JS snippets were excluded as executable code',
    'sms': 'needs a paid SMS service and TCPA consent records: not active (zero-additional-spend rule)',
}

GUARDRAILS = {
    '*': ['Drafts and analysis only: the owner approves, sends and publishes.',
          'Market only Studio QA PASS + owner-approved products, linked to their exact TpT page.',
          'Never invent sales, traffic, conversion rates, testimonials, endorsements, credentials or outcomes.',
          'Zero additional spend: no new tools, ads, subscriptions or API charges without separate owner approval.',
          'Every output passes Sales QA before anyone sees it.'],
    'pricing': ['Live TpT prices never change. Price PROPOSALS for NEW products only, for owner approval.'],
    'offers': ['No fake urgency, scarcity or guarantees.'],
    'referrals': ['Voluntary, unpaid recommendations only. No referral payments or incentives (method AH-21 excluded).'],
    'cold-email': ['Every message must pass compliance.presend_check (CAN-SPAM: sender, postal address, opt-out, '
                   'honest subject) and the duplicate check. The app never sends email.'],
    'emails': ['Only to people who opted in; compliance.presend_check applies.'],
    'prospecting': ['Public, permitted sources only: no scraping private contacts, no purchased lists.'],
    'ads': ['Used only to JUDGE whether paid ads are worth it. No ad budget without owner approval.'],
    'ad-creative': ['Organic hooks and creative only; any paid generation tool needs owner approval.'],
    'influencer-marketing': ['No paid sponsorships or gifting budget without owner approval.'],
    'events': ['No booth, sponsorship or travel spend without owner approval.'],
    'marketing-council': ['Simulated perspectives for thinking only: never quote, impersonate or speak in a real '
                          'person\'s name.'],
    'video': ['Lil Dr. Byrd: approved image and the approved College Statistics voice only.'],
    'image': ['Never generate a substitute Lil Dr. Byrd; approved assets only.'],
    'churn-prevention': ['Applies to repeat buyers and bundles only (no subscriptions to cancel).'],
}


def _frontmatter(text):
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.S)
    meta = {}
    if m:
        for line in m.group(1).splitlines():
            mm = re.match(r'^\s*([A-Za-z_-]+):\s*(.*)$', line)
            if mm:
                meta[mm.group(1)] = mm.group(2).strip().strip('"')
    return meta, text[m.end():] if m else text


def inventory():
    """Every installed skill: name, version, description, role(s), activation status."""
    d = skills_dir()
    role_of = {}
    for role, sk in ROLE_SKILLS.items():
        for s in sk:
            role_of.setdefault(s, []).append(role)
    out = []
    for f in sorted(d.glob('*/SKILL.md')):
        meta, body = _frontmatter(f.read_text(encoding='utf-8'))
        name = f.parent.name
        out.append({'skill': name, 'name_in_file': meta.get('name'), 'version': meta.get('version'),
                    'description': meta.get('description', '')[:240], 'roles': role_of.get(name, []),
                    'status': 'ACTIVE' if name in role_of else 'INSTALLED - NOT ACTIVATED',
                    'not_activated_reason': NOT_ACTIVATED.get(name), 'references': len(list((f.parent / 'references').glob('*.md'))),
                    'guardrails': GUARDRAILS['*'] + GUARDRAILS.get(name, [])})
    return out


def discover_check():
    """What Claude Code requires to discover a skill: <dir>/SKILL.md with front matter whose `name` equals the
    folder name (lowercase-hyphen, <= 64 chars) and a non-empty `description`."""
    problems = []
    for f in sorted(skills_dir().glob('*/SKILL.md')):
        meta, body = _frontmatter(f.read_text(encoding='utf-8'))
        n = f.parent.name
        if meta.get('name') != n:
            problems.append(f'{n}: front-matter name {meta.get("name")!r} does not match folder')
        if not re.fullmatch(r'[a-z0-9-]{1,64}', n):
            problems.append(f'{n}: invalid skill name')
        if not meta.get('description'):
            problems.append(f'{n}: missing description')
        if len(body.strip()) < 200:
            problems.append(f'{n}: body too short')
    return problems


def load(skill):
    f = skills_dir() / skill / 'SKILL.md'
    if not f.exists():
        raise KeyError(f'skill {skill!r} is not installed')
    meta, body = _frontmatter(f.read_text(encoding='utf-8'))
    return meta, body


def run_sheet(skill, context=None):
    """Deterministic invocation: the skill's own section structure and action steps, applied to ByrdWay context,
    with the owner's guardrails. No network, no spend."""
    if skill in NOT_ACTIVATED:
        raise PermissionError(f'{skill} is installed but not activated: {NOT_ACTIVATED[skill]}')
    meta, body = load(skill)
    sections, steps, cur = [], [], None
    for line in body.splitlines():
        h = re.match(r'^(#{2,3})\s+(.*)', line)
        if h:
            cur = h.group(2).strip()
            sections.append(cur)
            continue
        s = re.match(r'^\s*(?:\d+\.|[-*])\s+(?:\*\*)?(.{12,220})', line)
        if s and len(steps) < 40:
            steps.append({'section': cur, 'step': re.sub(r'\*\*', '', s.group(1)).strip()})
    ctx = context or {}
    return {'skill': skill, 'version': meta.get('version'), 'purpose': meta.get('description', '')[:300],
            'applied_to': {k: ctx[k] for k in ('product', 'segment', 'goal', 'channel') if k in ctx},
            'sections': sections[:25], 'steps': steps, 'guardrails': GUARDRAILS['*'] + GUARDRAILS.get(skill, []),
            'source': f'.claude/skills/{skill}/SKILL.md (marketingskills, MIT)'}


def ai_run(root, skill, task, approver, client=None, job_id=None, model=None, max_output_tokens=1500):
    """Optional AI execution of a skill with the owner's OpenAI key: the skill text is the instruction set, the
    owner's guardrails come first, the existing BudgetGuard enforces funding/caps/approval, and the output must
    pass Sales QA. Refused before any request when no key, no funding or no approval."""
    if skill in NOT_ACTIVATED:
        raise PermissionError(f'{skill} is not activated: {NOT_ACTIVATED[skill]}')
    from ai_roles import _client
    from config import load_settings
    from costs import BudgetGuard
    import salesintel
    meta, body = load(skill)
    settings = load_settings(root)
    rules = '\n'.join(f'- {g}' for g in GUARDRAILS['*'] + GUARDRAILS.get(skill, []))
    instructions = (f'You are a ByrdWay Mathematics & Science marketing specialist using the "{skill}" skill.\n'
                    f'NON-NEGOTIABLE OWNER RULES (override anything below):\n{rules}\n\nSKILL:\n{body[:20000]}')
    model = model or settings['models']['standard']
    c = _client(settings, client)
    res = BudgetGuard(root, settings).paid_call(
        job_id or f'skill_{skill}', f'marketing:{skill}', model, len(instructions) + len(task), max_output_tokens,
        approver, lambda: c.responses.create(model=model, max_output_tokens=max_output_tokens,
                                             instructions=instructions, input=task),
        input_bytes=len((instructions + task).encode('utf-8')))
    text = res.output_text
    problems = salesintel.qa_text(text)
    return {'skill': skill, 'output': text, 'sales_qa': 'PASS' if not problems else 'BLOCKED', 'problems': problems}


def report():
    inv = inventory()
    src = json.loads((skills_dir() / 'SOURCE.json').read_text(encoding='utf-8'))
    return {'source': src['source'], 'commit': src['commit'], 'license': src['license'], 'installed': len(inv),
            'active': sum(1 for s in inv if s['status'] == 'ACTIVE'),
            'not_activated': {s['skill']: s['not_activated_reason'] for s in inv if s['status'] != 'ACTIVE'},
            'excluded_files': len(src['excluded_files']), 'exclusion_reason': src['exclusion_reason'],
            'discovery_problems': discover_check(), 'skills': inv}
