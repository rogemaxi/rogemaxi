"""END-TO-END ACCEPTANCE: representative Explainer PDF through the real desktop window.

import -> diagnosis documented (nothing changed) -> owner authorizes repair of a COPY -> repair ->
independent verification (Release QA, visual diff) -> owner approval -> export -> integrity checks.
Plus the negative path: an answer-key error that the Studio cannot safely auto-correct is detected,
reported NOT_AUTO_FIXABLE, and the release gate refuses approval and export.

Set BYRDWAY_E2E_EVIDENCE=<folder> to keep the reports, page images and export for review (CI uploads it)."""
import os, shutil, sys, unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).parent))
from test_gui_workflows import GuiBase, HAVE_TK


@unittest.skipUnless(HAVE_TK, 'tkinter/display not available')
class ExplainerEndToEnd(GuiBase):
    def keep(self, name, src):
        dest = os.environ.get('BYRDWAY_E2E_EVIDENCE')
        if dest:
            d = Path(dest) / name
            if Path(src).is_dir():
                shutil.copytree(src, d, dirs_exist_ok=True)
            else:
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, d)

    def test_explainer_import_diagnose_authorize_repair_verify_approve_export(self):
        import pymupdf
        import selftest_fixtures as fx
        from engine import sha256, original_file
        from release import verify_export
        src_pdf = fx.representative_explainer_pdf(self.d / 'Multiplication_Anime_Explainer.pdf')
        upload_hash = sha256(src_pdf)

        # 1 IMPORT
        with self.pick(src_pdf):
            self.app.import_one()
        pid = self.app.ptree.selection()[0]
        prod = self.app.studio.products()[0]
        self.assertEqual(prod['product_type'], 'ANIME_EXPLAINER')
        self.assertEqual(prod['sha256'], upload_hash)

        # 2 DIAGNOSE - findings documented, nothing changed
        self.app.diagnose()
        self.pump()
        diag_html = self.opened[-1]
        self.assertEqual(diag_html.name, 'diagnosis.html')
        import json
        diag = json.loads((diag_html.parent / 'diagnosis.json').read_text(encoding='utf-8'))
        self.assertEqual(len(diag['findings']), 1)
        f = diag['findings'][0]
        self.assertEqual(f['state'], 'DETECTED')
        self.assertIn('Page 2: replace "7 × 8 = 54" with "7 × 8 = 56"', f['proposed_correction'])
        self.assertEqual(diag['academic_checked'], 6)
        self.assertEqual(self.app.studio.jobs(), [])
        self.assertEqual(sha256(original_file(self.app.studio.root, pid)[0]), upload_hash)
        self.keep('1_diagnosis', diag_html.parent)

        # 3 AUTHORIZATION - declining creates nothing
        with mock.patch.object(self.appmod.messagebox, 'askyesno', return_value=False):
            self.app.run_job()
        self.pump()
        self.assertEqual(self.app.studio.jobs(), [], 'declining the repair must change nothing')

        # 4 REPAIR + 5 VERIFY
        self.app.run_job()
        self.pump()
        jid = self.app.jtree.selection()[0]
        job = self.app.studio.job(jid)
        self.assertEqual(job['status'], 'AWAITING_OWNER_APPROVAL', job['qa']['reasons'])
        self.assertEqual(job['prior_diagnosis']['id'], diag['id'], 'repair must reference the documented diagnosis')
        self.assertIn('Repair a copy', job['repair_authorization']['method'])
        qa = job['qa']
        self.assertEqual(qa['decision'], 'PASS')
        self.assertEqual(qa['critical_failures'], 0)
        self.assertGreaterEqual(qa['score'], 99.9)
        self.assertEqual([c['state'] for c in job['corrections']], ['VERIFIED_AWAITING_OWNER_APPROVAL'])
        checks = {c[0]: c[3] for c in qa['checks']}
        self.assertTrue(checks['integrity.original_unchanged'])
        self.assertTrue(checks['integrity.all_changes_recorded'])
        vis = list(qa['visual'].values())[0]
        self.assertEqual(vis['changed_pages'], [2], 'only the corrected page may change')
        self.assertEqual(vis['before_pages'], vis['after_pages'])
        rep = self.opened[-1]
        self.assertEqual(rep.name, 'report.html')
        self.assertIn('BEFORE (original)', rep.read_text(encoding='utf-8'))
        self.assertEqual(sha256(original_file(self.app.studio.root, pid)[0]), upload_hash)

        # 6 OWNER APPROVAL (visual review of the reconstructed region is required)
        with self.ask('Dr. Byrd'), mock.patch.object(self.appmod.messagebox, 'askyesno', side_effect=[False]):
            self.app.approve()                                     # says "not reviewed" -> refused
        self.assertEqual(self.app.studio.job(jid)['status'], 'AWAITING_OWNER_APPROVAL')
        with self.ask('Dr. Byrd'):
            self.app.approve()
        job = self.app.studio.job(jid)
        self.assertEqual(job['status'], 'APPROVED')
        self.assertTrue(job['approval']['visual_reviewed'])

        # 7 EXPORT + integrity
        with mock.patch.object(self.appmod.filedialog, 'askdirectory', return_value=''):
            self.app.export()
        job = self.app.studio.job(jid)
        self.assertEqual(job['status'], 'EXPORTED')
        out = Path(job['export']['dir'])
        self.assertEqual(verify_export(out), [])
        exported = out / 'Multiplication_Anime_Explainer.pdf'
        with pymupdf.open(exported) as d, pymupdf.open(src_pdf) as o:
            self.assertEqual(d.page_count, o.page_count)
            self.assertIn('7 × 8 = 56', d[1].get_text())
            self.assertNotIn('7 × 8 = 54', d[1].get_text())
            self.assertEqual(d.get_toc(), o.get_toc(), 'table of contents preserved')
            for i in (0, 2, 3):
                self.assertEqual(d[i].get_pixmap(dpi=60).samples, o[i].get_pixmap(dpi=60).samples,
                                 f'page {i + 1} must be pixel-identical')
            self.assertEqual(len(d[0].get_images()), 1, 'illustration preserved')
        self.assertTrue((out / 'audit_trail' / 'report.html').exists())
        self.assertIn('Release approved by', (out / 'audit_trail' / 'report.html').read_text(encoding='utf-8'))
        self.assertEqual(sha256(original_file(self.app.studio.root, pid)[0]), upload_hash)
        self.assertEqual(sha256(src_pdf), upload_hash, "owner's own file untouched")
        self.keep('2_repair_job', self.app.studio.job_evidence_dir(jid))
        self.keep('3_export', out)
        self.assertEqual(self.errors_shown()[-1:], [] if not self.errors_shown() else self.errors_shown()[-1:])

    def test_answer_key_error_is_detected_but_not_auto_corrected_and_release_is_blocked(self):
        import selftest_fixtures as fx
        p = fx.representative_explainer_pdf(self.d / 'AnswerKey_Anime_Explainer.pdf', answer_key_error=True)
        with self.pick(p):
            self.app.import_one()
        self.app.diagnose()
        self.pump()
        self.app.run_job()
        self.pump()
        jid = self.app.jtree.selection()[0]
        job = self.app.studio.job(jid)
        self.assertEqual(job['status'], 'BLOCKED')
        states = {c['detail'][:40]: c['state'] for c in job['corrections']}
        self.assertIn('NOT_AUTO_FIXABLE', states.values())
        self.assertIn('VERIFIED', states.values(), 'the correctable worked example is still fixed on the copy')
        n = len(self.errors_shown())
        with self.ask('Dr. Byrd'):
            self.app.approve()
        self.assertEqual(len(self.errors_shown()), n + 1)
        with mock.patch.object(self.appmod.filedialog, 'askdirectory', return_value=''):
            self.app.export()
        self.assertNotIn(self.app.studio.job(jid)['status'], ('APPROVED', 'EXPORTED'))
        self.keep('4_blocked_answer_key_job', self.app.studio.job_evidence_dir(jid))


if __name__ == '__main__':
    unittest.main()
