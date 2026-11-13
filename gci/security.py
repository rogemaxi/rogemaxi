"""Credential handling, secret redaction, backup and restore (SSOI Phase 17).

* Credentials are stored only via Windows DPAPI (per-user encryption). On other
  platforms the store refuses to persist secrets rather than fall back to plaintext.
* `redact()` scrubs secret-shaped strings from anything written to logs/reports.
* Backups use SQLite's online backup API and are verified by re-opening and
  checking the event hash chain.
"""
import ctypes
import json
import re
import sqlite3
import sys
from pathlib import Path

SECRET_PATTERNS = [re.compile(p) for p in (
    r"sk-[A-Za-z0-9_\-]{16,}", r"(?i)bearer\s+[A-Za-z0-9._\-]{16,}", r"AKIA[0-9A-Z]{16}",
    r"(?i)(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*['\"]?[^\s'\"]{6,}",
    r"gh[pousr]_[A-Za-z0-9]{30,}", r"xox[baprs]-[A-Za-z0-9-]{10,}")]


def redact(text: str) -> str:
    for p in SECRET_PATTERNS:
        text = p.sub("[REDACTED]", text)
    return text


SCAN_PATTERNS = SECRET_PATTERNS[:3] + SECRET_PATTERNS[4:] + [
    re.compile(r"(?i)(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*['\"](?!__)[^'\"\s]{8,}['\"]")]


def scan_for_secrets(root) -> list:
    """Repository scan: literal secret values only (code like `token=True` is not a finding)."""
    hits = []
    for path in Path(root).rglob("*"):
        if path.is_file() and path.suffix in (".py", ".json", ".md", ".html", ".bat", ".txt", ".csv", ".toml", ".cfg"):
            if ".git" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for p in SCAN_PATTERNS:
                for m in p.finditer(text):
                    if "[REDACTED]" in m.group(0) or "example" in m.group(0).lower():
                        continue
                    hits.append({"file": str(path), "pattern": p.pattern})
    return hits


class CredentialStoreUnavailable(Exception):
    pass


class _BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _dpapi(data: bytes, protect: bool) -> bytes:
    if sys.platform != "win32":
        raise CredentialStoreUnavailable("Encrypted credential storage requires Windows DPAPI; refusing plaintext.")
    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    buf = ctypes.create_string_buffer(data, len(data))
    inp, out = _BLOB(len(data), buf), _BLOB()
    fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    if not fn(ctypes.byref(inp), None, None, None, None, 0, ctypes.byref(out)):
        raise CredentialStoreUnavailable("DPAPI call failed")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        kernel32.LocalFree(out.pbData)


class CredentialStore:
    """Holds API keys for *data providers only*. Brokerage passwords are refused outright."""
    FORBIDDEN = ("jpmorgan", "chase", "bank", "brokerage")

    def __init__(self, path):
        self.path = Path(path)

    def put(self, name: str, secret: str):
        if any(f in name.lower() for f in self.FORBIDDEN):
            raise PermissionError("Brokerage/bank credentials are never stored by GCI.")
        blob = _dpapi(secret.encode(), True)
        data = self._load()
        data[name] = blob.hex()
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def get(self, name: str) -> str:
        data = self._load()
        if name not in data:
            return None
        return _dpapi(bytes.fromhex(data[name]), False).decode()

    def revoke(self, name: str):
        data = self._load()
        data.pop(name, None)
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def _load(self):
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}


def backup(store, dest) -> dict:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    target = sqlite3.connect(str(dest))
    store.conn.backup(target)
    target.close()
    store.log("system", "BACKUP_CREATED", {"file": dest.name})
    return {"file": str(dest), "bytes": dest.stat().st_size}


def restore(backup_file, dest_path, dataset):
    from .db import Store
    src = sqlite3.connect(str(backup_file))
    if Path(dest_path).exists():
        raise FileExistsError("Restore target exists; restore into a new path, then swap after verification.")
    dst = sqlite3.connect(str(dest_path))
    src.backup(dst)
    src.close()
    dst.close()
    st = Store.open(dest_path, dataset)
    chain = st.verify_chain()
    if not chain["ok"]:
        st.close()
        raise ValueError(f"Restored database failed integrity check: {chain}")
    st.log("system", "RESTORED_FROM_BACKUP", {"file": Path(backup_file).name, "events_verified": chain["events_checked"]})
    return st
