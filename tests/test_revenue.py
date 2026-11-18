"""Revenue intake (KDP/Audible, Stripe) and the growth ceiling. ALL RECORDS ARE SYNTHETIC TEST DATA."""
import io
import json
import unittest
from datetime import date, timedelta

from gci.bridge import Bridge
from gci.control import Control
from gci.db import Store
from gci.ips import InvestmentPolicy, validate
from gci.marketdata import load_snapshot
from gci.ops import job_growth_check
from gci.revenue import import_kdp_payments, sync_stripe_payouts, check_stripe_key
from tests.test_operations import policy, ACK

T = (date.today() - timedelta(days=5)).strftime("%m/%d/%Y")
KDP = ("Payment Number,Marketplace,Payment Status,Payment Date,Payment Method,Net Earnings,FX Rate,Payout Amount,Sales Period,Accrued Royalty,Tax Withholding,Source\n"
       f"P1,Amazon.com,Paid,{T},EFT,412.50,N/A,412.50,2026-09,412.50,0,eBook\n"
       f"P1,Amazon.com,Paid,{T},EFT,87.50,N/A,87.50,2026-09,87.50,0,Audiobook - Audible\n"
       f"P2,Amazon.co.uk,Paid,{T},EFT,20.00,1.27,Pending,2026-09,20.00,0,eBook\n"
       f"P3,Amazon.de,Failed,{T},EFT,10.00,1.08,10.80,2026-09,10.00,0,eBook\n")


def mem():
    s = Store.open(":memory:", "SYNTHETIC"); Control(s).notify = lambda t, b: True; return s


class TestKDP(unittest.TestCase):
    def test_only_paid_count_and_audiobooks_split(self):
        s = mem()
        r = import_kdp_payments(s, KDP, "kdp.csv")
        self.assertEqual((r["added"], r["pending_skipped"], r["failed_skipped"]), (2, 1, 1))
        self.assertEqual(r["by_source"], {"Books": "412.50", "Audiobooks": "87.50"})
        self.assertEqual(Bridge(s).available_cash()["verified_seller_proceeds"], "500.00")
        self.assertEqual(import_kdp_payments(s, KDP, "kdp.csv")["duplicates"], 2)

    def test_rejects_wrong_report(self):
        with self.assertRaises(Exception):
            import_kdp_payments(mem(), "Title,Units\nBook,3\n", "royalties_estimator.csv")


class FakeStripe:
    def __init__(self, pages): self.pages, self.calls = pages, []
    def __call__(self, req, timeout):
        self.calls.append(req)
        body = json.dumps(self.pages[len(self.calls) - 1]).encode()
        class R:
            def __enter__(s): return s
            def __exit__(s, *a): return False
            def read(s): return body
        return R()


class TestStripe(unittest.TestCase):
    def test_full_secret_key_refused(self):
        for bad in ("sk_live_x", "sk_test_x", "", "pk_live_x"):
            with self.assertRaises(PermissionError):
                check_stripe_key(bad)
        check_stripe_key("rk_live_abc")

    def test_paid_payouts_only_paginated_idempotent(self):
        s = mem()
        from datetime import datetime, timezone
        ts = int(datetime.combine(date.today() - timedelta(days=3), datetime.min.time(), tzinfo=timezone.utc).timestamp())
        pages = [{"has_more": True, "data": [{"id": "po_1", "status": "paid", "amount": 12345, "currency": "usd", "arrival_date": ts}]},
                 {"has_more": False, "data": [{"id": "po_2", "status": "paid", "amount": 5000, "currency": "usd", "arrival_date": ts},
                                              {"id": "po_3", "status": "pending", "amount": 999, "currency": "usd", "arrival_date": ts}]}]
        fake = FakeStripe(pages)
        r = sync_stripe_payouts(s, "rk_test_abc", opener=fake)
        self.assertEqual(r["added"], 2)
        self.assertIn("starting_after=po_1", fake.calls[1].full_url)
        self.assertEqual(Bridge(s).available_cash()["verified_seller_proceeds"], "173.45")
        self.assertEqual(sync_stripe_payouts(s, "rk_test_abc", opener=FakeStripe(pages))["already_imported"], 2)


class TestGrowthCeiling(unittest.TestCase):
    def pol(self, share="0.30", cap="2000"):
        p = policy()
        p["contribution_rule"] = {"type": "base_plus_share_of_verified_net", "share_of_after_tax_net": share,
                                  "hard_cap": cap, "lookback_days": 30}
        return p

    def test_rule_validation(self):
        snap = load_snapshot()
        self.assertEqual(validate(self.pol(), snap), [])
        self.assertTrue(validate(self.pol(share="1.5"), snap))
        self.assertTrue(validate(self.pol(cap="50"), snap))  # cap below the $100 base

    def test_ceiling_grows_only_with_verified_recent_profit_and_is_capped(self):
        s = mem(); ip = InvestmentPolicy(s); v = ip.save_draft(self.pol()); ip.sign(v, acknowledgement=ACK)
        b = Bridge(s)
        self.assertEqual(b.effective_ceiling()["ceiling"], "100.00")           # no verified revenue yet
        import_kdp_payments(s, KDP, "kdp.csv")                                  # $500 paid, 5 days ago
        # 500 net x (1 - 30% tax) x 30% = 105 → 100 + 105 = 205
        self.assertEqual(b.effective_ceiling()["ceiling"], "205.00")
        b.record_business_expense("200", "ads", "E1", (date.today() - timedelta(days=2)).isoformat())
        self.assertEqual(b.effective_ceiling()["ceiling"], "163.00")           # (500-200) x .7 x .3 = 63
        self.assertEqual(b.effective_ceiling(today=date.today() + timedelta(days=40))["ceiling"], "100.00")  # old revenue ages out
        s2 = mem(); ip2 = InvestmentPolicy(s2); v2 = ip2.save_draft(self.pol(cap="150")); ip2.sign(v2, acknowledgement=ACK)
        import_kdp_payments(s2, KDP, "kdp.csv")
        self.assertEqual(Bridge(s2).effective_ceiling()["ceiling"], "150.00")  # hard cap holds

    def test_growth_check_tells_owner_to_raise_autoinvest(self):
        s = mem(); ip = InvestmentPolicy(s); v = ip.save_draft(self.pol()); ip.sign(v, acknowledgement=ACK)
        import_kdp_payments(s, KDP, "kdp.csv")
        r = job_growth_check(s, None)
        self.assertEqual(r["room"], "165.00")  # ceiling 205 - planned 40
        msgs = [e["message"] for e in Control(s).open_exceptions("WEEKLY")]
        self.assertTrue(any("raise the Autoinvest amounts in the Chase app" in m for m in msgs))


if __name__ == "__main__":
    unittest.main()
