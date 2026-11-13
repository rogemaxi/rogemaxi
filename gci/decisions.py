"""Decision Memory and falsification (SSOI Phase 4).

A decision record is immutable once written. Reviews and outcomes are appended
in a separate table. Falsification conditions are fixed before the outcome is known.
"""
import json
import math
import operator
import uuid
from datetime import date

from .db import Store, now_iso

REQUIRED_FIELDS = ["instrument", "market", "currency", "sources", "thesis", "contrary_evidence", "confidence",
                   "assumptions", "estimated_costs", "benchmark", "risk_rating", "regime", "falsification",
                   "review_date", "agents"]

OPS = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le, "==": operator.eq, "!=": operator.ne}


class DecisionError(Exception):
    pass


def validate(rec: dict):
    missing = [f for f in REQUIRED_FIELDS if rec.get(f) in (None, "", [], {})]
    if missing:
        raise DecisionError(f"Decision record incomplete; missing {missing}")
    for s in rec["sources"]:
        if not s.get("url") or not s.get("retrieved_at"):
            raise DecisionError("Every source needs a url and retrieved_at timestamp.")
    for f in rec["falsification"]:
        for k in ("metric", "op", "threshold", "justification"):
            if f.get(k) in (None, ""):
                raise DecisionError(f"Falsification condition missing '{k}': {f}")
        if f["op"] not in OPS:
            raise DecisionError(f"Unknown operator {f['op']}")
    c = rec["confidence"]
    if not (0 < float(c.get("probability", -1)) < 1):
        raise DecisionError("Confidence must be a probability strictly between 0 and 1 (no certainty claims).")
    date.fromisoformat(rec["review_date"])


class DecisionMemory:
    def __init__(self, store: Store):
        self.s = store

    def record(self, rec: dict, actor="agent:head_manager") -> str:
        validate(rec)
        did = "DEC-" + date.today().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6].upper()
        full = {"id": did, "created_ts": now_iso(), "owner_decision": None, **rec,
                "question": "What specific evidence would prove this recommendation wrong?"}
        with self.s.tx() as c:
            c.execute("INSERT INTO decisions VALUES (?,?,?,?,?)",
                      (did, full["created_ts"], json.dumps(full, default=str), rec["review_date"], "OPEN"))
            self.s.log(actor, "DECISION_RECORDED", {"id": did, "instrument": rec["instrument"]})
        return did

    def set_owner_decision(self, did: str, decision: str, note: str = ""):
        # Owner decisions are appended as events and status changes; the original record is preserved.
        with self.s.tx() as c:
            c.execute("UPDATE decisions SET status=? WHERE id=?", (f"OWNER_{decision}", did))
            self.s.log("owner", "OWNER_DECISION", {"decision_id": did, "decision": decision, "note": note})

    def get(self, did: str) -> dict:
        r = self.s.conn.execute("SELECT * FROM decisions WHERE id=?", (did,)).fetchone()
        if not r:
            return None
        rec = json.loads(r["record"])
        rec["status"] = r["status"]
        owner = [e for e in self.s.events(limit=10000, kind="OWNER_DECISION") if e["payload"]["decision_id"] == did]
        rec["owner_decision"] = owner[0]["payload"]["decision"] if owner else None
        rec["reviews"] = [dict(x) | {"observed": json.loads(x["observed"]), "triggered": json.loads(x["triggered"])}
                          for x in self.s.conn.execute("SELECT * FROM decision_reviews WHERE decision_id=? ORDER BY id", (did,))]
        return rec

    def list(self):
        return [self.get(r["id"]) for r in self.s.conn.execute("SELECT id FROM decisions ORDER BY created_ts DESC")]

    def due_reviews(self, today: str = None):
        today = today or date.today().isoformat()
        return [r["id"] for r in self.s.conn.execute(
            "SELECT id FROM decisions WHERE review_date <= ? AND status NOT LIKE 'CLOSED%' ORDER BY review_date", (today,))]

    def review(self, did: str, observed: dict, outcome: dict = None, lessons: str = "", actor="agent:auditor") -> dict:
        rec = self.get(did)
        if rec is None:
            raise DecisionError("Unknown decision")
        triggered, unevaluated = [], []
        for f in rec["falsification"]:
            if f["metric"] not in observed or observed[f["metric"]] is None:
                unevaluated.append(f["metric"])
                continue
            if OPS[f["op"]](float(observed[f["metric"]]), float(f["threshold"])):
                triggered.append(f)
        with self.s.tx() as c:
            c.execute("INSERT INTO decision_reviews (decision_id, ts, observed, triggered, outcome, lessons) VALUES (?,?,?,?,?,?)",
                      (did, now_iso(), json.dumps(observed), json.dumps(triggered), json.dumps(outcome) if outcome else None, lessons))
            if outcome is not None:
                c.execute("UPDATE decisions SET status=? WHERE id=?", ("CLOSED_FALSIFIED" if triggered else "CLOSED", did))
            self.s.log(actor, "DECISION_REVIEWED", {"id": did, "triggered": [t["metric"] for t in triggered],
                                                    "unevaluated": unevaluated})
        return {"triggered": triggered, "unevaluated": unevaluated, "thesis_falsified": bool(triggered)}

    # ---- decision-quality metrics -------------------------------------------
    def metrics(self) -> dict:
        resolved = []
        for d in self.list():
            outs = [r for r in d["reviews"] if r["outcome"]]
            if outs:
                o = json.loads(outs[-1]["outcome"])
                resolved.append((d, o, outs[-1]))
        n = len(resolved)
        if n == 0:
            return {"resolved_decisions": 0, "note": "No resolved decisions yet; metrics unavailable."}
        brier = sum((float(d["confidence"]["probability"]) - (1.0 if o.get("thesis_held") else 0.0)) ** 2
                    for d, o, _ in resolved) / n
        falsified = sum(1 for _, _, r in resolved if r["triggered"])
        claims = [(o.get("claims_verified", 0), o.get("claims_total", 0)) for _, o, _ in resolved]
        cv, ct = sum(a for a, _ in claims), sum(b for _, b in claims)
        excess = [o["excess_return_vs_benchmark"] for _, o, _ in resolved if o.get("excess_return_vs_benchmark") is not None]
        mean_ex = sum(excess) / len(excess) if excess else None
        se = (math.sqrt(sum((x - mean_ex) ** 2 for x in excess) / (len(excess) - 1)) / math.sqrt(len(excess))
              if len(excess) > 1 else None)
        return {"resolved_decisions": n, "brier_score": round(brier, 4),
                "falsification_rate": round(falsified / n, 4),
                "factual_accuracy": round(cv / ct, 4) if ct else None,
                "mean_excess_return_vs_benchmark": mean_ex, "excess_return_std_error": se,
                "sample_warning": "n < 30: do not infer skill; results are indistinguishable from luck." if n < 30 else None}

    def regime_matrix(self, research_costs: dict = None) -> list:
        """Market regime x recommendation category x decision quality x outcome x cost, with sample sizes."""
        cells = {}
        for d in self.list():
            key = (d["regime"].get("key", "UNKNOWN"), d.get("category", "UNCATEGORIZED"))
            cell = cells.setdefault(key, {"regime": key[0], "category": key[1], "n": 0, "resolved": 0,
                                          "held": 0, "falsified": 0, "cost": 0.0})
            cell["n"] += 1
            cell["cost"] += float((research_costs or {}).get(d["id"], 0))
            outs = [r for r in d["reviews"] if r["outcome"]]
            if outs:
                cell["resolved"] += 1
                cell["held"] += 1 if json.loads(outs[-1]["outcome"]).get("thesis_held") else 0
                cell["falsified"] += 1 if outs[-1]["triggered"] else 0
        for c in cells.values():
            c["hit_rate"] = round(c["held"] / c["resolved"], 3) if c["resolved"] else None
            c["sample_warning"] = "insufficient sample" if c["resolved"] < 30 else None
        return list(cells.values())
