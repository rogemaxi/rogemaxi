# ByrdWay Quality Scoring — specification (v0.4.2)

Implemented in `quality.py`; tested in `tests/test_repair_loop.py::Scoring`. The score is computed **only** by
the Release QA role from a **fresh re-extraction of the candidate package**, never from the repair agent's own
report.

## 1. Checks
Every test produces a check `(id, category, severity, passed, evidence)`; `passed` is `True`, `False`, or
`None` (could not be executed — e.g. no browser installed, image-only PDF).

| Severity | Weight | Examples |
|---|---|---|
| CRITICAL | 10 | wrong answer, JS exception, missing asset, original hash mismatch, unrecorded change, visual change outside a recorded fix, provisional template / missing mascot in a built product |
| MAJOR | 3 | broken in-page link, duplicate id, image without alt, button without accessible name, duplicate/blank PDF page, page numbering gap, broken TOC |
| MINOR | 1 | missing `lang`, missing viewport, empty title, mobile horizontal overflow, non-embedded non-standard fonts |
| INFO | 0 | external dependencies, visual change percentage, owner attestations (recorded, not scored) |

## 2. Score
`score = 100 × Σ weight(passed) ÷ Σ weight(executed)`, rounded to 2 decimals. Checks that did not run are
listed as `not_executed` and never count as passes.

## 3. Decision (evaluated in this order)
1. Any failed **CRITICAL** → **BLOCKED**
2. Any failed **MAJOR** → **BLOCKED**
3. Required categories not executed, or academic items neither verified nor owner-attested → **NOT_VERIFIED** (no score is reported)
4. `score < 99.9` → **BELOW_TARGET**
5. Otherwise → **PASS** (eligible for owner approval; never auto-released)

Because of rule 1, a weighted average **cannot hide a critical failure**: 5,000 passing checks plus one failed
critical check is still BLOCKED (unit-tested). Because weights are integers, 99.9 effectively requires **every
executed scored check to pass** unless the product has ≥ 1,000 weight points of checks.

## 4. Required coverage by product type
| Product type | Required categories |
|---|---|
| POWER_TOOL | integrity, html_structure, functionality, assets, browser_runtime, academic |
| EXPLAINER_PDF / CONCEPT_TILES / ANIME_EXPLAINER / LIL_DR_BYRD_EXPLAINER | integrity, pdf_structure, academic, visual |
| EXPLAINER_SOURCE_PACKAGE | integrity, pdf_structure, academic |
| BUILT_POWER_TOOL | integrity, html_structure, functionality, browser_runtime, academic, asset_fidelity |
| BUILT_EXPLAINER | integrity, pdf_structure, academic, asset_fidelity |

## 5. Integrity checks (always run)
* original SHA-256 re-computed and equal to import fingerprint
* candidate SHA-256 equal to the value recorded at repack
* candidate ZIP passes the same safety rules as uploads
* every binary asset (images, fonts, PDFs not deliberately corrected) byte-identical to the original
* no files added or removed
* **replay**: re-applying the recorded patch history to the original reproduces the candidate exactly — any
  silent edit is a CRITICAL failure

## 6. Academic verification
`academic.py` uses two methods per item where feasible (see module docstring). Status `UNSUPPORTED` or
`PARSE_ERROR` is never treated as correct; it keeps the result at NOT_VERIFIED until the owner attests, by
name, that they personally reviewed the item. An attestation never overrides a failed check.

## 7. Reproducibility
The decision is a pure function of the check list (`quality.score`). All checks and evidence are stored in
`jobs/<job>/qa/qa_result.json`, screenshots and page renders in `jobs/<job>/evidence` and `qa/`.
"Re-run Release QA" recomputes everything from the candidate file.
