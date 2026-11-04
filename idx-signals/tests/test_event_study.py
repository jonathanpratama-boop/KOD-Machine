import unittest

import numpy as np
import pandas as pd

from idxsig import event_study as es


def us_panel(
    n_tickers=40,
    n_sessions=200,
    seed=3,
    drift=None,
    start="2021-01-04",
    volume=(200_000, 3_000_000),
):
    rng = np.random.default_rng(seed)
    dates = pd.to_datetime(
        np.busday_offset(np.datetime64(start, "D"), np.arange(n_sessions), roll="forward")
    )
    rows = []
    for i in range(n_tickers):
        prev = float(rng.choice([4.0, 12.0, 30.0, 80.0]))
        mu = (drift or {}).get(i, 0.0)
        for d in range(n_sessions):
            o = prev * (1 + rng.normal(0, 0.004))
            c = o * (1 + float(np.clip(rng.normal(mu, 0.02), -0.15, 0.15)))
            vol = int(rng.integers(*volume))
            rows.append(
                {
                    "date": dates[d],
                    "ticker": f"U{i:03d}",
                    "previous": prev,
                    "open": o,
                    "high": max(o, c) * 1.005,
                    "low": min(o, c) * 0.995,
                    "close": c,
                    "volume": vol,
                    "value": vol * c,
                    "frequency": 100,
                    "unit_factor": 1.0,
                }
            )
            prev = c
    return pd.DataFrame(rows)


class TimingTests(unittest.TestCase):
    def setUp(self):
        self.dates = np.busday_offset(
            np.datetime64("2023-01-02", "D"), np.arange(30), roll="forward"
        )

    def idx(self, d):
        return int(np.searchsorted(self.dates, np.datetime64(d, "D")))

    def test_entry_is_the_open_of_the_first_session_after_the_date(self):
        self.assertEqual(
            es.entry_signal_session(self.dates, "2023-01-09"), self.idx("2023-01-09")
        )  # filed Monday: bought Tuesday's open (s + 1)
        self.assertEqual(
            es.entry_signal_session(self.dates, "2023-01-13"), self.idx("2023-01-13")
        )  # filed Friday: Monday's open
        self.assertEqual(
            es.entry_signal_session(self.dates, "2023-01-14"), self.idx("2023-01-13")
        )  # a Saturday: Monday's open
        self.assertEqual(es.entry_signal_session(self.dates, "2023-01-15"), self.idx("2023-01-13"))
        self.assertIsNone(
            es.entry_signal_session(self.dates, "2022-12-30")
        )  # nothing before the first session
        self.assertIsNone(es.entry_signal_session(self.dates, "2023-01-01"))


class RunEventsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = us_panel(drift={i: 0.004 for i in range(8)})
        dates = sorted(cls.df["date"].unique())
        cls.prep = es.prepare_us(cls.df, str(dates[0].date()), str(dates[-1].date()))
        cls.dates = cls.prep.m.dates
        cls.cfg = es.us_config(20, max_participation=0.5)

    def events(self, rows):
        return pd.DataFrame([{"ticker": t, "public_date": str(self.dates[i])} for t, i in rows])

    def test_entry_is_the_open_after_the_public_date_and_a_planted_drift_shows_as_excess(self):
        ev = self.events([(f"U{i:03d}", 70 + 4 * i) for i in range(8)])
        res = es.run_events(self.prep, ev, self.cfg, draws=60)
        f = es.filled(res)
        self.assertGreaterEqual(len(f), 6)
        self.assertTrue(
            (
                pd.to_datetime(res.entry_date[res.entry_date != ""])
                > pd.to_datetime(res.public_date[res.entry_date != ""])
            ).all()
        )
        row = res[res.entry_date != ""].iloc[0]
        j = int(np.searchsorted(self.dates, np.datetime64(row.entry_date, "D")))
        signal = int(np.searchsorted(self.dates, np.datetime64(row.public_date, "D")))
        self.assertEqual(j, signal + 1)  # the first session after the public date
        open_ = self.df[
            (self.df.ticker == row.ticker) & (self.df.date == pd.Timestamp(row.entry_date))
        ].open.iloc[0]
        self.assertAlmostEqual(row.entry_price, open_, places=6)  # bought at the open
        self.assertGreater(f.net_return.mean(), 0.03)
        self.assertGreater(f.excess.mean(), 0.02)
        self.assertTrue((f.control_n > 20).all())

    def test_no_drift_no_excess(self):
        ev = self.events([(f"U{i:03d}", 70 + 3 * (i - 10)) for i in range(10, 40)])
        f = es.filled(es.run_events(self.prep, ev, self.cfg, draws=60))
        self.assertGreater(len(f), 20)
        self.assertLess(abs(f.excess.mean()), 0.03)

    def test_unbuyable_control_draws_do_not_erase_the_control_mean(self):
        cfg = es.us_config(20, max_participation=0.001)  # a tight cap leaves many draws unbuyable
        res = es.run_events(
            self.prep, self.events([(f"U{i:03d}", 70 + 4 * i) for i in range(8, 30)]), cfg, draws=40
        )
        ex = res[res.status == "EXITED"]
        partial = ex[(ex.control_n > 0) & (ex.control_n < 40)]
        self.assertGreater(len(partial), 0)
        self.assertTrue(ex[ex.control_n > 0].control_mean.notna().all())

    def test_unknown_tickers_late_events_and_overlap(self):
        ev = self.events([("ZZZZ", 80), ("U002", 195), ("U001", 80), ("U001", 85)])
        res = es.run_events(self.prep, ev, self.cfg, draws=20)
        self.assertEqual(len(res), 3)  # the unknown ticker is not mapped
        self.assertEqual(
            res[res.ticker == "U002"].status.iloc[0], "INCOMPLETE"
        )  # 20 sessions do not fit before the data ends
        self.assertEqual(list(res[res.ticker == "U001"].status)[1], "SKIP_OVERLAP")

    def test_same_seed_same_controls(self):
        ev = self.events([(f"U{i:03d}", 70 + 4 * i) for i in range(5)])
        a = es.run_events(self.prep, ev, self.cfg, draws=30, seed=5)
        b = es.run_events(self.prep, ev, self.cfg, draws=30, seed=5)
        pd.testing.assert_frame_equal(a, b)


if __name__ == "__main__":
    unittest.main()
