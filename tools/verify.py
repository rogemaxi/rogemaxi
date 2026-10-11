#!/usr/bin/env python3
"""Proves the add-on is additive and the language packs are complete.

1. Removing the two inserted blocks from the build yields the ORIGINAL file byte-for-byte.
2. Every wording key used by the add-on exists in English, and every language
   pack has every English key.
3. Translations do not change the math: every number in an English string
   appears, unchanged, in its translation (CJK counting digits such as "2 点"
   for "two points" may be added).
"""
import json, pathlib, re, sys, hashlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
ORIG = ROOT / "original" / "Byrdway_Algebra_Power_Tool_ORIGINAL.html"
OUT = ROOT / "dist" / "Byrdway_Algebra_Power_Tool_PLUS_Mastery.html"
LANGS = ["en", "es", "zh", "hi", "ar", "fr", "pt", "ru", "ht", "vi", "ko", "ja"]
fails = []

orig = ORIG.read_bytes()
built = OUT.read_text(encoding="utf-8")
stripped = re.sub(r'<style id="bwm-style">.*?</style>\n', "", built, count=1, flags=re.S)
stripped = re.sub(r'<script id="bwm-script">.*?</script>\n', "", stripped, count=1, flags=re.S)
if stripped.encode("utf-8") != orig:
    fails.append("original bytes changed")
print("original sha256 ", hashlib.sha256(orig).hexdigest())
print("stripped sha256 ", hashlib.sha256(stripped.encode()).hexdigest())

src = (ROOT / "src" / "content.js").read_text(encoding="utf-8") + (ROOT / "src" / "addon.js").read_text(encoding="utf-8")
en = json.loads((ROOT / "src/i18n/en.json").read_text(encoding="utf-8"))
used = set(re.findall(r"s:'([a-z0-9_]+)'", src)) | set(re.findall(r"'@([a-z0-9_]+)'", src)) | set(re.findall(r"\['(op_[a-z]+)'", src))
used |= set(re.findall(r"(?<![A-Za-z])t\('([a-z0-9_]+)'[,)]", src))
missing = sorted(k for k in used if k not in en)
if missing:
    fails.append(f"keys missing from en.json: {missing}")

nums = lambda s: sorted(re.findall(r"\d+(?:[.,]\d+)*", s.replace(",", "")))
for l in LANGS:
    p = ROOT / "src/i18n" / f"{l}.json"
    if not p.exists():
        fails.append(f"{l}: pack missing"); continue
    d = json.loads(p.read_text(encoding="utf-8"))
    miss = [k for k in en if k not in d]
    if miss:
        fails.append(f"{l}: {len(miss)} keys missing e.g. {miss[:5]}")
    for k, v in en.items():
        if k in d and k != "_name":
            from collections import Counter
            lost = Counter(nums(v)) - Counter(nums(d[k]))
            if lost:
                fails.append(f"{l}.{k}: math numbers missing/changed {sorted(lost.elements())}")
            for ph in re.findall(r"\{[a-z]\}", v):
                if ph not in d[k]:
                    fails.append(f"{l}.{k}: placeholder {ph} missing")

print("\n".join(fails) if fails else "ALL CHECKS PASSED")
sys.exit(1 if fails else 0)
