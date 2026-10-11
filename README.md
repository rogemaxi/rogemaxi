# Byrdway Algebra Power Tool — Mastery Add-On

**Deliverable:** `dist/Byrdway_Algebra_Power_Tool_PLUS_Mastery.html` (one file, works offline).

## Add-only guarantee
The original file (`original/…ORIGINAL.html`, sha256 `4d24aef9…2bd66`) is never edited.
The build inserts exactly two blocks: a `<style id="bwm-style">` before `</head>` and a
`<script id="bwm-script">` before `</body>`. `tools/verify.py` strips both blocks and proves the
result is byte-identical to the original.

## What was added
- **Mastery Hub** on the Home dashboard plus a nav link on every page.
- **Diagnostic Test**: 25 questions covering all 10 areas, auto-scored, with results by area.
- **Prescriptive Plan**: areas ranked weakest → strongest (Fix First / Build / Strengthen / Extend) with linked next steps into the existing tabs.
- **First-Principles Lessons** for all 10 areas: Principle → Why → Build step by step → Check → Your Turn → Go deeper. A "🧠 First Principles" tab is added to each area.
- **EOC Checkouts**: five exams of 15 questions each — DOK 2.5, DOK 3, DOK 3.5, DOK 4, Extreme Mastery — with step-by-step solutions and an 80% mastery bar.
- **12 languages**: English, Español, 中文, हिन्दी, العربية (RTL), Français, Português, Русский, Kreyòl Ayisyen, Tiếng Việt, 한국어, 日本語. Only the wording changes. The math is stored once and marked `translate="no"`.

Progress is saved in the browser's localStorage, so it is per-device.

## Build & verify
```
python3 tools/build.py                          # assemble dist/
python3 tools/verify.py                         # add-only proof + i18n completeness + numbers unchanged
NODE_PATH=$(npm root -g) node tools/e2e.mjs     # 130 headless-browser checks
```
Edit content in `src/content.js` (math), `src/i18n/*.json` (wording), `src/addon.js` / `src/addon.css` (engine/UI).
