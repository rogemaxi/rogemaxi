"""Four-part owner approval interface (SSOI Phase 12).

Approval NEVER executes a trade. It records the owner's decision. The owner
executes any trade personally at the broker and imports the confirmation.
"""
import json
import uuid

from .db import Store, now_iso
from .decisions import DecisionMemory

CARD_PARTS = ("action", "reason", "inaction", "rejection_conditions")
EXEC_NOTE = ("Recorded only. GCI has not placed any order. If you choose to act, place the trade yourself in your "
             "J.P. Morgan account, then import the confirmation so the ledger reconciles.")


class ApprovalError(Exception):
    pass


class Approvals:
    def __init__(self, store: Store):
        self.s = store
        self.dm = DecisionMemory(store)

    def create(self, card: dict, decision_id: str = None, actor="agent:head_manager") -> str:
        for p in CARD_PARTS:
            if not card.get(p):
                raise ApprovalError(f"Decision card missing '{p}'.")
        aid = "APR-" + uuid.uuid4().hex[:8].upper()
        with self.s.tx() as c:
            c.execute("INSERT INTO approvals (id, decision_id, created_ts, card, status) VALUES (?,?,?,?,?)",
                      (aid, decision_id, now_iso(), json.dumps(card, default=str), "PENDING"))
            self.s.log(actor, "APPROVAL_REQUESTED", {"id": aid, "decision_id": decision_id, "action": card["action"]})
        return aid

    def decide(self, aid: str, decision: str, owner: str = "owner", note: str = "") -> dict:
        if owner != "owner":
            raise ApprovalError("Only the owner can approve, reject, or defer.")
        decision = decision.upper()
        if decision not in ("APPROVED", "REJECTED", "DEFERRED"):
            raise ApprovalError("Decision must be APPROVED, REJECTED, or DEFERRED.")
        row = self.s.conn.execute("SELECT * FROM approvals WHERE id=?", (aid,)).fetchone()
        if row is None:
            raise ApprovalError("Unknown approval.")
        if row["status"] not in ("PENDING", "DEFERRED"):
            raise ApprovalError(f"Already {row['status']}.")
        with self.s.tx() as c:
            c.execute("UPDATE approvals SET status=?, decided_ts=?, decided_by=?, note=? WHERE id=?",
                      (decision, now_iso(), owner, note, aid))
            if row["decision_id"]:
                self.dm.set_owner_decision(row["decision_id"], decision, note)
            self.s.log(owner, "APPROVAL_" + decision, {"id": aid, "note": note, "trade_executed": False})
        return {"id": aid, "status": decision, "trade_executed": False, "message": EXEC_NOTE}

    def list(self, status=None):
        q = "SELECT * FROM approvals" + (" WHERE status=?" if status else "") + " ORDER BY created_ts DESC"
        return [dict(r) | {"card": json.loads(r["card"])} for r in self.s.conn.execute(q, (status,) if status else ())]
