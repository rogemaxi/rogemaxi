"""Owner-readable HTML reports (opens in any browser, works offline).

jobs/<job>/report.html          - repair job: next step, corrections with lifecycle state,
                                  before/after screenshots and PDF pages, QA checks, exact changes
reports/<diag>/diagnosis.html   - read-only diagnosis: what is wrong and what would be changed
"""
import html, os
from pathlib import Path
from version import __version__, APP_NAME

E = html.escape
CSS = """
body{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f6f8fc;color:#14213d}
main{max-width:1150px;margin:auto;padding:18px}h1{font-size:1.5rem;margin:.2em 0}
.next{padding:14px 16px;border-radius:10px;font-size:1.1rem;font-weight:600;margin:12px 0}
.ok{background:#e6f4ea;border:1px solid #1a7f37}.bad{background:#fde8e8;border:1px solid #cf222e}
.warn{background:#fff8e1;border:1px solid #bf8700}
table{border-collapse:collapse;width:100%;background:#fff;margin:8px 0 18px}
th,td{border:1px solid #d0d7de;padding:6px 8px;text-align:left;vertical-align:top;font-size:.92rem}
th{background:#eef2f8}.pill{display:inline-block;padding:2px 8px;border-radius:10px;font-size:.8rem;font-weight:600}
.s-VERIFIED,.s-VERIFIED_AWAITING_OWNER_APPROVAL,.s-VERIFIED_OWNER_APPROVED,.s-PASS{background:#d1f0d9}
.s-NOT_AUTO_FIXABLE,.s-APPLIED_BUT_STILL_FAILING,.s-REVERTED_REGRESSION,.s-DETECTED,.s-FAIL{background:#fbd5d5}
.s-SUSPECTED,.s-PROPOSED_NOT_APPLIED,.s-NOT-RUN,.s-RESOLVED_BY_RELATED_FIX{background:#fdf0c4}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}.pair figure{margin:0;background:#fff;border:1px solid #d0d7de;padding:6px}
.pair img{width:100%;height:auto}pre{background:#fff;border:1px solid #d0d7de;padding:10px;overflow:auto;font-size:.82rem}
.add{color:#116611}.del{color:#aa1111}small{color:#555}
@media(max-width:700px){.pair{grid-template-columns:1fr}}
"""


def _rel(path, base):
    try:
        return Path(os.path.relpath(path, base)).as_posix()
    except ValueError:
        return Path(path).as_uri()


def _page(title, body):
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width, initial-scale=1"><title>{E(title)}</title><style>{CSS}</style></head>'
            f'<body><main>{body}<hr><small>{E(APP_NAME)} v{E(__version__)}</small></main></body></html>')


def _pair(title, before, after, base):
    if not (before and after and Path(before).exists() and Path(after).exists()):
        return ''
    return (f'<h3>{E(title)}</h3><div class="pair"><figure><figcaption>BEFORE (original)</figcaption>'
            f'<img src="{E(_rel(before, base))}" alt="before"></figure><figure><figcaption>AFTER (candidate)'
            f'</figcaption><img src="{E(_rel(after, base))}" alt="after"></figure></div>')


_VERDICT = {'VERIFIED_CORRECT': ('Correct', 's-VERIFIED'), 'SUSPECTED_ERROR': ('Possible error', 's-FAIL'),
            'LIKELY_OCR_MISREAD': ('Unclear reading - correct if read as shown', 's-SUSPECTED'),
            'NOT_CHECKABLE': ('Could not check', 's-NOT-RUN'), 'SUSPECTED_TYPO': ('Possible spelling error', 's-FAIL')}


def page_by_page(image_review):
    """Full detail for image-only pages: per-page coverage, every statement read with its verdict and
    the reason when it could not be checked, and the complete text the reader saw on the page."""
    b = []
    for rel, rv in (image_review or {}).items():
        pages, items = rv.get('pages') or {}, rv.get('items') or []
        tot = lambda k: sum(int(v.get(k) or 0) for v in pages.values())
        b.append(f'<h2>Page-by-page reading: {E(rel)}</h2><p>{len(pages)} page(s) read by {E(str(rv.get("engine")))} '
                 f'- {tot("lines_read")} text lines, {tot("math_lines")} lines containing math. '
                 f'{tot("verified")} math statements and worked steps verified correct, {tot("errors")} possible '
                 f'error(s), {tot("not_checkable")} could not be checked (reason given), {tot("typos")} possible '
                 f'spelling error(s).</p><table><tr><th>Page</th><th>Lines read</th><th>Math lines</th>'
                 f'<th>Checked</th><th>Correct</th><th>Possible errors</th><th>Could not check</th><th>Spelling</th>'
                 f'<th>Page status</th></tr>')
        for pno in sorted(pages, key=lambda k: int(k)):
            v = pages[pno]
            b.append(f'<tr><td>{pno}</td><td>{v.get("lines_read", 0)}</td><td>{v.get("math_lines", "")}</td>'
                     f'<td>{v.get("statements", 0)}</td><td>{v.get("verified", 0)}</td><td>{v.get("errors", "")}</td>'
                     f'<td>{v.get("not_checkable", "")}</td><td>{v.get("typos", "")}</td>'
                     f'<td>{E(str(v.get("status", "")))}</td></tr>')
        unv = [k for k, v in pages.items() if 'UNVERIFIED' in str(v.get('status', ''))]
        if unv:
            b.append(f'<p class="next warn">UNVERIFIED pages (math present but not machine-checked): '
                     f'{E(", ".join(sorted(unv, key=int)))} - your visual check is required.</p>')
        b.append('</table><p><small>Lines with math that are not listed below are definitions, single values, '
                 'formulas without a worked step, or text the reader could not separate from the artwork - your '
                 'page confirmation covers them.</small></p>')
        for pno in sorted(pages, key=lambda k: int(k)):
            mine = [i for i in items if str(i.get('page')) == str(pno)]
            b.append(f'<details><summary><b>Page {pno}</b>: {len(mine)} item(s) checked</summary>')
            if mine:
                b.append('<table><tr><th>What was read</th><th>Type</th><th>Verdict</th><th>Detail</th></tr>')
                for i in mine:
                    lab, cls = _VERDICT.get(i['status'], (i['status'], ''))
                    det = i.get('reason') or ''
                    if i['status'] in ('SUSPECTED_ERROR', 'SUSPECTED_TYPO') and i.get('expected'):
                        det = f'expected: {i["expected"]}'
                    if i.get('alternative_reading'):
                        det = f'read as {i["alternative_reading"]}'
                    b.append(f'<tr><td>{E(str(i.get("statement")))}</td><td>{E(str(i.get("kind")))}</td>'
                             f'<td><span class="pill {cls}">{E(lab)}</span></td><td>{E(str(det))}</td></tr>')
                b.append('</table>')
            tr = (pages[pno] or {}).get('transcript') or []
            if tr:
                b.append(f'<p><small>Full text read on page {pno} ({len(tr)} lines):</small></p><pre>' +
                         E('\n'.join(tr)) + '</pre>')
            b.append('</details>')
    return ''.join(b)


def _repairs_section(root, job, jd):
    """Corrections made on the protected copy: before/after picture of every corrected spot + Reviewer checks."""
    rv = job.get('repair_reviews') or []
    if not rv:
        return ''
    out = ['<h2>Corrections made on a protected copy (Repair Engineer → Repair Reviewer)</h2>'
           '<p>Each correction is drawn over the page picture (RECONSTRUCTED REGION, Helvetica: the original font '
           'cannot be reproduced without the editable source). Your original file is unchanged. Look at every '
           '"after" picture before approving.</p><table><tr><th>Item</th><th>Before</th><th>After</th>'
           '<th>Repair Reviewer</th></tr>']
    try:
        import imageread
        from engine import original_file
        fitz = imageread._fitz()
        orig = original_file(root, job['product_id'])[0]
        cand = job.get('candidate')
        ev = jd / 'evidence' / 'repairs'
        ev.mkdir(parents=True, exist_ok=True)
    except Exception:
        orig = cand = None
    for r in rv:
        pics = ['', '']
        acc = r.get('accepted')
        if isinstance(acc, dict) and orig and cand and Path(str(cand)).exists():
            box = acc['box']
            clip = fitz.Rect(box[0] - 80, box[1] - 30, box[2] + 80, box[3] + 30)
            for k, src in enumerate((orig, cand)):
                try:
                    with fitz.open(src) as d:
                        f = ev / f'{r["item"]}_{"before" if k == 0 else "after"}.png'
                        d[acc['page'] - 1].get_pixmap(dpi=150, clip=clip & d[acc['page'] - 1].rect).save(str(f))
                        pics[k] = f'<img style="max-width:330px" src="{E(_rel(f, jd))}" alt="{E(f.name)}">'
                except Exception:
                    pass
        last = (r.get('attempts') or [{}])[-1].get('review') or {}
        checks = ''.join(f'<li>{"✔" if c["passed"] else "✖"} {E(c["check"])}</li>' for c in last.get('checks', []))
        head = (f'ACCEPTED: "{E(str(r.get("old")))}" → "{E(str(r.get("new")))}" (attempt {len(r.get("attempts", []))})'
                if isinstance(acc, dict) else f'BLOCKED: {E(str(r.get("blocked")))}')
        out.append(f'<tr><td>{E(r["item"])}</td><td>{pics[0]}</td><td>{pics[1]}</td><td>{head}<ul>{checks}</ul></td></tr>')
    sb = job.get('qa_sendbacks') or []
    out.append('</table>' + (f'<p>Release QA sent work back to repair {len(sb)} time(s): '
                             f'{E(str(sb))}</p>' if sb else '<p>Release QA did not need to send any work back.</p>'))
    return ''.join(out)


def write_job_report(root, job):
    from controller import next_action
    root = Path(root)
    jd = root / 'jobs' / job['id']
    qa = job.get('qa') or {}
    status = job.get('status')
    cls = 'ok' if status in ('AWAITING_OWNER_APPROVAL', 'APPROVED', 'EXPORTED') else (
        'bad' if status in ('BLOCKED', 'ERROR') else 'warn')
    b = [f'<h1>Repair report: {E(job["product_name"])}</h1>',
         f'<div class="next {cls}">NEXT STEP: {E(next_action(job))}</div>',
         '<table><tr><th>Status</th><th>Release QA</th><th>Score</th><th>Stopped because</th><th>Original unchanged</th></tr>'
         f'<tr><td>{E(str(status))}</td><td>{E(str(qa.get("decision")))}</td><td>{E(str(qa.get("score")))}'
         f' / 100 (target {E(str(qa.get("target", 99.9)))})</td><td>{E(str(job.get("stop_reason")))}</td>'
         f'<td>{"YES (SHA-256 re-checked)" if job.get("original_intact") else "<b>NO - STOP</b>"}</td></tr></table>']
    pd, au = job.get('prior_diagnosis'), job.get('repair_authorization') or {}
    b.append('<p><b>Findings documented before repair:</b> ' + (
        f'diagnosis {E(pd["id"])} ({pd["findings"]} findings, {pd["proposed_corrections"]} proposed corrections) at {E(pd["created_at"])}'
        if pd else 'baseline findings recorded at job start (no separate diagnosis was run)') +
        f'<br><b>Repair of a copy authorized by:</b> {E(str(au.get("by")))} — {E(str(au.get("method", "")))} '
        f'{E(str(au.get("at", "")))}</p>')
    if job.get('approval'):
        ap = job['approval']
        b.append(f'<p><b>Release approved by:</b> {E(ap["owner"])} at {E(ap["at"])} '
                 f'(visual review confirmed: {ap.get("visual_reviewed")})</p>')
    if qa.get('reasons'):
        b.append('<h2>Why it is not ready</h2><ul>' + ''.join(f'<li>{E(r)}</li>' for r in qa['reasons']) + '</ul>')
    imf = qa.get('image_findings') or []
    decided = job.get('image_decisions') or {}
    if qa.get('image_review') or decided:
        for rel, rv in (qa.get('image_review') or {}).items():
            st = rv['stats']
            b.append(f'<h2>Image pages read by the page reader (OCR): {E(rel)}</h2><p>{len(rv["pages"])} image page(s) read; '
                     f'{st.get("VERIFIED_CORRECT", 0)} math statements verified correct, {st.get("SUSPECTED_ERROR", 0)} '
                     f'possible math error(s), {st.get("SUSPECTED_TYPO", 0)} possible typo(s), '
                     f'{st.get("LIKELY_OCR_MISREAD", 0)} unclear reading(s) not treated as errors. The reader cannot see '
                     f'every detail of an illustration, so each page still needs your visual confirmation.</p>')
        rows = [(f['image_item'], f) for f in imf] + [(k, {**v['snapshot'], 'decision': v['verdict']})
                                                     for k, v in decided.items() if v['verdict'] == 'dismissed']
        if rows:
            b.append('<table><tr><th>Page</th><th>Picture</th><th>Finding</th><th>Proposed correction</th><th>Your decision</th></tr>')
            for iid, f in sorted(rows, key=lambda x: (x[1].get('page') or 0)):
                img = (f'<img style="max-width:360px" src="{E(_rel(f["crop"], jd))}" alt="{E(iid)}">'
                       if f.get('crop') and Path(f['crop']).exists() else '')
                dec = (decided.get(iid) or {}).get('verdict') or 'to decide'
                b.append(f'<tr><td>{f.get("page")}</td><td>{img}</td><td>{E(str(f.get("detail") or f.get("statement")))}</td>'
                         f'<td>{E(str((decided.get(iid) or {}).get("correction") or f.get("proposal") or ""))}</td>'
                         f'<td>{E(dec)}</td></tr>')
            b.append('</table>')
    b.append(_repairs_section(root, job, jd))
    b.append(page_by_page(qa.get('image_review')))
    un = qa.get('unverified_items') or []
    if un:
        b.append(f'<h2>Questions that need your review ({len(un)})</h2><p>The verifier cannot check these '
                 'automatically (proofs, word problems, multi-part or unsupported question types). Check each one, '
                 'then use "Attest Unverifiable Item…" in tab 2 (key below, or ALL).</p><table><tr><th>#</th>'
                 '<th>Question</th><th>Why</th><th>Key</th></tr>')
        for n_, u in enumerate(un, 1):
            b.append(f'<tr><td>{n_}</td><td>{E(str(u.get("question")))}</td><td>{E(u["status"])}: '
                     f'{E(u["evidence"][:120])}</td><td><small>{E(u["key"])}</small></td></tr>')
        b.append('</table>')
    corr = job.get('corrections') or []
    if corr:
        b.append('<h2>Defects and corrections</h2><table><tr><th>State</th><th>Severity</th><th>Problem</th>'
                 '<th>Correction</th></tr>')
        for c in corr:
            st = c['state']
            if st == 'VERIFIED_AWAITING_OWNER_APPROVAL' and status in ('APPROVED', 'EXPORTED'):
                st = 'VERIFIED_OWNER_APPROVED'
            b.append(f'<tr><td><span class="pill s-{E(st)}">{E(st.replace("_", " "))}</span></td>'
                     f'<td>{E(c["severity"])}</td><td>{E(c.get("file") or "")}: {E(c["detail"])}</td>'
                     f'<td>{E(c.get("proposed_correction") or ("Fixed by a related correction above" if st == "RESOLVED_BY_RELATED_FIX" else "No automatic correction - needs a person"))}</td></tr>')
        b.append('</table><small>VERIFIED = Release QA re-tested a fresh copy and the defect is gone. '
                 'Nothing is released until you approve.</small>')
    ev = jd / 'evidence'
    qe = jd / 'qa' / 'evidence'
    b.append('<h2>Before / after evidence</h2>')
    b.append(_pair('Desktop view', ev / 'baseline_desktop.png', qe / 'qa_desktop.png', jd))
    b.append(_pair('Phone view (375 px)', ev / 'baseline_mobile.png', qe / 'qa_mobile.png', jd))
    for rel, cmp in (qa.get('visual') or {}).items():
        if isinstance(cmp, dict) and cmp.get('pages'):
            vd = jd / 'qa' / 'visual' / Path(rel).stem
            for p in cmp['pages']:
                if p.get('status') == 'CHANGED':
                    b.append(_pair(f'{rel} page {p["page"]} (only changed pages shown)',
                                   vd / 'before' / f'page_{p["page"]:03d}.png',
                                   vd / 'after' / f'page_{p["page"]:03d}.png', jd))
            b.append(f'<p>{E(rel)}: {len(cmp["pages"])} pages compared, changed pages: '
                     f'{E(str(cmp.get("changed_pages") or "none"))}</p>')
    diff = (jd / 'changes.diff').read_text(encoding='utf-8') if (jd / 'changes.diff').exists() else ''
    if diff.strip():
        lines = []
        for l in diff.splitlines():
            c = 'add' if l.startswith('+') and not l.startswith('+++') else (
                'del' if l.startswith('-') and not l.startswith('---') else '')
            lines.append(f'<span class="{c}">{E(l)}</span>')
        b.append('<h2>Exact changes (text files)</h2><pre>' + '\n'.join(lines) + '</pre>')
    if qa.get('checks'):
        b.append('<h2>All Release QA checks</h2><table><tr><th>Result</th><th>Severity</th><th>Check</th><th>Evidence</th></tr>')
        for c in qa['checks']:
            r = {True: 'PASS', False: 'FAIL', None: 'NOT-RUN'}[c[3]]
            b.append(f'<tr><td><span class="pill s-{r}">{r}</span></td><td>{E(c[2])}</td><td>{E(c[0])}</td>'
                     f'<td>{E(str(c[4]))}</td></tr>')
        b.append('</table>')
    out = jd / 'report.html'
    out.write_text(_page(f'Report {job["product_name"]}', ''.join(b)), encoding='utf-8')
    return out


def write_diagnosis_report(root, d):
    root = Path(root)
    dd = root / 'reports' / d['id']
    n_auto, n_person = d['proposed_corrections'], d['needs_person']
    cls = 'ok' if not d['findings'] and not d['academic_needs_human'] else ('warn' if not n_person else 'bad')
    nxt = ('No defects found. You can still run "Repair a Copy & Verify" to get a Release QA score.'
           if not d['findings'] else
           f'{n_auto} problem(s) can be corrected automatically on a COPY. '
           f'{n_person} need a person. Click "Repair a Copy & Verify" to apply the proposed corrections.')
    b = [f'<h1>Diagnosis (read-only): {E(d["product_name"])}</h1>',
         f'<div class="next {cls}">NEXT STEP: {E(nxt)}</div>',
         f'<p>Type: {E(str(d.get("product_type")))} - nothing was changed - original unchanged: '
         f'{"YES" if d["original_intact"] else "NO"}</p>',
         f'<p>Answers checked automatically: {d["academic_checked"]} ({d["academic_correct"]} correct). '
         f'Answers needing a person: {len(d["academic_needs_human"])}.</p>']
    if d['findings']:
        b.append('<h2>Findings</h2><table><tr><th>State</th><th>Severity</th><th>Problem</th><th>Proposed correction</th></tr>')
        for f in d['findings']:
            pic = (f'<br><img style="max-width:340px" src="{E(_rel(f["crop"], dd))}" alt="evidence">'
                   if f.get('crop') and Path(f['crop']).exists() else '')
            b.append(f'<tr><td><span class="pill s-{E(f["state"])}">{E(f["state"])}</span></td><td>{E(f["severity"])}</td>'
                     f'<td>{E(f.get("file") or "")}{(":" + str(f["line"])) if f.get("line") else ""} {E(f["detail"])}{pic}</td>'
                     f'<td>{E(f["proposed_correction"] or "None - needs a person")}</td></tr>')
        b.append('</table>')
    if d['academic_needs_human']:
        b.append('<h2>Answers the verifier cannot check</h2><ul>' + ''.join(
            f'<li>{E(str(a["question"]))} - {E(a["evidence"])}</li>' for a in d['academic_needs_human']) + '</ul>')
    b.append(page_by_page(d.get('image_review')))
    ev = dd / 'evidence'
    for name in ('baseline_desktop.png', 'baseline_mobile.png'):
        if (ev / name).exists():
            b.append(f'<h3>{"Desktop" if "desktop" in name else "Phone"} view as it is now</h3>'
                     f'<img style="max-width:100%;border:1px solid #ccc" src="evidence/{name}" alt="{name}">')
    out = dd / 'diagnosis.html'
    out.write_text(_page(f'Diagnosis {d["product_name"]}', ''.join(b)), encoding='utf-8')
    return out
