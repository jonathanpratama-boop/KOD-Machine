"""Experiment E1 mechanics on a synthetic panel with injected repricings. Each test names
the failure it guards against."""

import tempfile
import unittest
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from idxsig import e1


def jumpy_panel(n=40, s=820, seed=3):
    rng = np.random.default_rng(seed)
    dates = pd.to_datetime(np.busday_offset(np.datetime64("2020-11-02", "D"), np.arange(s), roll="forward"))
    rows = []
    for i in range(n):
        price, left = float(rng.choice([150, 480, 1500])), 0
        for d in range(s):
            prev = price
            if left == 0 and rng.random() < 0.004:
                left = 3
            vol = int(rng.integers(100_000, 1_000_000))
            if left:
                step, left, vol = 0.2, left - 1, vol * 8
            else:
                step = float(np.clip(rng.normal(0, 0.02), -0.06, 0.06))
            price = max(round(prev * (1 + step)), 50)
            rows.append({"date": dates[d], "ticker": f"S{i:03d}", "source": "synthetic", "previous": int(prev),
                         "open": pd.NA, "high": int(max(prev, price)), "low": int(min(prev, price)),
                         "close": int(price), "volume": vol, "value": int(vol * price), "frequency": 100,
                         "listed_shares": 10**9, "tradable_shares": 10**9})
    df = pd.DataFrame(rows)
    for c in ("previous", "open", "high", "low", "close", "volume", "value", "frequency", "listed_shares",
              "tradable_shares"):
        df[c] = df[c].astype("Int64")
    return df, {"sha256": "synthetic", "panel": "synthetic", "source_boundary": str(dates[-1].date()),
                "format": "panel-v2"}


class E1Mechanics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        warnings.simplefilter("ignore")
        cls.df, cls.meta = jumpy_panel()
        cls.study = e1.Study(cls.df, cls.meta)

    def test_holdout_is_sealed(self):
        """Guards against: holdout labels being formed at all (the study's market ends at validation's end)."""
        df, meta = jumpy_panel(n=6, s=1000)
        st = e1.Study(df, meta)
        self.assertLessEqual(str(st.dates[-1]), "2023-12-29")
        self.assertGreater(str(df["date"].max().date()), "2024-06-01")

    def test_forward_window_never_crosses_a_period_boundary(self):
        """Guards against: discovery labels using validation-period prices."""
        st = self.study
        lo, hi = st.m.bounds(*st.periods["discovery"])
        last = np.flatnonzero(st.elig["discovery"].any(axis=0)).max()
        self.assertLessEqual(last + e1.HORIZON, hi - 1)

    def test_episode_starts_are_the_first_qualifying_day(self):
        """Guards against: counting one repricing as several events, or starting it after it began."""
        st = self.study
        for x in e1.THRESHOLDS:
            n, d = np.nonzero(st.start[x])
            for k in range(1, e1.HORIZON + 1):
                ok = d - k >= 0
                self.assertFalse(st.qraw[x][n[ok], d[ok] - k].any())

    def test_labels_use_only_later_closes(self):
        """Guards against: an off-by-one that puts the decision day's own move into the label."""
        st = self.study
        n, d = np.argwhere(st.start[0.30] & st.elig["discovery"])[0]
        L = st.level[n]
        expect = max(L[d + k] / L[d] - 1 for k in range(1, 6) if np.isfinite(L[d + k]))
        self.assertAlmostEqual(st.r5max[n, d], expect)

    def test_controls_are_same_session_non_events_of_other_names(self):
        """Guards against: controls drawn from another day, from winners, or from the event's own ticker."""
        st = self.study
        events = st.episodes("discovery", 0.30).head(20)
        ctrl = st.matched_controls(events, "discovery")
        merged = ctrl.merge(events.reset_index().rename(columns={"index": "event_index"})[["event_index", "date", "ticker"]],
                            on="event_index", suffixes=("", "_event"))
        self.assertTrue((merged["date"] == merged["date_event"]).all())
        self.assertTrue((merged["ticker"] != merged["ticker_event"]).all())
        self.assertTrue((ctrl["r5max"] < 0.30).all())
        self.assertEqual(ctrl.groupby("event_index").size().min(), e1.N_CONTROLS)

    def test_selection_follows_the_preregistered_rule(self):
        """Guards against: picking a detector on anything but discovery lift with the admissibility floor."""
        table = self.study.detector_table("discovery")
        chosen = e1.Study.select(table)
        adm = table[table["admissible"]]
        self.assertTrue((adm["flags"] >= 200).all())
        self.assertEqual(chosen, adm.sort_values(["E30_lift", "flags"], ascending=False).iloc[0]["rule"])
        self.assertIsNone(e1.Study.select(table.assign(admissible=False)))

    def test_stage_outputs_are_never_overwritten(self):
        """Guards against: re-running a stage over its earlier results."""
        out = Path(tempfile.mkdtemp()) / "disc"
        e1.run_discovery(self.study, out)
        with self.assertRaises(FileExistsError):
            e1.run_discovery(self.study, out)


class E2OnOtherMarkets(unittest.TestCase):
    def test_study_runs_with_the_us_profile_and_family_g(self):
        """Guards against: the E2 path (no price limits, opens, family G, global panel format) failing
        only on real data, after the protocol is frozen."""
        from idxsig.profiles import US
        from idxsig.rules import moonshot_g

        df, meta = jumpy_panel(n=30)
        df["open"] = df["previous"].astype(float)
        for col in ("frequency", "listed_shares", "tradable_shares"):
            df[col] = np.nan
        meta = {**meta, "format": "panel-global-v1"}
        st = e1.Study(df, meta, protocol_path=e1.PKG_ROOT / "research" / "E2" / "protocol.json", profile=US,
                      family_module=moonshot_g)
        self.assertFalse(st.m.lock_up.any())
        out = Path(tempfile.mkdtemp())
        summary = e1.run_discovery(st, out / "disc")
        self.assertEqual(summary["protocol_id"], "KOD-GLOBAL-E2-v1")
        table = pd.read_csv(out / "disc" / "detector_selection.csv")
        self.assertEqual(len(table), 11)
        self.assertIn("gap", pd.read_csv(out / "disc" / "signal_stats.csv")["signal"].tolist())


class DetectorShortWindows(unittest.TestCase):
    def test_features_handle_windows_shorter_than_their_lookbacks(self):
        """Guards against: the harness's first prefix calls (1..60 sessions) crashing the detector (v1 bug)."""
        from idxsig.rules import moonshot_e1 as family

        for cols in (1, 2, 5, 19, 61):
            a = np.ones((3, cols))
            f = family.features(a * 100, a * 100, a * 101, a * 99, a * 1e6, a > 0, a > 0, a < 0)
            for name, arr in f.items():
                self.assertEqual(arr.shape, (3, cols), name)


if __name__ == "__main__":
    unittest.main()
