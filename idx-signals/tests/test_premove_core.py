import json
import unittest

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from idxsig.premove_core import TARGETS, build_examples, fit_model, prepare_panel


def panel(n=125, symbols=("AAA", "BBB"), varying=False):
    rows = []
    for k, symbol in enumerate(symbols):
        t = np.arange(n)
        close = 100 * np.exp(.001 * t + .015 * np.sin(t / 3 + k)) if varying else np.full(n, 100.)
        for j, day in enumerate(pd.date_range("2020-01-01", periods=n)):
            value = float(close[j])
            volume = float(10_000 + (j % 7) * 200)
            rows.append({"date": day, "ticker": symbol, "open": value, "high": value * 1.01,
                         "low": value * .99, "close": value, "volume": volume, "value": value * volume})
    return pd.DataFrame(rows)


class PanelAndExamples(unittest.TestCase):
    def test_bad_inputs_are_not_silently_cleaned(self):
        source = panel()
        for bad in (pd.concat([source, source.iloc[:1]]), source.assign(volume=-1),
                    source.assign(close=np.inf), source.assign(high=1), source.assign(volume=True)):
            with self.assertRaises(ValueError):
                prepare_panel(bad)
        with self.assertRaises(ValueError):
            prepare_panel(source.assign(date=source.date + pd.Timedelta(hours=1)))
        missing = source.copy()
        missing.loc[0, "close"] = np.nan
        self.assertTrue(np.isnan(prepare_panel(missing).iloc[0].close))

    def test_ordinary_windows_and_censored_rows_are_retained(self):
        result = build_examples(panel())
        f = result.frame
        self.assertEqual(len(f), 250)
        self.assertGreater(f.eligible.sum(), 100)
        self.assertTrue((f.loc[f.label_known, list(TARGETS)].sum(axis=1) == 1).all())
        tail = f.groupby("ticker").tail(5)
        self.assertTrue(tail.eligible.all())
        self.assertFalse(tail.label_known.any())
        self.assertTrue(tail[list(TARGETS)].isna().all().all())

    def test_complete_bar_is_optional_and_strictly_boolean(self):
        source = panel(symbols=("AAA",))
        self.assertTrue(prepare_panel(source).complete_bar.all())
        for value in (None, np.nan, 1, "True"):
            with self.assertRaises(ValueError):
                prepare_panel(source.assign(complete_bar=value))
        flagged = source.assign(complete_bar=True)
        flagged.loc[124, "complete_bar"] = False
        prepared = prepare_panel(flagged)
        self.assertEqual(len(prepared), len(source))
        self.assertFalse(prepared.iloc[-1].complete_bar)

    def test_partial_terminal_bar_censors_outcomes_and_preserves_history(self):
        source = panel(symbols=("AAA",), varying=True)
        original = build_examples(source)
        flagged = source.assign(complete_bar=True)
        flagged.loc[124, "complete_bar"] = False
        result = build_examples(flagged)
        f = result.frame
        self.assertEqual(len(f), len(original.frame))
        self.assertFalse(f.iloc[-1].complete_bar)
        self.assertFalse(f.iloc[-1].eligible)
        self.assertTrue(original.frame.iloc[119].label_known)
        self.assertTrue(f.iloc[119].eligible)
        self.assertFalse(f.iloc[119].label_known)
        self.assertTrue(f.iloc[119][list(TARGETS)].isna().all())
        # The partial future bar cannot change earlier features or eligibility.
        cols = ["date", "ticker", "eligible", *result.feature_columns, *result.sequence_columns]
        assert_frame_equal(original.frame.iloc[:-1][cols], f.iloc[:-1][cols])
        # Windows ending before the partial bar retain their known outcomes.
        assert_frame_equal(original.frame.iloc[:119], f.iloc[:119])

    def test_future_edits_do_not_change_features_or_current_eligibility(self):
        source = panel(varying=True)
        first = build_examples(source)
        cutoff = pd.Timestamp("2020-04-01")
        altered = source.copy()
        later = altered.date > cutoff
        for c in ("open", "high", "low", "close", "volume", "value"):
            altered.loc[later, c] *= 20
        second = build_examples(altered)
        cols = ["date", "ticker", "eligible", "median_value20", *first.feature_columns, *first.sequence_columns]
        assert_frame_equal(first.frame.loc[first.frame.date <= cutoff, cols].reset_index(drop=True),
                           second.frame.loc[second.frame.date <= cutoff, cols].reset_index(drop=True))
        prefix = build_examples(source[source.date <= cutoff])
        assert_frame_equal(first.frame.loc[first.frame.date <= cutoff, cols].reset_index(drop=True),
                           prefix.frame[cols].reset_index(drop=True))

    def test_next_open_not_signal_close_is_target_reference(self):
        source = panel(symbols=("AAA",))
        source.loc[source.index >= 81, ["open", "high", "low", "close"]] *= 1.5
        f = build_examples(source).frame
        row = f.iloc[80]
        self.assertTrue(row.eligible)
        self.assertEqual(row.entry_open, 150)
        self.assertEqual(row.neither, 1)
        self.assertEqual(row.up_first, 0)

    def test_first_close_crossing_sets_direction_and_lead_time(self):
        source = panel(symbols=("AAA",))
        for i, value in [(82, 120.), (83, 75.)]:
            source.loc[i, ["open", "high", "low", "close"]] = [value, value * 1.01, value * .99, value]
        row = build_examples(source).frame.iloc[80]
        self.assertEqual(row.up_first, 1)
        self.assertEqual(row.down_first, 0)
        self.assertEqual(row.first_hit_step, 2)
        self.assertEqual(row.first_hit_date, source.iloc[82].date)

    def test_missing_future_does_not_remove_a_current_candidate(self):
        source = panel(symbols=("AAA",)).drop(index=83)
        f = build_examples(source).frame
        row = f.loc[f.date == pd.Timestamp("2020-03-21")].iloc[0]
        self.assertTrue(row.eligible)
        self.assertFalse(row.label_known)
        self.assertTrue(np.isnan(row.up_first))
        # The missing bar also breaks subsequent history eligibility causally.
        after = f[(f.date > pd.Timestamp("2020-03-24")) & (f.date < pd.Timestamp("2020-04-10"))]
        self.assertFalse(after.eligible.any())

    def test_extreme_future_prices_are_preserved(self):
        source = panel(symbols=("AAA",))
        source.loc[82, ["open", "high", "low", "close"]] *= 100
        row = build_examples(source).frame.iloc[80]
        self.assertTrue(row.label_known)
        self.assertEqual(row.up_first, 1)

    def test_configuration_and_liquidity_are_explicit(self):
        source = panel()
        for kwargs in ({"horizon": 0}, {"horizon": True}, {"lookback": 61},
                       {"threshold_floor": np.nan}, {"vol_multiplier": -1}, {"min_value20": -1}):
            with self.assertRaises(ValueError):
                build_examples(source, **kwargs)
        self.assertFalse(build_examples(source, min_value20=1e9).frame.eligible.any())

    def test_liquidity_window_excludes_current_value(self):
        source = panel(symbols=("AAA",))
        expected = source.iloc[60:80].value.median()
        source.loc[80, "value"] = 1e15
        row = build_examples(source).frame.iloc[80]
        self.assertEqual(row.median_value20, expected)


class ModelFit(unittest.TestCase):
    def training(self):
        rng = np.random.default_rng(18)
        f = pd.DataFrame(rng.normal(size=(200, 7)), columns=["x", "y", "s0", "s1", "s2", "s3", "s4"])
        labels = np.where(f.x > .6, 0, np.where(f.y < -.7, 1, 2))
        for k, target in enumerate(TARGETS):
            f[target] = (labels == k).astype(float)
        return f

    def test_scaler_pca_and_weights_are_fit_only_from_training_rows(self):
        train = self.training()
        m = fit_model(train, ("x", "y"), ("s0", "s1", "s2", "s3", "s4"), pca_components=3)
        original = json.dumps(m.record(), allow_nan=False, sort_keys=True)
        np.testing.assert_allclose(m.mean, train[["x", "y"]].mean())
        np.testing.assert_allclose(m.sequence_mean, train[["s0", "s1", "s2", "s3", "s4"]].mean())
        self.assertTrue(all(m.converged))
        self.assertTrue(all(np.isfinite(m.objectives)))
        unseen = train.iloc[:10].copy()
        unseen[["x", "y", "s0", "s1", "s2", "s3", "s4"]] *= 100
        p = m.predict(unseen)
        self.assertTrue(np.isfinite(p).all())
        np.testing.assert_allclose(p.sum(axis=1), 1)
        self.assertEqual(original, json.dumps(m.record(), allow_nan=False, sort_keys=True))
        unseen[list(TARGETS)] = np.nan
        np.testing.assert_allclose(p, m.predict(unseen))
        self.assertEqual(original, json.dumps(fit_model(train, ("x", "y"), ("s0", "s1", "s2", "s3", "s4"), pca_components=3).record(), allow_nan=False, sort_keys=True))

    def test_constant_class_and_missing_targets_are_handled_honestly(self):
        train = self.training()
        train[list(TARGETS)] = [0, 0, 1]
        m = fit_model(train, ("x", "y"))
        np.testing.assert_allclose(m.predict(train), np.tile([0, 0, 1], (len(train), 1)))
        train.loc[0, "neither"] = np.nan
        with self.assertRaises(ValueError):
            fit_model(train, ("x", "y"))

    def test_invalid_model_configuration_and_nonfinite_features_fail(self):
        train = self.training()
        for kwargs in ({"ridge": 0}, {"ridge": np.inf}, {"pca_components": 0}):
            with self.assertRaises(ValueError):
                fit_model(train, ("x", "y"), **kwargs)
        with self.assertRaises(ValueError):
            fit_model(train.iloc[:0], ("x", "y"))
        with self.assertRaises(ValueError):
            fit_model(train, ("x", "x"))
        m = fit_model(train, ("x", "y"))
        train.loc[0, "x"] = np.inf
        with self.assertRaises(ValueError):
            m.predict(train)
        train["x"] = 1e308
        with self.assertRaises(ValueError):
            fit_model(train, ("x", "y"))


if __name__ == "__main__":
    unittest.main()
