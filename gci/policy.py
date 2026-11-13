"""Investment policy: prohibited instruments and prohibited operations.

Changing this policy requires a separately approved owner decision; the defaults
below implement the SSOI's initial policy.
"""

PROHIBITED_OPERATIONS = {
    "place_order": "GCI never places brokerage orders. The owner executes trades directly at the broker.",
    "withdraw": "GCI never withdraws funds.",
    "external_transfer": "GCI never moves money between real accounts.",
    "enable_margin": "Margin is prohibited by policy.",
    "store_bank_password": "Brokerage/bank passwords are never requested or stored.",
    "browser_automation_login": "Automating brokerage logins bypasses brokerage security and is prohibited.",
}

PROHIBITED_FLAGS = {
    "leveraged": "Leveraged products are prohibited by policy.",
    "inverse": "Inverse products are prohibited by policy.",
    "option": "Options are prohibited by policy.",
    "future": "Futures/derivatives are prohibited by policy.",
    "derivative": "Derivatives are prohibited by policy.",
    "crypto": "Cryptocurrency speculation is prohibited by policy.",
    "short": "Short selling is prohibited by policy.",
    "margin": "Margin is prohibited by policy.",
}

# Known leveraged/inverse tickers (non-exhaustive; metadata flags take precedence).
KNOWN_LEVERAGED = {"TQQQ", "SQQQ", "UPRO", "SPXU", "SSO", "SDS", "SOXL", "SOXS", "TNA", "TZA",
                   "QLD", "QID", "UVXY", "SVXY", "TMF", "TMV", "FAS", "FAZ", "LABU", "LABD", "NVDL", "TSLL"}

SANCTIONED_MARKETS = {"RU": "Russia: research only. U.S. sanctions restrict new investment; access not confirmed."}


class PolicyViolation(Exception):
    pass


def refuse(operation: str):
    """Every prohibited operation routes here and raises."""
    reason = PROHIBITED_OPERATIONS.get(operation, f"Operation '{operation}' is not permitted.")
    raise PolicyViolation(reason)


def instrument_violations(instrument: dict) -> list:
    """Return a list of policy reasons that block an instrument (empty = allowed)."""
    reasons = []
    sym = str(instrument.get("symbol", "")).upper()
    if sym in KNOWN_LEVERAGED:
        reasons.append(f"{sym} is a known leveraged/inverse product.")
    for flag, why in PROHIBITED_FLAGS.items():
        if instrument.get(flag):
            reasons.append(why)
    asset = str(instrument.get("asset_type", "")).lower()
    if asset in ("option", "future", "crypto", "swap", "cfd"):
        reasons.append(f"Asset type '{asset}' is prohibited by policy.")
    market = str(instrument.get("market", "")).upper()
    if market in SANCTIONED_MARKETS:
        reasons.append(SANCTIONED_MARKETS[market])
    return reasons
