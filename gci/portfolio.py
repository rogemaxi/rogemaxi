"""Portfolio calculation engine: FIFO lots, realized vs unrealized gains,
income, and returns that exclude deposits (Modified Dietz).

GCI only *records* trades the owner already executed at the broker. There is
no order-placement path in this module or anywhere else.
"""
from .db import Store, now_iso
from .ledgers import Ledgers, LedgerError
from .money import D, ZERO, cents
from .policy import instrument_violations, PolicyViolation


class Portfolio:
    def __init__(self, store: Store):
        self.s = store
        self.led = Ledgers(store)

    def record_buy(self, symbol: str, qty, price, fee=0, ts: str = None, external_id: str = None,
                   instrument: dict = None, actor="owner") -> int:
        symbol = symbol.upper()
        violations = instrument_violations(instrument or {"symbol": symbol})
        if violations:
            raise PolicyViolation("; ".join(violations))
        qty, price, fee = D(qty), D(price), D(fee)
        if qty <= ZERO or price <= ZERO or fee < ZERO:
            raise LedgerError("Quantity and price must be positive; fee cannot be negative.")
        cost = qty * price + fee
        with self.s.tx() as c:
            self.led.post("A", "BUY", cents(cost), f"Buy {qty} {symbol} @ {price}", external_id=external_id,
                          ref=symbol, actor=actor)
            cur = c.execute("INSERT INTO lots (symbol, acquired_ts, qty, remaining_qty, cost_total, ref) VALUES (?,?,?,?,?,?)",
                            (symbol, ts or now_iso(), str(qty), str(qty), str(cost), external_id))
            return cur.lastrowid

    def record_sell(self, symbol: str, qty, price, fee=0, ts: str = None, external_id: str = None, actor="owner") -> dict:
        symbol = symbol.upper()
        qty, price, fee = D(qty), D(price), D(fee)
        if qty <= ZERO or price <= ZERO or fee < ZERO:
            raise LedgerError("Quantity and price must be positive; fee cannot be negative.")
        held = self.position(symbol)["qty"]
        if qty > held:
            raise PolicyViolation(f"Selling {qty} {symbol} exceeds holdings of {held}: short selling is prohibited.")
        ts = ts or now_iso()
        proceeds_total = qty * price
        remaining, realized_total, basis_total = qty, ZERO, ZERO
        with self.s.tx() as c:
            self.led.post("A", "SELL", cents(proceeds_total - fee), f"Sell {qty} {symbol} @ {price}",
                          external_id=external_id, ref=symbol, actor=actor)
            for lot in c.execute("SELECT * FROM lots WHERE symbol=? AND CAST(remaining_qty AS REAL) > 0 "
                                 "ORDER BY acquired_ts, id", (symbol,)).fetchall():
                if remaining <= ZERO:
                    break
                lot_rem = D(lot["remaining_qty"])
                take = min(lot_rem, remaining)
                basis = D(lot["cost_total"]) * take / D(lot["qty"])
                share = take / qty
                lot_fee = fee * share
                lot_proceeds = proceeds_total * share
                gain = lot_proceeds - lot_fee - basis
                c.execute("UPDATE lots SET remaining_qty=? WHERE id=?", (str(lot_rem - take), lot["id"]))
                c.execute("INSERT INTO realized (ts, symbol, qty, proceeds, cost_basis, fees, gain, lot_id, ref) "
                          "VALUES (?,?,?,?,?,?,?,?,?)",
                          (ts, symbol, str(take), str(lot_proceeds), str(basis), str(lot_fee), str(gain), lot["id"], external_id))
                remaining -= take
                realized_total += gain
                basis_total += basis
            self.s.log(actor, "REALIZED", {"symbol": symbol, "qty": str(qty), "gain": str(cents(realized_total))})
        return {"symbol": symbol, "qty": qty, "proceeds": proceeds_total, "fees": fee, "cost_basis": basis_total,
                "realized_gain": realized_total}

    def record_income(self, kind: str, amount, symbol: str = "", external_id=None, actor="owner"):
        if kind not in ("DIVIDEND", "INTEREST"):
            raise LedgerError("Income kind must be DIVIDEND or INTEREST.")
        return self.led.post("A", kind, amount, f"{kind.title()} {symbol}".strip(), external_id=external_id,
                             ref=symbol, actor=actor)

    # ---- marks -------------------------------------------------------------
    def set_price(self, symbol, price, as_of, source, retrieved_at=None, currency="USD"):
        with self.s.tx() as c:
            c.execute("INSERT OR REPLACE INTO prices VALUES (?,?,?,?,?,?)",
                      (symbol.upper(), as_of, str(D(price)), currency, source, retrieved_at or now_iso()))

    def latest_price(self, symbol):
        r = self.s.conn.execute("SELECT * FROM prices WHERE symbol=? ORDER BY as_of DESC LIMIT 1", (symbol.upper(),)).fetchone()
        return dict(r) if r else None

    # ---- reads -------------------------------------------------------------
    def position(self, symbol: str) -> dict:
        rows = self.s.conn.execute("SELECT * FROM lots WHERE symbol=?", (symbol.upper(),)).fetchall()
        qty = sum((D(r["remaining_qty"]) for r in rows), ZERO)
        basis = sum((D(r["cost_total"]) * D(r["remaining_qty"]) / D(r["qty"]) for r in rows), ZERO)
        return {"symbol": symbol.upper(), "qty": qty, "cost_basis": basis}

    def holdings(self) -> list:
        syms = [r["symbol"] for r in self.s.conn.execute("SELECT DISTINCT symbol FROM lots ORDER BY symbol")]
        out = []
        for sym in syms:
            p = self.position(sym)
            if p["qty"] == ZERO:
                continue
            px = self.latest_price(sym)
            mv = p["qty"] * D(px["price"]) if px else None
            out.append({"symbol": sym, "qty": str(p["qty"]), "cost_basis": str(cents(p["cost_basis"])),
                        "price": px["price"] if px else None, "price_as_of": px["as_of"] if px else None,
                        "price_source": px["source"] if px else None,
                        "market_value": str(cents(mv)) if mv is not None else None,
                        "unrealized_gain": str(cents(mv - p["cost_basis"])) if mv is not None else None})
        return out

    def realized_gains(self, start: str = None, end: str = None):
        total = ZERO
        for r in self.s.conn.execute("SELECT * FROM realized"):
            if (start is None or r["ts"] >= start) and (end is None or r["ts"] <= end):
                total += D(r["gain"])
        return total

    def income(self, start=None, end=None):
        total = ZERO
        for r in self.s.conn.execute("SELECT * FROM ledger_entries WHERE ledger='A' AND kind IN ('DIVIDEND','INTEREST')"):
            if (start is None or r["ts"] >= start) and (end is None or r["ts"] <= end):
                total += D(r["amount"])
        return total

    def standalone_fees(self, start=None, end=None):
        total = ZERO
        for r in self.s.conn.execute("SELECT * FROM ledger_entries WHERE ledger='A' AND kind='FEE'"):
            if (start is None or r["ts"] >= start) and (end is None or r["ts"] <= end):
                total += -D(r["amount"])
        return total

    def summary(self) -> dict:
        h = self.holdings()
        cash = self.led.balance("A")
        priced = all(x["market_value"] is not None for x in h)
        mv = sum((D(x["market_value"]) for x in h if x["market_value"] is not None), ZERO)
        unreal = sum((D(x["unrealized_gain"]) for x in h if x["unrealized_gain"] is not None), ZERO)
        total = cash + mv
        flows = self.led.external_flows()
        return {"dataset": self.s.dataset, "cash": str(cents(cash)), "market_value": str(cents(mv)),
                "total_value": str(cents(total)), "all_positions_priced": priced,
                "net_contributions": str(cents(flows)),
                "investment_gain_total": str(cents(total - flows)),
                "realized_gain": str(cents(self.realized_gains())), "unrealized_gain": str(cents(unreal)),
                "income": str(cents(self.income())), "holdings": h}


def modified_dietz(start_value, end_value, flows: list, period_days: int):
    """Return excluding deposits. flows = [(day_offset, amount)], positive = deposit."""
    start_value, end_value = D(start_value), D(end_value)
    net = sum((D(a) for _, a in flows), ZERO)
    weighted = sum((D(a) * (D(period_days) - D(day)) / D(period_days) for day, a in flows), ZERO)
    denom = start_value + weighted
    if denom == ZERO:
        return None
    return (end_value - start_value - net) / denom
