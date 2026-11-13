# Known limitations, unverified items and unresolved defects (v0.5.0, 2026-11-09)

Labels: **IMPLEMENTED+TESTED** · **IMPLEMENTED, NOT VERIFIED ON TARGET** · **PARTIAL** · **NOT IMPLEMENTED**

## Not yet verified (owner action required)
| Item | Status | What is needed |
|---|---|---|
| Real owner Power Tool | **TESTED (Algebra 1 + Honors v2), owner review pending** | 64 screens clean, 100 answers read, 16 machine-verified, 0 wrong; 84 need owner review + attestation. |
| Real owner Explainer (Algebra 1 + Honors, flattened) | **TESTED, owner decisions pending** | 10 image findings (1 math, 9 spelling) await Confirm/Dismiss; then fix in the editable source, re-import, re-verify, attest. |
| Windows runtime | **VERIFIED on Windows Server 2025 (v0.5.0)** — see VERIFICATION_MANIFEST.txt in the release for the exact run | Same Windows core as Windows 11. Still run `install_windows.bat` + the 2-minute smoke test (USER_GUIDE §6) on your own PC once. |
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
| Image-only / flattened pages (Anime Explainers, scans) | **Yes (v0.5.0)**: local page reader (OCR, two passes) reads arithmetic statements, solved equations and spelling; each suspected error has page, location and a picture; known OCR confusions (÷/− read as ':', lost superscripts, ✓ read as V) are retried so correct math is not accused | **Never** (artwork is not edited) | You confirm or dismiss each finding; confirmed ones go on a **correction sheet** + annotated review copy for your editable source. Each image page still needs your visual confirmation (the reader cannot see everything) |
| Blank or duplicate pages, page-number gaps, broken table-of-contents targets or internal links, mixed page sizes, unembedded fonts, password protection | Yes | No (pages are never added, deleted or reordered) | Fix in source and re-import |
| Illustrations, mascot artwork, layout, typography | Compared visually (any change outside a recorded correction BLOCKS release) | **Never modified** | — |
| Editable sources inside a package (DOCX, PPTX, InDesign, Canva exports) | Detected and listed | **No editor implemented** | Edit in the original tool |

### Power Tools (HTML / JS / ZIP)
Automatically corrected on a copy: wrong answer keys (JS/JSON objects incl. nested, `data-answer`, JSON data blocks),
wrong multiple-choice index/letter, misspelled `onclick` handler, `getElementById` id typos, image/script path case or
typo mismatches, broken in-page links, missing `lang`, missing viewport.
Detected only (need a person or approved AI suggestion): JavaScript runtime errors without a matching static cause,
missing alt text, unnamed buttons, duplicate ids, external CDN dependencies, mobile overflow, unsupported question types.

## Findings from the first real owner products (v0.5.0)
* **Flattened "anime" Explainers (v0.5.0):** read by a free, local page reader. On the real Algebra 1 + Honors
  Explainer it verified 18 math statements and found 1 real math error and 9 real spelling errors, with 0 false
  accusations (details delivered to the owner privately, not stored here). **Not covered:** math drawn in graphs or diagrams,
  inequalities, words covered by characters, stylised or very small text, and statements the reader cannot see
  clearly - so each image page still needs your visual confirmation, and a product with image pages reaches PASS
  only after you decide every finding and attest the pages. Spelling suggestions are dictionary guesses; type the
  real correction in the review screen. A misspelling that happens to split into real words (e.g. "intergers" =
  "inter" + "gers") is not flagged, because OCR also drops spaces between real words.
* **Power Tool answer coverage**: 16 of 100 real answer items fall in machine-checkable domains; 84 need owner
  review. Extending the verifier to inequalities, systems, lines/slope and multi-part answers would raise coverage —
  an owner decision (feature work), not done.
* **Browser sweep** clicks up to 80 controls per screen; on the real tool 450 of 1,461 controls were clicked
  (navigation links are covered by visiting their screens). Product-specific scripts (typing answers into the tool's
  own checker) are not implemented.

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
* **PDF arithmetic extraction** checks statements of the form `a op b = c` and `Q:/A:` pairs from the text layer;
  image-only pages are read by the local page reader (OCR, v0.5.0) - see the support matrix for what it cannot see.
* **Editable-source correction** (DOCX/PPTX/Canva) is detected and preferred, but no editor for those formats is
  implemented yet — **NOT IMPLEMENTED**. Text sources (HTML/MD/JSON/JS/CSS) inside ZIPs are fully editable.
* **Browser tests** click every visible control and catch exceptions, broken images and mobile overflow; they do
  not know the intended pedagogy of each interaction (e.g. that a diagnostic routes correctly) — product-specific
  interaction scripts should be added once a real Power Tool is supplied.
* **Math rendering** in built modules is plain text (no MathJax, to stay offline).
* **No hard timeout** on a single SymPy simplification (see SECURITY_REVIEW).
* **Single-user, single-machine**; no concurrent job execution.

* **Windows 11 desktop**: v0.4.3 confirmed on the owner's Windows 11 PC (self-test 14/14). v0.5.0 not yet confirmed there
  (owner: Help → Run self-test, expect 16/16).
* **Code signing**: the .exe is unsigned (a certificate is a purchase — owner decision). SmartScreen warns once.
* **Antivirus** behaviour could not be tested in CI.

## Unresolved defects
None known in the implemented scope at the time of the final test run (see TEST_RESULTS.md).

## Byrd Powerhouse v0.5.x additions (2026-11-13) - honest limits
- **Picture-page Explainer repair is preview-only.** Fixes on flattened pages are proven correct by the Repair
  Reviewer but are not of sale quality; professional fixes go into the editable (Canva) source.
- **Construction content is drafted by the Curriculum Architect (Claude Code)** from the owner-approved TOC and must be
  reviewed by the owner before sale. Machine verification proves answers, units, arithmetic, spelling and layout -
  it does not prove pedagogy or classroom fit.
- **Power Tools pass only with the owner's approved template and Lil Dr. Byrd asset registered.** The engineering
  test used a template copied from the owner's own Algebra 1 v2 stylesheet; the owner must confirm it.
- **Revenue & Media never sends, publishes, prices or pays.** Video rendering happens in the owner's Canva/HeyGen;
  posting and emailing are done by the owner. Market research on the web is done outside the app.
- **Sales results are measured only from imported real sales data.** Until the owner imports a TpT sales report,
  the dashboard shows targets with no actuals - nothing is estimated or invented.
- **Expert methods from books are paraphrased with bibliographic citations** (not page-verified); only the
  Hormozi Diary of a CEO (2026-07-20) quotes are verified verbatim against a saved transcript.
- **99.997 % reliability is a target to be measured** over enough real products; current evidence is reported as
  counts of checks passed, never as an achieved reliability percentage.

## Video platform + Blotato (added 2026-11-13)
- Blotato integration follows Blotato's published REST docs and is tested against a simulated server; it has NOT yet run
  against the owner's live Blotato account (Video Producer / Social Publisher stay PARTIAL until it does).
- Google Flow and Adobe Firefly have no API this app can call: the Studio exports the shot list; the owner renders.
- Blotato AI templates use an AI voice: the Reviewer BLOCKS such a render until it is dubbed with the approved Lil Dr. Byrd recording.
- Hook / retention / emotional impact are capped below 9 until real audience data (3-second hold, average view) is entered.
