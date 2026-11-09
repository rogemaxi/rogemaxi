"""Builders (module order, verification, provenance, approved assets only),
Release-QA asset-fidelity blocks, backup/restore, agent coordination, HTML audit coverage."""
import copy, json, os, sys, tempfile, unittest, warnings, zipfile
from pathlib import Path
warnings.filterwarnings('ignore')
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import fixtures
import builders
from assets import register_asset, get_asset
from browsertest import playwright_available, run_browser_tests, browser_checks
from controller import Studio
from engine import import_product, sha256
from htmlaudit import audit_files
from orchestrator import Orchestrator
from release import backup_workspace, verify_backup, restore_backup

SAMPLES = HERE.parent / 'samples'
def _as_owner_content(bp):
    """Test fixture: the sample's format with the SAMPLE marking removed, standing in for owner-approved
    content. (The real sample stays protected - see test_v040.Forms.test_sample_content_blocks_release.)"""
    bp = copy.deepcopy(bp)
    bp.pop('_notice', None)
    for k in ('product_title', 'series'):
        if k in bp:
            bp[k] = bp[k].replace('SAMPLE ', 'Test ')
    for c in bp.get('chapters', []):
        c['title'] = c['title'].replace('SAMPLE ', 'Test ')
    return bp


PT = _as_owner_content(json.loads((SAMPLES / 'SAMPLE_power_tool_blueprint.json').read_text(encoding='utf-8')))
LDB = _as_owner_content(json.loads((SAMPLES / 'SAMPLE_lil_dr_byrd_physics_blueprint.json').read_text(encoding='utf-8')))


class Base(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.d = Path(self.t.name)
        self.ws = self.d / 'ws'
        self.studio = Studio(self.ws)

    def tearDown(self):
        for p in self.d.rglob('*'):
            try:
                os.chmod(p, 0o777 if p.is_dir() else 0o666)
            except OSError:
                pass
        self.t.cleanup()


class PowerToolBuilder(Base):
    def test_blueprint_validation(self):
        with self.assertRaises(ValueError):
            builders.Build.create(self.ws, {'product_title': 'x', 'subject': 'y', 'modules': [{'id': 'A B'}]}, 'power_tool')

    def test_module_order_and_approval(self):
        b = builders.Build.create(self.ws, PT, 'power_tool')
        with self.assertRaises(PermissionError):
            builders.build_power_tool_module(self.ws, b.id, 'm2-variables-both-sides')
        u = builders.build_power_tool_module(self.ws, b.id, 'm1-one-step')
        self.assertEqual(u['status'], builders.APPROVAL_READY)
        self.assertEqual(u['incorrect'], 0)
        self.assertTrue(all(r['status'] == 'CORRECT' for r in u['verification']))
        self.assertEqual(u['template']['template_status'], 'PROVISIONAL_UNAPPROVED')
        prov = json.loads((b.dir / 'modules' / 'm1-one-step' / 'provenance.json').read_text())
        self.assertTrue(all(i['provenance'] == 'owner_blueprint' for i in prov['items']))
        with self.assertRaises(PermissionError):
            b.approve('m1-one-step', owner_confirmed=False)
        b.approve('m1-one-step', owner_confirmed=True)
        u2 = builders.build_power_tool_module(self.ws, b.id, 'm2-variables-both-sides')
        self.assertEqual(u2['status'], builders.APPROVAL_READY)

    def test_wrong_answer_blocks_module(self):
        bp = copy.deepcopy(PT)
        bp['modules'][0]['practice'][0]['answer'] = 'x = 5'
        b = builders.Build.create(self.ws, bp, 'power_tool')
        u = builders.build_power_tool_module(self.ws, b.id, 'm1-one-step')
        self.assertEqual(u['status'], 'BLOCKED_ACADEMIC_DEFECT')
        with self.assertRaises(PermissionError):
            b.approve('m1-one-step', owner_confirmed=True)

    def test_ai_drafted_content_requires_owner_review(self):
        bp = copy.deepcopy(PT)
        bp['modules'][0]['practice'][0]['source'] = 'ai_draft:gpt-6.1-terra'
        b = builders.Build.create(self.ws, bp, 'power_tool')
        u = builders.build_power_tool_module(self.ws, b.id, 'm1-one-step')
        self.assertEqual(u['status'], 'NEEDS_OWNER_REVIEW')
        with self.assertRaises(PermissionError):
            b.approve('m1-one-step', owner_confirmed=True)
        b.approve('m1-one-step', owner_confirmed=True, attest_unsupported=True)

    def test_html_escaping_of_blueprint_content(self):
        bp = copy.deepcopy(PT)
        bp['modules'][0]['concepts'][0]['title'] = '<script>alert(1)</script>'
        b = builders.Build.create(self.ws, bp, 'power_tool')
        u = builders.build_power_tool_module(self.ws, b.id, 'm1-one-step')
        html = Path(u['output']).read_text()
        self.assertNotIn('<script>alert(1)</script>', html)

    @unittest.skipUnless(playwright_available(), 'Playwright not installed')
    def test_built_module_works_in_browser_and_scores(self):
        b = builders.Build.create(self.ws, PT, 'power_tool')
        u = builders.build_power_tool_module(self.ws, b.id, 'm1-one-step')
        out = Path(u['output'])
        r = run_browser_tests(out.parent, 'index.html', self.d / 'shots', 'built')
        self.assertTrue(all(c[3] for c in browser_checks(r)), browser_checks(r))
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            try:
                br = p.chromium.launch()
            except Exception:
                br = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
            pg = br.new_page()
            pg.goto(out.as_uri())
            pg.fill('#a0', '4')
            pg.click('#practice .card:nth-of-type(1) button')
            self.assertIn('Correct', pg.inner_text('#f0'))
            pg.fill('#a1', '7')
            pg.click('#practice .card:nth-of-type(2) button')
            self.assertIn('Not yet', pg.inner_text('#f1'))
            self.assertIn('Score: 1 / 3', pg.inner_text('#bw-score'))
            pg.check('input[name="q2"][value="1"]')
            pg.click('#practice .card:nth-of-type(3) button')
            self.assertIn('Score: 2 / 3', pg.inner_text('#bw-score'))
            pg.click('text=Finish')
            self.assertIn('two-step', pg.inner_text('#bw-pathway'))
            br.close()

    @unittest.skipUnless(playwright_available(), 'Playwright not installed')
    def test_provisional_template_blocks_release_and_approved_template_passes(self):
        def run(bp):
            b = builders.Build.create(self.ws, bp, 'power_tool')
            for u in b.state['order']:
                builders.build_power_tool_module(self.ws, b.id, u)
                b.approve(u, owner_confirmed=True)
            m = self.studio.assemble_and_import(b.id, True)
            return Orchestrator(self.ws).run_repair_job(m['id'])
        job = run(PT)
        self.assertEqual(job['qa']['decision'], 'BLOCKED')
        self.assertTrue(any('asset_fidelity.template' in r for r in job['qa']['reasons']))
        tpl = self.d / 'byrdway_template.html'
        tpl.write_text('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
                       'content="width=device-width, initial-scale=1"><title>{{TITLE}}</title></head>'
                       '<body class="byrdway">{{CONTENT}}{{SCRIPT}}</body></html>')
        register_asset(self.ws, tpl, 'byrdway_template', 'template', owner_confirmed=True)
        bp = copy.deepcopy(PT)
        bp['template_asset_id'] = 'byrdway_template'
        job2 = run(bp)
        self.assertEqual(job2['qa']['decision'], 'PASS', job2['qa']['reasons'])


class LilDrByrdBuilder(Base):
    def test_missing_mascot_blocks_artwork_only(self):
        b = builders.Build.create(self.ws, LDB, 'lil_dr_byrd')
        u = builders.build_lil_dr_byrd_chapter(self.ws, b.id, 'ch01')
        self.assertEqual(u['status'], 'BLOCKED_MISSING_APPROVED_ASSET')
        self.assertEqual(u['blocked_assets'][0]['asset'], 'lil_dr_byrd')
        self.assertIsNone(u['mascot'])
        self.assertTrue(Path(u['output']).exists(), 'text build continues while artwork is blocked')
        self.assertEqual(u['incorrect'], 0)
        import pymupdf
        with pymupdf.open(u['output']) as d:
            self.assertEqual(sum(len(p.get_images()) for p in d), 0, 'no substitute mascot generated')
            text = ''.join(p.get_text() for p in d)
        self.assertIn('Answers & Solutions', text)
        self.assertNotIn('Honors: kinetic energy', text, 'honors content omitted until approved')
        with self.assertRaises(PermissionError):
            b.approve('ch01', owner_confirmed=True, attest_unsupported=True)

    def test_registered_mascot_used_byte_identical(self):
        png = self.d / 'LilDrByrd_approved.png'
        png.write_bytes(fixtures.png_bytes((250, 200, 20)))
        rec = register_asset(self.ws, png, 'lil_dr_byrd', 'mascot', owner_confirmed=True)
        with self.assertRaises(ValueError):
            register_asset(self.ws, png, 'lil_dr_byrd', 'mascot', owner_confirmed=True)   # never replaced silently
        b = builders.Build.create(self.ws, LDB, 'lil_dr_byrd')
        u = builders.build_lil_dr_byrd_chapter(self.ws, b.id, 'ch01')
        self.assertEqual(u['status'], builders.APPROVAL_READY, u['verification'])
        self.assertEqual(u['mascot']['sha256'], rec['sha256'])
        import pymupdf
        with pymupdf.open(u['output']) as d:
            self.assertGreaterEqual(sum(len(p.get_images()) for p in d), 1)
        self.assertEqual(sha256(Path(b.dir / 'chapters' / 'ch01' / png.name)), rec['sha256'])

    def test_wrong_physics_answer_blocks_chapter(self):
        bp = copy.deepcopy(LDB)
        bp['chapters'][0]['practice'][0]['answer'] = '6 kg'
        b = builders.Build.create(self.ws, bp, 'lil_dr_byrd')
        u = builders.build_lil_dr_byrd_chapter(self.ws, b.id, 'ch01')
        self.assertEqual(u['status'], 'BLOCKED_ACADEMIC_DEFECT')

    def test_asset_tamper_detected(self):
        png = self.d / 'm.png'
        png.write_bytes(fixtures.png_bytes())
        rec = register_asset(self.ws, png, 'lil_dr_byrd', 'mascot', owner_confirmed=True)
        os.chmod(rec['file'], 0o666)
        Path(rec['file']).write_bytes(b'not the approved art')
        with self.assertRaises(ValueError):
            get_asset(self.ws, 'lil_dr_byrd')

    def test_only_owner_registers_assets(self):
        png = self.d / 'm.png'
        png.write_bytes(fixtures.png_bytes())
        with self.assertRaises(PermissionError):
            register_asset(self.ws, png, 'lil_dr_byrd', 'mascot')


class BackupRestore(Base):
    def test_backup_verify_restore(self):
        m = import_product(fixtures.broken_power_tool_zip(self.d / 't.zip'), self.ws)
        bk = backup_workspace(self.ws, self.d / 'b.zip')
        self.assertEqual(verify_backup(bk), [])
        with self.assertRaises(PermissionError):
            restore_backup(bk, self.d / 'restored')
        r = restore_backup(bk, self.d / 'restored', confirm=True)
        self.assertIsNone(r['pre_restore_backup'])
        self.assertEqual(Studio(self.d / 'restored').products()[0]['integrity'], 'OK')
        # restoring over an existing workspace makes a safety backup first
        r2 = restore_backup(bk, self.ws, confirm=True)
        self.assertTrue(Path(r2['pre_restore_backup']).exists())
        self.assertEqual(Studio(self.ws).products()[0]['id'], m['id'])

    def test_damaged_backup_refused(self):
        import_product(fixtures.broken_power_tool_zip(self.d / 't.zip'), self.ws)
        bk = backup_workspace(self.ws, self.d / 'b.zip')
        tmp = self.d / 'damaged.zip'
        with zipfile.ZipFile(bk) as zi, zipfile.ZipFile(tmp, 'w') as zo:
            for n in zi.namelist():
                data = zi.read(n)
                if n.endswith('manifest.json') and n != 'BACKUP_MANIFEST.json':
                    data = data + b' '
                zo.writestr(n, data)
        self.assertTrue(verify_backup(tmp))
        with self.assertRaises(ValueError):
            restore_backup(tmp, self.d / 'x', confirm=True)


class Coordination(Base):
    def test_roles_and_independence(self):
        m = import_product(fixtures.broken_power_tool_zip(self.d / 't.zip'), self.ws)
        job = Orchestrator(self.ws).run_repair_job(m['id'], run_browser=False)
        for r in ('Orchestrator', 'Power Tool Repair', 'Academic Verifier', 'Release QA'):
            self.assertIn(r, job['roles_used'])
        log = (self.ws / 'logs' / f'job_{job["id"]}.jsonl').read_text()
        self.assertIn('"role": "Release QA"', log)
        self.assertTrue((self.ws / 'jobs' / job['id'] / 'qa' / 'qa_result.json').exists())
        pdf = import_product(fixtures.explainer_pdf(self.d / 'x.pdf'), self.ws)
        job2 = Orchestrator(self.ws).run_repair_job(pdf['id'], run_browser=False)
        self.assertIn('Explainer Repair', job2['roles_used'])

    def test_next_action_is_plain_and_correct(self):
        from controller import next_action
        m = import_product(fixtures.broken_power_tool_zip(self.d / 't.zip'), self.ws)
        job = Orchestrator(self.ws).run_repair_job(m['id'], run_browser=False)
        self.assertIn('Chromium', next_action(job))
        self.assertIn('APPROVE', next_action({'status': 'AWAITING_OWNER_APPROVAL', 'qa': {'score': 100.0}}))
        self.assertIn('BLOCKED', next_action({'status': 'BLOCKED', 'qa': {'reasons': ['CRITICAL failed: x']}}))
        self.assertIn('Attest', next_action({'status': 'NOT_VERIFIED', 'qa': {'unverified_items': [1]}}))

    def test_controller_surface(self):
        m = self.studio.import_product(fixtures.broken_power_tool_zip(self.d / 't.zip'))
        self.assertEqual(self.studio.products()[0]['integrity'], 'OK')
        self.assertIn('issues', self.studio.local_audit(m['id']))
        self.assertTrue(all(self.studio.verify_all_originals().values()))
        self.assertIn('NOT verified', self.studio.cost_summary()['balance_note'])
        self.assertTrue(self.studio.activity())


class HtmlAuditCoverage(unittest.TestCase):
    def test_detects_accessibility_structure_navigation(self):
        html = ('<html><head></head><body><img src="a.png"><button></button><div id="x"></div><div id="x"></div>'
                '<a href="#nowhere">n</a><script src="https://cdn.example.com/lib.js"></script>'
                '<script>document.getElementById("missing")</script></body></html>')
        f, c = audit_files({'index.html': html, 'a.png': None})
        found = {x['check'] for x in f}
        for k in ('a11y.lang', 'responsive.viewport', 'structure.title', 'a11y.img_alt', 'a11y.button_name',
                  'structure.duplicate_id', 'nav.anchor', 'js.missing_element'):
            self.assertIn(k, found)
        self.assertTrue(any(x['check'] == 'deps.external' and x['severity'] == 'INFO' for x in f))

    def test_reference_outside_package_is_critical(self):
        f, _ = audit_files({'index.html': '<html lang="en"><img src="../../secret.png" alt=""></html>'})
        self.assertTrue(any(x['check'] == 'assets.escape' and x['severity'] == 'CRITICAL' for x in f))

    def test_clean_page_has_no_major_findings(self):
        z = fixtures.fixed_power_tool_zip(Path(tempfile.mkdtemp()) / 'f.zip')
        with zipfile.ZipFile(z) as zz:
            files = {n: (zz.read(n).decode() if not n.endswith('.png') else None) for n in zz.namelist()}
        f, _ = audit_files(files)
        self.assertFalse([x for x in f if x['severity'] in ('CRITICAL', 'MAJOR')], f)


if __name__ == '__main__':
    unittest.main()
