# Root Cause Report — ByrdWay Product Engineering Studio v0.4.0

Scope: Studio software only. Each entry: **file / function — cause — impact — correction — proof**.
Accountability note: earlier messages stated the system was *not yet* production-ready, but the release I
delivered as "v0.3" had a wrong label and an unusable builder workflow. Both were my defects.

## Confirmed issues reported by the owner

### R1. Version mismatch ("v0.3" folder, "v0.2" app and docs) — LABELING ERROR
* **Where:** `app.py` (`APP_TITLE = '… | v0.2'` hard-coded); README, USER_GUIDE, QUALITY_SCORING, SECURITY_REVIEW,
  KNOWN_LIMITATIONS titles (hard-coded v0.2); the delivery archive name `v0_3` was typed by hand in the packaging
  command (`git archive --prefix=…v0_3`).
* **Determination:** labeling error only. The v0.3 ZIP contained the latest source (the same commit verified by
  Windows CI); no outdated executable was distributed (no .exe was handed over). It was still an incomplete
  release process: no single source of version truth and no check that labels agree.
* **Impact:** the owner could not tell which build was running.
* **Correction:** `version.py` is the only version source (0.4.0). Window title, `--version`, Help → About,
  self-test report, installer banner, build banner and the GitHub release name read it. CI fails if the packaged
  .exe reports a different version. `tests/test_v040.py::Version` fails if any document title disagrees.

### R2. Builder buttons labeled "New … Build" opened an unexplained file picker
* **Where:** `app.py` `App.new_build()` called `filedialog.askopenfilename` for an existing blueprint JSON.
* **Cause:** the builder *engine* (`builders.py`) was implemented and tested, but no blueprint-authoring UI
  existed; the UI exposed developer input (a JSON file) as the only entry point, with no explanation and no
  prerequisite check.
* **Impact:** the owner could not start a build without writing JSON by hand.
* **Correction:** Builders tab rebuilt as numbered steps:
  1 product type → 2 *Create new blueprint (form)* / *Open saved blueprint or draft* / *Practice with sample* (with
  an explicit "format example only" warning) → 3 register approved template / Lil Dr. Byrd image, with a live ✔/✖
  readiness checklist → 4 build unit, open for review, approve/reject, *Edit blueprint (new version)*,
  *Assemble, verify & send to Jobs*. Every button that needs a file explains the requirement before the picker.
  New `BlueprintEditor` (fill-in form, line formats shown on screen, validation with exact line numbers, drafts).
  New `builders.power_tool_blueprint_from_form`, `chapter_blueprint_from_form`, `prerequisites`, `save_blueprint`.
* **Proof:** `tests/test_gui_workflows.py::Builders` (6 real-window tests incl. form → verified PASS candidate,
  validation errors, draft resume, sample blocked, missing mascot then registered).

### R3. Workflow did not separate diagnosis, proposal, application, verification and approval
* **Where:** `orchestrator.Orchestrator.run_repair_job` applied fixes immediately; findings were shown as raw text.
* **Impact:** the owner could not review findings before changes, nor see each defect's state.
* **Correction:** `Orchestrator.diagnose()` (read-only; nothing changed, working copy removed) with
  DETECTED / SUSPECTED findings and exact proposed corrections; `correction_lifecycle()` gives each defect a state
  (PROPOSED_NOT_APPLIED, VERIFIED, VERIFIED_AWAITING_OWNER_APPROVAL, NOT_AUTO_FIXABLE, REVERTED_REGRESSION,
  APPLIED_BUT_STILL_FAILING, RESOLVED_BY_RELATED_FIX). `report.py` writes readable HTML reports with before/after
  screenshots and PDF pages. Products tab now reads ① Import → ② Diagnose → ③ Repair a Copy & Verify.
* **Proof:** `tests/test_v040.py::Diagnosis`, `test_gui_workflows.ProductsAndJobs`.

## Defects found by the new real-window tests (fixed before release)
| # | Where | Cause | Impact | Correction |
|---|---|---|---|---|
| R4 | `app.py` `App.run_bg` (pre-existing) | Python's garbage collector could run on the worker thread and free Tk variables of closed windows | **Program abort** ("Tcl_AsyncDelete … wrong thread") after closing a dialog and starting a long task | `gc.collect()` on the UI thread before background work and after closing editors; `destroy()` cancels the poll timer |
| R5 | `builders._module_html` (pre-existing) | Module script references `bw-pathway`/`bw-score` elements that were only generated when used | Every assembled Power Tool without a study path was **BLOCKED** at Release QA | Elements always generated (hidden when unused) |
| R6 | `controller.Studio.latest_report` (new code) | Compared 1-second timestamps | "Open Latest Report" could open the older diagnosis | Uses file modification time; repair report wins ties |
| R7 | `app.py` (new code) | New method `_register` shadowed Tk's internal `_register` | Window could not open | Renamed `_register_asset_file` |

## Defects fixed earlier in this engagement (for completeness)
| # | Where | Cause → Correction |
|---|---|---|
| R8 | `browsertest.py` | Inside the PyInstaller .exe, Playwright looked for Chromium only inside the package → `configure_frozen()` points it at the per-user install (found by Windows CI) |
| R9 | `orchestrator.ReleaseQAAgent` | QA trusted files with any recorded history → replays the patch history on the original |
| R10 | `pdftools.inspect_pdf` | Scanned pages with only a page number were treated as text pages → threshold on real text |
| R11 | `academic.extract_source_items` | Only flat `{question, answer}` objects were read → string/comment-aware scanner, nested objects, aliases |
| R12 | `builders` / Release QA | SAMPLE blueprint content could be built and released like approved material → provenance flag, unit needs owner review, Release QA CRITICAL check `asset_fidelity.owner_content` |
| R13 | `app.py` `_poll` | Errors were shown in a dialog only → every error is also written to the Activity & Error Log (tab 6) |
| R14 | `builders._apply_template` | A template registered after a blueprint was created was ignored → default approved template id `byrdway_template` is used automatically |
| R15 | Costs tab | AI on/off state was implicit → explicit "AI processing: ENABLED/DISABLED — reason" line |
