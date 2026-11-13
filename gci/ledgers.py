"""Three separate, auditable ledgers.

A = Investment Capital, B = Research Operations, C = Protected Reserve.
Every movement between ledgers needs a single-use owner authorization.
Entries are immutable; corrections are new entries.
"""
import json
import uuid

from .db import Store, now_iso
from .money import D, ZERO

# kind -> (ledger, sign). Positive sign increases that ledger's cash/balance.
KINDS = {
    "A": {"CONTRIBUTION": 1, "MATCH_CONTRIBUTION": 1, "BUY": -1, "SELL": 1, "DIVIDEND": 1, "INTEREST": 1,
          "FEE": -1, "TAX_PAYMENT": -1, "DISTRIBUTION": -1, "TRANSFER_TO_B": -1, "TRANSFER_TO_C": -1,
          "TRANSFER_FROM_C": 1, "ADJUSTMENT": 1},
    "B": {"BUDGET_AUTHORIZED": 1, "TRANSFER_FROM_A": 1, "SPEND": -1, "ADJUSTMENT": 1},
    "C": {"RESERVE_ADD": 1, "TRANSFER_FROM_A": 1, "RESERVE_RELEASE": -1, "TRANSFER_TO_A": -1, "ADJUSTMENT": 1},
}
# Flows that change capital without being investment return.
EXTERNAL_FLOW_KINDS = {"CONTRIBUTION", "MATCH_CONTRIBUTION", "DISTRIBUTION", "TRANSFER_TO_B", "TRANSFER_TO_C",
                       "TRANSFER_FROM_C", "TAX_PAYMENT"}
AUTH_REQUIRED = {"DISTRIBUTION", "BUDGET_AUTHORIZED", "RESERVE_RELEASE", "ADJUSTMENT"}


class LedgerError(Exception):
    pass


class Ledgers:
    def __init__(self, store: Store):
        self.s = store

    # ---- authorizations -------------------------------------------------
    def authorize(self, action: str, amount, details: dict, owner: str = "owner") -> str:
        """Record an owner authorization. Only the owner (UI/CLI) calls this."""
        if owner in ("agent", "system") or owner.startswith("agent:"):
            raise LedgerError("Only the owner can create authorizations.")
        auth_id = "AUTH-" + uuid.uuid4().hex[:12].upper()
        with self.s.tx() as c:
            c.execute("INSERT INTO authorizations (id, ts, owner, action, amount, details, status) VALUES (?,?,?,?,?,?,?)",
                      (auth_id, now_iso(), owner, action, str(D(amount)) if amount is not None else None,
                       json.dumps(details), "APPROVED"))
            self.s.log(owner, "AUTHORIZATION_GRANTED", {"id": auth_id, "action": action, "amount": str(amount)})
        return auth_id

    def _consume(self, auth_id: str, action: str, amount) -> None:
        row = self.s.conn.execute("SELECT * FROM authorizations WHERE id=?", (auth_id,)).fetchone()
        if row is None:
            raise LedgerError(f"Authorization {auth_id} does not exist.")
        if row["status"] != "APPROVED":
            raise LedgerError(f"Authorization {auth_id} is {row['status']}; it cannot be reused.")
        if row["action"] != action:
            raise LedgerError(f"Authorization {auth_id} is for {row['action']}, not {action}.")
        if row["amount"] is not None and D(amount) > D(row["amount"]):
            raise LedgerError(f"Amount {amount} exceeds authorized {row['amount']}.")
        self.s.conn.execute("UPDATE authorizations SET status='CONSUMED', consumed_ts=? WHERE id=?", (now_iso(), auth_id))

    def revoke(self, auth_id: str, owner="owner"):
        with self.s.tx():
            self.s.conn.execute("UPDATE authorizations SET status='REVOKED' WHERE id=? AND status='APPROVED'", (auth_id,))
            self.s.log(owner, "AUTHORIZATION_REVOKED", {"id": auth_id})

    # ---- posting ---------------------------------------------------------
    def post(self, ledger: str, kind: str, amount, memo: str = "", authorization_id: str = None,
             external_id: str = None, ref: str = None, transfer_id: str = None, actor: str = "owner",
             allow_negative: bool = False) -> int:
        if ledger not in KINDS or kind not in KINDS[ledger]:
            raise LedgerError(f"Entry kind {kind} is not valid for ledger {ledger}.")
        amt = D(amount)
        if amt <= ZERO and kind != "ADJUSTMENT":
            raise LedgerError("Amounts are positive; the entry kind sets the direction.")
        signed = amt * KINDS[ledger][kind]
        with self.s.tx() as c:
            if kind in AUTH_REQUIRED and transfer_id is None:
                if not authorization_id:
                    raise LedgerError(f"{kind} on ledger {ledger} requires an owner authorization.")
                self._consume(authorization_id, f"{ledger}:{kind}", abs(amt))
            if external_id and c.execute("SELECT 1 FROM ledger_entries WHERE external_id=?", (external_id,)).fetchone():
                raise LedgerError(f"Duplicate transaction {external_id} rejected.")
            if signed < ZERO and not allow_negative and self.balance(ledger) + signed < ZERO:
                raise LedgerError(f"Ledger {ledger} balance would go negative; rejected (no margin/overdraft).")
            cur = c.execute("INSERT INTO ledger_entries (ledger, ts, kind, amount, memo, authorization_id, transfer_id, external_id, ref)"
                            " VALUES (?,?,?,?,?,?,?,?,?)",
                            (ledger, now_iso(), kind, str(signed), memo, authorization_id, transfer_id, external_id, ref))
            self.s.log(actor, "LEDGER_POSTED", {"ledger": ledger, "kind": kind, "amount": str(signed), "memo": memo,
                                                "authorization_id": authorization_id, "transfer_id": transfer_id})
            return cur.lastrowid

    def transfer(self, src: str, dst: str, amount, authorization_id: str, memo="", actor="owner") -> str:
        """Move value between ledgers. Requires an authorization for exactly this route."""
        route = {("A", "B"): ("TRANSFER_TO_B", "TRANSFER_FROM_A"), ("A", "C"): ("TRANSFER_TO_C", "TRANSFER_FROM_A"),
                 ("C", "A"): ("TRANSFER_TO_A", "TRANSFER_FROM_C")}
        if (src, dst) not in route:
            raise LedgerError(f"Transfers {src}->{dst} are not permitted.")
        out_kind, in_kind = route[(src, dst)]
        tid = "TRF-" + uuid.uuid4().hex[:10].upper()
        with self.s.tx():
            self._consume(authorization_id, f"TRANSFER:{src}->{dst}", amount)
            self.post(src, out_kind, amount, memo, authorization_id, transfer_id=tid, actor=actor)
            self.post(dst, in_kind, amount, memo, authorization_id, transfer_id=tid, actor=actor)
        return tid

    # ---- reads -----------------------------------------------------------
    def balance(self, ledger: str):
        rows = self.s.conn.execute("SELECT amount FROM ledger_entries WHERE ledger=?", (ledger,)).fetchall()
        return sum((D(r["amount"]) for r in rows), ZERO)

    def entries(self, ledger: str = None, limit=500):
        q = "SELECT * FROM ledger_entries" + (" WHERE ledger=?" if ledger else "") + " ORDER BY id DESC LIMIT ?"
        return [dict(r) for r in self.s.conn.execute(q, (ledger, limit) if ledger else (limit,))]

    def external_flows(self, start: str = None, end: str = None):
        """Net external capital flows into Ledger A (contributions minus distributions/transfers out)."""
        total = ZERO
        for r in self.s.conn.execute("SELECT * FROM ledger_entries WHERE ledger='A'"):
            if r["kind"] in EXTERNAL_FLOW_KINDS and (start is None or r["ts"] >= start) and (end is None or r["ts"] <= end):
                total += D(r["amount"])
        return total

    def reconcile_internal(self) -> dict:
        """Every transfer must net to zero across ledgers; no transfer may appear twice."""
        problems = []
        for r in self.s.conn.execute("SELECT transfer_id, SUM(CAST(amount AS REAL)) AS net, COUNT(*) AS n "
                                     "FROM ledger_entries WHERE transfer_id IS NOT NULL GROUP BY transfer_id"):
            legs = self.s.conn.execute("SELECT amount FROM ledger_entries WHERE transfer_id=?", (r["transfer_id"],)).fetchall()
            net = sum((D(x["amount"]) for x in legs), ZERO)
            if r["n"] != 2 or net != ZERO:
                problems.append({"transfer_id": r["transfer_id"], "legs": r["n"], "net": str(net)})
        for led in ("A", "B", "C"):
            if self.balance(led) < ZERO:
                problems.append({"ledger": led, "issue": "negative balance", "balance": str(self.balance(led))})
        return {"ok": not problems, "problems": problems,
                "balances": {k: str(self.balance(k)) for k in ("A", "B", "C")}}
