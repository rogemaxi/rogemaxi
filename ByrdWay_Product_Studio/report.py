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
    ev = dd / 'evidence'
    for name in ('baseline_desktop.png', 'baseline_mobile.png'):
        if (ev / name).exists():
            b.append(f'<h3>{"Desktop" if "desktop" in name else "Phone"} view as it is now</h3>'
                     f'<img style="max-width:100%;border:1px solid #ccc" src="evidence/{name}" alt="{name}">')
    out = dd / 'diagnosis.html'
    out.write_text(_page(f'Diagnosis {d["product_name"]}', ''.join(b)), encoding='utf-8')
    return out
