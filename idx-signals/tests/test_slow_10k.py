import importlib.util
import sys
import unittest
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

S10 = Path(__file__).resolve().parents[1] / "research" / "SLOW_10K"


def load(name):
    if str(S10) not in sys.path:
        sys.path.insert(0, str(S10))
    spec = importlib.util.spec_from_file_location(f"slow10k_{name}", S10 / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TextTests(unittest.TestCase):
    def setUp(self):
        self.lib = load("tenk_lib")

    def test_hidden_header_scripts_and_tags_do_not_count(self):
        html = (b"<html><ix:header><ix:hidden>secret hidden words</ix:hidden></ix:header><style>.x{color:red}</style><script>var alpha=1;</script>"
                b"<body><p>Risk &amp; Reward: the Company may lose money.</p><td>12,345 USD</td></body></html>")
        tf = self.lib.tf_from_html(html)
        self.assertEqual(tf["secret"], 0)
        self.assertEqual(tf["color"], 0)
        self.assertEqual(tf["alpha"], 0)
        self.assertEqual(tf["risk"], 1)
        self.assertEqual(tf["company"], 1)
        self.assertEqual(tf["usd"], 1)
        self.assertNotIn("12", tf)

    def test_cosine_identical_orthogonal_and_scaled(self):
        a = Counter({"alpha": 3, "beta": 4})
        self.assertAlmostEqual(self.lib.cosine(a, a), 1.0)
        self.assertAlmostEqual(self.lib.cosine(a, Counter({"gamma": 5})), 0.0)
        self.assertAlmostEqual(self.lib.cosine(a, Counter({"alpha": 6, "beta": 8})), 1.0)         # same direction, twice the length
        self.assertTrue(np.isnan(self.lib.cosine(a, Counter())))

    def test_the_previous_filing_is_the_one_300_to_450_days_earlier_closest_to_a_year(self):
        d = pd.Timestamp("2022-03-01")
        earlier = [{"accession": "a", "filing_date": pd.Timestamp("2021-03-05")}, {"accession": "b", "filing_date": pd.Timestamp("2021-10-01")},
                   {"accession": "c", "filing_date": pd.Timestamp("2020-12-01")}, {"accession": "d", "filing_date": pd.Timestamp("2021-02-20")}]
        self.assertEqual(self.lib.choose_previous(d, earlier)["accession"], "a")                   # 361 days beats 369
        self.assertIsNone(self.lib.choose_previous(d, [earlier[1], earlier[2]]))                    # 151 and 455 days
        self.assertIsNone(self.lib.choose_previous(d, []))


class BucketTests(unittest.TestCase):
    def setUp(self):
        self.lib = load("tenk_lib")

    def frame(self, n=400, seed=0):
        rng = np.random.default_rng(seed)
        dates = pd.Timestamp("2021-01-01") + pd.to_timedelta(np.sort(rng.integers(0, 365, n)), unit="D")
        return pd.DataFrame({"filing_date": dates, "cosine": rng.uniform(0.5, 1.0, n)})

    def test_a_filing_is_compared_only_with_strictly_earlier_filings(self):
        f = self.frame()
        b1 = self.lib.buckets(f)
        later = f.copy()
        later.loc[len(later) - 1, "cosine"] = 0.0                       # change the LAST filing only
        b2 = self.lib.buckets(later)
        self.assertTrue((b1.iloc[:-1] == b2.iloc[:-1]).all())           # nobody earlier is affected by a later filing
        self.assertEqual(b2.iloc[-1] in ("Q1", ""), True)

    def test_needs_200_earlier_filings_and_uses_the_20th_and_80th_percentile(self):
        f = self.frame(600)
        b = self.lib.buckets(f)
        first_classified = int(np.flatnonzero(b.to_numpy() != "")[0])
        self.assertGreaterEqual(first_classified, 200)
        share = b[b != ""].value_counts(normalize=True)
        self.assertAlmostEqual(share["Q1"], 0.2, delta=0.06)
        self.assertAlmostEqual(share["Q5"], 0.2, delta=0.06)

    def test_a_filing_dated_the_same_day_does_not_inform_another(self):
        f = pd.DataFrame({"filing_date": [pd.Timestamp("2021-06-01")] * 300, "cosine": np.linspace(0.5, 1.0, 300)})
        self.assertTrue((self.lib.buckets(f) == "").all())              # nobody has 200 strictly earlier filings


class EventTableTests(unittest.TestCase):
    def test_q1_and_q5_agree_between_the_three_and_five_way_buckets_and_stages_follow_the_filing_date(self):
        be = load("build_events")
        rng = np.random.default_rng(1)
        n = 1500
        dates = pd.Timestamp("2019-06-01") + pd.to_timedelta(np.sort(rng.integers(0, 1700, n)), unit="D")
        sim = pd.DataFrame({"ticker": [f"T{i}" for i in range(n)], "cik": range(n), "accession": [f"a{i}" for i in range(n)],
                            "filing_date": dates.strftime("%Y-%m-%d"), "http_status": 200, "cosine": rng.uniform(0.5, 1, n),
                            "length_ratio": 1.0, "n_tokens": 1000, "gap_days": 365})
        ev = be.build(sim)
        self.assertTrue(set(ev.stage) <= {1, 2})
        self.assertTrue(ev[ev.stage == 1].public_date.between("2021-01-04", "2022-12-30").all())
        self.assertTrue(ev[ev.stage == 2].public_date.between("2023-01-03", "2023-09-29").all())
        self.assertTrue(set(ev.quintile) <= {"Q1", "Q2", "Q3", "Q4", "Q5"})
        self.assertFalse((ev.bucket == "").any())
        failed = sim.copy()
        failed.loc[:100, "http_status"] = 404
        self.assertLess(len(be.build(failed)), len(ev) + 1)                                         # failed downloads are never events


class StatsTests(unittest.TestCase):
    def setUp(self):
        self.st = load("tenk_stats")
        rng = np.random.default_rng(4)
        n = 3000
        self.f = pd.DataFrame({
            "bucket": rng.choice(["Q1", "MID", "Q5"], n, p=[0.2, 0.6, 0.2]),
            "public_date": pd.Timestamp("2021-01-04") + pd.to_timedelta(rng.integers(0, 700, n), unit="D"),
            "excess": rng.normal(0, 0.25, n), "net_return": rng.normal(0, 0.25, n), "control_mean": rng.normal(0, 0.1, n)})
        self.f["entry_date"] = (self.f.public_date + pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
        self.f["public_date"] = self.f.public_date.dt.strftime("%Y-%m-%d")

    def boot(self, f):
        return self.st.Boot(self.st.week_id(f.entry_date), resamples=4000, seed=1)

    def test_the_bootstrap_se_matches_the_analytic_cluster_se_for_a_mean(self):
        f = self.f
        b = self.boot(f)
        r = b.mean(f.excess, self.st.week_id(f.entry_date))
        w = self.st.week_id(f.entry_date)
        mu = f.excess.mean()
        by = pd.Series(f.excess.to_numpy() - mu).groupby(w).sum()
        analytic = np.sqrt((by ** 2).sum()) / len(f)
        self.assertAlmostEqual(r["se"], analytic, delta=0.12 * analytic)

    def test_a_planted_spread_is_found_and_none_is_not(self):
        f = self.f.copy()
        f.loc[f.bucket == "Q5", "excess"] += 0.06
        b = self.boot(f)
        q5, q1 = self.st.scored_sets(f)
        sp = b.spread(q5.excess, self.st.week_id(q5.entry_date), q1.excess, self.st.week_id(q1.entry_date))
        self.assertGreater(sp["spread"], 0.04)
        self.assertGreater(sp["t"], 3.0)
        null = self.f
        q5, q1 = self.st.scored_sets(null)
        sp0 = self.boot(null).spread(q5.excess, self.st.week_id(q5.entry_date), q1.excess, self.st.week_id(q1.entry_date))
        self.assertLess(abs(sp0["t"]), 3.0)

    def test_shuffled_labels_give_no_spread_even_when_one_is_planted(self):
        f = self.f.copy()
        f.loc[f.bucket == "Q5", "excess"] += 0.06
        ts = self.st.shuffle_check(f, self.boot(f), k=10)
        self.assertEqual(len(ts), 10)
        self.assertLess(max(abs(x) for x in ts), 3.0)

    def test_gates_need_every_condition(self):
        f = self.f.copy()
        f.loc[f.bucket == "Q5", "excess"] += 0.08
        sp = {"spread": 0.08, "t": 4.0}
        g, yr = self.st.stage1_gates(f, sp, [1.0, -2.0])
        self.assertTrue(all(g.values()), g)
        self.assertFalse(self.st.stage1_gates(f, {"spread": 0.025, "t": 4.0}, [1.0])[0]["G2_spread_ge_3pct"])
        self.assertFalse(self.st.stage1_gates(f, {"spread": 0.08, "t": 2.9}, [1.0])[0]["G1_spread_t_ge_3"])
        self.assertFalse(self.st.stage1_gates(f, sp, [1.0, 3.1])[0]["G4_shuffled_labels_all_abs_t_lt_3"])
        bad = f.copy()
        bad.loc[(bad.bucket == "Q5") & (bad.entry_date.str[:4] == "2022"), "excess"] -= 0.5
        self.assertFalse(self.st.stage1_gates(bad, sp, [1.0])[0]["G3_spread_gt_0_in_2021_and_2022"])
        self.assertEqual(self.st.stage1_reading({"a": False}, {"spread": 0.01, "t": 1.6}), "LEAN_WITHOUT_SIZE: no stage 2")
        self.assertEqual(self.st.stage1_reading({"a": False}, {"spread": -0.01, "t": -1.0}), "NO_LARGE_EFFECT: no stage 2")
        self.assertEqual(self.st.stage1_reading({"a": True}, sp), "STAGE1_PASS: run stage 2")
        self.assertEqual(self.st.stage2_reading(self.st.stage2_gates({"spread": 0.02, "t": 2.0})), "LARGE_PERSISTENT_EFFECT")
        self.assertEqual(self.st.stage2_reading(self.st.stage2_gates({"spread": 0.01, "t": 2.0})), "DID_NOT_PERSIST")


class ComputeTests(unittest.TestCase):
    """run.compute on a synthetic US panel: a planted advantage of the Q5 names shows as a positive spread, and no-drift labels do not."""

    @classmethod
    def setUpClass(cls):
        from tests.test_event_study import us_panel
        from idxsig import event_study as es
        cls.es = es
        cls.runmod = load("run")
        cls.df = us_panel(n_tickers=300, n_sessions=330, seed=11, drift={i: 0.004 for i in range(0, 300, 2)}, start="2021-01-04")
        dates = sorted(cls.df["date"].unique())
        cls.prep = es.prepare_us(cls.df, str(dates[0].date()), str(dates[-1].date()))

    def events(self, q5_are_drifters: bool, seed: int = 2):
        """One event per ticker (like a 10-K a year), so no two holds overlap on a name."""
        rng = np.random.default_rng(seed)
        rows = []
        for i in range(300):
            day = pd.Timestamp("2021-06-01") + pd.Timedelta(days=int(rng.integers(0, 120)))
            drifter = i % 2 == 0
            label = ("Q5" if drifter else "Q1") if q5_are_drifters else str(rng.choice(["Q1", "Q5"]))
            rows.append({"ticker": f"U{i:03d}", "public_date": day.strftime("%Y-%m-%d"), "bucket": label, "quintile": label, "cosine": 0.9, "length_ratio": 1.0, "stage": 1})
        return pd.DataFrame(rows)

    def test_planted_advantage_is_a_positive_spread_and_labels_without_it_are_not(self):
        res, prim = self.runmod.compute(self.prep, self.events(True), 1, {}, go_check=False)
        self.assertGreater(res["spread"]["spread"], 0.03)
        self.assertGreater(res["spread"]["t"], 3.0)
        res0, _ = self.runmod.compute(self.prep, self.events(False), 1, {}, go_check=False)
        self.assertLess(abs(res0["spread"]["t"]), 3.0)
        self.assertIn("G4_shuffled_labels_all_abs_t_lt_3", res["gates"])

    def test_the_go_rule_stops_a_thin_stage(self):
        with self.assertRaises(RuntimeError):
            self.runmod.compute(self.prep, self.events(True), 1, {}, go_check=True)               # a few hundred scored events, not 1,000 per bucket


if __name__ == "__main__":
    unittest.main()
