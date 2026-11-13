# Genesis Capital Intelligence (GCI)

Owner-controlled investment research and decision-support system for Genesis 2 & 7, LLC.
**It never places trades, moves money, or logs into your brokerage.** You decide; you execute at J.P. Morgan; GCI records, checks and remembers.

## Run (Windows)
- `Launch GCI.bat` starts the dashboard at http://127.0.0.1:8765 (your REAL data, stored in `%LOCALAPPDATA%\GenesisCapitalIntelligence`).
- `Run Acceptance Demo.bat` runs the $40 and $10,000 acceptance demos on a separate SYNTHETIC database, plus the test suite.

Requires Python 3.11+. No third-party packages (standard library only), so there is no dependency manifest beyond Python itself.

## Command line
```
python -m gci serve [--db PATH] [--dataset REAL|SYNTHETIC] [--port 8765]
python -m gci demo --amount 40 --out demo_output
python -m gci verify --db PATH
python -m unittest discover -s tests -t .
python tools/package.py      # release ZIP + SHA-256
```

## Architecture (`gci/`)
| Module | Role |
|---|---|
| `db.py` | Versioned SQLite schema, REAL/SYNTHETIC separation, append-only hash-chained event log |
| `ledgers.py` | Ledger A (investment), B (research), C (reserve); single-use owner authorizations |
| `portfolio.py` | FIFO lots, realized/unrealized, income, returns excluding deposits |
| `funding.py` | Realized-gain certification, loss carryforward, research budget, auto-suspension |
| `matching.py` | Owner matching-contribution proposals (capital, never return) |
| `viability.py` | Capital-threshold gate |
| `doctrine.py` + `data/doctrine/library.json` | Global Investment Doctrine Library (39 investors) and fame-neutral Doctrine Council used by all six roles |
| `agents.py` | 6 specialists + deterministic Head Manager (routing, no self-review, dedupe, unit economics) |
| `decisions.py` / `regime.py` | Decision memory, falsification, calibration, regime tagging and matrix |
| `backtest.py` | Walk-forward, rolling windows, cost sensitivity, look-ahead and survivorship guards |
| `brokerage.py` | CSV import, duplicate prevention, reconciliation |
| `marketdata.py` | Dated evidence snapshots, live Treasury adapter, staleness flags |
| `approvals.py` | Four-part decision cards |
| `security.py` | Secret redaction and scanning, DPAPI credential store, backup and restore |
| `server.py` + `static/` | 12-section dashboard (localhost only, per-session token on writes) |

## Data sources
See `data/evidence/*.json`. Every value carries its URL, as-of date and retrieval time. Free sources are not exchange-licensed real-time feeds.

## Status, limits, and agent roles
- Status of every requirement: `docs/REQUIREMENTS_MATRIX.md`
- What existed before this build: `docs/RECOVERY_REPORT.md`
- Sign-off steps on Windows: `docs/ACCEPTANCE_CHECKLIST.md`

Backtests are labelled hypothetical. No returns are promised. 20X/50X are research-efficiency targets, not return targets.
