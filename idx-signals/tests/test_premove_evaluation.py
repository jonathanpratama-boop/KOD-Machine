"""Independent regressions for temporal splits and comparable alert accounting."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from idxsig import premove as pm
from idxsig.premove_core import Examples
from idxsig.provenance import sha256_file


def row(ticker="AAA", date="2023-01-01", *, known=True, up=0, hit=None, score=.5, **changes):
    date = pd.Timestamp(date)
    result = {"ticker": ticker, "date": date, "eligible": True, "label_known": known,
              "label_end_date": date + pd.Timedelta(days=5), "up_first": float(up) if known else np.nan,
              "down_first": 0. if known else np.nan, "neither": float(not up) if known else np.nan,
              "first_hit_date": pd.Timestamp(hit) if hit else (date + pd.Timedelta(days=2) if up else pd.NaT),
              "first_hit_step": 2. if up else np.nan, "ret1": .01, "ret5": .03,
              "barrier_up_fraction": .1, "baseline_volume": score, "baseline_volatility": score,
              "baseline_g2": 0., "summary_up": score, "sequence_up": score, "x": score}
    return {**result, **changes}


def fixture():
    rows = []
    for date in ("2021-12-20", "2022-12-20", "2023-01-01", "2023-01-02"):
        rows.extend([row("AAA", date, up=1, score=.8), row("BBB", date, score=.2)])
    rows.extend([row("CROSS_TRAIN", "2021-12-29", up=1), row("CROSS_CAL", "2022-12-29", up=1),
                 row("UNKNOWN", "2023-01-01", known=False, score=.9)])
    return Examples(pd.DataFrame(rows), ("x",), ())


class FakeModel:
    def __init__(self, train):
        self.fit_rows = list(train.ticker)

    def predict(self, frame):
        p = frame.x.to_numpy() * .8
        return np.column_stack([p, (1-p)*.2, (1-p)*.8])

    def record(self):
        return {"fit_rows": self.fit_rows, "converged": [True, True, True]}


def run_fixture(examples=None):
    protocol = json.loads(pm.PROTOCOL.read_text())
    protocol["evaluation"]["top_k"] = 1
    with patch.object(pm, "fit_model", side_effect=lambda train, *a, **kw: FakeModel(train)):
        return pm.evaluate(examples or fixture(), protocol)


class RankingAndTime(unittest.TestCase):
    def test_unknown_future_can_win_a_slot_without_replacement(self):
        pool = pd.DataFrame([row("UNKNOWN", known=False, score=.99), row("KNOWN", up=1, score=.5)])
        for method in pm.METHODS:
            with self.subTest(method=method):
                chosen = pm.shortlist(pool, method, 1)
                self.assertEqual(chosen.ticker.tolist(), ["UNKNOWN"])
                self.assertFalse(chosen.label_known.iloc[0])

    def test_ties_are_stable_ticker_order_independent_of_input_order(self):
        pool = pd.DataFrame([row("ZZZ"), row("AAA"), row("MMM")])
        for method in pm.METHODS:
            self.assertEqual(pm.shortlist(pool, method, 2).ticker.tolist(), ["AAA", "MMM"])
            self.assertEqual(pm.shortlist(pool.iloc[::-1], method, 2).ticker.tolist(), ["AAA", "MMM"])

    def test_duplicate_or_nonfinite_scores_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            pm.shortlist(pd.DataFrame([row(), row()]), "sequence")
        with self.assertRaisesRegex(ValueError, "non-finite"):
            pm.shortlist(pd.DataFrame([row(sequence_up=np.nan)]), "sequence")

    def test_fit_purges_future_crossing_labels_but_test_keeps_unknowns(self):
        frame = fixture().frame
        train = pm.period(frame, "2021-01-01", "2021-12-31", known=True)
        cal = pm.period(frame, "2022-01-01", "2022-12-31", known=True)
        test = pm.period(frame, "2023-01-01", "2023-12-31")
        self.assertNotIn("CROSS_TRAIN", train.ticker.tolist())
        self.assertNotIn("CROSS_CAL", cal.ticker.tolist())
        self.assertIn("UNKNOWN", test.ticker.tolist())
        self.assertTrue((train.label_end_date <= pd.Timestamp("2021-12-31")).all())
        self.assertTrue((cal.label_end_date <= pd.Timestamp("2022-12-31")).all())

    def test_test_outcomes_do_not_change_training_calibration_or_scores(self):
        examples = fixture()
        original = run_fixture(examples)
        changed = copy.deepcopy(examples)
        mask = changed.frame.date.dt.year == 2023
        changed.frame.loc[mask, "up_first"] = 0.
        changed.frame.loc[mask, "down_first"] = 1.
        changed.frame.loc[mask, "neither"] = 0.
        changed.frame.loc[mask, "label_known"] = True
        changed.frame.loc[mask, "first_hit_date"] = changed.frame.loc[mask, "date"] + pd.Timedelta(days=2)
        rerun = run_fixture(changed)
        self.assertEqual(original[1], rerun[1])
        self.assertEqual(original[0]["calibration"], rerun[0]["calibration"])
        for name in ("summary", "sequence"):
            np.testing.assert_allclose(original[2][f"{name}_up"], rerun[2][f"{name}_up"])
        self.assertNotIn("CROSS_TRAIN", original[1]["sequence"]["fit_rows"])

    def test_temperature_receives_only_mature_calibration_rows(self):
        examples = fixture()
        cal = (examples.frame.date == pd.Timestamp("2022-12-20"))
        examples.frame.loc[cal, "x"] = [.33, .77]
        examples.frame.loc[cal, ["up_first", "down_first", "neither"]] = [[0, 1, 0], [0, 0, 1]]
        expected = FakeModel(examples.frame.iloc[:0]).predict(examples.frame.loc[cal])
        with patch.object(pm, "calibrate", wraps=pm.calibrate) as calibration:
            run_fixture(examples)
        self.assertEqual(calibration.call_count, 2)
        for call in calibration.call_args_list:
            np.testing.assert_allclose(call.args[0], expected)
            np.testing.assert_array_equal(call.args[1], [[0, 1, 0], [0, 0, 1]])

    def test_probability_validation_and_temperature_are_explicit(self):
        p = np.array([[.8, .1, .1], [.1, .1, .8]])
        y = np.array([[1, 0, 0], [0, 0, 1]])
        temperature, losses = pm.calibrate(p, y)
        self.assertEqual(temperature, .5)
        self.assertEqual(set(losses), {str(t) for t in pm.TEMPERATURES})
        np.testing.assert_allclose(pm.probabilities(p, temperature).sum(axis=1), 1)
        for invalid in ([[.8, .8, .1]], [[np.nan, 0, 1]], [[-1, 1, 1]]):
            with self.assertRaises(ValueError):
                pm.probabilities(invalid)


class AlertAccounting(unittest.TestCase):
    def test_episodes_anchor_to_first_hit_instead_of_chaining(self):
        pool = pd.DataFrame([row("AAA", "2023-01-01", up=1, hit="2023-01-03"),
                             row("AAA", "2023-01-05", up=1, hit="2023-01-07"),
                             row("AAA", "2023-01-09", up=1, hit="2023-01-11"),
                             row("BBB", "2023-01-01", up=1, hit="2023-01-03")])
        ids = pm.episodes(pool)
        self.assertEqual(ids.iloc[0], ids.iloc[1])
        self.assertNotEqual(ids.iloc[1], ids.iloc[2])
        self.assertNotEqual(ids.iloc[0], ids.iloc[3])
        self.assertEqual(ids.nunique(), 3)

    def test_censored_selections_keep_denominator_and_missed_event_counts(self):
        pool = pd.DataFrame([row("AAA", up=1), row("BBB", up=1), row("CCC", known=False), row("DDD")])
        pool["episode_id"] = pm.episodes(pool)
        selected = pool.loc[[0, 2, 3]].copy()
        result, daily = pm.alert_metrics(pool, selected)
        self.assertEqual(result["selected"], 3)
        self.assertEqual(result["known_selected"], 2)
        self.assertEqual(result["up_hits"], 1)
        self.assertEqual(result["false_alerts_known"], 1)
        self.assertEqual(result["censored_selected"], 1)
        self.assertAlmostEqual(result["precision_lower_bound"], 1/3)
        self.assertAlmostEqual(result["precision_upper_bound"], 2/3)
        self.assertAlmostEqual(result["precision_known"], .5)
        self.assertEqual(result["known_episodes"], 2)
        self.assertEqual(result["episodes_caught"], 1)
        self.assertEqual(result["episodes_missed"], 1)
        self.assertEqual(daily.selected.sum(), 3)

    def test_repeated_alerts_count_one_episode_and_use_anchor_lead_time(self):
        pool = pd.DataFrame([row("AAA", "2023-01-01", up=1, hit="2023-01-05"),
                             row("AAA", "2023-01-03", up=1, hit="2023-01-07")])
        pool["episode_id"] = pm.episodes(pool)
        result, _ = pm.alert_metrics(pool, pool)
        self.assertEqual(result["episodes_caught"], 1)
        self.assertEqual(result["median_earliest_alert_lead_days"], 4)

    def test_alert_after_episode_anchor_does_not_count_as_early_detection(self):
        pool = pd.DataFrame([row("AAA", "2023-01-01", up=1, hit="2023-01-03"),
                             row("AAA", "2023-01-04", up=1, hit="2023-01-07")])
        pool["episode_id"] = pm.episodes(pool)
        result, _ = pm.alert_metrics(pool, pool.iloc[[1]])
        self.assertEqual(result["up_hits"], 1)  # The window target still came true.
        self.assertEqual(result["episodes_caught"], 0)
        self.assertEqual(result["episodes_missed"], 1)
        self.assertIsNone(result["median_earliest_alert_lead_days"])

    def test_bootstrap_is_paired_reproducible_and_counts_actual_slots(self):
        days = pd.date_range("2023-01-01", periods=20)
        a = pd.DataFrame({"hits": [1]*20, "selected": [2]*20}, index=days)
        b = pd.DataFrame({"hits": [1]*20, "selected": [4]*20}, index=days)
        first = pm.paired_bootstrap(a, b, draws=30)
        self.assertEqual(first, pm.paired_bootstrap(a, b, draws=30))
        self.assertAlmostEqual(first["delta"], .25)
        self.assertAlmostEqual(first["lower95"], .25)
        self.assertAlmostEqual(first["upper95"], .25)

    def test_bootstrap_aligns_the_same_calendar_days_before_resampling(self):
        days = pd.date_range("2023-01-01", periods=20)
        a = pd.DataFrame({"hits": [0, 1]*10, "selected": [1]*20}, index=days)
        result = pm.paired_bootstrap(a, a.iloc[::-1], draws=30)
        self.assertEqual(result["delta"], 0)
        self.assertEqual(result["lower95"], 0)
        self.assertEqual(result["upper95"], 0)

    def test_empty_population_does_not_invent_alerts_or_episodes(self):
        pool = pd.DataFrame([row()]).iloc[:0].copy()
        pool["episode_id"] = pm.episodes(pool)
        result, daily = pm.alert_metrics(pool, pool)
        self.assertEqual(result["selected"], 0)
        self.assertEqual(result["known_episodes"], 0)
        self.assertIsNone(result["precision_lower_bound"])
        self.assertIsNone(result["median_earliest_alert_lead_days"])
        self.assertTrue(daily.empty)


class Publication(unittest.TestCase):
    def test_published_run_is_hash_bound_and_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "COLLECTION.json"
            source.write_text('{"source":"synthetic"}\n')
            panel = root / "panel.csv"
            panel.write_text("synthetic test input\n")
            out = root / "result"
            results = run_fixture()
            pm.write_run(out, *results, input_path=panel, source_manifest=source)
            manifest_before = (out / "MANIFEST.json").read_bytes()
            manifest = json.loads(manifest_before)
            for path, item in manifest["files"].items():
                self.assertEqual(item["sha256"], sha256_file(out / path))
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(summary["provenance"]["input_sha256"], sha256_file(panel))
            self.assertEqual(summary["provenance"]["protocol_sha256"], sha256_file(pm.PROTOCOL))
            with self.assertRaises(FileExistsError):
                pm.write_run(out, *results, input_path=panel, source_manifest=source)
            self.assertEqual((out / "MANIFEST.json").read_bytes(), manifest_before)

    def test_cli_rejects_input_hash_mismatch_before_building_examples(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "COLLECTION.json"
            source.write_text(json.dumps({"panel_sha256": "0" * 64}))
            panel = root / "panel.csv"
            panel.write_text("untrusted input\n")
            with patch.object(pm, "build_examples") as build:
                self.assertEqual(pm.main(["--input", str(panel), "--source-manifest", str(source)]), 2)
                build.assert_not_called()


if __name__ == "__main__":
    unittest.main()
