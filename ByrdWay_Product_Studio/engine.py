"""ByrdWay Product Engineering Studio: protected, review-first local core.

Backward compatible with v0.1: import_product, inventory, original_file,
extract_text, local_audit, create_audit, save_proposal, approve_proposal,
safe_extract_zip, sha256, workspace, Budget, ROLES, SUPPORTED.

v0.2 hardening (milestone A):
  * ZIP archives are fully validated BEFORE anything is written (two-pass),
    backslash / drive-letter / absolute / '..' / symlink / duplicate /
    encrypted entries are rejected, and actual decompressed bytes are capped
    while streaming (declared sizes in a ZIP header can lie).
  * A rejected import leaves NO partial product in the inventory.
  * Originals are stored read-only; every manifest/report write is atomic.
  * Corrupted manifests no longer crash the inventory.
  * Product type detection for orchestration.
"""
import hashlib, json, os, re, shutil, stat, tempfile, time, uuid, zipfile
from pathlib import Path, PurePosixPath

SUPPORTED = {'.html', '.htm', '.js', '.css', '.txt', '.md', '.json', '.pdf', '.zip'}
TEXT_EXT = {'.html', '.htm', '.js', '.css', '.txt', '.md', '.json', '.svg', '.csv', '.xml'}
ROLES = ['Orchestrator', 'Power Tool Repair', 'Explainer Repair', 'Power Tool Builder',
         'Lil Dr. Byrd Builder', 'Academic Verifier', 'Release QA']
MAX_FILE = 35 * 1024 * 1024
ZIP_MAX_ENTRIES = 500
ZIP_MAX_TOTAL = 150 * 1024 * 1024
ZIP_MAX_MEMBER = 60 * 1024 * 1024
ZIP_MAX_RATIO = 200          # compression ratio above this for >1 MB members = bomb
WORKSPACE_FOLDERS = ('originals', 'proposals', 'reports', 'approved', 'working', 'jobs',
                     'logs', 'exports', 'backups', 'assets', 'builds')


def utcnow():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write_bytes(path, data):
    """Write via temp file + os.replace so a crash never leaves a half file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.tmp_', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_write_text(path, text):
    atomic_write_bytes(path, text.encode('utf-8'))


def write_json(path, obj):
    atomic_write_text(path, json.dumps(obj, indent=2, default=str))


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def make_read_only(path):
    p = Path(path)
    p.chmod(p.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def make_writable(path):
    p = Path(path)
    p.chmod(p.stat().st_mode | stat.S_IWUSR)


def rmtree_force(path):
    """Remove a tree including read-only files (Windows-safe)."""
    def onerror(func, p, _exc):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError:
            pass
    if Path(path).exists():
        shutil.rmtree(path, onerror=onerror)


def workspace(root):
    root = Path(root).resolve()
    for folder in WORKSPACE_FOLDERS:
        (root / folder).mkdir(parents=True, exist_ok=True)
    return root


# --------------------------------------------------------------- ZIP safety
def _entry_problem(name):
    """Return a reason string if a ZIP entry name is unsafe, else None."""
    if not name or '\x00' in name:
        return 'empty or NUL entry name'
    if '\\' in name:
        return 'backslash in entry name'
    if name.startswith('/') or re.match(r'^[A-Za-z]:', name):
        return 'absolute path'
    parts = PurePosixPath(name).parts
    if '..' in parts:
        return 'parent-directory traversal'
    if any(re.match(r'^(con|prn|aux|nul|com\d|lpt\d)(\..*)?$', p, re.I) for p in parts):
        return 'reserved Windows device name'
    if any(p.endswith(' ') or p.endswith('.') and p not in ('.',) for p in parts):
        return 'trailing space/dot (Windows-unsafe)'
    return None


def validate_zip(src):
    """Validate a ZIP without writing anything. Returns list of ZipInfo.

    Raises ValueError for anything unsafe or corrupted.
    """
    try:
        z = zipfile.ZipFile(src)
    except (zipfile.BadZipFile, OSError) as e:
        raise ValueError(f'Corrupted or invalid ZIP: {e}')
    with z:
        members = z.infolist()
        if len(members) > ZIP_MAX_ENTRIES:
            raise ValueError('ZIP contains too many entries')
        if sum(m.file_size for m in members) > ZIP_MAX_TOTAL:
            raise ValueError('ZIP uncompressed size exceeds limit')
        seen = set()
        for item in members:
            reason = _entry_problem(item.filename)
            if reason:
                raise ValueError(f'Unsafe ZIP entry ({reason}): {item.filename!r}')
            if (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('ZIP symbolic link forbidden')
            if item.flag_bits & 0x1:
                raise ValueError('Encrypted ZIP entries are not supported')
            key = item.filename.rstrip('/').lower()
            if key in seen:
                raise ValueError(f'Duplicate ZIP entry: {item.filename!r}')
            seen.add(key)
            if item.file_size > ZIP_MAX_MEMBER:
                raise ValueError(f'ZIP member too large: {item.filename!r}')
            if item.file_size > 1024 * 1024 and item.compress_size and \
                    item.file_size / item.compress_size > ZIP_MAX_RATIO:
                raise ValueError(f'Suspicious compression ratio (archive bomb): {item.filename!r}')
            if item.filename.lower().endswith('.zip'):
                # nested archives are kept as files but never auto-extracted
                pass
        bad = None
        try:
            bad = z.testzip()
        except Exception as e:  # zlib errors, CRC errors, truncation
            raise ValueError(f'Corrupted ZIP: {e}')
        if bad:
            raise ValueError(f'Corrupted ZIP member: {bad}')
        return members


def safe_extract_zip(src, dest):
    """Validate fully, then extract with a hard cap on actual bytes written."""
    members = validate_zip(src)
    dest = Path(dest).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    total = 0
    with zipfile.ZipFile(src) as z:
        for item in members:
            target = (dest / PurePosixPath(item.filename)).resolve()
            if not target.is_relative_to(dest):
                raise ValueError('Unsafe ZIP path')
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            written = 0
            with z.open(item) as inp, open(target, 'wb') as out:
                while True:
                    chunk = inp.read(1024 * 256)
                    if not chunk:
                        break
                    written += len(chunk)
                    total += len(chunk)
                    if written > max(item.file_size, 0) + 1024 or written > ZIP_MAX_MEMBER \
                            or total > ZIP_MAX_TOTAL:
                        raise ValueError('ZIP decompressed beyond declared/allowed size')
                    out.write(chunk)
    return dest


# ---------------------------------------------------------- product typing
def detect_product_type(src, names=None):
    """Classify a product so the orchestrator can choose specialist roles."""
    src = Path(src)
    ext = src.suffix.lower()
    low = src.name.lower()
    honors = 'honors' in low
    if ext == '.zip':
        names = names if names is not None else _zip_names(src)
        lower = [n.lower() for n in names]
        has_html = any(n.endswith(('.html', '.htm')) for n in lower)
        has_pdf = any(n.endswith('.pdf') for n in lower)
        has_src = any(n.endswith(('.docx', '.pptx', '.tex', '.indd', '.odt', '.key', '.pages', '.md'))
                      for n in lower)
        if has_pdf and (has_src or not has_html):
            kind = 'EXPLAINER_SOURCE_PACKAGE'
        elif has_html:
            kind = 'POWER_TOOL'
        else:
            kind = 'UNKNOWN_PACKAGE'
    elif ext in ('.html', '.htm'):
        kind = 'POWER_TOOL'
    elif ext == '.pdf':
        if 'concept tile' in low or 'concept_tile' in low or 'concepttile' in low:
            kind = 'CONCEPT_TILES'
        elif 'anime' in low:
            kind = 'ANIME_EXPLAINER'
        elif 'lil' in low and 'byrd' in low:
            kind = 'LIL_DR_BYRD_EXPLAINER'
        else:
            kind = 'EXPLAINER_PDF'
    elif ext in ('.js', '.css'):
        kind = 'POWER_TOOL_ASSET'
    else:
        kind = 'TEXT_DOCUMENT'
    return {'type': kind, 'honors': honors}


def _zip_names(src):
    try:
        with zipfile.ZipFile(src) as z:
            return z.namelist()
    except zipfile.BadZipFile:
        return []


def _validate_input(src):
    ext = src.suffix.lower()
    if ext == '.zip':
        return validate_zip(src)
    with open(src, 'rb') as f:
        head = f.read(8)
    if ext == '.pdf' and not head.startswith(b'%PDF'):
        raise ValueError('File has .pdf extension but is not a PDF (corrupted or mislabeled)')
    if ext in TEXT_EXT:
        data = src.read_bytes()
        if b'\x00' in data[:4096]:
            raise ValueError('Text product contains binary data (corrupted or mislabeled)')
    return None


# ----------------------------------------------------------------- import
def import_product(src, root):
    src = Path(src).resolve()
    root = workspace(root)
    if not src.is_file() or src.suffix.lower() not in SUPPORTED:
        raise ValueError('Unsupported input type')
    if src.stat().st_size > MAX_FILE:
        raise ValueError('File exceeds 35 MB limit')
    if src.stat().st_size == 0:
        raise ValueError('Empty file')
    _validate_input(src)                      # reject BEFORE creating anything
    pid = uuid.uuid4().hex[:12]
    final = root / 'originals' / pid
    staging = root / 'originals' / f'.staging_{pid}'
    staging.mkdir()
    try:
        dest = staging / src.name
        shutil.copy2(src, dest)
        digest = sha256(dest)
        if digest != sha256(src):
            raise ValueError('Copy verification failed')
        names = None
        if src.suffix.lower() == '.zip':
            safe_extract_zip(dest, staging / 'unpacked')
            names = _zip_names(dest)
        ptype = detect_product_type(dest, names)
        manifest = {'id': pid, 'name': src.name, 'sha256': digest,
                    'size': dest.stat().st_size, 'imported_at': utcnow(),
                    'status': 'ORIGINAL_LOCKED', 'product_type': ptype['type'],
                    'honors': ptype['honors'], 'source_path_at_import': str(src)}
        if names is not None:
            manifest['zip_entries'] = len(names)
        write_json(staging / 'manifest.json', manifest)
        os.replace(staging, final)
    except BaseException:
        rmtree_force(staging)
        raise
    # lock original bytes (and unpacked reference copy) read-only
    make_read_only(final / src.name)
    if (final / 'unpacked').exists():
        for p in (final / 'unpacked').rglob('*'):
            if p.is_file():
                make_read_only(p)
    return manifest


def inventory(root):
    root = workspace(root)
    result = []
    for p in (root / 'originals').glob('*/manifest.json'):
        if p.parent.name.startswith('.staging_'):
            continue
        try:
            result.append(json.loads(p.read_text(encoding='utf-8')))
        except (ValueError, OSError):
            result.append({'id': p.parent.name, 'name': '(corrupted manifest)',
                           'imported_at': '', 'status': 'MANIFEST_CORRUPTED'})
    return sorted(result, key=lambda x: x.get('imported_at', ''), reverse=True)


def original_file(root, pid):
    root = workspace(root)
    if not re.fullmatch(r'[0-9a-f]{12}', str(pid)):
        raise ValueError('Invalid product id')
    manifest = json.loads((root / 'originals' / pid / 'manifest.json').read_text(encoding='utf-8'))
    src = root / 'originals' / pid / manifest['name']
    if sha256(src) != manifest['sha256']:
        raise ValueError('Original hash mismatch: stop')
    return src, manifest


def verify_original(root, pid):
    """True if the locked original still matches its import fingerprint."""
    try:
        original_file(root, pid)
        return True
    except (ValueError, OSError):
        return False


# ------------------------------------------------------------- extraction
def extract_text(src, max_chars=60000):
    src = Path(src)
    ext = src.suffix.lower()
    if ext == '.pdf':
        try:
            import fitz
        except ImportError:
            return '', 'Install PyMuPDF to inspect PDF text.'
        try:
            doc = fitz.open(src)
        except Exception as e:
            return '', f'PDF could not be opened: {e}'
        with doc:
            text = '\n'.join(page.get_text() for page in doc)
        if not text.strip():
            return '', 'Image-only PDF: manual page inspection or approved OCR is needed.'
        return text[:max_chars], ('PDF text truncated.' if len(text) > max_chars else '')
    if ext == '.zip':
        texts = []
        try:
            with zipfile.ZipFile(src) as z:
                for info in z.infolist():
                    if Path(info.filename).suffix.lower() in TEXT_EXT and not info.is_dir():
                        with z.open(info) as f:
                            data = f.read(20000 * 4)
                        texts.append(f'\n### FILE {info.filename}\n' +
                                     data.decode('utf-8', errors='replace')[:20000])
        except zipfile.BadZipFile as e:
            return '', f'Corrupted ZIP: {e}'
        alltext = '\n'.join(texts)
        return alltext[:max_chars], ('ZIP content truncated.' if len(alltext) > max_chars else '')
    return src.read_text(encoding='utf-8', errors='replace')[:max_chars], ''


def local_audit(src):
    text, warning = extract_text(src)
    issues = []
    if warning:
        issues.append({'severity': 'WARNING', 'detail': warning})
    if not text.strip():
        issues.append({'severity': 'BLOCKER', 'detail': 'No machine-readable source text available for validation.'})
    if src.suffix.lower() in {'.html', '.htm', '.zip'}:
        if '<script' in text and 'onclick=' in text:
            issues.append({'severity': 'INFO', 'detail': 'Inline event handlers found; inspect browser interactions.'})
        if re.search(r'(?i)\b(todo|fixme|placeholder)\b', text):
            issues.append({'severity': 'REVIEW', 'detail': 'Placeholder/TODO/FIXME text found; human inspection needed.'})
    return {'issues': issues, 'chars_reviewed': len(text), 'source_hash': sha256(src), 'text': text}


def create_audit(root, pid):
    src, m = original_file(root, pid)
    audit = local_audit(src)
    report = {k: v for k, v in audit.items() if k != 'text'}
    report.update({'product_id': pid, 'product_name': m['name'], 'roles': ROLES,
                   'product_type': m.get('product_type', detect_product_type(src)['type']),
                   'quality_score': 'NOT_MEASURED', 'release': 'BLOCKED_PENDING_INDEPENDENT_TESTS',
                   'created_at': utcnow()})
    out = workspace(root) / 'reports' / f'{pid}_audit.json'
    write_json(out, report)
    return report


# -------------------------------------------------------------- proposals
def save_proposal(root, pid, proposed_text, reason):
    src, m = original_file(root, pid)
    if src.suffix.lower() not in {'.html', '.htm', '.js', '.css', '.txt', '.md', '.json'}:
        raise ValueError('Direct text proposals only; PDFs and ZIPs require source-aware editors.')
    if not proposed_text.strip():
        raise ValueError('Empty proposal')
    if not str(reason).strip():
        raise ValueError('A change reason is required')
    outdir = workspace(root) / 'proposals' / pid
    outdir.mkdir(parents=True, exist_ok=True)
    candidate = outdir / (uuid.uuid4().hex[:8] + '_' + src.name)
    atomic_write_text(candidate, proposed_text)
    record = {'product_id': pid, 'original_sha256': m['sha256'], 'candidate': str(candidate),
              'candidate_sha256': sha256(candidate), 'reason': reason,
              'status': 'AWAITING_OWNER_APPROVAL', 'quality_score': 'NOT_MEASURED',
              'created_at': utcnow()}
    write_json(candidate.with_suffix(candidate.suffix + '.review.json'), record)
    return record


def approve_proposal(root, pid, candidate_path, explicit_approval=False):
    """Low-level copy of a proposal into approved/. Requires explicit approval.

    NOTE: the full release path (release.py) additionally requires a Release QA
    PASS decision; the desktop UI only exposes that gated path.
    """
    if explicit_approval is not True:
        raise PermissionError('Explicit owner approval required')
    src, m = original_file(root, pid)
    candidate = Path(candidate_path).resolve()
    proposal_dir = (workspace(root) / 'proposals' / pid).resolve()
    if not candidate.is_relative_to(proposal_dir):
        raise ValueError('Candidate outside proposal directory')
    meta_path = candidate.with_suffix(candidate.suffix + '.review.json')
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    if meta['original_sha256'] != m['sha256'] or meta['candidate_sha256'] != sha256(candidate):
        raise ValueError('Proposal integrity mismatch')
    approved = workspace(root) / 'approved' / pid
    approved.mkdir(parents=True, exist_ok=True)
    out = approved / (uuid.uuid4().hex[:8] + '_' + src.name)
    shutil.copy2(candidate, out)
    meta['status'] = 'OWNER_APPROVED_COPY'
    meta['approved_copy'] = str(out)
    meta['approved_at'] = utcnow()
    write_json(meta_path, meta)
    return out


class Budget:
    def __init__(self, cap_usd=1.0, max_attempts=3):
        if not 0 < cap_usd <= 20 or not 1 <= max_attempts <= 5:
            raise ValueError('Budget limits exceeded')
        self.cap_usd = cap_usd
        self.max_attempts = max_attempts

    def can_continue(self, attempts, estimated_spent):
        return attempts < self.max_attempts and estimated_spent < self.cap_usd
