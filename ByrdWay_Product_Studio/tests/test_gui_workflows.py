"""Real GUI end-to-end tests: drive the actual Tk window by invoking its buttons, with only the
operating-system dialogs (file pickers / yes-no boxes) answered automatically.
Skipped when tkinter or a display is unavailable (runs on Windows CI and Linux+Xvfb)."""
import json, os, sys, tempfile, time, unittest, warnings
from pathlib import Path
from unittest import mock
warnings.filterwarnings('ignore')
sys.path.insert(0, str(Path(__file__).parent))

try:
    import tkinter
    _r = tkinter.Tk()
    _r.destroy()
    HAVE_TK = True
except Exception:
    HAVE_TK = False

from browsertest import playwright_available
BROWSER = playwright_available()


@unittest.skipUnless(HAVE_TK, 'tkinter/display not available')
class GuiBase(unittest.TestCase):
    def setUp(self):
        import app as appmod
        self.appmod = appmod
        self.t = tempfile.TemporaryDirectory()
        self.d = Path(self.t.name)
        self.app = appmod.App(self.d / 'ws')
        self.opened = []
        self.app.opener = lambda p: self.opened.append(Path(p))
        self.errors = []
        self.app.report_callback_exception = lambda *a: self.errors.append(a)
        self.shown = []
        self.patches = [
            mock.patch.object(appmod.messagebox, 'showinfo', side_effect=lambda *a, **k: self.shown.append(('info',) + a)),
            mock.patch.object(appmod.messagebox, 'showerror', side_effect=lambda *a, **k: self.shown.append(('error',) + a)),
            mock.patch.object(appmod.messagebox, 'askyesno', return_value=True),
            mock.patch.object(appmod.messagebox, 'askokcancel', return_value=True),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        try:
            self.app.destroy()
        except Exception:
            pass
        import gc
        gc.collect()
        for p in self.d.rglob('*'):
            try:
                os.chmod(p, 0o777 if p.is_dir() else 0o666)
            except OSError:
                pass
        self.t.cleanup()
        self.assertEqual(self.errors, [], 'a button raised an unhandled exception')

    def pump(self, timeout=300):
        end = time.time() + timeout
        self.app.update()
        while self.app.busy and time.time() < end:
            self.app.update()
            time.sleep(0.03)
        for _ in range(5):
            self.app.update()
            time.sleep(0.03)
        self.assertFalse(self.app.busy, 'background operation did not finish')

    def pick(self, path):
        return mock.patch.object(self.appmod.filedialog, 'askopenfilename', return_value=str(path))

    def ask(self, *answers):
        return mock.patch.object(self.appmod.simpledialog, 'askstring', side_effect=list(answers))

    def errors_shown(self):
        return [s for s in self.shown if s[0] == 'error']


class ProductsAndJobs(GuiBase):
    @unittest.skipUnless(BROWSER, 'Chromium not installed')
    def test_import_diagnose_repair_review_approve_export(self):
        import fixtures
        from engine import sha256
        z = fixtures.broken_power_tool_zip(self.d / 'Fractions_Power_Tool.zip')
        h = sha256(z)
        with self.pick(z):
            self.app.import_one()
        pid = self.app.ptree.selection()[0]
        self.assertIn('Fractions_Power_Tool.zip', self.app.ptree.item(pid)['values'])
        # Diagnose (read-only) -> readable report opened, nothing changed
        self.app.diagnose()
        self.pump()
        self.assertEqual(self.opened[-1].name, 'diagnosis.html')
        html = self.opened[-1].read_text(encoding='utf-8')
        self.assertIn('Wrong answer', html)
        self.assertIn('Proposed correction', html)
        self.assertEqual(self.app.studio.jobs(), [], 'diagnosis must not start a repair')
        # Repair a copy & verify -> jobs tab, report opened
        self.app.run_job()
        self.pump()
        self.assertEqual(str(self.app.nb.select()), str(self.app.jobs_frame))
        self.assertEqual(self.opened[-1].name, 'report.html')
        rep = self.opened[-1].read_text(encoding='utf-8')
        self.assertIn('VERIFIED', rep)
        self.assertIn('BEFORE (original)', rep)
        jid = self.app.jtree.selection()[0]
        self.assertIn('NEXT STEP', self.app.jtext.get('1.0', '2.0'))
        # Open latest report from products tab
        self.app.nb.select(self.app.products_frame)
        self.app.open_latest_report()
        self.assertEqual(self.opened[-1].name, 'report.html')
        # Jobs tab buttons
        self.app.open_job_report()
        self.app.open_evidence()
        self.assertTrue(self.opened[-1].is_dir())
        self.app.show_diff()
        self.app.rerun_qa()
        self.pump()
        with self.ask('Dr. Byrd'):
            self.app.approve()
        self.assertEqual(self.app.studio.job(jid)['status'], 'APPROVED')
        with mock.patch.object(self.appmod.filedialog, 'askdirectory', return_value=''):
            self.app.export()
        j = self.app.studio.job(jid)
        self.assertEqual(j['status'], 'EXPORTED')
        from release import verify_export
        self.assertEqual(verify_export(j['export']['dir']), [])
        from engine import original_file
        src, _ = original_file(self.app.studio.root, pid)
        self.assertEqual(sha256(src), h, 'original unchanged after the whole GUI workflow')
        self.assertEqual(self.errors_shown(), [])

    def test_release_gate_blocks_and_reject_works(self):
        p = self.d / 'runtime_bug.html'
        p.write_text('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>t</title></head><body>'
                     '<button onclick="go()">Go</button><script>function go(){ missingThing.x(); }</script></body></html>')
        with self.pick(p):
            self.app.import_one()
        self.app.run_job()
        self.pump()
        jid = self.app.jtree.selection()[0]
        self.assertNotEqual(self.app.studio.job(jid)['status'], 'AWAITING_OWNER_APPROVAL')
        n = len(self.errors_shown())
        with self.ask('Owner'):
            self.app.approve()
        self.assertEqual(len(self.errors_shown()), n + 1, 'approval of a non-passing job must be refused visibly')
        self.assertNotEqual(self.app.studio.job(jid)['status'], 'APPROVED')
        with mock.patch.object(self.appmod.filedialog, 'askdirectory', return_value=''):
            self.app.export()
        self.assertNotEqual(self.app.studio.job(jid)['status'], 'EXPORTED')
        with self.ask('needs a developer'):
            self.app.reject()
        self.assertEqual(self.app.studio.job(jid)['status'], 'REJECTED')

    def test_bad_import_is_explained_and_logged(self):
        bad = self.d / 'not_really.pdf'
        bad.write_text('hello')
        with self.pick(bad):
            self.app.import_one()
        self.assertEqual(self.errors_shown()[-1][1], 'Import blocked')
        self.app.refresh_logs()
        self.assertIn('Import blocked', self.app.actbox.get('1.0', 'end'))
        self.assertEqual(self.app.ptree.get_children(), ())

    def test_buttons_without_selection_explain_instead_of_failing(self):
        for fn in (self.app.diagnose, self.app.run_job, self.app.open_latest_report, self.app.open_job_report,
                   self.app.show_diff, self.app.rerun_qa, self.app.approve, self.app.reject, self.app.export,
                   self.app.build_next, self.app.open_unit, self.app.approve_unit, self.app.reject_unit,
                   self.app.assemble, self.app.bp_edit_build, self.app.audit):
            n = len(self.shown)
            fn()
            self.assertEqual(len(self.shown), n + 1, f'{fn.__name__} gave no explanation')

    def test_every_button_is_wired(self):
        from tkinter import ttk
        found = []

        def walk(w):
            for c in w.winfo_children():
                if isinstance(c, ttk.Button):
                    found.append((c.cget('text'), str(c.cget('command'))))
                walk(c)
        walk(self.app)
        self.assertGreaterEqual(len(found), 25)
        self.assertEqual([t for t, cmd in found if not cmd], [], 'button without a command')


class Builders(GuiBase):
    def _editor_fill(self, ed, title, practice, concept='Ratio :: A comparison of two quantities by division'):
        ed.vars['product_title'].set(title)
        ed.vars['subject'].set('Math 7')
        ed.vars['grade'].set('7')
        ed.texts['concepts'].insert('1.0', concept)
        ed.texts['practice'].insert('1.0', practice)

    def test_new_blueprint_validation_errors_are_shown_and_nothing_is_built(self):
        self.app.bp_new()
        ed = self.app.editor
        self._editor_fill(ed, 'Ratios', 'What is 3 × 4')            # missing ":: answer"
        ed.save(True)
        self.assertIn('practice line 1', ed.msg.cget('text'))
        self.assertEqual(self.app.studio.builds(), [])
        ed.destroy()

    def test_draft_save_and_resume(self):
        self.app.bp_new()
        ed = self.app.editor
        self._editor_fill(ed, 'Ratios draft', 'What is 3 × 4 :: 12')
        ed.save(False)
        drafts = list((self.app.studio.root / 'blueprints' / 'drafts').glob('*.json'))
        self.assertEqual(len(drafts), 1)
        with self.pick(drafts[0]):
            self.app.bp_open()
        ed2 = self.app.editor
        self.assertEqual(ed2.vars['product_title'].get(), 'Ratios draft')
        self.assertIn('12', ed2.texts['practice'].get('1.0', 'end'))
        ed2.save(True)
        self.assertEqual(len(self.app.studio.builds()), 1)

    @unittest.skipUnless(BROWSER, 'Chromium not installed')
    def test_power_tool_from_form_to_verified_release_candidate(self):
        self.app.bp_new()
        ed = self.app.editor
        self._editor_fill(ed, 'Ratios Power Tool', 'What is 3 × 4 :: 12\nSolve 2x + 1 = 9 :: x = 4\n'
                                                   'What is 10 ÷ 2 :: 4 | 5 | 6 :: 5')
        ed.add_unit('Module 2')
        ed.texts['practice'].insert('1.0', 'What is 9 + 6 :: 15')
        ed.save(True)
        bid = self.app.btree.selection()[0]
        self.assertIn('✖  Approved ByrdWay page template registered', self.app.prereq_box.get('1.0', 'end'))
        tpl = self.d / 'byrdway.html'
        tpl.write_text('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
                       'content="width=device-width, initial-scale=1"><title>{{TITLE}}</title></head><body>'
                       '{{CONTENT}}{{SCRIPT}}</body></html>')
        with self.pick(tpl):
            self.app.register_template()
        self.app.btree.selection_set(bid)
        self.app.refresh_prereqs()
        self.assertIn('✔  Approved ByrdWay page template registered', self.app.prereq_box.get('1.0', 'end'))
        for unit_no in range(2):
            self.app.btree.selection_set(bid)
            self.app.build_next()
            self.pump()
            unit = self.app.btree.selection()[0]
            self.assertIn('::', unit, f'selection did not move to the built unit; messages={self.shown[-3:]}; '
                                      f'units={ {u: x["status"] for u, x in self.app.studio.builds()[0]["units"].items()} }')
            self.app.open_unit()
            self.assertEqual(self.opened[-1].name, 'index.html')
            self.app.approve_unit()
        self.app.btree.selection_set(bid)
        self.app.assemble()
        self.pump()
        jid = self.app.jtree.selection()[0]
        job = self.app.studio.job(jid)
        self.assertEqual(job['qa']['decision'], 'PASS', job['qa']['reasons'])
        self.assertEqual(self.errors_shown(), [])

    def test_wrong_answer_in_form_blocks_unit_with_clear_message(self):
        self.app.bp_new()
        ed = self.app.editor
        self._editor_fill(ed, 'Bad answers', 'What is 3 × 4 :: 13')
        ed.save(True)
        bid = self.app.btree.selection()[0]
        self.app.build_next()
        self.pump()
        self.app.approve_unit()
        self.assertIn('mathematically wrong', self.errors_shown()[-1][2])

    def test_sample_is_labelled_and_blocked(self):
        self.app.kind_var.set('power_tool')
        self.app.bp_sample()
        ed = self.app.editor
        self.assertTrue(ed.sample.get())
        ed.save(True)
        b = self.app.studio.builds()[0]
        self.assertTrue(b['sample'])
        self.assertIn('SAMPLE', b['summary'])
        self.assertIn('✖  Content is owner material', self.app.prereq_box.get('1.0', 'end'))

    def test_lil_dr_byrd_missing_mascot_then_registered(self):
        import fixtures
        self.app.kind_var.set('lil_dr_byrd')
        self.app.bp_new()
        ed = self.app.editor
        ed.texts['sections'].insert('1.0', '## Speed\nSpeed is distance per time.\nKEY: v = d / t\n'
                                    'EXAMPLE: A cart rolls 100 m in 5 s. Speed? :: v = d/t; v = 100/5 :: 20 m/s :: '
                                    'v = d/t ; d = 100 m, t = 5 s ; v')
        ed.texts['practice'].insert('1.0', 'Force on 2 kg at 3 m/s^2? :: 6 N :: F = m*a ; m = 2 kg, a = 3 m/s^2 ; F')
        ed.save(True)
        bid = self.app.btree.selection()[0]
        self.assertIn('✖  Approved Lil Dr. Byrd image registered', self.app.prereq_box.get('1.0', 'end'))
        self.app.build_next()
        self.pump()
        self.app.approve_unit()
        self.assertIn('not registered', self.errors_shown()[-1][2])
        png = self.d / 'LilDrByrd.png'
        png.write_bytes(fixtures.png_bytes())
        with self.pick(png):
            self.app.register_mascot()
        self.app.btree.selection_set(bid)
        self.app.build_next()
        self.pump()
        self.app.approve_unit()
        st = self.app.studio.builds()[0]
        self.assertEqual(st['units']['ch01']['status'], 'OWNER_APPROVED')


class SettingsBackupHelp(GuiBase):
    def test_limits_and_ai_status(self):
        txt = self.app.cost_lbl.cget('text')
        self.assertIn('AI processing: DISABLED', txt)
        self.app.vars[('budget', 'max_job_usd')].set('999')
        self.app.save_limits()
        self.assertEqual(self.errors_shown()[-1][1], 'Invalid')
        self.app.vars[('budget', 'max_job_usd')].set('0.25')
        self.app.save_limits()
        self.assertEqual(self.app.studio.settings()['budget']['max_job_usd'], 0.25)

    def test_backup_and_restore(self):
        import fixtures
        with self.pick(fixtures.broken_power_tool_zip(self.d / 't.zip')):
            self.app.import_one()
        self.app.backup()
        self.pump()
        bk = list((self.app.studio.root / 'backups').glob('byrdway_backup_*.zip'))
        self.assertEqual(len(bk), 1)
        with self.pick(bk[0]):
            self.app.restore()
        self.pump()
        self.assertEqual(len(self.app.studio.products()), 1)
        self.assertEqual(self.app.studio.products()[0]['integrity'], 'OK')

    def test_help_selftest_and_version(self):
        from version import __version__
        self.assertIn(__version__, self.app.title())
        self.app.run_selftest()
        self.pump()
        kind, title, text = self.shown[-1][:3]
        self.assertEqual(title, 'Self-test')
        self.assertIn(__version__, text)
        if BROWSER:
            self.assertIn('PASSED', text)


if __name__ == '__main__':
    unittest.main()
