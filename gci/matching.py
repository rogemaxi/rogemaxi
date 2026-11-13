"""Owner matching-contribution planning (SSOI Phase 10).

A matching contribution is NEW CAPITAL. It is recorded as an external flow and
never counted as investment return. Nothing transfers automatically.
"""
import json
import uuid

from .db import Store, now_iso
from .ledgers import Ledgers, LedgerError
from .money import D, ZERO, cents


class Matching:
    def __init__(self, store: Store):
        self.s = store
        self.led = Ledgers(store)

    def propose(self, cert_id: str, ratio, owner_available_cash, owner_reserve_requirement) -> dict:
        row = self.s.conn.execute("SELECT * FROM gain_certifications WHERE id=?", (cert_id,)).fetchone()
        if row is None or row["status"] not in ("CERTIFIED", "ALLOCATED"):
            raise LedgerError("Matching is based only on a certified, realized gain.")
        rec = json.loads(row["record"])
        eligible = D(rec["eligible_net_gain"])
        ratio, cash, reserve = D(ratio), D(owner_available_cash), D(owner_reserve_requirement)
        if ratio < ZERO:
            raise LedgerError("Ratio cannot be negative.")
        capacity = max(cash - reserve, ZERO)
        target = eligible * ratio
        amount = min(target, capacity)
        prop = {"cert_id": cert_id, "eligible_net_gain": str(cents(eligible)), "ratio": str(ratio),
                "target": str(cents(target)), "owner_capacity_after_reserve": str(cents(capacity)),
                "proposed_amount": str(cents(amount)),
                "limited_by_capacity": amount < target,
                "note": "Matching contributions are new capital, not investment return. No transfer happens until you confirm "
                        "the deposit actually arrived at the broker."}
        pid = "MATCH-" + uuid.uuid4().hex[:10].upper()
        with self.s.tx() as c:
            c.execute("INSERT INTO contribution_proposals VALUES (?,?,?,?)", (pid, now_iso(), json.dumps(prop), "PROPOSED"))
            self.s.log("agent:compounding", "MATCH_PROPOSED", {"id": pid, **prop})
        return {"id": pid, "status": "PROPOSED", **prop}

    def confirm(self, proposal_id: str, actual_amount, owner="owner", external_id=None) -> int:
        if owner != "owner":
            raise LedgerError("Only the owner confirms contributions.")
        row = self.s.conn.execute("SELECT * FROM contribution_proposals WHERE id=?", (proposal_id,)).fetchone()
        if row is None or row["status"] != "PROPOSED":
            raise LedgerError("Proposal not found or already resolved.")
        with self.s.tx() as c:
            eid = self.led.post("A", "MATCH_CONTRIBUTION", cents(actual_amount), f"Owner match for {proposal_id}",
                                external_id=external_id, ref=proposal_id, actor=owner)
            c.execute("UPDATE contribution_proposals SET status='CONFIRMED' WHERE id=?", (proposal_id,))
        return eid

    def decline(self, proposal_id: str, owner="owner"):
        with self.s.tx() as c:
            c.execute("UPDATE contribution_proposals SET status='DECLINED' WHERE id=? AND status='PROPOSED'", (proposal_id,))
            self.s.log(owner, "MATCH_DECLINED", {"id": proposal_id})

    def list(self):
        return [{"id": r["id"], "ts": r["ts"], "status": r["status"], **json.loads(r["record"])}
                for r in self.s.conn.execute("SELECT * FROM contribution_proposals ORDER BY ts DESC")]
