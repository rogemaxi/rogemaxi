# Independent Human Review Register

Automated tests protect internal consistency: answers re-computed, physics models checked against analytic results, rendering and accessibility rules. They **cannot** establish scientific judgment, curriculum fit, translation quality, or real-device behavior. Each item below needs a named, qualified reviewer, a date and a sign-off, recorded here. **Every row is a release gate.**

| # | What | Why automation cannot cover it | Who should review | Scope | Status |
|---|---|---|---|---|---|
| H1 | Scientific accuracy of all 170 lessons | Tests check arithmetic and model consistency, not whether explanations, simplifications and misconception statements are physically correct and pedagogically sound | Physics teacher or university physicist (two reviewers recommended) | Every section's explanations, misconceptions, derivations and Honors problems; the 250 bank items and 20 DOK 4 tasks | NOT STARTED |
| H2 | Lab model assumptions | Tests show each model matches its own stated equations; a physicist must confirm those are appropriate simplifications for the course | Physics teacher / physicist | The 20 labs' assumptions lists | NOT STARTED |
| H3 | AP Physics 1 / 2 / C topic alignment | Topic titles are copied from College Board; deciding which lesson teaches which topic, and at what depth, is a judgment | AP-trained physics teacher | `docs/CURRICULUM_CROSSWALK.md`, AP columns | NOT STARTED |
| H4 | Cambridge 9702 alignment | Same as H3; Cambridge learning outcomes are more specific than topic headings | Cambridge-experienced teacher | Cambridge column | NOT STARTED |
| H5 | IB DP Physics alignment | IB themes, AHL depth, and the internal-assessment investigation | IB DP physics teacher | IB column | NOT STARTED |
| H6 | NGSS performance-expectation alignment | PEs are three-dimensional (practices, core ideas, crosscutting concepts); topic overlap is not enough | NGSS-trained teacher | NGSS column | NOT STARTED |
| H7 | Florida (optional layer) alignment | Same as H3; Physics 1 Honors (#2003390) list not retrieved | Florida-certified physics teacher | Florida column | NOT STARTED |
| H8 | Translations, 11 languages | All are AI-drafted; terminology, register and meaning need native-speaker teachers | One native-speaker science teacher per language | UI + all lesson, lab, assessment and reference text | NOT STARTED |
| H9 | Assessment validity | Difficulty levels and DOK are author-assigned; no field data | Assessment specialist plus pilot data | Bank, levels, finals, rubrics | NOT STARTED |
| H10 | Real-device performance (3D/2D) | The container has no GPU | Testers following `docs/DEVICE_TEST_PLAN.md` | Device matrix D1–D7 | NOT STARTED |
| H11 | Screen-reader accessibility | axe-core and keyboard tests cover only part of WCAG | Accessibility tester using NVDA / VoiceOver / TalkBack | Core paths | NOT STARTED |
| H12 | Laboratory safety text | Safety guidance must match local school policy | Science department head | Reference → Safety | NOT STARTED |
| H13 | Video links | Links are search results; content is not controlled | Teacher spot check | Video library | NOT STARTED (links are labeled as searches in the app) |
| H14 | Brand and third-party names | Names and trademarks used (AP®, IB, Cambridge, CPALMS, Khan Academy, YouTube, Feynman) | Owner / legal | Wording in the UI and docs | NOT STARTED |

## Sign-off log
| Item | Reviewer (name, credential) | Date | Result | Notes / issues filed |
|---|---|---|---|---|
| | | | | |
