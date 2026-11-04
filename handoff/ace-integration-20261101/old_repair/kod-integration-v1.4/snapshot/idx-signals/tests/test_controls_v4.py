"""Matched controls v4 (PR #8 review, 2026-10-15): v3 with a window-invariant listing age. v1-v3 count
listing_age from the first session of the market they are given and call every name present there "older",
so a window that starts after a listing changes the bucket (disclosed in research/E5/v1.1/protocol.json,
addendum.disclosed_not_fixed). v4 counts from the first listed session with Market.listed_before and keeps
a history that starts at the data's first session unknown below 250 sessions (Market.listing_censored).

Each test names the failure it guards against. Synthetic markets only."""

import unittest

import numpy as np

from idxsig import controls
from idxsig.backtest import RunConfig
from idxsig.execution import Market
from tests.support import random_walk_panel
from tests.support import run_synthetic as run
from tests.test_controls_v3 import frozen_features_pre_v3

N = 420
IPO = {
    3: 30,
    7: 150,
    11: 300,
}  # ticker index: first listed session; the other names start at session 0


def _market(n_tickers=14, n_sessions=N, ipo=None, **kw):
    df, meta = random_walk_panel(
        n_tickers=n_tickers, n_sessions=n_sessions, ipo=IPO if ipo is None else ipo, **kw
    )
    return Market.from_panel(df), df, meta


class ListingAgeV4(unittest.TestCase):
    def test_buckets_count_from_the_first_listed_session_and_keep_the_start_unknown(self):
        """Guards against: a name present at the data's first session called established before 250
        sessions of its history are known (v1-v3 call it older from its first session), or a new listing
        bucketed off its first-session count."""
        m, _, _ = _market()
        age = controls.features(m, "v4")["listing_age"]
        self.assertTrue(bool(m.listing_censored[0]) and not m.listing_censored[3])
        self.assertEqual(age[0, 0], -1)  # history starts at the data: unknown
        self.assertEqual(age[0, 249], -1)
        self.assertEqual(age[0, 250], 2)  # a lower bound of 250 sessions: older
        self.assertEqual(age[3, 29], -1)  # not listed yet
        self.assertEqual(age[3, 30], 0)
        self.assertEqual(age[3, 30 + 60], 1)
        self.assertEqual(age[3, 30 + 250], 2)
        v3 = controls.features(m, "v3")["listing_age"]
        self.assertEqual(v3[0, 0], 2)  # what v3 says: older from the first session
        np.testing.assert_array_equal(
            v3[3], age[3]
        )  # a listing inside the data: the same in v3 and v4

    def test_any_window_gets_the_buckets_of_the_whole_market(self):
        """Guards against: the v1-v3 defect itself, a window start that moves a name's bucket."""
        m, _, _ = _market()
        full = controls.features(m, "v4")["listing_age"]
        for lo in (1, 45, 100, 200, 280, 310):
            part = m.slice(lo, N)
            np.testing.assert_array_equal(
                controls.features(part, "v4")["listing_age"],
                full[:, lo:],
                err_msg=f"window from session {lo}",
            )
            again = part.slice(17, part.shape[1])  # a window of a window
            np.testing.assert_array_equal(
                controls.features(again, "v4")["listing_age"],
                full[:, lo + 17 :],
                err_msg=f"window from session {lo} + 17",
            )
        # the defect, reproduced on v3: name 3 listed at session 30 is "older" in a window from session 45
        v3_part = controls.features(m.slice(45, N), "v3")["listing_age"]
        self.assertEqual(v3_part[3, 0], 2)
        self.assertEqual(controls.features(m, "v3")["listing_age"][3, 45], 0)

    def test_a_window_built_from_a_frame_with_its_listing_history(self):
        """Guards against: losing the history when the window is a panel frame cut before the Market is built
        (e5.build_study's route: a per-name sessions_listed_before column)."""
        m, df, _ = _market()
        lo = 100
        dates = np.array(sorted(df["date"].unique()))
        cut = df[df["date"] >= dates[lo]].copy()
        part = m.slice(lo, N)
        cut["sessions_listed_before"] = cut["ticker"].map(dict(zip(m.tickers, part.listed_before)))
        built = Market.from_panel(cut)
        np.testing.assert_array_equal(built.listed_before, part.listed_before)
        full = controls.features(m, "v4")["listing_age"]
        # names listed inside the data: identical; names present since the data start: the frame carries a count
        # only, so they read as listed (a declared limit of that route), which agrees once the count reaches 250
        listed = ~m.listing_censored
        np.testing.assert_array_equal(
            controls.features(built, "v4")["listing_age"][listed], full[listed, lo:]
        )
        late = 250 - lo
        np.testing.assert_array_equal(
            controls.features(built, "v4")["listing_age"][:, late:], full[:, lo + late :]
        )

    def test_features_use_only_past_data(self):
        """Guards against: a v4 bucket computed with data after its session."""
        m, _, _ = _market(n_tickers=10, n_sessions=330)
        full = controls.features(m, "v4")
        for cut in (25, 61, 249, 251, 305):
            part = controls.features(m.truncate(cut), "v4")
            for name in controls.VERSIONS["v4"]:
                np.testing.assert_array_equal(
                    full[name][:, : cut + 1], part[name], err_msg=f"{name} cut {cut}"
                )

    def test_market_carries_the_censoring_through_every_copy(self):
        """Guards against: a slice, registry or unit copy that re-derives the flag from its own first column."""
        m, _, _ = _market()
        part = m.slice(100, N)
        np.testing.assert_array_equal(part.listing_censored, m.listing_censored)
        self.assertTrue(part.present[7].any() and not part.present[7, 0])
        self.assertTrue(
            bool(part.present[3, 0])
            and int(part.listed_before[3]) == 70
            and not part.listing_censored[3]
        )
        np.testing.assert_array_equal(m.truncate(10).listing_censored, m.listing_censored)
        units = m.with_units(np.ones(m.shape))
        np.testing.assert_array_equal(units.listing_censored, m.listing_censored)


class V4AgainstEarlierVersions(unittest.TestCase):
    def test_v1_to_v3_are_unchanged(self):
        """Guards against: the v4 change leaking into the versions the recorded runs used."""
        m, _, _ = _market()
        for version in ("v1", "v2"):
            live, frozen = controls.features(m, version), frozen_features_pre_v3(m, version)
            self.assertEqual(set(live), set(frozen))
            for name in live:
                np.testing.assert_array_equal(live[name], frozen[name], err_msg=f"{version} {name}")
        v3, v4 = controls.features(m, "v3"), controls.features(m, "v4")
        self.assertEqual(controls.VERSIONS["v4"], controls.VERSIONS["v3"])
        for name in controls.VERSIONS["v3"]:
            if name != "listing_age":
                np.testing.assert_array_equal(v3[name], v4[name], err_msg=name)
        self.assertEqual(controls.feature("volatility", "v4"), controls.feature("volatility", "v3"))
        self.assertEqual(controls.feature("listing_age", "v3"), controls.FEATURES["listing_age"])

    def test_run_records_v4_and_the_default_stays_v2(self):
        """Guards against: a v4 run reported as another version, or v4 becoming anyone's default."""
        df, meta = random_walk_panel(n_tickers=20, n_sessions=80, ipo={4: 20})
        s = run(RunConfig("PLACEBO_COINFLIP", random_draws=10, controls_version="v4"), df, meta)[
            "summary"
        ]
        self.assertEqual(s["harness"]["controls"], "v4")
        rm = s["random_matched"]
        self.assertEqual(rm["controls"]["version"], "v4")
        self.assertIn(
            "the same in any window", rm["controls"]["features"]["listing_age"]["description"]
        )
        self.assertTrue(set(rm["match_level_used"]) <= set(controls.level_names("v4")))
        self.assertEqual(sum(rm["match_level_used"].values()), s["signals"]["attempted"])
        self.assertEqual(RunConfig("PLACEBO_COINFLIP").controls_version, "v2")


if __name__ == "__main__":
    unittest.main()
