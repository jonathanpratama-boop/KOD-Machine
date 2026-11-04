import unittest

import numpy as np
import pandas as pd

from idxsig import idx_events as ie
from idxsig.execution import ExecConfig

from tests.support import random_walk_panel, synthetic_registry


def ts(s):
    return pd.Timestamp(s)


class SessionMappingTests(unittest.TestCase):
    def setUp(self):
        self.dates = np.busday_offset(
            np.datetime64("2023-01-02", "D"), np.arange(30), roll="forward"
        )

    def idx(self, d):
        return int(np.searchsorted(self.dates, np.datetime64(d, "D")))

    def test_morning_news_is_bought_at_that_days_close(self):
        s = ie.signal_session(self.dates, ts("2023-01-09T10:00:00+07:00"))
        self.assertEqual(s, self.idx("2023-01-09") - 1)  # entry at s + 1 = that day's close

    def test_the_cutoff_is_inclusive(self):
        d = self.idx("2023-01-09")
        self.assertEqual(ie.signal_session(self.dates, ts("2023-01-09T14:30:00+07:00")), d - 1)
        self.assertEqual(ie.signal_session(self.dates, ts("2023-01-09T14:31:00+07:00")), d)

    def test_news_after_the_cutoff_waits_for_the_next_close(self):
        self.assertEqual(
            ie.signal_session(self.dates, ts("2023-01-09T18:00:00+07:00")), self.idx("2023-01-09")
        )

    def test_weekend_news_is_bought_at_monday_close(self):
        s = ie.signal_session(self.dates, ts("2023-01-14T11:00:00+07:00"))  # a Saturday
        self.assertEqual(s, self.idx("2023-01-13"))  # signal Friday, entry Monday's close

    def test_no_session_before_the_first(self):
        self.assertIsNone(ie.signal_session(self.dates, ts("2023-01-01T08:00:00+07:00")))
        self.assertIsNone(
            ie.signal_session(self.dates, ts("2023-01-02T09:00:00+07:00"))
        )  # needs the session before it


def planted(n_sessions=200, drift_names=8, seed=3):
    df, meta = random_walk_panel(
        n_tickers=40, n_sessions=n_sessions, seed=seed, drift={i: 0.004 for i in range(drift_names)}
    )
    reg, _ = synthetic_registry(df, meta)
    return df, meta, reg


class RunEventsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df, cls.meta, cls.reg = planted()
        dates = sorted(cls.df["date"].unique())
        cls.prep = ie.prepare(cls.df, cls.reg, str(dates[0].date()), str(dates[-1].date()))
        cls.dates = cls.prep.m.dates
        cls.cfg = ExecConfig(holding_days=20, ca_mode="registry", max_participation=0.5)

    def events(self, rows):
        return pd.DataFrame(
            [{"ticker": t, "posted_wib": f"{self.dates[i]}T16:00:00+07:00"} for t, i in rows]
        )

    def test_a_planted_drift_shows_up_as_excess_over_matched_controls(self):
        ev = self.events([(f"S{i:03d}", 70 + 4 * i) for i in range(8)])
        res = ie.run_events(self.prep, ev, self.cfg, draws=60)
        f = ie.filled(res)
        self.assertGreaterEqual(len(f), 6)
        self.assertGreater(f.net_return.mean(), 0.04)
        self.assertGreater(f.excess.mean(), 0.03)
        self.assertTrue((f.control_n > 20).all())
        self.assertTrue(
            (res.entry_date > res.signal_date).all()
            or (res.entry_date[res.entry_date != ""] > res.signal_date[res.entry_date != ""]).all()
        )

    def test_no_drift_no_excess(self):
        ev = self.events([(f"S{i:03d}", 70 + 3 * (i - 10)) for i in range(10, 40)])
        f = ie.filled(ie.run_events(self.prep, ev, self.cfg, draws=60))
        self.assertGreater(len(f), 20)
        self.assertLess(abs(f.excess.mean()), 0.03)

    def test_overlap_while_held_is_skipped(self):
        ev = self.events([("S001", 80), ("S001", 85), ("S001", 120)])
        res = ie.run_events(self.prep, ev, self.cfg, draws=20)
        self.assertEqual(list(res.status)[1], "SKIP_OVERLAP")
        self.assertNotEqual(list(res.status)[2], "SKIP_OVERLAP")
        self.assertEqual(ie.status_counts(res)["SKIP_OVERLAP"], 1)

    def test_unknown_tickers_and_late_events(self):
        ev = self.events([("ZZZZ", 80), ("S002", 195)])
        res = ie.run_events(self.prep, ev, self.cfg, draws=20)
        self.assertEqual(len(res), 1)  # the unknown ticker is not mapped
        self.assertEqual(
            res.status.iloc[0], "INCOMPLETE"
        )  # 20 sessions do not fit before the data ends
        self.assertTrue(np.isnan(res.net_return.iloc[0]))
        self.assertEqual(len(ie.filled(res)), 0)

    def test_history_is_counted_on_the_whole_panel_not_the_window(self):
        dates = self.dates
        prep = ie.prepare(
            self.df, self.reg, str(dates[80]), str(dates[-1])
        )  # the window starts at session 80
        self.assertGreater(
            prep.evaluable[:, 0].sum(), 20
        )  # names with 80 sessions of history already
        res = ie.run_events(
            prep,
            pd.DataFrame([{"ticker": "S030", "posted_wib": f"{dates[85]}T16:00:00+07:00"}]),
            self.cfg,
            draws=20,
        )
        self.assertGreater(res.control_n.iloc[0], 0)

    def test_an_event_with_no_possible_control_does_not_stop_the_run(self):
        dates = self.dates
        early = pd.DataFrame(
            [
                {
                    "ticker": "S003",
                    "posted_wib": f"{dates[10]}T16:00:00+07:00",
                },  # nobody has 60 sessions yet
                {"ticker": "S003", "posted_wib": f"{dates[90]}T16:00:00+07:00"},
            ]
        )
        res = ie.run_events(self.prep, early, self.cfg, draws=20)
        self.assertEqual(len(res), 2)
        self.assertEqual(res.control_n.iloc[0], 0)
        self.assertTrue(np.isnan(res.excess.iloc[0]))
        self.assertGreater(res.control_n.iloc[1], 0)

    def test_the_mean_is_over_the_scored_draws_only(self):
        nan = np.nan
        net = np.array([[0.1, 0.2, nan], [nan, 0.4, nan], [0.3, nan, nan]])
        scored = np.array([[True, True, False], [False, True, False], [True, False, False]])
        np.testing.assert_allclose(ie.mean_over_scored(net, scored), [0.2, 0.3, nan])

    def test_unbuyable_control_draws_do_not_erase_the_control_mean(self):
        cfg = ExecConfig(
            holding_days=20, ca_mode="registry", max_participation=0.05
        )  # a tight cap leaves some draws unbuyable
        res = ie.run_events(
            self.prep, self.events([(f"S{i:03d}", 70 + 4 * i) for i in range(8, 30)]), cfg, draws=40
        )
        ex = res[res.status == "EXITED"]
        partial = ex[(ex.control_n > 0) & (ex.control_n < 40)]
        self.assertGreater(len(partial), 0)  # the case this test is about exists
        self.assertTrue(ex[ex.control_n > 0].control_mean.notna().all())
        self.assertEqual(len(ie.filled(res)), int((ex.control_n > 0).sum()))

    def test_same_seed_same_controls(self):
        ev = self.events([(f"S{i:03d}", 70 + 4 * i) for i in range(5)])
        a = ie.run_events(self.prep, ev, self.cfg, draws=30, seed=5)
        b = ie.run_events(self.prep, ev, self.cfg, draws=30, seed=5)
        pd.testing.assert_frame_equal(a, b)
        c = ie.run_events(self.prep, ev, self.cfg, draws=30, seed=6)
        self.assertFalse(np.allclose(a.control_mean.fillna(0), c.control_mean.fillna(0)))


if __name__ == "__main__":
    unittest.main()
