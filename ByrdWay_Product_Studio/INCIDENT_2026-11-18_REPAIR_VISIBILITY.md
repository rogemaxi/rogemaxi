# Incident 2026-11-18 — "12 findings, 11 correctable automatically, 0 need a person" + repair that looked stalled

Product: *ByrdWay Anime Explained Algebra 1 + Honors.pdf* (14 image-only pages), SHA-256 `be2309cba0421586…` (the same
file as the owner's screenshot, reproduced from the owner's upload on 2026-11-18).

## Root cause (confirmed by reproduction, not assumed)
| # | Question from the SSOI | Finding (evidence) |
|---|---|---|
| 1 | Why 12 = 11 + 0? | The 12th finding is **P001, severity INFO, "14 image-only pages: read by the page reader (OCR)…"**. It is informational (no defect, no action). The summary only counted "has a correction" and "DETECTED without a correction"; an INFO note (state SUSPECTED) fell in **neither** bucket. |
| 2 | Is the 12th misclassified or omitted from repair? | Correctly not repaired (nothing to fix); it was only missing from the accounting. |
| 3 | Does "Repair a Copy & Verify" create and dispatch a job? | **Yes.** Reproduced: job created, protected copy made, baseline read, Release QA run, job saved, shown in tab 2. |
| 4 | Stalled, failing silently, or not communicating? | **Not communicating.** The job ran 132 s on this machine (longer on a laptop) and sent only **3 progress messages**, with silences of **65 s**: page-reading progress was passed to the reader only when owner decisions existed (`dkw = {...} if decisions else {}`), and Release QA's re-reading had no progress at all. |
| 5 | Queue / threads / callbacks / exceptions | Background thread + queue worked; no exception; the busy guard already blocks a second job while one runs. |
| 6 | Results transferred to tab 2? | Yes: job record, report, evidence written; the app switched to tab 2. |
| 7 | Were findings mis-reported? | The **label** was wrong: the 11 corrections were read from page images (OCR). By design (and per this SSOI: no speculative corrections from OCR), the repair job does **not** apply them until the owner confirms each one in tab 2. So "11 correctable automatically" was false; the job correctly applied **0** and ended `NOT_VERIFIED / UNFIXABLE_DEFECTS_REQUIRE_HUMAN` without telling the owner the next step. The 2 math findings (p.8 "320+400 = 760" → 720; "6y=16 → y = 8" → 8/3) and 9 typos are real readings. |

## Surgical repairs (3 files; nothing else touched)
| File | Change | Why |
|---|---|---|
| `orchestrator.py` | `classify_findings()`: every finding in exactly one class — **automatic**, **needs your confirmation** (read from a page image), **needs a person**, **informational**; asserts the classes add up to the total. `accounting_line()` for the summary. | Defect 1 + 7 |
| `orchestrator.py` | Repair job passes page progress to the baseline read, every re-read and Release QA; announces Stage 1/4–4/4 with real counts (attempted / applied / failed); `repair_summary()` writes a terminal result (SUCCESS / PARTIAL / WAITING FOR YOUR CONFIRMATION / NOT VERIFIED / FAILED), still-open count, verification decision, real elapsed seconds and the exact next step. | Defect 4 |
| `app.py` | Diagnosis line uses the reconciled accounting; status bar shows "running N s - last step: …" (real seconds, no percentage); a dialog with the terminal result and next step when the job ends. | Defect 4 + 7 |
| `report.py` | Diagnosis report "NEXT STEP" uses the four classes; never says "corrected automatically" for OCR findings. | Defect 7 |

Not changed: the repair engine's decisions, verification checks, the 22 agents, the Revenue & Media Division, Blotato,
API keys, settings files, products, approved assets.

## Evidence on the real product (Linux reproduction, same code as the Windows build)
| | Before | After |
|---|---|---|
| Diagnosis summary | "12 findings, 11 correctable automatically, 0 need a person" | "12 findings = 0 correctable automatically + 11 need your confirmation (read from page images) + 0 need a person + 1 informational" |
| Repair progress messages | 3 | 36 |
| Longest silence | 65 s | 7.9 s |
| End of job | "JOB …: NOT_VERIFIED" | RESULT **WAITING FOR YOUR CONFIRMATION** in 125 s + exact next step (tab 2 → Review Image Findings → Repair Confirmed on a Copy) |
| Original SHA-256 before / after | be2309cba0421586… / be2309cba0421586… | be2309cba0421586… / be2309cba0421586… (unchanged) |

## Tests
New: `tests/test_repair_visibility.py` (5): accounting reconciles; OCR corrections never labeled automatic; every stage +
page progress + terminal next step; confirmed repair reaches an independently verified result; a second Repair press
while one runs is refused.

## Install / rollback
- Install: extract the new release ZIP into a NEW folder (e.g. Documents\ByrdWayStudio_6.0.1) and run it. Your
  workspace (Documents\ByrdWay_Product_Studio), settings and keys are reused untouched.
- Rollback: close it and start your previous folder's ByrdWayStudio.exe again. Nothing in the workspace format changed.
