"""Investment Policy Statement and standing authorization (SSOI §7).

The owner signs one versioned policy instead of approving every routine purchase. Routine purchases then
run inside J.P. Morgan's own Autoinvest (recurring investing) feature, which the owner configures in the
Chase app. GCI never creates, edits, pauses or cancels that instruction. It:
  * validates the owner's planned Autoinvest setup against the signed policy and the broker's verified rules;
  * produces exact setup steps for the owner;
  * monitors imported broker activity against the expected schedule (see ops.recurring_status).

Broker facts (J.P. Morgan Self-Directed Investing FAQ, retrieved 2026-11-13):
  recurring investing: stocks, ETFs, mutual funds; cash accounts only (margin not eligible);
  frequencies: weekly, twice per month, monthly, every 3 months, every 6 months, yearly;
  $5 minimum recurring amount per stock/ETF; no fee; funding from internal bank, external bank
  (debited 1 business day before trade) or account cash; edit/pause/cancel up to 1 day (internal/cash)
  or 2 business days (external bank) before the trade date.
"""
import hashlib
import json

from .db import Store, now_iso
from .money import D, ZERO
from .policy import instrument_violations

BROKER_RULES = {
    "source": "https://www.chase.com/personal/investments/faqs/self-directed-investing",
    "retrieved_at": "2026-11-13",
    "frequencies": {"weekly": 52, "twice_monthly": 24, "monthly": 12, "quarterly": 4, "semiannual": 2, "yearly": 1},
    "min_recurring_stock_etf": "5",
    "eligible_account_types": ["self_directed_cash"],
    "funding_sources": ["internal_bank", "external_bank", "account_cash"],
    "edit_deadline_business_days": {"internal_bank": 1, "account_cash": 1, "external_bank": 2},
    "fee": "0",
}
ALLOWED_CLASSES = {"us_equity", "international_equity", "global_equity", "fixed_income", "fixed_income_cash_equivalent"}

TEMPLATE = {
    "account": {"broker": "J.P. Morgan Self-Directed Investing", "account_type": "self_directed_cash",
                "account_owner": None, "account_last4": None},
    "eligible_instruments": ["VT", "VTI", "VXUS", "SGOV", "BND"],
    "initial_funding": "40",
    "recurring": {"amount_per_period": None, "frequency": "monthly", "funding_source": "internal_bank", "legs": []},
    "max_monthly_contribution": None,
    "target_allocation": {},
    "allocation_bands_pp": 10,
    "reinvest_dividends": True,
    "liquidity_requirement": {"emergency_fund_months_outside_gci": 3, "confirmed": False},
    "risk_limits": {"max_loss_tolerance_pct": None, "max_single_fund_pct": 100, "max_single_stock_pct": 5},
    "prohibited": ["margin", "options", "leveraged_or_inverse_etfs", "short_selling", "crypto",
                   "unapproved_foreign_market_orders", "unapproved_concentrated_positions", "unapproved_transfers"],
    "review_schedule": "quarterly",
    "suspension_conditions": ["reconciliation failure", "duplicate or unexpected transaction",
                              "contribution above ceiling", "credentials exposed", "stale data beyond limits",
                              "allocation outside bands for 2 consecutive weekly reports"],
}


class PolicyError(Exception):
    pass


def validate(policy: dict, snapshot: dict = None) -> list:
    """Return a list of problems. Empty list = valid."""
    p, errs = policy, []
    acct = p.get("account", {})
    if acct.get("account_type") not in BROKER_RULES["eligible_account_types"]:
        errs.append("Autoinvest requires a Self-Directed cash account (margin accounts are not eligible).")
    if not acct.get("account_owner"):
        errs.append("State who owns the brokerage account (Genesis 2 & 7, LLC or the owner personally).")
    rec = p.get("recurring", {})
    if rec.get("frequency") not in BROKER_RULES["frequencies"]:
        errs.append(f"Frequency must be one of {list(BROKER_RULES['frequencies'])}.")
    if rec.get("funding_source") not in BROKER_RULES["funding_sources"]:
        errs.append(f"Funding source must be one of {BROKER_RULES['funding_sources']}.")
    cands = {c["symbol"]: c for c in (snapshot or {}).get("candidates", [])}
    total = ZERO
    for leg in rec.get("legs", []):
        sym, amt = leg.get("symbol", "").upper(), D(leg.get("amount", 0))
        total += amt
        if sym not in [s.upper() for s in p.get("eligible_instruments", [])]:
            errs.append(f"{sym} is not in the policy's eligible instruments.")
        if instrument_violations({"symbol": sym, **cands.get(sym, {})}):
            errs.append(f"{sym} violates the prohibited-instrument policy.")
        if amt < D(BROKER_RULES["min_recurring_stock_etf"]):
            errs.append(f"{sym}: J.P. Morgan's minimum recurring amount is $5 (got ${amt}).")
        if cands and cands.get(sym, {}).get("asset_class") not in ALLOWED_CLASSES:
            errs.append(f"{sym}: asset class not allowed by policy.")
    if rec.get("legs"):
        if rec.get("amount_per_period") is None or D(rec["amount_per_period"]) != total:
            errs.append(f"Leg amounts (${total}) must add up to amount_per_period.")
        if p.get("max_monthly_contribution") is None:
            errs.append("Set a maximum monthly contribution (the ceiling).")
        else:
            monthly = total * D(BROKER_RULES["frequencies"].get(rec.get("frequency"), 12)) / D(12)
            if monthly > D(p["max_monthly_contribution"]):
                errs.append(f"Recurring plan ≈${monthly:.2f}/month exceeds the authorized ceiling ${p['max_monthly_contribution']}.")
    tgt = p.get("target_allocation", {})
    if tgt:
        s = sum(D(str(v)) for v in tgt.values())
        if s != D("100"):
            errs.append(f"Target allocation must total 100% (got {s}%).")
        if rec.get("legs") and total > 0:
            for leg in rec["legs"]:
                share = D(leg["amount"]) / total * 100
                t = D(str(tgt.get(leg["symbol"], 0)))
                if abs(share - t) > D(str(p.get("allocation_bands_pp", 10))):
                    errs.append(f"{leg['symbol']} recurring share {share:.0f}% is outside target {t}% ± band.")
    if p.get("risk_limits", {}).get("max_loss_tolerance_pct") is None:
        errs.append("State the maximum loss you could tolerate (risk_limits.max_loss_tolerance_pct).")
    if not p.get("liquidity_requirement", {}).get("confirmed"):
        errs.append("Confirm your emergency fund outside GCI (liquidity_requirement.confirmed).")
    return errs


def policy_hash(policy: dict) -> str:
    return hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest()


class InvestmentPolicy:
    def __init__(self, store: Store):
        self.s = store

    def save_draft(self, policy: dict, actor="owner") -> int:
        with self.s.tx() as c:
            v = (c.execute("SELECT MAX(version) m FROM ips_versions").fetchone()["m"] or 0) + 1
            c.execute("INSERT INTO ips_versions VALUES (?,?,?,?,?,?,?)",
                      (v, now_iso(), json.dumps(policy, sort_keys=True), policy_hash(policy), "DRAFT", None, None))
            self.s.log(actor, "IPS_DRAFT_SAVED", {"version": v})
        return v

    def sign(self, version: int, owner="owner", snapshot=None, acknowledgement: str = "") -> dict:
        if owner != "owner":
            raise PolicyError("Only the owner can sign the investment policy.")
        if "I authorize" not in acknowledgement:
            raise PolicyError("Signing requires the explicit acknowledgement text beginning 'I authorize'.")
        row = self.s.conn.execute("SELECT * FROM ips_versions WHERE version=?", (version,)).fetchone()
        if row is None or row["status"] != "DRAFT":
            raise PolicyError("Only a DRAFT version can be signed.")
        pol = json.loads(row["policy"])
        errs = validate(pol, snapshot)
        if errs:
            raise PolicyError("Policy is not valid: " + " | ".join(errs))
        with self.s.tx() as c:
            c.execute("UPDATE ips_versions SET status='SUPERSEDED' WHERE status='SIGNED'")
            c.execute("UPDATE ips_versions SET status='SIGNED', signed_ts=?, signed_by=? WHERE version=?", (now_iso(), owner, version))
            self.s.log(owner, "IPS_SIGNED", {"version": version, "hash": row["policy_hash"], "acknowledgement": acknowledgement})
        return {"version": version, "hash": row["policy_hash"], "status": "SIGNED"}

    def active(self):
        r = self.s.conn.execute("SELECT * FROM ips_versions WHERE status='SIGNED'").fetchone()
        if not r:
            return None
        pol = json.loads(r["policy"])
        if policy_hash(pol) != r["policy_hash"]:
            raise PolicyError("Signed policy hash mismatch: the stored policy was altered.")
        return {"version": r["version"], "signed_ts": r["signed_ts"], "hash": r["policy_hash"], "policy": pol}

    def versions(self):
        return [dict(r) | {"policy": json.loads(r["policy"])} for r in self.s.conn.execute("SELECT * FROM ips_versions ORDER BY version DESC")]

    def ceiling(self):
        a = self.active()
        return D(a["policy"]["max_monthly_contribution"]) if a else ZERO

    def raise_ceiling(self, new_ceiling, owner="owner", acknowledgement=""):
        """A higher ceiling is a new signed version; never an in-place edit."""
        a = self.active()
        if not a:
            raise PolicyError("No signed policy.")
        pol = dict(a["policy"], max_monthly_contribution=str(D(new_ceiling)))
        v = self.save_draft(pol, owner)
        return self.sign(v, owner, acknowledgement=acknowledgement)


def autoinvest_setup_steps(policy: dict) -> list:
    rec = policy["recurring"]
    dl = BROKER_RULES["edit_deadline_business_days"][rec["funding_source"]]
    steps = ["Open the Chase app → Invest → your Self-Directed cash account → Recurring investments (Autoinvest)."]
    for leg in rec["legs"]:
        steps.append(f"Create a recurring investment: {leg['symbol']}, ${D(leg['amount']):.2f}, {rec['frequency'].replace('_', ' ')}, "
                     f"funded from {rec['funding_source'].replace('_', ' ')}.")
    steps += [f"Dividend reinvestment: {'turn ON' if policy.get('reinvest_dividends') else 'leave OFF'} for these holdings.",
              f"To pause or change a plan, do it in the Chase app at least {dl} business day(s) before the trade date.",
              "Do not enter your Chase password anywhere in GCI. GCI only reads the statements you export."]
    return steps


def expected_schedule(policy: dict, start: str, end: str) -> list:
    """Expected Autoinvest trade dates in [start, end], anchored on recurring.start_date (day capped at 28).
    Approximate: the broker may shift dates for weekends/holidays, so monitoring allows a tolerance window."""
    from datetime import date, timedelta
    rec = policy["recurring"]
    s, e = date.fromisoformat(start[:10]), date.fromisoformat(end[:10])
    anchor = date.fromisoformat(rec.get("start_date") or start[:10])
    anchor = anchor.replace(day=min(anchor.day, 28))

    def add_months(d, n):
        y, m = divmod(d.month - 1 + n, 12)
        return d.replace(year=d.year + y, month=m + 1)
    out, i = [], 0
    while True:
        f = rec["frequency"]
        if f == "weekly":
            d = anchor + timedelta(days=7 * i)
        elif f == "twice_monthly":
            base = add_months(anchor.replace(day=1), i // 2)
            d = base.replace(day=1 if i % 2 == 0 else 15)
        else:
            d = add_months(anchor, i * {"monthly": 1, "quarterly": 3, "semiannual": 6, "yearly": 12}[f])
        if d > e:
            break
        if d >= s:
            out.append({"date": d.isoformat(), "legs": rec["legs"]})
        i += 1
    return out
