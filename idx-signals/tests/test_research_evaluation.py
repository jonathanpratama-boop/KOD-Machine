"""Adversarial regressions: future gaps cannot decide today's ranking or trade slots."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from idxsig import research_evaluation as ev


def rows():
    result = []
    dates = list(pd.date_range("2020-12-01", periods=8)) + [pd.Timestamp("2020-12-27")]
    dates += list(pd.date_range("2021-01-01", periods=8))
    for day, date in enumerate(dates):
        for i in range(12):
            row = {"date": date, "ticker": f"COIN{i:02}", "peers_ok": True,
                   "station": 1 + i % 5, "fwd1": (i - 5) * .005,
                   "fwd3": (i - 5) * .01, "fwd5": (i - 5) * .015}
            for j, feature in enumerate((*ev.COIN_A, *ev.PEER_FEATURES)):
                row[feature] = (i + 1) * (.01 + j / 100) + day / 10000
            row.update({"btc7": day / 100, "breadth": .5 + day / 100})
            row.update({feature: .01 * (j + day) for j, feature in enumerate(ev.STATION_FEATURES)})
            result.append(row)
    return pd.DataFrame(result)


class CausalUniverse(unittest.TestCase):
    def test_future_completeness_cannot_change_feature_ranks_or_predictions(self):
        original = rows()
        changed = original.copy()
        pending = changed.date >= "2021-01-01"
        changed.loc[pending & changed.ticker.isin(["COIN10", "COIN11"]), ["fwd1", "fwd3", "fwd5"]] = np.nan
        f1 = ev.prepare_features(original)
        f2 = ev.prepare_features(changed)
        cols = ["date", "ticker"] + [c for c in f1 if c.endswith("_rk")]
        assert_frame_equal(f1[cols], f2[cols])
        p1, a1 = ev.freeze_predictions(original, years=[2021])
        p2, a2 = ev.freeze_predictions(changed, years=[2021])
        assert_frame_equal(p1, p2)
        self.assertEqual(a1, a2)
        selected1 = ev.select_picks(p1, ["A", "B", "C"])
        selected2 = ev.select_picks(p2, ["A", "B", "C"])
        assert_frame_equal(selected1, selected2)
        self.assertTrue(selected2.ticker.isin(["COIN10", "COIN11"]).any())

    def test_unknown_top_candidate_keeps_its_slot(self):
        d = pd.DataFrame({"date": [pd.Timestamp("2021-01-01")] * 12,
                          "ticker": [f"X{i:02}" for i in range(12)], "pA": list(range(12))})
        picks = ev.select_picks(d, ["A"], top_k=1)
        self.assertEqual(picks[picks.method == "A"].ticker.tolist(), ["X11"])
        outcomes = d[["date", "ticker"]].assign(fwd3=.1)
        outcomes.loc[outcomes.ticker == "X11", "fwd3"] = np.nan
        report, scored = ev.score_picks(picks, outcomes)
        self.assertEqual(report["A"]["selected_picks"], 1)
        self.assertEqual(report["A"]["known_picks"], 0)
        self.assertEqual(report["A"]["unknown_picks"], 1)
        self.assertEqual(report["A"]["status"], "INCOMPLETE")
        self.assertIsNone(report["A"]["full_selection_mean"])
        self.assertIsNone(report["A"]["gross_observed_mean"])
        self.assertEqual(scored[scored.method == "A"].outcome_state.tolist(), ["UNKNOWN"])

    def test_future_columns_are_rejected_at_selection_boundary(self):
        prediction, _ = ev.freeze_predictions(rows(), years=[2021])
        with self.assertRaisesRegex(ValueError, "outcome-free"):
            ev.select_picks(prediction.assign(fwd3=.1), ["A"])

    def test_refit_uses_only_labels_matured_strictly_before_cutoff(self):
        frame = ev.prepare_features(rows())
        mask = ev.matured_training_mask(frame, "2021-01-01")
        self.assertEqual(int(mask.sum()), 8 * 12)
        self.assertFalse(mask[frame.date == "2020-12-27"].any())
        changed = rows()
        changed.loc[changed.date >= "2020-12-27", "fwd3"] = 9999
        original, audit = ev.freeze_predictions(rows(), years=[2021])
        new, _ = ev.freeze_predictions(changed, years=[2021])
        assert_frame_equal(original, new)
        self.assertLess(pd.Timestamp(audit[0]["last_training_label_maturity"]), pd.Timestamp(audit[0]["refit_at"]))

    def test_ties_are_resolved_without_input_order_or_future_information(self):
        p = pd.DataFrame({"date": ["2021-01-01"] * 12, "ticker": [f"X{i:02}" for i in range(12)], "pA": 0.1})
        a = ev.select_picks(p, ["A"])
        b = ev.select_picks(p.iloc[::-1], ["A"])
        assert_frame_equal(a, b)
        self.assertEqual(a[a.method == "A"].ticker.tolist(), [f"X{i:02}" for i in range(5)])

    def test_invalid_features_and_duplicate_keys_fail(self):
        d = rows()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            ev.prepare_features(pd.concat([d, d.iloc[:1]]))
        d.loc[0, "ret1"] = np.inf
        with self.assertRaisesRegex(ValueError, "infinite"):
            ev.prepare_features(d)

    def test_known_observed_means_do_not_hide_unknown_denominator(self):
        picks = pd.DataFrame({"date": pd.to_datetime(["2021-01-01"] * 2), "ticker": ["A", "B"], "method": "A", "weight": .5})
        outcomes = pd.DataFrame({"date": pd.to_datetime(["2021-01-01"] * 2), "ticker": ["A", "B"], "fwd3": [.1, np.nan]})
        report, _ = ev.score_picks(picks, outcomes)
        self.assertEqual(report["A"]["known_picks"], 1)
        self.assertAlmostEqual(report["A"]["net_observed_means"]["0.004"], .096)
        self.assertIsNone(report["A"]["full_selection_mean"])


class CorrectedArtifacts(unittest.TestCase):
    def test_new_run_has_frozen_outcome_free_files_and_consistent_denominators(self):
        d = rows()
        d.loc[(d.date == "2021-01-01") & (d.ticker == "COIN11"), "fwd3"] = np.nan
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input.csv"
            d.to_csv(source, index=False)
            output = Path(tmp) / "run"
            result = ev.write_corrected_run(d, output, source_paths=[source], years=[2021])
            frozen = pd.read_csv(output / "predictions.csv")
            self.assertEqual(result["rows_test"], len(frozen))
            self.assertFalse(any(c.startswith("fwd") for c in frozen))
            self.assertEqual(result["promotion"], "DISABLED_PENDING_REVIEW")
            self.assertEqual(json.loads((output / "RESULT.json").read_text())["rows_test"], len(frozen))
            self.assertTrue((output / "manifest.json").is_file())
            with self.assertRaises(FileExistsError):
                ev.write_corrected_run(d, output, years=[2021])

    def test_pressure_gap_is_not_compressed_into_three_day_window(self):
        dates = pd.date_range("2020-01-01", periods=25)
        taker = pd.DataFrame({"date": dates, "ticker": "X", "quote_vol": 100.0, "taker_buy_quote": 60.0})
        taker = taker[taker.date != dates[20]]
        base = pd.DataFrame({"date": dates, "ticker": "X"})
        combined = ev.add_pressure_features(base, taker)
        self.assertTrue(np.isnan(combined.loc[combined.date == dates[21], "tbz"].iloc[0]))
        self.assertTrue(np.isnan(combined.loc[combined.date == dates[20], "tb1"].iloc[0]))
        self.assertTrue(np.isfinite(combined.loc[combined.date == dates[24], "tbz"].iloc[0]))


if __name__ == "__main__":
    unittest.main()
