"""UI-independent application facade. The Tk UI calls only these functions,
so every user action is covered by automated tests without a display."""
from pathlib import Path
import json

import engine, release, builders, assets
from config import load_settings, save_settings
from costs import Ledger, get_api_key, store_api_key
from joblog import activity, read_activity
from orchestrator import Orchestrator


class Studio:
    def __init__(self, root):
        self.root = engine.workspace(root)

    # products
    def products(self):
        out = []
        for p in engine.inventory(self.root):
            if p.get('status') != 'MANIFEST_CORRUPTED':
                p['integrity'] = 'OK' if engine.verify_original(self.root, p['id']) else 'HASH MISMATCH'
            out.append(p)
        return out

    def import_product(self, path):
        m = engine.import_product(path, self.root)
        activity(self.root, 'Orchestrator', f'Imported {m["name"]} as {m["product_type"]}', sha256=m['sha256'])
        return m

    def local_audit(self, pid):
        return engine.create_audit(self.root, pid)

    def verify_all_originals(self):
        return {p['id']: engine.verify_original(self.root, p['id']) for p in engine.inventory(self.root)
                if p.get('status') != 'MANIFEST_CORRUPTED'}

    # jobs
    def run_job(self, pid, ai_enabled=False, approver=None, progress=None, run_browser=True, ai_client=None):
        return Orchestrator(self.root).run_repair_job(pid, ai_enabled=ai_enabled, approver=approver,
                                                      progress=progress, run_browser=run_browser, ai_client=ai_client)

    def jobs(self):
        return Orchestrator(self.root).list_jobs()

    def job(self, job_id):
        return Orchestrator(self.root).load_job(job_id)

    def job_report(self, job_id):
        p = self.root / 'jobs' / job_id / 'REPORT.md'
        return p.read_text(encoding='utf-8') if p.exists() else '(no report)'

    def job_diff(self, job_id):
        p = self.root / 'jobs' / job_id / 'changes.diff'
        return p.read_text(encoding='utf-8') if p.exists() else ''

    def job_evidence_dir(self, job_id):
        return self.root / 'jobs' / job_id

    def attest(self, job_id, item_key, owner, note):
        return release.attest(self.root, job_id, item_key, owner, note)

    def approve(self, job_id, owner, explicit=False, visual_reviewed=False):
        return release.owner_approve(self.root, job_id, owner, explicit, visual_reviewed)

    def reject(self, job_id, owner, reason):
        return release.owner_reject(self.root, job_id, owner, reason)

    def export(self, job_id, dest=None):
        return release.export_approved(self.root, job_id, dest)

    def rerun_qa(self, job_id):
        return release.requeue_qa(self.root, job_id)

    # builders
    def new_build(self, blueprint_path, kind):
        bp = json.loads(Path(blueprint_path).read_text(encoding='utf-8'))
        return builders.Build.create(self.root, bp, kind)

    def builds(self):
        out = []
        for p in (self.root / 'builds').glob('*/state.json'):
            try:
                out.append(json.loads(p.read_text(encoding='utf-8')))
            except ValueError:
                pass
        return sorted(out, key=lambda s: s.get('created_at', ''), reverse=True)

    def build_next(self, build_id):
        b = builders.Build(self.root, build_id)
        s = b.state
        for u in s['order']:
            st = s['units'][u]['status']
            if st == 'OWNER_APPROVED':
                continue
            if s['kind'] == 'power_tool':
                return u, builders.build_power_tool_module(self.root, build_id, u)
            return u, builders.build_lil_dr_byrd_chapter(self.root, build_id, u)
        return None, None

    def approve_unit(self, build_id, unit, explicit=False, attest_unsupported=False, note=''):
        return builders.Build(self.root, build_id).approve(unit, explicit, attest_unsupported, note)

    def assemble_and_import(self, build_id, explicit=False):
        out = builders.assemble(self.root, build_id, explicit)
        return self.import_product(out)

    def register_asset(self, path, asset_id, kind, note='', explicit=False):
        return assets.register_asset(self.root, path, asset_id, kind, note, explicit)

    def asset_registry(self):
        return assets.registry(self.root)

    # costs / settings
    def settings(self):
        return load_settings(self.root)

    def save_settings(self, s):
        save_settings(self.root, s)
        activity(self.root, 'Orchestrator', 'Settings updated')

    def cost_summary(self):
        return Ledger(self.root).summary(load_settings(self.root))

    def ledger(self):
        return Ledger(self.root).entries()

    def api_key_configured(self):
        return bool(get_api_key())

    def set_api_key(self, key):
        store_api_key(key)
        activity(self.root, 'Orchestrator', 'API key stored in OS secret store (value not logged)')

    # backup / logs
    def backup(self, dest=None):
        return release.backup_workspace(self.root, dest)

    def restore(self, backup_zip, confirm=False):
        return release.restore_backup(backup_zip, self.root, confirm)

    def activity(self, limit=300):
        return read_activity(self.root, limit)
