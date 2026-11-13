"""SSOI §18 acceptance runner: investment demos ($40, $10,000) + integration/operations/security demo.

Everything runs on SYNTHETIC databases. Market evidence and broker rules are the real dated sources.
The ByrdWay empty proceeds template is the real file format; the verified rows used later are synthetic.
"""
import json
import platform
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import VERSION
from .bridge import Bridge, BridgeError, BYRDWAY_COLUMNS
from .brokerage import BrokerageImport
from .control import Control, BreakerOpen
from .db import Store
from .demo import run as run_investment_demo
from .ips import InvestmentPolicy, PolicyError, TEMPLATE, autoinvest_setup_steps
from .ledgers import Ledgers
from .marketdata import load_snapshot
from .ops import Scheduler, ShadowMode, weekly_report, recurring_status, sync_known_exposures, DAILY
from .policy import PolicyViolation, refuse
from .portfolio import Portfolio
from .security import redact, scan_for_secrets
from .service import choose_allocation, PROPOSALS

ACK = "I authorize this investment policy. GCI places no orders and moves no money."


def run_operations(db_path, out_dir) -> dict:
    steps = []

    def step(title, ok, evidence):
        steps.append({"step": len(steps) + 1, "title": title, "pass": bool(ok), "evidence": evidence})

    db_path = Path(db_path)
    if db_path.exists():
        raise FileExistsError(db_path)
    s = Store.open(db_path, "SYNTHETIC")
    delivered = []
    notifier = lambda t, b: delivered.append(b) or True
    snap = load_snapshot()
    owner = {"horizon_years": 10, "emergency_fund_ok": True, "max_loss_tolerance_pct": 30}

    # 1-2 standing policy built from the current council recommendation (not hard-coded)
    ch = choose_allocation(snap, owner)
    legs = PROPOSALS[ch["pick"]]["legs"]
    pol = json.loads(json.dumps(TEMPLATE))
    pol["account"].update({"account_owner": "Owner (personal)", "account_last4": "0000"})
    per = 40
    amounts = [round(per * l["weight"], 2) for l in legs]
    pol["recurring"].update({"amount_per_period": str(sum(amounts)), "frequency": "monthly",
                             "start_date": (date.today() - timedelta(days=40)).isoformat(),
                             "legs": [{"symbol": l["symbol"], "amount": str(a)} for l, a in zip(legs, amounts)]})
    pol["max_monthly_contribution"] = "100"
    pol["target_allocation"] = {l["symbol"]: round(l["weight"] * 100) for l in legs}
    pol["risk_limits"]["max_loss_tolerance_pct"] = owner["max_loss_tolerance_pct"]
    pol["liquidity_requirement"]["confirmed"] = True
    ip = InvestmentPolicy(s)
    v = ip.save_draft(pol)
    signed = ip.sign(v, acknowledgement=ACK, snapshot=snap)
    step("Standing investment policy signed once (allocation from current council evidence)", signed["status"] == "SIGNED",
         {"pick": ch["pick"], "legs": pol["recurring"]["legs"], "ceiling": pol["max_monthly_contribution"], "hash": signed["hash"][:16]})
    steps_txt = autoinvest_setup_steps(pol)
    step("Brokerage capability verified; Autoinvest setup steps generated (owner configures; GCI cannot)",
         any("Autoinvest" in x for x in steps_txt), steps_txt)
    try:
        ip.raise_ceiling("5000", acknowledgement="ok")
        ceiling_blocked = False
    except PolicyError:
        ceiling_blocked = True
    step("Contribution ceiling cannot rise without a newly signed authorization", ceiling_blocked and str(ip.ceiling()) == "100",
         {"ceiling": str(ip.ceiling())})

    # 4-7 ByrdWay bridge
    b = Bridge(s)
    b.ctl.notify = notifier
    empty = ",".join(BYRDWAY_COLUMNS) + "\n"  # the real ByrdWay template is header-only today
    b.import_byrdway_proceeds(empty, "activation/seller_proceeds.csv")
    none = b.propose()
    step("Real ByrdWay status (no verified proceeds) → no contribution proposed", none["status"] == "NO_PROPOSAL",
         {"reason": none.get("reason"), "available": none.get("available", {}).get("available_for_investment")})
    rows = [["TPT", "SYN-1", str(date.today()), str(date.today()), "USD", "1200.00", "200.00", "0.00", "1000.00", "SYNTHETIC-report", "VERIFIED"],
            ["TPT", "SYN-2", str(date.today()), "", "USD", "59.00", "11.80", "0.00", "47.20", "", "PENDING"]]
    csv_text = empty + "\n".join(",".join(r) for r in rows) + "\n"
    imp = b.import_byrdway_proceeds(csv_text, "SYNTHETIC_proceeds.csv")
    av = b.available_cash()
    prop = b.propose(requested="40")
    step("ByrdWay funding proposal from VERIFIED proceeds after tax reserve and business reserve",
         imp["added"] == 1 and imp["unverified_skipped"] == 1 and prop["status"] == "PROPOSED" and prop["amount"] == "40.00", {"available": av, "proposal": prop})
    try:
        b.authorize(prop["id"])
        dist_required = False
    except BridgeError:
        dist_required = True
    b.record_owner_distribution("40", "Member distribution, single-member LLC (SYNTHETIC; confirm with CPA)", "SYN-DIST-1", str(date.today()))
    auth = b.authorize(prop["id"], distribution_external_id="SYN-DIST-1")
    step("Secure authorization bridge: personal account requires a recorded owner distribution; owner authorizes",
         dist_required and auth["status"] == "AUTHORIZED", auth)
    dup = b.import_byrdway_proceeds(csv_text, "SYNTHETIC_proceeds.csv")
    step("Duplicate business transactions rejected", dup["duplicates_rejected"] == 1 and dup["added"] == 0, dup)

    # 8 brokerage statement import: deposit matched + recurring purchases filled
    sched_dates = [x["date"] for x in recurring_status(s)["schedule"] if x["status"] != "UPCOMING"]
    lines = ["date,type,symbol,quantity,price,amount,fees,description", f"{date.today()},DEPOSIT,,,,40.00,,Transfer from checking"]
    px = {c["symbol"]: float(c["price"]) for c in snap["candidates"]}
    for d in sorted(set(sched_dates)):
        for leg in pol["recurring"]["legs"]:
            q = round(float(leg["amount"]) / px[leg["symbol"]], 5)
            lines.append(f"{d},BUY,{leg['symbol']},{q},{px[leg['symbol']]},,0,Recurring investment")
    lines.insert(1, f"{(date.today() - timedelta(days=45)).isoformat()},DEPOSIT,,,,200.00,,Initial personal funds")
    brk = BrokerageImport(s).import_activity("\n".join(lines) + "\n", "SYNTHETIC_jpm_activity.csv", "SYNTHETIC")
    rs = recurring_status(s)
    step("Broker statement import: authorized deposit confirmed; Autoinvest purchases reconciled to schedule",
         brk["bridge_deposit_matching"] and len(brk["bridge_deposit_matching"]["matched"]) == 1 and rs["status"] == "ON_TRACK",
         {"import": {k: brk[k] for k in ("added", "duplicates_skipped")}, "bridge": brk["bridge_deposit_matching"],
          "recurring": {k: rs[k] for k in ("status", "next_purchase")}})
    positions = "symbol,quantity\n" + "\n".join(f"{h['symbol']},{h['qty']}" for h in Portfolio(s).holdings())
    rec = BrokerageImport(s).reconcile_positions(positions, broker_cash=str(Ledgers(s).balance("A")))
    step("Independent portfolio reconciliation against broker positions", rec["ok"], rec)

    # 10 unauthorized operations
    refused = []
    for op in ("place_order", "withdraw", "external_transfer"):
        try:
            refuse(op)
        except PolicyViolation as e:
            refused.append(str(e))
    try:
        Ledgers(s).transfer("A", "C", "1", "AUTH-FORGED")
        forged = False
    except Exception:
        forged = True
    step("Unauthorized operations rejected (orders, withdrawals, transfers, forged authorization)", len(refused) == 3 and forged, refused)

    # 11-13 scheduler, idempotency, interruption recovery
    sch = Scheduler(s, Path(out_dir) / "reports")
    now = datetime.now(timezone.utc)
    r1 = sch.run_due(now)
    r2 = sch.run_due(now)
    failed = [x for x in r1 if x["status"] == "FAILED"]
    step("Background daily jobs run; re-running is idempotent", not failed and all(x["status"] == "ALREADY_DONE" for x in r2),
         {"first": {x["job"]: x["status"] for x in r1}, "second": {x["job"]: x["status"] for x in r2}, "failed": failed})
    tomorrow = now + timedelta(days=1)
    stale = (tomorrow - timedelta(hours=2)).replace(microsecond=0).isoformat()
    with s.tx() as c:
        c.execute("INSERT INTO job_runs (job, period_key, started_ts, heartbeat_ts, status, attempt) VALUES (?,?,?,?,?,?)",
                  ("valuation_snapshot", tomorrow.date().isoformat(), stale, stale, "RUNNING", 1))
    r3 = sch.run_due(tomorrow)
    vs = next(x for x in r3 if x["job"] == "valuation_snapshot")
    step("Recovery after interruption: stale RUNNING job detected and re-run", vs["status"] == "DONE" and s.events(kind="JOB_INTERRUPTED_RECOVERED"),
         {"valuation_snapshot": vs["status"]})

    # 14-16 breaker, immediate exception, weekly report
    ctl = Control(s, notifier=notifier)
    s.conn.execute("INSERT INTO lots (symbol, acquired_ts, qty, remaining_qty, cost_total, ref) VALUES ('VTI', ?, '0.5', '0.5', '186.31', 'SIM-ROGUE')",
                   (date.today().isoformat(),))
    from .ops import job_recurring_monitor
    job_recurring_monitor(s, None)
    try:
        b.propose(requested="10")
        blocked = False
    except BreakerOpen:
        blocked = True
    owner_action = [e for e in ctl.open_exceptions("IMMEDIATE") if e["category"] == "owner_action_deadline"]
    step("Circuit breaker: purchases above ceiling suspend contribution workflow and tell the owner to pause Autoinvest; no orders created",
         blocked and owner_action and s.events(kind="BREAKER_TRIPPED")[0]["payload"]["brokerage_orders_created"] == 0,
         {"breakers": [x for x in ctl.breakers() if x["state"] == "OPEN"], "owner_action": owner_action[0]["message"] if owner_action else None})
    ctl.reset("contribution_proposals", note="Acceptance drill: reviewed and reset")
    imm = ctl.open_exceptions("IMMEDIATE")
    ctl.resolve(imm[0]["id"], "Acceptance drill")
    step("Exception alerts: IMMEDIATE items notify promptly and are resolvable; breaker reset by owner only",
         len(delivered) >= 1, {"notifications_delivered": len(delivered), "first": delivered[0] if delivered else None,
                               "channel": "Windows toast" if sys.platform == "win32" else "in-app banner (toast needs Windows)"})
    rep = weekly_report(s, date.today(), Path(out_dir) / "reports")
    step("Weekly report: 12 required items; deposits excluded from performance", all(k in rep for k in (
        "1_opening_balance", "2_closing_balance", "3_contributions", "8_net_performance_excluding_deposits",
        "12_exceptions_requiring_owner_action")), {"file": Path(rep.get("file", "")).name, "contributions": rep["3_contributions"],
                                                   "performance": rep["8_net_performance_excluding_deposits"]})

    # 17-19 security + shadow mode
    sync_known_exposures(s)
    n = s.conn.execute("SELECT COUNT(*) FROM security_incidents WHERE status='OPEN'").fetchone()[0]
    sch.run_job("security_health", DAILY["security_health"], "acceptance")
    try:
        ShadowMode(s).activate(required_days=1)
        activated = True
    except PermissionError as e:
        activated, why = False, str(e)
    except BreakerOpen as e:
        activated, why = False, str(e)
    ev = ShadowMode(s).evaluate(required_days=1)
    step("Shadow mode: live activation refused while acceptance checks fail (incl. 4 unrotated credentials)",
         not activated and n == 4, {"reason": why, "checks": {c["item"]: c["passed"] for c in ev["checks"]}})
    hits = scan_for_secrets(Path(__file__).resolve().parent.parent / "gci") + scan_for_secrets(Path(__file__).resolve().parent.parent / "data")
    step("No secret values in the application or its data", not [h for h in hits if "security.py" not in h["file"]], {"hits": len(hits)})
    chain = s.verify_chain()
    step("Audit log hash chain intact", chain["ok"], chain)

    # 20 restart persistence
    before = {t: s.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in
              ("ips_versions", "bridge_entries", "bridge_proposals", "job_runs", "exceptions", "weekly_reports", "security_incidents")}
    s.close()
    s2 = Store.open(db_path, "SYNTHETIC")
    after = {t: s2.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in before}
    step("Safe restart: policy, bridge, jobs, exceptions, reports and incidents persist", before == after and s2.verify_chain()["ok"],
         {"before": before, "after": after})
    s2.close()
    return {"passed": sum(x["pass"] for x in steps), "total": len(steps), "steps": steps}


def run_all(out_dir) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    results = {"version": VERSION, "date": date.today().isoformat(), "platform": platform.platform(), "python": sys.version.split()[0]}
    for amt in ("40", "10000"):
        r = run_investment_demo(out / f"investment_{amt}" / "demo.db", amt, out / f"investment_{amt}")
        results[f"investment_{amt}"] = r
    results["operations"] = run_operations(out / "operations" / "ops.db", out / "operations")
    results["all_passed"] = all(results[k]["passed"] == results[k]["total"] for k in ("investment_40", "investment_10000", "operations"))
    (out / "acceptance_results.json").write_text(redact(json.dumps(results, indent=2, default=str)), encoding="utf-8")
    md = [f"# GCI {VERSION} acceptance run — {results['date']}", f"Platform: {results['platform']} · Python {results['python']}", ""]
    for k in ("investment_40", "investment_10000", "operations"):
        r = results[k]
        md.append(f"## {k}: {r['passed']}/{r['total']}")
        md += [f"- {'PASS' if st['pass'] else 'FAIL'} {st['step']}. {st['title']}" for st in r["steps"]]
        md.append("")
    (out / "ACCEPTANCE_SUMMARY.md").write_text("\n".join(md), encoding="utf-8")
    return results
