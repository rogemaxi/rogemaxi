# ByrdWay Algebra 1 + Honors Power Tool

* **Product:** `ByrdWay_Algebra_Honors_Upgrade_V3.html`. A standalone file; open it in any browser.
* **Release report:** [`RELEASE_REPORT.md`](RELEASE_REPORT.md) covers the defect inventory, change log, math evidence, language coverage and release gates.

## Rebuild (never edits the original)
```
python3 tools/check_i18n.py      # translation completeness + math fidelity, all 11 languages
python3 tools/build.py           # original/ + i18n/  ->  ByrdWay_Algebra_Honors_Upgrade_V3.html
```

## Certify
```
node tests/verify.js ByrdWay_Algebra_Honors_Upgrade_V3.html original/ByrdWay_Algebra_Honors_Upgrade_V2.original.html
node tests/english_words.js ByrdWay_Algebra_Honors_Upgrade_V3.html
node tests/dump_items.js ByrdWay_Algebra_Honors_Upgrade_V3.html items.json && python3 tests/verify_math.py items.json   # needs: pip install sympy
```

## Add a language
1. Copy `i18n/ui.en.json` and `i18n/content.en.json` to `<code>.json`, and translate the values. Keep every number and math expression verbatim.
2. Add `['<code>','<native name>','ltr'|'rtl']` to `BWM_LANGS`, and the code to `LANGS` in `tools/build.py` and `tools/check_i18n.py`.
3. Run `check_i18n.py`, then `build.py`, then the certification suite.
