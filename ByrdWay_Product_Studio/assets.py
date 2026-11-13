"""Approved asset registry (mascots, logos, templates, illustrations).

Only the owner registers assets. Each is copied, SHA-256 fingerprinted and
locked read-only. Builders may ONLY use registered assets; nothing here can
generate or substitute artwork.
"""
import re, shutil
from pathlib import Path
from engine import workspace, sha256, write_json, read_json, utcnow, make_read_only

KINDS = {'mascot', 'logo', 'template', 'illustration', 'font', 'reference_product', 'voice'}
LIL_DR_BYRD_ID = 'lil_dr_byrd'


def _reg_path(root):
    return workspace(root) / 'assets' / 'registry.json'


def registry(root):
    p = _reg_path(root)
    return read_json(p) if p.exists() else {}


def register_asset(root, src, asset_id, kind, note='', owner_confirmed=False):
    if owner_confirmed is not True:
        raise PermissionError('Only the owner can register an approved asset (owner_confirmed=True)')
    if not re.fullmatch(r'[a-z0-9_\-]{2,60}', asset_id):
        raise ValueError('asset_id must be lowercase letters, digits, _ or -')
    if kind not in KINDS:
        raise ValueError(f'kind must be one of {sorted(KINDS)}')
    src = Path(src)
    if not src.is_file():
        raise ValueError('Asset file not found')
    reg = registry(root)
    if asset_id in reg:
        raise ValueError('Asset id already registered; approved assets are never silently replaced')
    dest_dir = workspace(root) / 'assets' / asset_id
    dest_dir.mkdir(parents=True)
    dest = dest_dir / src.name
    shutil.copy2(src, dest)
    make_read_only(dest)
    reg[asset_id] = {'id': asset_id, 'kind': kind, 'file': str(dest), 'name': src.name,
                     'sha256': sha256(dest), 'registered_at': utcnow(), 'note': note}
    write_json(_reg_path(root), reg)
    return reg[asset_id]


def get_asset(root, asset_id):
    """Return verified asset record or None if not registered. Raises on tamper."""
    rec = registry(root).get(asset_id)
    if not rec:
        return None
    if not Path(rec['file']).exists() or sha256(rec['file']) != rec['sha256']:
        raise ValueError(f'Approved asset {asset_id} has been modified or removed: STOP')
    return rec
