# GCI v0.3.0 — Requirement Status (Final Master SSOI, institutional-grade)

Classification: **IMPLEMENTED** (built and exercised by a test that checks the required behavior) · **PARTIAL** · **MISSING** · **FAILED** · **BLOCKED** · **UNVERIFIED**.
Evidence commands: `python -m unittest discover -s tests -t .` (108 run on Windows; DPAPI test is Windows-only) · `python -m gci acceptance` (investment $40 20/20, $10,000 20/20, operations 19/19) · `node tools/ui_check.js` (15 sections plus controls) · CI workflow `windows-acceptance` (clean Windows).

## P0 Security and recovery
| Requirement | Status | Evidence / note |
|---|---|---|
| Recover `486aff1` and verify independently | IMPLEMENTED | All 84 prior tests re-run and passing. Re-verification found and fixed 4 defects (below). |
| Identify exposed credentials without revealing values | IMPLEMENTED | 4 findings in `congenial-barnacle/division07-n8n-ready.json` (Stripe **test**-mode key, Printful token, Printify JWT, Google API key). See `data/security/known_exposures.json`. |
| Rotate compromised credentials | **BLOCKED — owner action** | Only you can revoke these at Stripe, Printful, Printify and Google Cloud. GCI keeps live activation suspended until each is confirmed in Security & Audit. |
| Purge secrets from repo history / release artifacts | **BLOCKED — needs your go-ahead** | Rewriting `congenial-barnacle` history is irreversible and is another division's repo. GCI's own release ZIP is scanned and refuses to package if it finds a secret. |
| No secrets in GCI | IMPLEMENTED | Repository and data scan tests; package-time scan. |

## Defects found and repaired in this pass
1. Weekly report took an *older* snapshot as the closing balance, so −$100 of "performance" was really a deposit. Fixed and tested.
2. Imported holdings without a price were valued at $0. Now valued at cost and flagged, and the broker trade price is recorded as a dated observation.
3. Deposits were dated by import time instead of transaction date. Added `effective_date` with a migration.
4. Duplicate-research detection used only the snapshot ID, so changed evidence returned a stale analysis. Now keyed on a hash of the evidence content.
Also fixed: duplicated drift alerts, and exposed business credentials wrongly suspending market-data refresh.

## P1–P3 Engine, doctrine, ledgers, decision memory, validation
| Requirement | Status | Evidence |
|---|---|---|
| Six specialist roles + Head Manager, minimum set, no self-certification | IMPLEMENTED | `TestRouting`, `test_no_self_review` |
| Doctrine library: 39 preserved + Andurand, Cohen, Burry, Paulson (43) | IMPLEMENTED | `test_all_requested_investors_present_and_complete`, `test_original_39_preserved` |
| 10 attributes per investor | IMPLEMENTED (school-level fields labelled) | `test_every_investor_has_all_ten_required_attributes`. Conditions, limitations and risks are partly school-level and say so. |
| Fame-neutral council, no invented quotes or endorsements | IMPLEMENTED | `test_fame_neutral_counting`, `test_fabricated_attribution_rejected` |
| $20/$20 not hard-coded; re-evaluated on current data and owner profile; no-action alternative | IMPLEMENTED | Grid from 100% to 0% equity; `test_rich_equity_premium…`, 5% tolerance → `NO_ACTION` |
| Three ledgers, realized-only research funding (30% proposed, unapproved), reserves | IMPLEMENTED | `TestLedgers`, `TestFunding` |
| Decision memory, falsification, calibration, no rewriting history | IMPLEMENTED | Immutable records; `TestDecisionMemory` |
| Walk-forward, out-of-sample, cost/spread sensitivity, look-ahead and survivorship guards | IMPLEMENTED (engine, synthetic series) | `TestValidation` |
| Validation on real historical prices | **BLOCKED** | Needs a price-history source on your PC (not reachable from the build container) |
| Regime coverage beyond equity trend (CPI, VIX, USD, curve) | **PARTIAL** | Missing inputs report INSUFFICIENT DATA and are never invented |
| Country-level coverage (JP, CN, IN, EU, UK, CA, KR, TW, AU, EM) | **PARTIAL** | Covered through global/ex-U.S. funds; no country-level data adapters yet. Russia is investment-blocked. |

## P4 ByrdWay → Genesis Capital Authorization Bridge
| Requirement | Status | Evidence |
|---|---|---|
| Recover ByrdWay | IMPLEMENTED | Second-pass recovery found **ByrdWay Product Studio** (the Powerhouse Windows app) on branch `claude/vibrant-bardeen-fwsvne`, active today, with verified-net capital allocation in `bizintel.py`. My first audit missed it because it checked only `main`. Also found 4 non-investment branches (Algebra tools, physics course, Lumi animation), out of scope. |
| Read ByrdWay Studio's own sales ledger | IMPLEMENTED (read-only) | `Bridge.import_studio_ledger` reads `Documents\ByrdWay_Product_Studio\revenue\ledger.json` daily, excludes rows Studio marks `test`, and never writes to Studio (tested). The activation package's `seller_proceeds.csv` format is also supported. |
| Tax assumption alignment | **NEEDS OWNER DECISION** | Studio assumes a 25% tax set-aside; the bridge uses a more conservative 30%. Both are assumptions. Set one rate with your tax professional (Settings → bridge rules). |
| Only VERIFIED proceeds; fees/refunds arithmetic checked; duplicates rejected | IMPLEMENTED | `TestBridge` |
| Expenses, tax reserve (30% proposed), business cash reserve ($500 proposed), owner distributions | IMPLEMENTED | `test_available_cash_respects…` |
| Business revenue ≠ personal capital; personal account requires a recorded distribution with stated treatment | IMPLEMENTED | `test_personal_account_requires…` |
| Contribution ceiling; raises only by newly signed policy | IMPLEMENTED | `test_ceiling_raise_is_new_signed_version` |
| Deposit confirmation from broker statements (idempotent) | IMPLEMENTED | Auto-matched on statement import |
| Real ByrdWay revenue today | Shown honestly as **NO VERIFIED REVENUE** | ByrdWay's own report says verified proceeds are UNKNOWN; the template is empty |
| Integration inside the ByrdWay application | IMPLEMENTED as an interface, by design | GCI reads Studio's records; Studio code is not modified (another division, under active development). Studio's "owner pay / giving" bucket is the source for personal contributions. |

## P5 Brokerage capabilities
| Requirement | Status | Evidence |
|---|---|---|
| Investigate recurring/automatic investing | IMPLEMENTED | J.P. Morgan **Autoinvest** verified (Chase FAQ, 2026-11-13): stocks/ETFs/mutual funds; cash accounts only; weekly→yearly; $5 minimum per stock/ETF; free |
| One-time standing authorization (IPS), owner-signed, hash-sealed, versioned | IMPLEMENTED | `TestStandingPolicy` |
| Routine buys without repeated approvals | IMPLEMENTED via broker | You configure Autoinvest once (GCI generates the exact steps); GCI monitors |
| AI never places, edits or pauses broker instructions | IMPLEMENTED | No such code path; refusal tests; breakers raise "pause it yourself by <date>" |
| Read-only API connection to J.P. Morgan | **BLOCKED** | No supported retail read-only API verified. CSV import plus reconciliation instead; shown as NOT CONNECTED. |

## P6–P7 Operations, reporting, reconciliation, circuit breakers, shadow mode
| Requirement | Status | Evidence |
|---|---|---|
| Background daily jobs (8) + weekly report; idempotent | IMPLEMENTED | In-app scheduler thread + `python -m gci run-jobs` + `install-schedule` (Windows Task Scheduler); `test_idempotent_daily_jobs` |
| Interrupted-job recovery | IMPLEMENTED | `test_interrupted_job_recovered_and_rerun` |
| Weekly report with the 12 items; deposits excluded | IMPLEMENTED | `test_weekly_report_twelve_items_excludes_deposits` |
| Immediate exceptions only for urgent categories; deduplicated | IMPLEMENTED | `TestControl`. Channel: in-app banner + Windows toast. Email not configured (needs your SMTP choice). |
| Circuit breakers (stale data, failed reconciliation, compromised credentials, limits, duplicates, missing risk inputs, unexpected integration) | IMPLEMENTED | Tripping never touches broker orders (`brokerage_orders_created: 0` logged) |
| Independent reconciliation before certification | IMPLEMENTED | A failed reconciliation suspends certification, research spend and contributions |
| Shadow mode with 10-item acceptance checklist; activation gated | IMPLEMENTED | Activation refused while any check fails (today: 4 unrotated credentials, plus a real 7-day run still to do) |

## P8–P10 Windows delivery
| Requirement | Status | Evidence |
|---|---|---|
| 15-section dashboard, all controls real | IMPLEMENTED | `docs/screenshots/01–15`; `tools/ui_check.js` exit 0 |
| Persistence, backups, safe restart | IMPLEMENTED | Restart steps in both demos; backup/restore test |
| Clean Windows extraction + launch of the exact ZIP | IMPLEMENTED (CI, clean `windows-latest`) | [Run 43466240282](https://github.com/rogemaxi/rogemaxi/actions/runs/43466240282), commit `3ae154d`: ZIP SHA-256 verified → extracted to an empty folder → 108 tests passed (including **DPAPI encryption round-trip**) → acceptance $40 20/20, $10,000 20/20, operations 19/19 → the real `Launch GCI.bat` answered in 1 s → 17 API endpoints 200 → UI check ok across all 15 sections → Task Scheduler task created (next run 06:40), `run-jobs` executed, task removed. Evidence artifact attached to the run. |
| Windows defects found by that CI and fixed | IMPLEMENTED | [Run 43464963630](https://github.com/rogemaxi/rogemaxi/actions/runs/43464963630) failed at launch. Fixes: background jobs no longer hold the UI lock (separate DB connection), notifications fire-and-forget, launcher falls back to `python.exe`, `cmd /c` quoting. |
| Owner's own PC acceptance | **UNVERIFIED until you run it** | `docs/ACCEPTANCE_CHECKLIST.md` |
