"""Build the release ZIP and its SHA-256. Usage: python tools/package.py"""
import hashlib, subprocess, sys, zipfile
from pathlib import Path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from gci import VERSION
from gci.security import scan_for_secrets
hits = [h for h in scan_for_secrets(root) if "tests" not in h["file"] and "security.py" not in h["file"]]
if hits:
    sys.exit(f"Refusing to package: secret-shaped strings found {hits}")
commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True).stdout.strip()
dist = root / "dist"; dist.mkdir(exist_ok=True)
name = f"GenesisCapitalIntelligence-{VERSION}-{commit}"
out = dist / f"{name}.zip"
include = ["gci", "tests", "data", "docs", "tools", "README.md", "Launch GCI.bat", "Run Acceptance Demo.bat"]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for item in include:
        p = root / item
        files = [p] if p.is_file() else sorted(x for x in p.rglob("*") if x.is_file() and "__pycache__" not in x.parts)
        for f in files:
            z.write(f, f"{name}/{f.relative_to(root).as_posix()}")
digest = hashlib.sha256(out.read_bytes()).hexdigest()
(dist / f"{name}.zip.sha256").write_text(f"{digest}  {out.name}\n")
print(out, digest)
