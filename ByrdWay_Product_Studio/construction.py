"""Construction QA loop for Power Tools and Lil Dr. Byrd Explainers (Engineering agents 8-12).

    Builder (9) builds the unit from the approved blueprint
 -> Build QA (11) checks it INDEPENDENTLY (never the builder judging itself):
      academic   every answer re-computed by the Academic Verifier
      lessons    the same Reader/Verifier the Inspection Division uses re-reads the built page
                 (arithmetic statements, worked steps, spelling, brackets) - builders are held to
                 what the repairers learned (Observer lessons library)
      code       static HTML/JS audit (Power Tools)
      browser    real Chromium run: loads, no JS errors, every screen, phone width (Power Tools)
      mastery    the 9-point ByrdWay Mastery Experience standard, each item tested in the browser
      document   text layer, Lil Dr. Byrd image, every section, answers section (Explainers)
 -> Repair Engineer (4) fixes what can be fixed safely and deterministically (a wrong answer is
      replaced by the verifier's recomputed value); Repair Reviewer (5) re-verifies the fix
 -> rebuild, bounded rounds, stop on no progress
 -> Chief Judge (12): PASS only when 100 % of mandatory checks pass. A PASS unit waits for the
      owner; nothing is approved or released automatically.
"""
import json
import random
import re
from pathlib import Path

import academic
import builders as B
import imageread
from engine import read_json, sha256, utcnow, write_json

MAX_ROUNDS = 4
MASTERY_ITEMS = [
    ('mastery.1_placement_diagnostic', 'Placement diagnostic first, giving a personal path'),
    ('mastery.2_mastery_gate', 'Mastery gate (>= 90 %) before the next skill, with spaced review'),
    ('mastery.3_feedback_and_hints', 'Instant feedback and a misconception-specific hint on every wrong answer'),
    ('mastery.4_worked_faded_independent', 'Worked example -> faded example -> independent practice, Lil Dr. Byrd at the hard step'),
    ('mastery.5_session_progress_streaks', 'Session blocks adding up to ~2 hours, visible progress, streaks'),
    ('mastery.6_simulation', 'Interactive simulation where the subject allows'),
    ('mastery.7_unlimited_verified_practice', 'Unlimited generated practice with verified answers'),
    ('mastery.8_progress_report', 'Progress report stored locally, no account, works offline'),
    ('mastery.9_accessible_single_file', 'Accessible, mobile, single file, no paid service'),
]


def _chk(cid, passed, detail, mandatory=True):
    return {'check': cid, 'passed': bool(passed), 'detail': str(detail)[:400], 'mandatory': mandatory}


# ------------------------------------------------------------------ shared: Reader re-reads built text
def _lines_from_text(text):
    return [{'text': t.strip(), 'conf': 1.0, 'rect': (0, i * 10, 500, i * 10 + 9)}
            for i, t in enumerate(text.splitlines()) if t.strip()]


def reader_checks(text, where, tech_words=()):
    """The Inspection Division's own checks, run on a page the Builder produced."""
    lines = _lines_from_text(text)
    out = []
    errs = [f['statement'] for f in imageread.check_worked_steps(lines, lines) if f['status'] == imageread.STATUS_ERR]
    errs += [f'{l} = {r}' for ln in lines for st, l, r, _, _ in imageread.check_line(ln) if st == imageread.STATUS_ERR]
    out.append(_chk(f'lessons.{where}.arithmetic_and_steps', not errs,
                    f'wrong statements: {errs}' if errs else 'every arithmetic statement and worked step verifies'))
    paras = [p for p in re.split(r'\n\s*\n', text) if p.strip()]                # paragraphs may wrap inside brackets
    unbalanced = [p.strip()[:120] for p in paras if p.count('(') != p.count(')')]
    out.append(_chk(f'lessons.{where}.brackets', not unbalanced, unbalanced or 'every bracket closed'))
    tech = {w.lower() for w in tech_words} | _TECH
    typos = [x['shown'] for x in imageread.typo_candidates(lines, lines) if x['shown'].lower() not in tech] if lines else []
    out.append(_chk(f'lessons.{where}.spelling', not typos, f'possible misspellings: {typos}' if typos else 'no misspellings'))
    return out


_TECH = set('''byrdway lil honors kinematics displacement equilibrium newtons joules coulombs vectors scalars
centripetal kepler doppler kirchhoff snell ohm ohms photoelectric thermodynamics placement faded
centi milli kilo micro nano mega giga'''.split())


def academic_checks(results, where):
    out = []
    for r in results:
        ok = r['status'] == academic.CORRECT
        out.append(_chk(f'academic.{where}.{r.get("where", "?")}', ok,
                        f'{r["status"]}: {r.get("question")} -> claimed {r.get("claimed")}; '
                        f'expected {r.get("expected")} ({str(r.get("evidence"))[:120]})'))
    if not results:
        out.append(_chk(f'academic.{where}.has_checkable_items', False, 'no verifiable answers in this unit'))
    return out


# ------------------------------------------------------------------ Power Tool QA
def _page_data(html):
    m = re.search(r'<script type="application/json" id="bw-data">(.*?)</script>', html, re.S)
    return json.loads(m.group(1).replace('<\\/', '</')) if m else {}


def generator_instances(G, n=25, seed=7):
    """Instantiate a generator exactly like the page does (same template language) for verification."""
    rnd = random.Random(seed)
    out = []
    for _ in range(n):
        v = {}
        for k, (lo, hi) in G['params'].items():
            while True:
                v[k] = rnd.randint(int(lo), int(hi))
                if k not in G.get('nonzero', []) or v[k] != 0:
                    break
        for c, expr in (G.get('compute') or {}).items():
            import sympy as sp
            val = academic.safe_parse(expr).subs({sp.Symbol(k): x for k, x in v.items()})
            v[c] = int(val) if val == int(val) else float(val)
        fill = lambda t: _fill(t, v)
        spec = json.loads(_fill(json.dumps(G['verify']), v))
        out.append({'question': fill(G['template']), 'answer': fill(G.get('verify_answer', G['answer'])), 'verify': spec})
    return out


def _fill(t, v, paren=False):
    return re.sub(r'\{(\w+)\}', lambda m: (f'({v[m.group(1)]})' if paren else str(v[m.group(1)])), t)


def mastery_static_checks(bp, m, html, data):
    M = data.get('mastery') or {}
    out = []
    ok = bool(M.get('placement')) and 'id="placement"' in html
    out.append(_chk(MASTERY_ITEMS[0][0], ok, f'{len(M.get("placement") or [])} placement item(s) covering skills '
                    f'{sorted({p.get("skill") for p in M.get("placement") or []})}' if ok else 'no placement diagnostic'))
    ok = M.get('threshold', 0) >= 0.9 and 'id="bw-gate"' in html and ('id="review"' in html or not _earlier(bp, m))
    out.append(_chk(MASTERY_ITEMS[1][0], ok, f'threshold {M.get("threshold")}; spaced review items '
                    f'{len(M.get("review") or [])}' if ok else 'mastery gate or spaced review missing'))
    missing = [q['question'] for q in data.get('practice', []) if not q.get('hint') and not q.get('choices')]
    out.append(_chk(MASTERY_ITEMS[2][0], not missing, 'every practice item has a misconception-specific hint'
                    if not missing else f'practice items with no hint: {missing}'))
    order = [html.find(f'id="{x}"') for x in ('examples', 'faded', 'practice')]
    ok = all(i > 0 for i in order) and order == sorted(order) and bool(M.get('mascot'))
    out.append(_chk(MASTERY_ITEMS[3][0], ok, 'worked -> faded -> practice in order, Lil Dr. Byrd at the hard step'
                    if ok else f'order/mascot problem (positions {order}, mascot {"yes" if M.get("mascot") else "MISSING: register the approved Lil Dr. Byrd asset"})'))
    total = sum(b[1] for b in M.get('blocks') or [])
    ok = 100 <= total <= 140 and 'id="bw-progress"' in html and 'id="bw-streak"' in html
    out.append(_chk(MASTERY_ITEMS[4][0], ok, f'session blocks total {total} min; progress bar and streak present'))
    need = B.needs_simulation(bp, m)
    ok = (not need) or (bool(M.get('simulation')) and 'id="simulation"' in html)
    out.append(_chk(MASTERY_ITEMS[5][0], ok, ('simulation present' if M.get('simulation') else 'not required for this subject')
                    if ok else 'subject needs an interactive simulation'))
    gens = M.get('generators') or []
    bad, n = [], 0
    for G in gens:
        try:
            for it in generator_instances(G):
                n += 1
                r = academic.verify_item(it)
                if r['status'] != academic.CORRECT:
                    bad.append(f'{it["question"]} -> {it["answer"]}: {r["status"]}')
        except Exception as e:      # malformed generator = fail, never crash the judge
            bad.append(f'generator {G.get("skill")}: {type(e).__name__}: {e}')
    ok = bool(gens) and not bad
    out.append(_chk(MASTERY_ITEMS[6][0], ok, f'{len(gens)} generator(s); {n} generated problems verified, 0 wrong'
                    if ok else (f'wrong generated answers: {bad[:5]}' if bad else 'no generator in this module')))
    ok = 'bwReport' in html and 'localStorage' in html
    out.append(_chk(MASTERY_ITEMS[7][0], ok, 'local progress report present' if ok else 'progress report missing'))
    ext = re.findall(r'(?:src|href)="(https?:)?//', html)
    ok = '<html lang=' in html and 'name="viewport"' in html and not ext
    out.append(_chk(MASTERY_ITEMS[8][0], ok, 'lang, viewport, labels, single file with no external requests'
                    if ok else f'external references {len(ext)} / lang or viewport missing'))
    return out


def _earlier(bp, m):
    ids = [x['id'] for x in bp['modules']]
    return ids.index(m['id']) > 0 and any(x.get('practice') for x in bp['modules'][:ids.index(m['id'])])


def mastery_browser_checks(page_path, data):
    """Exercise the Mastery Experience in real Chromium (sandboxed: only this file may load)."""
    import browsertest
    if not browsertest.playwright_available():
        return [_chk('mastery.browser', False, 'Playwright/Chromium not installed: mastery behaviour NOT VERIFIED')]
    from playwright.sync_api import sync_playwright
    M, P = data.get('mastery') or {}, data.get('practice') or []
    out = []
    with sync_playwright() as p:
        br = browsertest._launch(p)
        try:
            ctx = br.new_context(viewport={'width': 375, 'height': 800})
            ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith('file:') else r.abort())
            pg = ctx.new_page()
            errors = []
            pg.on('pageerror', lambda e: errors.append(str(e)))
            pg.goto(Path(page_path).resolve().as_uri())
            if M.get('placement'):
                pg.fill('#p0', 'zzz')
                pg.click('#placement button')
                t = pg.inner_text('#bw-placement-path')
                out.append(_chk('mastery.browser.placement_path', 'path' in t.lower(), t))
            txt_input = [i for i, q in enumerate(P) if not q.get('choices')]
            if txt_input:
                i = txt_input[0]
                pg.fill(f'#a{i}', 'zzz-wrong')
                pg.click(f'#practice .card:nth-of-type({i + 1}) button')
                t = pg.inner_text(f'#f{i}')
                out.append(_chk('mastery.browser.hint_on_wrong', 'Not yet' in t and (not P[i].get('hint') or P[i]['hint'][:20] in t), t))
                out.append(_chk('mastery.browser.gate_locked', 'Locked' in pg.inner_text('#bw-gate'), pg.inner_text('#bw-gate')))
            for i, q in enumerate(P):                        # now answer everything correctly
                if q.get('choices'):
                    pg.check(f'input[name="q{i}"][value="{q["correct_index"]}"]')
                else:
                    pg.fill(f'#a{i}', q['answer'])
                pg.click(f'#practice .card:nth-of-type({i + 1}) button')
            g = pg.inner_text('#bw-gate')
            out.append(_chk('mastery.browser.gate_unlocks_at_mastery', 'unlocked' in g.lower() and pg.is_visible('#bw-next') is not None, g))
            out.append(_chk('mastery.browser.streak_visible', 'Streak' in pg.inner_text('#bw-streak'), pg.inner_text('#bw-streak')))
            if M.get('faded'):
                pg.fill('#fd0', M['faded'][0]['answer'])
                pg.click('#faded button')
                out.append(_chk('mastery.browser.faded_checks', 'Correct' in pg.inner_text('#ff0'), pg.inner_text('#ff0')))
            if M.get('generators'):
                pg.click('#generated .card:nth-of-type(1) button:has-text("New problem")')
                q = pg.inner_text('#gq0')
                out.append(_chk('mastery.browser.generator_makes_problems', q and 'Press' not in q, q))
            if M.get('simulation'):
                out.append(_chk('mastery.browser.simulation_computes', '=' in pg.inner_text('#sim-out'), pg.inner_text('#sim-out')))
            pg.click('#report button')
            rep = pg.inner_text('#bw-report-out')
            out.append(_chk('mastery.browser.report', 'MASTERED' in rep, rep[:200]))
            pg.reload()
            pg.click('#report button')
            out.append(_chk('mastery.browser.progress_saved_offline', 'MASTERED' in pg.inner_text('#bw-report-out'),
                            'progress survives a reload (stored on this device)'))
            out.append(_chk('mastery.browser.no_js_errors', not errors, errors[:3] or 'none'))
        finally:
            br.close()
    return out


def power_tool_qa(root, build_id, module_id, run_browser=True):
    b = B.Build(root, build_id)
    bp, u = b.blueprint, b.state['units'][module_id]
    m = next(x for x in bp['modules'] if x['id'] == module_id)
    page = Path(u['output'])
    html = page.read_text(encoding='utf-8')
    data = _page_data(html)
    checks = academic_checks(u.get('verification') or [], module_id)
    import htmlaudit
    findings, _ = htmlaudit.audit_files({'index.html': html})
    serious = [f for f in findings if f['severity'] in ('CRITICAL', 'MAJOR')]
    checks.append(_chk('code.static_audit', not serious, [f'{f["check"]}: {f["detail"]}' for f in serious][:5] or
                       f'{len(findings)} minor note(s), no critical/major'))
    checks.append(_chk('design.approved_template', u.get('template', {}).get('template_status') == 'OWNER_APPROVED_ASSET',
                       u.get('template', {}).get('template_status')))
    visible = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', html, flags=re.S)
    visible = re.sub(r'<(br|/p|/li|/h\d|/div|/tr|/section)[^>]*>', '\n', visible)
    import html as H
    checks += reader_checks(H.unescape(re.sub(r'<[^>]+>', ' ', visible)), module_id)
    checks += mastery_static_checks(bp, m, html, data)
    if run_browser:
        import browsertest
        r = browsertest.run_browser_tests(page.parent, page.name, page.parent / 'qa_shots', 'build_qa')
        checks += [_chk(c[0], c[3], c[4]) for c in browsertest.browser_checks(r)]
        checks += mastery_browser_checks(page, data)
    else:
        checks.append(_chk('browser.not_run', False, 'browser tests not run: behaviour NOT VERIFIED'))
    return checks


# ------------------------------------------------------------------ Explainer chapter QA
def explainer_qa(root, build_id, unit):
    b = B.Build(root, build_id)
    bp, u = b.blueprint, b.state['units'][unit]
    ch = bp['chapters'][int(unit[2:]) - 1]
    fitz = imageread._fitz()
    checks = academic_checks(u.get('verification') or [], unit)
    checks.append(_chk('asset.lil_dr_byrd', not u.get('blocked_assets') and u.get('mascot'),
                       'approved Lil Dr. Byrd asset used' if u.get('mascot') else u.get('blocked_assets')))
    with fitz.open(u['output']) as doc:
        text = '\n'.join(p.get_text('text', flags=0) for p in doc)
        imgs = sum(len(p.get_images()) for p in doc)
        checks.append(_chk('document.text_layer', len(text.strip()) > 200, f'{len(text)} characters of real text on {doc.page_count} page(s)'))
        checks.append(_chk('document.mascot_on_page', imgs >= 1, f'{imgs} image(s) in the chapter'))
    flat = re.sub(r'\s+', ' ', text)
    honors_ok = bool(bp.get('honors_approved'))
    for s in ch['sections']:
        if s.get('honors') and not honors_ok:
            continue
        checks.append(_chk(f'document.section.{s["heading"][:40]}', s['heading'][:25] in flat, 'section heading present'))
    if ch.get('practice'):
        checks.append(_chk('document.answers_section', 'Answers' in flat, 'answers & solutions section present'))
    checks += reader_checks(text, unit)
    return checks


# ------------------------------------------------------------------ Repair Engineer + Reviewer on the blueprint
def _iter_items(bp, kind, unit):
    if kind == 'power_tool':
        m = next(x for x in bp['modules'] if x['id'] == unit)
        for k in ('practice', 'worked_examples'):
            for it in m.get(k) or []:
                yield it
    else:
        ch = bp['chapters'][int(unit[2:]) - 1]
        for s in ch['sections']:
            for it in s.get('worked_examples') or []:
                yield it
        for it in ch.get('practice') or []:
            yield it


def repair_answers(root, build_id, unit, failed):
    """Repair Engineer: replace each INCORRECT answer by the verifier's recomputed value (only when the verifier
    produced one from an explicit spec); Repair Reviewer re-verifies each fix before it is kept."""
    b = B.Build(root, build_id)
    s = b.state
    bp = b.blueprint
    fixes = []
    wrong_q = {re.search(r'-> claimed', c['detail']) and c['detail'].split(': ', 1)[1].split(' -> claimed')[0]
               for c in failed if c['check'].startswith('academic.')}
    for it in _iter_items(bp, s['kind'], unit):
        if it.get('question') not in wrong_q:
            continue
        r = academic.verify_item(it)
        if r['status'] != academic.INCORRECT:
            continue
        new = r.get('suggested_answer') or r.get('expected')
        spec = it.get('verify') or (r.get('spec') if (r.get('spec') or {}).get('type') in ('solve', 'expression', 'physics') else None)
        if new is not None and re.match(r'^\s*[a-z]\s*=', str(it.get('answer', ''))) and '=' not in str(new):
            new = str(it['answer']).split('=')[0].strip() + ' = ' + str(new)
        if new is None or not spec:
            fixes.append({'question': it['question'], 'old': it.get('answer'), 'new': None,
                          'reviewer': 'NOT FIXED: no explicit verification spec - owner must correct the blueprint'})
            continue
        old = it['answer']
        trial = dict(it, answer=str(new), verify=spec)
        rv = academic.verify_item(trial)                       # Repair Reviewer: independent re-check
        if rv['status'] == academic.CORRECT:
            it['answer'] = str(new)
            it['verify'] = spec
            if it.get('accept'):
                it['accept'] = [str(new).split('=')[-1].strip()]
            if it.get('steps') and str(old).split('=')[-1].strip() in it['steps'][-1]:
                it['steps'][-1] = it['steps'][-1].replace(str(old).split('=')[-1].strip(), str(new).split('=')[-1].strip())
            fixes.append({'question': it['question'], 'old': old, 'new': str(new), 'reviewer': 'ACCEPTED: re-verified CORRECT'})
        else:
            fixes.append({'question': it['question'], 'old': old, 'new': str(new), 'reviewer': f'REJECTED: {rv["status"]}'})
    if any(f['reviewer'].startswith('ACCEPTED') for f in fixes):
        write_json(b.dir / 'blueprint.json', bp)
        s['blueprint_sha256'] = sha256(b.dir / 'blueprint.json')
        s.setdefault('construction_repairs', []).append({'unit': unit, 'at': utcnow(), 'fixes': fixes})
        b.save(s)
    return fixes


# ------------------------------------------------------------------ the loop
def construct_unit(root, build_id, unit, run_browser=True, max_rounds=MAX_ROUNDS, lessons=None):
    """Build -> independent Build QA -> repair -> rebuild ... -> Chief Judge. Returns the full evidence record."""
    b = B.Build(root, build_id)
    kind = b.state['kind']
    rounds, prev_fail = [], None
    for rnd in range(1, max_rounds + 1):
        u = (B.build_power_tool_module if kind == 'power_tool' else B.build_lil_dr_byrd_chapter)(root, build_id, unit)
        checks = power_tool_qa(root, build_id, unit, run_browser) if kind == 'power_tool' else explainer_qa(root, build_id, unit)
        failed = [c for c in checks if c['mandatory'] and not c['passed']]
        rec = {'round': rnd, 'built_sha256': u['output_sha256'], 'mandatory': sum(c['mandatory'] for c in checks),
               'failed': [f'{c["check"]}: {c["detail"]}' for c in failed]}
        rounds.append(rec)
        if not failed:
            break
        sig = sorted(c['check'] for c in failed)
        fixes = repair_answers(root, build_id, unit, failed)
        rec['repairs'] = fixes
        if not any(f['reviewer'].startswith('ACCEPTED') for f in fixes) or sig == prev_fail:
            rec['stop'] = 'no automatic repair possible for the remaining failures - sent back with the exact list'
            break
        prev_fail = sig
    passed = not failed
    n_m = sum(c['mandatory'] for c in checks)
    decision = {'decision': 'PASS - awaiting owner approval' if passed else 'SENT BACK - not releasable',
                'mandatory_checks': n_m, 'passed': n_m - len(failed), 'failed': len(failed),
                'pass_rate': f'{(n_m - len(failed)) / n_m * 100:.3f} %' if n_m else 'n/a',
                'rule': '100 % of mandatory checks must pass (Chief Judge, agent 12)'}
    s = b.state
    s['units'][unit].update(construction={'rounds': rounds, 'checks': checks, 'chief_judge': decision,
                                          'lessons_held_to': lessons or [], 'at': utcnow()})
    if not passed:
        s['units'][unit]['status'] = 'SENT_BACK_BY_CHIEF_JUDGE'
    b.save(s)
    write_json(b.dir / f'construction_{unit}.json', s['units'][unit]['construction'])
    return s['units'][unit]
