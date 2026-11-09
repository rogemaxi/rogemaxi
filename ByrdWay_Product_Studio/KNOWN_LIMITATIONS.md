# Known limitations, unverified items and unresolved defects (v0.2, 2026-11-09)

Labels: **IMPLEMENTED+TESTED** · **IMPLEMENTED, NOT VERIFIED ON TARGET** · **PARTIAL** · **NOT IMPLEMENTED**

## Not yet verified (owner action required)
| Item | Status | What is needed |
|---|---|---|
| Real owner Power Tool | NOT VERIFIED | Supply one original ByrdWay Power Tool ZIP/HTML with known defects. All results so far come from controlled fixtures. |
| Real owner Explainer / Concept Tiles + editable source | NOT VERIFIED | Supply one real Explainer PDF and its editable source (Canva/PPTX/DOCX export). |
| Windows runtime | **VERIFIED on Windows Server 2025** (CI run https://github.com/rogemaxi/rogemaxi/actions/runs/42544542267) | Same Windows core as Windows 11. Still run `install_windows.bat` + the 2-minute smoke test (USER_GUIDE §6) on your own PC once. |
| Windows .exe | **VERIFIED on Windows Server 2025** | Built by CI; full self-test passes inside the .exe; GUI launches. Not code-signed (Windows SmartScreen will warn: More info → Run anyway). |
| Chromium OS sandbox on Windows | IMPLEMENTED; tests pass on Windows | The CI log does not record which sandbox mode was used (the runner is an administrator account). |
| Live OpenAI calls | IMPLEMENTED, NOT VERIFIED ON TARGET | All AI paths tested with a mock client; no real API call was made (no key, no spend authorized). Uses the official `openai` SDK Responses API. |
| API balance | NOT VERIFIED | The app cannot read your OpenAI balance; the ledger records only this app's own estimated/recorded usage. The previously reported ~$19.10 was not checked. |
| Approved ByrdWay template, Lil Dr. Byrd mascot, approved reference products | BLOCKED – missing assets | Register them in the Builders tab. Until then built products are BLOCKED at Release QA by design. |
| Physics + Honors Lil Dr. Byrd content | BLOCKED – missing approved content | Builder and verifier are ready; chapter content must come from the owner's approved blueprint. Physics Concept Tiles intentionally not built. |

## Functional limitations
* **Academic verifier scope (PARTIAL by nature):** deterministic coverage = arithmetic/fractions/radicals/trig values,
  linear & polynomial equations (real roots), derivatives, indefinite/definite integrals, limits, simplification,
  mean/median/mode/range/variance/standard deviation, common geometry formulas, physics formula problems with SI
  units (when the item carries a `verify` spec). Word problems, proofs, graphs, chemistry/biology content and
  free-response explanations are flagged **UNSUPPORTED** → owner attestation or AI-assisted review.
* **Answer extraction from Power Tools** recognises JS/JSON objects at any nesting depth (comments and strings
  handled) with `q/question/prompt/problem/questionText/stem` + `answer/correctAnswer/solution/...` or
  `choices/options/answers` + `correct/correctIndex/answerIndex/...` (index, letter or value), `data-question`/`data-answer` attributes and JSON
  data blocks. Other storage formats need an adapter once a real Power Tool is supplied.
* **Automatic JS repair** is deterministic only for: misspelled handler/function names, `getElementById` id typos,
  asset path case/typo mismatches, broken in-page anchors, wrong answer keys, wrong multiple-choice indices,
  `lang` and viewport. Other runtime errors are escalated (or sent to AI if enabled and approved).
* **Flattened PDFs** cannot be edited losslessly. Region text replacement works only on text-layer pages, uses
  Helvetica (font may differ), is marked RECONSTRUCTED_REGION and requires your visual approval.
  Image-only pages are never rewritten.
* **PDF arithmetic extraction** checks statements of the form `a op b = c` and `Q:/A:` pairs from the text layer.
  Equations embedded as images or complex layouts are not read (no OCR).
* **Editable-source correction** (DOCX/PPTX/Canva) is detected and preferred, but no editor for those formats is
  implemented yet — **NOT IMPLEMENTED**. Text sources (HTML/MD/JSON/JS/CSS) inside ZIPs are fully editable.
* **Browser tests** click every visible control and catch exceptions, broken images and mobile overflow; they do
  not know the intended pedagogy of each interaction (e.g. that a diagnostic routes correctly) — product-specific
  interaction scripts should be added once a real Power Tool is supplied.
* **Math rendering** in built modules is plain text (no MathJax, to stay offline).
* **No hard timeout** on a single SymPy simplification (see SECURITY_REVIEW).
* **Single-user, single-machine**; no concurrent job execution.

## Unresolved defects
None known in the implemented scope at the time of the final test run (see TEST_RESULTS.md).
