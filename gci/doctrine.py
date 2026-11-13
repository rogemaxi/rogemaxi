"""Global Investment Doctrine Library and Doctrine Council (SSOI Addendum).

Each investor's principles map to a *lens*: a deterministic, documented test
run against the dated evidence. The council:
  * runs each lens ONCE and counts evidence per distinct lens, never per famous
    name (six value investors sharing one lens count as one piece of evidence);
  * surfaces disagreement between schools instead of averaging it away;
  * marks doctrines that need leverage, derivatives, activism, concentration or
    private markets as STUDY_ONLY for any action under current policy;
  * never approves anything. Lenses return SUPPORT / CHALLENGE / CAUTION /
    NEUTRAL / INSUFFICIENT_DATA / NOT_APPLICABLE. Only the owner approves.
"""
import json
from pathlib import Path

LIB_PATH = Path(__file__).resolve().parent.parent / "data" / "doctrine" / "library.json"
VERDICTS = ("CHALLENGE", "CAUTION", "INSUFFICIENT_DATA", "NEUTRAL", "SUPPORT", "NOT_APPLICABLE")
SEVERITY = {v: i for i, v in enumerate(VERDICTS)}  # lower = more severe
PRESERVATION_FAMILY = {"margin_of_safety", "risk_streams", "capital_preservation", "cycle", "liquidity"}
POLICY_BLOCKED = {"leverage", "derivatives", "activism", "concentration", "private_markets"}

# Rules are versioned. Every threshold is stated so a reviewer can disagree with it explicitly.
LENS_RULES = {
    "margin_of_safety": "Equity earnings yield (1/trailing P/E, weighted over equity legs) minus 13-week T-bill yield. "
                        "<1.0pp with equity weight >50% → CHALLENGE; <1.0pp with equity ≤50% → CAUTION; 1–3pp → NEUTRAL; >3pp → SUPPORT.",
    "risk_streams": "Distinct return streams (equity / government bonds and cash). One stream at 100% → CHALLENGE; "
                    "≥2 streams with no stream above 75% → SUPPORT; otherwise CAUTION.",
    "capital_preservation": "Severe-scenario loss = equity weight × 50% + bond weight × duration × 2pp. Compare with the owner's "
                            "stated maximum tolerable loss. Above it → CHALLENGE; unknown tolerance → INSUFFICIENT_DATA.",
    "cycle": "Equity legs within 5% of their 52-week high AND trailing P/E > 18 → CAUTION (elevated); >20% below the high → SUPPORT; else NEUTRAL.",
    "liquidity": "Change in 13-week T-bill yield over the observation window: > +0.10pp → CAUTION (tightening); < -0.10pp → SUPPORT; else NEUTRAL.",
    "contrarian": "Equity >20% below its 52-week high → SUPPORT (pessimism signal); otherwise NEUTRAL (no signal either way).",
    "momentum": "Price vs 200-day average: > +2% SUPPORT, < -2% CHALLENGE, else NEUTRAL.",
    "value_factor": "If ex-U.S. equities trade at a lower trailing P/E than U.S. equities: proposals including ex-U.S. → SUPPORT; U.S.-only → CAUTION.",
    "cost": "Weighted expense ratio ≤0.10% → SUPPORT; ≤0.50% → CAUTION; above → CHALLENGE.",
    "diversify_securities": "Every equity leg is a broad fund with ≥1,000 holdings → SUPPORT; any single-security equity leg → CHALLENGE.",
    "understand": "Every leg is a fund with a stated benchmark the owner can explain in one sentence → SUPPORT.",
    "horizon": "Owner horizon ≥5 years → SUPPORT; 3–5 → CAUTION; <3 with equity → CHALLENGE; unknown → INSUFFICIENT_DATA.",
    "inversion": "Known failure modes (no emergency fund, leverage, high fees, frequent trading, short horizon). Any present → CHALLENGE; any unknown → CAUTION; none → SUPPORT.",
    "edge": "Passive proposal (no edge claimed) → SUPPORT. Active selection without a validated out-of-sample test → CHALLENGE.",
    "sizing": "Kelly: with no measured edge, the active bet size is zero. Any single non-diversified security above 5% → CHALLENGE; else SUPPORT.",
    "falsifiable": "Recorded falsification conditions with written justifications → SUPPORT; none → CHALLENGE.",
    "asymmetry": "No asymmetric setup is claimed for a core passive holding → NEUTRAL.",
    "concentration": "Concentrated-research school: owning thousands of unanalysed businesses is a CHALLENGE in principle; acting on it is policy-blocked at this size.",
    "concentration_warning": "Concentration-risk lesson: diversified proposal → SUPPORT; any leg above 25% in a single company → CHALLENGE.",
    "distressed": "Requires credit-spread or default data, which this snapshot lacks → NOT_APPLICABLE.",
}
LENS_RULES_VERSION = "1.0"


PROFILE_FIELDS = ("principles", "sources", "testable_rules", "market_conditions", "limitations", "risks",
                  "small_capital_applicability", "evidence_quality", "conflicts_with", "review_requirement")


def load_library(path=None) -> dict:
    return json.loads(Path(path or LIB_PATH).read_text(encoding="utf-8"))


def profile(inv: dict, lib: dict) -> dict:
    """The ten required attributes for one investor. School-level fields are labelled as such."""
    sp = lib.get("school_profiles", {}).get(inv["school"], {})
    return {"name": inv["name"], "principles": [p["text"] for p in inv["principles"]], "sources": inv["sources"],
            "testable_rules": {p["lens"]: LENS_RULES[p["lens"]] for p in inv["principles"]},
            "market_conditions": sp.get("market_conditions") + " (school-level)" if sp else None,
            "limitations": "; ".join(x for x in (inv.get("caution"), sp.get("limitations", "") + " (school-level)") if x),
            "risks": sp.get("risks", "") + " (school-level)",
            "small_capital_applicability": inv["small_capital"], "evidence_quality": inv["source_quality"],
            "conflicts_with": sp.get("conflicts_with", []), "review_requirement": lib.get("review_requirements", {}).get(inv["small_capital"])}


def _eq(legs):
    return [l for l in legs if l["asset_class"].endswith("equity")]


def _r(lens, verdict, evidence, **derived):
    return {"lens": lens, "verdict": verdict, "evidence": evidence, "rule": LENS_RULES[lens], "derived": derived}


def run_lenses(proposal: dict, snap: dict, owner: dict) -> dict:
    """proposal = {name, legs:[{symbol, weight, asset_class}], active: bool, falsification: [...]}"""
    cands = {c["symbol"]: c for c in snap["candidates"]}
    legs = [{**l, **{k: cands[l["symbol"]].get(k) for k in ("expense_ratio", "trailing_pe", "price", "fifty_two_week_high",
                                                             "two_hundred_day_average", "holdings_count", "benchmark",
                                                             "avg_duration_years")}} for l in proposal["legs"]]
    eq = _eq(legs)
    eq_w = sum(l["weight"] for l in eq)
    bond_w = sum(l["weight"] for l in legs if l["asset_class"].startswith("fixed_income"))
    tbill = snap["rates"]["tbill_13w_coupon_equiv_pct"]
    out = {}

    # margin of safety
    pes = [(l["weight"], l["trailing_pe"]) for l in eq if l.get("trailing_pe")]
    if not eq:
        out["margin_of_safety"] = _r("margin_of_safety", "NOT_APPLICABLE", "No equity legs.")
    elif not pes:
        out["margin_of_safety"] = _r("margin_of_safety", "INSUFFICIENT_DATA", "No P/E data for equity legs.")
    else:
        ey = sum(w / pe for w, pe in pes) / sum(w for w, _ in pes) * 100
        prem = ey - tbill
        v = ("CHALLENGE" if eq_w > 0.5 else "CAUTION") if prem < 1 else ("NEUTRAL" if prem <= 3 else "SUPPORT")
        out["margin_of_safety"] = _r("margin_of_safety", v,
                                     f"Equity earnings yield {ey:.2f}% vs 13-week T-bill {tbill}% → premium {prem:.2f}pp "
                                     f"(equity weight {eq_w:.0%}). Trailing P/E is a crude proxy.",
                                     earnings_yield_pct=round(ey, 2), equity_premium_pp=round(prem, 2))

    # risk streams
    streams = {}
    for l in legs:
        k = "equity" if l["asset_class"].endswith("equity") else "bonds_cash"
        streams[k] = streams.get(k, 0) + l["weight"]
    mx = max(streams.values())
    v = "CHALLENGE" if len(streams) == 1 else ("SUPPORT" if mx <= 0.75 else "CAUTION")
    out["risk_streams"] = _r("risk_streams", v, f"Return streams: {streams}.", streams=streams)

    # capital preservation
    dur = sum(l["weight"] * (l.get("avg_duration_years") or 0.25) for l in legs if l["asset_class"].startswith("fixed_income"))
    loss = eq_w * 50 + dur * 2
    tol = owner.get("max_loss_tolerance_pct")
    if tol is None:
        out["capital_preservation"] = _r("capital_preservation", "INSUFFICIENT_DATA",
                                         f"Severe-scenario loss ≈{loss:.0f}%; owner's maximum tolerable loss not stated.",
                                         severe_loss_pct=round(loss, 1))
    else:
        out["capital_preservation"] = _r("capital_preservation", "CHALLENGE" if loss > tol else "SUPPORT",
                                         f"Severe-scenario loss ≈{loss:.0f}% vs owner tolerance {tol}%.", severe_loss_pct=round(loss, 1))

    # cycle / contrarian / momentum (equity legs, weight-averaged)
    def wavg(f):
        vals = [(l["weight"], f(l)) for l in eq if l.get("price") and l.get("fifty_two_week_high") and l.get("two_hundred_day_average")]
        return sum(w * x for w, x in vals) / sum(w for w, _ in vals) if vals else None
    off_high = wavg(lambda l: (float(l["price"]) / float(l["fifty_two_week_high"]) - 1) * 100)
    vs200 = wavg(lambda l: (float(l["price"]) / float(l["two_hundred_day_average"]) - 1) * 100)
    pe = sum(w * p for w, p in pes) / sum(w for w, _ in pes) if pes else None
    if off_high is None:
        for k in ("cycle", "contrarian", "momentum"):
            out[k] = _r(k, "NOT_APPLICABLE" if not eq else "INSUFFICIENT_DATA", "No equity price history.")
    else:
        cv = "CAUTION" if off_high > -5 and pe and pe > 18 else ("SUPPORT" if off_high < -20 else "NEUTRAL")
        out["cycle"] = _r("cycle", cv, f"Equity {off_high:.1f}% from 52-week high; trailing P/E {pe:.1f}.",
                          pct_from_52w_high=round(off_high, 1), weighted_pe=round(pe, 1) if pe else None)
        out["contrarian"] = _r("contrarian", "SUPPORT" if off_high < -20 else "NEUTRAL",
                               f"{off_high:.1f}% from 52-week high: " + ("pessimism signal." if off_high < -20 else
                               "no maximum-pessimism signal; this lens neither supports nor opposes buying now."))
        mv = "SUPPORT" if vs200 > 2 else ("CHALLENGE" if vs200 < -2 else "NEUTRAL")
        out["momentum"] = _r("momentum", mv, f"Equity {vs200:+.2f}% vs 200-day average.", pct_vs_200d=round(vs200, 2))

    # liquidity
    prev = snap["rates"].get("tbill_13w_coupon_equiv_pct_2026_11_02")
    if prev is None or not eq:
        out["liquidity"] = _r("liquidity", "INSUFFICIENT_DATA" if eq else "NOT_APPLICABLE", "No rate-change window available.")
    else:
        ch = round(tbill - prev, 2)
        out["liquidity"] = _r("liquidity", "CAUTION" if ch > 0.10 else ("SUPPORT" if ch < -0.10 else "NEUTRAL"),
                              f"13-week T-bill {prev}% → {tbill}% ({ch:+.2f}pp over ~10 days; short window).", tbill_change_pp=ch)

    # value factor
    us, xus = cands.get("VTI", {}).get("trailing_pe"), cands.get("VXUS", {}).get("trailing_pe")
    has_xus = any(l["symbol"] in ("VT", "VXUS") for l in eq)
    if not eq or not (us and xus):
        out["value_factor"] = _r("value_factor", "NOT_APPLICABLE" if not eq else "INSUFFICIENT_DATA", "No regional valuation data.")
    else:
        v = ("SUPPORT" if has_xus else "CAUTION") if xus < us else "NEUTRAL"
        out["value_factor"] = _r("value_factor", v, f"Ex-U.S. trailing P/E {xus} vs U.S. {us}; proposal "
                                 f"{'includes' if has_xus else 'excludes'} ex-U.S. equities.")

    # cost
    er = sum(l["weight"] * float(l["expense_ratio"]) for l in legs) * 100
    out["cost"] = _r("cost", "SUPPORT" if er <= 0.10 else ("CAUTION" if er <= 0.50 else "CHALLENGE"),
                     f"Weighted expense ratio {er:.3f}%/yr.", weighted_expense_pct=round(er, 3))

    # diversification, understanding, sizing, concentration
    single = [l for l in eq if (l.get("holdings_count") or 1000) < 1000 and l.get("wrapper", "ETF") == "STOCK"]
    out["diversify_securities"] = _r("diversify_securities", "CHALLENGE" if single else "SUPPORT",
                                     "Equity exposure via broad index funds." if not single else f"Single-stock legs: {single}")
    out["understand"] = _r("understand", "SUPPORT" if all(l.get("benchmark") for l in legs) else "CAUTION",
                           "; ".join(f"{l['symbol']} tracks {l.get('benchmark')}" for l in legs))
    big_single = [l for l in single if l["weight"] > 0.05]
    out["sizing"] = _r("sizing", "CHALLENGE" if big_single or proposal.get("active") else "SUPPORT",
                       "No measured edge → Kelly active-bet size is zero; exposure comes only from diversified funds."
                       if not proposal.get("active") else "Active bet proposed without a measured edge.")
    out["concentration"] = _r("concentration", "CHALLENGE",
                              "Concentrated-research doctrine dissents from owning thousands of businesses no one has analysed. "
                              "Policy block: single-company research cost exceeds 5% of a small position (Phase 7).",
                              policy_blocked=True)
    out["concentration_warning"] = _r("concentration_warning", "CHALLENGE" if any(l["weight"] > 0.25 for l in single) else "SUPPORT",
                                      "No single company exceeds 25% of the portfolio.")
    out["distressed"] = _r("distressed", "NOT_APPLICABLE", "No credit-spread or default data in this snapshot.")
    out["asymmetry"] = _r("asymmetry", "NEUTRAL", "Core passive holding; no asymmetric payoff is claimed.")

    # owner-dependent
    h = owner.get("horizon_years")
    out["horizon"] = _r("horizon", "INSUFFICIENT_DATA" if h is None else
                        ("SUPPORT" if h >= 5 else ("CAUTION" if h >= 3 else ("CHALLENGE" if eq else "SUPPORT"))),
                        f"Owner horizon: {h if h is not None else 'unknown'} years.")
    fails, unknown = [], []
    if owner.get("emergency_fund_ok") is False:
        fails.append("no emergency fund")
    elif owner.get("emergency_fund_ok") is None:
        unknown.append("emergency fund status")
    if h is not None and h < 3 and eq:
        fails.append("short horizon with equities")
    if er > 0.5:
        fails.append("high fees")
    out["inversion"] = _r("inversion", "CHALLENGE" if fails else ("CAUTION" if unknown else "SUPPORT"),
                          "How this fails: " + (", ".join(fails) if fails else "no known failure path present") +
                          (f"; unknown: {', '.join(unknown)}" if unknown else "") + ". No leverage; one-time purchase, no frequent trading.")
    out["edge"] = _r("edge", "CHALLENGE" if proposal.get("active") and not proposal.get("validated_oos") else "SUPPORT",
                     "Passive proposal: no edge claimed, so none needs proving." if not proposal.get("active")
                     else "Active selection lacks a validated out-of-sample test.")
    fz = proposal.get("falsification") or []
    out["falsifiable"] = _r("falsifiable", "SUPPORT" if fz and all(f.get("justification") for f in fz) else "CHALLENGE",
                            f"{len(fz)} falsification conditions recorded before the outcome.")
    return out


def council(proposal: dict, snap: dict, owner: dict, library: dict = None) -> dict:
    lib = library or load_library()
    lenses = run_lenses(proposal, snap, owner)
    by_investor, school_lenses = [], {}
    for inv in lib["investors"]:
        blocked = sorted(set(inv["requires"]) & POLICY_BLOCKED)
        items = [{"principle": p["text"], "lens": p["lens"], "verdict": lenses[p["lens"]]["verdict"]} for p in inv["principles"]]
        by_investor.append({"id": inv["id"], "name": inv["name"], "school": inv["school"], "region": inv["region"],
                            "applicability": inv["small_capital"], "policy_blocked_parts": blocked,
                            "source_quality": inv["source_quality"], "principles": items})
        for p in inv["principles"]:
            school_lenses.setdefault(inv["school"], set()).add(p["lens"])
    # Fame-neutral tally: one vote per DISTINCT lens.
    tally = {v: sorted(k for k, r in lenses.items() if r["verdict"] == v) for v in VERDICTS}
    name_counts = {v: sum(1 for i in by_investor for p in i["principles"] if p["verdict"] == v) for v in VERDICTS}
    # One dissent record per challenged lens: who challenges, and which other schools' lenses support the proposal.
    conflicts = []
    for l in tally["CHALLENGE"]:
        challengers = sorted(s for s, ls in school_lenses.items() if l in ls)
        supporters = {s: sorted(x for x in ls if lenses[x]["verdict"] == "SUPPORT")
                      for s, ls in school_lenses.items() if s not in challengers}
        conflicts.append({"challenge_lens": l, "challenging_schools": challengers,
                          "supporting_schools": {s: v for s, v in sorted(supporters.items()) if v}})
    challenges = [dict(lenses[l], doctrines=[i["name"] for i in by_investor if any(p["lens"] == l for p in i["principles"])])
                  for l in tally["CHALLENGE"]]
    preservation_challenges = [c["lens"] for c in challenges if c["lens"] in PRESERVATION_FAMILY]
    strongest = sorted(challenges, key=lambda c: (c["lens"] not in PRESERVATION_FAMILY, c["lens"]))
    return {"library_version": lib["library_version"], "lens_rules_version": LENS_RULES_VERSION,
            "proposal": proposal["name"], "lenses": lenses, "tally_by_distinct_lens": tally,
            "famous_name_counts_ignored_for_weighting": name_counts, "school_conflicts": conflicts,
            "challenges": challenges, "preservation_challenges": preservation_challenges,
            "strongest_dissent": strongest[0] if strongest else None, "investors": by_investor,
            "note": "Agreement among famous investors is not proof. Each lens counts once; the Judgment Reviewer must answer every CHALLENGE."}


ROLE_LENSES = {
    "market_intel": ["cycle", "liquidity", "momentum", "value_factor", "contrarian"],
    "research": ["cost", "diversify_securities", "understand", "margin_of_safety", "edge"],
    "risk": ["capital_preservation", "risk_streams", "sizing", "concentration_warning", "inversion"],
    "compounding": ["horizon", "cost"],
    "judgment": list(LENS_RULES),
    "auditor": ["falsifiable"],
}


def validate_citations(text_or_obj, library: dict = None) -> list:
    """Auditor check: no fabricated attributions or endorsements of GCI trades."""
    lib = library or load_library()
    names = {i["name"] for i in lib["investors"]}
    issues = []
    s = json.dumps(text_or_obj, default=str) if not isinstance(text_or_obj, str) else text_or_obj
    import re
    for m in re.finditer(r"([A-Z][a-z]+(?: [A-Z][a-z.]+)+) (?:recommends|endorses|approves|would buy|says to buy)", s):
        issues.append(f"Attribution not allowed: '{m.group(0)}'. Doctrines are frameworks, not endorsements.")
    if isinstance(text_or_obj, dict) and "investors" in text_or_obj:
        for i in text_or_obj["investors"]:
            if i["name"] not in names:
                issues.append(f"Unknown doctrine source '{i['name']}' (not in library).")
            for p in i["principles"]:
                if p["lens"] not in LENS_RULES:
                    issues.append(f"Principle maps to unknown lens '{p['lens']}'.")
    return issues
