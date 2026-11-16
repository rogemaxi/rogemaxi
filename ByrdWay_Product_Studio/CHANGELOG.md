# Changelog — Byrd Powerhouse AI

## 6.0.0 — 2026-11-16 · Marketing Intelligence Upgrade (preservation-first)
Baseline preserved: v0.5.0 @ commit 71fcf5b (Windows CI run 43426076078: 214/214 tests, exe self-test PASS). Full
source backup: `ByrdWay_Powerhouse_BASELINE_v0.5.0_71fcf5b_20261116T012413Z.zip` (SHA-256 ca0db6f1…5fe7a, private).

Added (nothing removed, no agent replaced):
- **Marketing Skills library** (github.com/coreyhaines31/marketingskills @ 1f83744, MIT): 53 skills installed in
  `.claude/skills/` (Claude Code discovers them natively); 43 active as tools of the existing 10 Revenue roles,
  10 installed but not activated (not applicable to a TpT seller or need paid services). 163 executable/eval files
  excluded after security review. `marketingskills.py`: inventory, discovery check, run sheets, optional OpenAI run
  through the existing BudgetGuard with Sales QA on every output. See MARKETING_SKILLS_REPORT.md.
- **Revenue targets (owner 6.0):** week 1 = 1,000 verified paid TpT units; weekly ceiling 1,000 × 1.18^(n−1);
  minimum path +10 %/week. Targets only, never shown as sales.
- **SECRET → DISTRIBUTION → PRESSURE TEST** ledger (`compliance.pressure_test`): hypothesis, audience, offer, exact
  TpT page, exposure, clicks, responses, verified orders, paid units, seller proceeds, decision. Every number needs
  its source; unmeasured numbers show NOT MEASURED.
- **Email compliance** (`compliance.presend_check` / `record_sent`): recipient verification, opt-outs (permanent),
  duplicate and 7-day frequency prevention, exact TpT listing + price match, sender identity, postal address,
  opt-out instruction, honest subject, promotional identification, Sales QA. The app never sends email.
- Tab 8 row 4: Marketing Skills library · Run a marketing skill · Check an email draft · Pressure tests.
  Command Center: each Revenue agent's Details lists its skills; RUN output includes its skill run sheets.
- Version 6.0.0 everywhere (window title, docs, self-test, release).

## 0.5.0 — 2026-11-13
Command Center (22 agents), Blotato video platform + publishing, interrupted-job recovery, business intelligence
(labels, acquisition plan, capital allocation, 11 cited segments, offer test). See git history for earlier work.
