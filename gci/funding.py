"""Realized-profit certification, research budget control, and automatic suspension.

Policy defaults are proposals pending owner approval (SSOI Phase 9):
  research_share = 30% of eligible, audited, realized net gains
  budget floor   = $0 additional spending
Unrealized appreciation is never distributable.
"""
import json
import uuid

from .db import Store, now_iso
from .ledgers import Ledgers, LedgerError
from .money import D, ZERO, cents
from .portfolio import Portfolio

DEFAULT_POLICY = {
    "research_share": "0.30",        # proposal, not yet owner-approved
    "research_share_approved": False,
    "tax_rate": "0.24",              # owner must confirm their marginal rate
    "per_job_cost_cap": "1.00",
    "monthly_research_cap": "0.00",  # budget floor: $0 unless owner authorizes
}


class BudgetSuspended(Exception):
    pass


class Funding:
    def __init__(self, store: Store):
        self.s = store
        self.led = Ledgers(store)
        self.pf = Portfolio(store)

    def policy(self) -> dict:
        return {**DEFAULT_POLICY, **(self.s.setting("funding_policy", {}) or {})}

    def set_policy(self, owner="owner", **changes):
        if owner != "owner":
            raise LedgerError("Only the owner can change funding policy.")
        pol = self.policy()
        pol.update({k: str(v) if not isinstance(v, bool) else v for k, v in changes.items()})
        self.s.set_setting("funding_policy", pol, actor=owner)
        return pol

    # ---- certification (performed by the Independent Auditor role) ----------
    def carryforward(self) -> "D":
        rows = self.s.conn.execute("SELECT record FROM gain_certifications WHERE status IN ('CERTIFIED','ALLOCATED') "
                                   "ORDER BY period_end DESC LIMIT 1").fetchall()
        return D(json.loads(rows[0]["record"])["carryforward_after"]) if rows else ZERO

    def certify(self, period_start: str, period_end: str, auditor: str = "agent:auditor") -> dict:
        if not auditor.startswith("agent:auditor") and auditor != "owner":
            raise LedgerError("Gain certification must be performed by the Independent Auditor or the owner.")
        overlap = self.s.conn.execute(
            "SELECT id FROM gain_certifications WHERE status!='REJECTED' AND NOT (period_end < ? OR period_start > ?)",
            (period_start, period_end)).fetchone()
        if overlap:
            raise LedgerError(f"Period overlaps certification {overlap['id']}; gains cannot be counted twice.")
        recon = self.led.reconcile_internal()
        pol = self.policy()
        realized = self.pf.realized_gains(period_start, period_end)
        income = self.pf.income(period_start, period_end)
        fees = self.pf.standalone_fees(period_start, period_end)
        net = realized + income - fees
        cf_before = self.carryforward()  # <= 0
        combined = net + cf_before
        eligible_pre_tax = max(combined, ZERO)
        cf_after = min(combined, ZERO)
        tax = eligible_pre_tax * D(pol["tax_rate"])
        eligible = eligible_pre_tax - tax
        share = D(pol["research_share"])
        record = {
            "period_start": period_start, "period_end": period_end,
            "realized_trading_gain": str(cents(realized)), "income": str(cents(income)), "standalone_fees": str(cents(fees)),
            "net_realized": str(cents(net)), "carryforward_before": str(cents(cf_before)),
            "carryforward_after": str(cents(cf_after)), "tax_rate": pol["tax_rate"], "tax_provision": str(cents(tax)),
            "eligible_net_gain": str(cents(eligible)), "research_share": pol["research_share"],
            "research_share_owner_approved": pol["research_share_approved"],
            "proposed_research_allocation": str(cents(eligible * share)),
            "unrealized_excluded": True, "reconciliation_ok": recon["ok"], "auditor": auditor,
        }
        status = "CERTIFIED" if recon["ok"] else "REJECTED"
        if not recon["ok"]:
            record["rejection_reason"] = "Internal ledger reconciliation failed"
            self.suspend("Reconciliation failed during certification")
        cid = "CERT-" + uuid.uuid4().hex[:10].upper()
        with self.s.tx() as c:
            c.execute("INSERT INTO gain_certifications VALUES (?,?,?,?,?,?)",
                      (cid, now_iso(), period_start, period_end, json.dumps(record), status))
            self.s.log(auditor, "GAINS_" + status, {"id": cid, **record})
        return {"id": cid, "status": status, **record}

    def allocate_to_research(self, cert_id: str, authorization_id: str, amount=None) -> str:
        """Owner-approved transfer of part of a certified gain from Ledger A to Ledger B."""
        row = self.s.conn.execute("SELECT * FROM gain_certifications WHERE id=?", (cert_id,)).fetchone()
        if row is None or row["status"] != "CERTIFIED":
            raise LedgerError("Only a CERTIFIED, not-yet-allocated gain can fund research.")
        rec = json.loads(row["record"])
        cap = D(rec["proposed_research_allocation"])
        amt = D(amount) if amount is not None else cap
        if amt > cap:
            raise LedgerError(f"Allocation {amt} exceeds certified research allocation {cap}.")
        if amt <= ZERO:
            raise LedgerError("Nothing eligible to allocate.")
        with self.s.tx() as c:
            tid = self.led.transfer("A", "B", cents(amt), authorization_id, memo=f"Research funding from {cert_id}")
            c.execute("UPDATE gain_certifications SET status='ALLOCATED' WHERE id=?", (cert_id,))
        return tid

    # ---- research budget controller ----------------------------------------
    def suspended(self):
        return self.s.setting("research_suspended", None)

    def suspend(self, reason: str, actor="system"):
        self.s.set_setting("research_suspended", {"reason": reason, "ts": now_iso()}, actor=actor)

    def resume(self, owner="owner"):
        if owner != "owner":
            raise LedgerError("Only the owner can resume research spending.")
        recon = self.led.reconcile_internal()
        if not recon["ok"]:
            raise LedgerError("Cannot resume: reconciliation still failing.")
        self.s.set_setting("research_suspended", None, actor=owner)

    def available_budget(self):
        return self.led.balance("B")

    def spend(self, amount, job_id: str, memo: str = "", actor="system") -> int:
        amt = D(amount)
        susp = self.suspended()
        if susp:
            self.s.log(actor, "SPEND_REJECTED", {"job": job_id, "amount": str(amt), "reason": "suspended: " + susp["reason"]})
            raise BudgetSuspended(f"Research spending suspended: {susp['reason']}")
        cap = D(self.policy()["per_job_cost_cap"])
        if amt > cap:
            self.s.log(actor, "SPEND_REJECTED", {"job": job_id, "amount": str(amt), "reason": f"exceeds per-job cap {cap}"})
            raise LedgerError(f"Spend {amt} exceeds per-job cap {cap}; owner approval required to raise it.")
        avail = self.available_budget()
        if amt > avail:
            self.s.log(actor, "SPEND_REJECTED", {"job": job_id, "amount": str(amt), "reason": f"exceeds available budget {avail}"})
            if avail <= ZERO:
                self.suspend("Authorized research budget exhausted")
            raise LedgerError(f"Spend {amt} exceeds available research budget {avail}.")
        entry = self.led.post("B", "SPEND", amt, memo or f"Research job {job_id}", ref=job_id, actor=actor)
        if self.available_budget() <= ZERO:
            self.suspend("Authorized research budget exhausted")
        return entry
