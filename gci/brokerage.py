"""Brokerage import and reconciliation (SSOI Phase 11).

There is no verified, supported read-only API that GCI can use for a retail
J.P. Morgan Self-Directed Investing account, so GCI imports the owner's own CSV
exports (activity and positions). It never logs in, never stores passwords,
never automates a browser, never places orders.

Activity CSV columns (case-insensitive; owner maps others in Settings):
  date, type, symbol, quantity, price, amount, fees, description
Supported types: BUY, SELL, DIVIDEND, INTEREST, DEPOSIT, WITHDRAWAL, FEE
"""
import csv
import hashlib
import io
import json

from .db import Store, now_iso
from .ledgers import Ledgers, LedgerError
from .money import D, ZERO, cents
from .portfolio import Portfolio

CONNECTION_STATUS = {
    "jpmorgan_api": "NOT CONNECTED - no supported read-only retail API verified. Import CSV statements instead.",
    "order_placement": "DISABLED BY DESIGN",
}

ALIASES = {"trade date": "date", "transaction date": "date", "action": "type", "transaction type": "type",
           "ticker": "symbol", "qty": "quantity", "shares": "quantity", "net amount": "amount", "commission": "fees"}


def _norm(row):
    out = {}
    for k, v in row.items():
        if k is None:
            continue
        key = ALIASES.get(k.strip().lower(), k.strip().lower())
        out[key] = (v or "").strip()
    return out


class BrokerageImport:
    def __init__(self, store: Store):
        self.s = store
        self.pf = Portfolio(store)
        self.led = Ledgers(store)

    def import_activity(self, csv_text: str, source: str, dataset_label: str) -> dict:
        if dataset_label != self.s.dataset:
            raise LedgerError(f"File labelled {dataset_label} cannot be imported into a {self.s.dataset} database.")
        added, dupes, errors = 0, 0, []
        for i, raw in enumerate(csv.DictReader(io.StringIO(csv_text)), start=2):
            row = _norm(raw)
            h = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
            if self.s.conn.execute("SELECT 1 FROM imports WHERE row_hash=?", (h,)).fetchone():
                dupes += 1
                continue
            try:
                with self.s.tx() as c:
                    self._apply(row, ext=f"IMP-{h[:16]}")
                    c.execute("INSERT INTO imports VALUES (?,?,?,?)", (h, now_iso(), source, json.dumps(row)))
                added += 1
            except Exception as exc:  # report each bad row; never half-apply
                errors.append({"line": i, "error": str(exc), "row": row})
        self.s.log("owner", "BROKERAGE_IMPORT", {"source": source, "added": added, "duplicates": dupes, "errors": len(errors)})
        return {"added": added, "duplicates_skipped": dupes, "errors": errors}

    def _apply(self, row, ext):
        t = row.get("type", "").upper()
        ts = row.get("date") or now_iso()
        fee = D(row.get("fees") or 0)
        if t in ("BUY", "BOUGHT"):
            self.pf.record_buy(row["symbol"], row["quantity"], row["price"], fee, ts=ts, external_id=ext)
        elif t in ("SELL", "SOLD"):
            self.pf.record_sell(row["symbol"], abs(D(row["quantity"])), row["price"], fee, ts=ts, external_id=ext)
        elif t in ("DIVIDEND", "INTEREST"):
            self.pf.record_income(t, abs(D(row["amount"])), row.get("symbol", ""), external_id=ext)
        elif t in ("DEPOSIT", "CONTRIBUTION"):
            self.led.post("A", "CONTRIBUTION", abs(D(row["amount"])), "Deposit (imported)", external_id=ext)
        elif t == "FEE":
            self.led.post("A", "FEE", abs(D(row["amount"])), row.get("description", "Fee"), external_id=ext)
        elif t == "WITHDRAWAL":
            raise LedgerError("Withdrawals must be recorded as owner-authorized DISTRIBUTION entries.")
        else:
            raise LedgerError(f"Unsupported transaction type '{t}'")

    def reconcile_positions(self, csv_text: str, broker_cash=None, tolerance="0.00001") -> dict:
        """Compare the broker's positions export with GCI's computed holdings."""
        tol = D(tolerance)
        broker = {}
        for raw in csv.DictReader(io.StringIO(csv_text)):
            row = _norm(raw)
            broker[row["symbol"].upper()] = D(row["quantity"])
        ours = {h["symbol"]: D(h["qty"]) for h in self.pf.holdings()}
        exceptions = []
        for sym in sorted(set(broker) | set(ours)):
            b, o = broker.get(sym, ZERO), ours.get(sym, ZERO)
            if abs(b - o) > tol:
                exceptions.append({"symbol": sym, "broker_qty": str(b), "gci_qty": str(o), "difference": str(b - o)})
        if broker_cash is not None:
            ours_cash = self.led.balance("A")
            if abs(D(broker_cash) - ours_cash) > D("0.01"):
                exceptions.append({"symbol": "CASH", "broker": str(cents(D(broker_cash))), "gci": str(cents(ours_cash))})
        ok = not exceptions
        self.s.log("agent:auditor", "BROKER_RECONCILIATION", {"ok": ok, "exceptions": exceptions})
        if not ok:
            from .funding import Funding
            Funding(self.s).suspend("Brokerage reconciliation failed")
        return {"ok": ok, "exceptions": exceptions, "synced_at": now_iso()}
