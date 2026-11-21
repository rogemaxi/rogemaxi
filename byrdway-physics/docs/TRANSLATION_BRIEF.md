# Content translation brief (for translation agents)

Project root: /home/user/rogemaxi/byrdway-physics. Translate instructional CONTENT into ONE target language for the assigned scope.

## Find what is missing
`node tools/i18n.mjs merge`, then compare `node tools/i18n.mjs keys <scopes>` with `src/data/i18n/content/<lang>.json`; translate only keys that are missing. Scopes:
- Unit N (lessons): `unit.N 'N.*'` → file `src/data/i18n/content/<lang>/uNN.json` (NN two-digit).
- Labs: `'lab.*'` → `<lang>/labs.json` (lab05.json already exists for Lab 5 — keep it; do not duplicate its keys).
- Assessment bank: `'bank.*'` → `<lang>/bank.json` (≈1 900 keys — work in chunks of ~150).
- Reference: `'ref.*'` → `<lang>/ref.json`.
Keep existing entries in a file and add the missing keys. Work in chunks (one section or ~150 keys at a time) and write chunks to disk as you go (merge them with a small node script) so progress is never lost. Write JSON with JSON.stringify(obj, null, 1).

## Rules
- Natural, accurate, student-friendly secondary-school register with that language's standard physics terminology; read `<lang>/u05.json` and `src/data/i18n/ui/<lang>.json` first and stay consistent with them.
- Keep formulas, symbols, variable names, units and chemical symbols exactly. EVERY digit sequence in the English must appear as ASCII digits in the translation (no spelled-out numbers, no native digit systems, no converting e.g. "1600s" into centuries).
- Keep any {placeholder} and **bold** markers. Translate "AP Physics C extension:" / "A Level extension:" with the word for "extension" but keep "AP Physics C" / "A Level" in Latin script.
- Complete meaning, no omissions; misconception "wrong" statements must stay wrong.

## Verify
After each unit/file: `node tools/i18n.mjs merge` then `node --test tests/unit/i18n.test.js`. Fix every failure naming your language and keys. Failures for other languages are other agents' — ignore them.

Do NOT edit any other file. Do NOT commit. Report: files completed, key counts, i18n test status for your language.
