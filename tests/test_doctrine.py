"""Doctrine Library and Council tests. Market evidence = real dated snapshot; owner profiles are SYNTHETIC."""
import copy
import unittest

from gci.agents import auditor
from gci.db import Store
from gci.doctrine import load_library, council, run_lenses, validate_citations, LENS_RULES, ROLE_LENSES, POLICY_BLOCKED
from gci.marketdata import load_snapshot
from gci.service import PROPOSALS, choose_allocation, analyze_starter_allocation

OWNER = {"horizon_years": 10, "emergency_fund_ok": True}
REQUIRED_NAMES = ["Warren Buffett", "Charlie Munger", "Benjamin Graham", "Peter Lynch", "John Bogle", "Philip Fisher",
                  "Howard Marks", "Seth Klarman", "Li Lu", "Mohnish Pabrai", "Rakesh Jhunjhunwala", "Radhakishan Damani",
                  "Walter Schloss", "Sir John Templeton", "Anthony Bolton", "Terry Smith", "Francisco García Paramés",
                  "Akira Mori", "Jim Simons", "Ray Dalio", "George Soros", "Stanley Druckenmiller", "David Tepper",
                  "Ken Griffin", "Cliff Asness", "Israel Englander", "Paul Tudor Jones", "Michael Steinhardt", "Bruce Kovner",
                  "Louis Bacon", "David E. Shaw", "John Overdeck and David Siegel", "Michael Platt", "Alan Howard",
                  "Chris Hohn", "Bill Ackman", "Masayoshi Son", "Nicolai Tangen", "Edward O. Thorp",
                  "Pierre Andurand", "Steve Cohen", "Michael Burry", "John Paulson"]


class TestLibrary(unittest.TestCase):
    def setUp(self):
        self.lib = load_library()

    def test_all_requested_investors_present_and_complete(self):
        names = {i["name"] for i in self.lib["investors"]}
        self.assertEqual(set(REQUIRED_NAMES) - names, set())
        for i in self.lib["investors"]:
            self.assertTrue(i["principles"] and i["sources"], i["id"])
            self.assertIn(i["small_capital"], ("APPLICABLE", "PARTIAL", "STUDY_ONLY"))
            self.assertIn(i["source_quality"], ("primary", "secondary", "limited"))
            for p in i["principles"]:
                self.assertIn(p["lens"], LENS_RULES, (i["id"], p["lens"]))

    def test_every_investor_has_all_ten_required_attributes(self):
        from gci.doctrine import profile, PROFILE_FIELDS
        for i in self.lib["investors"]:
            p = profile(i, self.lib)
            for f in PROFILE_FIELDS:
                self.assertTrue(p[f], (i["id"], f))

    def test_original_39_preserved(self):
        self.assertGreaterEqual(len(self.lib["investors"]), 43)
        self.assertIn("buffett", {i["id"] for i in self.lib["investors"]})

    def test_policy_blocked_doctrines_are_not_actionable(self):
        for i in self.lib["investors"]:
            if set(i["requires"]) & {"concentration", "activism", "private_markets"} and not i["school"] == "macro":
                self.assertIn(i["small_capital"], ("STUDY_ONLY", "PARTIAL"), i["id"])

    def test_every_lens_has_a_rule_and_every_role_maps_to_lenses(self):
        used = {p["lens"] for i in self.lib["investors"] for p in i["principles"]}
        self.assertEqual(used - set(LENS_RULES), set())
        for role in ("market_intel", "research", "risk", "compounding", "judgment", "auditor"):
            self.assertTrue(set(ROLE_LENSES[role]) <= set(LENS_RULES))


class TestCouncil(unittest.TestCase):
    def setUp(self):
        self.snap = load_snapshot()

    def test_real_disagreement_is_surfaced(self):
        c = council(PROPOSALS["ALL_EQUITY"], self.snap, OWNER)
        self.assertTrue(c["tally_by_distinct_lens"]["SUPPORT"])
        self.assertTrue(c["tally_by_distinct_lens"]["CHALLENGE"])
        lenses = {d["challenge_lens"] for d in c["school_conflicts"]}
        self.assertIn("risk_streams", lenses)  # Dalio/Graham vs index school
        rs = next(d for d in c["school_conflicts"] if d["challenge_lens"] == "risk_streams")
        self.assertIn("index", rs["supporting_schools"])

    def test_fame_neutral_counting(self):
        """Adding ten more famous names to an existing lens must not change the evidence tally."""
        lib = load_library()
        base = council(PROPOSALS["ALL_EQUITY"], self.snap, OWNER, lib)
        lib2 = copy.deepcopy(lib)
        for n in range(10):
            lib2["investors"].append({"id": f"clone{n}", "name": f"Famous Clone {n}", "region": "x", "school": "index",
                                      "principles": [{"text": "low cost", "lens": "cost"}], "requires": [],
                                      "small_capital": "APPLICABLE", "source_quality": "secondary", "sources": ["x"]})
        more = council(PROPOSALS["ALL_EQUITY"], self.snap, OWNER, lib2)
        self.assertEqual(base["tally_by_distinct_lens"], more["tally_by_distinct_lens"])
        self.assertGreater(more["famous_name_counts_ignored_for_weighting"]["SUPPORT"],
                           base["famous_name_counts_ignored_for_weighting"]["SUPPORT"])

    def test_lenses_never_approve(self):
        for p in PROPOSALS.values():
            for r in run_lenses(p, self.snap, OWNER).values():
                self.assertIn(r["verdict"], ("SUPPORT", "CHALLENGE", "CAUTION", "NEUTRAL", "INSUFFICIENT_DATA", "NOT_APPLICABLE"))

    def test_margin_of_safety_math(self):
        r = run_lenses(PROPOSALS["ALL_EQUITY"], self.snap, OWNER)["margin_of_safety"]
        ey = 100 / 19.84
        self.assertAlmostEqual(r["derived"]["earnings_yield_pct"], round(ey, 2))
        self.assertAlmostEqual(r["derived"]["equity_premium_pp"], round(ey - 4.24, 2))
        self.assertEqual(r["verdict"], "CHALLENGE")

    def test_selection_rule_is_deterministic_and_preservation_first(self):
        a, b = choose_allocation(self.snap, OWNER), choose_allocation(self.snap, OWNER)
        self.assertEqual(a["pick"], b["pick"])
        self.assertEqual(a["pick"], "BARBELL")
        self.assertEqual(set(a["resolved_by_allocation"]), {"margin_of_safety", "risk_streams"})

    def test_rich_equity_premium_keeps_all_equity(self):
        snap = copy.deepcopy(self.snap)
        for c in snap["candidates"]:
            if c["symbol"] == "VT":
                c["trailing_pe"] = 10.0  # 10% earnings yield → premium > 3pp
        self.assertEqual(run_lenses(PROPOSALS["ALL_EQUITY"], snap, OWNER)["margin_of_safety"]["verdict"], "SUPPORT")
        rich = choose_allocation(snap, OWNER)
        self.assertEqual(rich["pick"], "EQ80")  # highest share without a preservation challenge; 100% is still one stream
        thin = choose_allocation(self.snap, OWNER)
        self.assertGreater(PROPOSALS[rich["pick"]]["equity_weight"], PROPOSALS[thin["pick"]]["equity_weight"])

    def test_owner_facts_change_verdicts(self):
        r = run_lenses(PROPOSALS["ALL_EQUITY"], self.snap, {"horizon_years": 2, "emergency_fund_ok": False,
                                                            "max_loss_tolerance_pct": 10})
        self.assertEqual(r["horizon"]["verdict"], "CHALLENGE")
        self.assertEqual(r["inversion"]["verdict"], "CHALLENGE")
        self.assertEqual(r["capital_preservation"]["verdict"], "CHALLENGE")
        self.assertEqual(run_lenses(PROPOSALS["ALL_EQUITY"], self.snap, {})["horizon"]["verdict"], "INSUFFICIENT_DATA")

    def test_active_bets_without_edge_are_challenged(self):
        p = dict(PROPOSALS["ALL_EQUITY"], active=True)
        r = run_lenses(p, self.snap, OWNER)
        self.assertEqual(r["edge"]["verdict"], "CHALLENGE")
        self.assertEqual(r["sizing"]["verdict"], "CHALLENGE")


class TestIntegration(unittest.TestCase):
    def test_every_challenge_answered_and_unresolved_become_rejection_conditions(self):
        s = Store.open(":memory:", "SYNTHETIC")
        r = analyze_starter_allocation(s, 40, OWNER)
        responses = {x["lens"] for x in r["job"]["judgment"]["doctrine_responses"]}
        self.assertTrue({c["lens"] for c in r["council"]["challenges"]} <= responses)
        r2 = analyze_starter_allocation(s, 40, {"horizon_years": 10, "emergency_fund_ok": True, "max_loss_tolerance_pct": 5})
        self.assertEqual(r2["choice"], "NO_ACTION")  # 5% tolerance: no equity mix fits, so hold T-bills
        snap = copy.deepcopy(load_snapshot())
        for c in snap["candidates"]:
            if c["symbol"] == "VT":
                c["price"] = "145.00"  # >2% below its 200-day average -> momentum CHALLENGE (not a preservation lens)
        r3 = analyze_starter_allocation(s, 40, OWNER, snap)
        self.assertTrue(any("momentum" in c for c in r3["card"]["rejection_conditions"]))
        self.assertTrue(r["job"]["auditor"]["certified"], r["job"]["auditor"]["issues"])
        for role in ("market_intel", "research", "risk", "auditor"):
            self.assertIn("doctrine_lenses", r["job"][role])

    def test_fabricated_attribution_rejected(self):
        self.assertTrue(validate_citations("Warren Buffett recommends buying VT now."))
        snap = load_snapshot()
        out = auditor({"evidence": snap, "thesis": "Ray Dalio endorses this allocation.",
                       "council": council(PROPOSALS["BARBELL"], snap, OWNER)}, {})
        self.assertFalse(out["certified"])

    def test_unknown_doctrine_source_rejected(self):
        c = council(PROPOSALS["BARBELL"], load_snapshot(), OWNER)
        c["investors"].append({"name": "Invented Guru", "principles": []})
        self.assertTrue(any("Invented Guru" in i for i in validate_citations(c)))


if __name__ == "__main__":
    unittest.main()
