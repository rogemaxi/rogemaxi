"""Six specialist roles + a deterministic Head Manager (SSOI Phase 3).

Specialists here are deterministic, rule-based analysts: they cost $0 per call
and are fully reproducible. An optional LLM backend can be added behind the
same interface later; every call is metered through the budget controller.

Rules enforced:
  * The Head Manager selects the minimum sufficient specialist set.
  * No agent may review/approve its own output.
  * Consequential decisions always get Capital Protection + Judgment + Auditor.
"""
import json
import re
import time
import uuid

from .db import Store, now_iso
from .funding import Funding
from .money import D, ZERO, cents
from .policy import instrument_violations
from . import viability

AGENTS = {
    "market_intel": "Global Market Intelligence",
    "research": "Investment Research",
    "risk": "Capital Protection and Portfolio Risk",
    "compounding": "Compounding and Income Planning",
    "auditor": "Independent Auditor",
    "judgment": "Judgment Reviewer",
}

ROUTES = {
    "fund_expense_comparison": ["research", "auditor"],
    "regional_market_update": ["market_intel", "research"],
    "allocation_change": ["market_intel", "research", "risk", "judgment", "auditor"],
    "budget_certification": ["compounding", "auditor"],
    "contribution_plan": ["compounding", "auditor"],
    "risk_check": ["risk"],
}
CONSEQUENTIAL = {"allocation_change"}
DEPENDENCIES = {"risk": ["research"], "judgment": ["research"], "auditor": ["research", "risk", "judgment", "compounding"]}

UNSUPPORTED_CLAIM_PATTERNS = [r"\bguarantee", r"\brisk[- ]free (?:return|profit)", r"\bcan(?:'|no)t lose\b",
                              r"\b100% (?:accurate|certain|safe)", r"\bsure thing\b", r"\b(?:20|50)x returns?\b"]


class AgentError(Exception):
    pass


# ---------------- specialists ----------------
def market_intel(ctx):
    ev = ctx["evidence"]
    stale = [k for k, v in ev.get("freshness", {}).items() if v.get("stale")]
    rates = ev.get("rates", {})
    return {"summary": f"3-mo T-bill (coupon-equivalent) {rates.get('tbill_13w_coupon_equiv_pct')}% as of {rates.get('as_of')}.",
            "stale_inputs": stale, "regions_note": ev.get("regions_note", ""),
            "sources": [s for s in ev.get("sources", []) if s.get("kind") in ("rates", "macro")]}


def research(ctx):
    cards = []
    for c in ctx["candidates"]:
        v = viability.assess(c, ctx["amount_for"](c), ctx["cash"], ctx.get("liquidity_reserve", 0),
                             ctx.get("research_cost", 0))
        cards.append({"symbol": c["symbol"], "name": c.get("name"), "asset_class": c.get("asset_class"),
                      "wrapper": c.get("wrapper", "ETF"), "expense_ratio": c.get("expense_ratio"),
                      "price": c.get("price"), "price_as_of": c.get("price_as_of"),
                      "benchmark": c.get("benchmark"), "viability": v, "risks": c.get("risks", []),
                      "assumptions": c.get("assumptions", []), "sources": c.get("sources", [])})
    return {"cards": cards}


def risk(ctx, research_out):
    findings, verdict = [], "PASS"
    profile = ctx.get("owner_profile", {})
    if profile.get("horizon_years") is None:
        findings.append("Owner time horizon unknown: equity exposure cannot be confirmed suitable.")
        verdict = "REVIEW"
    elif profile["horizon_years"] < 3:
        findings.append("Horizon < 3 years: equity drawdowns of 30-50% have historically taken years to recover.")
        verdict = "REJECT" if ctx.get("proposal_equity_pct", 0) > 0 else verdict
    if profile.get("emergency_fund_ok") is False:
        findings.append("Owner reports no emergency fund: investing reserve money is not suitable.")
        verdict = "REJECT"
    for card in research_out["cards"]:
        if card["viability"]["classification"] == "REJECT":
            findings.append(f"{card['symbol']}: rejected by gate - {card['viability']['reasons']}")
        if card.get("asset_class") == "international_equity":
            findings.append(f"{card['symbol']}: currency and geopolitical exposure (non-USD assets).")
    findings.append("Historical stress reference: global equities fell roughly a third to a half in 2008-09 and in early 2020. "
                    "A $40 position could temporarily be worth $20-27.")
    return {"verdict": verdict, "findings": findings}


def judgment(ctx, research_out, risk_out):
    challenges = [
        "Counter-thesis: with $40, every outcome is economically tiny; the real driver of wealth here is contribution "
        "rate, not security selection.",
        "Doing nothing (holding cash/T-bills) preserves capital and earns near the T-bill rate; inaction cost is mainly "
        "missed equity risk premium, which is uncertain and only expected over long horizons.",
        "Confidence should stay moderate: no forecast of short-term returns is justified by the evidence.",
    ]
    if risk_out["verdict"] != "PASS":
        challenges.append(f"Risk verdict is {risk_out['verdict']}; recommend not acting until resolved.")
    responses = []
    cn = ctx.get("council")
    if cn:
        resolved = ctx.get("resolved_by_allocation", [])
        for c in cn["challenges"]:
            if c["derived"].get("policy_blocked"):
                disp = "POLICY_BLOCKED: acting on it would breach the Phase 7 research-cost gate and the concentration policy."
            else:
                disp = "UNRESOLVED: owner decides; listed as a rejection condition."
            responses.append({"lens": c["lens"], "doctrines": c["doctrines"], "evidence": c["evidence"], "disposition": disp})
            if not c["derived"].get("policy_blocked"):
                challenges.append(f"Doctrine dissent ({c['lens']}: {', '.join(c['doctrines'][:3])}): {c['evidence']}")
        for l in resolved:
            responses.append({"lens": l, "disposition": "RESOLVED_BY_ALLOCATION: the chosen allocation answers this challenge "
                                                         "raised against the 100%-equity alternative."})
        challenges.append("Fame check: evidence is counted once per distinct lens "
                          f"({len(cn['tally_by_distinct_lens']['SUPPORT'])} support, {len(cn['tally_by_distinct_lens']['CHALLENGE'])} challenge), "
                          "not by how many famous investors share a view.")
    recommend = "PROCEED_TO_OWNER" if risk_out["verdict"] in ("PASS", "REVIEW") else "REJECT"
    return {"challenges": challenges, "doctrine_responses": responses, "recommendation": recommend, "confidence_ceiling": 0.6}


def compounding(ctx):
    proj = []
    start, monthly, years = D(ctx.get("start", 0)), D(ctx.get("monthly", 0)), int(ctx.get("years", 10))
    for label, r in (("adverse", D("-0.02")), ("conservative", D("0.03")), ("base", D("0.06"))):
        bal, contrib = start, start
        for _ in range(years * 12):
            bal = bal * (1 + r / 12) + monthly
            contrib += monthly
        proj.append({"scenario": label, "annual_return_assumed": str(r), "years": years,
                     "ending_value": str(cents(bal)), "of_which_contributions": str(cents(contrib)),
                     "of_which_growth": str(cents(bal - contrib))})
    return {"projections": proj, "disclaimer": "Illustrative arithmetic under assumed constant returns. Not a forecast."}


def auditor(ctx, outputs):
    issues = []
    text = json.dumps(outputs, default=str)
    for pat in UNSUPPORTED_CLAIM_PATTERNS:
        for m in re.finditer(pat, ctx.get("thesis", ""), re.I):
            issues.append(f"Unsupported claim in thesis: '{m.group(0)}'")
    # Narrative drift: every percentage cited in the thesis must exist in the evidence.
    allowed = set(re.findall(r"\d+\.?\d*", json.dumps(ctx["evidence"], default=str)))
    allowed |= {format(float(n) * 100, "g") for n in list(allowed) if float(n) < 1}  # 0.0006 -> "0.06" (percent form)
    allowed |= set(re.findall(r"\d+\.?\d*", json.dumps(ctx.get("derived", {}), default=str)))  # recorded calculations
    if ctx.get("council"):
        from .doctrine import validate_citations
        issues += validate_citations(ctx["council"])
        issues += validate_citations(ctx.get("thesis", ""))
    for num in re.findall(r"(\d+\.?\d*)\s*%", ctx.get("thesis", "")):
        if num not in allowed:
            issues.append(f"Thesis cites {num}% which does not appear in the recorded evidence (narrative drift).")
    for s in ctx["evidence"].get("sources", []):
        if not s.get("url") or not s.get("retrieved_at"):
            issues.append(f"Source missing url/timestamp: {s}")
    if "research" in outputs:
        for card in outputs["research"]["cards"]:
            if not card["sources"]:
                issues.append(f"{card['symbol']}: research card has no sources.")
    return {"certified": not issues, "issues": issues, "checked_bytes": len(text)}


# ---------------- head manager ----------------
class HeadManager:
    def __init__(self, store: Store):
        self.s = store
        self.funding = Funding(store)

    def select(self, task_type: str) -> list:
        if task_type not in ROUTES:
            raise AgentError(f"Unknown task type {task_type}")
        return list(ROUTES[task_type])

    def check_not_self_review(self, author: str, reviewer: str):
        if author == reviewer:
            raise AgentError(f"Agent '{author}' cannot review or approve its own findings.")

    def duplicate_of(self, task_type: str, key: str):
        r = self.s.conn.execute("SELECT id FROM research_jobs WHERE task_type=? AND status='DONE' AND output LIKE ? "
                                "AND ts >= datetime('now','-1 day')", (task_type, f'%"dedupe_key": "{key}"%')).fetchone()
        return r["id"] if r else None

    def run(self, task_type: str, ctx: dict, dedupe_key: str = None, est_cost=ZERO) -> dict:
        agents = self.select(task_type)
        if dedupe_key:
            dup = self.duplicate_of(task_type, dedupe_key)
            if dup:
                return {"job_id": dup, "duplicate": True, "agents": agents}
        est_cost = D(est_cost)
        if est_cost > ZERO:
            self.funding.spend(est_cost, f"pending-{task_type}")  # raises if over budget/suspended
        job_id = "JOB-" + uuid.uuid4().hex[:8].upper()
        t0 = time.perf_counter()
        out = {"dedupe_key": dedupe_key, "agents": agents}
        if "market_intel" in agents:
            out["market_intel"] = market_intel(ctx)
        if "research" in agents:
            out["research"] = research(ctx)
        if "risk" in agents:
            out["risk"] = risk(ctx, out["research"])
        if "judgment" in agents:
            self.check_not_self_review("research", "judgment")
            out["judgment"] = judgment(ctx, out["research"], out["risk"])
        if "compounding" in agents:
            out["compounding"] = compounding(ctx)
        if "auditor" in agents:
            self.check_not_self_review("research", "auditor")
            out["auditor"] = auditor(ctx, {k: v for k, v in out.items() if k in AGENTS})
        if ctx.get("council"):
            from .doctrine import ROLE_LENSES
            for role in agents:
                if role in out and isinstance(out[role], dict) and role != "judgment":
                    out[role]["doctrine_lenses"] = {l: {"verdict": ctx["council"]["lenses"][l]["verdict"],
                                                        "evidence": ctx["council"]["lenses"][l]["evidence"]}
                                                    for l in ROLE_LENSES[role]}
        if task_type in CONSEQUENTIAL:
            missing = {"risk", "judgment", "auditor"} - set(agents)
            if missing:
                raise AgentError(f"Consequential task missing independent review: {missing}")
        ms = int((time.perf_counter() - t0) * 1000)
        with self.s.tx() as c:
            c.execute("INSERT INTO research_jobs VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (job_id, now_iso(), task_type, json.dumps(agents), "DONE", str(est_cost), ms, 0, None,
                       json.dumps(out, default=str)))
            self.s.log("agent:head_manager", "JOB_DONE", {"job": job_id, "task": task_type, "agents": agents,
                                                          "cost": str(est_cost), "ms": ms})
        return {"job_id": job_id, "duplicate": False, **out}

    def unit_economics(self) -> dict:
        rows = self.s.conn.execute("SELECT * FROM research_jobs").fetchall()
        n = len(rows)
        cost = sum((D(r["cost"]) for r in rows), ZERO)
        verified = 0
        for r in rows:
            o = json.loads(r["output"] or "{}")
            if o.get("auditor", {}).get("certified"):
                verified += 1
        decided = self.s.conn.execute("SELECT COUNT(*) n FROM approvals WHERE status IN ('APPROVED','REJECTED')").fetchone()["n"]
        return {"jobs": n, "total_cost": str(cents(cost)), "verified_decisions": verified, "owner_decisions": decided,
                "cost_per_verified_decision": str(cents(cost / verified)) if verified else "unavailable",
                "cost_per_bp_of_return": "unavailable (no defensible attributable result yet)",
                "avg_duration_ms": (sum(r["duration_ms"] for r in rows) // n) if n else None}
