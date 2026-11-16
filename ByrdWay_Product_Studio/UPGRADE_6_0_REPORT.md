# Byrd Powerhouse 6.0.0 — upgrade report (before / after, security, cost, limitations)

## Discovered baseline
| Item | Baseline (before) |
|---|---|
| Version / commit | 0.5.0 @ 71fcf5b (branch claude/vibrant-bardeen-fwsvne) |
| Windows verification | CI run 43426076078: 214/214 tests, no skips allowed; exe self-test from the ZIP PASS |
| Agents | 12 Engineering + 10 Revenue & Media = 22 (Command Center) |
| Modules / test files | 34 Python modules / 23 test files |
| Integrations actually configured in the app | Blotato REST (owner key, verified live 2026-11-13: YouTube connected); OpenAI (optional, BudgetGuard); TpT = CSV sales import (TpT has no seller API) |
| Not present in the app (nothing to preserve) | Gmail, n8n. Notion CRM lives in the owner's Notion workspace, outside the app. |
| Backup | full source archive, timestamped, SHA-256 recorded (private deliverables/backups) |

## After (6.0.0)
| Item | After |
|---|---|
| Agents | **22 preserved** (same roles, names, statuses; no agent added or removed) |
| Marketing skills | **53 installed**, 43 active in existing roles, 10 installed-not-activated (reasons in MARKETING_SKILLS_REPORT.md) |
| New modules | marketingskills.py, compliance.py (+ tests/test_marketing_6_0.py) |
| Changed behaviour | weekly targets (owner directive: 1,000 then ≤ +18 %/week); 2 existing tests updated to the new owner numbers, none weakened |
| Tests | see VERIFICATION_MANIFEST.txt in the release (Windows) and TEST_RESULTS section below |

## Security and dependency review
- Library license MIT; provenance pinned to commit 1f837447…; content hash in `.claude/skills/SOURCE.json`.
- Scan of all 53 skills: no prompt-injection text; 29 executable files (Node teardown scraper, 2 Python helpers,
  26 website-tracking JS snippets) and 134 eval/data files **excluded** — the app never executes third-party code.
- Reference docs contain example `curl` commands and third-party API names (PostHog, Gemini, ElevenLabs, Ahrefs);
  they are documentation only, never executed; any paid tool they mention requires separate owner approval.
- No new Python dependencies. No secrets in source, templates, logs or the ZIP (scan in CI evidence).
- Email: the app cannot send; compliance gate blocks non-compliant drafts; opt-outs permanent.

## Actual additional cost
**$0.** No subscriptions, API calls, ads or purchases were made. Optional OpenAI use stays at $0 unless you fund it
in tab 4 (budget.funded_usd defaults to 0).

## Known limitations (6.0)
- Skills run in the app as deterministic run sheets (free). Full AI execution of a skill needs your OpenAI key and
  funded budget (each call approved by you). In Claude Code the skills run natively.
- When Claude Code invokes a skill WITH a request, it substitutes `$0`/`$1`-style text in the displayed skill with
  request words (seen in marketing-psychology's price examples). The installed files are byte-identical to upstream.
- The 1,000 × 1.18^(n−1) ceiling is a target: week 26 = 62,669 units, week 52 = 4.6 million. Real sales are $0
  recorded until a TpT report is imported.
- No Gmail/n8n integration exists to test; cold email stays manual (draft → pre-send QA → you send → record).
- Blotato: only YouTube connected in your account; Facebook/Instagram/TikTok must be connected by you.
