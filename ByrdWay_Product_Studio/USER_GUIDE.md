# ByrdWay Product Engineering Studio — Installation & User Guide (v0.2)

Owner: Genesis 2 & 7, LLC · ByrdWay Mathematics & Science. Runs locally on Windows 11. No Claude/Anthropic
account is needed. OpenAI is optional and only used when you allow it.

## 1. Install (once)
1. Install **Python 3.12** from python.org and tick **"Add python.exe to PATH"**.
2. Extract this folder somewhere permanent, for example `Documents\ByrdWay_Studio_App`.
3. Double-click **`install_windows.bat`**. It creates a private environment (`.venv`), installs the pinned
   libraries from `requirements.txt`, asks before downloading the Chromium browser engine (~150 MB, needed for
   Power Tool browser tests), then runs the self-test.
4. Start the Studio with **`START_WINDOWS.bat`**.

Your data lives in `Documents\ByrdWay_Product_Studio` (originals, jobs, reports, exports, backups, logs, settings).

## 2. Everyday workflow: repair an existing product
1. **Products tab → Import Product…** Choose a Power Tool (`.html` or `.zip`) or an Explainer / Concept Tiles PDF.
   The original is copied, fingerprinted (SHA-256) and locked. Your own file is never changed.
2. Select it → **Run Repair & Verify Job**. The Studio:
   * finds defects (wrong answers, broken buttons, JS errors, missing images, broken links, accessibility,
     PDF page/numbering/TOC issues, wrong arithmetic in explainers),
   * applies the smallest safe fixes to a **working copy** (one at a time, checkpointed, rolled back on regression),
   * re-tests in a sandboxed browser and independently re-verifies every answer,
   * hands the repacked candidate to **Release QA**, which re-tests it from scratch and decides
     PASS / BLOCKED / NOT_VERIFIED / BELOW_TARGET.
3. **Jobs tab**: read the report and every QA check; **Before / After Diff** shows exact line changes;
   **Open Evidence Folder** shows screenshots (desktop + phone), PDF page renders and visual diffs.
4. If QA says **NOT_VERIFIED** because some questions cannot be checked automatically (e.g. essay questions,
   image-only pages), review them yourself, then **Attest Unverifiable Item…** (use a key from the list, or `ALL`).
   Attestation never overrides a failed check.
5. If QA says **PASS**: **APPROVE for release…** (type your name; for PDFs you must confirm you looked at the page
   images), then **Export Approved…**. The export folder contains the product, the full audit trail and
   `SHA256SUMS.txt`. Nothing is uploaded; you publish to TpT yourself.
6. **BLOCKED** means a defect needs human attention; the report lists each one under *Human escalation required*.

## 3. Optional AI assistance (OpenAI)
1. **API Costs & Settings tab**: set *Owner-authorized funding* to what you actually added (e.g. 10), keep a
   *Reserve* (default $1), and per-job / per-day caps.
2. **Store OpenAI API key…** (saved in Windows Credential Manager) or set the `OPENAI_API_KEY` user
   environment variable. The key never appears in files or logs.
3. On the Products tab tick *Allow AI repair suggestions*. When deterministic fixes run out, the Studio may ask to
   send product text to OpenAI; **every call shows its estimated maximum cost and needs your Yes.**
   AI suggestions are tested exactly like any other change and cannot pass QA unless they actually fix the defect.
4. The ledger shows each call. It is a local record, **not** your verified OpenAI balance — check the
   OpenAI dashboard. Prices in `settings.json` were copied from developers.openai.com/api/docs/pricing on
   2026-11-09; re-check before funding. A model without a configured price cannot be called.

## 4. New products (builders)
* Write a blueprint JSON (see `samples\SAMPLE_power_tool_blueprint.json` and
  `samples\SAMPLE_lil_dr_byrd_physics_blueprint.json` — format examples only, not approved content).
* **Register Approved Asset…** first: your approved ByrdWay HTML template (kind `template`, must contain
  `{{CONTENT}}`; optional `{{TITLE}}`, `{{SCRIPT}}`) and the **Lil Dr. Byrd** image (id `lil_dr_byrd`, kind `mascot`).
  The Studio never draws or substitutes the mascot; without it the chapter is built text-only and marked
  BLOCKED_MISSING_APPROVED_ASSET.
* **Builders tab → New … Build → Build Next Module/Chapter**. Every answer is verified; a wrong answer blocks the
  module. Open the output, then **Approve Selected Unit…**. The next unit cannot be built until the previous one is
  approved. When all are approved, **Assemble & Import for QA**, then run a Repair & Verify job on the package.
* Builds using the built-in *provisional* layout are always BLOCKED at Release QA until an approved template is used.

## 5. Backup & restore
**Backup & Restore tab → Create verified backup now** (saved in `backups\`, every file hash-checked).
**Restore from backup…** verifies the backup first and saves a safety copy of the current workspace next to it.

## 6. Clean-machine smoke test (run after install or after building the .exe)
1. `run_tests_windows.bat` → expect `OK` (UI test may be skipped only if no display).
2. Start the app. Import a real Power Tool ZIP (a copy, not your only one). Run a job; confirm the Jobs tab shows a QA
   decision and `Open Evidence Folder` contains `baseline_desktop.png` and `baseline_mobile.png`.
3. Confirm the original in `Documents\ByrdWay_Product_Studio\originals\<id>\` still has the SHA-256 shown on import
   (Products → Verify Originals).
4. Approve a PASS job, export it, and confirm `SHA256SUMS.txt` exists in the export.
5. Create a backup; restore it into the same workspace; Verify Originals again.
6. With no API key configured, confirm the Costs tab says "API key configured: NO" and jobs still run.
Record results; report any failure with `logs\activity.jsonl`.

## 7. Building a Windows .exe (optional)
`build_windows_exe.bat` builds `dist\ByrdWayStudio\ByrdWayStudio.exe` with PyInstaller using
`byrdway_studio.spec`. **This has not been built or tested on Windows by the developer**; run the smoke test above
on the built exe before relying on it. Chromium is not bundled; run `install_windows.bat` (or
`python -m playwright install chromium`) once on the machine.

## 8. Running tests
`run_tests_windows.bat` or `python -m unittest discover -s tests -v`.
