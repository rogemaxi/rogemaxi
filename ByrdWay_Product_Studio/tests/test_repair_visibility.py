"""Incident 2026-11-18 (owner screenshot): '12 findings, 11 correctable automatically, 0 need a person' and a repair
that looked stalled. Root causes: (1) an INFO finding was in no class; (2) OCR-read corrections were labeled
'automatic' although the repair job (correctly) waits for the owner's confirmation; (3) page-reading progress was not
passed to the repair run or to Release QA (65-s silences) and the job ended without a terminal summary/next step."""
import os
import sys
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest import mock

warnings.filterwarnings('ignore')
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import imageread  # noqa: E402
import orchestrator  # noqa: E402

OCR = imageread.available()


class Accounting(unittest.TestCase):
    def test_every_finding_in_exactly_one_class_and_totals_reconcile(self):
        F = [{'id': 'P001', 'severity': 'INFO', 'check': 'pdf.image_only', 'proposed_correction': None},
             {'id': 'a', 'severity': 'CRITICAL', 'check': 'image.math_error', 'image_item': True, 'proposed_correction': 'y = 8/3'},
             {'id': 'b', 'severity': 'MINOR', 'check': 'image.typo', 'proposed_correction': 'Rating'},
             {'id': 'c', 'severity': 'MAJOR', 'check': 'js.error', 'proposed_correction': 'patch'},
             {'id': 'd', 'severity': 'MAJOR', 'check': 'html.missing_alt', 'proposed_correction': None}]
        c = orchestrator.classify_findings(F)
        self.assertEqual(c, {'auto_fixable': 1, 'needs_owner_confirmation': 2, 'needs_person': 1, 'informational': 1})
        self.assertEqual(sum(c.values()), len(F))
        self.assertEqual([f['classification'] for f in F],
                         ['informational', 'needs_owner_confirmation', 'needs_owner_confirmation', 'auto_fixable', 'needs_person'])
        line = orchestrator.accounting_line({'findings': F, **c})
        self.assertIn('5 findings = 1 correctable automatically + 2 need your confirmation', line)
        self.assertIn('1 need a person + 1 informational', line)


class Base(unittest.TestCase):
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


@unittest.skipUnless(OCR, 'page reader (rapidocr-onnxruntime) not installed')
class ImageExplainerRepairVisibility(Base):
    def _prep(self):
        import selftest_fixtures as fx
        from controller import Studio
        from engine import sha256
        p = fx.image_only_explainer_pdf(self.d / 'Signs_Anime_Explainer.pdf')
        h = sha256(p)
        s = Studio(self.ws)
        m = s.import_product(p)
        return s, m, p, h

    def test_diagnosis_reconciles_and_ocr_corrections_need_confirmation(self):
        s, m, p, h = self._prep()
        d = s.diagnose(m['id'], run_browser=False)
        n = len(d['findings'])
        self.assertEqual(d['auto_fixable'] + d['needs_owner_confirmation'] + d['needs_person'] + d['informational'], n)
        self.assertEqual(d['auto_fixable'], 0, 'nothing read from a page image is labeled automatic')
        self.assertGreaterEqual(d['needs_owner_confirmation'], 3)
        self.assertGreaterEqual(d['informational'], 1)
        html = (self.ws / 'reports' / d['id'] / 'diagnosis.html').read_text(encoding='utf-8')
        self.assertIn('need your confirmation first', html)
        self.assertNotIn('can be corrected automatically', html)

    def test_repair_reports_every_stage_page_progress_and_terminal_next_step(self):
        from engine import sha256
        s, m, p, h = self._prep()
        msgs = []
        j = s.run_job(m['id'], run_browser=False, progress=msgs.append)
        text = '\n'.join(msgs)
        for stage in ('Stage 1/4', 'Stage 2/4', 'Stage 3/4', 'Stage 4/4', 'RESULT '):
            self.assertIn(stage, text)
        self.assertGreater(sum('Reading page' in x for x in msgs), 1, 'page progress during baseline AND Release QA')
        sm = j['summary']
        self.assertEqual(sm['terminal'], 'WAITING FOR YOUR CONFIRMATION')
        self.assertEqual(sm['applied'], 0)
        self.assertEqual(sm['attempted'], sm['applied'] + sm['failed'])
        self.assertEqual(sm['total_findings'], sm['auto_fixable'] + sm['needs_owner_confirmation'] + sm['needs_person'] + sm['informational'])
        self.assertIn('Review Image Findings', sm['next_step'])
        self.assertNotEqual(j['status'], 'AWAITING_OWNER_APPROVAL', 'unverified copy is never shown as ready')
        self.assertEqual(sha256(p), h)
        from engine import original_file
        self.assertEqual(sha256(original_file(self.ws, m['id'])[0]), h)

    def test_confirmed_repair_reaches_success_with_independent_verification(self):
        s, m, p, h = self._prep()
        j = s.run_job(m['id'], run_browser=False)
        for it in s.image_findings(j['id']):
            s.decide_image_finding(j['id'], it['id'], 'confirmed', 'Owner',
                                   replacement='equation' if it['kind'] == 'typo' else None)
        msgs = []
        j2 = s.repair_image_findings(j['id'], 'Owner', True, progress=msgs.append)
        self.assertTrue(any('Stage 4/4' in x for x in msgs))
        sm = j2['summary']
        self.assertGreater(sm['applied'], 0)
        self.assertEqual(sm['verification'], j2['qa']['decision'])
        self.assertIn(sm['terminal'], ('SUCCESS', 'PARTIAL'))
        if j2['qa']['decision'] == 'PASS':
            self.assertEqual(j2['status'], 'AWAITING_OWNER_APPROVAL')


class DuplicateDispatch(unittest.TestCase):
    def test_second_repair_while_one_runs_is_refused(self):
        try:
            import tkinter
            tkinter.Tk().destroy()
        except Exception:
            self.skipTest('no display')
        import app as appmod
        with tempfile.TemporaryDirectory() as t, mock.patch.object(appmod.messagebox, 'showinfo') as info:
            a = appmod.App(Path(t) / 'ws')
            try:
                import threading
                gate = threading.Event()
                a.run_bg('Repair & verify', lambda: gate.wait(5))
                a.run_bg('Repair & verify', lambda: None)          # pressed again
                info.assert_called_once()
                self.assertEqual(info.call_args[0][0], 'Busy')
                a._poll()
                self.assertIn('running', a.status.get())
                gate.set()
            finally:
                a.destroy()


if __name__ == '__main__':
    unittest.main()


class PreviewPatchHonesty(unittest.TestCase):
    def test_image_patch_needs_visual_approval_and_flags_lines_still_using_old_value(self):
        bl = [{'id': 'p8-a', 'check': 'image.math_error', 'severity': 'CRITICAL', 'image_item': 'p8-a', 'page': 8,
               'file': 'X.pdf', 'statement': '320+400 = 760', 'expected': '720', 'proposal': 'use 720',
               'fix': {'type': 'image_patch'}},
              {'id': 'p3-t', 'check': 'image.typo', 'severity': 'MINOR', 'image_item': 'p3-t', 'page': 3,
               'file': 'X.pdf', 'proposal': 'Rating', 'fix': {'type': 'image_patch'}}]
        job = {'iterations': [{'applied': [{'finding': 'p8-a'}], 'rejected': [{'finding': 'p3-t', 'error': 'spelling: the owner must type the correct word'}]},
                              {'applied': [], 'rejected': [{'finding': 'p3-t', 'error': 'spelling: the owner must type the correct word'}]}],
               'qa': {'decision': 'NOT_VERIFIED', 'open_findings': [{'id': 'p3-t'}],
                      'image_review': {'X.pdf': {'pages': {'8': {'transcript': ['320+400 = 760', '8a+5s=760', 'a+s=120']}}}}}}
        r = orchestrator.repair_summary(job, bl, 10)
        self.assertEqual((r['attempted'], r['applied'], r['failed']), (2, 1, 1), 'each finding counted once')
        self.assertEqual(r['terminal'], 'PARTIAL')
        self.assertIn('type the correct word', r['next_step'])
        self.assertIn('preview quality', r['next_step'])
        self.assertIn('Canva', r['next_step'])
        self.assertEqual(r['consistency_review'][0]['lines'], ['8a+5s=760'])
