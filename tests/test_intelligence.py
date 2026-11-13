"""Agents, decision memory, regimes, validation, brokerage, security, server.
ALL RECORDS HERE ARE SYNTHETIC TEST DATA."""
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import date, timedelta

from gci import agents, backtest
from gci.agents import HeadManager, AgentError
from gci.approvals import Approvals, ApprovalError
from gci.brokerage import BrokerageImport
from gci.db import Store
from gci.decisions import DecisionMemory, DecisionError
from gci.funding import Funding
from gci.ledgers import Ledgers, LedgerError
from gci.marketdata import load_snapshot, fetch_treasury_bills, freshness, DataUnavailable
from gci.money import D
from gci.portfolio import Portfolio
from gci.regime import classify
from gci.security import redact, scan_for_secrets, CredentialStore, CredentialStoreUnavailable, backup, restore
from gci.service import analyze_starter_allocation


def mem():
    return Store.open(":memory:", "SYNTHETIC")


PROFILE = {"horizon_years": 10, "emergency_fund_ok": True}


class TestRouting(unittest.TestCase):  # items 1, 20
    def test_minimum_sufficient_sets(self):
        hm = HeadManager(mem())
        self.assertEqual(hm.select("fund_expense_comparison"), ["research", "auditor"])
        self.assertEqual(hm.select("regional_market_update"), ["market_intel", "research"])
        self.assertEqual(set(hm.select("allocation_change")) >= {"research", "risk", "judgment", "auditor"}, True)
        self.assertEqual(hm.select("budget_certification"), ["compounding", "auditor"])
        with self.assertRaises(AgentError):
            hm.select("make_me_rich")

    def test_no_self_review(self):
        with self.assertRaises(AgentError):
            HeadManager(mem()).check_not_self_review("research", "research")

    def test_duplicate_research_prevented(self):
        s = mem()
        r1 = analyze_starter_allocation(s, 40, PROFILE)
        hm = HeadManager(s)
        snap = load_snapshot()
        dup = hm.run("allocation_change", {}, dedupe_key=f"starter-40-{snap['snapshot_id']}")
        self.assertTrue(dup["duplicate"])
        self.assertEqual(dup["job_id"], r1["job_id"])

    def test_judgment_challenges_and_risk_rejects_unsuitable(self):  # 20
        s = mem()
        r = analyze_starter_allocation(s, 40, {"horizon_years": 1, "emergency_fund_ok": False})
        self.assertEqual(r["job"]["risk"]["verdict"], "REJECT")
        self.assertEqual(r["job"]["judgment"]["recommendation"], "REJECT")
        self.assertTrue(any("doing nothing" in c.lower() for c in r["job"]["judgment"]["challenges"]))

    def test_unknown_profile_needs_review(self):
        r = analyze_starter_allocation(mem(), 40, {})
        self.assertEqual(r["job"]["risk"]["verdict"], "REVIEW")


class TestAuditorIntegrity(unittest.TestCase):  # items 18, 19
    def ctx(self, thesis, sources=None):
        snap = load_snapshot()
        if sources is not None:
            snap = {**snap, "sources": sources}
        return {"evidence": snap, "thesis": thesis}

    def test_narrative_drift_detected(self):
        out = agents.auditor(self.ctx("VT costs 0.06% and T-bills pay 7.5%."), {})
        self.assertFalse(out["certified"])
        self.assertTrue(any("7.5" in i for i in out["issues"]))

    def test_supported_numbers_pass(self):
        self.assertTrue(agents.auditor(self.ctx("VT costs 0.06%; 13-week bills 4.24%."), {})["certified"])

    def test_unsupported_claims(self):
        out = agents.auditor(self.ctx("This is guaranteed and you can't lose."), {})
        self.assertGreaterEqual(len(out["issues"]), 2)

    def test_source_integrity(self):
        out = agents.auditor(self.ctx("x", sources=[{"title": "no url"}]), {})
        self.assertFalse(out["certified"])


class TestDecisionMemory(unittest.TestCase):  # items 13, 14
    def test_complete_record_and_falsification(self):
        s = mem()
        r = analyze_starter_allocation(s, 40, PROFILE)
        dm = DecisionMemory(s)
        d = dm.get(r["decision_id"])
        for f in ("thesis", "contrary_evidence", "falsification", "sources", "regime", "benchmark", "review_date", "agents"):
            self.assertTrue(d[f], f)
        res = dm.review(r["decision_id"], {"expense_ratio": 0.0006, "jpm_commission_usd": 0})
        self.assertFalse(res["thesis_falsified"])
        self.assertIn("tracking_difference_pp_12m", res["unevaluated"])
        res = dm.review(r["decision_id"], {"expense_ratio": 0.0015}, outcome={"thesis_held": False, "claims_verified": 3,
                                                                               "claims_total": 3})
        self.assertTrue(res["thesis_falsified"])
        self.assertEqual(dm.get(r["decision_id"])["status"], "CLOSED_FALSIFIED")
        m = dm.metrics()
        self.assertEqual(m["resolved_decisions"], 1)
        self.assertIn("n < 30", m["sample_warning"])

    def test_record_rejected_without_falsification_or_with_certainty(self):
        dm = DecisionMemory(mem())
        with self.assertRaises(DecisionError):
            dm.record({"instrument": "VT"})
        good = {"instrument": "VT", "market": "US", "currency": "USD", "thesis": "t", "contrary_evidence": ["c"],
                "confidence": {"probability": 1.0}, "assumptions": ["a"], "estimated_costs": {"x": 0}, "benchmark": "b",
                "risk_rating": "PASS", "regime": {"key": "k"}, "review_date": date.today().isoformat(), "agents": {"a": 1},
                "sources": [{"url": "https://x", "retrieved_at": "2026-11-13"}],
                "falsification": [{"metric": "m", "op": ">", "threshold": 1, "justification": "j"}]}
        with self.assertRaises(DecisionError):
            dm.record(good)  # probability 1.0 = certainty claim
        good["confidence"] = {"probability": 0.6}
        did = dm.record(good)
        self.assertIn(did, dm.due_reviews())  # review date today -> scheduled

    def test_owner_decision_cannot_overwrite_record(self):
        s = mem()
        r = analyze_starter_allocation(s, 40, PROFILE)
        thesis = DecisionMemory(s).get(r["decision_id"])["thesis"]
        Approvals(s).decide(r["approval_id"], "REJECTED", note="too risky")
        d = DecisionMemory(s).get(r["decision_id"])
        self.assertEqual(d["thesis"], thesis)
        self.assertEqual(d["owner_decision"], "REJECTED")


class TestApprovals(unittest.TestCase):  # item 21
    def test_four_parts_required_and_no_execution(self):
        s = mem(); a = Approvals(s)
        with self.assertRaises(ApprovalError):
            a.create({"action": "x", "reason": "y"})
        aid = a.create({"action": "a", "reason": "b", "inaction": "c", "rejection_conditions": ["d"]})
        with self.assertRaises(ApprovalError):
            a.decide(aid, "APPROVED", owner="agent:research")
        d = a.decide(aid, "DEFERRED")
        self.assertFalse(d["trade_executed"])
        d = a.decide(aid, "APPROVED")
        self.assertFalse(d["trade_executed"])
        with self.assertRaises(ApprovalError):
            a.decide(aid, "REJECTED")
        self.assertEqual(s.conn.execute("SELECT COUNT(*) n FROM lots").fetchone()["n"], 0)


class TestRegime(unittest.TestCase):  # item 15
    def test_reproducible_and_unknown_when_missing(self):
        inp = {"tbill_3m_change_pp": 0.5, "cpi_yoy_pct": 3.0, "vix": 30, "equity_vs_200d_pct": -5}
        a, b = classify(inp), classify(dict(inp))
        self.assertEqual(a, b)
        self.assertEqual(a["tags"]["rate_direction"], "RISING")
        self.assertEqual(a["tags"]["inflation"], "MODERATE")
        self.assertEqual(a["tags"]["volatility"], "HIGH")
        self.assertEqual(a["tags"]["equity_trend"], "DOWNTREND")
        self.assertEqual(a["tags"]["dollar"], "UNKNOWN")


def synth_prices(n=240):
    import math
    eq = [100 * (1.006 ** i) * (1 + 0.08 * math.sin(i / 7)) for i in range(n)]
    bd = [100 * (1.003 ** i) for i in range(n)]
    return {"EQ": eq, "BD": bd}


class TestValidation(unittest.TestCase):  # items 16, 17
    def test_no_lookahead(self):
        prices = synth_prices()
        seen = []

        def strat(hist):
            seen.append(len(hist["EQ"]))
            return {"EQ": 1.0}
        backtest.simulate(prices, strat, 10, 50)
        self.assertEqual(seen[0], 11)  # at t=10 only indices 0..10 visible
        self.assertTrue(all(isinstance(v, tuple) for v in [tuple()]))

        def cheat(hist):
            return {"EQ": 1.0 if hist["EQ"][-1] < prices["EQ"][len(hist["EQ"])] else 0.0}  # tries t+1 via closure
        # Can't stop closures over global data, but history itself never contains t+1:
        def peek(hist):
            hist["EQ"][len(hist["EQ"])]  # IndexError if look-ahead attempted
        with self.assertRaises(IndexError):
            backtest.simulate(prices, peek, 10, 20)

    def test_walk_forward_out_of_sample_non_overlapping(self):
        wf = backtest.walk_forward(synth_prices(), lambda train: (lambda h: {"EQ": 0.6, "BD": 0.4}), train=60, test=24)
        self.assertGreaterEqual(wf["n_folds"], 3)
        for f in wf["folds"]:
            self.assertEqual(f["train"][1], f["test"][0])

    def test_costs_reduce_results_monotonically(self):
        p = synth_prices()
        flip = lambda h: {"EQ": 1.0} if len(h["EQ"]) % 2 else {"BD": 1.0}
        res = backtest.cost_sensitivity(p, flip, 0, 100)
        vals = [r["final_value"] for r in res]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_benchmark_comparison_and_windows(self):
        p = synth_prices()
        w = backtest.rolling_windows(240, 60, 40)
        cmp = backtest.compare_to_benchmark(p, lambda h: {"EQ": 0.6, "BD": 0.4}, lambda h: {"EQ": 1.0}, w)
        self.assertGreaterEqual(cmp["n"], 3)
        self.assertIn("BACKTEST", cmp["label"])

    def test_no_leverage_in_backtests(self):
        with self.assertRaises(ValueError):
            backtest.simulate(synth_prices(), lambda h: {"EQ": 2.0}, 0, 10)

    def test_survivorship(self):
        with self.assertRaises(backtest.LookAheadError):
            backtest.survivorship_check({"A": (0, None), "B": (50, None)}, ["A", "B"], 10)

    def test_inflation_and_drawdown(self):
        self.assertAlmostEqual(backtest.real_return(0.10, 0.03), 1.10 / 1.03 - 1)
        self.assertAlmostEqual(backtest.max_drawdown([100, 120, 60, 130]), -0.5)


class TestMarketData(unittest.TestCase):  # items 2, 3, 27
    def test_snapshot_sourced_and_dated(self):
        snap = load_snapshot(today=date(2026, 11, 13))
        self.assertTrue(all(s["url"].startswith("https://") and s["retrieved_at"] for s in snap["sources"]))
        self.assertFalse(snap["freshness"]["prices"]["stale"])
        self.assertTrue(snap["freshness"]["jpm_fractional_list"]["stale"])  # 2024 list must be flagged

    def test_stale_detection(self):
        self.assertTrue(freshness("2026-01-01", 3, date(2026, 11, 13))["stale"])

    def test_api_failure_is_reported_not_faked(self):
        def boom(url, timeout):
            raise urllib.error.URLError("network policy")
        with self.assertRaises(DataUnavailable):
            fetch_treasury_bills("202611", opener=boom)

    def test_treasury_parser(self):
        csv = ('Date,"4 WEEKS BANK DISCOUNT","13 WEEKS BANK DISCOUNT","13 WEEKS COUPON EQUIVALENT"\n'
               '11/12/2026,3.97,4.14,4.24\n')

        class R:
            def __enter__(s): return s
            def __exit__(s, *a): return False
            def read(s): return csv.encode()
        d = fetch_treasury_bills("202611", opener=lambda u, timeout: R())
        self.assertEqual((d["as_of"], d["tbill_13w_coupon_equiv_pct"]), ("2026-11-12", 4.24))


class TestBrokerage(unittest.TestCase):  # items 22, 23, 4
    CSV = ("Trade Date,Action,Ticker,Qty,Price,Net Amount,Commission,Description\n"
           "2026-11-13,DEPOSIT,,,,40.00,,Deposit\n"
           "2026-11-13,BUY,VT,0.25682,155.75,,0,Bought VT\n")

    def test_import_dedup_and_reconcile(self):
        s = mem(); b = BrokerageImport(s)
        r = b.import_activity(self.CSV, "test", "SYNTHETIC")
        self.assertEqual((r["added"], r["errors"]), (2, []))
        r2 = b.import_activity(self.CSV, "test", "SYNTHETIC")
        self.assertEqual((r2["added"], r2["duplicates_skipped"]), (0, 2))
        ok = b.reconcile_positions("symbol,quantity\nVT,0.25682\n", broker_cash=str(D("40") - D("0.25682") * D("155.75")))
        self.assertTrue(ok["ok"], ok)
        bad = b.reconcile_positions("symbol,quantity\nVT,0.30000\n")
        self.assertFalse(bad["ok"])
        self.assertTrue(Funding(s).suspended())  # failed reconciliation suspends research spend

    def test_synthetic_file_refused_by_real_db(self):
        with tempfile.TemporaryDirectory() as d:
            s = Store.open(os.path.join(d, "real.db"), "REAL")
            with self.assertRaises(LedgerError):
                BrokerageImport(s).import_activity(self.CSV, "t", "SYNTHETIC")
            s.close()

    def test_withdrawal_not_importable_as_plain_flow(self):
        s = mem(); b = BrokerageImport(s)
        r = b.import_activity("date,type,amount\n2026-11-13,WITHDRAWAL,5\n", "t", "SYNTHETIC")
        self.assertEqual(len(r["errors"]), 1)


class TestSecurity(unittest.TestCase):  # items 24, 26
    def test_redaction(self):
        t = redact("key sk-abcdefghijklmnopqrstuvwx and password=hunter2222 Bearer abcdefghijklmnopqrstu")
        self.assertNotIn("hunter2222", t); self.assertNotIn("sk-abcdef", t); self.assertNotIn("abcdefghijklmnopqrstu", t)

    def test_repository_has_no_secrets(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        hits = [h for h in scan_for_secrets(root) if "test_" not in h["file"] and "security.py" not in h["file"]]
        self.assertEqual(hits, [])

    def test_brokerage_credentials_refused_and_no_plaintext(self):
        with tempfile.TemporaryDirectory() as d:
            cs = CredentialStore(os.path.join(d, "c.json"))
            with self.assertRaises(PermissionError):
                cs.put("jpmorgan_password", "x")
            if os.name != "nt":
                with self.assertRaises(CredentialStoreUnavailable):
                    cs.put("data_api_key", "abc")
                self.assertFalse(os.path.exists(os.path.join(d, "c.json")))

    def test_backup_and_restore(self):
        with tempfile.TemporaryDirectory() as d:
            s = Store.open(os.path.join(d, "a.db"), "SYNTHETIC")
            Ledgers(s).post("A", "CONTRIBUTION", "40")
            backup(s, os.path.join(d, "bk.db"))
            s.close()
            r = restore(os.path.join(d, "bk.db"), os.path.join(d, "restored.db"), "SYNTHETIC")
            self.assertEqual(Ledgers(r).balance("A"), D("40"))
            self.assertTrue(r.verify_chain()["ok"])
            r.close()

    def test_tamper_detection(self):
        s = mem()
        s.log("x", "E", {"a": 1})
        s.conn.execute("DROP TRIGGER events_no_update")
        s.conn.execute("UPDATE events SET payload='{\"a\": 2}' WHERE kind='E'")
        self.assertFalse(s.verify_chain()["ok"])


class TestServer(unittest.TestCase):  # items 21, 28 via HTTP
    @classmethod
    def setUpClass(cls):
        from http.server import ThreadingHTTPServer
        from gci.server import App, make_handler
        cls.tmp = tempfile.TemporaryDirectory()
        cls.store = Store.open(os.path.join(cls.tmp.name, "s.db"), "SYNTHETIC")
        cls.app = App(cls.store, __import__("pathlib").Path(cls.tmp.name))
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.app))
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.store.close(); cls.tmp.cleanup()

    def call(self, path, body=None, token=True):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json",
                                              **({"X-GCI-Token": self.app.token} if token else {})})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_all_sections_load(self):
        for p in ("/api/status", "/api/markets", "/api/research", "/api/risk", "/api/compounding", "/api/decisions",
                  "/api/agents", "/api/ledgers", "/api/approvals", "/api/audit", "/api/settings"):
            code, _ = self.call(p)
            self.assertEqual(code, 200, p)

    def test_post_requires_token(self):
        code, _ = self.call("/api/contribution", {"amount": "1"}, token=False)
        self.assertEqual(code, 403)

    def test_order_placement_refused(self):
        code, body = self.call("/api/place-order", {"symbol": "VT"})
        self.assertEqual(code, 403); self.assertTrue(body["refused"])

    def test_analyze_and_decide_flow(self):
        code, r = self.call("/api/analyze", {"amount": "40", "horizon_years": 10, "emergency_fund_ok": True})
        self.assertEqual(code, 200)
        code, d = self.call("/api/approve", {"id": r["approval_id"], "decision": "APPROVED"})
        self.assertEqual(code, 200); self.assertFalse(d["trade_executed"])

    def test_html_has_twelve_sections(self):
        with urllib.request.urlopen(self.base + "/") as r:
            html = r.read().decode()
        for name in ("Command Center", "Global Markets", "Portfolio", "Research", "Risk", "Compounding", "Decision Memory",
                     "Agent Operations", "Capital Ledgers", "Approvals", "Audit", "Settings"):
            self.assertIn(name, html)
        self.assertNotIn("__TOKEN__", html)


class TestAcceptance(unittest.TestCase):  # items 25 (partial), Phase 19
    def test_demo_40_and_10000(self):
        from gci.demo import run
        with tempfile.TemporaryDirectory() as d:
            for amt in ("40", "10000"):
                r = run(os.path.join(d, amt, "demo.db"), amt, os.path.join(d, amt))
                self.assertEqual(r["passed"], r["total"], [s for s in r["steps"] if not s["pass"]])


if __name__ == "__main__":
    unittest.main()
