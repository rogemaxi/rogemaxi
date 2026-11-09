# ByrdWay Product Engineering Studio v0.2

**Status:** working local application with a tested repair → verify → QA → owner-approval → export pipeline,
desktop UI, cost-controlled optional OpenAI assistance and 96 automated tests (see `TEST_RESULTS.md`).
**Not yet production-verified:** it has not been run against a real owner product or on Windows 11
(see `KNOWN_LIMITATIONS.md`). No 99.9 claim is made for any real product until Release QA measures it.

Owner: Genesis 2 & 7, LLC · ByrdWay Mathematics & Science. Claude is not required at runtime.

## Quick start (Windows 11)
1. Install Python 3.12 (tick *Add to PATH*).
2. Double-click `install_windows.bat` (installs pinned libraries, optionally Chromium, runs self-test).
3. Double-click `START_WINDOWS.bat`.
Full instructions: **`USER_GUIDE.md`**.

## The seven roles (one coordinated application)
| # | Role | Implementation |
|---|---|---|
| 1 | Master Orchestrator | `orchestrator.Orchestrator` — job state machine, bounded loop (iterations, runtime, no-progress, repeated-failure), checkpoints, rollback, evidence log, escalation |
| 2 | Power Tool Repair | `htmlaudit.py` static audit + minimal deterministic fixes; `browsertest.py` sandboxed Chromium tests; optional AI patch suggestions |
| 3 | Explainer Repair | `pdftools.py` — structure audit, page renders, before/after visual diff, evidence-backed region corrections on text-layer pages only |
| 4 | Power Tool Builder | `builders.build_power_tool_module` — blueprint-driven, one module at a time, owner approval gates, provenance |
| 5 | Lil Dr. Byrd Builder | `builders.build_lil_dr_byrd_chapter` — print-ready PDF, approved mascot only (registry), never substituted |
| 6 | Academic Verifier | `academic.py` — deterministic, two independent methods per item, unsupported domains flagged |
| 7 | Release QA | `orchestrator.ReleaseQAAgent` — re-extracts and re-tests the candidate, replays the patch history, scores (`quality.py`), can BLOCK; nothing bypasses it |

## Files
| Area | Files |
|---|---|
| Core / safety | `engine.py` (import, hashing, ZIP safety, v0.1 API kept), `zipproject.py` (working copies, diff, checkpoints, repack), `assets.py` |
| Verification | `academic.py`, `htmlaudit.py`, `browsertest.py`, `pdftools.py`, `quality.py` |
| Workflow | `orchestrator.py`, `release.py` (attest, approve, reject, export, backup, restore), `builders.py` |
| AI & cost | `ai_roles.py`, `costs.py`, `config.py` |
| UI | `app.py` (Tk desktop), `controller.py` (UI-free facade) |
| Windows | `install_windows.bat`, `START_WINDOWS.bat`, `run_tests_windows.bat`, `build_windows_exe.bat`, `byrdway_studio.spec`, `requirements*.txt` |
| Docs | `USER_GUIDE.md`, `QUALITY_SCORING.md`, `SECURITY_REVIEW.md`, `KNOWN_LIMITATIONS.md`, `TEST_RESULTS.md`, `CLAUDE.md` (dev contract) |
| Samples | `samples/` — blueprint *format* examples (not approved content) |

## Non-negotiables enforced in code
Originals immutable (SHA-256, read-only, re-verified at every gate) · working copies only · atomic writes ·
no uploads/publishing code · every paid API call estimated, capped and individually approved · keys never stored
in files or logs · weighted score can never hide a critical failure · NOT_VERIFIED instead of an invented score ·
explicit named owner approval before export.

## Run tests
`python -m unittest discover -s tests -v`
(UI test: `xvfb-run -a python -m unittest tests.test_ui_smoke` on Linux; runs normally on Windows.)
