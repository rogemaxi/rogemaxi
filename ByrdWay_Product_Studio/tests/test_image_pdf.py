"""v0.5.0/v0.6.0: reading and verifying IMAGE-ONLY (flattened) PDFs, including every worked step.
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

    def test_worked_steps_every_step_checked(self):
        p = fx.image_only_explainer_pdf(self.d / 'f.pdf')
        rv = imageread.review_pdf(p, crop_dir=self.d / 'crops')
        steps = [i for i in rv['items'] if i['kind'] == 'worked step']
        bad = [i for i in steps if i['status'] == imageread.STATUS_ERR]
        self.assertEqual([i['statement'] for i in bad], ['4x + 12 - 2x = 2x + 14'])
        self.assertEqual(bad[0]['page'], 3)
        self.assertEqual(bad[0]['expected'], '2x + 12')
        self.assertTrue(Path(bad[0]['crop']).exists())
        self.assertIn('2x + 12', bad[0]['proposal'])
        ok = {i['statement'] for i in steps if i['status'] == imageread.STATUS_OK}
        for s in ('f(5) = 3(5) + 2', '15 + 2 = 17', '320 + 400 = 720'):
            self.assertIn(s, ok, 'a correct step (incl. a function value) must verify')
        self.assertEqual(rv['stats']['coverage']['pages'], 3)
        self.assertEqual(rv['stats']['coverage']['pages_unverified'], 0)
        self.assertTrue(all(v['status'] for v in rv['pages'].values()), 'every page gets an explicit status')
        pg = rv['pages'][3]
        self.assertGreaterEqual(pg['verified'], 5)
        self.assertTrue(any('Simplify' in t for t in pg['transcript']), 'full page text is kept for the report')

    def test_step_readings_do_not_hide_or_invent_errors(self):
        same = lambda a, b: any(imageread._same(x, y) for _, x in imageread._term_readings(a, {})
                                for _, y in imageread._term_readings(b, {}))
        self.assertTrue(same('(3x2)3', '27x6'), 'lost superscripts')
        self.assertTrue(same('7.500,000', '7.5×106'), 'scientific notation with OCR separators')
        self.assertTrue(same('(2x)2 - 52', '4x2-25'))
        self.assertFalse(same('4x + 12 - 2x', '2x + 14'), 'a 1-based power reading must not hide an error')
        self.assertFalse(same('320+400', '760'))
        self.assertEqual(imageread._term_readings('Area of the garden', {}), [], 'prose is not math')

    def test_text_layer_patterns_never_accused(self):
        # flattened exponents, percents, thousands separators, contradictions and run-on statements in extracted text
        lines = ['Join powers: 105 × 10-8 = 105 - 8 = 10-3', 'Answer: 3 × 105 = 300,000', 'Check: 1.8/9 = 0.20 = 20%',
                 'Subtract the equations: 0 = 5', '(−3)(−3)(−3)(−3) = 81', 'Evaluate g(2). g(2) = (2)² + 1 (2)² = 4 = 5',
                 '2001 - 12 = 40,000 - 1 = 39,999', 'Simplify: 3(x + 2) - x', '= 3x + 6 - x', '= 2x + 6']
        ln = [{'text': t, 'conf': 1.0, 'rect': (100, 20 * i, 500, 20 * i + 14)} for i, t in enumerate(lines)]
        items = imageread.check_worked_steps(ln, ln) + [
            {'status': st, 'statement': f'{l} = {r}'} for x in ln for st, l, r, _, _ in imageread.check_line(x)]
        bad = [i['statement'] for i in items if i['status'] == imageread.STATUS_ERR]
        self.assertEqual(bad, [], 'correct text must never be accused')
        self.assertTrue(any(i['statement'].startswith('3x + 6 - x') and i['status'] == imageread.STATUS_OK for i in items))
        wrong = [{'text': t, 'conf': 1.0, 'rect': (100, 20 * i, 500, 20 * i + 14)} for i, t in
                 enumerate(['Simplify: 3(x + 2) - x', '= 3x + 6 - x', '= 2x + 8', 'Check: 1.8/9 = 0.25'])]
        bad = [i['statement'] for i in imageread.check_worked_steps(wrong, wrong) if i['status'] == imageread.STATUS_ERR]
        bad += [f'{l} = {r}' for x in wrong for st, l, r, _, _ in imageread.check_line(x) if st == imageread.STATUS_ERR]
        self.assertEqual(sorted(set(bad)), ['1.8/9 = 0.25', '3x + 6 - x = 2x + 8'], 'real errors are still caught')

    def test_solving_steps_equations_and_inequalities(self):
        def run(texts):
            ln = [{'text': t, 'conf': 0.95, 'rect': (100, 22 * i, 300, 22 * i + 14)} for i, t in enumerate(texts)]
            return imageread.check_relation_chains(ln, ln)
        ok = run(['3(x - 2) + 5 ≤ 14', '3x - 1 ≤ 14', '3x ≤ 15', 'x ≤ 5'])
        self.assertEqual([f['status'] for f in ok], [imageread.STATUS_OK] * 3)
        ok = run(['x2 - 4x - 5 = 0', '(x + 1)(x - 5) = 0', 'x = -1   x = 5'])
        self.assertEqual([f['status'] for f in ok], [imageread.STATUS_OK] * 2, 'lost superscript + two solutions')
        bad = run(['2x + 7 > 15', '2x > 8', 'x > 3'])
        self.assertEqual([f['status'] for f in bad][-1], imageread.STATUS_ERR, 'wrong final inequality is caught')
        self.assertIn('4', bad[-1]['expected'])
        self.assertEqual(run(['b > 1', '0 < b < 1']), [], 'parallel statements are not solving steps')
        part = run(['(x - 8)(x + 3) = 0', 'x = 8'])
        self.assertEqual(part[0]['status'], imageread.STATUS_UNREADABLE, 'an incomplete reading is never accused')

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
        diag_html = (self.ws / 'reports' / d['id'] / 'diagnosis.html').read_text(encoding='utf-8')
        self.assertIn('Signs_Anime_Explainer.pdf', diag_html)
        self.assertIn('Page-by-page reading', diag_html)
        self.assertIn('4x + 12 - 2x = 2x + 14', diag_html)
        job_html = (self.ws / 'jobs' / j['id'] / 'report.html').read_text(encoding='utf-8')
        self.assertIn('Page-by-page reading', job_html)
        self.assertIn('Full text read on page 3', job_html)
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

    def test_confirmed_errors_repaired_on_copy_reviewed_reverified_then_approved(self):
        import release, pymupdf
        s, m, d, j, h, p = self._job()
        with self.assertRaises(PermissionError):
            s.repair_image_findings(j['id'], 'Owner', True)                   # nothing confirmed yet
        for it in s.image_findings(j['id']):
            s.decide_image_finding(j['id'], it['id'], 'confirmed', 'Owner',
                                   replacement='equation' if it['kind'] == 'typo' else None)
        with self.assertRaises(PermissionError):
            s.repair_image_findings(j['id'], 'Owner', False)                  # explicit authorization required
        j2 = s.repair_image_findings(j['id'], 'Owner', True)
        reviews = j2['repair_reviews']
        self.assertTrue(reviews and all(r['accepted'] for r in reviews), reviews)
        self.assertTrue(all(r['reviewer'].startswith('Repair Reviewer') for r in reviews))
        self.assertEqual(j2['qa'].get('image_findings'), [], 'independent re-diagnosis finds no remaining error')
        self.assertEqual(sha256(original_file(self.ws, m['id'])[0]), h, 'original untouched')
        self.assertEqual(sha256(p), h)
        with pymupdf.open(j2['candidate']) as doc:
            txt = imageread.review_pdf(j2['candidate'])
        self.assertEqual(txt['stats']['SUSPECTED_ERROR'], 0, 'the repaired copy verifies')
        self.assertEqual(txt['stats']['SUSPECTED_TYPO'], 0)
        self.assertTrue(any('2x + 12' == i['statement'].split(' = ', 1)[-1] for i in txt['items']))
        with self.assertRaises(PermissionError):
            s.approve(j2['id'], 'Owner', True)                                # pages not yet confirmed
        j3 = release.attest(self.ws, j2['id'], 'ALL', 'Owner', 'checked every page and every correction')
        self.assertEqual(j3['qa']['decision'], 'PASS', j3['qa']['reasons'])
        with self.assertRaises(PermissionError):
            s.approve(j2['id'], 'Owner', True)                                # reconstructed regions: visual review
        s.approve(j2['id'], 'Owner', True, visual_reviewed=True)
        out = s.export(j2['id'])
        self.assertEqual(release.verify_export(out), [])

    def test_spelling_repair_needs_the_owners_word(self):
        s, m, d, j, h, p = self._job()
        for it in s.image_findings(j['id']):
            s.decide_image_finding(j['id'], it['id'], 'confirmed' if it['kind'] == 'typo' else 'dismissed', 'Owner')
        j2 = s.repair_image_findings(j['id'], 'Owner', True)
        self.assertEqual(j2['changes']['changed'], [], 'no word is guessed on the owner\'s behalf')
        self.assertTrue(any('must type the correct word' in str(x) for it in j2['iterations'] for x in it['rejected']))

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
            before = set(app.studio.jobs() and [x['id'] for x in app.studio.jobs()])
            with mock.patch.object(appmod.simpledialog, 'askstring', return_value='Owner'), \
                    mock.patch.object(appmod.messagebox, 'askyesno', return_value=True):
                app.repair_confirmed()
                t.pump()
            new = [x for x in app.studio.jobs() if x['id'] not in before]
            self.assertEqual(len(new), 1, 'Repair Confirmed on a Copy created one repair job')
            j2 = app.studio.job(new[0]['id'])
            self.assertTrue(any(r['accepted'] for r in j2.get('repair_reviews', [])), j2.get('repair_reviews'))
            self.assertEqual(t.errors, [])
        finally:
            t.tearDown()


if __name__ == '__main__':
    unittest.main()
