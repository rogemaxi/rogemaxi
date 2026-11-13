"""Quiet background operations (SSOI §14, §16).

* Jobs are idempotent: each (job, period) completes at most once. Re-running the scheduler is always safe.
* Interrupted jobs (RUNNING with a stale heartbeat, e.g. after a crash or reboot) are marked INTERRUPTED and
  re-run, up to 3 attempts, then FAILED with an exception.
* Routine results go into the weekly report. Only IMMEDIATE exceptions interrupt the owner.
* Shadow mode is the default. Leaving it requires every acceptance check to pass.
"""
import json
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .control import Control
from .db import Store, now_iso
from .decisions import DecisionMemory
from .doctrine import load_library, validate_citations
from .ips import InvestmentPolicy, expected_schedule, validate as validate_ips
from .ledgers import Ledgers
from .marketdata import load_snapshot, fetch_treasury_bills, DataUnavailable
from .money import D, ZERO, cents
from .portfolio import Portfolio, modified_dietz

KNOWN_EXPOSURES = Path(__file__).resolve().parent.parent / "data" / "security" / "known_exposures.json"
HEARTBEAT_STALE = timedelta(minutes=15)
MAX_ATTEMPTS = 3


def _today(now=None):
    return (now or datetime.now(timezone.utc)).date()


def week_key(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


# ------------------------------------------------------------------ job bodies
def job_market_data(s, now):
    ctl = Control(s)
    out = {}
    try:
        out["treasury_live"] = fetch_treasury_bills()
    except DataUnavailable as exc:
        out["treasury_live"] = None
        if "format" in str(exc) or "column" in str(exc):
            ctl.trip("integration_unexpected", f"Treasury data format changed: {exc}")
        out["live_error"] = str(exc)
    snap = load_snapshot(today=_today(now))
    stale = {k: v for k, v in snap["freshness"].items() if v["stale"]}
    if "prices" in stale or "rates" in stale:
        ctl.trip("stale_data", f"Evidence snapshot stale: {', '.join(stale)}")
    elif stale:
        ctl.raise_exception("stale_data", f"Stale reference data: {', '.join(stale)}", dedupe_key=f"stale:{','.join(sorted(stale))}",
                            severity="WEEKLY")
    out["stale"] = list(stale)
    return out


def job_valuation_snapshot(s, now):
    summ = Portfolio(s).summary()
    rec = {**{k: summ[k] for k in ("cash", "market_value", "total_value", "net_contributions", "realized_gain",
                                   "unrealized_gain", "income", "all_positions_priced")},
           "holdings": summ["holdings"], "ledger_B": str(Ledgers(s).balance("B")), "ledger_C": str(Ledgers(s).balance("C"))}
    with s.tx() as c:
        c.execute("INSERT OR REPLACE INTO valuation_snapshots VALUES (?,?)", (_today(now).isoformat(), json.dumps(rec)))
    return {"total_value": rec["total_value"]}


def job_risk_monitor(s, now):
    ctl = Control(s)
    ip = InvestmentPolicy(s).active()
    summ = Portfolio(s).summary()
    total = D(summ["total_value"])
    out = {"drift": []}
    if not ip:
        out["note"] = "No signed policy; allocation bands not checked."
        return out
    tgt, band = ip["policy"].get("target_allocation", {}), D(str(ip["policy"].get("allocation_bands_pp", 10)))
    if total <= 0 or not tgt:
        return out
    held = {h["symbol"]: D(h["market_value"] or 0) / total * 100 for h in summ["holdings"]}
    for sym, t in tgt.items():
        diff = held.get(sym, ZERO) - D(str(t))
        if abs(diff) > band:
            out["drift"].append({"symbol": sym, "actual_pct": str(round(held.get(sym, ZERO), 1)), "target_pct": t})
    if out["drift"]:
        ctl.raise_exception("allocation_drift", f"Allocation outside bands: {out['drift']}", dedupe_key=f"drift:{sorted(d['symbol'] for d in out['drift'])}",
                            severity="WEEKLY")
    if ip["policy"]["risk_limits"].get("max_loss_tolerance_pct") is None:
        ctl.trip("missing_risk_inputs", "Signed policy lacks a maximum loss tolerance")
    return out


def recurring_status(s, now=None, tolerance_days=4) -> dict:
    """Compare J.P. Morgan Autoinvest's expected purchases with imported broker activity."""
    ip = InvestmentPolicy(s).active()
    if not ip or not ip["policy"]["recurring"].get("legs"):
        return {"status": "NOT_CONFIGURED", "message": "No signed policy with an Autoinvest plan."}
    pol = ip["policy"]
    today = _today(now)
    start = pol["recurring"].get("start_date") or ip["signed_ts"][:10]
    sched = expected_schedule(pol, start, (today + timedelta(days=45)).isoformat())
    lots = [dict(r) for r in s.conn.execute("SELECT * FROM lots WHERE acquired_ts >= ?", (start,))]
    used, rows = set(), []
    for ev in sched:
        d = date.fromisoformat(ev["date"])
        for leg in ev["legs"]:
            want = D(leg["amount"])
            hit = next((l for l in lots if l["id"] not in used and l["symbol"] == leg["symbol"].upper()
                        and abs((date.fromisoformat(l["acquired_ts"][:10]) - d).days) <= tolerance_days
                        and abs(D(l["cost_total"]) - want) <= max(D("0.05"), want * D("0.02"))), None)
            if hit:
                used.add(hit["id"])
                st = "FILLED"
            elif d > today:
                st = "UPCOMING"
            elif (today - d).days <= tolerance_days:
                st = "PENDING_IMPORT"
            else:
                st = "MISSING"
            rows.append({"date": ev["date"], "symbol": leg["symbol"], "amount": str(want), "status": st,
                         "lot": hit["id"] if hit else None})
    unexpected = [l for l in lots if l["id"] not in used]
    month_spend = {}
    for l in lots:
        m = l["acquired_ts"][:7]
        month_spend[m] = month_spend.get(m, ZERO) + D(l["cost_total"])
    ceiling = D(pol["max_monthly_contribution"])
    over = {m: str(cents(v)) for m, v in month_spend.items() if v > ceiling}
    nxt = next((r for r in rows if r["status"] == "UPCOMING"), None)
    status = "OVER_CEILING" if over else ("MISSING_PURCHASES" if any(r["status"] == "MISSING" for r in rows) else "ON_TRACK")
    return {"status": status, "schedule": rows, "unexpected_purchases": [{"symbol": l["symbol"], "date": l["acquired_ts"][:10],
            "cost": str(cents(D(l["cost_total"])))} for l in unexpected], "months_over_ceiling": over,
            "next_purchase": nxt, "ceiling": str(ceiling)}


def job_recurring_monitor(s, now):
    ctl = Control(s)
    r = recurring_status(s, now)
    if r["status"] == "OVER_CEILING":
        pol = InvestmentPolicy(s).active()["policy"]
        from .ips import BROKER_RULES
        dl = BROKER_RULES["edit_deadline_business_days"][pol["recurring"]["funding_source"]]
        ctl.trip("limit_exceeded", f"Purchases exceed the signed monthly ceiling in {list(r['months_over_ceiling'])}")
        ctl.raise_exception("owner_action_deadline",
                            f"Pause or edit Autoinvest in the Chase app at least {dl} business day(s) before the next trade "
                            f"({(r['next_purchase'] or {}).get('date', 'next scheduled date')}). GCI cannot and will not change it.",
                            dedupe_key=f"pause-autoinvest:{list(r['months_over_ceiling'])}")
    if any(x["status"] == "MISSING" for x in r.get("schedule", [])):
        ctl.raise_exception("recurring_missing", "Expected Autoinvest purchase(s) not found in imported statements "
                            "(import a newer statement, or check the plan in the Chase app).",
                            dedupe_key=f"missing:{[x['date'] for x in r['schedule'] if x['status'] == 'MISSING']}", severity="WEEKLY")
    if r.get("unexpected_purchases"):
        ctl.raise_exception("unexpected_purchase", f"Purchases outside the Autoinvest plan: {r['unexpected_purchases']} — confirm "
                            "they were yours.", dedupe_key=f"unexp:{r['unexpected_purchases']}", severity="WEEKLY")
    return {"status": r["status"]}


def job_reconciliation_status(s, now):
    ev = s.events(limit=1, kind="BROKER_RECONCILIATION")
    if not ev:
        Control(s).raise_exception("reconciliation_due", "No brokerage reconciliation yet: import positions and reconcile.",
                                   dedupe_key="recon-never", severity="WEEKLY")
        return {"last": None}
    last = ev[0]
    age = (_today(now) - date.fromisoformat(last["ts"][:10])).days
    if not last["payload"]["ok"]:
        Control(s).trip("reconciliation_failed", "Latest brokerage reconciliation has exceptions")
    elif age > 35:
        Control(s).raise_exception("reconciliation_due", f"Last reconciliation was {age} days ago.", dedupe_key=f"recon-age:{week_key(_today(now))}",
                                   severity="WEEKLY")
    return {"last": last["ts"], "ok": last["payload"]["ok"], "age_days": age}


def job_source_integrity(s, now):
    snap = load_snapshot(today=_today(now))
    bad = [x for x in snap["sources"] if not x.get("url", "").startswith("https://") or not x.get("retrieved_at")]
    lib = load_library()
    lib_issues = validate_citations({"investors": [{"name": i["name"], "principles": i["principles"]} for i in lib["investors"]]}, lib)
    if bad or lib_issues:
        Control(s).raise_exception("source_integrity", f"{len(bad)} bad sources, {len(lib_issues)} doctrine issues",
                                   dedupe_key=f"src:{len(bad)}:{len(lib_issues)}", severity="WEEKLY")
    return {"bad_sources": len(bad), "doctrine_issues": len(lib_issues)}


def job_decision_reviews(s, now):
    due = DecisionMemory(s).due_reviews(_today(now).isoformat())
    if due:
        Control(s).raise_exception("decision_review_due", f"{len(due)} decision review(s) due: {', '.join(due[:5])}",
                                   dedupe_key=f"due:{','.join(due)}", severity="WEEKLY")
    return {"due": due}


def job_security_health(s, now):
    ctl = Control(s)
    chain = s.verify_chain()
    if not chain["ok"]:
        ctl.raise_exception("security_incident", f"Audit log hash chain broken at event {chain['broken_at_seq']}", dedupe_key="chain-broken")
    sync_known_exposures(s)
    open_inc = [dict(r) for r in s.conn.execute("SELECT * FROM security_incidents WHERE status='OPEN'")]
    if open_inc:
        ctl.trip("credentials_compromised", f"{len(open_inc)} exposed credential(s) not yet confirmed rotated")
    return {"chain_ok": chain["ok"], "open_security_incidents": len(open_inc)}


DAILY = {"market_data": job_market_data, "valuation_snapshot": job_valuation_snapshot, "risk_monitor": job_risk_monitor,
         "recurring_monitor": job_recurring_monitor, "reconciliation_status": job_reconciliation_status,
         "source_integrity": job_source_integrity, "decision_reviews": job_decision_reviews, "security_health": job_security_health}


def job_weekly_report(s, now):
    rep = weekly_report(s, _today(now) - timedelta(days=7))
    return {"week_start": rep["week_start"], "file": rep.get("file")}


WEEKLY = {"weekly_report": job_weekly_report}


# ------------------------------------------------------------------ scheduler
class Scheduler:
    def __init__(self, store: Store, report_dir: Path = None):
        self.s = store
        self.report_dir = report_dir

    def recover_interrupted(self, now=None):
        now = now or datetime.now(timezone.utc)
        cutoff = (now - HEARTBEAT_STALE).replace(microsecond=0).isoformat()
        rows = self.s.conn.execute("SELECT * FROM job_runs WHERE status='RUNNING' AND heartbeat_ts < ?", (cutoff,)).fetchall()
        with self.s.tx() as c:
            for r in rows:
                c.execute("UPDATE job_runs SET status='INTERRUPTED', finished_ts=? WHERE id=?", (now_iso(), r["id"]))
                self.s.log("system", "JOB_INTERRUPTED_RECOVERED", {"job": r["job"], "period": r["period_key"], "attempt": r["attempt"]})
        return [dict(r) for r in rows]

    def run_job(self, name, fn, period_key, now=None):
        done = self.s.conn.execute("SELECT 1 FROM job_runs WHERE job=? AND period_key=? AND status='DONE'", (name, period_key)).fetchone()
        if done:
            return {"job": name, "period": period_key, "status": "ALREADY_DONE"}
        running = self.s.conn.execute("SELECT 1 FROM job_runs WHERE job=? AND period_key=? AND status='RUNNING'", (name, period_key)).fetchone()
        if running:
            return {"job": name, "period": period_key, "status": "IN_PROGRESS_ELSEWHERE"}
        attempts = self.s.conn.execute("SELECT COUNT(*) n FROM job_runs WHERE job=? AND period_key=?", (name, period_key)).fetchone()["n"]
        if attempts >= MAX_ATTEMPTS:
            return {"job": name, "period": period_key, "status": "GAVE_UP"}
        with self.s.tx() as c:
            rid = c.execute("INSERT INTO job_runs (job, period_key, started_ts, heartbeat_ts, status, attempt) VALUES (?,?,?,?,?,?)",
                            (name, period_key, now_iso(), now_iso(), "RUNNING", attempts + 1)).lastrowid
        try:
            result = fn(self.s, now)
            status = "DONE"
        except Exception as exc:  # job failure is recorded, never silently swallowed
            result, status = {"error": str(exc), "trace": traceback.format_exc()[-800:]}, "FAILED"
            if attempts + 1 >= MAX_ATTEMPTS:
                Control(self.s).raise_exception("job_failed", f"{name} failed {MAX_ATTEMPTS} times for {period_key}: {exc}",
                                                dedupe_key=f"jobfail:{name}:{period_key}", severity="WEEKLY")
        with self.s.tx() as c:
            c.execute("UPDATE job_runs SET status=?, finished_ts=?, heartbeat_ts=?, result=? WHERE id=?",
                      (status, now_iso(), now_iso(), json.dumps(result, default=str), rid))
        return {"job": name, "period": period_key, "status": status, "result": result}

    def run_due(self, now=None) -> list:
        now = now or datetime.now(timezone.utc)
        self.recover_interrupted(now)
        day = _today(now).isoformat()
        out = [self.run_job(n, f, day, now) for n, f in DAILY.items()]
        if _today(now).weekday() == 0 or self.s.setting("report_any_day", False):  # Mondays: report on the prior week
            out += [self.run_job(n, f, week_key(_today(now) - timedelta(days=7)), now) for n, f in WEEKLY.items()]
        return out

    def history(self, limit=100):
        return [dict(r) for r in self.s.conn.execute("SELECT id, job, period_key, started_ts, finished_ts, status, attempt "
                                                     "FROM job_runs ORDER BY id DESC LIMIT ?", (limit,))]


# ------------------------------------------------------------------ weekly report
def _snapshot_on_or_before(s, d: str):
    r = s.conn.execute("SELECT * FROM valuation_snapshots WHERE as_of <= ? ORDER BY as_of DESC LIMIT 1", (d,)).fetchone()
    return (r["as_of"], json.loads(r["record"])) if r else (None, None)


def weekly_report(s: Store, week_start: date, report_dir: Path = None) -> dict:
    ws = week_start - timedelta(days=week_start.weekday())
    we = ws + timedelta(days=7)
    a, b = ws.isoformat(), we.isoformat()
    o_date, opening = _snapshot_on_or_before(s, (ws - timedelta(days=1)).isoformat())
    c_date, closing = _snapshot_on_or_before(s, (we - timedelta(days=1)).isoformat())
    if we - timedelta(days=1) >= date.today() or closing is None or c_date < a:
        # The week includes today, or no snapshot falls inside the week: use live ledger values (never an older snapshot).
        closing = Portfolio(s).summary()
        c_date = "live"
    led = [dict(r) for r in s.conn.execute("SELECT * FROM ledger_entries WHERE COALESCE(effective_date, ts) >= ? "
                                           "AND COALESCE(effective_date, ts) < ?", (a, b))]
    sumk = lambda L, kinds: sum((D(e["amount"]) for e in led if e["ledger"] == L and e["kind"] in kinds), ZERO)
    contributions = sumk("A", {"CONTRIBUTION", "MATCH_CONTRIBUTION"})
    ext = sumk("A", {"CONTRIBUTION", "MATCH_CONTRIBUTION", "DISTRIBUTION", "TRANSFER_TO_B", "TRANSFER_TO_C", "TRANSFER_FROM_C", "TAX_PAYMENT"})
    realized = sum((D(r["gain"]) for r in s.conn.execute("SELECT gain FROM realized WHERE ts >= ? AND ts < ?", (a, b))), ZERO)
    income = sumk("A", {"DIVIDEND", "INTEREST"})
    fees = -sumk("A", {"FEE"})
    research = -sumk("B", {"SPEND"})
    open_v = D(opening["total_value"]) if opening else None
    close_v = D(closing["total_value"])
    unreal_close = D(closing["unrealized_gain"])
    unreal_change = unreal_close - D(opening["unrealized_gain"]) if opening else None
    perf = close_v - open_v - ext if open_v is not None else None
    md_ret = modified_dietz(open_v, close_v, [(3, ext)], 7) if open_v not in (None, ZERO) else None
    total = close_v if close_v else D(1)
    alloc = [{"symbol": h["symbol"], "pct": str(round(D(h["market_value"] or 0) / total * 100, 1))} for h in closing["holdings"]] \
        + [{"symbol": "CASH", "pct": str(round(D(closing["cash"]) / total * 100, 1))}] if close_v else []
    ctl = Control(s)
    risks = [f"{b_['label']} suspended: {b_['reason']}" for b_ in ctl.breakers() if b_["state"] == "OPEN"]
    rs = recurring_status(s)
    from .bridge import Bridge
    bridge = Bridge(s).available_cash()
    exc = ctl.open_exceptions()
    rec = {
        "week_start": a, "week_end": (we - timedelta(days=1)).isoformat(), "dataset": s.dataset,
        "1_opening_balance": str(cents(open_v)) if open_v is not None else "INSUFFICIENT DATA (no valuation snapshot before this week)",
        "opening_as_of": o_date, "2_closing_balance": str(cents(close_v)), "closing_as_of": c_date,
        "3_contributions": str(cents(contributions)), "4_realized_gains_losses": str(cents(realized)),
        "5_unrealized_gains_losses": {"closing": str(cents(unreal_close)),
                                      "change": str(cents(unreal_change)) if unreal_change is not None else "INSUFFICIENT DATA"},
        "6_dividends_interest": str(cents(income)), "7_fees": str(cents(fees)), "7_research_expenses": str(cents(research)),
        "8_net_performance_excluding_deposits": {"dollars": str(cents(perf)) if perf is not None else "INSUFFICIENT DATA",
                                                 "modified_dietz_pct": f"{md_ret * 100:.2f}" if md_ret is not None else "INSUFFICIENT DATA"},
        "9_allocation": alloc, "10_material_risks": risks or ["No open circuit breakers."],
        "11_next_contribution": {"autoinvest": rs.get("status"), "next_purchase": rs.get("next_purchase"),
                                 "bridge_available_for_investment": bridge["available_for_investment"], "bridge_status": bridge["status"]},
        "12_exceptions_requiring_owner_action": [{"id": e["id"], "severity": e["severity"], "message": e["message"]} for e in exc],
        "label": "SIMULATED (synthetic dataset)" if s.dataset == "SYNTHETIC" else "Based on your imported records only",
    }
    md = render_markdown(rec)
    with s.tx() as c:
        c.execute("INSERT OR REPLACE INTO weekly_reports VALUES (?,?,?,?)", (a, now_iso(), json.dumps(rec, default=str), md))
        s.log("agent:auditor", "WEEKLY_REPORT", {"week_start": a})
    if report_dir:
        Path(report_dir).mkdir(parents=True, exist_ok=True)
        f = Path(report_dir) / f"GCI_weekly_{a}.md"
        f.write_text(md, encoding="utf-8")
        rec["file"] = str(f)
    return rec


def render_markdown(r):
    L = [f"# Genesis Capital Intelligence — Weekly Report", f"Week {r['week_start']} to {r['week_end']} · {r['label']}", "",
         "| # | Item | Value |", "|---|---|---|",
         f"| 1 | Opening balance | {r['1_opening_balance']} |", f"| 2 | Closing balance | {r['2_closing_balance']} |",
         f"| 3 | Contributions (deposits — not returns) | {r['3_contributions']} |",
         f"| 4 | Realized gains/losses | {r['4_realized_gains_losses']} |",
         f"| 5 | Unrealized gains/losses | {r['5_unrealized_gains_losses']['closing']} (change {r['5_unrealized_gains_losses']['change']}) |",
         f"| 6 | Dividends & interest | {r['6_dividends_interest']} |",
         f"| 7 | Fees / research expenses | {r['7_fees']} / {r['7_research_expenses']} |",
         f"| 8 | Net investment performance excl. deposits | {r['8_net_performance_excluding_deposits']['dollars']} "
         f"({r['8_net_performance_excluding_deposits']['modified_dietz_pct']}%) |",
         f"| 9 | Allocation | {', '.join(a['symbol'] + ' ' + a['pct'] + '%' for a in r['9_allocation']) or '—'} |",
         f"| 10 | Material risks | {'; '.join(r['10_material_risks'])} |",
         f"| 11 | Next contribution | Autoinvest: {r['11_next_contribution']['autoinvest']}; next: "
         f"{(r['11_next_contribution']['next_purchase'] or {}).get('date', '—')}; ByrdWay funds available: "
         f"{r['11_next_contribution']['bridge_available_for_investment']} ({r['11_next_contribution']['bridge_status']}) |",
         f"| 12 | Needs your action | {len(r['12_exceptions_requiring_owner_action'])} item(s) |", ""]
    for e in r["12_exceptions_requiring_owner_action"]:
        L.append(f"- **{e['severity']}** {e['id']}: {e['message']}")
    L.append("\nPast performance does not predict future results. Deposits are never counted as investment returns.")
    return "\n".join(L)


# ------------------------------------------------------------------ security incidents
def sync_known_exposures(s):
    if not KNOWN_EXPOSURES.exists():
        return 0
    n = 0
    for f in json.loads(KNOWN_EXPOSURES.read_text(encoding="utf-8"))["findings"]:
        with s.tx() as c:
            if not c.execute("SELECT 1 FROM security_incidents WHERE id=?", (f["id"],)).fetchone():
                c.execute("INSERT INTO security_incidents (id, ts, provider, location, finding, status) VALUES (?,?,?,?,?,?)",
                          (f["id"], now_iso(), f["provider"], f["location"], f["finding"], "OPEN"))
                n += 1
    return n


def confirm_rotation(s, incident_id, note, owner="owner"):
    if owner != "owner":
        raise PermissionError("Only the owner confirms credential rotation.")
    if len(note or "") < 10:
        raise ValueError("Describe what was done (e.g. 'Revoked token in Printful dashboard on 2026-11-14; new token in n8n credential store').")
    with s.tx() as c:
        c.execute("UPDATE security_incidents SET status='ROTATED_CONFIRMED', resolved_ts=?, note=? WHERE id=?", (now_iso(), note, incident_id))
        s.log(owner, "CREDENTIAL_ROTATION_CONFIRMED", {"id": incident_id, "note": note})


# ------------------------------------------------------------------ shadow mode
SHADOW_ITEMS = {
    "policy_signed": "A valid Investment Policy is signed",
    "autoinvest_plan_valid": "The Autoinvest plan passes broker rules and policy limits",
    "daily_jobs_ran": "Daily jobs completed on the required number of distinct days",
    "weekly_report_generated": "At least one weekly report generated",
    "reconciliation_passed": "Latest brokerage reconciliation passed",
    "exception_drill": "An IMMEDIATE exception was raised, delivered and resolved",
    "breaker_drill": "A circuit breaker was tripped and reset by the owner",
    "recovery_drill": "An interrupted job was detected and re-run successfully",
    "no_open_security_incidents": "All exposed credentials confirmed rotated",
    "windows_acceptance": "Windows acceptance run recorded (owner PC or CI evidence)",
}


class ShadowMode:
    def __init__(self, store: Store):
        self.s = store

    def mode(self):
        return self.s.setting("operating_mode", "SHADOW")

    def evaluate(self, required_days=7) -> dict:
        s = self.s
        ip = InvestmentPolicy(s).active()
        days = s.conn.execute("SELECT COUNT(DISTINCT period_key) n FROM job_runs WHERE job='security_health' AND status='DONE'").fetchone()["n"]
        recon = s.events(limit=1, kind="BROKER_RECONCILIATION")
        ev = lambda kind: s.events(limit=1, kind=kind)
        resolved_immediate = s.conn.execute("SELECT 1 FROM exceptions WHERE severity='IMMEDIATE' AND status='RESOLVED'").fetchone()
        win = s.setting("windows_acceptance_evidence")
        checks = {
            "policy_signed": (bool(ip), f"version {ip['version']}" if ip else "no signed policy"),
            "autoinvest_plan_valid": (bool(ip) and not validate_ips(ip["policy"]) and bool(ip["policy"]["recurring"]["legs"]),
                                      "valid" if ip else "no policy"),
            "daily_jobs_ran": (days >= required_days, f"{days}/{required_days} days"),
            "weekly_report_generated": (bool(s.conn.execute("SELECT 1 FROM weekly_reports").fetchone()), ""),
            "reconciliation_passed": (bool(recon) and recon[0]["payload"]["ok"], recon[0]["ts"] if recon else "never"),
            "exception_drill": (bool(resolved_immediate), ""),
            "breaker_drill": (bool(ev("BREAKER_RESET")), ""),
            "recovery_drill": (bool(ev("JOB_INTERRUPTED_RECOVERED")) and bool(s.conn.execute(
                "SELECT 1 FROM job_runs WHERE status='DONE' AND attempt>1").fetchone()), ""),
            "no_open_security_incidents": (not s.conn.execute("SELECT 1 FROM security_incidents WHERE status='OPEN'").fetchone(),
                                           f"{s.conn.execute('SELECT COUNT(*) n FROM security_incidents WHERE status=?', ('OPEN',)).fetchone()['n']} open"),
            "windows_acceptance": (bool(win), win or "not recorded"),
        }
        with s.tx() as c:
            for k, (ok, evd) in checks.items():
                c.execute("INSERT OR REPLACE INTO shadow_checks VALUES (?,?,?,?)", (k, "PASSED" if ok else "PENDING", now_iso(), str(evd)))
        return {"mode": self.mode(), "all_passed": all(ok for ok, _ in checks.values()),
                "checks": [{"item": k, "label": SHADOW_ITEMS[k], "passed": ok, "evidence": evd} for k, (ok, evd) in checks.items()]}

    def activate(self, owner="owner", required_days=7):
        if owner != "owner":
            raise PermissionError("Only the owner can leave shadow mode.")
        Control(self.s).guard("live_activation")
        e = self.evaluate(required_days)
        if not e["all_passed"]:
            missing = [c["item"] for c in e["checks"] if not c["passed"]]
            raise PermissionError(f"Shadow-mode acceptance incomplete: {missing}")
        self.s.set_setting("operating_mode", "ACTIVE", actor=owner)
        self.s.log(owner, "MODE_ACTIVE", {"note": "Monitoring of owner-configured Autoinvest is live. GCI still places no orders."})
        return {"mode": "ACTIVE"}

    def record_windows_acceptance(self, evidence: str, owner="owner"):
        self.s.set_setting("windows_acceptance_evidence", evidence, actor=owner)
