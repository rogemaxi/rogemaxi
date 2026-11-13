"""Local dashboard server. Binds to 127.0.0.1 only. Every state-changing request
must carry the per-session token embedded in the page (blocks cross-site requests
from other browser tabs). The person at this computer is treated as the owner.
"""
import json
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from . import VERSION
from .agents import HeadManager, AGENTS, ROUTES
from .approvals import Approvals
from .brokerage import BrokerageImport, CONNECTION_STATUS
from .db import Store
from .decisions import DecisionMemory
from .funding import Funding
from .ledgers import Ledgers
from .marketdata import load_snapshot, fetch_treasury_bills, DataUnavailable
from .matching import Matching
from .money import D
from .policy import PolicyViolation, refuse
from .portfolio import Portfolio
from .regime import RULES, classify
from .security import backup, redact
from .service import analyze_starter_allocation, candidates_from_snapshot
from . import agents as agent_mod

STATIC = Path(__file__).parent / "static"


class App:
    def __init__(self, store: Store, backup_dir: Path):
        self.s = store
        self.token = secrets.token_urlsafe(24)
        self.backup_dir = backup_dir
        self.lock = threading.Lock()

    # ---- GET views ----
    def status(self, q):
        f = Funding(self.s)
        snap = _safe_snapshot()
        alerts = []
        if f.suspended():
            alerts.append({"level": "high", "text": "Research spending suspended: " + f.suspended()["reason"]})
        if snap:
            for k, v in snap["freshness"].items():
                if v["stale"]:
                    alerts.append({"level": "medium", "text": f"Stale data: {k} as of {v['as_of']} ({v['age_days']} days old)"})
        due = DecisionMemory(self.s).due_reviews()
        if due:
            alerts.append({"level": "medium", "text": f"{len(due)} decision review(s) due: {', '.join(due)}"})
        chain = self.s.verify_chain()
        if not chain["ok"]:
            alerts.append({"level": "high", "text": "Audit log integrity check FAILED"})
        return {"version": VERSION, "dataset": self.s.dataset, "brokerage": CONNECTION_STATUS,
                "portfolio": Portfolio(self.s).summary(), "pending_approvals": len(Approvals(self.s).list("PENDING")),
                "alerts": alerts, "chain": chain}

    def markets(self, q):
        snap = _safe_snapshot()
        if not snap:
            return {"available": False, "message": "No evidence snapshot loaded."}
        return {"available": True, "snapshot": snap["snapshot_id"], "label": snap["label"], "rates": snap["rates"],
                "freshness": snap["freshness"], "regions_note": snap["regions_note"], "broker": snap["broker"],
                "regime": classify({k: v for k, v in snap["regime_inputs"].items() if not k.startswith("_")}),
                "regime_rules": RULES, "sources": snap["sources"]}

    def research(self, q):
        snap = _safe_snapshot()
        return {"candidates": candidates_from_snapshot(snap) if snap else [],
                "jobs": [dict(r) | {"output": json.loads(r["output"] or "{}")} for r in
                         self.s.conn.execute("SELECT * FROM research_jobs ORDER BY ts DESC LIMIT 20")]}

    def risk(self, q):
        pf = Portfolio(self.s).summary()
        total = D(pf["total_value"])
        alloc = [{"symbol": h["symbol"], "pct": str(round(D(h["market_value"]) / total * 100, 2)) if total and h["market_value"] else None}
                 for h in pf["holdings"]]
        scen = []
        for name, shock in (("Equity crash (-50%, 2008-09 scale)", "-0.50"), ("Equity bear (-30%)", "-0.30"),
                            ("Rates +2pp on 5.7y-duration bonds (≈-11%)", "-0.114")):
            loss = sum((D(h["market_value"] or 0) * D(shock) for h in pf["holdings"]
                        if (shock != "-0.114" and h["symbol"] in ("VT", "VTI", "VXUS")) or (shock == "-0.114" and h["symbol"] == "BND")), D(0))
            scen.append({"scenario": name, "estimated_change": str(round(loss, 2))})
        return {"allocation": alloc, "stress_tests": scen, "cash": pf["cash"],
                "note": "Stress tests apply historical-scale shocks to current holdings; they are not predictions."}

    def compounding(self, q):
        ctx = {"start": q.get("start", ["40"])[0], "monthly": q.get("monthly", ["0"])[0], "years": q.get("years", ["10"])[0]}
        return agent_mod.compounding(ctx)

    def decisions(self, q):
        dm = DecisionMemory(self.s)
        return {"decisions": dm.list(), "due": dm.due_reviews(), "metrics": dm.metrics(), "regime_matrix": dm.regime_matrix()}

    def doctrine(self, q):
        from .doctrine import load_library, LENS_RULES, ROLE_LENSES
        from .service import choose_allocation
        snap = _safe_snapshot()
        lib = load_library()
        out = {"library": lib, "lens_rules": LENS_RULES, "role_lenses": ROLE_LENSES}
        if snap:
            ch = choose_allocation(snap, self.s.setting("owner_profile", {}) or {})
            out["councils"] = {k: {kk: v[kk] for kk in ("proposal", "lenses", "tally_by_distinct_lens", "school_conflicts",
                                                        "preservation_challenges", "note")} for k, v in ch["councils"].items()}
            out["pick"], out["rule"], out["resolved"] = ch["pick"], ch["rule"], ch["resolved_by_allocation"]
        return out

    def agents(self, q):
        return {"roles": AGENTS, "routes": ROUTES, "economics": HeadManager(self.s).unit_economics()}

    def ledgers(self, q):
        led = Ledgers(self.s)
        return {"balances": {k: str(led.balance(k)) for k in "ABC"}, "entries": led.entries(limit=200),
                "reconciliation": led.reconcile_internal(),
                "certifications": [dict(r) | {"record": json.loads(r["record"])} for r in
                                   self.s.conn.execute("SELECT * FROM gain_certifications ORDER BY ts DESC")],
                "authorizations": [dict(r) for r in self.s.conn.execute("SELECT * FROM authorizations ORDER BY ts DESC")],
                "matching": Matching(self.s).list(), "funding_policy": Funding(self.s).policy(),
                "suspended": Funding(self.s).suspended()}

    def approvals(self, q):
        return {"approvals": Approvals(self.s).list()}

    def audit(self, q):
        return {"chain": self.s.verify_chain(), "events": self.s.events(limit=300)}

    def settings(self, q):
        return {"funding_policy": Funding(self.s).policy(), "dataset": self.s.dataset, "db": Path(self.s.path).name,
                "brokerage": CONNECTION_STATUS, "owner_profile": self.s.setting("owner_profile", {})}

    # ---- POST actions ----
    def act(self, path, body):
        if path == "/api/analyze":
            prof = self.s.setting("owner_profile", {})
            prof = {**prof, **{k: body[k] for k in ("horizon_years", "emergency_fund_ok") if k in body}}
            r = analyze_starter_allocation(self.s, body.get("amount", "40"), prof)
            return {"decision_id": r["decision_id"], "approval_id": r["approval_id"]}
        if path == "/api/approve":
            return Approvals(self.s).decide(body["id"], body["decision"], "owner", body.get("note", ""))
        if path == "/api/contribution":
            return {"entry": Ledgers(self.s).post("A", "CONTRIBUTION", body["amount"], body.get("memo", "Owner contribution"))}
        if path == "/api/trade":  # record a trade the owner ALREADY executed at the broker
            pf = Portfolio(self.s)
            fn = pf.record_buy if body["side"] == "BUY" else pf.record_sell
            return {"result": str(fn(body["symbol"], body["qty"], body["price"], body.get("fee", 0),
                                     external_id=body.get("confirmation_id") or None))}
        if path == "/api/price":
            Portfolio(self.s).set_price(body["symbol"], body["price"], body["as_of"], body.get("source", "owner entry"))
            return {"ok": True}
        if path == "/api/authorize":
            return {"authorization_id": Ledgers(self.s).authorize(body["action"], body.get("amount"), {"note": body.get("note", "")})}
        if path == "/api/transfer":
            return {"transfer_id": Ledgers(self.s).transfer(body["src"], body["dst"], body["amount"], body["authorization_id"])}
        if path == "/api/certify":
            return Funding(self.s).certify(body["period_start"], body["period_end"])
        if path == "/api/allocate":
            return {"transfer_id": Funding(self.s).allocate_to_research(body["cert_id"], body["authorization_id"])}
        if path == "/api/match/propose":
            return Matching(self.s).propose(body["cert_id"], body["ratio"], body["owner_cash"], body["owner_reserve"])
        if path == "/api/match/confirm":
            return {"entry": Matching(self.s).confirm(body["id"], body["amount"])}
        if path == "/api/import":
            return BrokerageImport(self.s).import_activity(body["csv"], body.get("source", "upload"), self.s.dataset)
        if path == "/api/reconcile":
            return BrokerageImport(self.s).reconcile_positions(body["csv"], body.get("cash"))
        if path == "/api/review":
            return DecisionMemory(self.s).review(body["id"], body["observed"], body.get("outcome"), body.get("lessons", ""))
        if path == "/api/policy":
            return Funding(self.s).set_policy(**body)
        if path == "/api/profile":
            self.s.set_setting("owner_profile", body)
            return {"ok": True}
        if path == "/api/resume":
            Funding(self.s).resume()
            return {"ok": True}
        if path == "/api/backup":
            from datetime import datetime
            return backup(self.s, self.backup_dir / f"gci_backup_{datetime.now():%Y%m%d_%H%M%S}.db")
        if path == "/api/refresh-rates":
            try:
                return {"ok": True, "data": fetch_treasury_bills()}
            except DataUnavailable as exc:
                return {"ok": False, "error": str(exc), "message": "Live fetch unavailable; showing last dated snapshot."}
        if path == "/api/place-order":
            refuse("place_order")
        raise KeyError(path)


def _safe_snapshot():
    try:
        return load_snapshot()
    except Exception:
        return None


GET_ROUTES = {"/api/status": "status", "/api/markets": "markets", "/api/research": "research", "/api/risk": "risk",
              "/api/compounding": "compounding", "/api/decisions": "decisions", "/api/agents": "agents",
              "/api/ledgers": "ledgers", "/api/approvals": "approvals", "/api/audit": "audit", "/api/settings": "settings",
              "/api/portfolio": "status", "/api/doctrine": "doctrine"}


def make_handler(app: App):
    class H(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def _send(self, code, obj, ctype="application/json"):
            data = obj if isinstance(obj, bytes) else redact(json.dumps(obj, default=str)).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            u = urlparse(self.path)
            if u.path in ("/", "/index.html"):
                html = (STATIC / "index.html").read_text(encoding="utf-8").replace("__TOKEN__", app.token)
                return self._send(200, html.encode(), "text/html; charset=utf-8")
            if u.path in GET_ROUTES:
                with app.lock:
                    return self._send(200, getattr(app, GET_ROUTES[u.path])(parse_qs(u.query)))
            self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.headers.get("X-GCI-Token") != app.token:
                return self._send(403, {"error": "missing or invalid session token"})
            n = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
                with app.lock:
                    return self._send(200, app.act(urlparse(self.path).path, body))
            except PolicyViolation as exc:
                app.s.log("owner", "REFUSED_OPERATION", {"path": self.path, "reason": str(exc)})
                return self._send(403, {"error": str(exc), "refused": True})
            except KeyError as exc:
                return self._send(400, {"error": f"missing field or unknown action: {exc}"})
            except Exception as exc:
                return self._send(400, {"error": str(exc)})
    return H


def serve(db_path, dataset="REAL", port=8765, open_browser=True):
    store = Store.open(db_path, dataset)
    app = App(store, Path(db_path).parent / "backups")
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app))
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    print(f"GCI {VERSION} running at {url}  (dataset: {dataset}, db: {db_path}). Close this window to stop.")
    if open_browser:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    finally:
        store.close()
    return srv
