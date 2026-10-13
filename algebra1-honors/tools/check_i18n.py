#!/usr/bin/env python3
"""Validate translation catalogs: completeness, placeholders, and mathematical fidelity.

Math fidelity rule: every number and every math token (anything containing = < > ^ ( ) / or a
digit next to a letter, e.g. abs(x-5)=3, 2x^2, f^-1(11)) in an English stem/explanation must
appear verbatim, the same number of times, in the translation. Translators may not edit math.
Usage: python3 tools/check_i18n.py [lang ...]
"""
import json, pathlib, re, sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
LANGS = sys.argv[1:] or ["es", "zh", "hi", "ar", "fr", "pt", "ru", "ht", "vi", "ko", "ja"]
en_ui = json.loads((ROOT / "i18n/ui.en.json").read_text())
en_c = json.loads((ROOT / "i18n/content.en.json").read_text())
NUM = re.compile(r"-?\d+(?:\.\d+)?")
MATH = re.compile(r"[^\s,;:?]*[=<>^()/][^\s,;:?]*|\b\d+[a-z]\S*")
PH = re.compile(r"\{\w+\}")
# Terms the original catalog already keeps in English for that language (e.g. pt step_flash = "Flashcards").
SAME_OK = {"pt": {"nav_flash", "need3_p", "eng_flash"}}

def toks(s):
    return Counter(NUM.findall(s)), Counter(m.strip(".,;:") for m in MATH.findall(s) if re.search(r"[\dxy]", m))

bad = 0
for l in LANGS:
    ui = json.loads((ROOT / f"i18n/ui.{l}.json").read_text())
    c = json.loads((ROOT / f"i18n/content.{l}.json").read_text())
    probs = []
    for k, v in en_ui.items():
        if k not in ui: probs.append(f"ui missing {k}"); continue
        if set(PH.findall(v)) != set(PH.findall(ui[k])): probs.append(f"ui placeholder mismatch {k}")
        if l != "en" and ui[k] == v and re.search(r"[a-z]{4}", v) and k not in ("nav_blueprint", "need2_p", "eng_blueprint") and k not in SAME_OK.get(l, ()):
            probs.append(f"ui untranslated {k}")
    for part in ("stems", "prose", "skills", "tags"):
        if len(c[part]) != len(en_c[part]): probs.append(f"{part} count {len(c[part])} != {len(en_c[part])}"); continue
        if part in ("stems", "prose"):
            for i, (e, t) in enumerate(zip(en_c[part], c[part])):
                en_n, en_m = toks(e); tr_n, tr_m = toks(t)
                if en_n - tr_n: probs.append(f"{part}[{i}] numbers lost {dict(en_n - tr_n)}")
                missing_m = [m for m in en_m if t.count(m) < en_m[m]]
                if missing_m: probs.append(f"{part}[{i}] math changed {missing_m}")
        for i, (e, t) in enumerate(zip(en_c[part], c[part])):
            if l != "en" and e == t and re.search(r"[a-z]{4}", e) and part != "prose" and ("-" in e or " " in e): probs.append(f"{part}[{i}] untranslated")
    print(f"{l}: {'OK' if not probs else str(len(probs)) + ' problem(s)'}")
    for p in probs[:25]: print("   ", p)
    bad += len(probs)
sys.exit(1 if bad else 0)
