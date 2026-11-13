"""Core financial engine tests. ALL RECORDS HERE ARE SYNTHETIC TEST DATA."""
import os
import sqlite3
import tempfile
import unittest
from decimal import Decimal as Dec

from gci.db import Store, DatasetMismatch
from gci.funding import Funding, BudgetSuspended
from gci.ledgers import Ledgers, LedgerError
from gci.matching import Matching
from gci.money import D
from gci.policy import PolicyViolation, refuse
from gci.portfolio import Portfolio, modified_dietz
from gci import viability

DAY = ("2000-01-01T00:00:00", "2999-12-31T23:59:59Z")


def mem():
    return Store.open(":memory:", "SYNTHETIC")


class TestPortfolio(unittest.TestCase):  # items 7, 8
    def setUp(self):
        self.s = mem(); self.led = Ledgers(self.s); self.pf = Portfolio(self.s)
        self.led.post("A", "CONTRIBUTION", "1000", "seed")

    def test_fifo_realized_and_unrealized(self):
        self.pf.record_buy("VT", "2", "100", "0", ts="2026-01-01")
        self.pf.record_buy("VT", "2", "150", "0", ts="2026-02-01")
        r = self.pf.record_sell("VT", "3", "200", "3")
        # FIFO: 2@100 + 1@150 = 350 basis; proceeds 600 - 3 fee = 597 -> gain 247
        self.assertEqual(r["realized_gain"].quantize(Dec("0.01")), Dec("247.00"))
        self.pf.set_price("VT", "160", "2026-03-01", "test")
        h = self.pf.holdings()[0]
        self.assertEqual(h["unrealized_gain"], "10.00")  # 1 share basis 150, value 160
        self.assertEqual(self.led.balance("A"), Dec("1000") - 200 - 300 + 597)

    def test_fractional_quantities_exact(self):
        self.pf.record_buy("VT", "0.25682", "155.75")
        self.assertEqual(self.pf.position("VT")["qty"], Dec("0.25682"))

    def test_no_short_selling(self):
        self.pf.record_buy("VT", "1", "100")
        with self.assertRaises(PolicyViolation):
            self.pf.record_sell("VT", "2", "100")

    def test_no_margin(self):
        with self.assertRaises(LedgerError):
            self.pf.record_buy("VT", "100", "100")  # $10,000 > $1,000 cash

    def test_contributions_not_returns(self):  # item 12
        self.pf.record_buy("VT", "1", "100")
        self.pf.set_price("VT", "100", "2026-01-01", "t")
        before = D(self.pf.summary()["investment_gain_total"])
        self.led.post("A", "CONTRIBUTION", "500", "new money")
        self.assertEqual(D(self.pf.summary()["investment_gain_total"]), before)

    def test_modified_dietz_excludes_deposit(self):
        # $10 grows to $20 only because of a $10 deposit -> 0% return, not 100%.
        self.assertEqual(modified_dietz(10, 20, [(0, 10)], 30), 0)


class TestLedgers(unittest.TestCase):  # items 10, 11, 22
    def setUp(self):
        self.s = mem(); self.led = Ledgers(self.s)
        self.led.post("A", "CONTRIBUTION", "100")

    def test_transfer_requires_authorization_and_is_single_use(self):
        with self.assertRaises(LedgerError):
            self.led.transfer("A", "C", "10", "AUTH-NOPE")
        a = self.led.authorize("TRANSFER:A->C", "10", {})
        self.led.transfer("A", "C", "10", a)
        with self.assertRaises(LedgerError):
            self.led.transfer("A", "C", "10", a)
        self.assertEqual(self.led.balance("C"), Dec("10"))
        self.assertTrue(self.led.reconcile_internal()["ok"])

    def test_authorization_amount_and_route_enforced(self):
        a = self.led.authorize("TRANSFER:A->C", "5", {})
        with self.assertRaises(LedgerError):
            self.led.transfer("A", "C", "6", a)
        b = self.led.authorize("TRANSFER:A->B", "5", {})
        with self.assertRaises(LedgerError):
            self.led.transfer("A", "C", "5", b)

    def test_reserve_release_requires_authorization(self):
        a = self.led.authorize("TRANSFER:A->C", "20", {})
        self.led.transfer("A", "C", "20", a)
        with self.assertRaises(LedgerError):
            self.led.post("C", "RESERVE_RELEASE", "5")
        r = self.led.authorize("C:RESERVE_RELEASE", "5", {})
        self.led.post("C", "RESERVE_RELEASE", "5", authorization_id=r)
        self.assertEqual(self.led.balance("C"), Dec("15"))

    def test_agents_cannot_authorize(self):
        with self.assertRaises(LedgerError):
            self.led.authorize("TRANSFER:A->B", "1", {}, owner="agent:research")

    def test_duplicate_transaction_rejected(self):
        self.led.post("A", "DIVIDEND", "1", external_id="X1")
        with self.assertRaises(LedgerError):
            self.led.post("A", "DIVIDEND", "1", external_id="X1")

    def test_entries_immutable(self):
        with self.assertRaises(sqlite3.DatabaseError):
            self.s.conn.execute("UPDATE ledger_entries SET amount='999'")
        with self.assertRaises(sqlite3.DatabaseError):
            self.s.conn.execute("DELETE FROM events")

    def test_negative_balance_blocked(self):
        with self.assertRaises(LedgerError):
            self.led.post("B", "SPEND", "1")


class TestFunding(unittest.TestCase):  # items 8, 9, 10
    def setUp(self):
        self.s = mem(); self.led = Ledgers(self.s); self.pf = Portfolio(self.s); self.f = Funding(self.s)
        self.led.post("A", "CONTRIBUTION", "1000")

    def test_unrealized_not_distributable(self):
        self.pf.record_buy("VT", "1", "100")
        self.pf.set_price("VT", "500", "2026-01-01", "t")  # huge unrealized gain
        c = self.f.certify(*DAY)
        self.assertEqual(D(c["eligible_net_gain"]), 0)
        self.assertEqual(D(c["proposed_research_allocation"]), 0)

    def test_research_allocation_math(self):
        self.pf.record_buy("VT", "1", "100")
        self.pf.record_sell("VT", "1", "200")  # +100 realized
        c = self.f.certify(*DAY)
        # 100 * (1 - 0.24) * 0.30 = 22.80
        self.assertEqual(c["proposed_research_allocation"], "22.80")
        self.assertFalse(c["research_share_owner_approved"])

    def test_loss_carryforward(self):
        self.pf.record_buy("VT", "1", "100", ts="2026-01-01")
        self.pf.record_sell("VT", "1", "60")  # -40
        c1 = self.f.certify("2000-01-01", "2500-01-01")
        self.assertEqual(c1["carryforward_after"], "-40.00")
        # later period +100 gain: eligible pre-tax should be 60
        self.s.conn.execute("UPDATE realized SET ts='2000-06-01'")  # keep first loss in first period
        self.pf.record_buy("VT", "1", "100")
        r = self.pf.record_sell("VT", "1", "200")
        self.s.conn.execute("UPDATE realized SET ts='2600-01-01' WHERE CAST(gain AS REAL) > 0")
        c2 = self.f.certify("2500-01-02", "2700-01-01")
        self.assertEqual(c2["carryforward_before"], "-40.00")
        self.assertEqual(D(c2["eligible_net_gain"]), D("60") * D("0.76"))

    def test_no_double_counting_periods(self):
        self.f.certify("2026-01-01", "2026-06-30")
        with self.assertRaises(LedgerError):
            self.f.certify("2026-06-01", "2026-12-31")

    def test_budget_ceiling_and_suspension(self):
        a = self.led.authorize("B:BUDGET_AUTHORIZED", "2", {})
        self.led.post("B", "BUDGET_AUTHORIZED", "2", authorization_id=a)
        self.f.spend("0.50", "job1")
        with self.assertRaises(LedgerError):
            self.f.spend("1.60", "job2")  # over budget (1.50 left), under cap? cap 1.00 -> rejected either way
        self.f.set_policy(per_job_cost_cap="5")
        with self.assertRaises(LedgerError):
            self.f.spend("1.60", "job3")
        self.f.spend("1.50", "job4")
        self.assertTrue(self.f.suspended())
        with self.assertRaises(BudgetSuspended):
            self.f.spend("0.01", "job5")

    def test_allocation_requires_owner_authorization(self):
        self.pf.record_buy("VT", "1", "100"); self.pf.record_sell("VT", "1", "200")
        c = self.f.certify(*DAY)
        with self.assertRaises(LedgerError):
            self.f.allocate_to_research(c["id"], "AUTH-FAKE")
        a = self.led.authorize("TRANSFER:A->B", c["proposed_research_allocation"], {})
        self.f.allocate_to_research(c["id"], a)
        self.assertEqual(self.f.available_budget(), Dec("22.80"))
        with self.assertRaises(LedgerError):  # already allocated
            self.f.allocate_to_research(c["id"], self.led.authorize("TRANSFER:A->B", "1", {}))


class TestMatching(unittest.TestCase):  # item 12
    def test_match_is_capital_and_capped(self):
        s = mem(); led = Ledgers(s); pf = Portfolio(s)
        led.post("A", "CONTRIBUTION", "100")
        pf.record_buy("VT", "1", "10"); pf.record_sell("VT", "1", "20")
        cert = Funding(s).certify(*DAY)
        m = Matching(s).propose(cert["id"], "1.0", owner_available_cash="12", owner_reserve_requirement="10")
        self.assertEqual(m["proposed_amount"], "2.00"); self.assertTrue(m["limited_by_capacity"])
        gain_before = pf.summary()["investment_gain_total"]
        Matching(s).confirm(m["id"], "2.00")
        self.assertEqual(pf.summary()["investment_gain_total"], gain_before)
        with self.assertRaises(LedgerError):
            Matching(s).confirm(m["id"], "2.00")


class TestViability(unittest.TestCase):  # items 5, 6
    base = {"symbol": "VT", "accessible_in_account": True, "fractional_supported": True, "min_investment": "5",
            "price": "155.75", "commission_per_trade": "0", "spread_bps": 5, "expense_ratio": "0.0006", "fx_cost_bps": 0}

    def test_viable(self):
        self.assertEqual(viability.assess(self.base, 40, 40)["classification"], "ECONOMICALLY VIABLE")

    def test_insufficient_information(self):
        c = dict(self.base); c["expense_ratio"] = None
        self.assertEqual(viability.assess(c, 40, 40)["classification"], "INSUFFICIENT INFORMATION")

    def test_commission_kills_small_position(self):
        c = dict(self.base); c["commission_per_trade"] = "20"
        self.assertEqual(viability.assess(c, 40, 100)["classification"], "DEFER")

    def test_whole_share_unaffordable(self):
        c = dict(self.base); c["fractional_supported"] = False
        self.assertEqual(viability.assess(c, 40, 40)["classification"], "DEFER")

    def test_currency_cost(self):
        c = dict(self.base); c["fx_cost_bps"] = 100  # 1% each way
        r = viability.assess(c, 40, 40)
        self.assertEqual(r["classification"], "DEFER")

    def test_prohibited_and_inaccessible(self):
        c = dict(self.base); c["symbol"] = "TQQQ"
        self.assertEqual(viability.assess(c, 40, 40)["classification"], "REJECT")
        c = dict(self.base); c["accessible_in_account"] = False
        self.assertEqual(viability.assess(c, 40, 40)["classification"], "REJECT")
        c = dict(self.base); c["market"] = "RU"
        self.assertEqual(viability.assess(c, 40, 40)["classification"], "REJECT")

    def test_insufficient_cash(self):
        self.assertEqual(viability.assess(self.base, 40, 30)["classification"], "REJECT")


class TestProhibitions(unittest.TestCase):  # item 28
    def test_refused_operations(self):
        for op in ("place_order", "withdraw", "external_transfer", "enable_margin", "store_bank_password"):
            with self.assertRaises(PolicyViolation):
                refuse(op)

    def test_prohibited_instruments(self):
        s = mem(); Ledgers(s).post("A", "CONTRIBUTION", "100"); pf = Portfolio(s)
        for inst in ({"symbol": "SQQQ"}, {"symbol": "X", "option": True}, {"symbol": "BTC", "asset_type": "crypto"}):
            with self.assertRaises(PolicyViolation):
                pf.record_buy(inst["symbol"], "1", "1", instrument=inst)

    def test_no_order_placement_code_path(self):
        import gci, pathlib, re
        src = "".join(p.read_text() for p in pathlib.Path(gci.__file__).parent.rglob("*.py"))
        self.assertIsNone(re.search(r"def\s+place_order|submit_order|requests\.post\(.*order", src))


class TestDatasetSeparation(unittest.TestCase):
    def test_real_and_synthetic_never_mix(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.db")
            Store.open(p, "SYNTHETIC").close()
            with self.assertRaises(DatasetMismatch):
                Store.open(p, "REAL")


if __name__ == "__main__":
    unittest.main()
