# Known limitations, unverified items and unresolved defects (v0.4.1, 2026-11-09)

Labels: **IMPLEMENTED+TESTED** · **IMPLEMENTED, NOT VERIFIED ON TARGET** · **PARTIAL** · **NOT IMPLEMENTED**

## Not yet verified (owner action required)
| Item | Status | What is needed |
|---|---|---|
| Real owner Power Tool | **BLOCKED — owner file needed** | Supply one original ByrdWay Power Tool ZIP/HTML with known defects. All results so far come from controlled fixtures. |
| Real owner Explainer / Concept Tiles + editable source | **BLOCKED — owner file needed** | Supply one real Explainer PDF and its editable source (Canva/PPTX/DOCX export). |
| Windows runtime | **VERIFIED on Windows Server 2025 (v0.4.1, run 42663089124)** (CI run https://github.com/rogemaxi/rogemaxi/actions/runs/42544542267) | Same Windows core as Windows 11. Still run `install_windows.bat` + the 2-minute smoke test (USER_GUIDE §6) on your own PC once. |
| Windows .exe | **VERIFIED on Windows Server 2025** | Built by CI; full self-test passes inside the .exe; GUI launches. Not code-signed (Windows SmartScreen will warn: More info → Run anyway). |
| Chromium OS sandbox on Windows | IMPLEMENTED; tests pass on Windows | The CI log does not record which sandbox mode was used (the runner is an administrator account). |
| Live OpenAI calls | IMPLEMENTED, NOT VERIFIED ON TARGET | All AI paths tested with a mock client; no real API call was made (no key, no spend authorized). Uses the official `openai` SDK Responses API. |
| API balance | NOT VERIFIED | The app cannot read your OpenAI balance; the ledger records only this app's own estimated/recorded usage. The previously reported ~$19.10 was not checked. |
| Approved ByrdWay template, Lil Dr. Byrd mascot, approved reference products | BLOCKED – missing assets | Register them in the Builders tab. Until then built products are BLOCKED at Release QA by design. |
| Physics + Honors Lil Dr. Byrd content | BLOCKED – missing approved content | Builder and verifier are ready; chapter content must come from the owner's approved blueprint. Physics Concept Tiles intentionally not built. |

## What the Studio can repair — exact support matrix
### Explainer / Concept Tiles / Lil Dr. Byrd PDFs
| Defect | Detected | Automatically corrected | Otherwise |
|---|---|---|---|
| Wrong arithmetic statement `a op b = c` (+ − × ÷ ·, fractions, powers) on a page **with a text layer**, statement occurring once on the page | Yes (two independent methods) | **Yes** — region text replacement on a copy; marked RECONSTRUCTED_REGION; replacement font is Helvetica (may differ from your font); change verified to stay inside the region; all other pages verified pixel-identical; **owner must confirm visual review** | — |
| Wrong answer in an answer key (`Q…` / `A: …` lines) | Yes | **No** | Correct it in your editable source (Canva/PPTX/DOCX), export a new PDF, re-import and re-verify |
| Math written in prose, equations drawn as images or vector art | No (not read) | No | Owner review + attestation |
| Image-only / flattened pages (scans, flattened exports) | Text not read (no OCR) | **Never rewritten** | Owner review + attestation, or supply editable source |
| Blank or duplicate pages, page-number gaps, broken table-of-contents targets or internal links, mixed page sizes, unembedded fonts, password protection | Yes | No (pages are never added, deleted or reordered) | Fix in source and re-import |
| Illustrations, mascot artwork, layout, typography | Compared visually (any change outside a recorded correction BLOCKS release) | **Never modified** | — |
| Editable sources inside a package (DOCX, PPTX, InDesign, Canva exports) | Detected and listed | **No editor implemented** | Edit in the original tool |

### Power Tools (HTML / JS / ZIP)
Automatically corrected on a copy: wrong answer keys (JS/JSON objects incl. nested, `data-answer`, JSON data blocks),
wrong multiple-choice index/letter, misspelled `onclick` handler, `getElementById` id typos, image/script path case or
typo mismatches, broken in-page links, missing `lang`, missing viewport.
Detected only (need a person or approved AI suggestion): JavaScript runtime errors without a matching static cause,
missing alt text, unnamed buttons, duplicate ids, external CDN dependencies, mobile overflow, unsupported question types.

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

* **Windows 11 desktop** itself was not available for testing (GitHub has no Windows 11 runners).
* **Code signing**: the .exe is unsigned (a certificate is a purchase — owner decision). SmartScreen warns once.
* **Antivirus** behaviour could not be tested in CI.

## Unresolved defects
None known in the implemented scope at the time of the final test run (see TEST_RESULTS.md).
