# Requirements-to-Evidence Matrix — GCI v0.1.0

Status key: **WORKING** (implemented and tested) · **PARTIAL** · **MISSING** · **FAILED** · **BLOCKED** · **UNVERIFIED**.
Test suite: `python -m unittest discover -s tests -t .` gives 70 tests, all passing on Linux (Python 3.13).

| Phase | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Recovery audit and report | WORKING | `docs/RECOVERY_REPORT.md` |
| 2 | Global coverage (US, JP, CN, IN, EU, UK, CA, KR, TW, AU, EM) | **PARTIAL** | Broad U.S./ex-U.S./global funds are researched. Country-level data adapters are not built. Russia is hard-blocked (`policy.SANCTIONED_MARKETS`), with a test. |
| 2 | Investment universe (US equity, intl equity, fixed income); asset class vs wrapper | WORKING | Snapshot candidates VT, VTI, VXUS, SGOV, BND; each `asset_class` + `wrapper` |
| 2 | No options/margin/leverage/crypto/short | WORKING | `policy.py`; `TestProhibitions`, `test_no_short_selling`, `test_no_margin` |
| 3 | 6 specialists + deterministic Head Manager, minimum set | WORKING | `agents.py` `ROUTES`; `TestRouting` |
| 3 | No self-approval; consequential decisions get independent review | WORKING | `check_not_self_review`, CONSEQUENTIAL guard; tests |
| 3 | Duplicate research prevented | WORKING | `test_duplicate_research_prevented` |
| 3 | LLM-backed specialists | **MISSING (by design for now)** | Specialists are rule-based ($0 per call, reproducible). An LLM backend can sit behind the same interface, metered through the budget controller. |
| 4 | Decision memory with every listed field, immutable | WORKING | `decisions.py` `REQUIRED_FIELDS`; `TestDecisionMemory` |
| 4 | Falsification fixed before outcome, scheduled review, metrics (Brier, falsification rate, accuracy) | WORKING | `review()`, `due_reviews()`, `metrics()` with n<30 warning |
| 5 | Reproducible regime tagging; quarterly matrix with sample sizes | WORKING | `regime.py`, `regime_matrix()`; `TestRegime` |
| 5 | Regime inputs populated | **PARTIAL** | Only equity trend is filled from data (1/8 coverage). CPI, VIX, USD and curve need adapters; they show UNKNOWN and are never guessed. |
| 6 | Rolling windows, walk-forward, OOS, cost/spread sensitivity, drawdown, inflation-adjusted, benchmark, look-ahead and survivorship guards | WORKING (engine) | `backtest.py`; `TestValidation` on **synthetic** series |
| 6 | Validation on real historical prices | **BLOCKED** | Needs a licensed or official price-history source on the owner's machine (network blocked here) |
| 6 | Tax sensitivity | **PARTIAL** | Tax provision rate in certification; no lot-level tax optimisation |
| 7 | Capital threshold gate (4 classes) | WORKING | `viability.py`; `TestViability` |
| 8 | Three ledgers, single-use authorizations, immutable, no commingling | WORKING | `ledgers.py`; `TestLedgers` |
| 9 | Realized-gain certification, carryforward, tax, no double count, 30% proposal flagged unapproved | WORKING | `funding.py`; `TestFunding` |
| 9 | Budget ceiling/floor ($0), auto-suspension | WORKING | `spend()`, `suspend()`; tests and demo step 16 |
| 10 | Matching contributions as capital, capped by owner reserve, confirm-only | WORKING | `matching.py`; `TestMatching`, demo step 18 |
| 11 | JPMorgan read-only API | **BLOCKED** | None verified; see recovery report |
| 11 | CSV import, duplicate prevention, reconciliation, sync timestamps | WORKING | `brokerage.py`; `TestBrokerage` |
| 11 | No passwords, no browser automation, no orders/withdrawals/transfers | WORKING | `refuse()`, CredentialStore forbids brokerage creds; HTTP refusal test |
| 12 | 4-part decision card; approve/reject/defer; never trades | WORKING | `approvals.py`; `TestApprovals`, UI click-through |
| 13 | Unit economics; cost/bp marked unavailable | WORKING | `HeadManager.unit_economics()` |
| 14 | 20X/50X efficiency baseline program | **PARTIAL** | Metrics are captured (jobs, cost, verified decisions, duration). The baseline period has not started and no multiplier is claimed. |
| 15 | Daily/weekly/monthly/quarterly schedule | **PARTIAL** | Due-review detection and alerts on open. No background scheduler yet; Windows Task Scheduler setup is still to do. |
| 16 | 12-section dashboard, labelled stale/simulated/unavailable, working buttons | WORKING | `gci/static/index.html`; `docs/screenshots/01–12`; Playwright click-through |
| 16 | Native Windows app | **PARTIAL** | Local web dashboard (127.0.0.1) launched by `Launch GCI.bat`; not a native window |
| 17 | Versioned schema, provenance, append-only hash-chained audit log | WORKING | `db.py`; tamper test |
| 17 | Encrypted credential store | **UNVERIFIED** | Windows DPAPI code path not run (no Windows host). It refuses plaintext on other OSes (tested). |
| 17 | Backup/restore with integrity check | WORKING | `security.backup/restore`; test |
| 18 | 28 test areas | 26 WORKING · #25 Windows packaging **UNVERIFIED** · #2 live retrieval **BLOCKED** here (failure handling tested) | `tests/` |
| 19 | $40 end-to-end demo (20 steps) | WORKING on Linux | `python -m gci demo --amount 40` → 20/20 |
| 19 | $10,000 scalability demo | WORKING on Linux | 20/20 |
| 19 | "Launch the actual Windows application" | **NOT VERIFIED** | Owner must run on Windows |
| 20 | Release ZIP + SHA-256 + docs | WORKING | `tools/package.py`, `dist/` |
| 20 | Clean-Windows extract-and-launch | **NOT DONE** | See `ACCEPTANCE_CHECKLIST.md` |

## SSOI Addendum — Global Investment Doctrine Library (v0.2.0)

| Requirement | Status | Evidence |
|---|---|---|
| Library covering all 38 named investors/managers + Thorp | WORKING | `data/doctrine/library.json` (39 entries: principles, lens map, region, school, sources, source quality, $40 applicability, cautions); `TestLibrary` |
| Doctrine as research frameworks, not trading instructions | WORKING | Lenses return SUPPORT/CHALLENGE/CAUTION/NEUTRAL/INSUFFICIENT_DATA/NOT_APPLICABLE only; never approve (`test_lenses_never_approve`) |
| Shared library across the existing six roles (no 38 new agents) | WORKING | `doctrine.ROLE_LENSES`; each role's output carries `doctrine_lenses` |
| Competing principles challenge recommendations; no deference to fame | WORKING | One vote per distinct lens (`test_fame_neutral_counting`); dissent records; Judgment answers every CHALLENGE |
| Leverage/derivatives/activism/concentration doctrines not actionable | WORKING | `small_capital` = STUDY_ONLY/PARTIAL; concentration dissent marked POLICY_BLOCKED |
| No fabricated attribution ("X recommends…") | WORKING | `validate_citations` in Auditor; `test_fabricated_attribution_rejected` |
| Doctrine changes real outcomes, transparently | WORKING | Deterministic selection rule: with a 0.80pp equity premium and a single return stream, the $40 recommendation moves from 100% VT to $20 VT + $20 SGOV; reverses if premium > 3pp (`test_rich_equity_premium_keeps_all_equity`) |
| Lens inputs beyond equity valuation (CPI, VIX, credit spreads) | **PARTIAL** | Not in snapshot → INSUFFICIENT_DATA / NOT_APPLICABLE, never guessed |
| Doctrine library fact-check by a human | **UNVERIFIED** | Principles are paraphrased from widely documented public works; owner/analyst review recommended, especially entries marked `source_quality: limited` |
