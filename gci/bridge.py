"""Capital Authorization Bridge: ByrdWay Powerhouse → owner → brokerage (SSOI §3C, §8).

ByrdWay and GCI stay separate systems. The interface is ByrdWay's own evidence file format
(`activation/seller_proceeds.csv` in the ByrdWay activation package):
    source,transaction_id,earned_at,settled_at,currency,gross,fees,refunds,seller_proceeds,evidence_reference,verification_status
Only rows with verification_status == VERIFIED count. Price-times-sales projections never count.

Business revenue is not personal investment capital. The bridge keeps a separate business record
(proceeds, expenses, tax reserve, business reserve, owner distributions) and computes cash that is
available under the approved rules. It proposes a contribution; the owner authorizes it; the actual
deposit is confirmed only when it appears in an imported brokerage statement. Nothing moves money.
"""
import csv
import io
import json
import uuid
from datetime import date, datetime, timedelta

from .control import Control, BreakerOpen
from .db import Store, now_iso
from .ips import InvestmentPolicy
from .ledgers import Ledgers, LedgerError
from .money import D, ZERO, cents

BYRDWAY_COLUMNS = ["source", "transaction_id", "earned_at", "settled_at", "currency", "gross", "fees", "refunds",
                   "seller_proceeds", "evidence_reference", "verification_status"]
DEFAULT_RULES = {"tax_reserve_rate": "0.30", "business_cash_reserve": "500", "deposit_match_days": 7}
BUSINESS_KINDS = {"SELLER_PROCEEDS": 1, "BUSINESS_EXPENSE": -1, "OWNER_DISTRIBUTION": -1, "CONTRIBUTION_SENT": 0}


def studio_ledger_path():
    """ByrdWay Product Studio's sales ledger (read-only). Studio: app.py ROOT, salesintel._dir(root)/'ledger.json'."""
    import os
    from pathlib import Path
    root = Path(os.environ.get("BYRDWAY_WORKSPACE") or (Path.home() / "Documents" / "ByrdWay_Product_Studio"))
    return root / "revenue" / "ledger.json"


class BridgeError(Exception):
    pass


class Bridge:
    def __init__(self, store: Store):
        self.s = store
        self.ctl = Control(store)

    def rules(self):
        return {**DEFAULT_RULES, **(self.s.setting("bridge_rules", {}) or {})}

    def set_rules(self, owner="owner", **kw):
        if owner != "owner":
            raise BridgeError("Only the owner sets bridge accounting rules.")
        r = {**self.rules(), **{k: str(v) for k, v in kw.items()}}
        self.s.set_setting("bridge_rules", r, actor=owner)
        return r

    # ---- imports ------------------------------------------------------------
    def import_byrdway_proceeds(self, csv_text: str, source_file: str) -> dict:
        reader = csv.DictReader(io.StringIO(csv_text))
        missing = [c for c in BYRDWAY_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise BridgeError(f"Not a ByrdWay seller_proceeds file; missing columns {missing}")
        added, skipped_unverified, duplicates, errors = 0, 0, 0, []
        for i, row in enumerate(reader, start=2):
            if row["verification_status"].strip().upper() != "VERIFIED":
                skipped_unverified += 1
                continue
            try:
                gross, fees, refunds, net = (D(row[k] or 0) for k in ("gross", "fees", "refunds", "seller_proceeds"))
                if cents(gross - fees - refunds) != cents(net):
                    raise BridgeError(f"seller_proceeds {net} ≠ gross {gross} − fees {fees} − refunds {refunds}")
                if not row["evidence_reference"].strip():
                    raise BridgeError("verified row has no evidence_reference")
                ext = f"BW-{row['source'].strip()}-{row['transaction_id'].strip()}"
                if self.s.conn.execute("SELECT 1 FROM bridge_entries WHERE external_id=?", (ext,)).fetchone():
                    duplicates += 1
                    continue
                self._post("SELLER_PROCEEDS", net, f"ByrdWay {row['source']}", ext, row["settled_at"] or row["earned_at"], row)
                added += 1
            except BridgeError as exc:
                errors.append({"line": i, "error": str(exc)})
        if duplicates:
            self.ctl.raise_exception("duplicate_transaction", f"{duplicates} duplicate ByrdWay transaction(s) rejected from {source_file}",
                                     dedupe_key=f"bw-dup:{source_file}:{duplicates}")
        self.s.log("owner", "BYRDWAY_IMPORT", {"file": source_file, "added": added, "unverified_skipped": skipped_unverified,
                                               "duplicates": duplicates, "errors": len(errors)})
        return {"added": added, "unverified_skipped": skipped_unverified, "duplicates_rejected": duplicates, "errors": errors}

    def import_studio_ledger(self, path=None) -> dict:
        """Read ByrdWay Product Studio's sales ledger (never writes to it). Studio rows come from imported TpT sales
        reports; rows Studio marks test=True are excluded, exactly as Studio's own dashboard does."""
        import hashlib
        from pathlib import Path
        p = Path(path) if path else studio_ledger_path()
        if not p.exists():
            return {"status": "NOT_FOUND", "path": str(p), "added": 0}
        rows = json.loads(p.read_text(encoding="utf-8"))
        added = dup = tests = bad = 0
        for r in rows:
            if r.get("test"):
                tests += 1
                continue
            try:
                net = D(str(r["gross"])) - D(str(r.get("fees", 0))) - D(str(r.get("refund", 0)))
                ext = "STUDIO-" + hashlib.sha256(json.dumps(r.get("raw", r), sort_keys=True).encode()).hexdigest()[:20]
                if self.s.conn.execute("SELECT 1 FROM bridge_entries WHERE external_id=?", (ext,)).fetchone():
                    dup += 1
                    continue
                if net > ZERO:
                    self._post("SELLER_PROCEEDS", net, f"ByrdWay Studio sale: {r.get('product', '')[:60]}", ext, r.get("date"),
                               {"source": r.get("source"), "studio_ledger": str(p)})
                    added += 1
                elif net < ZERO:
                    self._post("BUSINESS_EXPENSE", -net, f"ByrdWay Studio net refund: {r.get('product', '')[:60]}", ext, r.get("date"))
                    added += 1
            except Exception:
                bad += 1
        self.s.log("system", "STUDIO_LEDGER_SYNC", {"path": str(p), "added": added, "already_imported": dup, "test_rows_excluded": tests,
                                                    "unreadable": bad})
        return {"status": "OK", "path": str(p), "added": added, "already_imported": dup, "test_rows_excluded": tests, "unreadable": bad}

    def record_business_expense(self, amount, memo, external_id, effective_date):
        return self._post("BUSINESS_EXPENSE", amount, memo, external_id, effective_date)

    def record_owner_distribution(self, amount, treatment: str, external_id, effective_date, owner="owner"):
        """Owner draw/distribution from the LLC. `treatment` must state the accountant-approved treatment."""
        if owner != "owner":
            raise BridgeError("Only the owner records distributions.")
        if not treatment or len(treatment) < 10:
            raise BridgeError("State the distribution's accounting treatment (e.g. 'Member distribution, single-member LLC, per CPA').")
        return self._post("OWNER_DISTRIBUTION", amount, f"Owner distribution — {treatment}", external_id, effective_date,
                          {"treatment": treatment})

    def _post(self, kind, amount, memo, external_id, effective_date, record=None):
        amt = D(amount)
        if amt <= ZERO:
            raise BridgeError("Amounts are positive; the kind sets direction.")
        try:
            with self.s.tx() as c:
                cur = c.execute("INSERT INTO bridge_entries (ts, kind, amount, source, external_id, effective_date, memo, record) "
                                "VALUES (?,?,?,?,?,?,?,?)", (now_iso(), kind, str(amt), "byrdway" if kind == "SELLER_PROCEEDS" else "owner",
                                                             external_id, effective_date, memo, json.dumps(record or {})))
                self.s.log("owner", "BRIDGE_POSTED", {"kind": kind, "amount": str(amt), "external_id": external_id})
                return cur.lastrowid
        except Exception as exc:
            if "UNIQUE" in str(exc):
                self.ctl.raise_exception("duplicate_transaction", f"Duplicate business transaction {external_id} rejected",
                                         dedupe_key=f"bridge-dup:{external_id}")
                raise BridgeError(f"Duplicate transaction {external_id} rejected.") from exc
            raise

    # ---- available cash ----------------------------------------------------
    def totals(self):
        t = {k: ZERO for k in BUSINESS_KINDS}
        for r in self.s.conn.execute("SELECT kind, amount FROM bridge_entries"):
            t[r["kind"]] = t.get(r["kind"], ZERO) + D(r["amount"])
        return t

    def available_cash(self) -> dict:
        r, t = self.rules(), self.totals()
        proceeds, expenses = t["SELLER_PROCEEDS"], t["BUSINESS_EXPENSE"]
        profit = proceeds - expenses
        tax = max(profit, ZERO) * D(r["tax_reserve_rate"])
        sent = sum((D(json.loads(x["record"])["amount"]) for x in
                    self.s.conn.execute("SELECT record FROM bridge_proposals WHERE status IN ('AUTHORIZED','DEPOSIT_CONFIRMED')")), ZERO)
        available = proceeds - expenses - tax - D(r["business_cash_reserve"]) - sent
        verified = proceeds > ZERO
        return {"verified_seller_proceeds": str(cents(proceeds)), "business_expenses": str(cents(expenses)),
                "tax_reserve": str(cents(tax)), "business_cash_reserve": str(cents(D(r["business_cash_reserve"]))),
                "contributions_authorized_or_sent": str(cents(sent)), "owner_distributions_recorded": str(cents(t["OWNER_DISTRIBUTION"])),
                "available_for_investment": str(cents(max(available, ZERO))), "has_verified_revenue": verified,
                "status": "AVAILABLE" if available > 0 else ("NO_VERIFIED_REVENUE" if not verified else "NOTHING_AVAILABLE_AFTER_RESERVES"),
                "rules": r}

    # ---- proposals ----------------------------------------------------------
    def month_authorized(self, month: str):
        return sum((D(json.loads(x["record"])["amount"]) for x in self.s.conn.execute(
            "SELECT record FROM bridge_proposals WHERE status IN ('AUTHORIZED','DEPOSIT_CONFIRMED') AND ts LIKE ?", (month + "%",))), ZERO)

    def propose(self, requested=None, actor="agent:compounding") -> dict:
        self.ctl.guard("contribution_proposals")
        ip = InvestmentPolicy(self.s).active()
        if not ip:
            return {"status": "NO_SIGNED_POLICY", "message": "Sign an Investment Policy before contribution proposals can be made."}
        av = self.available_cash()
        month = date.today().strftime("%Y-%m")
        ceiling = D(ip["policy"]["max_monthly_contribution"])
        room = max(ceiling - self.month_authorized(month), ZERO)
        avail = D(av["available_for_investment"])
        want = D(requested) if requested is not None else D(ip["policy"]["recurring"]["amount_per_period"] or 0)
        amount = min(want, room, avail)
        owner_kind = ip["policy"]["account"]["account_owner"]
        personal = "llc" not in str(owner_kind).lower()
        if amount <= ZERO:
            return {"status": "NO_PROPOSAL", "reason": av["status"] if avail <= 0 else "Monthly ceiling reached",
                    "available": av, "ceiling": str(ceiling), "room_this_month": str(room)}
        rec = {"amount": str(cents(amount)), "requested": str(cents(want)), "ceiling": str(ceiling), "room_this_month": str(cents(room)),
               "available_cash": av, "policy_version": ip["version"], "account_owner": owner_kind,
               "transfer_treatment": ("Business → owner: record an owner distribution (with your CPA-approved treatment) before "
                                      "depositing to your personal brokerage account." if personal else
                                      "Business-owned brokerage account: transfer stays inside Genesis 2 & 7, LLC."),
               "limited_by": [n for n, v in (("request", want), ("ceiling", room), ("available_cash", avail)) if v == amount]}
        pid = "BRG-" + uuid.uuid4().hex[:8].upper()
        with self.s.tx() as c:
            c.execute("INSERT INTO bridge_proposals (id, ts, record, status) VALUES (?,?,?,?)", (pid, now_iso(), json.dumps(rec), "PROPOSED"))
            self.s.log(actor, "BRIDGE_PROPOSED", {"id": pid, **{k: rec[k] for k in ("amount", "ceiling", "limited_by")}})
        return {"id": pid, "status": "PROPOSED", **rec}

    def authorize(self, proposal_id: str, owner="owner", distribution_external_id: str = None) -> dict:
        if owner != "owner":
            raise BridgeError("Only the owner authorizes contributions.")
        row = self.s.conn.execute("SELECT * FROM bridge_proposals WHERE id=?", (proposal_id,)).fetchone()
        if row is None or row["status"] != "PROPOSED":
            raise BridgeError("Proposal not found or already resolved.")
        rec = json.loads(row["record"])
        if "llc" not in str(rec["account_owner"]).lower():
            d = self.s.conn.execute("SELECT * FROM bridge_entries WHERE kind='OWNER_DISTRIBUTION' AND external_id=?",
                                    (distribution_external_id,)).fetchone() if distribution_external_id else None
            if d is None or D(d["amount"]) < D(rec["amount"]):
                raise BridgeError("Personal account: record an owner distribution of at least this amount first and reference it.")
        month = date.today().strftime("%Y-%m")
        ip = InvestmentPolicy(self.s).active()
        if self.month_authorized(month) + D(rec["amount"]) > D(ip["policy"]["max_monthly_contribution"]):
            self.ctl.trip("limit_exceeded", f"Authorizing {proposal_id} would exceed the monthly ceiling")
            raise BridgeError("Would exceed the signed monthly ceiling.")
        auth = Ledgers(self.s).authorize("BRIDGE:CONTRIBUTION", rec["amount"], {"proposal": proposal_id}, owner)
        with self.s.tx() as c:
            c.execute("UPDATE bridge_proposals SET status='AUTHORIZED', authorization_id=? WHERE id=?", (auth, proposal_id))
            self.s.log(owner, "BRIDGE_AUTHORIZED", {"id": proposal_id, "authorization_id": auth, "money_moved_by_gci": False})
        return {"id": proposal_id, "status": "AUTHORIZED", "authorization_id": auth,
                "next_step": f"Transfer ${rec['amount']} to the brokerage account yourself, then import the statement. GCI moves no money."}

    def match_deposits(self, deposits: list) -> dict:
        """deposits: [{ref, amount, date}] from imported broker statements. Confirms authorized proposals; flags the rest."""
        matched, unexpected = [], []
        days = int(self.rules()["deposit_match_days"])
        for dep in deposits:
            if self.s.conn.execute("SELECT 1 FROM bridge_proposals WHERE deposit_ref=?", (dep["ref"],)).fetchone():
                continue  # already matched (idempotent)
            cands = self.s.conn.execute("SELECT * FROM bridge_proposals WHERE status='AUTHORIZED' ORDER BY ts").fetchall()
            hit = None
            for p in cands:
                rec = json.loads(p["record"])
                age = (date.fromisoformat(dep["date"][:10]) - date.fromisoformat(p["ts"][:10])).days
                if abs(D(rec["amount"]) - D(dep["amount"])) <= D("0.01") and -1 <= age <= days:
                    hit = p
                    break
            if hit:
                with self.s.tx() as c:
                    c.execute("UPDATE bridge_proposals SET status='DEPOSIT_CONFIRMED', deposit_ref=? WHERE id=?", (dep["ref"], hit["id"]))
                    self.s.log("agent:auditor", "BRIDGE_DEPOSIT_CONFIRMED", {"id": hit["id"], "deposit_ref": dep["ref"]})
                matched.append({"proposal": hit["id"], "deposit": dep["ref"]})
            else:
                unexpected.append(dep)
        for dep in unexpected:
            self.ctl.raise_exception("unmatched_deposit", f"Deposit {dep['ref']} ${dep['amount']} on {dep['date']} matches no authorized "
                                     "bridge proposal (fine if it was a personal contribution; please confirm).",
                                     dedupe_key=f"unmatched:{dep['ref']}", severity="WEEKLY")
        return {"matched": matched, "unexpected": unexpected}

    def proposals(self):
        return [dict(r) | {"record": json.loads(r["record"])} for r in self.s.conn.execute("SELECT * FROM bridge_proposals ORDER BY ts DESC")]
