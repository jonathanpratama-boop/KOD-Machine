"""e1.Study options added for E5 (panel_format from the protocol, the IGNITION guard, as-traded
price bands, the v3 detection pool). Every option is opt-in; the default path is the recorded E1/E2
path. Synthetic panels only. Each test names the failure it guards against."""

import json
import tempfile
import types
import unittest
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from idxsig import controls, e1
from idxsig.profiles import US
from idxsig.rules import moonshot_g
from tests.test_e1 import jumpy_panel

E2_PROTOCOL = e1.PKG_ROOT / "research" / "E2" / "protocol.json"
UNITS_FORMAT = "panel-global-v2-units"
SPLIT_TICKER = "S000"
SPLIT_FACTOR = 10.0  # adjusted -> as-traded: the source rescaled this name's early prices by 1/10


def us_panel(n=30, with_units=True, split_until="2022-06-30"):
    """jumpy_panel in the E2 US shape (opens, no share counts), optionally with a unit_factor column."""
    df, meta = jumpy_panel(n=n)
    # Dollar-scale prices for the split name so a 10x unit factor crosses the US band edges (1, 5, 20).
    split = (df["ticker"] == SPLIT_TICKER).to_numpy()
    for col in ("previous", "high", "low", "close"):
        df[col] = df[col].astype(float)
        df.loc[split, col] = df.loc[split, col] / 100
    df["open"] = df["previous"].astype(float)
    for col in ("frequency", "listed_shares", "tradable_shares"):
        df[col] = np.nan
    if with_units:
        factor = np.ones(len(df))
        early = (df["ticker"] == SPLIT_TICKER) & (df["date"] <= pd.Timestamp(split_until))
        factor[early.to_numpy()] = SPLIT_FACTOR
        df["unit_factor"] = factor
        meta = {**meta, "format": UNITS_FORMAT}
    else:
        meta = {**meta, "format": "panel-global-v1"}
    return df, meta


def protocol_with(panel_format, base=E2_PROTOCOL) -> Path:
    proto = json.loads(base.read_text(encoding="utf-8"))
    if panel_format is None:
        proto.pop("data", None)
    else:
        proto["data"] = {"panel_format": panel_format}
    path = Path(tempfile.mkdtemp()) / "protocol.json"
    path.write_text(json.dumps(proto, indent=2) + "\n", encoding="utf-8")
    return path


def us_study(df, meta, proto_path=None, **kw):
    return e1.Study(df, meta, protocol_path=proto_path or protocol_with(UNITS_FORMAT), profile=US,
                    family_module=moonshot_g, **kw)


def frames_equal(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    return list(a.columns) == list(b.columns) and a.equals(b)


class DefaultsUnchanged(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        warnings.simplefilter("ignore")
        cls.df, cls.meta = jumpy_panel()

    def test_explicit_legacy_options_equal_the_bare_call(self):
        """Guards against: the new keyword defaults changing anything the recorded E1 path produced."""
        bare = e1.Study(self.df, self.meta)
        explicit = e1.Study(self.df, self.meta, pool_units="panel", pool_version="v1")
        self.assertEqual(bare.pool_keys, ("price_band", "liquidity", "market_cap"))
        self.assertEqual(bare.pool_keys, explicit.pool_keys)
        self.assertEqual(set(bare.buckets), {"price_band", "liquidity", "market_cap"})
        self.assertIsNone(bare.m.unit_factor)
        self.assertTrue(frames_equal(bare.detector_table("discovery"), explicit.detector_table("discovery")))
        ev = bare.episodes("discovery", 0.30).head(20)
        ev2 = explicit.episodes("discovery", 0.30).head(20)
        self.assertTrue(frames_equal(ev, ev2))
        ctrl, ctrl2 = bare.matched_controls(ev, "discovery"), explicit.matched_controls(ev2, "discovery")
        self.assertTrue(frames_equal(ctrl, ctrl2))
        self.assertTrue(frames_equal(bare.signal_stats(ev, ctrl, "x"), explicit.signal_stats(ev2, ctrl2, "x")))
        self.assertEqual(json.dumps(bare.evaluate("F1_ARA", "validation"), sort_keys=True, default=float),
                         json.dumps(explicit.evaluate("F1_ARA", "validation"), sort_keys=True, default=float))
        self.assertNotIn("volatility_q", ev.columns)
        self.assertNotIn("close_as_traded", ev.columns)
        self.assertLessEqual(int(ctrl["match_relaxed_steps"].max()), 3)

    def test_a_unit_factor_column_alone_changes_nothing(self):
        """Guards against: the mere presence of unit_factor (US repair panel) re-banding the default pool."""
        df, meta = us_panel()
        plain, _ = us_panel(with_units=False)
        proto = protocol_with(UNITS_FORMAT)
        with_col = us_study(df, meta, proto)
        without = e1.Study(plain, {**meta, "format": "panel-global-v1"}, protocol_path=E2_PROTOCOL, profile=US,
                           family_module=moonshot_g)
        self.assertIsNotNone(with_col.m.unit_factor)  # carried for callers, not used by default
        for k in ("price_band", "liquidity", "market_cap"):
            np.testing.assert_array_equal(with_col.buckets[k], without.buckets[k])
        self.assertTrue(frames_equal(with_col.episodes("discovery", 0.30), without.episodes("discovery", 0.30)))

    def test_e1_protocol_declares_the_legacy_format(self):
        """Guards against: reading data.panel_format from E1's own protocol changing E1's panel check."""
        proto, _ = e1.protocol()
        self.assertEqual(proto["data"]["panel_format"], "panel-v2")
        with self.assertRaises(ValueError):
            e1.Study(self.df, {**self.meta, "format": "panel-v1"})


class PanelFormatFromProtocol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        warnings.simplefilter("ignore")
        cls.df, cls.meta = us_panel()

    def test_units_format_is_accepted_when_the_protocol_names_it(self):
        """Guards against: the US repair panel (panel-global-v2-units) failing Study's format check."""
        st = us_study(self.df, self.meta)
        self.assertEqual(st.panel_format, UNITS_FORMAT)
        self.assertEqual(st.protocol_id, "KOD-GLOBAL-E2-v1")

    def test_protocol_without_data_keeps_the_legacy_expectation(self):
        """Guards against: a protocol that never named a format silently accepting a different panel."""
        with self.assertRaises(ValueError):
            us_study(self.df, self.meta, protocol_with(None))
        plain, plain_meta = us_panel(with_units=False)
        st = us_study(plain, plain_meta, protocol_with(None))
        self.assertEqual(st.panel_format, "panel-global-v1")

    def test_panel_must_match_the_declared_format(self):
        """Guards against: a protocol naming one format and the study running on another."""
        with self.assertRaises(ValueError):
            us_study(self.df, {**self.meta, "format": "panel-global-v1"})
        with self.assertRaises(ValueError):
            us_study(self.df, {**self.meta, "format": "panel-global-v2"})

    def test_unknown_declared_formats_are_refused(self):
        """Guards against: a typo in a protocol's data.panel_format becoming a new accepted format."""
        with self.assertRaises(ValueError):
            us_study(self.df, {**self.meta, "format": "panel-global-v9"}, protocol_with("panel-global-v9"))
        self.assertEqual(e1.PANEL_FORMATS, ("panel-v2", "panel-global-v1", "panel-global-v2-units"))


def family_without_ignition():
    """The G family with its IGNITION member removed (an E5-style family has none)."""
    mod = types.ModuleType("family_no_ignition")
    mod.FEATURE_ARGS = moonshot_g.FEATURE_ARGS
    mod.FAMILY = tuple((n, d) for n, d in moonshot_g.FAMILY if "IGNITION" not in n)
    mod.features = moonshot_g.features
    mod.family_flags = lambda f: {k: v for k, v in moonshot_g.family_flags(f).items() if "IGNITION" not in k}
    mod.__file__ = moonshot_g.__file__
    return mod


class IgnitionGuard(unittest.TestCase):
    def test_a_family_without_ignition_builds_and_reports(self):
        """Guards against: KeyError / StopIteration in _signals when the family has no IGNITION member."""
        warnings.simplefilter("ignore")
        df, meta = us_panel(with_units=False)
        st = e1.Study(df, meta, protocol_path=E2_PROTOCOL, profile=US, family_module=family_without_ignition())
        self.assertTrue(np.isnan(st.sig["ign"]).all())
        table = st.detector_table("discovery")
        self.assertEqual(len(table), len(moonshot_g.FAMILY) - 1)
        self.assertNotIn("G5_IGNITION_D", table["rule"].tolist())
        ev = st.episodes("discovery", 0.30).head(5)
        stats = st.signal_stats(ev, st.matched_controls(ev, "discovery"), "x")
        ign = stats[stats["signal"] == "ign"].iloc[0]
        self.assertEqual(int(ign["events_with_value"]), 0)
        self.assertTrue(np.isnan(ign["auc"]))

    def test_a_family_with_ignition_is_unchanged(self):
        """Guards against: the guard altering the E1/E2 ign signal."""
        warnings.simplefilter("ignore")
        df, meta = us_panel(with_units=False)
        st = e1.Study(df, meta, protocol_path=E2_PROTOCOL, profile=US, family_module=moonshot_g)
        np.testing.assert_array_equal(st.sig["ign"], st.flags["G5_IGNITION_D"].astype(float))


class AsTradedPool(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        warnings.simplefilter("ignore")
        cls.df, cls.meta = us_panel()
        cls.st = us_study(cls.df, cls.meta, pool_units="as_traded")
        cls.legacy = us_study(cls.df, cls.meta)

    def test_market_carries_the_unit_factor(self):
        """Guards against: unit_factor attached to the full market but lost in the sealed slice."""
        m = self.st.m
        self.assertEqual(m.unit_factor.shape, m.shape)
        n = list(m.tickers).index(SPLIT_TICKER)
        early = m.dates <= np.datetime64("2022-06-30")
        self.assertTrue((m.unit_factor[n, early] == SPLIT_FACTOR).all())
        self.assertTrue((m.unit_factor[n, ~early] == 1.0).all())
        self.assertTrue((np.delete(m.unit_factor, n, axis=0) == 1.0).all())

    def test_price_band_uses_the_as_traded_close(self):
        """Guards against: the ERRATA wrong-band control defect (banding the rescaled price, not the traded one)."""
        st, m = self.st, self.st.m
        expect = controls.features(m, "v2", US.band_edges, as_traded=True)["price_band"]
        np.testing.assert_array_equal(st.buckets["price_band"], expect)
        n = list(m.tickers).index(SPLIT_TICKER)
        early = np.flatnonzero(m.present[n] & (m.dates <= np.datetime64("2022-06-30")))
        edges = np.array(US.band_edges, dtype=float)
        adjusted = m.close[n, early]
        band_traded = np.searchsorted(edges, adjusted * SPLIT_FACTOR, side="left")
        band_adjusted = np.searchsorted(edges, adjusted, side="left")
        np.testing.assert_array_equal(st.buckets["price_band"][n, early], band_traded)
        np.testing.assert_array_equal(self.legacy.buckets["price_band"][n, early], band_adjusted)
        self.assertTrue((band_traded != band_adjusted).any())  # the defect, by default: a different band
        for k in ("liquidity", "market_cap"):  # unit-free features are untouched
            np.testing.assert_array_equal(st.buckets[k], self.legacy.buckets[k])
        d = int(early[np.flatnonzero(band_traded != band_adjusted)[0]])
        row = st.row(n, d)
        self.assertEqual(row["price_band"], US.band_names[int(band_traded[early == d][0])])
        self.assertAlmostEqual(row["close_as_traded"], float(m.close[n, d]) * SPLIT_FACTOR)
        self.assertAlmostEqual(row["close"], float(m.close[n, d]))  # the panel close stays what it was
        self.assertNotEqual(row["price_band"], self.legacy.row(n, d)["price_band"])

    def test_controls_match_on_the_as_traded_band(self):
        """Guards against: an event in one traded band drawing controls from another."""
        st = self.st
        ev = st.episodes("discovery", 0.30)
        ctrl = st.matched_controls(ev, "discovery")
        full = ctrl[ctrl["match_relaxed_steps"] == 0]
        self.assertGreater(len(full), 0)
        merged = full.merge(ev.reset_index().rename(columns={"index": "event_index"})[["event_index", "price_band"]],
                            on="event_index", suffixes=("", "_event"))
        self.assertTrue((merged["price_band"] == merged["price_band_event"]).all())
        self.assertIn("close_as_traded", ctrl.columns)

    def test_as_traded_needs_a_unit_factor_column(self):
        """Guards against: as-traded matching silently running on a panel that has no unit factors."""
        plain, plain_meta = us_panel(with_units=False)
        with self.assertRaises(ValueError):
            us_study(plain, plain_meta, protocol_with(None), pool_units="as_traded")
        with self.assertRaises(ValueError):
            us_study(self.df, self.meta, pool_units="traded")


class PoolV3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        warnings.simplefilter("ignore")
        cls.df, cls.meta = jumpy_panel(n=120)  # enough names for full four-key matches to occur
        cls.st = e1.Study(cls.df, cls.meta, pool_version="v3")
        cls.legacy = e1.Study(cls.df, cls.meta)

    def test_volatility_quintile_comes_from_the_signal_vol20(self):
        """Guards against: a pool volatility defined differently from the vol20 the signals report."""
        st = self.st
        self.assertEqual(st.pool_keys, ("price_band", "liquidity", "volatility", "market_cap"))
        self.assertEqual(e1.POOL_VERSIONS["v1"], ("price_band", "liquidity", "market_cap"))
        v = st.buckets["volatility"]
        self.assertEqual(v.dtype, np.int8)
        self.assertEqual(set(np.unique(v)) - {-1}, {0, 1, 2, 3, 4})
        expect = controls._bucket(np.where(st.m.present, st.sig["vol20"], np.nan), 5)
        np.testing.assert_array_equal(v, expect)
        np.testing.assert_array_equal(v == -1, ~(st.m.present & np.isfinite(st.sig["vol20"])))
        for k in ("price_band", "liquidity", "market_cap"):
            np.testing.assert_array_equal(st.buckets[k], self.legacy.buckets[k])

    def test_controls_share_the_volatility_quintile_and_relax_to_min_pool(self):
        """Guards against: the extra key being carried but never matched on, or starving the pool."""
        st = self.st
        ev = st.episodes("discovery", 0.30)
        ctrl = st.matched_controls(ev, "discovery")
        self.assertIn("volatility_q", ev.columns)
        self.assertIn("volatility_q", ctrl.columns)
        self.assertEqual(ctrl.groupby("event_index").size().min(), e1.N_CONTROLS)
        self.assertLessEqual(int(ctrl["match_relaxed_steps"].max()), 4)
        cols = ["event_index", "price_band", "liquidity_q", "volatility_q", "market_cap_q"]
        merged = ctrl.merge(ev.reset_index().rename(columns={"index": "event_index"})[cols],
                            on="event_index", suffixes=("", "_event"))
        full = merged[merged["match_relaxed_steps"] == 0]
        one = merged[merged["match_relaxed_steps"] == 1]
        self.assertGreater(len(full), 0)
        self.assertGreater(len(one), 0)
        for k in ("price_band", "liquidity_q", "volatility_q", "market_cap_q"):
            self.assertTrue((full[k] == full[f"{k}_event"]).all(), k)
        # relaxation drops market_cap first, then volatility (controls v3 priority)
        for k in ("price_band", "liquidity_q", "volatility_q"):
            self.assertTrue((one[k] == one[f"{k}_event"]).all(), k)
        # the pool is the tightest level with at least N_CONTROLS names (MIN_POOL), as controls relax
        tick = pd.Index(st.m.tickers)
        day = pd.Index(st.dates.astype(str))
        elig = st.elig["discovery"]
        for e in ev.head(40).itertuples(index=False):
            n, d = tick.get_loc(e.ticker), day.get_loc(e.date)
            pool, steps = st._pool(n, d, elig)
            kept = st.pool_keys[: len(st.pool_keys) - steps]
            for k in kept:
                self.assertTrue((st.buckets[k][pool, d] == st.buckets[k][n, d]).all(), k)
            if steps < len(st.pool_keys):
                self.assertGreaterEqual(len(pool), e1.N_CONTROLS)
            if steps > 0:  # one key tighter would have starved the pool
                tighter = pool
                for k in st.pool_keys[: len(kept) + 1]:
                    tighter = tighter[st.buckets[k][tighter, d] == st.buckets[k][n, d]]
                self.assertLess(len(tighter), e1.N_CONTROLS)
        self.assertEqual(e1.N_CONTROLS, controls.MIN_POOL)

    def test_evaluate_runs_under_v3(self):
        """Guards against: the validation pool (evaluate) not honouring the extra key."""
        st = self.st
        res = st.evaluate("F1_ARA", "validation")
        self.assertIn("volatility_q", st.last_flags.columns)
        self.assertTrue(all(0 <= int(k) <= 4 for k in res["matched_random_relaxed_steps"]))

    def test_unknown_pool_version_is_refused(self):
        with self.assertRaises(ValueError):
            e1.Study(self.df, self.meta, pool_version="v2")


if __name__ == "__main__":
    unittest.main()
