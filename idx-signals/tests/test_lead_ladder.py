"""LEAD_LADDER_v1 machinery and the void rule, on synthetic data only."""

import json
import unittest
from pathlib import Path

import numpy as np

from idxsig import lead_ladder as ll
from idxsig import void
from idxsig.backtest import RunConfig
from tests.rulekit import module_rule, with_rule
from tests.support import random_walk_panel
from tests.support import run_synthetic as run

PROTO = json.loads(
    (
        Path(__file__).resolve().parents[1] / "research" / "LEAD_LADDER_v1" / "protocol.json"
    ).read_text()
)


def small_proto(**over):
    p = json.loads(json.dumps(PROTO))
    p["bootstrap"]["resamples"] = 300
    p["markets"] = {"SYN": {"can_confirm": True}}
    p.update(over)
    return p


def world(n=300, s=420, n_up=160, n_down=160, lead_up=3, lead_down=None, seed=1):
    """Random-walk levels with planted one-session +40% / -30% jumps at t+5, so the protocol's episode start (the
    earliest base from which the move completes within 5 sessions) is t, and a feature planted at t - lead."""
    rng = np.random.default_rng(seed)
    logret = rng.normal(0, 0.004, (n, s))
    feat = rng.normal(0, 1, (n, s))
    used = np.zeros((n, s), dtype=bool)
    planted = {"up": [], "down": []}
    for kind, count, total, lead in (
        ("up", n_up, np.log(1.40), lead_up),
        ("down", n_down, np.log(0.70), lead_down),
    ):
        k = 0
        while k < count:
            i, t = int(rng.integers(n)), int(rng.integers(60, s - 40))
            if used[i, t - 45 : t + 30].any():
                continue
            used[i, t - 45 : t + 30] = True
            logret[i, t + 5] += total
            if lead is not None:
                feat[i, t - lead] = 6.0
            planted[kind].append((i, t))
            k += 1
    level = np.exp(np.cumsum(logret, axis=1))
    present = np.ones((n, s), dtype=bool)
    prev = np.ones((n, s))
    zeros = np.zeros((n, s), dtype=np.int64)
    buckets = {"price_band": zeros, "liquidity": zeros, "market_cap": zeros}
    dates = (np.datetime64("2021-01-04", "D") + 2 * np.arange(s)).astype("datetime64[D]")
    return (
        level,
        present,
        prev,
        buckets,
        {"plant": feat, "noise": rng.normal(0, 1, (n, s))},
        dates,
        planted,
    )


def ladder(proto, **kw):
    level, present, prev, buckets, feats, dates, planted = world(**kw)
    lad = ll.Ladder(
        level, present, present, prev, buckets, feats, (), dates, (0, level.shape[1]), proto
    )
    return lad, planted


def lifts(lad, proto, kinds=("FAST_UP", "FAST_DOWN")):
    tab = __import__("pandas").concat([lad.table(k) for k in kinds], ignore_index=True)
    return ll.aggregate(tab, lad.dates, lad.feature_names, lad.binary, proto, "SYN"), tab


class EpisodeTests(unittest.TestCase):
    def test_qualifying_up_down_and_one_session_limit(self):
        lvl = np.array([[1.0, 1.0, 1.1, 1.2, 1.31, 1.31, 1.31, 1.31]])
        up = ll.qualifying(lvl, ll.Kind("U", 5, "up"))
        self.assertTrue(up[0, 1])  # 1.31 / 1.0 within 5 sessions
        self.assertFalse(up[0, 4])
        spike = np.array([[1.0, 1.0, 1.40, 1.40, 1.40, 1.40]])
        self.assertTrue(ll.qualifying(spike, ll.Kind("U", 5, "up"))[0, 1])
        self.assertFalse(
            ll.qualifying(spike, ll.Kind("S", 4, "up", max_day=1.15))[0, 1]
        )  # one +40% session
        down = np.array([[1.0, 0.9, 0.8, 0.75, 0.75, 0.75]])
        self.assertTrue(ll.qualifying(down, ll.Kind("D", 5, "down"))[0, 0])  # 0.75 <= 1/1.3
        self.assertTrue(
            ll.qualifying(down, ll.Kind("D", 5, "down", max_day=1.15))[0, 0]
        )  # no fall below -13% in a session

    def test_first_in_separates_episodes(self):
        q = np.array([[False, True, True, False, False, True, False, False, False, True]])
        self.assertEqual(np.flatnonzero(ll.first_in(q, 3)).tolist(), [1, 9])

    def test_planted_starts_are_found(self):
        lad, planted = ladder(small_proto())
        n, t = lad.events("FAST_UP")
        found = set(zip(n.tolist(), t.tolist()))
        hit = sum(1 for i, tt in planted["up"] if (i, tt) in found)
        self.assertGreater(hit, 0.9 * len(planted["up"]))


class LadderTests(unittest.TestCase):
    def test_planted_lead_is_recovered_at_its_lead_and_not_later(self):
        proto = small_proto()
        lad, _ = ladder(proto, lead_up=3)
        agg, _ = lifts(lad, proto)
        cell = agg[
            (agg.kind == "FAST_UP")
            & (agg.analysis == "void")
            & (agg.feature == "plant")
            & (agg["tail"] == "top")
        ]
        by = cell.set_index("lead")["lift"]
        self.assertGreater(by[3], 5.0)
        self.assertLess(by[5], 2.0)
        self.assertLess(by[1], 2.0)
        noise = agg[(agg.kind == "FAST_UP") & (agg.feature == "noise") & (agg.analysis == "void")]
        self.assertTrue((noise["lift"].between(0.4, 1.8)).all(), noise["lift"].tolist())

    def test_gates_pass_a_directional_lead_and_flag_a_movement_only_lead(self):
        proto = small_proto()
        lad, _ = ladder(proto, lead_up=3)  # planted before up moves only
        agg, _ = lifts(lad, proto)
        g = ll.gate(agg, proto)
        row = g[
            (g.kind == "FAST_UP") & (g.lead == 3) & (g.feature == "plant") & (g["tail"] == "top")
        ].iloc[0]
        self.assertTrue(row["passes"], row.to_dict())
        self.assertEqual(ll.verdict(g, proto)["verdict"], "LEAD_FOUND")
        both, _ = ladder(proto, lead_up=3, lead_down=3, seed=2)  # same feature before falls too
        g2 = ll.gate(lifts(both, proto)[0], proto)
        row2 = g2[
            (g2.kind == "FAST_UP")
            & (g2.lead == 3)
            & (g2.feature == "plant")
            & (g2["tail"] == "top")
        ].iloc[0]
        self.assertFalse(row2["passes"])
        self.assertTrue(row2["movement_only"], row2.to_dict())

    def test_noise_world_has_no_passing_cell(self):
        proto = small_proto()
        lad, _ = ladder(proto, lead_up=None)
        g = ll.gate(lifts(lad, proto)[0], proto)
        self.assertEqual(int(g["passes"].sum()), 0)
        self.assertEqual(ll.verdict(g, proto)["verdict"], "NO_DAYS_AHEAD_LEAD")

    def test_no_lookahead_features_after_the_lead_session_are_never_read(self):
        proto = small_proto()
        level, present, prev, buckets, feats, dates, _ = world(n=120, s=300, n_up=40, n_down=10)
        lad = ll.Ladder(level, present, present, prev, buckets, feats, (), dates, (0, 300), proto)
        a = lad.table("FAST_UP")
        # scramble every feature value on sessions >= each event's t: leads >= 1 must not change
        n, t = lad.events("FAST_UP")
        scr = {k: v.copy() for k, v in feats.items()}
        for k in scr:
            for i, tt in zip(n, t):
                scr[k][:, tt:] = np.random.default_rng(tt).normal(size=scr[k][:, tt:].shape)
        lad2 = ll.Ladder(level, present, present, prev, buckets, feats, (), dates, (0, 300), proto)
        lad2.features = scr
        b = lad2.table("FAST_UP")
        cols = [c for c in a.columns if c.startswith("plant|") or c.startswith("noise|")]
        late = a["lead"] >= 1
        # each event's u < t, but scrambling also hits other events' later sessions; only compare events whose u
        # precedes every scrambled start (the first event's t)
        first_t = int(t.min())
        keep = late & (a["u"] < first_t)
        self.assertGreater(int(keep.sum()), 0)
        self.assertTrue(
            np.allclose(
                a.loc[keep, cols].to_numpy(float), b.loc[keep, cols].to_numpy(float), equal_nan=True
            )
        )

    def test_void_drops_extended_events_and_pool_names(self):
        proto = small_proto()
        lad, _ = ladder(proto)
        tab = lad.table("FAST_UP")
        v = tab[tab.analysis == "void"]
        self.assertFalse(lad.ext[v["name_idx"].to_numpy(), v["u"].to_numpy()].any())
        self.assertGreaterEqual(len(tab[tab.analysis == "all"]), len(v))


class VoidRuleTests(unittest.TestCase):
    def test_extended_uses_prior_window_only(self):
        lvl = np.ones((1, 30))
        lvl[0, 25] = 1.2
        ext = void.extended(lvl)
        self.assertEqual(np.flatnonzero(ext[0]).tolist(), [25])
        lvl2 = lvl.copy()
        lvl2[0, 26:] = 5.0  # later sessions cannot change the call at 25
        self.assertTrue(void.extended(lvl2)[0, 25])
        self.assertFalse(
            void.extended(np.ones((1, 5)))[0].any()
        )  # fewer than 10 prior sessions: never extended

    def test_backtest_void_option_drops_flags_on_extended_sessions(self):
        df, meta = random_walk_panel(n_sessions=200)
        daily = module_rule(
            "EVERYDAY",
            """
            def compute(m):
                return np.where(m.tradeable, 1.0, np.nan)
        """,
            holding=1,
        )
        with with_rule(daily):
            base = run(RunConfig("EVERYDAY", random_draws=5, overlap="allow"), df, meta)["summary"]
            voided = run(
                RunConfig("EVERYDAY", random_draws=5, overlap="allow", void_extended=0.10), df, meta
            )["summary"]
        self.assertNotIn("void", base)
        self.assertGreater(voided["void"]["flags_voided"], 0)
        self.assertEqual(
            voided["signals"]["total"], base["signals"]["total"] - voided["void"]["flags_voided"]
        )


if __name__ == "__main__":
    unittest.main()
