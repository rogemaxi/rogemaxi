"""Source-aware working copies: unpack -> edit -> diff -> checkpoint/rollback -> repack.

The locked original in originals/<pid>/ is never written. All edits happen in
working/<job_id>/files/. Every patch is recorded with before/after hashes.
"""
import difflib, json, os, re, shutil, zipfile
from pathlib import Path, PurePosixPath
from engine import (workspace, original_file, sha256, sha256_bytes, write_json, read_json,
                    utcnow, atomic_write_bytes, rmtree_force, make_writable, TEXT_EXT,
                    _entry_problem, validate_zip)

FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)  # deterministic repacks


class PatchError(ValueError):
    pass


def safe_relpath(rel):
    """Normalise a product-relative path; refuse anything that could escape."""
    rel = str(rel).strip()
    reason = _entry_problem(rel)
    if reason:
        raise PatchError(f'Unsafe path ({reason}): {rel!r}')
    p = PurePosixPath(rel)
    if p.is_absolute() or not p.parts:
        raise PatchError(f'Unsafe path: {rel!r}')
    return p.as_posix()


class WorkingCopy:
    def __init__(self, root, job_id):
        self.root = workspace(root)
        self.job_id = job_id
        self.dir = self.root / 'working' / job_id
        self.files = self.dir / 'files'
        self.cp_dir = self.dir / 'checkpoints'
        self.meta_path = self.dir / 'working.json'

    # ------------------------------------------------------------ creation
    @classmethod
    def create(cls, root, pid, job_id):
        wc = cls(root, job_id)
        if wc.dir.exists():
            raise ValueError('Working copy already exists for this job')
        src, manifest = original_file(root, pid)
        wc.files.mkdir(parents=True)
        wc.cp_dir.mkdir()
        if src.suffix.lower() == '.zip':
            unpacked = src.parent / 'unpacked'
            for p in sorted(unpacked.rglob('*')):
                rel = p.relative_to(unpacked)
                if p.is_dir():
                    (wc.files / rel).mkdir(parents=True, exist_ok=True)
                else:
                    (wc.files / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(p, wc.files / rel)   # copyfile: drop read-only bit
            kind = 'zip'
        else:
            shutil.copyfile(src, wc.files / src.name)
            kind = 'single'
        baseline = {r: sha256(wc.files / r) for r in wc.list_files()}
        meta = {'job_id': job_id, 'product_id': pid, 'product_name': manifest['name'],
                'original_sha256': manifest['sha256'], 'kind': kind, 'created_at': utcnow(),
                'baseline_hashes': baseline, 'history': [], 'checkpoints': []}
        write_json(wc.meta_path, meta)
        return wc

    @property
    def meta(self):
        return read_json(self.meta_path)

    def _save(self, meta):
        write_json(self.meta_path, meta)

    # ------------------------------------------------------------ file access
    def list_files(self):
        return sorted(p.relative_to(self.files).as_posix() for p in self.files.rglob('*') if p.is_file())

    def path(self, rel):
        rel = safe_relpath(rel)
        p = (self.files / rel).resolve()
        if not p.is_relative_to(self.files.resolve()):
            raise PatchError('Path escapes working copy')
        return p

    def read(self, rel):
        return self.path(rel).read_text(encoding='utf-8', errors='replace')

    def read_bytes(self, rel):
        return self.path(rel).read_bytes()

    def text_files(self):
        return [f for f in self.list_files() if PurePosixPath(f).suffix.lower() in TEXT_EXT]

    # ------------------------------------------------------------ patching
    def apply_patch(self, rel, find, replace, reason, source='deterministic', defect_id=None):
        """Replace `find` (must occur exactly once) with `replace` in a text file."""
        rel = safe_relpath(rel)
        if PurePosixPath(rel).suffix.lower() not in TEXT_EXT:
            raise PatchError('Only text source files can be patched; binary assets are protected')
        p = self.path(rel)
        if not p.exists():
            raise PatchError(f'File not found in product: {rel}')
        if not find:
            raise PatchError('Empty find text')
        if find == replace:
            raise PatchError('Patch makes no change')
        text = p.read_text(encoding='utf-8')
        count = text.count(find)
        if count != 1:
            raise PatchError(f'Patch target must occur exactly once in {rel}; found {count}')
        before = sha256_bytes(text.encode('utf-8'))
        new = text.replace(find, replace, 1)
        atomic_write_bytes(p, new.encode('utf-8'))
        rec = {'ts': utcnow(), 'file': rel, 'find': find, 'replace': replace, 'reason': reason,
               'source': source, 'defect_id': defect_id, 'before_sha256': before,
               'after_sha256': sha256(p), 'line': text[:text.index(find)].count('\n') + 1}
        meta = self.meta
        meta['history'].append(rec)
        self._save(meta)
        return rec

    def replace_file_bytes(self, rel, data, reason, source, evidence=None, defect_id=None):
        """Replace a whole file (used for evidence-backed PDF region corrections)."""
        rel = safe_relpath(rel)
        p = self.path(rel)
        if not p.exists():
            raise PatchError(f'File not found in product: {rel}')
        before = sha256(p)
        atomic_write_bytes(p, data)
        rec = {'ts': utcnow(), 'file': rel, 'replace_file': True, 'reason': reason, 'source': source,
               'defect_id': defect_id, 'before_sha256': before, 'after_sha256': sha256(p),
               'evidence': evidence or {}}
        meta = self.meta
        meta['history'].append(rec)
        self._save(meta)
        return rec

    # ------------------------------------------------------------ versions
    def checkpoint(self, label):
        meta = self.meta
        cid = f'cp{len(meta["checkpoints"]):03d}'
        dest = self.cp_dir / cid
        shutil.copytree(self.files, dest)
        meta['checkpoints'].append({'id': cid, 'label': label, 'ts': utcnow(),
                                    'history_len': len(meta['history']),
                                    'hashes': {r: sha256(dest / r) for r in self.list_files()}})
        self._save(meta)
        return cid

    def rollback(self, cid, reason='regression'):
        meta = self.meta
        cps = {c['id']: c for c in meta['checkpoints']}
        if cid not in cps:
            raise ValueError(f'Unknown checkpoint {cid}')
        src = self.cp_dir / cid
        for r, h in cps[cid]['hashes'].items():
            if sha256(src / r) != h:
                raise ValueError(f'Checkpoint {cid} corrupted at {r}; refusing rollback')
        rmtree_force(self.files)
        shutil.copytree(src, self.files)
        meta['history'].append({'ts': utcnow(), 'rollback_to': cid, 'reason': reason})
        self._save(meta)
        return cid

    # ------------------------------------------------------------ comparison
    def changed_files(self):
        base = self.meta['baseline_hashes']
        now = {r: sha256(self.files / r) for r in self.list_files()}
        changed = sorted(r for r in now if r in base and now[r] != base[r])
        added = sorted(r for r in now if r not in base)
        removed = sorted(r for r in base if r not in now)
        return {'changed': changed, 'added': added, 'removed': removed}

    def original_text(self, rel):
        src, _ = original_file(self.root, self.meta['product_id'])
        if self.meta['kind'] == 'single':
            return src.read_text(encoding='utf-8', errors='replace')
        return (src.parent / 'unpacked' / safe_relpath(rel)).read_text(encoding='utf-8', errors='replace')

    def diff(self, context=3):
        """Unified diff of every changed text file against the locked original."""
        out = []
        ch = self.changed_files()
        for rel in ch['changed']:
            if PurePosixPath(rel).suffix.lower() not in TEXT_EXT:
                out.append(f'Binary file changed: {rel}\n')
                continue
            a = self.original_text(rel).splitlines(keepends=True)
            b = self.read(rel).splitlines(keepends=True)
            out.append(''.join(difflib.unified_diff(a, b, f'original/{rel}', f'candidate/{rel}', n=context)))
        for rel in ch['added']:
            out.append(f'Added file: {rel}\n')
        for rel in ch['removed']:
            out.append(f'Removed file: {rel}\n')
        return '\n'.join(out)

    def protected_binaries_unchanged(self):
        ch = self.changed_files()
        bad = [r for r in ch['changed'] + ch['removed'] if PurePosixPath(r).suffix.lower() not in TEXT_EXT]
        return (not bad), bad

    # ------------------------------------------------------------ repack
    def repack(self, out_path):
        """Write the candidate package (ZIP for zip products, file otherwise)."""
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        meta = self.meta
        if meta['kind'] == 'single':
            rel = self.list_files()[0]
            atomic_write_bytes(out_path, self.read_bytes(rel))
            return out_path
        tmp = out_path.with_name(out_path.name + '.partial')
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
            for rel in self.list_files():
                info = zipfile.ZipInfo(rel, FIXED_ZIP_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                z.writestr(info, self.read_bytes(rel))
        validate_zip(tmp)                       # our own output must pass our own rules
        os.replace(tmp, out_path)
        return out_path

    def destroy(self):
        rmtree_force(self.dir)


def verify_zip_contents(zip_path, expected_hashes):
    """Return list of mismatches between a ZIP and {relpath: sha256}."""
    problems = []
    with zipfile.ZipFile(zip_path) as z:
        names = set(n for n in z.namelist() if not n.endswith('/'))
        for rel, h in expected_hashes.items():
            if rel not in names:
                problems.append(f'missing {rel}')
            elif sha256_bytes(z.read(rel)) != h:
                problems.append(f'hash mismatch {rel}')
        for n in names - set(expected_hashes):
            problems.append(f'unexpected {n}')
    return problems
