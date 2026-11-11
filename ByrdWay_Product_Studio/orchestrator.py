"""Master Orchestrator and the seven specialist roles (milestone G).

DETECT -> DIAGNOSE -> REPAIR -> TEST -> INDEPENDENT VERIFY -> SCORE -> REPEAT

The seven roles are logical components (not seven paid processes):
  1 Orchestrator            - this module: job state machine, limits, evidence
  2 PowerToolRepairAgent    - static HTML/JS audit + browser tests + minimal fixes
  3 ExplainerRepairAgent    - PDF inspection + evidence-backed region corrections
  4 Power Tool Builder      - builders.build_power_tool_module (blueprint driven)
  5 Lil Dr. Byrd Builder    - builders.build_lil_dr_byrd_chapter (approved mascot only)
  6 AcademicVerifierAgent   - academic.py, deterministic, independent of repairers
  7 ReleaseQAAgent          - fresh re-test of the repacked candidate; can BLOCK

The orchestrator never scores or certifies; only ReleaseQAAgent produces the
decision, from a fresh extraction of the candidate package.
"""
import json, shutil, tempfile, time, uuid, zipfile
from collections import Counter
from pathlib import Path, PurePosixPath

import academic
import htmlaudit
import imageread
import pdftools
from browsertest import run_browser_tests, browser_checks, compare_images
from config import load_settings
from engine import (workspace, original_file, verify_original, write_json, read_json, utcnow, sha256,
                    safe_extract_zip, TEXT_EXT, rmtree_force)
from joblog import JobLog
from quality import score
from zipproject import WorkingCopy, PatchError

ROLE_ORCH, ROLE_PT, ROLE_EX, ROLE_AV, ROLE_QA = ('Orchestrator', 'Power Tool Repair', 'Explainer Repair',
                                                 'Academic Verifier', 'Release QA')
TERMINAL = {'APPROVED', 'EXPORTED', 'REJECTED'}


def _files_map(base):
    base = Path(base)
    out = {}
    for p in sorted(base.rglob('*')):
        if p.is_file():
            rel = p.relative_to(base).as_posix()
            out[rel] = p.read_text(encoding='utf-8', errors='replace') if p.suffix.lower() in TEXT_EXT else None
    return out


# ================================================================ agents
class AcademicVerifierAgent:
    role = ROLE_AV

    def verify_sources(self, files):
        """Verify answer items embedded in Power Tool source. Returns (results, findings, checks)."""
        results, findings, checks = [], [], []
        for rel, text in files.items():
            if text is None or PurePosixPath(rel).suffix.lower() not in ('.js', '.json', '.html', '.htm'):
                continue
            for item in academic.extract_source_items(rel, text):
                r = academic.verify_item(item)
                r.update(file=rel, line=item.get('line'), question=item.get('question'))
                results.append(r)
                cid = f'academic:{rel}:{item.get("line")}:{(item.get("question") or "")[:40]}'
                passed = True if r['status'] == academic.CORRECT else (False if r['status'] == academic.INCORRECT else None)
                checks.append((cid, 'academic', 'CRITICAL', passed, r['evidence'][:200]))
                if r['status'] == academic.INCORRECT:
                    findings.append({'id': f'A{len(findings) + 1:03d}', 'check': 'academic.wrong_answer',
                                     'severity': 'CRITICAL', 'category': 'academic', 'file': rel,
                                     'line': item.get('line'), 'detail': f'Wrong answer for "{item.get("question")}": '
                                     f'claimed {r["claimed"]}, verified {r["expected"]}',
                                     'evidence': '; '.join(r['methods']), 'fix': academic.repair_for_item(item, r)})
        return results, findings, checks

    def verify_pdf_text(self, rel, page_texts):
        results, findings, checks = [], [], []
        for pno, text in enumerate(page_texts, 1):
            for item in academic.extract_arithmetic_claims(text) + academic.extract_qa_pairs(text):
                r = academic.verify_item(item)
                r.update(file=rel, page=pno, question=item.get('question'))
                results.append(r)
                passed = True if r['status'] == academic.CORRECT else (False if r['status'] == academic.INCORRECT else None)
                checks.append((f'academic:{rel}:p{pno}:{item["question"][:40]}', 'academic', 'CRITICAL', passed,
                               r['evidence'][:200]))
                if r['status'] == academic.INCORRECT:
                    fix = None
                    loc = item.get('location', {}).get('text', '').strip().rstrip('.,')
                    if loc and r.get('suggested_answer') and item.get('verify', {}).get('type') == 'expression':
                        new = loc[:loc.rindex(item['answer'])] + r['suggested_answer']
                        fix = {'type': 'pdf_text', 'file': rel, 'page': pno, 'find': loc, 'replace': new,
                               'reason': f'Arithmetic claim "{loc}" verified incorrect; correct value {r["suggested_answer"]}'}
                    findings.append({'id': f'A{len(findings) + 1:03d}', 'check': 'academic.wrong_claim',
                                     'severity': 'CRITICAL', 'category': 'academic', 'file': rel, 'page': pno,
                                     'detail': f'Page {pno}: "{loc or item["question"]}" is incorrect (expected {r["expected"]})',
                                     'evidence': '; '.join(r['methods']), 'fix': fix})
        return results, findings, checks


    def verify_image_review(self, rel, review, decisions):
        """Turn an OCR review of image-only pages into results, findings and checks.
        Suspected errors and typos need the OWNER's decision (confirmed / dismissed); until then they
        hold the product at NOT_VERIFIED and cannot be covered by a blanket attestation."""
        results, findings, checks = [], [], []
        decisions = decisions or {}
        for it in review['items']:
            pno, iid = it['page'], it['id']
            ev = f'read from the page image (OCR, confidence {it["conf"]:.2f}); ' + str(it.get('evidence') or '')
            if it['status'] == imageread.STATUS_OK:
                results.append({'status': academic.CORRECT, 'file': rel, 'page': pno, 'question': it['statement'],
                                'evidence': ev, 'methods': it.get('methods', [])})
                checks.append((f'academic:{rel}:p{pno}:ocr:{iid}', 'academic', 'CRITICAL', True, ev[:200]))
                continue
            if it['status'] == imageread.STATUS_MISREAD:
                findings.append({'id': iid, 'check': 'image.ocr_misread', 'severity': 'INFO', 'category': 'academic',
                                 'file': rel, 'page': pno, 'line': None, 'crop': it.get('crop'), 'fix': None,
                                 'detail': f'Page {pno}: "{it["statement"]}" was read unclearly; it is correct if read as '
                                           f'"{it.get("alternative_reading")}". Not reported as an error.',
                                 'evidence': ev})
                continue
            if it['status'] not in (imageread.STATUS_ERR, 'SUSPECTED_TYPO'):
                continue
            typo = it['status'] == 'SUSPECTED_TYPO'
            d = decisions.get(iid) or {}
            verdict = d.get('verdict')
            passed = None if not verdict else (verdict == 'dismissed')
            sev = 'MINOR' if typo else 'CRITICAL'
            cid = f'image:{rel}:{iid}'
            checks.append((cid, 'typography' if typo else 'academic', sev, passed,
                           (f'owner {verdict}: ' if verdict else 'awaiting owner decision: ') + it['statement']))
            if verdict == 'dismissed':
                continue
            if not verdict:
                results.append({'status': 'PENDING_OWNER_DECISION', 'file': rel, 'page': pno,
                                'question': f'Image finding {iid}: {it["statement"]}', 'evidence': ev})
            what = 'spelling' if typo else f'"{it["statement"]}" appears incorrect (verified value: {it.get("expected")})'
            findings.append({'id': iid, 'check': 'image.typo' if typo else 'image.math_error', 'severity': sev,
                             'category': 'typography' if typo else 'academic', 'file': rel, 'page': pno, 'line': None,
                             'detail': f'Page {pno}: {what}' + (f' "{it["statement"]}"' if typo else '') +
                                       (' - CONFIRMED by owner' if verdict == 'confirmed' else ' - read from the page image'),
                             'evidence': ev, 'fix': None, 'proposal': it.get('proposal'), 'crop': it.get('crop'),
                             'image_item': iid, 'decision': verdict, 'rect': it['rect'], 'statement': it['statement'],
                             'expected': it.get('expected')})
        for pno, st in review['pages'].items():
            results.append({'status': 'OCR_PARTIAL', 'file': rel, 'page': int(pno),
                            'question': f'Page {pno} is an image: confirm it has no errors the reader could not read',
                            'evidence': f'{st["lines_read"]} text lines machine-read; {st["statements"]} math statements '
                                        f'found, {st["verified"]} verified correct'})
        return results, findings, checks


class PowerToolRepairAgent:
    role = ROLE_PT

    def __init__(self, settings):
        self.settings = settings

    def detect(self, site_dir, files, shots_dir, label, run_browser=True):
        findings, checks = htmlaudit.audit_files(files)
        br = None
        entry = htmlaudit.entry_page([p for p, t in files.items() if t is not None])
        if entry and run_browser:
            b = self.settings['browser']
            br = run_browser_tests(site_dir, entry, shots_dir, label, b['timeout_ms'], b['max_clicks'], b['chromium_path'])
            checks += browser_checks(br)
            for e in br.get('errors', []):
                findings.append({'id': f'B{len(findings) + 1:03d}', 'check': 'browser.js_exception', 'severity': 'CRITICAL',
                                 'category': 'functionality', 'file': entry, 'line': None,
                                 'detail': f'JavaScript exception: {e["message"]} (after {e["after"]})',
                                 'evidence': 'headless Chromium pageerror', 'fix': None})
            for img in br.get('broken_images', []):
                findings.append({'id': f'B{len(findings) + 1:03d}', 'check': 'browser.broken_image', 'severity': 'MAJOR',
                                 'category': 'assets', 'file': entry, 'line': None, 'detail': f'Image failed to load: {img}',
                                 'evidence': 'naturalWidth == 0', 'fix': None})
        return findings, checks, br


class ExplainerRepairAgent:
    role = ROLE_EX

    def detect(self, pdf_path, rel, render_dir):
        rep, findings, checks = pdftools.inspect_pdf(pdf_path, render_dir)
        texts = pdftools.page_texts(pdf_path) if rep.get('pages') else []
        return rep, findings, checks, texts

    def apply_fix(self, wc, fix, work_dir):
        src = wc.path(fix['file'])
        Path(work_dir).mkdir(parents=True, exist_ok=True)
        out = Path(work_dir) / f'fix_{uuid.uuid4().hex[:6]}.pdf'
        ev = pdftools.propose_text_correction(src, out, fix['page'], fix['find'], fix['replace'], Path(work_dir) / out.stem)
        if not ev['change_confined_to_region']:
            raise PatchError('Visual diff shows changes outside the corrected region; rejected')
        evidence = {k: v for k, v in ev.items() if k != 'comparison'}
        evidence['changed_pages'] = ev['changed_pages']
        return wc.replace_file_bytes(fix['file'], out.read_bytes(), fix['reason'], 'deterministic:pdf_region', evidence)


# ============================================================== detection
def detect_all(settings, site_dir, shots_dir, label, run_browser=True, decisions=None, progress=None):
    """Run every applicable specialist against a directory of product files."""
    files = _files_map(site_dir)
    res = {'findings': [], 'checks': [], 'browser': None, 'academic': [], 'pdf': {}, 'types': set(),
           'image_review': {}}
    html = [p for p in files if p.lower().endswith(('.html', '.htm'))]
    pdfs = [p for p in files if p.lower().endswith('.pdf')]
    av = AcademicVerifierAgent()
    if html:
        res['types'].add('power_tool')
        f, c, br = PowerToolRepairAgent(settings).detect(site_dir, files, shots_dir, label, run_browser)
        res['findings'] += f
        res['checks'] += c
        res['browser'] = br
        r, f2, c2 = av.verify_sources(files)
        res['academic'] += r
        res['findings'] += f2
        res['checks'] += c2
    for rel in pdfs:
        res['types'].add('pdf')
        rep, f, c, texts = ExplainerRepairAgent().detect(Path(site_dir) / rel, rel, Path(shots_dir) / f'{label}_{PurePosixPath(rel).stem}')
        res['pdf'][rel] = rep
        res['findings'] += f
        res['checks'] += [(f'{x[0]}:{rel}',) + tuple(x[1:]) for x in c]
        r, f2, c2 = av.verify_pdf_text(rel, texts)
        res['academic'] += r
        res['findings'] += f2
        res['checks'] += c2
        image_pages = rep.get('image_only_pages') or []
        if image_pages:
            if imageread.available():
                review = imageread.review_pdf(Path(site_dir) / rel, image_pages,
                                              crop_dir=Path(shots_dir) / f'{label}_image_review_{PurePosixPath(rel).stem}',
                                              progress=progress, cache_dir=settings.get('_ocr_cache'))
                res['image_review'][rel] = review
                r3, f3, c3 = av.verify_image_review(rel, review, decisions)
                res['academic'] += r3
                res['findings'] += f3
                res['checks'] += c3
            else:
                res['checks'].append((f'academic.image_reader:{rel}', 'academic', 'CRITICAL', None,
                                      'image-only pages but the page reader (OCR) is not installed'))
    res['types'] = sorted(res['types'])
    return res


def _fkey(f):
    return (f['check'], f.get('file'), f.get('detail'))


def _fixkey(f):
    x = f['fix']
    return (x.get('file'), x.get('find'), x.get('replace'))


def _regressions(before, after):
    b = {c[0]: c[3] for c in before['checks']}
    a = {c[0]: c[3] for c in after['checks']}
    reg = [cid for cid, ok in b.items() if ok is True and a.get(cid) is False]
    old = {_fkey(f) for f in before['findings']}
    new = [f for f in after['findings'] if f['severity'] in ('CRITICAL', 'MAJOR') and _fkey(f) not in old]
    return reg, new


# ============================================================ orchestrator
class Orchestrator:
    role = ROLE_ORCH

    def __init__(self, root, settings=None):
        self.root = workspace(root)
        self.settings = dict(settings or load_settings(root))
        self.settings['_ocr_cache'] = str(self.root / 'cache' / 'ocr')

    def _job_dir(self, job_id):
        return self.root / 'jobs' / job_id

    def load_job(self, job_id):
        return read_json(self._job_dir(job_id) / 'job.json')

    def save_job(self, job):
        job['updated_at'] = utcnow()
        write_json(self._job_dir(job['id']) / 'job.json', job)

    def list_jobs(self):
        out = []
        for p in (self.root / 'jobs').glob('*/job.json'):
            try:
                out.append(read_json(p))
            except ValueError:
                continue
        return sorted(out, key=lambda j: j.get('created_at', ''), reverse=True)

    # --------------------------------------------------------------------
    def run_repair_job(self, pid, ai_enabled=False, approver=None, ai_client=None, run_browser=True,
                       progress=None, authorization=None):
        """Full bounded quality loop. Returns the job record."""
        r = self.settings['repair']
        job_id = time.strftime('%Y%m%d%H%M%S') + '_' + uuid.uuid4().hex[:6]
        jd = self._job_dir(job_id)
        jd.mkdir(parents=True)
        log = JobLog(self.root, job_id)
        say = (lambda m: (log.info(ROLE_ORCH, m), progress and progress(m)))
        src, manifest = original_file(self.root, pid)
        job = {'id': job_id, 'product_id': pid, 'product_name': manifest['name'],
               'product_type': manifest.get('product_type'), 'original_sha256': manifest['sha256'],
               'created_at': utcnow(), 'status': 'BASELINE', 'iterations': [], 'stop_reason': None,
               'limits': dict(r), 'ai_enabled': bool(ai_enabled), 'escalations': [], 'attestations': [],
               'roles_used': [ROLE_ORCH, ROLE_AV, ROLE_QA],
               'repair_authorization': authorization or {'by': 'not recorded (direct engine call)'},
               'prior_diagnosis': self._latest_diagnosis(pid)}
        self.save_job(job)
        say(f'Job {job_id} started for {manifest["name"]} ({manifest.get("product_type")})')
        t0 = time.time()
        try:
            wc = WorkingCopy.create(self.root, pid, job_id)
            cp = wc.checkpoint('baseline')
            shots = jd / 'evidence'
            state = detect_all(self.settings, wc.files, shots, 'baseline', run_browser)
            job['roles_used'] += [ROLE_PT] if 'power_tool' in state['types'] else []
            job['roles_used'] += [ROLE_EX] if 'pdf' in state['types'] else []
            job['baseline'] = self._summ(state)
            write_json(jd / 'baseline_findings.json', state['findings'])
            say(f'Baseline: {len(state["findings"])} findings, {len(state["checks"])} checks')
            job['status'] = 'REPAIRING'
            self.save_job(job)
            fail_count = Counter()
            signatures = []
            ai_used = 0
            for it in range(1, int(r['max_iterations']) + 1):
                if time.time() - t0 > r['max_runtime_seconds']:
                    job['stop_reason'] = 'RUNTIME_LIMIT'
                    break
                exhausted = {k for k, v in fail_count.items() if v >= r['repeat_failure_limit']}
                fixable = [f for f in state['findings'] if f.get('fix') and _fixkey(f) not in exhausted]
                ai_patches = []
                if not fixable:
                    unresolved = [f for f in state['findings'] if f['severity'] in ('CRITICAL', 'MAJOR')]
                    if not unresolved:
                        job['stop_reason'] = 'NO_OPEN_DEFECTS'
                        break
                    if ai_enabled and ai_used < 2:
                        ai_patches = self._ai_patches(job_id, wc, unresolved, approver, ai_client, log)
                        ai_used += 1
                        if ai_patches is None:
                            job['stop_reason'] = getattr(self, '_last_ai_stop', None) or 'AI_UNAVAILABLE'
                            break
                        fixable = [{'id': f'AI{i}', 'check': 'ai.patch', 'severity': 'MAJOR', 'fix': p,
                                    'detail': p['reason'], 'file': p['file']} for i, p in enumerate(ai_patches)
                                   if (p['file'], p['find'], p['replace']) not in exhausted]
                    if not fixable:
                        job['stop_reason'] = 'UNFIXABLE_DEFECTS_REQUIRE_HUMAN'
                        break
                iter_cp = wc.checkpoint(f'before iteration {it}')
                applied, rejected = [], []
                for f in fixable:
                    fx = f['fix']
                    single_cp = wc.checkpoint(f'before fix {f["id"]}')
                    try:
                        if fx.get('type') == 'pdf_text':
                            rec = ExplainerRepairAgent().apply_fix(wc, fx, jd / 'pdf_work')
                        else:
                            rec = wc.apply_patch(fx['file'], fx['find'], fx['replace'], fx['reason'],
                                                 source='ai_suggestion' if f['check'] == 'ai.patch' else 'deterministic',
                                                 defect_id=f['id'])
                        applied.append({'finding': f['id'], 'key': list(map(str, _fkey(f))), 'check': f['check'],
                                        'file': fx['file'], 'severity': f['severity'], 'detail': f['detail'],
                                        'reason': fx['reason'], 'line': rec.get('line')})
                    except Exception as e:  # any failed fix is rolled back, counted, never fatal
                        fail_count[_fixkey(f)] += 1
                        rejected.append({'finding': f['id'], 'error': str(e)})
                        wc.rollback(single_cp, f'fix failed: {e}')
                new_state = detect_all(self.settings, wc.files, shots, f'iter{it}', run_browser)
                reg, new_defects = _regressions(state, new_state)
                rec = {'iteration': it, 'applied': applied, 'rejected': rejected, 'regressions': reg,
                       'new_defects': [_fkey(f) for f in new_defects],
                       'open_before': len(state['findings']), 'open_after': len(new_state['findings'])}
                if reg or new_defects:
                    wc.rollback(iter_cp, f'regression: {reg or new_defects}')
                    for f in fixable:
                        fail_count[_fixkey(f)] += 1
                    rec['rolled_back'] = True
                    log.warn(ROLE_ORCH, f'Iteration {it} regressed; rolled back', regressions=reg)
                else:
                    state = new_state
                    wc.checkpoint(f'after iteration {it}')
                job['iterations'].append(rec)
                self.save_job(job)
                say(f'Iteration {it}: applied {len(applied)}, rejected {len(rejected)}, '
                    f'{"ROLLED BACK" if rec.get("rolled_back") else "kept"}; open findings {len(state["findings"])}')
                sig = tuple(sorted(map(str, (_fkey(f) for f in state['findings']))))
                signatures.append(sig)
                if len(signatures) > r['no_progress_limit'] and \
                        all(s == sig for s in signatures[-(r['no_progress_limit'] + 1):]):
                    job['stop_reason'] = 'NO_PROGRESS'
                    break
            else:
                job['stop_reason'] = job['stop_reason'] or 'ITERATION_LIMIT'
            job['escalations'] = [{'fix': list(k), 'failures': v} for k, v in fail_count.items()
                                  if v >= r['repeat_failure_limit']]
            job['escalations'] += [{'finding': f['id'], 'severity': f['severity'], 'detail': f['detail'],
                                    'needs': 'human review' if not f.get('fix') else 'fix failed'}
                                   for f in state['findings'] if f['severity'] in ('CRITICAL', 'MAJOR')]
            job['final_open_findings'] = state['findings']
            write_json(jd / 'final_findings.json', state['findings'])
            # candidate
            cand_dir = self.root / 'proposals' / pid
            cand_dir.mkdir(parents=True, exist_ok=True)
            cand = wc.repack(cand_dir / f'{job_id}_{manifest["name"]}')
            job['candidate'] = str(cand)
            job['candidate_sha256'] = sha256(cand)
            job['history'] = wc.meta['history']
            job['checkpoints'] = [{'id': c['id'], 'history_len': c['history_len']} for c in wc.meta['checkpoints']]
            diff = wc.diff()
            (jd / 'changes.diff').write_text(diff, encoding='utf-8')
            job['changes'] = wc.changed_files()
            job['status'] = 'QA'
            self.save_job(job)
            qa = ReleaseQAAgent(self.root, self.settings).evaluate(job, run_browser)
            job['qa'] = qa
            job['status'] = {'PASS': 'AWAITING_OWNER_APPROVAL'}.get(qa['decision'], qa['decision'])
            job['corrections'] = correction_lifecycle(read_json(jd / 'baseline_findings.json'), job, qa)
            say(f'Release QA decision: {qa["decision"]} score={qa["score"]}')
        except Exception as e:
            log.error(ROLE_ORCH, 'Job failed', exc=e)
            job['status'] = 'ERROR'
            job['error'] = f'{type(e).__name__}: {e}'
        job['duration_s'] = round(time.time() - t0, 2)
        job.pop('_ai_stop', None)
        job['original_intact'] = verify_original(self.root, pid)
        self.save_job(job)
        self._write_report(job)
        try:
            import report
            report.write_job_report(self.root, job)
        except Exception as e:                       # report is evidence, never fatal
            log.error(ROLE_ORCH, 'HTML report failed', exc=e)
        return job

    # --------------------------------------------------------------------
    def diagnose(self, pid, run_browser=True, progress=None):
        """Read-only diagnosis: finds defects and PROPOSES corrections. Changes nothing."""
        src, manifest = original_file(self.root, pid)
        diag_id = 'diag_' + time.strftime('%Y%m%d%H%M%S') + '_' + uuid.uuid4().hex[:4]
        out = self.root / 'reports' / diag_id
        out.mkdir(parents=True)
        wc = WorkingCopy.create(self.root, pid, diag_id)
        try:
            progress and progress('Diagnosing (read-only)...')
            st = detect_all(self.settings, wc.files, out / 'evidence', 'baseline', run_browser, progress=progress)
        finally:
            shutil.rmtree(wc.dir, ignore_errors=True)
        findings = []
        for f in st['findings']:
            state = 'SUSPECTED' if f['severity'] == 'INFO' else 'DETECTED'
            findings.append({**f, 'state': state,
                             'proposed_correction': describe_fix(f.get('fix')) if f.get('fix') else f.get('proposal')})
        unverified = [r for r in st['academic'] if r['status'] not in (academic.CORRECT, academic.INCORRECT)]
        result = {'id': diag_id, 'product_id': pid, 'product_name': manifest['name'],
                  'product_type': manifest.get('product_type'), 'created_at': utcnow(), 'findings': findings,
                  'academic_checked': len(st['academic']),
                  'academic_correct': len([r for r in st['academic'] if r['status'] == academic.CORRECT]),
                  'academic_needs_human': [{'question': r.get('question'), 'status': r['status'],
                                            'evidence': r['evidence']} for r in unverified],
                  'browser': st.get('browser'), 'checks': [list(c) for c in st['checks']],
                  'proposed_corrections': len([f for f in findings if f['proposed_correction']]),
                  'needs_person': len([f for f in findings if not f['proposed_correction'] and f['state'] == 'DETECTED']),
                  'image_findings': len([f for f in findings if f.get('image_item')]),
                  'image_review': {rel: {'pages': v['pages'], 'stats': v['stats'], 'engine': v['engine'],
                                         'items': [{k: i.get(k) for k in ('id', 'page', 'status', 'kind', 'statement',
                                                                          'expected', 'reason', 'alternative_reading')}
                                                   for i in v['items']]}
                                   for rel, v in st.get('image_review', {}).items()},
                  'original_intact': verify_original(self.root, pid)}
        write_json(out / 'diagnosis.json', result)
        try:
            import report
            report.write_diagnosis_report(self.root, result)
        except Exception as e:
            JobLog(self.root, diag_id).error(ROLE_ORCH, 'diagnosis report failed', exc=e)
        JobLog(self.root, diag_id).info(ROLE_ORCH, f'Diagnosis of {manifest["name"]}: {len(findings)} findings, '
                                        f'{result["proposed_corrections"]} correctable automatically')
        return result

    def _latest_diagnosis(self, pid):
        best = None
        for p in (self.root / 'reports').glob('diag_*/diagnosis.json'):
            try:
                d = read_json(p)
            except ValueError:
                continue
            if d.get('product_id') == pid and (best is None or d['created_at'] >= best['created_at']):
                best = {'id': d['id'], 'created_at': d['created_at'], 'findings': len(d['findings']),
                        'proposed_corrections': d['proposed_corrections'],
                        'report': str(p.parent / 'diagnosis.html')}
        return best

    def _ai_patches(self, job_id, wc, unresolved, approver, client, log):
        from ai_roles import propose_patches
        from costs import BudgetExceeded, SpendNotApproved, PriceUnknown
        files = {rel: wc.read(rel) for rel in wc.text_files() if rel.lower().endswith(('.html', '.htm', '.js', '.css', '.json'))}
        try:
            patches = propose_patches(self.root, job_id, files, unresolved, approver, client=client)
            log.info(ROLE_PT, f'AI suggested {len(patches)} patch(es)')
            return patches
        except BudgetExceeded:
            reason = 'BUDGET_LIMIT'
        except SpendNotApproved:
            reason = 'SPEND_NOT_APPROVED'
        except PriceUnknown:
            reason = 'PRICE_UNKNOWN'
        except Exception as e:
            log.error(ROLE_PT, 'AI call failed', exc=e)
            reason = 'AI_ERROR'
        log.warn(ROLE_ORCH, f'AI step stopped: {reason}')
        self._last_ai_stop = reason
        return None

    def _summ(self, state):
        sev = Counter(f['severity'] for f in state['findings'])
        return {'findings': len(state['findings']), 'by_severity': dict(sev), 'checks': len(state['checks']),
                'academic_items': len(state['academic']), 'types': state['types']}

    def _write_report(self, job):
        jd = self._job_dir(job['id'])
        lines = [f'# Job report {job["id"]}', '', f'Product: {job["product_name"]} ({job.get("product_type")})',
                 f'Status: **{job["status"]}**  Stop reason: {job.get("stop_reason")}',
                 f'Original intact (SHA-256 re-verified): {job.get("original_intact")}', '']
        qa = job.get('qa')
        if qa:
            lines += [f'## Release QA (independent re-test of candidate)', f'Decision: **{qa["decision"]}**  '
                      f'Score: {qa["score"]} (target {qa["target"]})  Executed checks: {qa["executed_checks"]}',
                      ''] + [f'- {r}' for r in qa['reasons']] + ['']
        lines.append('## Iterations')
        for it in job.get('iterations', []):
            lines.append(f'- {it["iteration"]}: applied {len(it["applied"])}, rejected {len(it["rejected"])}'
                         f'{", ROLLED BACK" if it.get("rolled_back") else ""}')
            for a in it['applied']:
                lines.append(f'  - {a["file"]}: {a["reason"]}')
        if job.get('escalations'):
            lines += ['', '## Human escalation required'] + [f'- {json.dumps(e)[:300]}' for e in job['escalations']]
        if job.get('error'):
            lines += ['', f'## ERROR\n{job["error"]}']
        (jd / 'REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


# ================================================================ QA agent
class ReleaseQAAgent:
    """Independent: re-extracts the candidate package and re-runs every test."""
    role = ROLE_QA

    def __init__(self, root, settings):
        self.root = workspace(root)
        self.settings = dict(settings)
        self.settings['_ocr_cache'] = str(self.root / 'cache' / 'ocr')

    def evaluate(self, job, run_browser=True):
        jd = self.root / 'jobs' / job['id']
        qa_dir = jd / 'qa'
        rmtree_force(qa_dir)
        qa_dir.mkdir(parents=True)
        log = JobLog(self.root, job['id'])
        checks = []
        pid = job['product_id']
        intact = verify_original(self.root, pid)
        checks.append(('integrity.original_unchanged', 'integrity', 'CRITICAL', intact,
                       'SHA-256 of locked original re-computed'))
        cand = Path(job['candidate'])
        cand_ok = cand.exists() and sha256(cand) == job['candidate_sha256']
        checks.append(('integrity.candidate_hash', 'integrity', 'CRITICAL', cand_ok, 'candidate unchanged since repack'))
        src, manifest = original_file(self.root, pid) if intact else (None, None)
        fresh = qa_dir / 'candidate'
        orig_dir = qa_dir / 'original'
        if cand.suffix.lower() == '.zip':
            try:
                safe_extract_zip(cand, fresh)
                checks.append(('integrity.zip_valid', 'integrity', 'CRITICAL', True, 'candidate ZIP passes safety rules'))
            except ValueError as e:
                checks.append(('integrity.zip_valid', 'integrity', 'CRITICAL', False, str(e)))
                return self._finish(job, checks, {}, log)
            shutil.copytree(src.parent / 'unpacked', orig_dir) if src else None
        else:
            fresh.mkdir()
            shutil.copyfile(cand, fresh / manifest['name'] if manifest else fresh / cand.name)
            if src:
                orig_dir.mkdir()
                shutil.copyfile(src, orig_dir / src.name)
        # protected (binary) files must be byte-identical unless changed by a recorded evidence-backed fix
        recorded = {h['file'] for h in job.get('history', []) if h.get('replace_file')}
        if src:
            o, c = _files_map(orig_dir), _files_map(fresh)
            bad = []
            for rel in o:
                if o[rel] is None and rel not in recorded:
                    if rel not in c or sha256(orig_dir / rel) != sha256(fresh / rel):
                        bad.append(rel)
            removed = [r for r in o if r not in c]
            added = [r for r in c if r not in o]
            checks.append(('integrity.protected_assets_unchanged', 'integrity', 'CRITICAL', not bad,
                           f'changed/missing protected files: {bad}' if bad else 'all images/binaries byte-identical'))
            checks.append(('integrity.no_unexpected_file_changes', 'integrity', 'CRITICAL', not removed and not added,
                           f'removed {removed} added {added}'))
            # replay the recorded patch history onto the ORIGINAL; candidate must match exactly
            silent = _replay_mismatches(o, c, fresh, job)
            checks.append(('integrity.all_changes_recorded', 'integrity', 'CRITICAL', not silent,
                           f'changes not explained by recorded patches: {silent}' if silent
                           else 'replaying recorded patches on the original reproduces the candidate exactly'))
        state = detect_all(self.settings, fresh, qa_dir / 'evidence', 'qa', run_browser,
                           decisions=job.get('image_decisions'))
        checks += state['checks']
        # visual comparison against the original
        visual = {}
        if 'pdf' in state['types'] and src:
            for rel in state['pdf']:
                if (orig_dir / rel).exists():
                    cmp = pdftools.compare_pdfs(orig_dir / rel, fresh / rel, qa_dir / 'visual' / PurePosixPath(rel).stem)
                    allowed = set()
                    for h in job.get('history', []):
                        if h.get('replace_file') and h['file'] == rel:
                            allowed |= set(h.get('evidence', {}).get('changed_pages', []))
                    unexpected = [p for p in cmp['changed_pages'] if p not in allowed]
                    visual[rel] = cmp
                    checks.append((f'visual.changes_confined:{rel}', 'visual', 'CRITICAL', not unexpected,
                                   f'changed pages {cmp["changed_pages"]}, allowed {sorted(allowed)}'))
                    checks.append((f'visual.page_count:{rel}', 'visual', 'CRITICAL',
                                   cmp['before_pages'] == cmp['after_pages'],
                                   f'{cmp["before_pages"]} -> {cmp["after_pages"]} pages'))
        if state.get('browser') and state['browser'].get('screenshots', {}).get('desktop'):
            base = jd / 'evidence' / 'baseline_desktop.png'
            if base.exists():
                d = compare_images(base, state['browser']['screenshots']['desktop'], qa_dir / 'visual_desktop_diff.png')
                visual['desktop'] = d
                checks.append(('visual.render_compared', 'visual', 'INFO', True,
                               f'{d["changed_fraction"] * 100:.3f}% of pixels changed vs baseline'))
        # asset fidelity for built products
        prov = fresh / 'BUILD_PROVENANCE.json'
        if prov.exists():
            p = read_json(prov)
            checks.append(('asset_fidelity.owner_content', 'asset_fidelity', 'CRITICAL', not p.get('sample_content'),
                           'built from SAMPLE blueprint content - not approved ByrdWay material'
                           if p.get('sample_content') else 'owner blueprint content'))
            for u, rec in p['units'].items():
                t = (rec.get('template') or {}).get('template_status')
                if t is not None:
                    checks.append((f'asset_fidelity.template:{u}', 'asset_fidelity', 'CRITICAL', t == 'OWNER_APPROVED_ASSET',
                                   f'template status {t}'))
                if p['kind'] == 'lil_dr_byrd':
                    checks.append((f'asset_fidelity.mascot:{u}', 'asset_fidelity', 'CRITICAL',
                                   bool(rec.get('mascot')) and not rec.get('blocked_assets'),
                                   f'mascot {rec.get("mascot")}, blocked {rec.get("blocked_assets")}'))
        return self._finish(job, checks, {'state': state, 'visual': visual}, log)

    def _finish(self, job, checks, extra, log):
        state = extra.get('state') or {'academic': [], 'findings': [], 'types': []}
        ptype = job.get('product_type') or 'UNKNOWN'
        if (Path(job['candidate']).suffix.lower() == '.zip' and
                any(c[0].startswith('asset_fidelity') for c in checks)):
            ptype = 'BUILT_POWER_TOOL' if 'power_tool' in state['types'] else 'BUILT_EXPLAINER'
        attested = {a['item'] for a in job.get('attestations', [])}
        unverified = [r for r in state['academic'] if r['status'] not in (academic.CORRECT, academic.INCORRECT)]
        attestable = [r for r in unverified if r['status'] != 'PENDING_OWNER_DECISION']
        n_att = len([r for r in attestable if _item_key(r) in attested]) + (len(attestable) if 'ALL' in attested else 0)
        n_att = min(n_att, len(unverified))
        if 'ALL' in attested and (not state['academic'] or
                                  not any(r['status'] == 'PENDING_OWNER_DECISION' for r in state['academic'])):
            checks.append(('academic.owner_attested', 'academic', 'CRITICAL', True, 'owner attested academic review'))
        for a in job.get('attestations', []):
            checks.append((f'owner_attestation:{a["item"][:40]}', 'attestation', 'INFO', True, a.get('note', '')))
        result = score(checks, ptype, self.settings['repair']['quality_target'], len(unverified), n_att)
        pending = [r for r in unverified if r['status'] == 'PENDING_OWNER_DECISION']
        if pending:
            result['reasons'].insert(0, f'{len(pending)} image finding(s) need your decision '
                                        f'(tab 2: Review Image Findings…)')
        result['image_findings'] = [f for f in state['findings'] if f.get('image_item')]
        result['image_review'] = {rel: {'pages': v['pages'], 'stats': v['stats'], 'engine': v['engine'],
                                        'items': [{k: i.get(k) for k in ('id', 'page', 'status', 'kind', 'statement',
                                                                         'expected', 'reason', 'alternative_reading')}
                                                  for i in v['items']]}
                                  for rel, v in state.get('image_review', {}).items()}
        result['unverified_items'] = [{'key': _item_key(r), 'file': r.get('file'), 'question': r.get('question'),
                                       'status': r['status'], 'evidence': r['evidence']} for r in unverified]
        result['open_findings'] = state['findings']
        result['visual'] = extra.get('visual', {})
        result['browser'] = state.get('browser')
        result['evaluated_at'] = utcnow()
        result['product_type_scored_as'] = ptype
        write_json(self.root / 'jobs' / job['id'] / 'qa' / 'qa_result.json', result)
        log.info(ROLE_QA, f'QA decision {result["decision"]}', score=result['score'], reasons=result['reasons'][:10])
        return result


def _replay_mismatches(orig, cand, fresh_dir, job):
    import copy
    state = {k: v for k, v in orig.items() if v is not None}
    replaced = {}
    snaps = {0: (copy.deepcopy(state), {})}
    cps = {c['id']: c['history_len'] for c in job.get('checkpoints', [])}
    problems = []
    for i, h in enumerate(job.get('history', []), 1):
        if 'rollback_to' in h:
            s0, r0 = snaps.get(cps.get(h['rollback_to'], 0), snaps[0])
            state, replaced = copy.deepcopy(s0), dict(r0)
        elif h.get('replace_file'):
            replaced[h['file']] = h['after_sha256']
        elif h.get('file') in state:
            if state[h['file']].count(h['find']) != 1:
                problems.append(f'history replay failed at {h["file"]}')
            else:
                state[h['file']] = state[h['file']].replace(h['find'], h['replace'], 1)
        snaps[i] = (copy.deepcopy(state), dict(replaced))
    for rel, text in state.items():
        if cand.get(rel) is not None and cand[rel] != text:
            problems.append(rel)
    for rel, h in replaced.items():
        if (fresh_dir / rel).exists() and sha256(fresh_dir / rel) != h:
            problems.append(rel)
    return problems


def describe_fix(fx):
    if not fx:
        return None
    if fx.get('type') == 'pdf_text':
        return f'Page {fx["page"]}: replace "{fx["find"]}" with "{fx["replace"]}" ({fx["reason"]})'
    return f'{fx["file"]}: change `{fx["find"][:80]}` to `{fx["replace"][:80]}` ({fx["reason"]})'


def correction_lifecycle(baseline, job, qa):
    """Per-defect state: DETECTED/SUSPECTED -> PROPOSED -> APPLIED -> VERIFIED (or REVERTED /
    NOT_AUTO_FIXABLE / STILL_OPEN). VERIFIED requires that Release QA's fresh re-test no longer finds it."""
    applied, reverted = {}, set()
    for it in job.get('iterations', []):
        keys = [tuple(a['key']) for a in it['applied'] if a.get('key')]
        if it.get('rolled_back'):
            reverted.update(keys)
        else:
            for a in it['applied']:
                if a.get('key'):
                    applied[tuple(a['key'])] = a
    still_open = {tuple(map(str, _fkey(f))) for f in qa.get('open_findings', [])}
    out = []
    for f in baseline:
        k = tuple(map(str, _fkey(f)))
        if k in applied and k not in still_open:
            state = 'VERIFIED' if qa.get('decision') in ('PASS', 'NOT_VERIFIED', 'BELOW_TARGET', 'BLOCKED') else 'APPLIED'
        elif k in applied:
            state = 'APPLIED_BUT_STILL_FAILING'
        elif k in reverted:
            state = 'REVERTED_REGRESSION'
        elif f.get('fix'):
            state = 'PROPOSED_NOT_APPLIED'
        elif k in still_open:
            state = 'NOT_AUTO_FIXABLE' if f['severity'] != 'INFO' else 'SUSPECTED'
        else:
            state = 'RESOLVED_BY_RELATED_FIX'
        if state == 'VERIFIED' and job.get('status') == 'AWAITING_OWNER_APPROVAL':
            state = 'VERIFIED_AWAITING_OWNER_APPROVAL'
        out.append({'severity': f['severity'], 'check': f['check'], 'file': f.get('file'), 'detail': f['detail'],
                    'proposed_correction': describe_fix(f.get('fix')), 'state': state})
    return out


def _item_key(r):
    return f'{r.get("file")}|{r.get("page") or r.get("line")}|{(r.get("question") or "")[:60]}'
