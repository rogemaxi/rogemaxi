"""Owner-controlled release: attestation, approval, rejection, export, backup, restore.

Release path (the only one exposed in the UI):
  Release QA decision PASS  ->  owner approval (explicit, named)  ->  export
Release QA BLOCKED / NOT_VERIFIED / BELOW_TARGET cannot be approved. The only
owner input that can change a NOT_VERIFIED result is an attestation that the
owner personally reviewed items the deterministic verifier cannot check; it
never overrides a failed check. Nothing is uploaded or published anywhere.
"""
import json, os, shutil, time, zipfile
from pathlib import Path
from engine import (workspace, original_file, verify_original, sha256, write_json, read_json, utcnow,
                    validate_zip, rmtree_force, atomic_write_bytes)
from joblog import JobLog
from orchestrator import Orchestrator, ReleaseQAAgent


def attest(root, job_id, item_key, owner_name, note):
    """Owner attests they reviewed an unverifiable academic item (or 'ALL')."""
    if not owner_name or not note:
        raise ValueError('Owner name and review note are required')
    o = Orchestrator(root)
    job = o.load_job(job_id)
    if job['status'] in ('APPROVED', 'EXPORTED', 'REJECTED'):
        raise PermissionError(f'Job is {job["status"]}')
    job.setdefault('attestations', []).append({'item': item_key, 'owner': owner_name, 'note': note, 'at': utcnow()})
    qa = ReleaseQAAgent(o.root, o.settings).evaluate(job)
    job['qa'] = qa
    job['status'] = {'PASS': 'AWAITING_OWNER_APPROVAL'}.get(qa['decision'], qa['decision'])
    o.save_job(job)
    JobLog(root, job_id).info('Release QA', f'Attestation by {owner_name} for {item_key}; re-evaluated: {qa["decision"]}')
    return job


def requeue_qa(root, job_id, run_browser=True):
    o = Orchestrator(root)
    job = o.load_job(job_id)
    qa = ReleaseQAAgent(o.root, o.settings).evaluate(job, run_browser)
    job['qa'] = qa
    if job['status'] not in ('APPROVED', 'EXPORTED', 'REJECTED'):
        job['status'] = {'PASS': 'AWAITING_OWNER_APPROVAL'}.get(qa['decision'], qa['decision'])
    o.save_job(job)
    return job


def owner_approve(root, job_id, owner_name, explicit_approval=False, visual_reviewed=False):
    if explicit_approval is not True:
        raise PermissionError('Explicit owner approval required')
    if not owner_name or not owner_name.strip():
        raise ValueError('Approver name required')
    o = Orchestrator(root)
    job = o.load_job(job_id)
    qa = job.get('qa') or {}
    if qa.get('decision') != 'PASS':
        raise PermissionError(f'Release QA has not passed this candidate (decision {qa.get("decision")}). '
                              f'Release is BLOCKED; no override exists.')
    if not verify_original(root, job['product_id']):
        raise PermissionError('Original fingerprint mismatch: STOP')
    if sha256(job['candidate']) != job['candidate_sha256']:
        raise PermissionError('Candidate changed after QA: STOP')
    reconstructed = [h for h in job.get('history', []) if h.get('replace_file')]
    if reconstructed and visual_reviewed is not True:
        raise PermissionError('Candidate contains reconstructed PDF regions: owner must confirm visual review')
    job['status'] = 'APPROVED'
    job['approval'] = {'owner': owner_name.strip(), 'at': utcnow(), 'candidate_sha256': job['candidate_sha256'],
                       'qa_score': qa.get('score'), 'visual_reviewed': bool(visual_reviewed)}
    o.save_job(job)
    JobLog(root, job_id).info('Release QA', f'Owner approval recorded: {owner_name}')
    return job


def owner_reject(root, job_id, owner_name, reason):
    o = Orchestrator(root)
    job = o.load_job(job_id)
    if job['status'] == 'EXPORTED':
        raise PermissionError('Already exported')
    job['status'] = 'REJECTED'
    job['rejection'] = {'owner': owner_name, 'reason': reason, 'at': utcnow()}
    o.save_job(job)
    JobLog(root, job_id).info('Release QA', f'Owner rejected: {reason}')
    return job


def export_approved(root, job_id, dest_dir=None):
    """Copy an approved candidate + full audit trail to exports/. Never publishes."""
    root = workspace(root)
    o = Orchestrator(root)
    job = o.load_job(job_id)
    if job['status'] not in ('APPROVED', 'EXPORTED'):
        raise PermissionError(f'Only owner-approved candidates can be exported (status {job["status"]})')
    if sha256(job['candidate']) != job['approval']['candidate_sha256']:
        raise PermissionError('Candidate changed after approval: STOP')
    if not verify_original(root, job['product_id']):
        raise PermissionError('Original fingerprint mismatch: STOP')
    out = Path(dest_dir) if dest_dir else root / 'exports' / f'{job_id}'
    out.mkdir(parents=True, exist_ok=True)
    name = job['product_name']
    product_out = out / name
    shutil.copy2(job['candidate'], product_out)
    jd = root / 'jobs' / job_id
    trail = out / 'audit_trail'
    trail.mkdir(exist_ok=True)
    for f in ('job.json', 'REPORT.md', 'changes.diff', 'baseline_findings.json', 'final_findings.json'):
        if (jd / f).exists():
            shutil.copy2(jd / f, trail / f)
    if (jd / 'qa' / 'qa_result.json').exists():
        shutil.copy2(jd / 'qa' / 'qa_result.json', trail / 'qa_result.json')
    log = root / 'logs' / f'job_{job_id}.jsonl'
    if log.exists():
        shutil.copy2(log, trail / 'job_log.jsonl')
    sums = {}
    for p in sorted(out.rglob('*')):
        if p.is_file() and p.name != 'SHA256SUMS.txt':
            sums[p.relative_to(out).as_posix()] = sha256(p)
    (out / 'SHA256SUMS.txt').write_text(''.join(f'{h}  {r}\n' for r, h in sums.items()), encoding='utf-8')
    if sha256(product_out) != job['candidate_sha256']:
        raise ValueError('Export integrity failure')
    if product_out.suffix.lower() == '.zip':
        validate_zip(product_out)
    job['status'] = 'EXPORTED'
    job['export'] = {'path': str(product_out), 'sha256': sha256(product_out), 'at': utcnow(), 'dir': str(out)}
    o.save_job(job)
    JobLog(root, job_id).info('Release QA', f'Exported to {out} (local only; nothing published)')
    return out


def verify_export(export_dir):
    """Re-check SHA256SUMS of an export folder. Returns list of problems."""
    export_dir = Path(export_dir)
    problems = []
    for line in (export_dir / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        h, rel = line.split('  ', 1)
        p = export_dir / rel
        if not p.exists():
            problems.append(f'missing {rel}')
        elif sha256(p) != h:
            problems.append(f'modified {rel}')
    return problems


# ---------------------------------------------------------------- backups
BACKUP_EXCLUDE = {'backups', 'working'}


def backup_workspace(root, dest=None):
    root = workspace(root)
    stamp = time.strftime('%Y%m%d_%H%M%S')
    dest = Path(dest) if dest else root / 'backups' / f'byrdway_backup_{stamp}.zip'
    manifest = {}
    tmp = dest.with_name(dest.name + '.partial')
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as z:
        for p in sorted(root.rglob('*')):
            if not p.is_file():
                continue
            rel = p.relative_to(root)
            if rel.parts[0] in BACKUP_EXCLUDE or p.name.startswith('.tmp_'):
                continue
            manifest[rel.as_posix()] = sha256(p)
            z.write(p, rel.as_posix())
        z.writestr('BACKUP_MANIFEST.json', json.dumps({'created_at': utcnow(), 'files': manifest}, indent=1))
    os.replace(tmp, dest)
    problems = verify_backup(dest)
    if problems:
        raise ValueError(f'Backup verification failed: {problems[:5]}')
    return dest


def verify_backup(backup_zip):
    problems = []
    with zipfile.ZipFile(backup_zip) as z:
        m = json.loads(z.read('BACKUP_MANIFEST.json'))
        names = set(z.namelist())
        import hashlib
        for rel, h in m['files'].items():
            if rel not in names:
                problems.append(f'missing {rel}')
                continue
            if hashlib.sha256(z.read(rel)).hexdigest() != h:
                problems.append(f'hash mismatch {rel}')
    return problems


def restore_backup(backup_zip, target_root, confirm=False):
    """Restore into target_root. An existing non-empty workspace is first backed up."""
    if confirm is not True:
        raise PermissionError('Restore requires explicit confirmation')
    problems = verify_backup(backup_zip)
    if problems:
        raise ValueError(f'Backup is damaged; refusing restore: {problems[:5]}')
    target = Path(target_root).resolve()
    safety = None
    stamp = time.strftime('%Y%m%d_%H%M%S')
    if target.exists() and any(target.iterdir()):
        # safety copy lives OUTSIDE the workspace being replaced
        safety = backup_workspace(target, target.parent / f'{target.name}_pre_restore_{stamp}.zip')
    staging = target.with_name(target.name + '.restore_staging')
    rmtree_force(staging)
    _extract_backup(backup_zip, staging)
    (staging / 'BACKUP_MANIFEST.json').unlink()
    workspace(staging)
    if (target / 'backups').exists():                       # keep existing backup archives
        for p in (target / 'backups').iterdir():
            if p.is_file():
                shutil.copy2(p, staging / 'backups' / p.name)
    old = target.with_name(target.name + '.before_restore')
    rmtree_force(old)
    if target.exists():
        os.replace(target, old)
    os.replace(staging, target)
    rmtree_force(old)
    return {'restored_to': str(target), 'pre_restore_backup': str(safety) if safety else None}


def _extract_backup(backup_zip, dest, max_total=4 * 1024 ** 3):
    from engine import _entry_problem
    from pathlib import PurePosixPath
    dest = Path(dest).resolve()
    dest.mkdir(parents=True)
    total = 0
    with zipfile.ZipFile(backup_zip) as z:
        for info in z.infolist():
            reason = _entry_problem(info.filename)
            if reason or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError(f'Unsafe entry in backup: {info.filename!r}')
            target = (dest / PurePosixPath(info.filename)).resolve()
            if not target.is_relative_to(dest):
                raise ValueError('Unsafe backup path')
            total += info.file_size
            if total > max_total:
                raise ValueError('Backup too large')
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as i, open(target, 'wb') as o:
                shutil.copyfileobj(i, o)
