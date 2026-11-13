"""Transparent, reproducible market-regime tagging (SSOI Phase 5).

Every rule is a fixed threshold documented here. Missing inputs produce
"UNKNOWN", never a guess. Version the rules so old tags stay interpretable.
"""
REGIME_RULES_VERSION = "1.0"

RULES = {
    "rate_direction": "3-mo T-bill yield change over ~3 months: > +0.25pp RISING, < -0.25pp FALLING, else FLAT",
    "inflation": "CPI y/y: < 2% LOW, 2-3.5% MODERATE, > 3.5% HIGH",
    "volatility": "VIX level: < 15 LOW, 15-25 NORMAL, > 25 HIGH",
    "dollar": "Broad USD index 6-mo change: > +3% STRENGTHENING, < -3% WEAKENING, else STABLE",
    "equity_trend": "Broad equity index vs 200-day average: > +2% UPTREND, < -2% DOWNTREND, else SIDEWAYS",
    "yield_curve": "10y minus 3-mo yield: < 0 INVERTED, 0-0.5pp FLAT, > 0.5pp NORMAL",
    "cycle": "Unemployment rate change over 12 months: >= +0.5pp CONTRACTION_RISK, else EXPANSION (Sahm-style proxy)",
}


def _band(value, cuts, labels):
    if value is None:
        return "UNKNOWN"
    for cut, label in zip(cuts, labels):
        if value < cut:
            return label
    return labels[-1]


def classify(inputs: dict) -> dict:
    g = inputs.get
    tags = {
        "rate_direction": _band(g("tbill_3m_change_pp"), [-0.25, 0.25000001], ["FALLING", "FLAT", "RISING"]),
        "inflation": _band(g("cpi_yoy_pct"), [2.0, 3.5000001], ["LOW", "MODERATE", "HIGH"]),
        "volatility": _band(g("vix"), [15, 25.0000001], ["LOW", "NORMAL", "HIGH"]),
        "dollar": _band(g("usd_6m_change_pct"), [-3, 3.0000001], ["WEAKENING", "STABLE", "STRENGTHENING"]),
        "equity_trend": _band(g("equity_vs_200d_pct"), [-2, 2.0000001], ["DOWNTREND", "SIDEWAYS", "UPTREND"]),
        "yield_curve": _band(g("curve_10y_3m_pp"), [0, 0.5000001], ["INVERTED", "FLAT", "NORMAL"]),
        "cycle": _band(g("unemployment_12m_change_pp"), [0.5], ["EXPANSION", "CONTRACTION_RISK"]),
        "geopolitical": inputs.get("geopolitical_note") or "NOT_ASSESSED",
    }
    known = [k for k, v in tags.items() if v not in ("UNKNOWN", "NOT_ASSESSED")]
    return {"rules_version": REGIME_RULES_VERSION, "tags": tags, "inputs": inputs,
            "coverage": f"{len(known)}/{len(tags)}", "key": "|".join(tags[k] for k in ("rate_direction", "inflation", "volatility"))}
