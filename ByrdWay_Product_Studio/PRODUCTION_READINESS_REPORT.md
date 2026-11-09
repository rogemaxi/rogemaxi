# Production Readiness Report — ByrdWay Product Engineering Studio v0.4.0

Date 2026-11-09. Evidence: Windows CI run https://github.com/rogemaxi/rogemaxi/actions/runs/42663089124 (commit
faa30e9, Microsoft Windows Server 2025, Python 3.12) plus local runs (Linux, Python 3.12 + Tk, Python 3.13).

## Verdict
* **Studio software acceptance criteria: PASS** — every workflow below was exercised end to end on Windows,
  including the real desktop window, with no skipped tests accepted.
* **Production certification for ByrdWay products: BLOCKED** — one criterion cannot be completed without the
  owner: running one *real* ByrdWay Power Tool and one *real* Explainer through the Studio
  (CLAUDE.md acceptance test). All product results so far use representative fixtures with planted defects.
  I am therefore **not** certifying production readiness.

## Workflow status
| Workflow / criterion | Status | Evidence |
|---|---|---|
| One consistent version | **PASS** | `version.py` = 0.4.0; title, Help → About, `--version`, self-test, installer/build banners, release name; CI: "Packaged exe version 0.4.0 matches version.py"; `test_v040.Version` |
| Windows install (pinned deps) | **PASS** (Windows Server 2025) | CI step "Install pinned dependencies" (same commands as `install_windows.bat`) |
| Windows startup, packaged .exe launch | **PASS** (Windows Server 2025) | "GUI started, stayed running 20s, workspace created"; .exe self-test 14/14 |
| Windows 11 desktop specifically | **NOT DIRECTLY TESTED** | GitHub provides no Windows 11 machines; Server 2025 shares the Windows 11 core. Owner check: Help → Run self-test (1 minute) |
| Every primary button works or explains why not | **PASS** | `test_every_button_is_wired`, `test_buttons_without_selection_explain_instead_of_failing` (16 buttons), all workflow tests below |
| Products: import → protected copy → diagnose → repair → readable report → before/after | **PASS** | `test_import_diagnose_repair_review_approve_export` (real window, Windows) |
| Import of supported formats (ZIP, HTML, PDF) | **PASS** with fixtures · **BLOCKED** for real owner files | 14 malicious-ZIP cases rejected; corrupted/mislabeled files refused with a logged, readable error |
| Jobs: inspect, diff, evidence, re-run QA, approve, reject, export | **PASS** | same test + `test_release_gate_blocks_and_reject_works` |
| Release gate blocks unverified / unapproved changes | **PASS** | approval refused for BLOCKED job (visible error), export refused without approval |
| Builders: create blueprint (form), validate, drafts/resume, build unit, review, approve, assemble, verify | **PASS** | 6 real-window builder tests incl. form → Windows-verified PASS candidate; wrong answer blocks unit with plain message |
| Approved assets: template, Lil Dr. Byrd image (never substituted) | **PASS** | `test_lil_dr_byrd_missing_mascot_then_registered`; asset tamper detection |
| Sample content never passes as approved material | **PASS** | `test_sample_content_blocks_release` (Release QA CRITICAL) |
| Repair engine states: detected / suspected / proposed / applied / verified / awaiting approval | **PASS** | `test_v040.Diagnosis` (incl. NOT_AUTO_FIXABLE reported, not faked) |
| Supported defects corrected on working copies; originals unchanged | **PASS** | wrong answers, wrong MC index, broken handler, missing asset, broken link, lang/viewport, PDF arithmetic; SHA-256 re-checked after export |
| Quality checks & regression tests | **PASS** | 127 tests on Windows; rollback-on-regression test |
| Backup and restore | **PASS** | GUI test `test_backup_and_restore`; damaged backup refused |
| API spending safeguards | **PASS** (mock client) | 19 cost/AI tests; Costs tab shows "AI processing: DISABLED — reason" |
| Live OpenAI call | **NOT TESTED (by design)** | no authorized key/funding; no charges incurred |
| Errors logged and recoverable | **PASS** | every UI error written to tab 6 (`test_bad_import_is_explained_and_logged`); Tk thread-abort defect fixed |
| Save/export permissions, working directories | **PASS** (Windows) | exports/workspace created and verified in CI temp folders |
| Antivirus compatibility | **NOT TESTABLE HERE** | unsigned .exe will trigger SmartScreen once; code signing requires a purchased certificate (owner decision) |
| Windows .exe + source release packaged | **PASS** | draft GitHub release "ByrdWay Product Engineering Studio v0.4.0" with `ByrdWayStudio_v0.4.0_Windows_exe.zip` and `ByrdWay_Product_Studio_v0.4.0_source.zip` (owner publishes) |
| Limitations documented | **PASS** | KNOWN_LIMITATIONS.md |

## To move "BLOCKED" to PASS
Upload one real Power Tool (ZIP/HTML) and one real Explainer/Concept Tiles PDF (with editable source if available).
I will run them through Diagnose → Repair → Release QA and report the measured result, adapting the answer-key
reader if your files use a format it does not yet recognise.
