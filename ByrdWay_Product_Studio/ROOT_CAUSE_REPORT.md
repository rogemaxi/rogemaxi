# Root Cause Report — ByrdWay Product Engineering Studio v0.4.2

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

## Final acceptance review (v0.4.2)
| # | Where | Cause | Impact | Correction | Proof |
|---|---|---|---|---|---|
| R16 | `.github/workflows/byrdway-windows.yml`, release step | `git archive HEAD:ByrdWay_Product_Studio` ran *inside* the app folder, so Git resolved the path relative to that folder and archived nothing | The v0.4.0 draft release's source ZIP was **176 bytes (empty)**; commit 0d20eaa therefore FAILED as a release although its tests passed | archive built from the repository root; workflow refuses a source ZIP with < 50 entries or without `version.py`; release assets are downloaded back and SHA-256-compared; superseded drafts removed | VERIFICATION_MANIFEST.txt in the v0.4.2 draft release |
| R17 | `costs.estimate_cost` / `BudgetGuard.authorize` | Caps were checked against an *estimate* (≈3.5 characters per token × 1.5). Symbol-heavy or non-English text uses more tokens, so a recorded charge could exceed a cap after the call. The daily-cap test used a mock reply larger than the requested output limit and did not detect this | A cap could be crossed by one call | Caps are now checked against a **guaranteed maximum**: input tokens ≤ UTF-8 bytes, output ≤ `max_output_tokens`. If OpenAI ever reports more, the entry is flagged `exceeded_authorized` and AI is stopped for that job | `test_recorded_charge_never_exceeds_authorized_maximum`, `test_daily_cap_accumulates_and_is_never_exceeded`, `test_usage_above_maximum_halts_ai_for_the_job` |
| R18 | `costs.BudgetGuard.paid_call`, tests | Denial paths were correct (refusal before any request) but tests only proved "no request", not "no ledger charge"; failed calls were recorded as `FAILED` with `charged_usd`, which read like a confirmed charge | Spending evidence was ambiguous | Every denial path tested for **no request and no ledger entry**; failed calls now `FAILED_ASSUMED_MAX`, `confirmed_charge: false` (the maximum stays reserved against caps) | `test_every_denial_makes_no_call_and_records_nothing` (8 denial paths), loop tests assert empty ledger |
| R19 | `orchestrator.run_repair_job`, `app.App.run_job` | The owner's "Repair a copy" confirmation and the preceding diagnosis were not recorded in the job | Audit trail could not show findings were documented and repair was authorized before changes | Job records `prior_diagnosis` and `repair_authorization`; report and exported audit trail show both, plus the release approval | `tests/test_e2e_explainer.py` |
| R20 | `app.App.approve` | Answering "No" to "Have you reviewed the page images?" still led to the final confirmation, then failed | Confusing approval flow | Stops immediately and tells the owner what to review | same test |

## First real-product acceptance run (v0.4.2) — owner Power Tool (HTML) + owner Explainer (PDF)
Owner content is not stored in this repository; only Studio defects are recorded here.
| # | Where | Cause | Impact on the real products | Correction | Proof |
|---|---|---|---|---|---|
| R21 | `academic.extract_source_items` | Answer keys stored as `{q, a}` were not recognised (`a` was not an answer key name) | **0 of 100** answers were read; the tool would have looked "clean" with no verification | `a` accepted when paired with a question key | real run: 100 of 100 read; `test_q_a_keys_in_nested_json_data` |
| R22 | `browsertest.run_browser_tests` | Clickable controls were counted once on the first screen; single-page tools that switch screens via `#/…` were never explored | Only the cover screen (1 control) of a 64-screen tool was tested | bounded crawl of every discovered `#` screen; new check `browser.all_screens_visited` | real run: 64/64 screens, 450 clicks; `test_bug_on_an_inner_screen_is_found` |
| R23 | `academic.classify` | Method phrases ("by factoring", "using the quadratic formula") were parsed as mathematics | Supported equations reported as PARSE_ERROR | method phrases stripped | `test_method_phrases_are_not_mathematics` |
| R24 | `academic.parse_answer_set` | `±` answers and "(or …)" alternatives not understood | Correct answers unverifiable | `±` expands to both roots; "(or …)" ignored | same tests |
| R25 | `academic.verify_item` | Prose questions mis-classified as equations produced PARSE_ERROR | Misleading label | wording that is not pure mathematics → UNSUPPORTED (hostile input still PARSE_ERROR) | `test_prose_questions_are_unsupported_not_parse_errors` |
| R26 | `academic.extract_source_items` | A "non-math text" filter dropped a real proof question (no digits) | A question would silently miss the owner review list | filter applies only to generic field names | `test_proof_items_are_never_dropped` |
| R27 | `pdftools.inspect_pdf` | Page sizes compared exactly | False "mixed page sizes" warning for a < 1-point difference | 2-point tolerance | `test_sub_point_size_differences_are_not_flagged` |
| R28 | `report.write_job_report` | Items needing owner review were shown only in the Jobs tab | The readable report did not say *which* questions to review | report lists every item with its attestation key | real run report |
