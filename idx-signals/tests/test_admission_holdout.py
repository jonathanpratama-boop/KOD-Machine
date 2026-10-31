"""ADMISSION_HOLDOUT_v1: freshness across the window boundary and the collector's window (fixtures, no market data)."""

import importlib.util
import unittest
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parents[1] / "research/ADMISSION_HOLDOUT_v1"


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ho = load("holdout")


def sl(rows):
    return pd.DataFrame(
        [{"date": d, "ticker": t, "rank": r, "rank_score": p} for d, t, r, p in rows]
    )


class Boundary(unittest.TestCase):
    def test_the_first_day_uses_the_day_before_for_freshness_and_that_day_is_not_traded(self):
        f = sl(
            [
                ("2023-12-31", "A", 1, 0.12),
                ("2023-12-31", "Z", 2, 0.12),
                ("2024-01-01", "A", 1, 0.12),
                ("2024-01-01", "B", 2, 0.12),
            ]
        )
        base, chal, elig = ho.holdout_lists(f)
        self.assertEqual(set(base.date), {"2024-01-01"})
        self.assertEqual(chal.ticker.tolist(), ["B"])  # A was in the 2023-12-31 list: not fresh
        self.assertEqual(dict(zip(elig.ticker, elig.reason)), {"A": "NOT_FRESH", "B": "ELIGIBLE"})

    def test_without_the_prior_list_the_first_day_is_freshness_unknown(self):
        f = sl([("2024-01-01", "B", 1, 0.12)])
        _, chal, elig = ho.holdout_lists(f)
        self.assertEqual(chal.ticker.tolist(), [])
        self.assertEqual(elig.reason.tolist(), ["FRESHNESS_UNKNOWN"])

    def test_yearly_compounds_monthly_returns(self):
        y = ho.yearly({"2024-01": 0.10, "2024-02": -0.10, "2025-01": 0.05})
        self.assertAlmostEqual(y["2024"], 1.1 * 0.9 - 1)
        self.assertAlmostEqual(y["2025"], 0.05)


class CollectorWindow(unittest.TestCase):
    def test_the_window_ends_before_the_prospective_trial_and_the_shared_guard_is_untouched(self):
        col = load("collect")
        self.assertEqual((col.FIRST, col.LAST), ("2023-07-01", "2026-10-29"))
        self.assertEqual(col.ms("2026-10-29", end=True) + 1, col.ms("2026-10-30"))
        spec = importlib.util.spec_from_file_location(
            "fresh_cpc", Path(__file__).resolve().parents[2] / "tools/collect_premove_crypto.py"
        )
        fresh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fresh)
        self.assertEqual((fresh.START_MS, fresh.END_MS), (1577836800000, 1704067199999))


if __name__ == "__main__":
    unittest.main()
