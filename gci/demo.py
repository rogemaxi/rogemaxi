"""Phase 19 end-to-end acceptance demonstration.

Runs against a SYNTHETIC database (never your real records). Market evidence is
the real dated snapshot; every trade, gain and contribution here is SIMULATED.
These are software acceptance tests, not investment-return forecasts.
"""
import json
from datetime import date
from pathlib import Path

from .approvals import Approvals
from .brokerage import BrokerageImport, CONNECTION_STATUS
from .db import Store
from .decisions import DecisionMemory
from .funding import Funding, BudgetSuspended
from .ledgers import Ledgers, LedgerError
from .marketdata import load_snapshot
from .matching import Matching
from .money import D, cents
from .portfolio import Portfolio
from .security import backup, redact
from .service import analyze_starter_allocation


def run(db_path, scenario_amount="40", out_dir=None, horizon_years=10) -> dict:
    steps = []

    def step(n, title, ok, evidence):
        steps.append({"step": n, "title": title, "pass": bool(ok), "evidence": evidence})

    amount = D(scenario_amount)
    db_path = Path(db_path)
    if db_path.exists():
        raise FileExistsError(f"{db_path} exists; demos always start from a fresh synthetic database.")
    s = Store.open(db_path, "SYNTHETIC")
    led, pf, fund = Ledgers(s), Portfolio(s), Funding(s)

    step(1, "Application backend launched", True, {"db": db_path.name, "dataset": s.dataset})
    step(2, "No brokerage connection falsely claimed", "NOT CONNECTED" in CONNECTION_STATUS["jpmorgan_api"], CONNECTION_STATUS)

    snap = load_snapshot()
    step(3, "Current dated research loaded from cited sources", bool(snap["sources"]),
         {"snapshot": snap["snapshot_id"], "sources": len(snap["sources"]), "freshness": snap["freshness"]})

    led.post("A", "CONTRIBUTION", amount, "SIMULATED initial owner capital")
    result = analyze_starter_allocation(s, amount, {"horizon_years": horizon_years, "emergency_fund_ok": True}, snap)
    cards = result["job"]["research"]["cards"]
    classes = {c["asset_class"] for c in cards}
    step(4, "U.S. equity, international equity and fixed income compared",
         {"us_equity", "international_equity"} <= classes and any(c.startswith("fixed_income") for c in classes),
         [{"symbol": c["symbol"], "class": c["asset_class"], "expense_ratio": c["expense_ratio"]} for c in cards])
    step(5, "Eligibility and minimum investment checked",
         all(c["viability"]["classification"] != "INSUFFICIENT INFORMATION" for c in cards),
         {c["symbol"]: c["viability"]["classification"] for c in cards})
    step(6, "Fees and economic viability calculated", True, {c["symbol"]: c["viability"]["checks"] for c in cards})
    step(7, "Researched candidate + no-action alternative", bool(result["card"]["inaction"]),
         {"candidate": "VT", "no_action": result["card"]["inaction"]})
    step(8, "Independent risk and judgment reviews",
         result["job"]["risk"]["verdict"] in ("PASS", "REVIEW", "REJECT") and bool(result["job"]["judgment"]["challenges"]),
         {"risk": result["job"]["risk"]["verdict"], "judgment": result["job"]["judgment"]["recommendation"],
          "auditor_certified": result["job"]["auditor"]["certified"]})
    dm = DecisionMemory(s)
    dec = dm.get(result["decision_id"])
    step(9, "Falsification conditions recorded before outcome", len(dec["falsification"]) >= 1,
         [f"{f['metric']} {f['op']} {f['threshold']}" for f in dec["falsification"]])
    step(10, "Four-part owner decision card created", all(result["card"].get(k) for k in
         ("action", "reason", "inaction", "rejection_conditions")), {k: result["card"][k] for k in
         ("action", "reason", "inaction", "rejection_conditions")})

    decision = Approvals(s).decide(result["approval_id"], "APPROVED", note="SIMULATED owner decision")
    step(11, "Owner decision simulated; no trade placed", decision["trade_executed"] is False, decision)
    step(12, "Decision stored in permanent memory", dm.get(result["decision_id"])["owner_decision"] == "APPROVED",
         {"decision_id": result["decision_id"]})

    price = D(next(c for c in snap["candidates"] if c["symbol"] == "VT")["price"])
    qty = (amount / price).quantize(D("0.00001"), rounding="ROUND_DOWN")
    pf.record_buy("VT", qty, price, 0, external_id="SIM-FILL-1")
    pf.set_price("VT", price, snap["rates"]["as_of"], "Yahoo Finance via snapshot " + snap["snapshot_id"])
    step(13, "Simulated portfolio ledger updated", pf.position("VT")["qty"] == qty,
         {"VT_qty": str(qty), "cash_left": str(cents(led.balance("A"))), "label": "SIMULATED FILL"})

    # 14: hypothetical gain and loss
    g = pf.record_sell("VT", (qty / 2).quantize(D("0.00001")), price * D("1.10"), 0, external_id="SIM-SELL-GAIN")
    pf.record_buy("SGOV", D("0.1"), D("100.53"), 0, external_id="SIM-BUY-SGOV")
    l = pf.record_sell("SGOV", D("0.1"), D("100.00"), 0, external_id="SIM-SELL-LOSS")
    pf.record_income("DIVIDEND", "0.12", "VT", external_id="SIM-DIV-1")
    step(14, "Hypothetical realized gain and loss", g["realized_gain"] > 0 and l["realized_gain"] < 0,
         {"gain": str(cents(g["realized_gain"])), "loss": str(cents(l["realized_gain"])), "dividend": "0.12",
          "label": "HYPOTHETICAL"})

    today = date.today().isoformat()
    cert = fund.certify(today + "T00:00:00", today + "T23:59:59Z")
    net = D(cert["net_realized"])
    expect_alloc = cents(max(net, D(0)) * (1 - D(cert["tax_rate"])) * D(cert["research_share"]))
    step(15, "Research budget calculated from audited realized gains",
         D(cert["proposed_research_allocation"]) == expect_alloc and cert["unrealized_excluded"],
         {k: cert[k] for k in ("net_realized", "tax_provision", "eligible_net_gain", "research_share",
                               "proposed_research_allocation", "research_share_owner_approved")})
    auth = led.authorize("TRANSFER:A->B", cert["proposed_research_allocation"], {"cert": cert["id"]})
    fund.allocate_to_research(cert["id"], auth)
    budget = fund.available_budget()
    fund.set_policy(per_job_cost_cap=str(budget + D("100")))  # owner raises job cap so the BUDGET ceiling is what's tested
    try:
        fund.spend(budget + D("5.00"), "SIM-OVERSPEND")
        rejected = False
        why = None
    except (LedgerError, BudgetSuspended) as exc:
        rejected, why = True, str(exc)
    step(16, "Overspending attempt rejected", rejected, {"budget": str(budget), "attempt": str(budget + 5), "reason": why})

    a = led.authorize("TRANSFER:A->C", "0.50", {"purpose": "protected reserve"})
    led.transfer("A", "C", "0.50", a)
    try:
        led.post("C", "RESERVE_RELEASE", "0.50", "unauthorized release attempt")
        blocked = False
    except LedgerError as exc:
        blocked, msg = True, str(exc)
    try:
        led.transfer("A", "C", "0.50", a)
        reuse_blocked = False
    except LedgerError:
        reuse_blocked = True
    step(17, "Protected reserve controls enforced", blocked and reuse_blocked and led.balance("C") == D("0.50"),
         {"reserve_balance": str(led.balance("C")), "unauthorized_release": msg, "authorization_reuse_blocked": reuse_blocked})

    m = Matching(s).propose(cert["id"], "1.0", owner_available_cash="500", owner_reserve_requirement="400")
    before = pf.summary()
    Matching(s).confirm(m["id"], m["proposed_amount"])
    after = pf.summary()
    gain_unchanged = D(before["investment_gain_total"]) == D(after["investment_gain_total"])
    step(18, "Matching contribution proposed; counted as capital, not return", gain_unchanged,
         {"proposal": m, "investment_gain_before": before["investment_gain_total"],
          "investment_gain_after": after["investment_gain_total"]})

    report = {"title": f"GCI Acceptance Demonstration - ${cents(amount)} scenario", "dataset": "SYNTHETIC",
              "date": today, "portfolio": after, "ledgers": led.reconcile_internal(), "chain": s.verify_chain(),
              "decision": result["decision_id"], "certification": cert}
    out_dir = Path(out_dir or db_path.parent)
    out_dir.mkdir(parents=True, exist_ok=True)
    rep_path = out_dir / f"acceptance_report_{int(amount)}.json"
    rep_path.write_text(redact(json.dumps({"steps": steps, **report}, indent=2, default=str)), encoding="utf-8")
    step(19, "Auditable report generated", rep_path.exists(), {"file": rep_path.name, "chain": report["chain"]})

    backup(s, out_dir / f"backup_{int(amount)}.db")
    counts_before = _counts(s)
    s.close()
    s2 = Store.open(db_path, "SYNTHETIC")
    counts_after = _counts(s2)
    persisted = counts_before == counts_after and s2.verify_chain()["ok"]
    step(20, "Closed and reopened: all records persist", persisted, {"before": counts_before, "after": counts_after})
    s2.close()
    # rewrite the report including step 20
    rep_path.write_text(redact(json.dumps({"steps": steps, **report}, indent=2, default=str)), encoding="utf-8")
    return {"passed": sum(x["pass"] for x in steps), "total": len(steps), "steps": steps, "report": str(rep_path)}


def _counts(s):
    tables = ["events", "ledger_entries", "lots", "realized", "decisions", "approvals", "research_jobs",
              "gain_certifications", "contribution_proposals", "authorizations"]
    return {t: s.conn.execute(f"SELECT COUNT(*) n FROM {t}").fetchone()["n"] for t in tables}
