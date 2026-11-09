# ByrdWay Product Engineering Studio — Installation & User Guide (v0.4.2)

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
See **OWNER_QUICK_START.md** (also under Help → Quick Start) for the short version.
1. **Products tab → ① Import Product…** The original is copied, fingerprinted (SHA-256) and locked.
2. **② Diagnose (no changes)** opens a readable report: every finding is **DETECTED** (a test failed) or
   **SUSPECTED** (needs a look), with the exact **proposed correction** or "needs a person".
3. **③ Repair a Copy & Verify** applies proposed corrections to a working copy (one at a time, checkpointed,
   rolled back on regression), re-tests in a sandboxed browser, re-verifies every answer, and hands the candidate to
   **Release QA**, which re-tests it from scratch. The repair report shows each defect's state:
   VERIFIED (QA confirmed it is gone) · NOT AUTO-FIXABLE · REVERTED (caused a regression) · RESOLVED BY RELATED FIX,
   plus before/after screenshots (desktop + phone) and before/after PDF pages.
4. **Jobs tab**: the coloured **NEXT STEP** line tells you what to do. **Open Readable Report**, **Before / After
   Diff**, **Open Evidence Folder**, **Re-run Release QA**, **Attest Unverifiable Item…**, **APPROVE for release…**,
   **Reject…**, **Export Approved…**. Approval is refused unless Release QA passed; export is refused unless approved.

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

## 4. New products (builders tab)
Numbered steps on screen: **1** choose product type · **2** create a blueprint with the fill-in form (no JSON), open a
saved blueprint/draft, or practise with the sample (always marked SAMPLE and blocked at release) · **3** register
approved assets (page template / Lil Dr. Byrd image) — a ✔/✖ checklist shows what is missing and why · **4** build one
unit, open it, approve or reject it, then **Assemble, verify & send to Jobs**. Every answer is verified while building;
a wrong answer blocks that unit with a plain explanation. Builds are saved continuously and can be resumed any time.

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

## 7. Windows .exe (optional)
A tested build is produced automatically on every change (GitHub → Actions → "ByrdWay Studio - Windows
verification" → artifact **ByrdWayStudio-Windows-exe**). You can also build it yourself with
`build_windows_exe.bat`. The exe passes the full self-test on Windows in CI. It is not code-signed, so
SmartScreen will warn once (More info → Run anyway). Chromium is not bundled: run `install_windows.bat` once
(or `python -m playwright install chromium`).

## 8. Health check
`START_WINDOWS.bat` users: open a Command Prompt in the folder and run `.venv\Scripts\python app.py --selftest`.
exe users: `ByrdWayStudio.exe --selftest`. It repairs products with planted defects in a temporary folder and
writes `selftest_report.json`; `"passed": true` means the whole pipeline works on this PC.

## 9. Running tests
`run_tests_windows.bat` or `python -m unittest discover -s tests -v`.
