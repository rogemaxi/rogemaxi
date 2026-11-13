"""Standing policy, ByrdWay bridge, circuit breakers, scheduler, weekly report, shadow mode, security incidents.
ALL RECORDS ARE SYNTHETIC TEST DATA."""
import json
import unittest
from datetime import date, datetime, timedelta, timezone

from gci.bridge import Bridge, BridgeError, BYRDWAY_COLUMNS
from gci.brokerage import BrokerageImport
from gci.control import Control, BreakerOpen
from gci.db import Store
from gci.funding import Funding
from gci.ips import InvestmentPolicy, PolicyError, TEMPLATE, validate, autoinvest_setup_steps, expected_schedule
from gci.ledgers import Ledgers
from gci.marketdata import load_snapshot
from gci.ops import Scheduler, ShadowMode, weekly_report, recurring_status, confirm_rotation, sync_known_exposures
from gci.portfolio import Portfolio

ACK = "I authorize this investment policy. GCI places no orders and moves no money."


def mem():
    s = Store.open(":memory:", "SYNTHETIC")
    Control(s).notify = lambda t, b: True
    return s


def policy(**over):
    p = json.loads(json.dumps(TEMPLATE))
    p["account"]["account_owner"] = "Owner (personal)"
    p["recurring"].update({"amount_per_period": "40", "frequency": "monthly", "start_date": "2026-11-20",
                           "legs": [{"symbol": "VT", "amount": "20"}, {"symbol": "SGOV", "amount": "20"}]})
    p["max_monthly_contribution"] = "100"
    p["target_allocation"] = {"VT": 50, "SGOV": 50}
    p["risk_limits"]["max_loss_tolerance_pct"] = 30
    p["liquidity_requirement"]["confirmed"] = True
    for k, v in over.items():
        p[k] = v
    return p


def signed(s, p=None):
    ip = InvestmentPolicy(s)
    v = ip.save_draft(p or policy())
    ip.sign(v, acknowledgement=ACK, snapshot=load_snapshot())
    return ip


class TestStandingPolicy(unittest.TestCase):
    def test_valid_policy_signs_and_is_tamper_evident(self):
        s = mem(); ip = signed(s)
        a = ip.active()
        self.assertEqual(a["version"], 1)
        s.conn.execute("UPDATE ips_versions SET policy=replace(policy,'\"100\"','\"9999\"')")
        with self.assertRaises(PolicyError):
            ip.active()

    def test_broker_rules_enforced(self):
        snap = load_snapshot()
        bad = policy(); bad["recurring"]["legs"][0]["amount"] = "3"; bad["recurring"]["amount_per_period"] = "23"
        self.assertTrue(any("$5" in e for e in validate(bad, snap)))
        bad = policy(); bad["recurring"]["frequency"] = "daily"
        self.assertTrue(any("Frequency" in e for e in validate(bad, snap)))
        bad = policy(); bad["account"]["account_type"] = "margin"
        self.assertTrue(any("margin" in e for e in validate(bad, snap)))
        bad = policy(); bad["recurring"]["legs"][0]["symbol"] = "TQQQ"; bad["eligible_instruments"].append("TQQQ")
        self.assertTrue(any("prohibited" in e for e in validate(bad, snap)))
        bad = policy(max_monthly_contribution="30")
        self.assertTrue(any("ceiling" in e for e in validate(bad, snap)))

    def test_signing_requires_owner_and_explicit_acknowledgement(self):
        s = mem(); ip = InvestmentPolicy(s); v = ip.save_draft(policy())
        with self.assertRaises(PolicyError):
            ip.sign(v, owner="agent:research", acknowledgement=ACK)
        with self.assertRaises(PolicyError):
            ip.sign(v, acknowledgement="ok")
        bad = InvestmentPolicy(s).save_draft(policy(max_monthly_contribution=None))
        with self.assertRaises(PolicyError):
            ip.sign(bad, acknowledgement=ACK)

    def test_ceiling_raise_is_new_signed_version(self):
        s = mem(); ip = signed(s)
        r = ip.raise_ceiling("300", acknowledgement=ACK)
        self.assertEqual(r["version"], 2)
        self.assertEqual(str(ip.ceiling()), "300")
        self.assertEqual([v["status"] for v in ip.versions()], ["SIGNED", "SUPERSEDED"])

    def test_setup_steps_and_schedule(self):
        steps = autoinvest_setup_steps(policy())
        self.assertTrue(any("VT, $20.00, monthly" in x for x in steps))
        self.assertTrue(any("password" in x for x in steps))
        self.assertEqual(len(expected_schedule(policy(), "2026-11-01", "2027-02-28")), 4)


def byrdway_csv(rows):
    head = ",".join(BYRDWAY_COLUMNS)
    return head + "\n" + "\n".join(",".join(r) for r in rows) + "\n"


class TestBridge(unittest.TestCase):
    ROWS = [["TPT", "T1", "2026-11-02", "2026-11-05", "USD", "1000.00", "200.00", "0.00", "800.00", "tpt-report-nov", "VERIFIED"],
            ["TPT", "T2", "2026-11-03", "", "USD", "59.00", "11.80", "0.00", "47.20", "", "PENDING"],
            ["STRIPE", "ch_1", "2026-11-04", "2026-11-06", "USD", "100.00", "3.20", "0.00", "96.80", "stripe-payout-1", "VERIFIED"]]

    def setUp(self):
        self.s = mem(); self.b = Bridge(self.s)

    def test_no_verified_revenue_means_no_proposal(self):
        signed(self.s)
        r = self.b.propose()
        self.assertEqual(r["status"], "NO_PROPOSAL")
        self.assertEqual(r["reason"], "NO_VERIFIED_REVENUE")

    def test_only_verified_rows_and_arithmetic_checked(self):
        r = self.b.import_byrdway_proceeds(byrdway_csv(self.ROWS), "proceeds.csv")
        self.assertEqual((r["added"], r["unverified_skipped"]), (2, 1))
        bad = [["TPT", "T9", "2026-11-02", "", "USD", "100", "10", "0", "95", "x", "VERIFIED"]]
        r = self.b.import_byrdway_proceeds(byrdway_csv(bad), "bad.csv")
        self.assertEqual(r["added"], 0); self.assertEqual(len(r["errors"]), 1)

    def test_duplicates_rejected(self):
        self.b.import_byrdway_proceeds(byrdway_csv(self.ROWS), "a.csv")
        r = self.b.import_byrdway_proceeds(byrdway_csv(self.ROWS), "a.csv")
        self.assertEqual(r["duplicates_rejected"], 2)
        self.assertTrue(Control(self.s).open_exceptions("IMMEDIATE"))

    def test_available_cash_respects_expenses_tax_reserve_and_ceiling(self):
        signed(self.s)
        self.b.import_byrdway_proceeds(byrdway_csv(self.ROWS), "a.csv")  # 896.80 verified
        self.b.record_business_expense("100", "software", "EXP-1", "2026-11-05")
        av = self.b.available_cash()
        # profit 796.80; tax 30% = 239.04; reserve 500 -> 57.76
        self.assertEqual(av["available_for_investment"], "57.76")
        p = self.b.propose(requested="1000")
        self.assertEqual(p["amount"], "57.76"); self.assertIn("available_cash", p["limited_by"])

    def test_personal_account_requires_recorded_distribution_and_deposit_matching(self):
        signed(self.s)
        self.b.import_byrdway_proceeds(byrdway_csv(self.ROWS), "a.csv")
        p = self.b.propose(requested="40")
        with self.assertRaises(BridgeError):
            self.b.authorize(p["id"])
        with self.assertRaises(BridgeError):
            self.b.record_owner_distribution("40", "draw", "D1", "2026-11-10")  # treatment too vague
        self.b.record_owner_distribution("40", "Member distribution, single-member LLC, per CPA", "D1", "2026-11-10")
        a = self.b.authorize(p["id"], distribution_external_id="D1")
        self.assertEqual(a["status"], "AUTHORIZED")
        today = date.today().isoformat()
        m = self.b.match_deposits([{"ref": "DEP-1", "amount": "40.00", "date": today}, {"ref": "DEP-2", "amount": "13.00", "date": today}])
        self.assertEqual(len(m["matched"]), 1); self.assertEqual(len(m["unexpected"]), 1)
        again = self.b.match_deposits([{"ref": "DEP-1", "amount": "40.00", "date": today}])
        self.assertEqual(again["matched"], [])  # idempotent

    def test_reads_byrdway_studio_ledger_read_only(self):
        import os, tempfile
        rows = [{"date": "2026-11-10", "product": "Algebra 1", "units": 1, "gross": 29.99, "fees": 6.0, "refund": 0, "buyer": "o1",
                 "test": False, "source": "TpT sales report", "raw": {"Order": "o1"}},
                {"date": "2026-11-10", "product": "TEST order", "units": 1, "gross": 59.0, "fees": 0, "refund": 0, "buyer": "t",
                 "test": True, "source": "TpT sales report", "raw": {"Order": "TEST"}}]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "ledger.json")
            open(p, "w").write(json.dumps(rows))
            before = open(p).read()
            r = self.b.import_studio_ledger(p)
            self.assertEqual((r["added"], r["test_rows_excluded"]), (1, 1))
            self.assertEqual(self.b.available_cash()["verified_seller_proceeds"], "23.99")
            self.assertEqual(self.b.import_studio_ledger(p)["already_imported"], 1)
            self.assertEqual(open(p).read(), before)  # Studio's file is never modified
        self.assertEqual(self.b.import_studio_ledger("/nonexistent/ledger.json")["status"], "NOT_FOUND")

    def test_breaker_blocks_proposals(self):
        signed(self.s)
        Control(self.s).trip("reconciliation_failed", "test")
        with self.assertRaises(BreakerOpen):
            self.b.propose()


class TestControl(unittest.TestCase):
    def test_exceptions_deduplicated_and_immediate_notified(self):
        s = mem(); sent = []
        c = Control(s, notifier=lambda t, b: sent.append(b) or True)
        a = c.raise_exception("credentials_compromised", "x"); b = c.raise_exception("credentials_compromised", "x")
        self.assertTrue(b["duplicate"]); self.assertEqual(len(sent), 1)
        c.raise_exception("allocation_drift", "y")
        self.assertEqual(len(sent), 1)  # weekly items don't interrupt the owner

    def test_breaker_trip_reset_never_touches_orders(self):
        s = mem(); c = Control(s)
        wf = c.trip("duplicate_transaction", "dup")
        self.assertIn("contribution_proposals", wf)
        ev = s.events(kind="BREAKER_TRIPPED")[0]["payload"]
        self.assertEqual(ev["brokerage_orders_created"], 0)
        with self.assertRaises(PermissionError):
            c.reset("contribution_proposals", owner="agent:risk")
        c.reset("contribution_proposals", note="checked")
        self.assertIsNone(c.is_open("contribution_proposals"))


class TestSchedulerAndReports(unittest.TestCase):
    def test_idempotent_daily_jobs(self):
        s = mem(); sch = Scheduler(s)
        now = datetime(2026, 11, 13, 12, tzinfo=timezone.utc)
        r1 = sch.run_due(now); r2 = sch.run_due(now)
        self.assertTrue(all(x["status"] in ("DONE", "FAILED") for x in r1))
        self.assertTrue(all(x["status"] in ("ALREADY_DONE", "DONE", "FAILED") for x in r2))
        self.assertEqual([x for x in r1 if x["status"] == "FAILED"], [], [x.get("result") for x in r1 if x["status"] == "FAILED"])

    def test_interrupted_job_recovered_and_rerun(self):
        s = mem(); sch = Scheduler(s)
        old = "2026-11-13T00:00:00+00:00"
        s.conn.execute("INSERT INTO job_runs (job, period_key, started_ts, heartbeat_ts, status, attempt) VALUES "
                       "('valuation_snapshot','2026-11-13',?,?, 'RUNNING', 1)", (old, old))
        out = sch.run_due(datetime(2026, 11, 13, 12, tzinfo=timezone.utc))
        v = next(x for x in out if x["job"] == "valuation_snapshot")
        self.assertEqual(v["status"], "DONE")
        self.assertTrue(s.events(kind="JOB_INTERRUPTED_RECOVERED"))
        self.assertEqual(s.conn.execute("SELECT attempt FROM job_runs WHERE status='DONE' AND job='valuation_snapshot'").fetchone()[0], 2)

    def test_weekly_report_twelve_items_excludes_deposits(self):
        s = mem(); led = Ledgers(s); pf = Portfolio(s)
        Scheduler(s).run_job("valuation_snapshot", __import__("gci.ops", fromlist=["x"]).job_valuation_snapshot, "d0",
                             datetime.now(timezone.utc) - timedelta(days=8))
        s.conn.execute("UPDATE valuation_snapshots SET as_of=?", ((date.today() - timedelta(days=8)).isoformat(),))
        led.post("A", "CONTRIBUTION", "100", "new money this week")
        pf.record_income("DIVIDEND", "0.50", "VT")
        r = weekly_report(s, date.today())
        for k in ("1_opening_balance", "2_closing_balance", "3_contributions", "4_realized_gains_losses", "5_unrealized_gains_losses",
                  "6_dividends_interest", "7_fees", "7_research_expenses", "8_net_performance_excluding_deposits", "9_allocation",
                  "10_material_risks", "11_next_contribution", "12_exceptions_requiring_owner_action"):
            self.assertIn(k, r)
        self.assertEqual(r["3_contributions"], "100.00")
        self.assertEqual(r["8_net_performance_excluding_deposits"]["dollars"], "0.50")  # the $100 deposit is not performance

    def test_recurring_monitor_detects_missing_and_over_ceiling(self):
        s = mem(); signed(s); led = Ledgers(s); pf = Portfolio(s)
        led.post("A", "CONTRIBUTION", "500")
        pf.record_buy("VT", "0.12841", "155.75", ts="2026-11-20")
        r = recurring_status(s, datetime(2026, 12, 30, tzinfo=timezone.utc))
        st = {(x["date"], x["symbol"]): x["status"] for x in r["schedule"]}
        self.assertEqual(st[("2026-11-20", "VT")], "FILLED")
        self.assertEqual(st[("2026-11-20", "SGOV")], "MISSING")
        pf.record_buy("VTI", "0.5", "372.62", ts="2026-12-02")  # $186 > $100 ceiling, outside plan
        r = recurring_status(s, datetime(2026, 12, 30, tzinfo=timezone.utc))
        self.assertEqual(r["status"], "OVER_CEILING")
        self.assertTrue(r["unexpected_purchases"])


class TestShadowAndSecurity(unittest.TestCase):
    def test_cannot_activate_until_all_checks_pass(self):
        s = mem(); sm = ShadowMode(s)
        self.assertEqual(sm.mode(), "SHADOW")
        with self.assertRaises(PermissionError):
            sm.activate()
        e = sm.evaluate()
        self.assertFalse(e["all_passed"])
        self.assertEqual(len(e["checks"]), 10)

    def test_security_incidents_block_activation_until_rotation_confirmed(self):
        s = mem()
        self.assertEqual(sync_known_exposures(s), 4)
        Scheduler(s).run_job("security_health", __import__("gci.ops", fromlist=["x"]).job_security_health, "d1")
        self.assertTrue(Control(s).is_open("live_activation"))
        with self.assertRaises(ValueError):
            confirm_rotation(s, "SEC-2026-001", "done")
        for i in range(1, 5):
            confirm_rotation(s, f"SEC-2026-00{i}", "Revoked old token and issued a new one stored in n8n credentials")
        self.assertEqual(s.conn.execute("SELECT COUNT(*) FROM security_incidents WHERE status='OPEN'").fetchone()[0], 0)

    def test_no_secret_values_in_exposure_registry(self):
        from gci.security import scan_for_secrets
        from pathlib import Path
        self.assertEqual(scan_for_secrets(Path(__file__).resolve().parent.parent / "data"), [])


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(__import__("os").name == "nt", "Windows DPAPI only")
class TestWindowsOnly(unittest.TestCase):
    def test_dpapi_roundtrip_no_plaintext(self):
        import os, tempfile
        from gci.security import CredentialStore
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "creds.json")
            cs = CredentialStore(p)
            cs.put("market_data_api_key", "example-not-a-real-key-123456")
            self.assertEqual(cs.get("market_data_api_key"), "example-not-a-real-key-123456")
            self.assertNotIn("example-not-a-real-key", open(p).read())
            cs.revoke("market_data_api_key")
            self.assertIsNone(cs.get("market_data_api_key"))
