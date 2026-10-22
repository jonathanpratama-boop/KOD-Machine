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


if __name__ == "__main__":
    unittest.main()
