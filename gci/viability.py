"""Capital threshold gate (SSOI Phase 7).

Classifies a candidate position as ECONOMICALLY VIABLE / DEFER / REJECT /
INSUFFICIENT INFORMATION. Expected return is deliberately NOT an input:
uncertain returns cannot justify a position or fund research.
"""
from .money import D, ZERO, cents
from .policy import instrument_violations

REQUIRED = ["symbol", "accessible_in_account", "fractional_supported", "min_investment", "price",
            "commission_per_trade", "spread_bps", "expense_ratio", "fx_cost_bps"]

DEFAULT_LIMITS = {"max_round_trip_cost_pct": "1.0", "max_research_cost_pct": "5.0", "max_single_fund_pct": "100"}


def assess(candidate: dict, amount, cash_available, liquidity_reserve=0, research_cost=0, limits=None) -> dict:
    limits = {**DEFAULT_LIMITS, **(limits or {})}
    reasons, checks = [], {}
    missing = [k for k in REQUIRED if candidate.get(k) is None]
    if missing:
        return {"classification": "INSUFFICIENT INFORMATION", "reasons": [f"Missing: {', '.join(missing)}"],
                "checks": checks}
    pv = instrument_violations(candidate)
    if pv:
        return {"classification": "REJECT", "reasons": pv, "checks": checks}
    amount, cash = D(amount), D(cash_available)
    if not candidate["accessible_in_account"]:
        return {"classification": "REJECT", "reasons": ["Not available in the owner's brokerage account."], "checks": checks}
    if amount <= ZERO:
        return {"classification": "REJECT", "reasons": ["Amount must be positive."], "checks": checks}

    price, min_inv = D(candidate["price"]), D(candidate["min_investment"])
    if not candidate["fractional_supported"] and price > amount:
        reasons.append(f"One share costs {cents(price)} > {cents(amount)} and fractional shares are not supported.")
        return {"classification": "DEFER", "reasons": reasons, "checks": checks}
    if amount < min_inv:
        reasons.append(f"Amount {cents(amount)} is below the minimum investment {cents(min_inv)}.")
        return {"classification": "DEFER", "reasons": reasons, "checks": checks}

    commission = D(candidate["commission_per_trade"])
    spread_cost = amount * D(candidate["spread_bps"]) / D(10000)
    fx_cost = amount * D(candidate["fx_cost_bps"]) / D(10000) * 2
    round_trip = commission * 2 + spread_cost + fx_cost
    rt_pct = round_trip / amount * 100
    annual_er = amount * D(candidate["expense_ratio"])
    research_pct = D(research_cost) / amount * 100
    checks.update({"round_trip_cost": str(cents(round_trip)), "round_trip_cost_pct": f"{rt_pct:.3f}",
                   "annual_expense_cost": f"{annual_er:.4f}", "research_cost_pct_of_position": f"{research_pct:.2f}",
                   "cash_after": str(cents(cash - amount - commission))})

    if amount + commission > cash:
        return {"classification": "REJECT", "reasons": ["Insufficient available cash (no margin)."], "checks": checks}
    if cash - amount - commission < D(liquidity_reserve):
        reasons.append("Position would breach the owner's liquidity reserve.")
    if rt_pct > D(limits["max_round_trip_cost_pct"]):
        reasons.append(f"Round-trip trading cost {rt_pct:.2f}% exceeds limit {limits['max_round_trip_cost_pct']}%.")
    if research_pct > D(limits["max_research_cost_pct"]):
        reasons.append(f"Research cost is {research_pct:.1f}% of the position; exceeds limit {limits['max_research_cost_pct']}%.")
    if reasons:
        return {"classification": "DEFER", "reasons": reasons, "checks": checks}
    return {"classification": "ECONOMICALLY VIABLE",
            "reasons": ["Accessible, affordable, low cost relative to size, no policy violations. "
                        "This is a cost/access test, not a return forecast."],
            "checks": checks}
