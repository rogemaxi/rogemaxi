"""v0.4.0: one authoritative version, read-only diagnosis, correction lifecycle,
blueprint form editor conversion, sample-content protection."""
import json, os, re, sys, tempfile, unittest, warnings, zipfile
from pathlib import Path
warnings.filterwarnings('ignore')
HERE = Path(__file__).parent
APP = HERE.parent
sys.path.insert(0, str(HERE))
import fixtures
import builders as B
from version import __version__
from engine import import_product, sha256, original_file
from orchestrator import Orchestrator


class Version(unittest.TestCase):
    def test_single_version_everywhere(self):
        self.assertRegex(__version__, r'^\d+\.\d+\.\d+$')
        for doc in ('README.md', 'USER_GUIDE.md', 'QUALITY_SCORING.md', 'SECURITY_REVIEW.md', 'KNOWN_LIMITATIONS.md',
                    'OWNER_QUICK_START.md', 'PRODUCTION_READINESS_REPORT.md', 'ROOT_CAUSE_REPORT.md'):
            first = (APP / doc).read_text(encoding='utf-8').splitlines()[0]
            self.assertIn(__version__, first, f'{doc} title does not state v{__version__}')
            for v in re.findall(r'\bv(\d+\.\d+(?:\.\d+)?)\b', first):
                self.assertEqual(v, __version__, f'{doc} title names another version')
        src = (APP / 'app.py').read_text(encoding='utf-8')
        self.assertNotRegex(src, r"\| v0\.\d'", 'hard-coded version in app.py')
        for bat in ('install_windows.bat', 'build_windows_exe.bat'):
            self.assertIn('version.py', (APP / bat).read_text(encoding='utf-8'), bat)

    def test_cli_version(self):
        import subprocess
        out = subprocess.run([sys.executable, str(APP / 'app.py'), '--version'], capture_output=True, text=True, cwd=APP)
        self.assertEqual(out.stdout.strip(), __version__)


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


class Diagnosis(Base):
    def test_diagnose_is_read_only_and_states_are_explicit(self):
        z = fixtures.broken_power_tool_zip(self.d / 't.zip')
        m = import_product(z, self.ws)
        o = Orchestrator(self.ws)
        d = o.diagnose(m['id'], run_browser=False)
        self.assertTrue(d['original_intact'])
        self.assertEqual(o.list_jobs(), [])
        self.assertFalse(list((self.ws / 'proposals').rglob('*.zip')), 'diagnosis must not create candidates')
        self.assertFalse(list((self.ws / 'working').iterdir()), 'diagnosis working copy is removed')
        states = {f['state'] for f in d['findings']}
        self.assertEqual(states, {'DETECTED'})
        self.assertEqual(d['proposed_corrections'], 6)
        self.assertTrue(any('answer: "56"' in (f['proposed_correction'] or '') for f in d['findings']))
        html = (self.ws / 'reports' / d['id'] / 'diagnosis.html').read_text(encoding='utf-8')
        self.assertIn('nothing was changed', html)

    def test_suspected_vs_detected(self):
        p = self.d / 'cdn.html'
        p.write_text('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
                     'content="width=device-width, initial-scale=1"><title>t</title>'
                     '<script src="https://cdn.example.com/x.js"></script></head><body><img src="a.png"></body></html>')
        m = import_product(p, self.ws)
        d = Orchestrator(self.ws).diagnose(m['id'], run_browser=False)
        by = {f['check']: f['state'] for f in d['findings']}
        self.assertEqual(by['deps.external'], 'SUSPECTED')
        self.assertEqual(by['a11y.img_alt'], 'DETECTED')
        self.assertIsNone([f for f in d['findings'] if f['check'] == 'a11y.img_alt'][0]['proposed_correction'])

    def test_correction_lifecycle_after_repair(self):
        m = import_product(fixtures.broken_power_tool_zip(self.d / 't.zip'), self.ws)
        job = Orchestrator(self.ws).run_repair_job(m['id'], run_browser=False)
        states = [c['state'] for c in job['corrections']]
        self.assertEqual(len(states), 6)
        self.assertTrue(all(s.startswith('VERIFIED') for s in states), states)
        rep = (self.ws / 'jobs' / job['id'] / 'report.html').read_text(encoding='utf-8')
        self.assertIn('NEXT STEP', rep)
        self.assertIn('Chromium', rep, 'NOT_VERIFIED for missing browser must say how to fix it')

    def test_unfixable_is_reported_not_faked(self):
        p = self.d / 'bug.html'
        p.write_text('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>t</title></head><body>'
                     '<img src="a.png"></body></html>')
        m = import_product(p, self.ws)
        job = Orchestrator(self.ws).run_repair_job(m['id'], run_browser=False)
        c = [x for x in job['corrections'] if x['check'] == 'a11y.img_alt'][0]
        self.assertEqual(c['state'], 'NOT_AUTO_FIXABLE')
        self.assertEqual(job['status'], 'BLOCKED')


class Forms(Base):
    def test_power_tool_form_round_trip_and_errors(self):
        bp = json.loads((APP / 'samples' / 'SAMPLE_power_tool_blueprint.json').read_text(encoding='utf-8'))
        bp2 = B.power_tool_blueprint_from_form(B.form_from_power_tool_blueprint(bp))
        self.assertEqual([q['question'] for q in bp2['modules'][0]['practice']],
                         [q['question'] for q in bp['modules'][0]['practice']])
        with self.assertRaises(B.FormError) as e:
            B.power_tool_blueprint_from_form({'product_title': 'X', 'subject': 'Y',
                                              'modules': [{'title': 'M', 'practice': 'ok :: 1\nbroken line'}]})
        self.assertIn('practice line 2', str(e.exception))
        with self.assertRaises(B.FormError) as e:
            B.power_tool_blueprint_from_form({'product_title': 'X', 'subject': 'Y',
                                              'modules': [{'title': 'M', 'practice': 'Q :: 1 | 2 :: 3'}]})
        self.assertIn('not one of', str(e.exception))

    def test_chapter_form_with_physics_checks(self):
        bp = B.chapter_blueprint_from_form({'subject': 'Physics', 'chapters': [{
            'title': 'Forces', 'sections': '## Newton\nForce changes motion.\nKEY: F = m a\n'
                                           'EXAMPLE: 5 kg at 2 m/s^2? :: F = m a; F = 10 :: 10 N :: F = m*a ; m = 5 kg, a = 2 m/s^2 ; F',
            'practice': 'Force on 2 kg at 3 m/s^2? :: 6 N :: F = m*a ; m = 2 kg, a = 3 m/s^2 ; F'}]})
        ex = bp['chapters'][0]['sections'][0]['worked_examples'][0]
        self.assertEqual(ex['verify']['given'], {'m': '5 kg', 'a': '2 m/s^2'})
        from academic import verify_item
        self.assertEqual(verify_item(ex)['status'], 'CORRECT')
        self.assertEqual(verify_item(bp['chapters'][0]['practice'][0])['status'], 'CORRECT')

    def test_sample_content_blocks_release(self):
        from controller import Studio
        s = Studio(self.ws)
        form = s.sample_form('power_tool')
        self.assertTrue(form['_sample'])
        b = s.create_build_from_form('power_tool', form)
        for u in b.state['order']:
            r = B.build_power_tool_module(self.ws, b.id, u)
            self.assertEqual(r['status'], 'NEEDS_OWNER_REVIEW')
            b.approve(u, owner_confirmed=True, attest_unsupported=True)
        job = s.assemble_and_verify(b.id, run_browser=False)
        self.assertEqual(job['qa']['decision'], 'BLOCKED')
        self.assertTrue(any('owner_content' in r for r in job['qa']['reasons']))

    def test_prerequisites_report_missing_assets(self):
        rows = dict((l, ok) for l, ok, _ in B.prerequisites(self.ws, 'lil_dr_byrd'))
        self.assertFalse(rows['Approved Lil Dr. Byrd image registered'])
        rows = dict((l, ok) for l, ok, _ in B.prerequisites(self.ws, 'power_tool'))
        self.assertFalse(rows['Approved ByrdWay page template registered'])


if __name__ == '__main__':
    unittest.main()
