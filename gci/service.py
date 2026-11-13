"""Workflows that tie the engines together. Used by the dashboard, CLI and demo."""
from datetime import date, timedelta

from .agents import HeadManager
from .approvals import Approvals
from .decisions import DecisionMemory
from .marketdata import load_snapshot
from .money import D, cents
from .regime import classify
from . import VERSION

BROKER_DEFAULTS = {"fractional_supported": True, "min_investment": "5", "commission_per_trade": "0"}


def candidates_from_snapshot(snap: dict) -> list:
    spread = next((a["value"] for a in snap.get("assumptions", []) if a["id"] == "spread_bps"), None)
    fx = next((a["value"] for a in snap.get("assumptions", []) if a["id"] == "fx_cost_bps"), None)
    out = []
    for c in snap["candidates"]:
        srcs = [s for s in snap["sources"] if s.get("symbol") == c["symbol"] or s["kind"] in ("broker", "prices")]
        risks = {"global_equity": ["Equity drawdowns of 30-50% have occurred", "Currency exposure on ~40% non-U.S. holdings"],
                 "us_equity": ["Equity drawdowns", "Single-country concentration (U.S.)"],
                 "international_equity": ["Equity drawdowns", "Currency and geopolitical exposure"],
                 "fixed_income_cash_equivalent": ["Yield falls when the Fed cuts", "Inflation can exceed yield"],
                 "fixed_income": ["Interest-rate risk (~5.7y duration)", "Credit risk (small, investment-grade)"]}
        out.append({**BROKER_DEFAULTS, **c, "accessible_in_account": c.get("jpm_fractional_eligible"),
                    "spread_bps": spread, "fx_cost_bps": fx, "sources": srcs,
                    "risks": risks.get(c["asset_class"], []),
                    "assumptions": ["Broker eligibility list is dated 2024-11-19; confirm in the J.P. Morgan app before buying."]})
    return out


def analyze_starter_allocation(store, amount, owner_profile: dict, snap: dict = None, review_days=90) -> dict:
    """Phase 19 steps 3-10: research, viability, independent review, falsification, decision card."""
    snap = snap or load_snapshot()
    amount = D(amount)
    cands = candidates_from_snapshot(snap)
    equity_pick = "VT"
    thesis = (f"Put ${cents(amount)} into one broad global stock fund (VT, about 10,185 stocks across developed and emerging "
              f"markets, 0.06% annual cost) using a $0-commission fractional order. One fund gives the widest "
              f"diversification for the fewest decisions. Alternative: hold in T-bills/SGOV at about 4.24% "
              f"(13-week bill, as of {snap['rates']['as_of']}) if the money may be needed within 5 years.")
    ctx = {"evidence": snap, "candidates": cands, "cash": amount, "amount_for": lambda c: amount,
           "owner_profile": owner_profile, "proposal_equity_pct": 100, "thesis": thesis,
           "liquidity_reserve": 0, "research_cost": 0}
    hm = HeadManager(store)
    job = hm.run("allocation_change", ctx, dedupe_key=f"starter-{amount}-{snap['snapshot_id']}")
    if job.get("duplicate"):
        job = {**job, **_job_output(store, job["job_id"])}
    regime = classify({k: v for k, v in snap["regime_inputs"].items() if not k.startswith("_")})
    vt = next(c for c in job["research"]["cards"] if c["symbol"] == equity_pick)
    sgov = next(c for c in job["research"]["cards"] if c["symbol"] == "SGOV")
    review_date = (date.today() + timedelta(days=review_days)).isoformat()
    falsification = [
        {"metric": "tracking_difference_pp_12m", "op": "<", "threshold": -0.30,
         "justification": "VT's cost is 0.06%/yr; a shortfall vs its index worse than 0.30pp (5x the fee) would mean the "
                          "fund is failing its core job of matching the index."},
        {"metric": "expense_ratio", "op": ">", "threshold": 0.0010,
         "justification": "The low-cost rationale fails if the fee rises above 0.10% while near-identical funds stay lower."},
        {"metric": "jpm_commission_usd", "op": ">", "threshold": 0,
         "justification": "Any per-trade commission on a $40 position consumes a large share of it."},
        {"metric": "owner_horizon_years", "op": "<", "threshold": 5,
         "justification": "Equity suitability depends on not needing the money for 5+ years."},
    ]
    record = {
        "category": "STARTER_ALLOCATION", "instrument": equity_pick, "market": "Global (NYSE Arca-listed ETF)",
        "currency": "USD", "sources": snap["sources"], "evidence_snapshot": snap["snapshot_id"], "thesis": thesis,
        "contrary_evidence": job["judgment"]["challenges"],
        "confidence": {"probability": 0.6, "statement": "Moderate: VT will track its index within 0.30pp over 12 months "
                       "and remain the lowest-friction diversified option at this size. No return forecast is made."},
        "assumptions": [a["basis"] for a in snap["assumptions"]] + vt["assumptions"],
        "estimated_costs": {"commission": "0.00", "spread_round_trip": vt["viability"]["checks"].get("round_trip_cost"),
                            "annual_expense": vt["viability"]["checks"].get("annual_expense_cost"), "research_usd": "0.00"},
        "benchmark": "FTSE Global All Cap Index (passive benchmark); cash benchmark: 13-week T-bill",
        "risk_rating": job["risk"]["verdict"], "risk_findings": job["risk"]["findings"],
        "regime": regime, "falsification": falsification, "review_date": review_date,
        "agents": {"selected": job["agents"], "versions": {"gci": VERSION, "agents": "deterministic-rules-1.0"},
                   "job_id": job["job_id"]},
        "auditor": job["auditor"], "viability": {c["symbol"]: c["viability"]["classification"] for c in job["research"]["cards"]},
    }
    dm = DecisionMemory(store)
    did = dm.record(record)
    card = {
        "action": f"Buy ${cents(amount)} of VT (Vanguard Total World Stock ETF) as a $0-commission fractional order, "
                  f"placed by you in your J.P. Morgan account.",
        "reason": f"Widest diversification (≈10,185 stocks, U.S. + international) at 0.06%/yr (≈${cents(amount * D('0.0006'))}/yr "
                  f"on ${cents(amount)}). Fractional orders from $5 with $0 commission make a ${cents(amount)} position economically viable.",
        "inaction": f"Money stays in cash. If swept to T-bills/SGOV it earns about {snap['rates']['tbill_13w_coupon_equiv_pct']}% "
                    f"(≈${cents(amount * D(str(snap['rates']['tbill_13w_coupon_equiv_pct'])) / 100)}/yr) with almost no price risk; "
                    f"you forgo uncertain long-run equity growth.",
        "rejection_conditions": [
            "You may need this money within 5 years, or you have no emergency fund → choose SGOV/cash instead.",
            "VT is not offered for fractional purchase in your J.P. Morgan app (list we have is dated 2024-11-19).",
            "A commission or minimum above $5 applies to this order.",
            "You are not prepared to see the $40 fall to roughly $20-27 in a severe downturn.",
        ],
        "details": {
            "sources": snap["sources"], "risks": job["risk"]["findings"], "fees": record["estimated_costs"],
            "assumptions": record["assumptions"],
            "portfolio_impact": f"100% of ${cents(amount)} investable cash → global equity. Ledger A cash → $0 after settlement.",
            "alternatives": [f"SGOV (T-bills, 0.09% fee, 30-day SEC yield 3.86%): {sgov['viability']['classification']}",
                             "Split VTI/VXUS: viable but two orders for the same exposure as VT; no benefit at $40.",
                             "BND: bond fund with ~5.7-year duration; adds rate risk without a stated need."],
            "reviewer_conclusions": {"risk": job["risk"]["verdict"], "judgment": job["judgment"]["recommendation"],
                                     "auditor_certified": job["auditor"]["certified"], "auditor_issues": job["auditor"]["issues"]},
            "evidence_freshness": snap["freshness"],
        },
    }
    aid = Approvals(store).create(card, did)
    return {"decision_id": did, "approval_id": aid, "job_id": job["job_id"], "card": card, "job": job, "regime": regime}


def _job_output(store, job_id):
    import json
    r = store.conn.execute("SELECT output FROM research_jobs WHERE id=?", (job_id,)).fetchone()
    return json.loads(r["output"])
