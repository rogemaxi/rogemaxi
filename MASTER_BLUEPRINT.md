# ByrdWay Power Tool Master Blueprint
**For any capable LLM agent (Claude, GPT, Gemini) that upgrades or builds ByrdWay Power Tools.**
Owner: Dr. Rogé J. Byrd · Genesis 2 & 7 LLC · ByrdWay Mathematics and Science
Reference implementation: `algebra1-honors/` in this repository. It is verified (V3, Oct 13, 2026), so copy its methods.

---

## 0. How to use this document

* Give the agent the **kickoff prompt** in §12, attach the Power Tool HTML, and give it access to this repository.
* Work on **one Power Tool per session**. Each session must end with the §10 deliverables committed, plus a release decision.
* If the agent can't run a real browser and Python, it **cannot certify**. It may only prepare fixes and must say "UNVERIFIED".

## 1. Non-negotiable rules

1. **Fidelity before creativity.** Never rewrite, redesign, or replace working content. Keep the dark-navy visual identity, dashboard-first layout, curriculum, titles, areas, diagrams, taxonomy, and standalone single-HTML architecture.
2. **Recover before you create.** Inspect the actual file first. Never regenerate a Power Tool from memory.
3. **Never edit the original.** Copy it to `<product>/original/` and build the new version from it with a script.
4. **Every defect follows the same path:** identify → isolate → back up → repair → test → regression-test → verify → document.
5. **Prove, don't claim.** Never write "100%", "fully translated", "complete", or "verified" without a test that shows it. Separate VERIFIED from INFERENCE in every report.
6. **No false language claims.** Content that is not translated must say so in the student's language and be marked `lang="en"`. Never show English inside a translated screen without that notice.
7. **Math is sacred.** Translations may never change a number, symbol, or expression. Answer keys must be machine-checked.
8. **Don't change prices, publish, buy, or spend credits** without explicit owner authorization.
9. **Grades 6–8 are out of scope.**
10. **When reporting, correct your own errors.** Re-read your report against the raw test logs before delivering. (V3 caught three wrong numbers this way.)

## 2. Product queue (11 remaining)

| Day | Power Tool | Notes |
|---|---|---|
| 1 | Algebra 2 + Honors | Closest to the master; reuse the most |
| 2 | Geometry + Honors | Diagrams and proofs: check that SVG labels stay `translate="no"` |
| 3 | Precalculus + Honors | Trig and unit-circle notation must be preserved verbatim |
| 4 | Calculus | Limits and integrals notation; the checker's MATH regex may need ∫, lim, Σ |
| 5 | College Algebra | |
| 6 | College Statistics | Numeric tolerance for rounded answers (≈) |
| 7 | FTCE Mathematics 6–12 | Teacher-certification content: exam-style item formats |
| 8 | FTCE General Knowledge Mathematics | |
| 9 | Biology | Science: answer keys are factual, not computable; see §6.3 |
| 10 | Chemistry | Stoichiometry is computable; chemical formulas must stay `translate="no"` |
| 11 | Catalog standardization pass | Re-run every product's suite; one shared release matrix |

"One per working day" is a target, not permission to skip gates. If a day ends uncertified, the product ships as "not certified", with the reason given.

## 3. The master architecture (what a finished Power Tool contains)

Taken from Algebra 1 + Honors V3. An upgrade must have, or preserve, all of these:

* **Dashboard first.** The landing page has a playful "How Do I Use This? · Show Me Around!" tour (5 steps, optional, never changes scores).
* **Areas.** Each area offers Cheat Sheet, Blueprint, Flashcards, Test Me (Foundation → Proficient → Advanced → Honors), Honors Layer, Interactive Support and AI Tutor resources.
* **Mastery Hub.** It has:
  * an adaptive **diagnostic**: 20 items by default, 40 extended, from a bank of **at least 250 verified items**;
  * a **prescriptive plan** ordered by prerequisites;
  * first-principles lessons;
  * **5 EOC checkouts** of 15 items each (80% threshold, i.e. 12/15), with written performance tasks.
* **Item schema.** `{id, a: areaId, s: stemKey, m: math, o: [correct, d1, d2, d3], w: [steps], skill, difficulty 1–5, distractorTags}`. `o[0]` is always correct, and the display order is shuffled deterministically.
* **Persistence.** `localStorage` with a schema version, plus JSON export/import with validation and reset.
* **i18n.** The `BWM_LANGS` list, the `BWM_I18N[lang][key]` catalog and `t(key)`. Math strings are rendered with `translate="no" dir="ltr"`.
* **Feynman frame** (where applicable): deconstruct → explain → demonstrate → reconstruct → apply → diagnose → verify. These are ByrdWay's operational adaptations, not a verbatim Feynman framework.

## 4. Repository layout per product (copy from `algebra1-honors/`)

```
<product>/
  original/<Name>.original.html      # untouched input; record its SHA-256
  <Name>_V3.html                     # built output (never hand-edited)
  i18n/ui.<lang>.json                # interface strings by key
  i18n/content.<lang>.json           # stems / prose / skills / tags as arrays aligned to English
  tools/build.py                     # exact-match surgical edits + i18n injection
  tools/check_i18n.py                # completeness, placeholders, math fidelity
  tests/verify.js                    # browser suite -> tests/results.json
  tests/english_words.js             # stray-English scan
  tests/dump_items.js + verify_math.py   # answer-key verification
  tests/screenshots/
  RELEASE_REPORT.md
  README.md
```

Copy the tools from `algebra1-honors/`. `check_i18n.py`, `english_words.js` and `textnodes.js` are generic. `build.py`, `verify.js` (its routes) and `verify_math.py` (its item families) are product-specific: rewrite those parts for each product.

## 5. Daily procedure

### Step 1: Recover (≈15 min)
* Copy the input to `original/`, record its SHA-256, and read the whole structure: `grep -n` for `<script`, top-level `const`/`function`, and line lengths.
* Find the data (areas, item bank, checkouts, lessons, i18n catalogs), the routers and the layered overrides. Later layers often reassign earlier functions; map which version is live and which is dead code.
* Read any embedded self-reports (e.g. a `LOCALIZATION_MISSING` count) as **leads, not facts**.

### Step 2: Diagnose by measurement (≈45 min)
Load the file in headless Chromium (Playwright; `executablePath` or `/opt/pw-browsers`). Then, in this order:
1. **Inventory features** (for Gate A): every route, control count, and the English text of each route. Save this as the regression baseline.
2. **Language residue.** For each language, set it via the app's own `setLang`, visit every route, and compare text nodes against an English run of the same routes. Identical nodes mean untranslated text.
   * ⚠️ Use a **TreeWalker over live text nodes**. Don't use `innerText` on a detached clone: it doesn't break lines and hides mixed sentences.
   * ⚠️ Also scan for stray English words inside translated text. Identical-node checks miss mixed-language sentences.
3. **Catalog gaps.** List every item whose `s` stem is raw English instead of a key, plus prose in `w` rendered as math, hardcoded English in templates, `alert`/`confirm` text, `aria-label` text, and tour text.
4. **Adaptive behaviour.** Simulate strong, weak and alternating students by clicking real buttons. Log the difficulty of each item. The diagnostic is adaptive only if the strong and weak paths diverge measurably (V3 standard: strong reaches difficulty ≥4, and its mean is ≥1.5 higher than weak).
5. **Scoring.** Through the UI, 20/20, 0/20 and a known mix must be stored and displayed exactly.
6. **Answer keys.** Dump all served items and check every one (§6).
7. **Mobile, RTL, accessibility.** At 375 px there must be no horizontal scroll; in Arabic, `dir="rtl"`; every control needs an accessible name; `<html lang>` must match.

Write the **defect inventory** (ID, severity, evidence) before changing anything.

### Step 3: Repair surgically (≈2–3 h)
* All edits go in `tools/build.py` as `rep(old, new, count=1, tag="D#")`. The build **aborts** if a target doesn't match exactly. Never use regex rewrites of whole functions.
* Prefer the smallest change. Typical patterns:
  * Hardcoded English in the global shell → `${esc(L('key','English'))}`. `L()` falls back to the original English, so English output stays byte-identical.
  * Hardcoded English in the mastery closure → `t('key')`.
  * Raw-English stems → don't rewrite the data. Add catalog entries keyed by the English sentence, merged into `BWM_I18N`.
  * Prose in solution steps → a `stepHTML()` that translates words and keeps math neutral.
  * Untranslated long content → a translated "English only for now" notice plus `lang="en" dir="ltr"`.
  * Inject new code **inside** the existing closure, before its event listeners. Wrap functions; don't replace them.
* Put translations in `i18n/` files. Run `check_i18n.py` until it's clean, then build.

### Step 4: Verify (≈1 h)
Run the suite. Every check must pass, or be explained as a release blocker:
* **G1:** English regression identical apart from the listed intended changes.
* **B1/B2/B3:** language coverage, honest labelling, tour coverage.
* **A1–A3:** adaptive behaviour.
* **S1/S2:** scoring and option uniqueness.
* **P1:** persistence across language switch and reload.
* **M1:** mobile layout. **X1:** accessible names. **R1:** no JavaScript errors.
* `verify_math.py`: N/N items, 0 failures. `english_words.js`: 0.

Take screenshots: the dashboard in Arabic, the diagnostic on a phone in a CJK language, the plan, and an English-only page showing its notice. **Look at them.**

### Step 5: Deliver (≈30 min)
Write `RELEASE_REPORT.md` with the 10 sections in §10. Check every number against the logs. Commit, push, and send the HTML and report to the owner.

## 6. Mathematical and factual verification

### 6.1 Computable items (math, physics, chemistry)
* **Templated families** (same stem, varying numbers): parse the equation and solve it with sympy. Compare with `o[0]`, and require that **no distractor** also matches.
* **Word problems and EOC items:** recompute each one from the problem statement in Python, independent of the options. One line each.
* **Rounded keys (≈):** use a tolerance of half a unit in the displayed last digit.
* **Structural items** (factor, simplify, identity): compare `expand(option) == expand(target)`.

### 6.2 Translation fidelity
`check_i18n.py` requires every number and math token in each English stem and explanation to appear verbatim in the translation. Common slips are numerals written as words ("five units") and a reformatted expression.

### 6.3 Non-computable items (biology, conceptual chemistry, FTCE pedagogy)
* For each item, record a **justification with a source class**: textbook-standard fact, an official standard such as NGSS, or the FTCE competency list. Flag any item where you're less than certain as `NEEDS-HUMAN-REVIEW`. Never mark it verified.
* Check that exactly one option is defensible. Ambiguous items are defects.
* Never copy protected material from other publishers.

## 7. Translation standard (12 languages now, built for 100+)

* **Current languages:** en, es, zh (Simplified), hi, ar (RTL), fr, pt, ru, ht, vi, ko, ja.
* **Reuse each language's existing terms** from its `BWM_I18N` catalog (e.g. "Blueprint" stays as a brand term in all languages; pt keeps "Flashcards"). Read them first.
* **Catalog categories:** UI keys; question stems; solution prose; skill labels; misconception labels; tour; dialogs; `aria-label`s; notices.
* **Adding a language** is data only: add two JSON files and a `BWM_LANGS` entry, then run `check_i18n.py`. For RTL, set the `'rtl'` flag.
* **Order of work:**
  1. The student journey: dashboard → tour → diagnostic → results → plan → EOC. This is the sellable minimum.
  2. Long-form curriculum: cheat sheets, blueprints, flashcards, Test Me, honors, lessons, performance tasks.
  3. Native-speaker educator review.
* **Disclose plainly** that LLM-authored translations need native-speaker review before being marketed as fully supported.

## 8. Adaptive diagnostic standard

* Cover areas first: always pick the least-sampled area, so 20 items means 2 per area for 10 areas.
* Choose difficulty with a **global staircase**: start at 2, move ±0.5 per answer, clamp to 1–5. Blend it with the area's last response (±1). Pick the nearest available difficulty, breaking ties by item id.
* Lock answered items once the engine moves on, and show why.
* Report results as descriptive with intervals, never as a calibrated ability score. Five or more distinct responses in an area with ≥80% correct counts only as *provisional* proficiency.
* If the bank lacks items at some difficulties in an area, record it as a **content gap** in the report. Don't fake adaptivity.

## 9. Release gates

| Gate | Pass condition |
|---|---|
| **A: Zero feature regression** | Every route has the same controls and the same English text as the original, except the documented intended changes. No JavaScript errors. |
| **B: Complete language coverage** | Every surface (dashboard, tour, lessons, worked examples, questions, explanations, diagnostic, remediation, cheat sheets, blueprints, flashcards, all 5 levels, feedback, tutor instructions) renders in every language. Tested on **rendered text**, not catalog completeness. |
| **C: Evidence-based certification** | Math N/N, adaptive and scoring checks, language tests, accessibility, desktop and mobile, persistence, regression, all recorded in `tests/results.json`, with no known blockers. |

**Release decisions:**
* **PASS:** all three gates pass.
* **CONDITIONAL PASS:** A and C pass; B is partial but honestly labelled, and the product is marketed truthfully. This is where Algebra 1 V3 stands.
* **FAIL:** anything else.

## 10. Required deliverables per product (`RELEASE_REPORT.md`)

1. Recovered source (file names, sizes, SHA-256).
2. Verified defect inventory (ID, severity, evidence).
3. Corrected standalone HTML.
4. Exact change log (each `build.py` tag mapped to a defect).
5. Mathematical/factual verification evidence (N/N).
6. Language coverage matrix (surface × language).
7. Functional and regression results (suite summary).
8. Real-browser verification (engine, viewports, screenshots, and what was **not** tested).
9. Release-gate matrix and the release decision.
10. The downloadable artifact, committed and sent to the owner.

## 11. Building a NEW Power Tool (after the existing catalog is certified)

Do this only after the catalog is certified and the owner has prioritized commercially. Use the same architecture, with new content authored to the item schema:
1. **Scope.** List the areas (8–12), aligned to the course's real standards. Benchmark rigor against strong university programs (MIT, Stanford, ETH, Oxford, Cambridge, Harvard, Caltech) using current, public, subject-level evidence. Never copy their materials, and don't treat prestige as proof that instruction works.
2. **For each area,** author the cheat sheet, blueprint (SEE → IDENTIFY → CHOOSE → EXECUTE → CHECK), flashcards (8 types), Test Me in 4 tiers, honors layer, lesson, and prerequisites.
3. **Item bank.** At least 25 items per area (≥250 total), spread across difficulties 1–5, with **at least 3 items per difficulty in every area**. That avoids the content gap Algebra 1 has in Systems. Each wrong option gets a misconception tag.
4. **5 EOC checkouts** of 15 items each, rising in cognitive demand, each with a written performance task and rubric.
5. **Start from a copy of the Algebra 1 V3 HTML.** Replace the data; keep the engine. Then run §5 Steps 2–5 on the new product exactly as for an upgrade.

## 12. Kickoff prompt (copy and paste to the agent)

> You are upgrading the ByrdWay **[PRODUCT NAME]** Power Tool. Follow `MASTER_BLUEPRINT.md` in this repository exactly. Use `algebra1-honors/` as the verified reference implementation and copy its tools.
> The attached HTML is the source of truth: inspect it before changing anything, and never edit it. Put it in `[product]/original/` and build the new version with `tools/build.py` using exact-match edits only.
> Diagnose by measuring in a real headless browser. Repair surgically. Translate the student journey into all 12 languages with the math-fidelity checker. Machine-verify every answer key. Run the full suite, and look at the screenshots.
> Deliver the 10 items in §10 and a release decision (PASS / CONDITIONAL PASS / FAIL). Separate verified facts from inference. Never claim completion without evidence. Check every number in the report against the test logs. Then commit, push, and send me the HTML and report.

## 13. Pitfalls already found (don't repeat them)

* Embedded "coverage" counts in the file were stale. Measure instead.
* Item stems were sometimes raw English sentences rather than keys, so `t()` silently returned English.
* Solution prose sat inside `translate="no"` math spans, so it was invisible to translators.
* Layered overrides left dead code: only the last `renderPlan`/`renderLesson` assignment is live.
* `innerText` on detached nodes gives misleading line splits.
* `x` declared `real=True` in sympy makes `solve` return `[]` for complex-only roots. That's correct behaviour, not a bug.
* Float and integer intervals compare unequal in sympy, so use ints.
* CJK nav labels wrap mid-word. Fix with `white-space:nowrap`.
* Cognates (es/fr "plan", fr "questions"/"correct") trigger false English alarms. Allowlist them per language, with a comment.
* The agent's own report numbers can drift from the logs. Re-check before delivery.
