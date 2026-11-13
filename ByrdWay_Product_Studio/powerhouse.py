"""BYRD POWERHOUSE - the agent organization of the ByrdWay Product Engineering Studio.

One application, two divisions. Each agent is a named role backed by real code (no empty wrappers); its
status is computed from what the code can actually do, per product family:
  WORKING  - implemented and proven by tests (and on real products where noted)
  PARTIAL  - implemented with documented limits
  MISSING  - not built yet (shown, never hidden)

The Observer (agent 7) closes the learning loop: every defect the Inspection Division finds and every repair
that passes QA becomes a LESSON in the workspace (lessons/lessons.json). Builders must pass the check that
guards each lesson before Build QA; build reports list the lessons they were held to.
"""
import json
import time
from collections import OrderedDict
from pathlib import Path

FAMILIES = ('Power Tool', 'Lil Dr. Byrd Explainer', 'Concept Tiles')

ENGINEERING = [
    # id, name, group, job, code, status per family (PT, Explainer, CT)
    (1, 'Reader', 'A. Detect', 'Reads every screen and page (code, browser, text layer, OCR on picture pages)',
     'htmlaudit, browsertest, pdftools, imageread.review_pdf', ('WORKING', 'WORKING', 'WORKING')),
    (2, 'Answer Verifier', 'A. Detect', 'Recomputes every answer, worked step and solving step independently',
     'academic + verifier_algebra (exact Algebra 1 forms), imageread.check_worked_steps / check_relation_chains',
     ('WORKING', 'WORKING', 'WORKING')),
    (3, 'Diagnostician', 'A. Detect', 'Turns findings into a defect register with location, evidence, proposed fix',
     'orchestrator.diagnose', ('WORKING', 'WORKING', 'WORKING')),
    (4, 'Repair Engineer', 'B. Repair', 'Smallest safe fix on a protected copy',
     'zipproject patches, pdftools region fix, imagerepair.apply_patch', ('WORKING', 'PARTIAL', 'PARTIAL')),
    (5, 'Repair Reviewer', 'B. Repair', 'Independently re-reads and re-verifies every fix; rejects and sends back',
     'imagerepair.review_patch, orchestrator regression rollback', ('WORKING', 'PARTIAL', 'PARTIAL')),
    (6, 'Release QA', 'C. QA Loop', 'Fresh re-test of the whole copy; failures go back to repair (bounded loop)',
     'orchestrator.ReleaseQAAgent + QA send-back', ('WORKING', 'WORKING', 'WORKING')),
    (7, 'Observer', 'D. Learn', 'Turns every confirmed defect and fix into a lesson the builders must obey',
     'powerhouse.record_lessons', ('WORKING', 'WORKING', 'WORKING')),
    (8, 'Curriculum Architect', 'E. Build', 'Turns an approved table of contents into a unit-by-unit build plan',
     'concepttiles.toc_from_blueprint_md, builders blueprints + mastery_data', ('WORKING', 'WORKING', 'WORKING')),
    (9, 'Builder', 'E. Build', 'Writes each unit from the plan in the owner\'s product design',
     'builders.build_power_tool_module / build_lil_dr_byrd_chapter, byrdway_tiles.build_product (approved ByrdWay format)',
     ('WORKING', 'WORKING', 'WORKING')),
    (10, 'Assembler', 'E. Build', 'Assembles all approved units into one complete product package',
     'builders.assemble, concepttiles.assemble_product + qa_product', ('WORKING', 'WORKING', 'WORKING')),
    (11, 'Build QA', 'F. Build QA', 'Independent checks of every built unit, incl. the Inspection checks',
     'construction.power_tool_qa / explainer_qa (incl. 9-point Mastery standard in Chromium), byrdway_tiles.conformance',
     ('WORKING', 'WORKING', 'WORKING')),
    (12, 'Chief Judge', 'F. Build QA', 'Final gate: 100 % of mandatory checks pass or the unit goes back',
     'construction.construct_unit (repair + rebuild loop), concepttiles.build_unit', ('WORKING', 'WORKING', 'WORKING')),
]

REVENUE_STATUS = {   # honest status of each Revenue & Media role inside the app
    'market_research': ('PARTIAL', 'library methods + free research notes; web research is done outside the app'),
    'offer_pricing': ('WORKING', 'salesintel.offer_proposals / value_score / van_westendorp - PROPOSALS only'),
    'prospector': ('WORKING', 'salesintel.rank_prospects on the owner\'s local list - no paid lookups'),
    'script_storyboard': ('WORKING', 'salesintel.media_package from VERIFIED products'),
    'video_producer': ('PARTIAL', 'BUILT; live Blotato account + template schema verified 2026-11-13; first paid generation not yet run - videoplatform: 30-45 s Lil Dr. Byrd brief -> Blotato AI video (API, owner-confirmed credits) '
                                  'or Google Flow / Adobe Firefly shot list (manual render) -> Commercial Reviewer'),
    'social_publisher': ('PARTIAL', 'BUILT; live Blotato account verified 2026-11-13 (only YouTube connected so far); no post published yet - videoplatform.publish via Blotato to Facebook / Instagram / TikTok / YouTube after '
                                    'Reviewer PASS + explicit owner approval (never automatic)'),
    'sales_followup': ('WORKING', 'salesintel.followup_drafts - drafts only, the owner sends'),
    'retention': ('WORKING', 'salesintel.retention_paths'),
    'revenue_tracker': ('WORKING', 'salesintel.dashboard / import_sales_csv - real sales only, TEST rows excluded'),
    'sales_qa': ('WORKING', 'salesintel.sales_qa + library_qa + experiments (measured, minimum sample)'),
}


def _revenue():
    import salesintel
    return [(n, j, REVENUE_STATUS[k][1], REVENUE_STATUS[k][0], m) for k, n, j, m in salesintel.ROLES]



def organization():
    """The whole Powerhouse as data (for the app screen and the docs)."""
    groups = OrderedDict()
    for aid, name, group, job, code, st in ENGINEERING:
        groups.setdefault(group, []).append({'id': aid, 'name': name, 'job': job, 'code': code,
                                             'status': dict(zip(FAMILIES, st))})
    return {'engineering': groups,
            'revenue': [{'name': n, 'job': j, 'where': w, 'status': s, 'methods': m} for n, j, w, s, m in _revenue()],
            'quality_target': '99.997 % reliability, measured through evidence; 100 % of mandatory release checks must pass',
            'sales_targets': 'Week 1: 125 paid units; then +10 % (minimum) to +17 % (stretch) every week toward 1,000+ paid units per week '
                             '(week 23 on the minimum path, week 15 on the stretch path)'}


# ------------------------------------------------------------------ Observer: lessons library
GUARD = {                          # which mandatory check enforces a lesson in construction / repair
    'image.math_error': 'worked steps, arithmetic and solving steps re-verified on every built page',
    'image.typo': 'spelling check on every built page',
    'academic': 'every answer recomputed independently (with units)',
    'answer_key': 'every answer recomputed independently (with units)',
    'html': 'browser and code checks on every built Power Tool screen',
    'js': 'browser and code checks on every built Power Tool screen',
    'pdf': 'structure checks on every built PDF',
}


def _lessons_path(root):
    return Path(root) / 'lessons' / 'lessons.json'


def load_lessons(root):
    p = _lessons_path(root)
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'lessons': {}, 'updated': None}


def _guard_for(check):
    for k, v in GUARD.items():
        if str(check).startswith(k):
            return v
    return 'Release QA re-test'


def record_lessons(root, job):
    """Observer: learn from one finished job (detected defects, confirmed findings, verified repairs)."""
    lib = load_lessons(root)
    L = lib['lessons']
    product = job.get('product_type') or 'unknown'
    seen = []
    items = [(c.get('check'), c.get('detail'), c.get('state')) for c in job.get('corrections') or []]
    items += [(f.get('check'), f.get('detail'), 'CONFIRMED_BY_OWNER' if f.get('decision') == 'confirmed' else 'DETECTED')
              for f in (job.get('qa') or {}).get('image_findings') or []]
    for r in job.get('repair_reviews') or []:
        if isinstance(r.get('accepted'), dict):
            items.append(('repair.image_patch', f'{r.get("old")} -> {r.get("new")}', 'REPAIRED_AND_REVIEWED'))
    for check, detail, state in items:
        if not check:
            continue
        key = str(check).split(':')[0]
        les = L.setdefault(key, {'check': key, 'guarded_by': _guard_for(key), 'count': 0, 'products': [],
                                 'examples': [], 'first_seen': time.strftime('%Y-%m-%d'), 'states': {}})
        les['count'] += 1
        les['last_seen'] = time.strftime('%Y-%m-%d')
        if product not in les['products']:
            les['products'].append(product)
        les['states'][state] = les['states'].get(state, 0) + 1
        if len(les['examples']) < 5 and detail:
            les['examples'].append(str(detail)[:160])
        seen.append(key)
    lib['updated'] = time.strftime('%Y-%m-%d %H:%M:%S')
    p = _lessons_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(lib, indent=2), encoding='utf-8')
    return sorted(set(seen))


def lessons_for_build(root):
    """The lessons every builder is held to (each with the mandatory check that enforces it)."""
    return [{'lesson': k, 'guarded_by': v['guarded_by'], 'times_seen': v['count']}
            for k, v in sorted(load_lessons(root)['lessons'].items(), key=lambda kv: -kv[1]['count'])]


# ------------------------------------------------------------------ which agent did what in a job
def job_timeline(job):
    """Map a repair job to the agents that acted, in order (for the Powerhouse screen)."""
    steps = []
    base = job.get('baseline') or {}
    steps.append(('Reader + Answer Verifier', f'read the product; {base.get("findings", base.get("n_findings", "?"))} findings'
                  if isinstance(base, dict) else 'read the product'))
    steps.append(('Diagnostician', f'{len(job.get("corrections") or [])} defects registered'))
    applied = sum(len(i.get('applied', [])) for i in job.get('iterations', []))
    rejected = sum(len(i.get('rejected', [])) for i in job.get('iterations', []))
    steps.append(('Repair Engineer', f'{applied} fixes applied on a protected copy, {rejected} rejected'))
    rv = job.get('repair_reviews') or []
    if rv:
        steps.append(('Repair Reviewer', f'{sum(1 for r in rv if isinstance(r.get("accepted"), dict))} accepted, '
                                         f'{sum(1 for r in rv if r.get("accepted") is False)} sent back / blocked'))
    qa = job.get('qa') or {}
    steps.append(('Release QA', f'decision {qa.get("decision")}; '
                                f'{len(job.get("qa_sendbacks") or [])} send-back round(s)'))
    steps.append(('Observer', 'lessons recorded for the builders'))
    return steps
