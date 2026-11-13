"""Desktop UI smoke test: builds every tab, drives import -> job -> QA view.
Skipped automatically when tkinter or a display is unavailable.
Linux CI: xvfb-run -a python -m unittest tests.test_ui_smoke"""
import os, sys, tempfile, time, unittest, warnings
from pathlib import Path
warnings.filterwarnings('ignore')
sys.path.insert(0, str(Path(__file__).parent))

try:
    import tkinter
    _r = tkinter.Tk()
    _r.destroy()
    HAVE_TK = True
except Exception:
    HAVE_TK = False


@unittest.skipUnless(HAVE_TK, 'tkinter/display not available')
class UISmoke(unittest.TestCase):
    def test_app_end_to_end(self):
        import fixtures
        from unittest import mock
        import app as appmod
        from app import App
        with tempfile.TemporaryDirectory() as t, \
                mock.patch.object(appmod.messagebox, 'askyesno', return_value=True):   # answer "Repair a copy?"
            app = App(Path(t) / 'ws')
            app.opener = lambda p: None
            try:
                self.assertEqual(app.nb.index('end'), 9)
                self.assertEqual(str(app.nb.select()), str(app.cc), 'Command Center opens first')
                self.assertEqual(len(app.cc.data['engineering']), 12)
                self.assertEqual(len(app.cc.data['revenue']), 10)
                cards = [w for g in app.cc.grid_frame.winfo_children() for w in g.winfo_children() if isinstance(w, appmod.tk.Frame)
                         and w.winfo_children()]
                self.assertGreaterEqual(len(cards), 22)
                z = fixtures.broken_power_tool_zip(Path(t) / 'tool.zip')
                m = app.studio.import_product(z)
                app.refresh_products()
                self.assertIn(m['id'], app.ptree.get_children())
                app.ptree.selection_set(m['id'])
                app.run_job()
                deadline = time.time() + 240
                while app.busy and time.time() < deadline:
                    app.update()
                    time.sleep(0.05)
                self.assertFalse(app.busy, 'job did not finish')
                app.update()
                jobs = app.jtree.get_children()
                self.assertEqual(len(jobs), 1)
                app.cc.refresh()
                self.assertEqual(dict(app.cc.data['kpis'])['Products protected'], 1)
                self.assertEqual(dict(app.cc.data['kpis'])['Repair jobs'], 1)
                self.assertNotEqual(app.cc.data['engineering'][5]['last'], 'no action yet')   # Release QA acted
                app.jtree.selection_set(jobs[0])
                app.show_job()
                text = app.jtext.get('1.0', 'end')
                self.assertIn('Release QA', text)
                self.assertIn('PASS', text)
                app.refresh_all()
                shot = os.environ.get('BYRDWAY_UI_SHOT')
                if shot:
                    app.nb.select(app.jobs_frame)
                    app.update()
                    time.sleep(0.5)
                    app.update()
                    from PIL import ImageGrab
                    ImageGrab.grab(bbox=(app.winfo_rootx(), app.winfo_rooty(),
                                         app.winfo_rootx() + app.winfo_width(),
                                         app.winfo_rooty() + app.winfo_height())).save(shot)
            finally:
                app.destroy()
                import gc
                gc.collect()


if __name__ == '__main__':
    unittest.main()
