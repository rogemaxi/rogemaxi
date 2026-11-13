# GCI Phase 1: Recovery Audit Report

**Date:** 2026-11-13 · **Auditor:** Claude Code · **Scope:** Genesis Capital Intelligence (GCI) only. The ByrdWay Engineering and Marketing divisions were not touched.

## 1. What was searched

| Location | Method | Result |
|---|---|---|
| `rogemaxi/rogemaxi` (this repo) | git history and file tree | 1 commit ("Initialize repository"), only `.gitkeep`. **No GCI code.** |
| `rogemaxi/congenial-barnacle` (private) | cloned and scanned | One n8n workflow (`division07-n8n-ready.json`, ByrdWay "Global Reach" division). **No GCI code.** ⚠ See security finding. |
| Google Drive | full-text search for "Genesis Capital Intelligence", "GCI", "JPMorgan", "Capital Intelligence", "investment ledger" | ByrdWay Powerhouse SSOIs, Z28/Z29 division notes, books. **No GCI spec, code, prototype, or investment records.** |
| Notion | search for "Genesis Capital Intelligence" | No results. |

## 2. Verdict

There was **no prior GCI implementation** to recover: no code, tests, interfaces, ledgers, or investment records. That makes "last working implementation" **MISSING**. Every SSOI function started as MISSING, and GCI v0.1.0 was built from zero in this repository as a separate module. Nothing approved was overwritten.

Related material that was found but **deliberately not reused**: Drive notes for a ByrdWay "Division 03B" describe a "70% reinvestment / 30% extraction" loop and "1000X" targets. That is a marketing-division concept. It conflicts with this SSOI's realized-gains-only funding rule and no-return-promise rule, so it was left out.

## 3. Security finding (outside GCI scope; action needed by the owner)

`rogemaxi/congenial-barnacle` → `division07-n8n-ready.json` was committed with the message "all nodes and credentials embedded". GCI's secret scanner finds **4 secret-shaped strings** in it (API-key/Bearer patterns; values not printed). The repo is private, but anyone with access to the repo can read these keys from git history.
**Recommended:** rotate those API keys at each provider, then remove them from the file and from git history. This was not changed because it belongs to another division.

## 4. JPMorgan integration (Phase 11 finding)

- **Read-only API:** no supported, owner-usable read-only API for a retail J.P. Morgan Self-Directed Investing account was verified. Status: **BLOCKED / UNVERIFIED**. GCI uses CSV statement import and reconciliation instead. Third-party aggregators (for example Plaid) may be an option, but they were not verified and are not implemented.
- **Verified broker facts** (sources in `data/evidence/2026-11-13_snapshot.json`): $0 online stock/ETF commissions. Fractional shares from $5 for S&P 500 and NASDAQ-100 stocks and listed ETFs; VT, VTI, VXUS, SGOV and BND appear on the eligible list. Sales carry a $0.01–$0.03 per $1,000 transaction fee.
- **Stale input:** the eligibility list is **dated 2024-11-19**. The dashboard flags it as stale. Confirm eligibility in the J.P. Morgan app before acting.

## 5. Environment limits encountered

- This build container's network policy blocks direct calls to Treasury, FRED and Yahoo. Live data was retrieved through a sourced research tool and saved as a dated snapshot. The shipped app calls Treasury directly on the owner's machine, and when that fails it says so instead of inventing data.
- **No Windows host was available here.** Launching the ZIP in a clean Windows environment is **NOT DONE** and must be done by the owner (see `ACCEPTANCE_CHECKLIST.md`).
