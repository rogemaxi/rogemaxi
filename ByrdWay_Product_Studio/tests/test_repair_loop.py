"""Core repair engine + quality loop: detect -> repair -> verify -> QA, with
browser evidence, regression rollback, no-progress / iteration / runtime stops,
critical-defect blocking, approval authorization and export integrity."""
import os, stat, sys, tempfile, unittest, warnings, zipfile
from pathlib import Path
warnings.filterwarnings('ignore')
sys.path.insert(0, str(Path(__file__).parent))
import fixtures
import orchestrator
from browsertest import playwright_available
from config import load_settings, save_settings
from engine import import_product, sha256, original_file
from orchestrator import Orchestrator
from release import owner_approve, owner_reject, export_approved, verify_export, attest
from quality import score

BROWSER = playwright_available()


class LoopBase(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.d = Path(self.t.name)
        self.ws = self.d / 'ws'

    def tearDown(self):
        for p in self.d.rglob('*'):
            try:
                os.chmod(p, 0o777 if p.is_dir() else 0o666)
            except OSError:
                pass
        self.t.cleanup()

    def settings(self, **repair):
        s = load_settings(self.ws)
        s['repair'].update(repair)
        save_settings(self.ws, s)
        return s


@unittest.skipUnless(BROWSER, 'Playwright not installed')
class EndToEndPowerTool(LoopBase):
    def test_broken_fails_before_and_passes_after_with_browser_evidence(self):
        z = fixtures.broken_power_tool_zip(self.d / 'tool.zip')
        upload_hash = sha256(z)
        m = import_product(z, self.ws)
        job = Orchestrator(self.ws).run_repair_job(m['id'])
        # BEFORE: baseline found every planted defect, including the real browser exception
        jd = self.ws / 'jobs' / job['id']
        import json
        base = json.loads((jd / 'baseline_findings.json').read_text())
        checks = {f['check'] for f in base}
        for expected in ('academic.wrong_answer', 'js.undefined_handler', 'assets.missing', 'nav.anchor',
                         'a11y.lang', 'browser.js_exception'):
            self.assertIn(expected, checks)
        self.assertTrue((jd / 'evidence' / 'baseline_desktop.png').exists())
        # AFTER: independent QA re-test of the repacked candidate passes, zero critical
        qa = job['qa']
        self.assertEqual(qa['decision'], 'PASS', qa['reasons'])
        self.assertEqual(qa['critical_failures'], 0)
        self.assertGreaterEqual(qa['score'], 99.9)
        qa_checks = {c[0]: c[3] for c in qa['checks']}
        self.assertTrue(qa_checks['browser.no_js_exceptions'])
        self.assertTrue(qa_checks['integrity.protected_assets_unchanged'])
        self.assertTrue((jd / 'qa' / 'evidence' / 'qa_desktop.png').exists())
        with zipfile.ZipFile(job['candidate']) as zc:
            js = zc.read('quiz.js').decode()
        self.assertIn('answer: "56"', js)
        self.assertIn('correct: 1', js)
        # originals byte-identical after import + repair
        src, _ = original_file(self.ws, m['id'])
        self.assertEqual(sha256(src), upload_hash)
        self.assertEqual(sha256(z), upload_hash)
        # approval authorization
        with self.assertRaises(PermissionError):
            owner_approve(self.ws, job['id'], 'Owner', explicit_approval=False)
        with self.assertRaises(PermissionError):
            export_approved(self.ws, job['id'])
        owner_approve(self.ws, job['id'], 'Dr. Byrd', explicit_approval=True)
        out = export_approved(self.ws, job['id'])
        self.assertEqual(verify_export(out), [])
        self.assertTrue((out / 'audit_trail' / 'REPORT.md').exists())
        self.assertEqual(sha256(src), upload_hash, 'original intact after export')
        # tampering with an export is detected
        with open(out / 'tool.zip', 'ab') as f:
            f.write(b'x')
        self.assertTrue(verify_export(out))

    def test_candidate_tamper_after_qa_blocks_approval(self):
        m = import_product(fixtures.broken_power_tool_zip(self.d / 'tool.zip'), self.ws)
        job = Orchestrator(self.ws).run_repair_job(m['id'])
        with open(job['candidate'], 'ab') as f:
            f.write(b'tamper')
        with self.assertRaises(PermissionError):
            owner_approve(self.ws, job['id'], 'Owner', True)

    def test_unfixable_runtime_error_blocks_release(self):
        html = ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
                'content="width=device-width, initial-scale=1"><title>t</title></head><body>'
                '<button onclick="go()">Go</button><script>function go(){ scoreBoard.total += 1; }</script>'
                '<script>var items=[{q:"What is 2 + 2?", answer:"4"}];</script></body></html>')
        p = self.d / 'runtime_bug.html'
        p.write_text(html)
        m = import_product(p, self.ws)
        job = Orchestrator(self.ws).run_repair_job(m['id'])
        self.assertEqual(job['status'], 'BLOCKED')
        self.assertEqual(job['stop_reason'], 'UNFIXABLE_DEFECTS_REQUIRE_HUMAN')
        self.assertTrue(any('scoreBoard' in r for r in job['qa']['reasons']))
        self.assertTrue(job['escalations'])
        with self.assertRaises(PermissionError):
            owner_approve(self.ws, job['id'], 'Owner', True)
        owner_reject(self.ws, job['id'], 'Owner', 'needs developer')
        self.assertEqual(Orchestrator(self.ws).load_job(job['id'])['status'], 'REJECTED')


class LoopControls(LoopBase):
    """These run without a browser so loop logic is tested deterministically."""

    def _import(self):
        return import_product(fixtures.broken_power_tool_zip(self.d / 'tool.zip'), self.ws)['id']

    def _persistent_fix(self, monkey_detect):
        real = orchestrator.detect_all

        def fake(settings, site_dir, shots_dir, label, run_browser=True):
            st = real(settings, site_dir, shots_dir, label, False)
            st['findings'].append({'id': 'X1', 'check': 'fake.persistent', 'severity': 'MAJOR', 'category': 't',
                                   'file': 'index.html', 'detail': 'never goes away',
                                   'fix': {'file': 'index.html', 'find': 'repeated addition.',
                                           'replace': 'repeated addition. ', 'reason': 'no-op'}})
            return st
        orchestrator.detect_all = fake
        self.addCleanup(setattr, orchestrator, 'detect_all', real)

    def test_no_progress_detection(self):
        self.settings(max_iterations=10, no_progress_limit=2)
        pid = self._import()
        self._persistent_fix(True)
        job = Orchestrator(self.ws).run_repair_job(pid, run_browser=False)
        self.assertEqual(job['stop_reason'], 'NO_PROGRESS')
        self.assertLess(len(job['iterations']), 10)

    def test_iteration_limit(self):
        self.settings(max_iterations=1)
        pid = self._import()
        self._persistent_fix(True)
        job = Orchestrator(self.ws).run_repair_job(pid, run_browser=False)
        self.assertEqual(job['stop_reason'], 'ITERATION_LIMIT')
        self.assertEqual(len(job['iterations']), 1)

    def test_runtime_limit(self):
        s = self.settings(max_runtime_seconds=10)
        pid = self._import()
        self._persistent_fix(True)
        import time
        real_time = time.time
        start = real_time()
        calls = {'n': 0}

        def fake_time():
            calls['n'] += 1
            return start + (0 if calls['n'] < 3 else 1000)
        orchestrator.time.time = fake_time
        self.addCleanup(setattr, orchestrator.time, 'time', real_time)
        job = Orchestrator(self.ws).run_repair_job(pid, run_browser=False)
        self.assertEqual(job['stop_reason'], 'RUNTIME_LIMIT')

    def test_regression_triggers_rollback_and_escalation(self):
        self.settings(max_iterations=4, repeat_failure_limit=2)
        pid = self._import()
        real = orchestrator.detect_all

        def fake(settings, site_dir, shots_dir, label, run_browser=True):
            st = real(settings, site_dir, shots_dir, label, False)
            # a "repair" that deletes the checkAnswer function -> regression
            if 'function checkAnswer' in (Path(site_dir) / 'quiz.js').read_text():
                st['findings'].append({'id': 'R1', 'check': 'bad.fix', 'severity': 'MINOR', 'category': 't',
                                       'file': 'quiz.js', 'detail': 'tempting but harmful',
                                       'fix': {'file': 'quiz.js', 'find': 'function checkAnswer()',
                                               'replace': 'function removedAnswer()', 'reason': 'harmful'}})
            return st
        orchestrator.detect_all = fake
        self.addCleanup(setattr, orchestrator, 'detect_all', real)
        job = Orchestrator(self.ws).run_repair_job(pid, run_browser=False)
        rolled = [i for i in job['iterations'] if i.get('rolled_back')]
        self.assertTrue(rolled, 'regression must be rolled back')
        self.assertTrue(rolled[0]['regressions'] or rolled[0]['new_defects'])
        self.assertTrue(job['escalations'])
        with zipfile.ZipFile(job['candidate']) as z:
            self.assertIn('function checkAnswer()', z.read('quiz.js').decode())

    def test_missing_browser_means_not_verified(self):
        pid = self._import()
        job = Orchestrator(self.ws).run_repair_job(pid, run_browser=False)
        self.assertEqual(job['qa']['decision'], 'NOT_VERIFIED')
        self.assertIsNone(job['qa']['score'], 'no score may be claimed without coverage')
        self.assertIn('browser_runtime', job['qa']['missing_required_categories'])

    def test_qa_detects_unrecorded_change(self):
        """Release QA is independent: a silent edit to the candidate is caught."""
        pid = self._import()
        o = Orchestrator(self.ws)
        job = o.run_repair_job(pid, run_browser=False)
        cand = Path(job['candidate'])
        tmp = self.d / 'silent.zip'
        with zipfile.ZipFile(cand) as zi, zipfile.ZipFile(tmp, 'w') as zo:
            for n in zi.namelist():
                data = zi.read(n)
                if n == 'index.html':
                    data = data.replace(b'repeated addition', b'repeated subtraction')
                zo.writestr(n, data)
        os.replace(tmp, cand)
        job['candidate_sha256'] = sha256(cand)
        from orchestrator import ReleaseQAAgent
        qa = ReleaseQAAgent(self.ws, o.settings).evaluate(job, run_browser=False)
        failed = {c[0] for c in qa['failed']}
        self.assertIn('integrity.all_changes_recorded', failed)
        self.assertEqual(qa['decision'], 'BLOCKED')


class PdfLoop(LoopBase):
    def test_wrong_claim_repaired_with_visual_evidence(self):
        p = fixtures.explainer_pdf(self.d / 'Multiplication_Anime_Explainer.pdf')
        h = sha256(p)
        m = import_product(p, self.ws)
        self.assertEqual(m['product_type'], 'ANIME_EXPLAINER')
        job = Orchestrator(self.ws).run_repair_job(m['id'])
        self.assertEqual(job['qa']['decision'], 'PASS', job['qa']['reasons'])
        ch = [h2 for h2 in job['history'] if h2.get('replace_file')]
        self.assertEqual(ch[0]['evidence']['changed_pages'], [2])
        self.assertTrue(ch[0]['evidence']['change_confined_to_region'])
        import pdftools
        texts = pdftools.page_texts(job['candidate'])
        self.assertIn('7 × 8 = 56', texts[1])
        self.assertNotIn('= 54', texts[1])
        with self.assertRaises(PermissionError):
            owner_approve(self.ws, job['id'], 'Owner', True)                 # visual review required
        owner_approve(self.ws, job['id'], 'Owner', True, visual_reviewed=True)
        src, _ = original_file(self.ws, m['id'])
        self.assertEqual(sha256(src), h)

    def test_image_only_pdf_is_not_verified_and_never_rewritten(self):
        p = fixtures.explainer_pdf(self.d / 'Scanned_Concept_Tiles.pdf', image_only=True)
        m = import_product(p, self.ws)
        job = Orchestrator(self.ws).run_repair_job(m['id'])
        self.assertEqual(job['qa']['decision'], 'NOT_VERIFIED')
        self.assertEqual(job['changes']['changed'], [])
        # owner attestation is the only path, and it is recorded
        j = attest(self.ws, job['id'], 'ALL', 'Dr. Byrd', 'Reviewed every tile against answer key by hand')
        self.assertEqual(j['qa']['decision'], 'PASS')
        self.assertTrue(any(c[0].startswith('owner_attestation') for c in j['qa']['checks']))

    def test_flattened_page_correction_refused(self):
        import pdftools
        p = fixtures.explainer_pdf(self.d / 'scan.pdf', image_only=True)
        with self.assertRaises(pdftools.FlattenedPageError):
            pdftools.propose_text_correction(p, self.d / 'o.pdf', 1, '7', '8', self.d / 'w')


class Scoring(unittest.TestCase):
    def test_weighted_average_never_hides_critical(self):
        checks = [(f'c{i}', 'integrity', 'MINOR', True, '') for i in range(5000)]
        checks.append(('crit', 'integrity', 'CRITICAL', False, 'wrong answer'))
        r = score(checks, 'UNKNOWN')
        self.assertGreater(r['raw_score'], 99.7)
        self.assertEqual(r['decision'], 'BLOCKED')

    def test_missing_coverage_is_not_verified(self):
        r = score([('a', 'integrity', 'CRITICAL', True, '')], 'POWER_TOOL')
        self.assertEqual(r['decision'], 'NOT_VERIFIED')
        self.assertIsNone(r['score'])

    def test_minor_failure_below_target(self):
        cats = ['integrity', 'html_structure', 'functionality', 'assets', 'browser_runtime', 'academic']
        checks = [(c, c, 'CRITICAL', True, '') for c in cats] + [('m', 'responsive', 'MINOR', False, '')]
        r = score(checks, 'POWER_TOOL')
        self.assertEqual(r['decision'], 'BELOW_TARGET')

    def test_unverified_academic_items(self):
        cats = ['integrity', 'html_structure', 'functionality', 'assets', 'browser_runtime', 'academic']
        checks = [(c, c, 'CRITICAL', True, '') for c in cats]
        self.assertEqual(score(checks, 'POWER_TOOL', academic_unverified=1)['decision'], 'NOT_VERIFIED')
        self.assertEqual(score(checks, 'POWER_TOOL', academic_unverified=1, attested=1)['decision'], 'PASS')

    def test_reproducible(self):
        checks = [('a', 'integrity', 'MAJOR', True, ''), ('b', 'x', 'MINOR', False, '')]
        self.assertEqual(score(checks, 'UNKNOWN'), score(list(checks), 'UNKNOWN'))


if __name__ == '__main__':
    unittest.main()
