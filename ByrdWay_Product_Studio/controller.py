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
    def run_job(self, pid, ai_enabled=False, approver=None, progress=None, run_browser=True, ai_client=None,
                authorization=None):
        return Orchestrator(self.root).run_repair_job(pid, ai_enabled=ai_enabled, approver=approver,
                                                      progress=progress, run_browser=run_browser, ai_client=ai_client,
                                                      authorization=authorization)

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

    def image_findings(self, job_id):
        return release.image_findings(self.root, job_id)

    def decide_image_finding(self, job_id, item_id, verdict, owner, correction=None, replacement=None):
        return release.decide_image_finding(self.root, job_id, item_id, verdict, owner, correction,
                                            replacement=replacement)

    def repair_image_findings(self, job_id, owner, explicit=False, progress=None):
        return release.repair_confirmed_image_findings(self.root, job_id, owner, explicit, progress)

    def export_correction_sheet(self, job_id, owner, explicit=False, dest=None):
        return release.export_correction_sheet(self.root, job_id, owner, explicit, dest)

    def rerun_qa(self, job_id):
        return release.requeue_qa(self.root, job_id)

    def diagnose(self, pid, progress=None, run_browser=True):
        return Orchestrator(self.root).diagnose(pid, run_browser=run_browser, progress=progress)

    def latest_report(self, pid):
        cands = []
        for j in self.jobs():
            if j['product_id'] == pid and (self.root / 'jobs' / j['id'] / 'report.html').exists():
                p = self.root / 'jobs' / j['id'] / 'report.html'
                cands.append((p.stat().st_mtime_ns, 1, p))
        for d in (self.root / 'reports').glob('diag_*/diagnosis.json'):
            try:
                x = json.loads(d.read_text(encoding='utf-8'))
            except ValueError:
                continue
            if x.get('product_id') == pid and (d.parent / 'diagnosis.html').exists():
                p = d.parent / 'diagnosis.html'
                cands.append((p.stat().st_mtime_ns, 0, p))
        return max(cands, key=lambda c: (c[0], c[1]))[2] if cands else None

    def job_html_report(self, job_id):
        p = self.root / 'jobs' / job_id / 'report.html'
        if not p.exists():
            try:
                import report
                p = report.write_job_report(self.root, self.job(job_id))
            except Exception:
                return None
        return p

    # builders
    def new_build(self, blueprint_path, kind):
        bp = json.loads(Path(blueprint_path).read_text(encoding='utf-8'))
        return builders.Build.create(self.root, bp, kind)

    def builds(self):
        out = []
        for p in (self.root / 'builds').glob('*/state.json'):
            try:
                s = json.loads(p.read_text(encoding='utf-8'))
                bp = json.loads((p.parent / 'blueprint.json').read_text(encoding='utf-8'))
            except (ValueError, OSError):
                continue
            s['title'] = bp.get('product_title') or (bp.get('chapters') or [{}])[0].get('title', '')
            s['sample'] = builders.is_sample(bp)
            done = sum(1 for u in s['order'] if s['units'][u]['status'] == 'OWNER_APPROVED')
            s['summary'] = f'{done}/{len(s["order"])} approved' + (' — SAMPLE' if s['sample'] else '') + (
                ' — assembled' if s.get('assembled') else '')
            out.append(s)
        return sorted(out, key=lambda s: s.get('created_at', ''), reverse=True)

    def build_prerequisites(self, kind, build_id=None):
        bp = builders.Build(self.root, build_id).blueprint if build_id else None
        return builders.prerequisites(self.root, kind, bp)

    def sample_form(self, kind):
        here = Path(__file__).resolve().parent / 'samples'
        if kind == 'power_tool':
            bp = json.loads((here / 'SAMPLE_power_tool_blueprint.json').read_text(encoding='utf-8'))
            return builders.form_from_power_tool_blueprint(bp)
        bp = json.loads((here / 'SAMPLE_lil_dr_byrd_physics_blueprint.json').read_text(encoding='utf-8'))
        return builders.form_from_chapter_blueprint(bp)

    def load_blueprint_form(self, path):
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        if data.get('_form_kind'):                      # a saved draft
            return data['_form_kind'], data['form']
        if 'modules' in data:
            return 'power_tool', builders.form_from_power_tool_blueprint(data)
        if 'chapters' in data:
            return 'lil_dr_byrd', builders.form_from_chapter_blueprint(data)
        raise ValueError('This file is not a ByrdWay blueprint (no modules or chapters found).')

    def build_form(self, build_id):
        b = builders.Build(self.root, build_id)
        kind = b.state['kind']
        bp = b.blueprint
        return kind, (builders.form_from_power_tool_blueprint(bp) if kind == 'power_tool'
                      else builders.form_from_chapter_blueprint(bp))

    def create_build_from_form(self, kind, form):
        bp = (builders.power_tool_blueprint_from_form(form) if kind == 'power_tool'
              else builders.chapter_blueprint_from_form(form))
        builders.save_blueprint(self.root, bp, kind)
        b = builders.Build.create(self.root, bp, kind)
        activity(self.root, 'Power Tool Builder' if kind == 'power_tool' else 'Lil Dr. Byrd Builder',
                 f'Build {b.id} created from form')
        return b

    def save_draft(self, kind, form):
        d = self.root / 'blueprints' / 'drafts'
        d.mkdir(parents=True, exist_ok=True)
        import re, time
        name = re.sub(r'[^A-Za-z0-9]+', '_', form.get('product_title') or (form.get('chapters') or [{}])[0].get('title') or 'draft')[:40]
        p = d / f'{kind}_{name}_{time.strftime("%Y%m%d_%H%M%S")}.json'
        engine.write_json(p, {'_form_kind': kind, 'form': form})
        return p

    def reject_unit(self, build_id, unit, reason):
        return builders.Build(self.root, build_id).reject(unit, reason)

    def assemble_and_verify(self, build_id, progress=None, run_browser=True):
        m = self.assemble_and_import(build_id, True)
        return self.run_job(m['id'], progress=progress, run_browser=run_browser)

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


def next_action(job):
    """One plain-English instruction for the owner, derived only from recorded job state."""
    qa = job.get('qa') or {}
    st = job.get('status')
    if st == 'ERROR':
        return f'Job crashed ({job.get("error")}). Send logs\\activity.jsonl to your developer.'
    if st == 'EXPORTED':
        return f'Done. Exported to {job.get("export", {}).get("dir")}. Upload to TpT yourself when ready.'
    if st == 'APPROVED':
        return 'Approved. Click "Export Approved…" to save the final product with its audit trail.'
    if st == 'REJECTED':
        return 'Rejected by owner. Nothing will be exported.'
    if st == 'AWAITING_OWNER_APPROVAL':
        extra = ' Check the before/after page images first (Open Evidence Folder).' if any(
            h.get('replace_file') for h in job.get('history', [])) else ''
        return (f'Release QA PASSED ({qa.get("score")}/100). Review "Before / After Diff", then click '
                f'"APPROVE for release…".{extra}')
    pend = [u for u in qa.get('unverified_items') or [] if isinstance(u, dict) and u.get('status') == 'PENDING_OWNER_DECISION']
    if pend:
        n = len(pend)
        return (f'The page reader found {n} possible error(s) on image pages. Click "Review Image Findings…" '
                f'and confirm or dismiss each one (a picture of each is shown).')
    if st == 'BLOCKED' and any(f.get('image_item') and f.get('decision') == 'confirmed'
                               for f in qa.get('image_findings') or []):
        return ('You confirmed error(s) on image pages. Best: click "Export Correction Sheet…" and correct them in '
                'your editable source (Canva/PPTX), then import the new PDF. Or click "Repair Confirmed on a Copy…" '
                'to have the Studio draw the corrections on a protected copy (checked by the Repair Reviewer and '
                'Release QA; you approve each corrected spot).')
    if st == 'NOT_VERIFIED':
        if qa.get('unverified_items'):
            return (f'{len(qa["unverified_items"])} question(s) cannot be checked automatically. Review them '
                    f'yourself, then use "Attest Unverifiable Item…" (or ALL).')
        miss = qa.get('missing_required_categories') or []
        if 'browser_runtime' in miss:
            return 'Browser tests could not run: use Help → Install browser engine (one-time download), then Re-run Release QA.'
        if 'academic' in miss:
            return ('No answers could be read automatically (image-only pages or an unknown answer format). '
                    'Check the content yourself and attest ALL, or send the product to your developer.')
        return 'Coverage incomplete: ' + '; '.join(qa.get('reasons', []))
    if st == 'BLOCKED':
        first = (qa.get('reasons') or ['see report'])[0]
        return f'Release BLOCKED by a defect that needs a person: {first}'
    if st == 'BELOW_TARGET':
        return 'Minor issues keep the score under 99.9. See failed checks below; fix in source or re-run.'
    return f'Status {st}.'
