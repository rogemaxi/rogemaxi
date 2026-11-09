# CLAUDE CODE EXECUTION CONTRACT — BYRDWAY PRODUCT ENGINEERING STUDIO

## Mission
CONTINUE AND FINISH the existing ByrdWay Product Engineering Studio prototype in this folder. DO NOT replace, discard, or silently redesign the existing code, approved product assets, or workflows. Owner: Genesis 2 & 7, LLC / ByrdWay Mathematics & Science. This is a Windows 11 local-first desktop app, using the OpenAI API for runtime intelligence. Claude Code is only the development assistant; no Anthropic API or Claude subscription may be required to run the delivered application.

## Read before modifying
Inspect README.md, app.py, engine.py, ai_roles.py, tests/test_engine.py. Run the existing tests and record baseline results. Inspect all code for defects and missing requirements. Maintain backward compatibility for original import, hashing, ZIP protections, and audit/report workflows. Never overwrite originals.

## Seven coordinated roles (logical roles, not seven persistent paid processes)
1. Orchestrator: job state machine, dependency ordering, retry/cost/time caps, evidence log, approval gates.
2. Power Tool Repair: HTML/CSS/JS/ZIP math, science, accessibility, navigation, scoring, diagnostic and interactive fixes.
3. Explainer Repair: Anime Explainers and Concept Tiles PDFs plus editable sources, academic accuracy, figures, answer keys, layout and visual comparison.
4. Power Tool Builder: new blueprint-driven interactive products, one module at a time with owner approval.
5. Lil Dr. Byrd Builder: approved mascot only, chapter-by-chapter high-quality explainers, never synthesize or replace mascot without supplied approved asset and authorization.
6. Academic Verifier: independent deterministic symbolic/numeric checks where feasible plus model-assisted review; evidence-backed answers, no self-grading.
7. Release QA: functional regression, source and visual diffs, safety and academic checks, signed-off export candidate.

## Non-negotiable safety and quality
- Originals immutable, SHA-256 recorded, backups and versioned working copies; atomic output writes.
- Never auto-publish, modify TpT listings, send messages, spend money beyond explicitly confirmed API calls, or alter locked creative.
- 99.9/100 is an ACCEPTANCE TARGET, not a claim. Define a documented weighted quality score based on executed tests and evidence. ZERO known critical academic, functional, security, or asset-fidelity defects to release. A pass percentage alone cannot override critical defects.
- Repair loop: inspect -> minimal patch -> deterministic tests -> independent academic checks -> regression/visual checks -> repeat. Limit retries, runtime and token/cost budget; detect no-progress and stop with actionable BLOCKED status. Never loop forever.
- OpenAI API: owner-supplied OPENAI_API_KEY through environment/OS secret store, never in code or logs; configurable models, pre-call estimated budget checks, recorded actual usage/cost when available, daily/per-job cap, manual approval for API spending. Support offline local audits with no API key. Do not claim an API balance was verified.
- Do not claim a PDF can be edited losslessly when only a flattened PDF exists. Detect editable source availability and require approval for reconstruction.
- Do not invent approved product templates, curriculum, graphics, Lil Dr. Byrd imagery, or source files. Ask for missing assets, and implement placeholder-safe scaffolding rather than fabricated finished content.

## Delivery milestones — complete in order, test each
A. Baseline and repair: run tests, fix actual defects, add structured job logs and robust error handling.
B. Source-aware ZIP project unpack/edit/repack into proposals, safe file path rules, diff previews and rollback.
C. Headless browser tests for Power Tool HTML/JS interactions (Playwright or equivalent), test reports and screenshots. If browser installation requires downloads, explain and request approval.
D. Independent academic validation suite for representative algebra/geometry/calculus/statistics/science cases; compare generated answers to deterministic solutions where possible; clear unsupported-domain flags.
E. PDF/Explainer inspection, page rendering and before/after comparison; editable-source corrections when available; never silently rewrite flattened pages.
F. Blueprint-driven Power Tool and Lil Dr. Byrd chapter builders with explicit per-module approval and content provenance.
G. Full QA scoring with hard blockers, repair loops, reproducible test evidence, export review and owner approval UI.
H. Windows install/package, requirements lock, setup guide, security review and clean-machine smoke-test instructions. Package exe only if successfully tested in Windows environment; otherwise clearly report unverified.

## Acceptance tests
- Existing four tests remain passing, plus new tests for every implemented feature.
- Malicious ZIP/path traversal and archive bombs rejected.
- Original files remain byte-identical after import, repair and export.
- Known broken HTML/JS sample fails before and passes after repair, with browser test evidence.
- Known wrong answer key fails academic check and corrected version passes.
- Repeat/rollback/stop-on-budget and stop-on-no-progress cases covered.
- Human approval required before any candidate is labeled ready for release.
- Test one real owner-provided Power Tool and one real owner-provided Explainer source before claiming production readiness.

## Execution discipline
Do not stop at planning or create empty agent wrappers. Implement code, run tests, fix failures, record actual commands and outcomes, and deliver usable artifacts. At each milestone report COMPLETED, TESTED, BLOCKED, COST, NEXT. Do not claim access to user files or Windows runtime unless actually available. Prefer free local libraries and minimal dependencies. Never ask Claude Code to autonomously use or reveal credentials. If requirements conflict, preserve current approved originals and request owner approval.

## Immediate command
Start by reading the existing files and running `python -m unittest discover -s tests -v`. Then implement milestone A, verify, and continue milestone-by-milestone without discarding previous work. Ask for the first original Power Tool ZIP/HTML and editable Explainer sources when integration tests need them.
