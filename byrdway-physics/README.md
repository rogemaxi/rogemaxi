# ByrdWay Physics I + Honors Power Tool

An offline, single-file interactive course for Physics I and Physics I Honors by Dr. Rogé J. Byrd, ByrdWay Math and Science.

- 20 units and 170 lessons. Each lesson has objectives, a phenomenon, a prediction, explanations, vocabulary, formulas, a worked example, guided and independent practice, misconceptions, a diagram, mastery criteria, an Honors problem and video search links.
- 20 interactive 3D laboratories, each with a 2D fallback, live measurements, graphs, a data table, challenges and a "calculate before you run" check.
- 10 learning engines:
  - Cheat sheets and Blueprints
  - Flashcards (spaced review)
  - Test Me
  - Reality Labs
  - Feynman Discovery Studio
  - Interactive Support
  - an offline guided Tutor
  - Formula Laboratory
  - Error Detective
- Assessment:
  - a 250-item bank and a 20-question adaptive diagnostic that builds a personal plan
  - five mastery levels, with DOK 4 performance tasks and rubrics at Level 4
  - Core and Honors finals
- Reference: formulas, constants, SI units, glossary, misconceptions, Florida standards crosswalk, lab safety, math reference, translation report.
- 12 interface languages: English, Spanish, French, Haitian Creole, Portuguese, Arabic (right-to-left), Chinese, Hindi, Bengali, Vietnamese, Korean, Japanese. Lesson translation is in progress; see `docs/TRANSLATION_REPORT.md`.

## Use it

Open `dist/ByrdWay_Physics_I_Honors.html` in a current browser: Chrome, Edge, Firefox or Safari. It needs no internet connection, server, account or installation.

- **Progress:** saved in the browser on that device. Use **Settings → Export progress** to move it to another device or keep a backup.
- **Privacy:** nothing is sent anywhere. The only exception is the optional cloud tutor, and only if a school enters its own HTTPS service address in the Tutor.
- **Videos:** the links open Khan Academy, YouTube and The Organic Chemistry Tutor search results in a new tab. Those need internet access.

## Build from source

```bash
npm ci                 # esbuild 0.24.0, three 0.170.0, playwright 1.56.1, axe-core 4.10.2 (pinned)
npm run build          # → dist/ByrdWay_Physics_I_Honors.html (single file, all JS/CSS inlined)
npm test               # unit, science, content, bank, formula and lab-model tests
npm run test:e2e       # browser suites against the built file (Playwright + Chromium)
node tests/e2e/a11y.mjs   # axe-core WCAG 2.1 AA audit
npm run report         # regenerate docs/TRACEABILITY.md and docs/STANDARDS_CROSSWALK.md
node tools/i18n.mjs report   # regenerate docs/TRANSLATION_REPORT.md
```

## Layout

| Path | Contents |
|---|---|
| `src/data/curriculum/u01–u20.js` | Lesson content. Each numeric answer has a `calc` expression that the tests re-check. |
| `src/data/resources.json` | Units, sections and video links imported from the owner's workbook (`tools/import_library.py`). |
| `src/data/bank/` | The 250 assessment items and 20 DOK 4 tasks. |
| `src/data/formulas.js` | Executable formulas for the Formula Laboratory. |
| `src/data/reference/` | Standards crosswalk, safety, math and SI reference data. |
| `src/physics/` | Physics library (mechanics, waves/thermo, E&M/modern), tested in `tests/unit/physics.test.js`. |
| `src/lab/` | Lab harness, Three.js and 2D renderers, and the 20 lab models (`labs/labNN.js`), each with `tests/unit/labNN.test.js`. |
| `src/app/` | Views, i18n, storage, narration and quiz runner. |
| `src/engines/` | Pure logic for the study plan, error analysis, assessment and formula solving. |
| `docs/` | Traceability, assessment design, standards crosswalk, compatibility, accessibility/performance, translation and release-readiness reports. |

## Honest limits

- Assessment scores are practice estimates; item difficulties are author-assigned, not psychometrically calibrated.
- Translations are AI-drafted and not yet reviewed by native-speaker teachers. Untranslated text appears in English and is marked as such.
- The standards alignment is provisional until a Florida-certified teacher reviews it.
- Video links are search results, not individually reviewed videos.
- The Tutor is offline guided hints, not AI. Cloud AI works only if a school connects its own service; no API key is ever stored in the file.
