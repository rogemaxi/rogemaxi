# Assessment Design — ByrdWay Physics I + Honors

Code: `src/engines/assess.js` (pure logic, unit-tested in `tests/unit/bank.test.js`), `src/app/views/assess.js` (UI), bank in `src/data/bank/`.

## Item bank
- 250 original items: 13 per unit for Units 1–10, 12 per unit for Units 11–20. Each item has a unit, section, mastery level (1–5), honestly assigned DOK (1–3), Honors flag, skill tag, optional prerequisite tag, and a worked solution.
- Numeric items carry an independent `calc` expression; the test suite re-computes every answer (≤ 1 %). In the app, answers are graded against the exact calc value with 2.5 % tolerance (accepts 3-significant-figure rounding). Wrong numeric answers are analyzed by the Error Detective (sign, prefixes, ½, squares, g, unit conversions, reciprocal, π).
- Multiple-choice items have four choices and an explanation for each distractor.
- Every Core section of the course is assessed by at least one item; every unit has items at all five levels.
- Difficulty levels are **author-assigned**. No psychometric calibration (IRT, field testing) has been done.

## Adaptive readiness diagnostic
- 20 questions, one from each unit, units in random order.
- Staircase: ability θ starts at 2. After each answer θ moves by ±step (correct = up), where step = max(0.4, 0.9/√(k+1)) for the k-th answer, clamped to [1, 5]. The next item is the unused item of the next unit whose level is nearest θ.
- Verified properties (tests): a student who answers everything correctly ends at θ = 5 and sees mostly Level 4–5 items in the second half; all wrong ends at θ = 1 with Level 1–2 items; a student who knows only Level ≤ 2 material settles near θ ≈ 2–3.
- **Learning plan:** strengths (units with every item correct), focus units (any miss), prerequisite gaps (prerequisite tags of missed items), and recommended sections = each missed item's section plus the prerequisite sections named in that lesson, in course order. Suggested practice links to Test Me and Flashcards for the focus units.
- **Honors readiness** (dashboard): "ready" if Level 3 best ≥ 80 %, or diagnostic ≥ 75 % overall with ≥ 2 Honors items answered and ≥ 60 % of them correct; otherwise "building", or "not enough evidence" when nothing has been taken.

## Five mastery levels
Each level draws 12 items of exactly that level, spread round-robin across units (Unit 19 enrichment appears only at Level 5).
1. Foundational Mastery — recall and direct use.
2. Developing Proficiency — guided multistep.
3. Independent Application — unfamiliar grade-level problems.
4. Extended Reasoning — DOK 3 items **plus** one of 19 DOK 4 performance tasks (one per Physics I unit; Unit 19's task is enrichment). Each task has a real-world scenario with data, three parts ending in design/justify/critique, a 4-criterion × 4-level rubric, and an exemplar. Responses and rubric scores are saved; scoring is by the student or teacher — the app does not pretend to grade open-ended reasoning.
5. Advanced Honors Challenges — multiconcept Honors items.

## Finals
- **Core final:** 38 items, two per Physics I unit (Unit 19 excluded), levels 1–4, no Honors items.
- **Honors final:** 38 items, two per unit, levels 3–5, Honors items first.
- Results show a per-unit breakdown. All scores are labeled practice estimates, not validated test scores.

## Unit assessments
All bank items of a unit, shuffled, with links to the lessons of missed items.
