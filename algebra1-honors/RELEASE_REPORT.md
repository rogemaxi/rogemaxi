# ByrdWay Algebra 1 + Honors Power Tool — V3 Release Report

**Date:** October 13, 2026 · **Owner:** Dr. Rogé J. Byrd · Genesis 2 & 7 LLC · ByrdWay Mathematics and Science
**Operating rule:** fidelity before creativity. Surgical corrections only.

**Release decision: CONDITIONAL PASS.** The dashboard, navigation, onboarding tour, adaptive diagnostic, results, study plan and EOC checkouts are verified in all 12 languages. The long-form curriculum is still English-only and is now honestly labelled as such. Full Gate B (complete language coverage) is **not** met; see section 9.

---

## 1. Recovered source

| | File | SHA-256 |
|---|---|---|
| Input (untouched, kept in `original/`) | `ByrdWay_Algebra_Honors_Upgrade_V2.original.html` (1,011,399 bytes) | `8532144939e751586bb614088dfdc59e4cd57c89e045994b87bef778584bd59b` |
| Output | `ByrdWay_Algebra_Honors_Upgrade_V3.html` (1,799,022 bytes; growth is translation data) | `22db7ba79ded7229a983820b59edf805b566085418ab4ead5d1c6ddaeb04feb2` |

The build regenerates V3 from the untouched original every time (`python3 tools/build.py`). The original is never edited.
`PROJECT_INSTRUCTIONS.txt`, the operating manual and the reference manifest were **not** supplied in this session and were not available to recover. This audit used the HTML itself as the source of truth.

## 2. Verified defect inventory

Each defect was confirmed by measurement in headless Chromium before any repair.

| ID | Severity | Defect (as found) | Evidence |
|---|---|---|---|
| D1 | Release-blocking | **The diagnostic showed English in all 11 non-English languages.** 100 of the 250 bank questions stored raw English sentences where translation keys belonged, and their solution explanations were English prose locked as `translate="no"` math. | 100 untranslated stems × 11 languages; the file's own `BWM_LOCALIZATION_MISSING` recorded 3,321 missing entries per language |
| D2 | Release-blocking | **The dashboard and navigation were hardcoded English**: nav bar, "What are you working on?" tiles, "What do you need right now?" grid, Learning Engines, Five EOC block, the `<h1>Dashboard</h1>`, the How This Works page, area tab bar and onboarding tour. | Spanish dashboard: 25 of 40 lines identical to English |
| D3 | Release-blocking | **Mixed-language interfaces**: plan sentences, backup/reset/import dialogs, storage errors and the EOC written-task block were hardcoded English. The "this is English-only" lesson disclaimer was itself written in English. | Rendered-text diff per route |
| D4 | High | **Pre-existing key leak in the plan (English too):** EOC items showed raw keys such as "EOC reasoning: s_factor". | Plan page screenshot |
| D5 | High | **Weak adaptive ceiling.** In the default 20-item diagnostic, a student answering everything correctly never saw anything above difficulty 3, so all 43 difficulty-4/5 honors items were unreachable. | Simulated strong student: max difficulty 3 |
| D6 | Medium | **Revisited diagnostic items looked answerable** but silently ignored clicks (answers lock after the adaptive engine moves on). | UI test |
| D7 | Medium | **Inconsistent language selection.** The picker existed only on hub/learn/EOC pages, not on area pages. `<html lang>` stayed `en` and `dir` was never set (Arabic). English-only sections weren't marked `lang="en"`. | DOM inspection |
| D8 | Low | Nav links wrapped mid-word in Chinese/Japanese/Korean on phones. | 390 px screenshot |
| D9 | Honesty | The coverage notice cited a stale "3,321 missing entries" count and did not say which sections are translated. | Source |

**Checked and confirmed sound (no change needed):** scoring engine (`answers[id] === 0` with deterministic option shuffle); all 325 served answer keys (section 5); persistence and backup validation; option uniqueness; 250-item bank; 10-area coverage.

## 3. Repairs: exact change log

All repairs are 72 exact-match edits in `tools/build.py`. Each must match exactly once or the build aborts. No content, curriculum, taxonomy, diagram, style or feature was removed.

| Fix | What changed |
|---|---|
| D1 | Added the translation catalog `BWM_REPAIR_I18N` (100 stems, 105 explanations, 129 skill labels, 304 misconception labels and 124 UI strings, × 11 languages), merged into the existing `BWM_I18N`. Results review now renders word explanations translated through a new `stepHTML()`. Pure math stays language-neutral, and "Answer: X" becomes the localized label + math. |
| D2 | `navBar`, `renderHome`, `renderHow` and the area tab bar call `L(key, english)`, which returns the selected language or the original English byte-for-byte. Dashboard h1, Learning Engines (area names now localized), EOC block, help button, invitation and all 5 tour steps use `t()`. |
| D3 | Plan, controls, dialogs, storage errors, lesson disclaimer and EOC written-task block use `t()` keys. |
| D4 | New `skillName()` shows "EOC reasoning: <question wording>" instead of the raw key. |
| D5 | One-line change to the difficulty target in `selectAdaptive`. It now uses a global staircase (start 2, ±0.5 per answer, clamped 1–5) blended with the area's last response (±1). Area coverage order and the trace are unchanged; the trace reason was updated. |
| D6 | Revisited diagnostic items render disabled options and a translated note explaining the lock. |
| D7 | A language picker in the top nav on every page, synced with the in-page pickers. `<html lang>` and `dir` follow the selection (Arabic → `rtl`). English-only sections are marked `lang="en" dir="ltr"` and carry a translated notice. Switching language re-renders an open tour or invitation. |
| D8 | CSS `.topnav .navlinks a{white-space:nowrap}`. |
| D9 | The coverage notice now lists exactly what is and isn't translated, in each language. |

## 4. Adaptive diagnostic: before and after

Measured through the real UI (clicking options) on 20-item runs:

| Student | Before: difficulty sequence | After: difficulty sequence |
|---|---|---|
| All correct | 2,2,2,2,2,2,2,2,2,2,3,3,3,3,3,3,3,3,3,3 (max 3) | 2,3,3,4,4,5,5,5,4,4,4,4,5,5,4,4,4,5,4,4 (17 of 20 at difficulty 4–5) |
| All wrong | 2,2,2,2,2,2,2,2,2,2,2,1,1,3,1,2,1,2,1,2 (first 10 all difficulty 2) | 2,2,1,2,1,2,1,2,1,2,2,1,1,3,1,2,1,2,1,2 (drops to difficulty 1 from item 3; the single 3 is the Systems area, which has no item below difficulty 2 left) |
| Alternating | stays at 2–3 | stays at 2–3 |

Coverage is still exactly 2 items in each of the 10 areas, with 20 unique items. Scoring is exact: 20/20, 0/20 and 10/20 are stored and displayed correctly.

**Content limit, not a code defect:** the bank's difficulty spread is uneven. For example, Systems has 20 items at difficulty 3 and none at difficulty 1. Adding easy Systems items would improve adaptivity for struggling students.

## 5. Mathematical verification evidence

`python3 tests/verify_math.py` → **Verified 325 of 325 items; 0 failures.**

* 150 templated bank items: re-solved with sympy from the stated equation (linear, inequality, slope, evaluation, vertex, maximum, systems, factoring by expansion, zero product, roots, composition, inverse, mean, residual).
* 100 bank word problems and 75 EOC items: recomputed from the problem statement in Python/sympy, independent of the options.
* For every item: the keyed option `o[0]` equals the computed answer, and **no distractor also equals it**.
* The 25 legacy `BWM_DIAGNOSTIC` items are no longer served (they only re-render pre-V2 saved results). They were hand-verified correct.
* Translation fidelity: `python3 tools/check_i18n.py` requires every number and math expression in each English stem and explanation to appear verbatim in all 11 translations. It caught and fixed 4 real slips during authoring (numerals written as words: 1 in Vietnamese, 3 in Arabic).

## 6. Language coverage report

| Surface | en | es | zh | hi | ar | fr | pt | ru | ht | vi | ko | ja |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Dashboard, nav, tabs, How page | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Onboarding tour (5 steps) + invitation | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Adaptive diagnostic (all 250 items) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Results review + explanations | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Prescriptive plan (skills, misconceptions) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Five EOC checkouts (MC) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Lessons index + short lessons | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Cheat Sheets, Blueprints, Flashcards, Test Me, Honors, Interactive, Master Index | ✓ | EN* | EN* | EN* | EN* | EN* | EN* | EN* | EN* | EN* | EN* | EN* |
| Expanded lessons, written performance tasks | ✓ | EN* | EN* | EN* | EN* | EN* | EN* | EN* | EN* | EN* | EN* | EN* |

EN* = English content, shown with a translated notice saying it's English-only for now, and marked `lang="en"` for screen readers. The surrounding nav and tabs stay in the chosen language.

How coverage was tested: the actual rendered text on every screen was compared with an identical English run (zero English-identical text nodes), plus a second scan for stray English words inside translated sentences (zero hits). Not tested: translation-file completeness alone.

**Translation quality caveat:** I authored the translations and checked them for math fidelity and consistency with each language's existing terminology. They have **not** been reviewed by native-speaker math educators. Get that review before marketing any language as fully supported, especially Haitian Creole and Hindi.

## 7. Functional and regression results

`node tests/verify.js` → **68/68 checks passed** (`tests/results.json`). `node tests/english_words.js` → 0 stray English words in 11 languages.

* **G1 Zero feature regression:** in English, all 16 routes have identical controls and identical text to the original, apart from the 2 intended wording fixes (D9 and "English only").
* **P1 Persistence:** language plus an in-progress diagnostic survive a language switch and a reload.
* **A3:** the locked-item behaviour works.
* **X1:** every button, link and select on translated screens has an accessible name.
* **M1:** no horizontal scroll at 375 px (en, ru, vi, ar, hi).
* **R1:** zero JavaScript errors in every language.

## 8. Real-browser verification

Headless Chromium (Playwright 1.56) at desktop 1280 px and phone 375–390 px widths. Screenshots are in `tests/screenshots/`: Arabic RTL dashboard, Japanese phone diagnostic, Spanish plan, Hindi cheat sheet with the English-only notice, and the English dashboard.
**Not done:** testing on physical iOS/Android devices or Safari/Firefox engines. Recommended before the commercial launch.

## 9. Release-gate matrix

| Gate | Result | Basis |
|---|---|---|
| A — Zero feature regression | **PASS** | G1, R1, 68/68 suite |
| B — Complete language coverage | **FAIL (partial)** | The student journey (dashboard → diagnostic → plan → EOC) is complete in 12 languages. The long-form curriculum (~3,200 strings per language) is English-only and honestly labelled. |
| C — Evidence-based certification | **PASS with caveats** | Math 325/325, adaptive, scoring, persistence, accessibility basics and mobile layout verified. Native-speaker review and physical-device testing are not yet done. |

**No known release-blocking defect remains in the translated surfaces.** The one remaining blocker for an "available in 12 languages" claim is translating the long-form curriculum.

## 10. Deliverables

* `ByrdWay_Algebra_Honors_Upgrade_V3.html`: the standalone, downloadable artifact (no external dependencies).
* `original/`: the untouched input. `tools/build.py`: reproducible surgical build. `i18n/`: per-language catalogs (the system for growing to 100+ languages: add `ui.<lang>.json` + `content.<lang>.json` and an entry in `BWM_LANGS`).
* `tools/check_i18n.py`, `tests/verify.js`, `tests/english_words.js`, `tests/verify_math.py`: the reusable certification suite for the next Power Tool upgrades.

## Recommended next moves (by revenue leverage)

1. **Ship V3 as "English + 11-language guided experience"**, marketed truthfully. It's sellable now; don't claim full 12-language curriculum yet.
2. **Translate the long-form curriculum** with the same catalog and fidelity-check pipeline (~3,200 strings × 11). Then run native-speaker review on Spanish first (largest market), then Haitian Creole and Chinese.
3. **Add easy Systems items (difficulty 1–2)** so struggling students get gentler diagnostic items.
4. **Reuse this build-and-test suite** as the template for Algebra 2, Geometry and Precalculus, one per day.
