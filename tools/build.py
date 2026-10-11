#!/usr/bin/env python3
"""Build the extended Power Tool by INSERTING two blocks into the original file.

Insertion points (the only places touched):
  1. a new <style id="bwm-style"> immediately before </head>
  2. a new <script id="bwm-script"> immediately before </body>
Every original byte is kept in order; tools/verify.py proves it.
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ORIG = ROOT / "original" / "Byrdway_Algebra_Power_Tool_ORIGINAL.html"
OUT = ROOT / "dist" / "Byrdway_Algebra_Power_Tool_PLUS_Mastery.html"
LANGS = ["en", "es", "zh", "hi", "ar", "fr", "pt", "ru", "ht", "vi", "ko", "ja"]

def main():
    html = ORIG.read_text(encoding="utf-8")
    css = (ROOT / "src" / "addon.css").read_text(encoding="utf-8")
    content = (ROOT / "src" / "content.js").read_text(encoding="utf-8")
    engine = (ROOT / "src" / "addon.js").read_text(encoding="utf-8")
    i18n = {}
    for l in LANGS:
        p = ROOT / "src" / "i18n" / f"{l}.json"
        if p.exists():
            i18n[l] = json.loads(p.read_text(encoding="utf-8"))
    i18n_js = json.dumps(i18n, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    script = ("(function(){\n'use strict';\n" + content + "\nconst BWM_I18N = " + i18n_js + ";\n"
              + engine + "\n})();\n")
    assert "</script" not in script.lower()
    style_block = '<style id="bwm-style">\n' + css + '</style>\n'
    script_block = '<script id="bwm-script">\n' + script + '</script>\n'
    assert html.count("</head>") == 1 and html.count("</body>") == 1
    out = html.replace("</head>", style_block + "</head>", 1).replace("</body>", script_block + "</body>", 1)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(out, encoding="utf-8")
    print(f"built {OUT.relative_to(ROOT)} ({len(out):,} bytes; languages: {', '.join(i18n)})")

if __name__ == "__main__":
    sys.exit(main())
