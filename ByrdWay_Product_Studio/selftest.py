"""End-to-end self-test of the installed or packaged application.

Runs the real pipeline (import -> repair -> independent verification -> Release QA
-> approval gate -> export integrity -> original preservation) on products with
deliberately planted defects, in a throw-away workspace. No network, no API calls.

  python app.py --selftest          (or ByrdWayStudio.exe --selftest)
Exit code 0 = every check passed. A JSON report is printed and saved.
"""
import json, sys, tempfile, time, traceback
from pathlib import Path


def run(report_path=None, browser=True):
    import selftest_fixtures as fx
    from engine import import_product, sha256, original_file
    from orchestrator import Orchestrator
    from release import owner_approve, export_approved, verify_export
    from browsertest import playwright_available
    results, t0 = [], time.time()

    def check(name, ok, detail=''):
        results.append({'check': name, 'passed': bool(ok), 'detail': str(detail)[:300]})

    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        ws = d / 'ws'
        try:
            have_browser = browser and playwright_available()
            check('browser_engine_available', have_browser,
                  'Chromium ready' if have_browser else 'Use Help → Install browser engine (or ByrdWayStudio.exe --install-browser)')
            z = fx.broken_power_tool_zip(d / 'SelfTest_Power_Tool.zip')
            h = sha256(z)
            m = import_product(z, ws)
            job = Orchestrator(ws).run_repair_job(m['id'], run_browser=have_browser)
            qa = job.get('qa') or {}
            fixed = {a['check'] for it in job.get('iterations', []) for a in it['applied']}
            for c in ('academic.wrong_answer', 'js.undefined_handler', 'assets.missing', 'nav.anchor', 'a11y.lang'):
                check(f'power_tool_repaired:{c}', c in fixed)
            br = qa.get('browser') or {}
            if have_browser:
                check('browser_tests_executed', br.get('available') and br.get('load_ok'),
                      br.get('unavailable_reason') or br.get('harness_errors') or 'ok')
            check('power_tool_release_qa_pass', qa.get('decision') == 'PASS' if have_browser else
                  qa.get('decision') == 'NOT_VERIFIED', f'{qa.get("decision")} {qa.get("score")} {qa.get("reasons")}')
            src, _ = original_file(ws, m['id'])
            check('original_byte_identical_after_repair', sha256(src) == h)
            if qa.get('decision') == 'PASS':
                try:
                    owner_approve(ws, job['id'], 'selftest', explicit_approval=False)
                    check('approval_requires_explicit_owner', False)
                except PermissionError:
                    check('approval_requires_explicit_owner', True)
                owner_approve(ws, job['id'], 'Self-test', explicit_approval=True)
                out = export_approved(ws, job['id'], d / 'export')
                check('export_integrity', verify_export(out) == [])
                check('original_byte_identical_after_export', sha256(src) == h)
            p = fx.explainer_pdf(d / 'SelfTest_Anime_Explainer.pdf')
            pm = import_product(p, ws)
            pj = Orchestrator(ws).run_repair_job(pm['id'], run_browser=False)
            check('pdf_wrong_claim_corrected', pj.get('qa', {}).get('decision') == 'PASS',
                  pj.get('qa', {}).get('reasons'))
            import imageread
            if imageread.available():
                ip = fx.image_only_explainer_pdf(d / 'SelfTest_Flattened_Explainer.pdf')
                rv = imageread.review_pdf(ip)
                errs = {i['statement'] for i in rv['items'] if i['status'] == imageread.STATUS_ERR}
                check('image_pdf_reader_finds_planted_error', '7 × 8 = 54' in errs, sorted(errs))
                cp = fx.image_only_explainer_pdf(d / 'SelfTest_Flattened_Clean.pdf', with_errors=False)
                rc = imageread.review_pdf(cp)
                check('image_pdf_reader_no_false_accusation', rc['stats']['SUSPECTED_ERROR'] == 0
                      and rc['stats']['VERIFIED_CORRECT'] >= 5, rc['stats'])
            else:
                check('image_pdf_reader_available', False, 'page reader (OCR) not installed')
            bad = d / 'evil.zip'
            import zipfile
            with zipfile.ZipFile(bad, 'w') as zz:
                zz.writestr('../evil.txt', 'x')
            try:
                import_product(bad, ws)
                check('malicious_zip_rejected', False)
            except ValueError:
                check('malicious_zip_rejected', True)
        except Exception as e:
            check('selftest_crashed', False, f'{type(e).__name__}: {e}\n{traceback.format_exc(limit=4)}')
    from version import __version__
    rep = {'version': __version__, 'passed': all(r['passed'] for r in results), 'checks': results,
           'seconds': round(time.time() - t0, 1), 'python': sys.version.split()[0], 'platform': sys.platform}
    if report_path:
        Path(report_path).write_text(json.dumps(rep, indent=2), encoding='utf-8')
    return rep


def main():
    rep = run(Path.cwd() / 'selftest_report.json')
    print(json.dumps(rep, indent=2))
    return 0 if rep['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
