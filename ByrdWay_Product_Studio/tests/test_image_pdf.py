"""v0.5.0: reading and verifying IMAGE-ONLY (flattened) PDFs.
Controlled fixtures only (selftest_fixtures.image_only_explainer_pdf) - no owner content."""
import os, sys, tempfile, unittest, warnings
from pathlib import Path
from unittest import mock
warnings.filterwarnings('ignore')
sys.path.insert(0, str(Path(__file__).parent))
import selftest_fixtures as fx
import imageread
from engine import import_product, sha256, original_file

OCR = imageread.available()


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
class Reader(Base):
    def test_planted_errors_found_with_page_and_evidence(self):
        p = fx.image_only_explainer_pdf(self.d / 'f.pdf')
        rv = imageread.review_pdf(p, crop_dir=self.d / 'crops')
        errs = [i for i in rv['items'] if i['status'] == imageread.STATUS_ERR]
        by = {(i['page'], i['statement']): i for i in errs}
        self.assertIn((1, '7 × 8 = 54'), by)
        self.assertEqual(by[(1, '7 × 8 = 54')]['expected'], '56')
        self.assertTrue(any(i['page'] == 2 and i['expected'] == '7' for i in errs), errs)
        typos = [i for i in rv['items'] if i['status'] == 'SUSPECTED_TYPO']
        self.assertEqual([t['shown'] for t in typos], ['equasion'])
        for i in errs + typos:
            self.assertTrue(Path(i['crop']).exists(), 'every finding has picture evidence')
            self.assertEqual(len(i['rect']), 4)
            self.assertTrue(i['proposal'])

    def test_correct_content_is_never_accused(self):
        p = fx.image_only_explainer_pdf(self.d / 'clean.pdf', with_errors=False)
        rv = imageread.review_pdf(p)
        self.assertEqual(rv['stats']['SUSPECTED_ERROR'], 0, rv['items'])
        self.assertEqual(rv['stats']['SUSPECTED_TYPO'], 0, rv['items'])
        ok = [i['statement'] for i in rv['items'] if i['status'] == imageread.STATUS_OK]
        self.assertIn('(-18) ÷ (-3) = 6', ok, 'the ÷-read-as-: trap must verify, not be accused')
        self.assertGreaterEqual(len(ok), 6)

    def test_ocr_confusions(self):
        self.assertIn('3x-5=16', [r.replace(' ', '') for r in imageread._equation_readings('3x : 5=16')])
        self.assertIn('x^2-5x-24=0', imageread._equation_readings('x2-5x-24=0'))
        self.assertIn('3^(2x-1)=3^(3)', imageread._equation_readings('32x-1=33'))
        self.assertEqual(imageread.clean('5+7=12V'), '5+7=12')

    def test_merged_words_are_not_typos_but_misspellings_are(self):
        sp = imageread._spell()
        for w in ('valuethatmakes', 'groupingortrinomials', 'multiplytoacandaddtob', 'factorthegcf'):
            self.assertTrue(imageread._known(w, sp) or imageread._segmentable(w, sp), w)
        for w in ('equasion', 'varible', 'paralel', 'coeficient', 'denominater'):
            self.assertFalse(imageread._known(w, sp) or imageread._segmentable(w, sp), w)

    def test_annotated_review_copy_never_changes_pixels(self):
        p = fx.image_only_explainer_pdf(self.d / 'f.pdf')
        ok = imageread.annotated_review_copy(p, self.d / 'review.pdf', [
            {'page': 1, 'rect': (60, 97, 307, 116), 'id': 'x', 'statement': '7 × 8 = 54', 'correction': '56'}])
        self.assertTrue(ok)
        import pymupdf
        with pymupdf.open(self.d / 'review.pdf') as d:
            self.assertEqual(len(list(d[0].annots())), 1)


@unittest.skipUnless(OCR, 'page reader not installed')
class Workflow(Base):
    def _job(self, with_errors=True):
        from controller import Studio
        s = Studio(self.ws)
        p = fx.image_only_explainer_pdf(self.d / 'Signs_Anime_Explainer.pdf', with_errors=with_errors)
        h = sha256(p)
        m = s.import_product(p)
        d = s.diagnose(m['id'], run_browser=False)
        j = s.run_job(m['id'], run_browser=False)
        return s, m, d, j, h, p

    def test_findings_documented_then_owner_decides_then_correction_sheet(self):
        import release
        s, m, d, j, h, p = self._job()
        img = [f for f in d['findings'] if f.get('image_item')]
        self.assertGreaterEqual(len(img), 3)
        self.assertTrue(all(f['proposed_correction'] and f.get('crop') for f in img))
        self.assertIn('Signs_Anime_Explainer.pdf', (self.ws / 'reports' / d['id'] / 'diagnosis.html').read_text(encoding='utf-8'))
        self.assertEqual(j['status'], 'NOT_VERIFIED')
        self.assertIn('need your decision', j['qa']['reasons'][0])
        self.assertEqual(j['changes']['changed'], [], 'a flattened PDF is never edited')
        # a blanket attestation can NOT clear undecided findings
        j2 = release.attest(self.ws, j['id'], 'ALL', 'Owner', 'looked at it')
        self.assertNotEqual(j2['qa']['decision'], 'PASS')
        items = s.image_findings(j['id'])
        with self.assertRaises(PermissionError):
            s.export_correction_sheet(j['id'], 'Owner', True)            # nothing confirmed yet
        for it in items:
            s.decide_image_finding(j['id'], it['id'], 'confirmed', 'Owner')
        j3 = s.job(j['id'])
        self.assertEqual(j3['qa']['decision'], 'BLOCKED', 'a confirmed error blocks release')
        with self.assertRaises(PermissionError):
            s.approve(j['id'], 'Owner', True)
        with self.assertRaises(PermissionError):
            s.export_correction_sheet(j['id'], 'Owner', False)            # explicit approval required
        out = s.export_correction_sheet(j['id'], 'Owner', True)
        csv = (out / 'corrections.csv').read_text(encoding='utf-8')
        self.assertIn('7 × 8 = 54', csv)
        self.assertTrue(list((out / 'evidence').glob('*.png')))
        self.assertTrue(list(out.glob('*_REVIEW_ANNOTATED.pdf')))
        self.assertEqual(sha256(original_file(self.ws, m['id'])[0]), h)
        self.assertEqual(sha256(p), h)
        from controller import next_action
        self.assertIn('Correction Sheet', next_action(s.job(j['id'])))

    def test_dismissed_misread_then_attested_can_pass(self):
        s, m, d, j, h, p = self._job()
        for it in s.image_findings(j['id']):
            s.decide_image_finding(j['id'], it['id'], 'dismissed', 'Owner')
        import release
        j2 = release.attest(self.ws, j['id'], 'ALL', 'Owner', 'checked every page by eye')
        self.assertEqual(j2['qa']['decision'], 'PASS', j2['qa']['reasons'])

    def test_clean_flattened_pdf_end_to_end_to_export(self):
        import release
        s, m, d, j, h, p = self._job(with_errors=False)
        self.assertEqual([f for f in d['findings'] if f.get('image_item')], [])
        self.assertEqual(j['status'], 'NOT_VERIFIED', 'image pages always need the owner\'s visual confirmation')
        j2 = release.attest(self.ws, j['id'], 'ALL', 'Owner', 'checked both pages')
        self.assertEqual(j2['qa']['decision'], 'PASS', j2['qa']['reasons'])
        s.approve(j['id'], 'Owner', True)
        out = s.export(j['id'])
        self.assertEqual(release.verify_export(out), [])
        self.assertEqual(sha256(out / 'Signs_Anime_Explainer.pdf'), h, 'exported product is the untouched original')


try:
    import tkinter
    _r = tkinter.Tk()
    _r.destroy()
    HAVE_TK = True
except Exception:
    HAVE_TK = False


@unittest.skipUnless(OCR and HAVE_TK, 'page reader or display not available')
class ReviewScreen(unittest.TestCase):
    def test_review_dialog_confirm_dismiss_and_export(self):
        sys.path.insert(0, str(Path(__file__).parent))
        from test_gui_workflows import GuiBase
        t = GuiBase('setUp')
        t.setUp()
        try:
            app, appmod = t.app, t.appmod
            p = fx.image_only_explainer_pdf(t.d / 'Signs_Anime_Explainer.pdf')
            with t.pick(p):
                app.import_one()
            app.run_job()
            t.pump()
            jid = app.jtree.selection()[0]
            self.assertIn('Review Image Findings', app.jtext.get('1.0', '2.0'))
            dlg = app.review_image_findings()
            n = len(dlg.items)
            self.assertGreaterEqual(n, 3)
            self.assertIsNotNone(dlg._img, 'the evidence picture is shown')
            with mock.patch.object(appmod.simpledialog, 'askstring', return_value='Owner'):
                dlg.decide('confirmed')
                for _ in range(n - 1):
                    dlg.decide('dismissed')
            decisions = [i['decision'] for i in app.studio.image_findings(jid)]
            self.assertEqual(decisions.count('confirmed'), 1)
            self.assertEqual(decisions.count('dismissed'), n - 1)
            dlg.destroy()
            with mock.patch.object(appmod.simpledialog, 'askstring', return_value='Owner'):
                app.export_correction_sheet()
            self.assertEqual(t.opened[-1].name, 'correction_sheet.html')
            self.assertEqual(t.errors, [])
        finally:
            t.tearDown()


if __name__ == '__main__':
    unittest.main()
