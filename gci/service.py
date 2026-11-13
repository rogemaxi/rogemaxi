"""Workflows that tie the engines together. Used by the dashboard, CLI and demo."""
import json
from datetime import date, timedelta

from .agents import HeadManager
from .approvals import Approvals
from .decisions import DecisionMemory
from .doctrine import council, LENS_RULES_VERSION
from .marketdata import load_snapshot
from .money import D, cents
from .regime import classify
from . import viability, VERSION

BROKER_DEFAULTS = {"fractional_supported": True, "min_investment": "5", "commission_per_trade": "0"}
SELECTION_RULE = ("Start from 100% VT (lowest cost, widest diversification). If the Doctrine Council raises two or more "
                  "capital-preservation CHALLENGEs against it (margin of safety, return streams, capital preservation, "
                  "cycle, liquidity) and the 50/50 VT/SGOV barbell raises fewer, recommend the barbell.")

BASE_FALSIFICATION = [
    {"metric": "tracking_difference_pp_12m", "op": "<", "threshold": -0.30,
     "justification": "VT's cost is 0.06%/yr; a shortfall vs its index worse than 0.30pp (5x the fee) would mean the "
                      "fund is failing its core job of matching the index."},
    {"metric": "expense_ratio", "op": ">", "threshold": 0.0010,
     "justification": "The low-cost rationale fails if VT's fee rises above 0.10% while near-identical funds stay lower."},
    {"metric": "jpm_commission_usd", "op": ">", "threshold": 0,
     "justification": "Any per-trade commission on a small position consumes a large share of it."},
    {"metric": "owner_horizon_years", "op": "<", "threshold": 5,
     "justification": "Equity suitability depends on not needing the money for 5+ years."},
]
BARBELL_FALSIFICATION = [
    {"metric": "equity_premium_pp", "op": ">", "threshold": 3.0,
     "justification": "The barbell exists because equities' earnings-yield premium over T-bills is thin (<1pp). Above 3pp, "
                      "holding half in T-bills is no longer justified by this lens; revisit toward more equity."},
    {"metric": "sgov_expense_ratio", "op": ">", "threshold": 0.0015,
     "justification": "Above 0.15%, SGOV's fee would consume a material share of its T-bill yield versus alternatives."},
]
PROPOSALS = {
    "ALL_EQUITY": {"name": "100% VT (global equity)", "legs": [{"symbol": "VT", "weight": 1.0, "asset_class": "global_equity"}],
                   "falsification": BASE_FALSIFICATION},
    "BARBELL": {"name": "50% VT + 50% SGOV (barbell)",
                "legs": [{"symbol": "VT", "weight": 0.5, "asset_class": "global_equity"},
                         {"symbol": "SGOV", "weight": 0.5, "asset_class": "fixed_income_cash_equivalent"}],
                "falsification": BASE_FALSIFICATION + BARBELL_FALSIFICATION},
}


def candidates_from_snapshot(snap: dict) -> list:
    spread = next((a["value"] for a in snap.get("assumptions", []) if a["id"] == "spread_bps"), None)
    fx = next((a["value"] for a in snap.get("assumptions", []) if a["id"] == "fx_cost_bps"), None)
    out = []
    for c in snap["candidates"]:
        srcs = [s for s in snap["sources"] if s.get("symbol") == c["symbol"] or s["kind"] in ("broker", "prices")]
        risks = {"global_equity": ["Equity drawdowns of 30-50% have occurred", "Currency exposure on non-U.S. holdings"],
                 "us_equity": ["Equity drawdowns", "Single-country concentration (U.S.)"],
                 "international_equity": ["Equity drawdowns", "Currency and geopolitical exposure"],
                 "fixed_income_cash_equivalent": ["Yield falls when the Fed cuts", "Inflation can exceed yield"],
                 "fixed_income": ["Interest-rate risk (~5.7y duration)", "Credit risk (small, investment-grade)"]}
        out.append({**BROKER_DEFAULTS, **c, "accessible_in_account": c.get("jpm_fractional_eligible"),
                    "spread_bps": spread, "fx_cost_bps": fx, "sources": srcs,
                    "risks": risks.get(c["asset_class"], []),
                    "assumptions": ["Broker eligibility list is dated 2024-11-19; confirm in the J.P. Morgan app before buying."]})
    return out


def choose_allocation(snap, owner) -> dict:
    councils = {k: council(p, snap, owner) for k, p in PROPOSALS.items()}
    a, b = councils["ALL_EQUITY"], councils["BARBELL"]
    pick = "BARBELL" if len(a["preservation_challenges"]) >= 2 and len(b["preservation_challenges"]) < len(a["preservation_challenges"]) \
        else "ALL_EQUITY"
    other = "ALL_EQUITY" if pick == "BARBELL" else "BARBELL"
    resolved = sorted(set(a["preservation_challenges"]) - set(councils[pick]["preservation_challenges"])) if pick == "BARBELL" else []
    return {"pick": pick, "other": other, "councils": councils, "resolved_by_allocation": resolved, "rule": SELECTION_RULE}


def analyze_starter_allocation(store, amount, owner_profile: dict, snap: dict = None, review_days=90) -> dict:
    """Phase 19 steps 3-10 with the Doctrine Council: research, viability, independent review, falsification, card."""
    snap = snap or load_snapshot()
    amount = D(amount)
    cands = candidates_from_snapshot(snap)
    by_sym = {c["symbol"]: c for c in cands}
    choice = choose_allocation(snap, owner_profile)
    prop, cn = PROPOSALS[choice["pick"]], choice["councils"][choice["pick"]]
    alt_cn = choice["councils"][choice["other"]]
    legs = [{**l, "amount": cents(amount * D(str(l["weight"])))} for l in prop["legs"]]
    leg_viability = {l["symbol"]: viability.assess(by_sym[l["symbol"]], l["amount"], l["amount"]) for l in legs}
    mos = cn["lenses"]["margin_of_safety"]["derived"]
    rates = snap["rates"]
    if choice["pick"] == "BARBELL":
        thesis = (f"Split ${cents(amount)}: ${legs[0]['amount']} into VT (about 10,185 stocks worldwide, 0.06% annual cost) and "
                  f"${legs[1]['amount']} into SGOV (0-3 month T-bills, 0.09% cost, 30-day SEC yield 3.86%). The Doctrine Council "
                  f"found the equity earnings yield of {mos['earnings_yield_pct']}% only {mos['equity_premium_pp']}pp above the "
                  f"4.24% 13-week T-bill (thin margin of safety), and that 100% equity is a single return stream. The split answers "
                  f"both while keeping global equity exposure.")
    else:
        thesis = (f"Put ${cents(amount)} into VT (about 10,185 stocks worldwide, 0.06% annual cost) using a $0-commission "
                  f"fractional order. Alternative: T-bills/SGOV at about 4.24% if the money may be needed within 5 years.")
    derived = {k: v["derived"] for k, v in cn["lenses"].items()}
    ctx = {"evidence": snap, "candidates": cands, "cash": amount, "amount_for": lambda c: amount,
           "owner_profile": owner_profile, "proposal_equity_pct": int(sum(l["weight"] for l in legs
                                                                           if l["asset_class"].endswith("equity")) * 100),
           "thesis": thesis, "liquidity_reserve": 0, "research_cost": 0, "council": cn, "derived": derived,
           "resolved_by_allocation": choice["resolved_by_allocation"]}
    hm = HeadManager(store)
    job = hm.run("allocation_change", ctx, dedupe_key=dedupe_key(amount, snap, owner_profile))
    if job.get("duplicate"):
        job = {**job, **_job_output(store, job["job_id"])}
    regime = classify({k: v for k, v in snap["regime_inputs"].items() if not k.startswith("_")})
    review_date = (date.today() + timedelta(days=review_days)).isoformat()
    unresolved = [r for r in job["judgment"].get("doctrine_responses", []) if r["disposition"].startswith("UNRESOLVED")]
    record = {
        "category": "STARTER_ALLOCATION", "instrument": "+".join(l["symbol"] for l in legs),
        "allocation": [{k: str(v) if k == "amount" else v for k, v in l.items()} for l in legs],
        "market": "Global (U.S.-listed ETFs)", "currency": "USD", "sources": snap["sources"],
        "evidence_snapshot": snap["snapshot_id"], "thesis": thesis,
        "contrary_evidence": job["judgment"]["challenges"],
        "confidence": {"probability": 0.6, "statement": "Moderate: the allocation will meet its cost/diversification/"
                       "preservation purpose over 12 months. No return forecast is made."},
        "assumptions": [a["basis"] for a in snap["assumptions"]] + by_sym["VT"]["assumptions"],
        "estimated_costs": {"commission": "0.00", "spread_round_trip": {s: v["checks"].get("round_trip_cost") for s, v in leg_viability.items()},
                            "weighted_expense_pct": cn["lenses"]["cost"]["derived"]["weighted_expense_pct"], "research_usd": "0.00"},
        "benchmark": "FTSE Global All Cap Index (equity sleeve); 13-week T-bill (cash sleeve and no-action benchmark)",
        "risk_rating": job["risk"]["verdict"], "risk_findings": job["risk"]["findings"],
        "regime": regime, "falsification": prop["falsification"], "review_date": review_date,
        "agents": {"selected": job["agents"], "versions": {"gci": VERSION, "agents": "deterministic-rules-1.0",
                                                           "doctrine_library": cn["library_version"], "lens_rules": LENS_RULES_VERSION},
                   "job_id": job["job_id"]},
        "doctrine_council": {"chosen": prop["name"], "selection_rule": choice["rule"],
                             "chosen_tally": cn["tally_by_distinct_lens"], "alternative": PROPOSALS[choice["other"]]["name"],
                             "alternative_tally": alt_cn["tally_by_distinct_lens"],
                             "resolved_by_allocation": choice["resolved_by_allocation"],
                             "responses": job["judgment"].get("doctrine_responses", []), "dissent_records": cn["school_conflicts"]},
        "auditor": job["auditor"], "viability": {s: v["classification"] for s, v in leg_viability.items()},
    }
    did = DecisionMemory(store).record(record)
    legs_txt = " and ".join(f"${l['amount']} of {l['symbol']}" for l in legs)
    tb = rates["tbill_13w_coupon_equiv_pct"]
    card = {
        "action": f"Buy {legs_txt} as $0-commission fractional orders, placed by you in your J.P. Morgan account.",
        "reason": (f"{prop['name']}. " + ("Doctrine Council: equity earns only "
                   f"{mos['equity_premium_pp']}pp more than T-bills on trailing earnings (margin-of-safety lens: Graham, Klarman, Marks) "
                   "and 100% equity is a single return stream (Dalio, Graham). Half in T-bills answers both; the VT half keeps "
                   "global diversification at 0.06%/yr (Bogle, Buffett's index guidance)."
                   if choice["pick"] == "BARBELL" else
                   "Widest diversification at 0.06%/yr; the council found fewer than two capital-preservation challenges.")),
        "inaction": f"Money stays in cash. If swept to T-bills/SGOV it earns about {tb}% "
                    f"(≈${cents(amount * D(str(tb)) / 100)}/yr) with almost no price risk; you forgo uncertain long-run equity growth.",
        "rejection_conditions": [
            "You may need this money within 5 years, or you have no emergency fund → hold SGOV/cash only.",
            "Any leg is not offered for fractional purchase in your J.P. Morgan app (our eligibility list is dated 2024-11-19).",
            "A commission, or a minimum above $5, applies to these orders.",
        ] + [f"You find this unresolved dissent decisive — {r['lens']}: {r['evidence']}" for r in unresolved],
        "details": {
            "sources": snap["sources"], "risks": job["risk"]["findings"], "fees": record["estimated_costs"],
            "assumptions": record["assumptions"],
            "portfolio_impact": f"{legs_txt}. Ledger A cash → $0 after settlement.",
            "alternatives": [f"{PROPOSALS[choice['other']]['name']}: council tally "
                             f"{ {k: len(v) for k, v in alt_cn['tally_by_distinct_lens'].items()} }",
                             "Split VTI/VXUS: same exposure as VT with two orders; no benefit at this size.",
                             "BND: ~5.7-year duration adds rate risk without a stated need.",
                             "Single stocks (concentrated-research school): policy-blocked; research cost exceeds the position's economics."],
            "doctrine_review": {"chosen_tally": {k: len(v) for k, v in cn["tally_by_distinct_lens"].items()},
                                "responses": job["judgment"].get("doctrine_responses", []),
                                "selection_rule": choice["rule"], "note": cn["note"]},
            "reviewer_conclusions": {"risk": job["risk"]["verdict"], "judgment": job["judgment"]["recommendation"],
                                     "auditor_certified": job["auditor"]["certified"], "auditor_issues": job["auditor"]["issues"]},
            "leg_viability": {s: v["classification"] for s, v in leg_viability.items()},
            "evidence_freshness": snap["freshness"],
        },
    }
    aid = Approvals(store).create(card, did)
    return {"decision_id": did, "approval_id": aid, "job_id": job["job_id"], "card": card, "job": job, "regime": regime,
            "allocation": legs, "choice": choice["pick"], "council": cn}


def dedupe_key(amount, snap, owner_profile) -> str:
    import hashlib
    prof = hashlib.sha256(json.dumps(owner_profile, sort_keys=True).encode()).hexdigest()[:10]
    return f"starter-{D(amount)}-{snap['snapshot_id']}-{prof}"


def _job_output(store, job_id):
    r = store.conn.execute("SELECT output FROM research_jobs WHERE id=?", (job_id,)).fetchone()
    return json.loads(r["output"])
