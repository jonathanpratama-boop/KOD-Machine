"""Study-level look-ahead check (Fix 2): leaky toy studies fail, their clean twins pass.

The toys are synthetic, seeded and offline; no historical study is run. Each leaky toy
reproduces a defect class found in KOD study code: a centred window, a full-sample
statistic, rows dropped because a future value is missing, and an outcome label stored
on its signal row. Inputs the check cannot interpret are refused, never guessed.
"""

from datetime import timedelta
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from idxsig import panel
from idxsig.lookahead import (
    COMPARE,
    ONLY_IN_CANDIDATE,
    ONLY_IN_REFERENCE,
    SCRAMBLE,
    TRUNCATION,
    VALUE_DIFFERS,
    LookaheadCheckError,
    compare_decisions,
    scramble_check,
    truncation_check,
)

CUTOFFS = ("2026-01-15T00:00:00Z", "2026-01-25T00:00:00Z", "2026-02-02T00:00:00Z")
COLUMNS = dict(data_time_column="time", time_column="time", key_columns=("time", "asset"))
LAG = {"fwd3": timedelta(days=3)}


def prices(days: int = 40) -> pd.DataFrame:
    """Seeded random-walk closes and volumes for three assets, one row per UTC day."""
    rng = np.random.default_rng(20261104)
    times = pd.date_range("2026-01-01", periods=days, freq="D", tz="UTC")
    frames = [
        pd.DataFrame(
            {
                "time": times,
                "asset": asset,
                "close": 100 * np.exp(np.cumsum(rng.normal(0, 0.02, days))),
                "volume": rng.integers(1000, 5000, days),
            }
        )
        for asset in "ABC"
    ]
    return pd.concat(frames, ignore_index=True)


def labelled() -> pd.DataFrame:
    """Prices with a three-day forward return stored on its signal row, as studies do."""
    data = prices()
    future = data.groupby("asset").close.shift(-3)
    return data.assign(fwd3=future / data.close - 1)


def trailing(close: pd.Series) -> pd.Series:
    return close.rolling(5).mean()


def centred(close: pd.Series) -> pd.Series:
    return close.rolling(5, center=True).mean()


def full_sample(close: pd.Series) -> pd.Series:
    return pd.Series(close.mean(), index=close.index)


def study(signal, *, drop_missing_future: bool = False, drop_missing_label: bool = False):
    """A toy study: long when the close is above a per-asset signal of the closes."""

    def decide(data: pd.DataFrame) -> pd.DataFrame:
        d = data.sort_values(["asset", "time"], kind="stable")
        if drop_missing_future:
            d = d[d.groupby("asset").close.shift(-3).notna()]
        if drop_missing_label:
            d = d[d.fwd3.notna()]
        d = d.assign(score=d.groupby("asset").close.transform(signal)).dropna(subset=["score"])
        return d.assign(long=d.close > d.score)[["time", "asset", "score", "long"]]

    return decide


CLEAN = study(trailing)
LEAKS = {
    "centred rolling mean": study(centred),
    "full-sample mean": study(full_sample),
    "rows dropped when the future close is missing": study(trailing, drop_missing_future=True),
}
CHECKS = (truncation_check, scramble_check)


def panel_rows(days: int = 60) -> pd.DataFrame:
    """Seeded rows as ``idxsig.panel.load`` returns them, plus one merged numpy float column.

    The rows pass through a temporary panel file and manifest, so the dtypes are the
    loader's own: naive session dates, object tickers and pandas nullable Int64 prices.
    """
    rng = np.random.default_rng(20261105)
    dates = pd.bdate_range("2025-01-02", periods=days).strftime("%Y-%m-%d")
    frames = []
    for ticker in ("ASII", "BBCA", "TLKM"):
        close = np.round(5000 * np.exp(np.cumsum(rng.normal(0, 0.02, days)))).astype(int)
        volume = rng.integers(100_000, 1_000_000, days)
        prices_as_traded = {c: close for c in ("previous", "open", "high", "low", "close")}
        frames.append(
            pd.DataFrame(
                {
                    "date": dates,
                    "ticker": ticker,
                    "source": "idx_mirror",
                    **prices_as_traded,
                    "volume": volume,
                    "value": close * volume,
                    "frequency": rng.integers(100, 2000, days),
                    "listed_shares": 10**9,
                    "tradable_shares": 6 * 10**8,
                }
            )
        )
    with tempfile.TemporaryDirectory() as tmp:
        path, manifest = Path(tmp, "panel.csv"), Path(tmp, "panel.json")
        pd.concat(frames, ignore_index=True).to_csv(path, index=False)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest.write_text(json.dumps({"panel": str(path), "sha256": digest}))
        rows, _, _ = panel.load(manifest)
    return rows.assign(foreign_net=rng.normal(0, 1, len(rows)))


def panel_study(signal, *, drop_missing_flag: bool = False):
    """The toy study on panel rows: long when the close is above a per-ticker signal."""

    def decide(rows: pd.DataFrame) -> pd.DataFrame:
        d = rows.sort_values(["ticker", "date"], kind="stable")
        if drop_missing_flag:
            d = d[d.up3.notna()]
        close = d.close.astype(float)
        d = d.assign(score=close.groupby(d.ticker).transform(signal)).dropna(subset=["score"])
        return d.assign(long=d.close.astype(float) > d.score)[["date", "ticker", "score", "long"]]

    return decide


PANEL = dict(
    data_time_column="date",
    time_column="date",
    key_columns=("date", "ticker"),
    cutoffs=("2025-02-03", "2025-03-03"),
    assume_utc=True,
)


class Spy:
    """Record a copy of every input the check hands to ``decide``."""

    def __init__(self, decide):
        self.decide, self.inputs = decide, []

    def __call__(self, data: pd.DataFrame) -> pd.DataFrame:
        self.inputs.append(data.copy(deep=True))
        return self.decide(data)


class LeakyToysFail(unittest.TestCase):
    def test_each_leak_fails_truncation_at_every_cutoff(self):
        for name, decide in LEAKS.items():
            with self.subTest(leak=name):
                report = truncation_check(decide, prices(), cutoffs=CUTOFFS, **COLUMNS)
                self.assertEqual(report.verdict, "LEAK")
                self.assertTrue(all(c.decisions_differing for c in report.cutoffs))

    def test_each_leak_fails_scramble(self):
        for name, decide in LEAKS.items():
            with self.subTest(leak=name):
                report = scramble_check(decide, prices(), cutoffs=CUTOFFS, **COLUMNS)
                self.assertEqual(report.verdict, "LEAK")
                self.assertEqual(report.first_leak.cutoff, CUTOFFS[0])

    def test_centred_window_names_the_first_differing_decision_and_cutoff(self):
        decide = LEAKS["centred rolling mean"]
        cut = truncation_check(decide, prices(), cutoffs=CUTOFFS, **COLUMNS).to_dict()
        self.assertEqual(
            cut["first_leak"],
            {
                "cutoff": "2026-01-15T00:00:00Z",
                "kind": ONLY_IN_REFERENCE,
                "decision_time": "2026-01-14T00:00:00Z",
                "key": ("2026-01-14T00:00:00Z", "A"),
                "column": None,
                "reference": None,
                "candidate": None,
            },
        )
        scrambled = scramble_check(decide, prices(), cutoffs=CUTOFFS, **COLUMNS).first_leak
        first = scrambled.first_difference
        self.assertEqual((first.kind, first.column), (VALUE_DIFFERS, "score"))
        self.assertEqual(first.decision_time, "2026-01-14T00:00:00Z")
        full = decide(prices()).set_index(["time", "asset"]).score
        expected = float(full[(pd.Timestamp("2026-01-14", tz="UTC"), "A")])
        self.assertEqual(first.reference, repr(expected))

    def test_full_sample_mean_changes_the_very_first_decision(self):
        report = truncation_check(LEAKS["full-sample mean"], prices(), cutoffs=CUTOFFS, **COLUMNS)
        first = report.first_leak
        self.assertEqual(first.decisions_differing, first.decisions_compared)
        self.assertEqual(first.first_difference.decision_time, "2026-01-01T00:00:00Z")

    def test_a_label_on_its_signal_row_is_caught_once_its_lag_is_declared(self):
        leaky = study(trailing, drop_missing_label=True)
        undeclared = truncation_check(leaky, labelled(), cutoffs=CUTOFFS, **COLUMNS)
        self.assertEqual(undeclared.verdict, "PASS")  # rows dated <= T carry the label
        for check in CHECKS:
            with self.subTest(check=check.__name__):
                report = check(leaky, labelled(), cutoffs=CUTOFFS, value_lags=LAG, **COLUMNS)
                self.assertEqual(report.verdict, "LEAK")
                self.assertEqual(report.first_leak.first_difference.kind, ONLY_IN_REFERENCE)
                clean = check(CLEAN, labelled(), cutoffs=CUTOFFS, value_lags=LAG, **COLUMNS)
                self.assertEqual(clean.verdict, "PASS")
                self.assertEqual(clean.to_dict()["value_lags"], {"fwd3": "P3DT0H0M0S"})


class CleanTwinPasses(unittest.TestCase):
    def test_trailing_window_passes_truncation_with_every_count_reported(self):
        report = truncation_check(CLEAN, prices(), cutoffs=CUTOFFS, **COLUMNS)
        self.assertEqual(
            (report.check, report.verdict, report.input_rows), (TRUNCATION, "PASS", 120)
        )
        self.assertEqual(report.value_columns, ("score", "long"))
        for result, days_after in zip(report.cutoffs, (25, 15, 7)):
            self.assertEqual(result.rows_removed, 3 * days_after)
            self.assertEqual((result.values_hidden, result.values_replaced), (0, None))
            self.assertEqual(result.reference_rows, 3 * 36)
            in_scope = 3 * (36 - days_after)
            self.assertEqual(result.reference_in_scope, in_scope)
            self.assertEqual(result.candidate_in_scope, in_scope)
            self.assertEqual(result.candidate_rows, in_scope)
            self.assertEqual((result.decisions_compared, result.decisions_differing), (in_scope, 0))
            self.assertIsNone(result.first_difference)

    def test_trailing_window_passes_scramble_and_names_scrambled_columns(self):
        report = scramble_check(CLEAN, prices(), cutoffs=CUTOFFS, **COLUMNS)
        self.assertEqual((report.check, report.verdict), (SCRAMBLE, "PASS"))
        self.assertEqual(report.scrambled_columns, ("close", "volume"))
        self.assertEqual(report.unscrambled_columns, ("time", "asset"))
        self.assertEqual((report.seed, report.missing_share), (0, 0.25))
        self.assertEqual([c.values_replaced for c in report.cutoffs], [150, 90, 42])
        self.assertTrue(all(c.rows_removed is None for c in report.cutoffs))

    def test_default_scramble_leaves_integer_decision_keys_alone(self):
        numbered = prices().assign(asset=lambda d: d.asset.map({"A": 0, "B": 1, "C": 2}))
        report = scramble_check(CLEAN, numbered, cutoffs=CUTOFFS, **COLUMNS)
        self.assertEqual(report.verdict, "PASS")
        self.assertEqual(report.scrambled_columns, ("close", "volume"))
        self.assertEqual(report.unscrambled_columns, ("time", "asset"))
        leak = scramble_check(LEAKS["centred rolling mean"], numbered, cutoffs=CUTOFFS, **COLUMNS)
        self.assertEqual(leak.verdict, "LEAK")


class WhatDecideSees(unittest.TestCase):
    def test_truncation_keeps_rows_at_or_before_cutoff_and_hides_unknown_labels(self):
        spy = Spy(CLEAN)
        truncation_check(spy, labelled(), cutoffs=CUTOFFS, value_lags=LAG, **COLUMNS)
        self.assertEqual(len(spy.inputs), 2 + len(CUTOFFS))
        pd.testing.assert_frame_equal(spy.inputs[0], labelled())
        pd.testing.assert_frame_equal(spy.inputs[1], labelled())
        for seen, cutoff in zip(spy.inputs[2:], CUTOFFS):
            stamp = pd.Timestamp(cutoff)
            original = labelled().loc[labelled().time <= stamp]
            self.assertEqual(seen.index.tolist(), original.index.tolist())
            unknown = seen.time + LAG["fwd3"] > stamp
            self.assertTrue(seen.fwd3[unknown].isna().all())
            pd.testing.assert_series_equal(seen.fwd3[~unknown], original.fwd3[~unknown])
            pd.testing.assert_frame_equal(seen.drop(columns="fwd3"), original.drop(columns="fwd3"))

    def test_scramble_keeps_rows_identifiers_and_every_value_up_to_the_cutoff(self):
        spy = Spy(CLEAN)
        scramble_check(spy, prices(), cutoffs=CUTOFFS, **COLUMNS)
        original = prices()
        for seen, cutoff in zip(spy.inputs[2:], CUTOFFS):
            after = original.time > pd.Timestamp(cutoff)
            pd.testing.assert_frame_equal(seen[["time", "asset"]], original[["time", "asset"]])
            pd.testing.assert_frame_equal(seen[~after], original[~after])
            self.assertEqual(seen.dtypes.tolist(), original.dtypes.tolist())
            noisy = seen.close[after]
            self.assertTrue(noisy.isna().any())
            self.assertFalse((noisy.dropna() == original.close[after][noisy.notna()]).any())
            low, high = original.volume.min(), original.volume.max()
            self.assertTrue(seen.volume[after].between(low, high).all())

    def test_constant_and_empty_columns_draw_noise_from_the_stated_fallback_ranges(self):
        n = len(prices())
        data = prices().assign(
            ceiling=np.full(n, 127, dtype=np.int8),
            floor=np.zeros(n, dtype=np.uint8),
            level=2.5,
            blank=np.nan,
            counts=pd.array([7] * n, dtype="Int64"),
        )
        spy = Spy(CLEAN)
        scramble_check(spy, data, cutoffs=CUTOFFS[:1], **COLUMNS)
        after = (data.time > pd.Timestamp(CUTOFFS[0])).to_numpy()
        for column, low, high in (
            ("ceiling", 126, 127),  # [v - 1, v + 1] cut to the int8 bounds
            ("floor", 0, 1),  # [v - 1, v + 1] cut to the uint8 bounds
            ("level", 1.5, 3.5),
            ("blank", 0.0, 1.0),  # no finite value
            ("counts", 6, 8),
        ):
            with self.subTest(column=column):
                noise = spy.inputs[2][column][after].dropna()
                self.assertEqual(spy.inputs[2][column].dtype, data[column].dtype)
                self.assertTrue(noise.between(low, high).all())
                self.assertGreater(noise.nunique(), 1)

    def test_scramble_noise_is_reproducible_from_its_seed(self):
        first, again, other = Spy(CLEAN), Spy(CLEAN), Spy(CLEAN)
        reports = [
            scramble_check(spy, prices(), cutoffs=CUTOFFS, seed=seed, **COLUMNS).to_dict()
            for spy, seed in ((first, 7), (again, 7), (other, 8))
        ]
        self.assertEqual(reports[0], reports[1])
        self.assertEqual(reports[2]["seed"], 8)
        for a, b in zip(first.inputs, again.inputs):
            pd.testing.assert_frame_equal(a, b)
        self.assertFalse(first.inputs[2].close.equals(other.inputs[2].close))

    def test_a_study_that_edits_its_input_cannot_affect_later_runs(self):
        def editing(data: pd.DataFrame) -> pd.DataFrame:
            data["close"] = data.close * 2
            return CLEAN(data)

        for check in CHECKS:
            with self.subTest(check=check.__name__):
                data = prices()
                self.assertEqual(check(editing, data, cutoffs=CUTOFFS, **COLUMNS).verdict, "PASS")
                pd.testing.assert_frame_equal(data, prices())


class PandasNullableColumns(unittest.TestCase):
    """The canonical panel holds prices as pandas nullable Int64; scramble must reach them."""

    def test_the_panel_loader_gives_nullable_prices_and_naive_dates(self):
        rows = panel_rows()
        self.assertEqual((str(rows.close.dtype), str(rows.date.dtype)), ("Int64", "datetime64[ns]"))

    def test_a_centred_window_on_panel_prices_fails_scramble_by_default(self):
        report = scramble_check(panel_study(centred), panel_rows(), **PANEL)
        self.assertEqual(report.verdict, "LEAK")
        self.assertEqual(report.first_leak.first_difference.column, "score")
        self.assertEqual(report.scrambled_columns, (*panel.INT_COLUMNS, "foreign_net"))
        self.assertEqual(report.unscrambled_columns, ("date", "ticker", "source"))

    def test_scrambled_nullable_columns_keep_their_dtype_and_gain_missing_values(self):
        spy, rows = Spy(panel_study(trailing)), panel_rows()
        self.assertEqual(scramble_check(spy, rows, **PANEL).verdict, "PASS")
        for seen, cutoff in zip(spy.inputs[2:], PANEL["cutoffs"]):
            after = (rows.date > pd.Timestamp(cutoff)).to_numpy()
            self.assertEqual(seen.dtypes.tolist(), rows.dtypes.tolist())
            pd.testing.assert_frame_equal(seen[~after], rows[~after])
            noisy = seen.close[after]
            self.assertTrue(noisy.isna().any())
            self.assertLess((noisy.dropna() == rows.close[after][noisy.notna()]).mean(), 0.05)
            self.assertTrue(noisy.dropna().between(rows.close.min(), rows.close.max()).all())

    def test_a_nullable_flag_known_later_is_set_missing_once_its_lag_is_declared(self):
        rows = panel_rows()
        flagged = rows.assign(up3=rows.groupby("ticker").close.shift(-3) > rows.close)
        lag = {"up3": timedelta(days=5)}  # three sessions span at most five days
        for check in CHECKS:
            with self.subTest(check=check.__name__):
                leaky = panel_study(trailing, drop_missing_flag=True)
                self.assertEqual(check(leaky, flagged, value_lags=lag, **PANEL).verdict, "LEAK")
                clean = panel_study(trailing)
                self.assertEqual(check(clean, flagged, value_lags=lag, **PANEL).verdict, "PASS")
        spy = Spy(panel_study(trailing))
        truncation_check(spy, flagged, value_lags=lag, **PANEL)
        for seen, cutoff in zip(spy.inputs[2:], PANEL["cutoffs"]):
            self.assertEqual(str(seen.up3.dtype), "boolean")
            self.assertTrue(seen.up3[seen.date + lag["up3"] > pd.Timestamp(cutoff)].isna().all())

    def test_numbers_in_a_dtype_it_cannot_scramble_are_refused_not_skipped(self):
        rows = panel_rows()
        sparse = rows.assign(spread=pd.arrays.SparseArray(np.zeros(len(rows))))
        with self.assertRaisesRegex(LookaheadCheckError, r"'spread' holds numbers in dtype Sparse"):
            scramble_check(panel_study(centred), sparse, **PANEL)
        named = scramble_check(panel_study(centred), sparse, columns=["close"], **PANEL)
        self.assertEqual(named.verdict, "LEAK")
        self.assertIn("spread", named.unscrambled_columns)


class CompareDecisions(unittest.TestCase):
    CUTOFF = CUTOFFS[1]

    def tables(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        data = prices()
        return CLEAN(data), CLEAN(data[data.time <= pd.Timestamp(self.CUTOFF)])

    def compare(self, reference, candidate, **kw):
        kw = {"time_column": "time", "key_columns": ("time", "asset"), **kw}
        return compare_decisions(reference, candidate, cutoff=self.CUTOFF, **kw)

    def test_identical_decisions_pass_and_later_decisions_are_counted(self):
        report = self.compare(*self.tables())
        result = report.cutoffs[0]
        self.assertEqual((report.check, report.verdict, report.input_rows), (COMPARE, "PASS", None))
        self.assertEqual((result.reference_rows, result.reference_in_scope), (108, 63))
        self.assertEqual((result.candidate_rows, result.decisions_compared), (63, 63))

    def test_row_and_column_order_do_not_matter(self):
        reference, candidate = self.tables()
        shuffled = candidate.sample(frac=1, random_state=3)[candidate.columns[::-1]]
        self.assertEqual(self.compare(reference, shuffled).verdict, "PASS")

    def test_a_change_after_the_cutoff_is_not_a_leak(self):
        reference, candidate = self.tables()
        later = reference.time > pd.Timestamp(self.CUTOFF)
        reference.loc[later, "score"] = -1.0
        self.assertEqual(self.compare(reference, candidate).verdict, "PASS")

    def test_each_kind_of_difference_is_reported(self):
        reference, candidate = self.tables()
        first = candidate.sort_values(["time", "asset"]).index[0]
        extra = candidate.loc[[first]].assign(asset="Z")
        changed = candidate.copy()
        changed.loc[first, "score"] = 1.5
        cases = [
            (candidate.drop(index=first), ONLY_IN_REFERENCE, None, None),
            (pd.concat([candidate, extra]), ONLY_IN_CANDIDATE, None, None),
            (changed, VALUE_DIFFERS, "score", "1.5"),
        ]
        for table, kind, column, text in cases:
            with self.subTest(kind=kind):
                report = self.compare(reference, table)
                self.assertEqual(report.verdict, "LEAK")
                self.assertEqual(report.cutoffs[0].decisions_differing, 1)
                difference = report.first_leak.first_difference
                self.assertEqual((difference.kind, difference.column), (kind, column))
                self.assertEqual(difference.decision_time, "2026-01-05T00:00:00Z")
                self.assertEqual(difference.candidate, text)

    def test_a_decision_moved_past_the_cutoff_differs_in_its_time(self):
        reference = pd.DataFrame(
            {"id": ["a", "b"], "time": ["2026-01-20T00:00:00Z", "2026-01-21T00:00:00Z"]}
        )
        candidate = reference.assign(time=["2026-01-20T00:00:00Z", "2026-01-26T00:00:00Z"])
        report = self.compare(reference, candidate, key_columns=("id",))
        difference = report.first_leak.first_difference
        self.assertEqual(
            (difference.kind, difference.key, difference.column), (VALUE_DIFFERS, ("b",), "time")
        )
        self.assertEqual(
            (difference.reference, difference.candidate),
            ("2026-01-21T00:00:00Z", "2026-01-26T00:00:00Z"),
        )

    def test_mismatched_columns_and_an_empty_scope_are_refused(self):
        reference, candidate = self.tables()
        with self.assertRaisesRegex(LookaheadCheckError, r"only in candidate \['extra'\]"):
            self.compare(reference, candidate.assign(extra=1))
        with self.assertRaisesRegex(LookaheadCheckError, "no decision in either table"):
            compare_decisions(
                reference,
                candidate,
                time_column="time",
                key_columns=("time", "asset"),
                cutoff="2025-12-31T00:00:00Z",
            )


class EdgeCases(unittest.TestCase):
    def test_empty_data_is_refused(self):
        for check in CHECKS:
            with self.subTest(check=check.__name__):
                with self.assertRaisesRegex(LookaheadCheckError, "data is empty"):
                    check(CLEAN, prices().iloc[0:0], cutoffs=CUTOFFS, **COLUMNS)

    def test_a_study_without_decisions_is_refused(self):
        def nothing(data: pd.DataFrame) -> pd.DataFrame:
            return CLEAN(data).iloc[0:0]

        with self.assertRaisesRegex(LookaheadCheckError, "made no decisions"):
            truncation_check(nothing, prices(), cutoffs=CUTOFFS, **COLUMNS)

    def test_unsorted_input_is_cut_by_time_not_by_position(self):
        shuffled = prices().sample(frac=1, random_state=11)
        for decide in (CLEAN, LEAKS["centred rolling mean"]):
            for check in CHECKS:
                with self.subTest(check=check.__name__):
                    in_order = check(decide, prices(), cutoffs=CUTOFFS, **COLUMNS)
                    mixed = check(decide, shuffled, cutoffs=CUTOFFS, **COLUMNS)
                    if check is truncation_check:
                        self.assertEqual(mixed.cutoffs, in_order.cutoffs)
                    self.assertEqual(mixed.verdict, in_order.verdict)
                    self.assertEqual(
                        [c.values_replaced for c in mixed.cutoffs],
                        [c.values_replaced for c in in_order.cutoffs],
                    )

    def test_offset_times_are_compared_in_utc(self):
        utc = truncation_check(CLEAN, prices(), cutoffs=CUTOFFS, **COLUMNS)
        jakarta = prices().assign(time=prices().time.dt.tz_convert("Asia/Jakarta"))
        text = jakarta.assign(time=jakarta.time.map(lambda t: t.isoformat()))
        wib = [
            "2026-01-15T07:00:00+07:00",
            "2026-01-25T07:00:00+07:00",
            "2026-02-02T07:00:00+07:00",
        ]
        for data in (jakarta, text):
            with self.subTest(dtype=str(data.time.dtype)):
                report = truncation_check(CLEAN, data, cutoffs=wib, **COLUMNS)
                self.assertEqual(report.cutoffs, utc.cutoffs)
                self.assertEqual(report.cutoffs[0].cutoff, "2026-01-15T00:00:00Z")

    def test_naive_times_are_refused_unless_utc_is_stated(self):
        naive = prices().assign(time=prices().time.dt.tz_localize(None))
        with self.assertRaisesRegex(LookaheadCheckError, "assume_utc=True"):
            truncation_check(CLEAN, naive, cutoffs=CUTOFFS, **COLUMNS)
        with self.assertRaisesRegex(LookaheadCheckError, "without a UTC offset"):
            truncation_check(CLEAN, prices(), cutoffs=["2026-01-15"], **COLUMNS)
        stated = truncation_check(
            CLEAN,
            naive,
            cutoffs=["2026-01-15", "2026-01-25", "2026-02-02"],
            assume_utc=True,
            **COLUMNS,
        )
        self.assertTrue(stated.assume_utc)
        self.assertEqual(
            stated.cutoffs, truncation_check(CLEAN, prices(), cutoffs=CUTOFFS, **COLUMNS).cutoffs
        )

    def test_epoch_numbers_and_mixed_or_missing_times_are_refused(self):
        epoch = prices().assign(time=prices().time.astype("int64") // 10**9)
        mixed = prices().assign(time=prices().time.map(lambda t: t.isoformat()))
        mixed.loc[0, "time"] = "2026-01-01T00:00:00"
        missing = prices().assign(time=prices().time.astype(object))
        missing.loc[5, "time"] = None
        for data, message in (
            (epoch, "epoch numbers are refused"),
            (mixed, "without a UTC offset"),
            (missing, "missing at row 5"),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(LookaheadCheckError, message):
                    truncation_check(CLEAN, data, cutoffs=CUTOFFS, **COLUMNS)

    def test_duplicate_or_missing_decision_keys_are_refused(self):
        def duplicated(data: pd.DataFrame) -> pd.DataFrame:
            decisions = CLEAN(data)
            return pd.concat([decisions, decisions.iloc[:1]])

        def keyless(data: pd.DataFrame) -> pd.DataFrame:
            return CLEAN(data).assign(asset=None)

        with self.assertRaisesRegex(
            LookaheadCheckError, r"duplicate key \('2026-01-05T00:00:00Z', 'A'\)"
        ):
            truncation_check(duplicated, prices(), cutoffs=CUTOFFS, **COLUMNS)
        with self.assertRaisesRegex(LookaheadCheckError, "key column 'asset' is missing"):
            truncation_check(keyless, prices(), cutoffs=CUTOFFS, **COLUMNS)
        with self.assertRaisesRegex(LookaheadCheckError, "reset_index"):
            truncation_check(
                lambda d: CLEAN(d).set_index("asset"), prices(), cutoffs=CUTOFFS, **COLUMNS
            )

    def test_nondeterministic_or_malformed_studies_are_refused(self):
        def random(data: pd.DataFrame) -> pd.DataFrame:
            return CLEAN(data).assign(score=lambda d: np.random.default_rng().random(len(d)))

        with self.assertRaisesRegex(LookaheadCheckError, "not deterministic"):
            truncation_check(random, prices(), cutoffs=CUTOFFS, **COLUMNS)
        with self.assertRaisesRegex(LookaheadCheckError, "must be a pandas DataFrame, not list"):
            truncation_check(lambda d: [], prices(), cutoffs=CUTOFFS, **COLUMNS)
        with self.assertRaisesRegex(LookaheadCheckError, "must be callable"):
            truncation_check(None, prices(), cutoffs=CUTOFFS, **COLUMNS)

    def test_uninformative_or_malformed_cutoffs_are_refused(self):
        for cutoffs, message in (
            (["2026-02-09T00:00:00Z"], "changes no input value"),
            (["2026-01-02T00:00:00Z"], "before the first decision"),
            ([CUTOFFS[0], CUTOFFS[0]], "distinct"),
            (CUTOFFS[0], "nonempty sequence"),
            ([], "nonempty sequence"),
        ):
            with self.subTest(cutoffs=cutoffs):
                with self.assertRaisesRegex(LookaheadCheckError, message):
                    truncation_check(CLEAN, prices(), cutoffs=cutoffs, **COLUMNS)

    def test_invalid_scramble_and_lag_settings_are_refused(self):
        for settings, message in (
            ({"columns": ["asset"]}, "only numpy float, integer and bool"),
            ({"columns": ["time"]}, "not a data value column"),
            ({"columns": "close"}, "nonempty sequence"),
            ({"missing_share": 1.0}, r"\[0, 1\)"),
            ({"seed": -1}, "nonnegative integer"),
            ({"seed": True}, "nonnegative integer"),
            ({"value_lags": {"volume": timedelta(days=1)}}, "cannot hold a missing value"),
            ({"value_lags": {"close": timedelta(0)}}, "positive timedelta"),
            ({"value_lags": {"close": 3}}, "positive timedelta"),
            ({"value_lags": ["close"]}, "must map column names"),
            (
                {"columns": ["volume"], "value_lags": {"close": timedelta(days=1)}},
                "must also be scrambled",
            ),
        ):
            with self.subTest(settings=settings):
                with self.assertRaisesRegex(LookaheadCheckError, message):
                    scramble_check(CLEAN, prices(), cutoffs=CUTOFFS, **COLUMNS, **settings)


if __name__ == "__main__":
    unittest.main()
