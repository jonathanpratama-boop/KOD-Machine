"""Synthetic tests for idxsig/e8.py (research/E8, peer spillover). No real data."""

import unittest

import numpy as np
import pandas as pd

from idxsig import e6, e8

START = pd.Timestamp("2020-04-01", tz="UTC")


def synth(n=30, days=120, seed=3, jump_day=100, jump_coin=0, group=(0, 1, 2, 3), moved_peer=None):
    """n coins; coins in `group` share a factor. Coin `jump_coin` rises ~35% over the 24 hours ending at
    the last hour of `jump_day`, with 5x volume. `moved_peer` (if given) rises with it."""
    rng = np.random.default_rng(seed)
    T = days * 24
    mkt = rng.normal(0, 0.004, T)
    grp = rng.normal(0, 0.006, T)
    r = mkt[None, :] + rng.normal(0, 0.006, (n, T))
    r[list(group)] += grp[None, :]
    quote = np.exp(rng.normal(np.log(1.2e5), 0.3, (n, T)))
    t1 = 24 * jump_day + 23
    for c in [jump_coin] + ([moved_peer] if moved_peer is not None else []):
        r[c, t1 - 23 : t1 + 1] += np.log(1.35) / 24
        quote[c, t1 - 23 : t1 + 1] *= 5
    close = 10 * np.exp(np.cumsum(r, axis=1))
    opn = np.concatenate([close[:, :1], close[:, :-1]], axis=1)
    high = np.maximum(close, opn) * 1.002
    low = np.minimum(close, opn) * 0.998
    tb = quote * 0.5
    present = np.ones((n, T), dtype=bool)
    h = e6.Hourly(
        [f"C{i:02d}USDT" for i in range(n)], START, present, opn, high, low, close, quote, tb
    )
    return h, t1


def perturb_after(h, hour):
    later = np.arange(h.present.shape[1])[None, :] > hour
    g = lambda a, m=1.7: np.where(later, a * m + 0.3, a)
    present = h.present.copy()
    present[5, hour + 1 :] = False
    return e6.Hourly(
        h.symbols,
        h.start,
        present,
        g(h.open),
        g(h.high, 1.9),
        g(h.low, 1.5),
        g(h.close),
        g(h.quote, 3.0),
        g(h.tb, 2.0),
    )


def period(h):
    return (str(h.start + pd.Timedelta(days=95)), str(h.start + pd.Timedelta(days=115)))


class Signal(unittest.TestCase):
    def test_leader_fires_once_at_the_first_crossing(self):
        h, t1 = synth()
        f = e8.features(h)
        lead, raw = e8.leaders(f)
        hits = np.flatnonzero(lead[0])
        self.assertEqual(len(hits), 1)
        self.assertTrue(t1 - 23 < hits[0] <= t1)
        self.assertTrue(raw[0, hits[0] : t1 + 1].any())
        self.assertFalse(lead[1:, :].any())

    def test_peers_are_the_linked_coins_that_have_not_moved(self):
        h, t1 = synth(moved_peer=3)
        f = e8.features(h)
        L, P = e8.peer_events(h, f, period=period(h))
        self.assertEqual(
            set(L["leader"].tolist()), {0, 3}
        )  # the coin that moved with it is a leader too
        got = set(P["peer"].tolist())
        self.assertEqual(got, {1, 2})  # neither leader is anyone's peer
        self.assertEqual(len(P), 2)  # one event per coin even when two leaders name it
        self.assertTrue((P["link"] >= e8.LINK_MIN).all())
        self.assertTrue((P["res24"] <= e8.PEER_RES_MAX).all())

    def test_signal_ignores_every_later_bar(self):
        h, t1 = synth()
        cut = t1 + 2
        f1, f2 = e8.features(h), e8.features(perturb_after(h, cut))
        for k in ("elig", "r24", "res24", "res", "vol24", "liq", "vol30h"):
            np.testing.assert_array_equal(
                np.nan_to_num(np.asarray(f1[k], float)[:, : cut + 1], nan=-9),
                np.nan_to_num(np.asarray(f2[k], float)[:, : cut + 1], nan=-9),
                k,
            )
        p = (period(h)[0], str(h.start + pd.Timedelta(hours=cut)))
        _, P1 = e8.peer_events(h, f1, period=p, hold=0)
        _, P2 = e8.peer_events(perturb_after(h, cut), f2, period=p, hold=0)
        pd.testing.assert_frame_equal(P1.reset_index(drop=True), P2.reset_index(drop=True))
        self.assertGreater(len(P1), 0)

    def test_link_window_stops_where_the_leader_move_starts(self):
        h, t1 = synth()
        f = e8.features(h)
        ret2 = f["ret"].copy()
        ret2[:, t1 - 22 : t1 + 1] = np.random.default_rng(9).normal(
            0, 1, ret2[:, t1 - 22 : t1 + 1].shape
        )
        cand = np.ones(len(h.symbols), dtype=bool)
        cand[0] = False
        a, _ = e8.links(f["ret"], f["mkt"], 0, t1, cand)
        b, _ = e8.links(ret2, f["mkt"], 0, t1, cand)
        np.testing.assert_array_equal(a, b)
        self.assertTrue(np.isnan(a[0]))
        self.assertTrue((a[[1, 2, 3]] > 0.3).all())  # same group
        self.assertTrue((np.abs(a[4:]) < 0.15).all())  # unrelated coins

    def test_low_beta_coins_are_not_linked_by_the_market(self):
        """Amendment 1: two low-beta coins with independent news must not look linked."""
        rng = np.random.default_rng(11)
        n, T = 30, 24 * 120
        mkt = rng.normal(0, 0.01, T)
        beta = np.ones(n)
        beta[[0, 1]] = 0.1
        r = beta[:, None] * mkt[None, :] + rng.normal(0, 0.004, (n, T))
        med = np.median(r, axis=0)
        res = r - med[None, :]  # the original median residual
        cand = np.ones(n, dtype=bool)
        cand[0] = False
        t = 24 * 100
        lk, _ = e8.links(r, med, 0, t, cand)
        lo, hi = t - 743, t - 23
        naive = np.corrcoef(res[0, lo:hi], res[1, lo:hi])[0, 1]
        self.assertGreater(naive, 0.5)  # the defect amendment 1 removes
        self.assertLess(abs(lk[1]), 0.15)

    def test_asset_backed_tokens_are_never_loaded(self):
        self.assertIn("PAXG", e8.ASSET_BACKED)
        self.assertIn("BKRW", e8.ASSET_BACKED)

    def test_eligibility_needs_history_liquidity_and_no_long_gap(self):
        h, _ = synth()
        present = h.present.copy()
        present[7, 24 * 50 : 24 * 60] = False  # a 10-day gap
        h2 = e6.Hourly(
            h.symbols,
            h.start,
            present,
            *(
                np.where(present, a, np.nan)
                for a in (h.open, h.high, h.low, h.close, h.quote, h.tb)
            ),
        )
        f = e8.features(h2)
        self.assertFalse(f["elig"][:, : 24 * 60].any())  # under 60 complete days for everyone
        self.assertFalse(
            f["elig"][7, 24 * 61 : 24 * 110].any()
        )  # gap within the last 60 days ... and history
        self.assertTrue(f["elig"][8, 24 * 70])

    def test_discovery_refuses_2023(self):
        with self.assertRaises(e6.HoldoutError):
            e8.load("unused.jsonl", last_hour=pd.Timestamp("2023-01-01 00:00", tz="UTC"))


if __name__ == "__main__":
    unittest.main()


def one_coin(T=100, t=10, edits=None, absent=()):
    """Flat price 1.0 with tiny ranges; edits: {bar: (open, high, low, close)}."""
    o = np.ones((1, T))
    hi = np.full((1, T), 1.001)
    lo = np.full((1, T), 0.999)
    cl = np.ones((1, T))
    for b, (a, bh, bl, c) in (edits or {}).items():
        o[0, b], hi[0, b], lo[0, b], cl[0, b] = a, bh, bl, c
    pres = np.ones((1, T), dtype=bool)
    pres[0, list(absent)] = False
    nan = lambda a: np.where(pres, a, np.nan)
    return e6.Hourly(
        ["X"],
        START,
        pres,
        nan(o),
        nan(hi),
        nan(lo),
        nan(cl),
        nan(np.full((1, T), 1e5)),
        nan(np.full((1, T), 5e4)),
    )


def net(px, liq=1e6):
    s = e8.slippage(np.array([liq]))[0]
    return px * (1 - e8.FEE - s) / (1 + e8.FEE + s) - 1


class Plan(unittest.TestCase):
    def run_(self, **kw):
        return e8.window(one_coin(**kw), np.array([0]), 10, np.array([1e6]))

    def test_take_profit(self):
        w = self.run_(edits={13: (1.0, 1.25, 0.99, 1.2)})
        self.assertEqual(w["reason"][0], "TAKE_PROFIT")
        self.assertAlmostEqual(w["net"][0], net(1.2))
        self.assertEqual(w["bars"][0], 3)
        self.assertTrue(w["U20"][0])
        self.assertFalse(w["U30"][0])

    def test_stop_first_when_both_levels_are_touched(self):
        w = self.run_(edits={14: (1.0, 1.3, 0.85, 1.0)})
        self.assertEqual(w["reason"][0], "STOP")
        self.assertAlmostEqual(w["net"][0], net(0.9))
        self.assertTrue(w["U30"][0])  # the label still sees the high

    def test_gap_through_the_stop_fills_at_the_open(self):
        w = self.run_(edits={15: (0.8, 0.82, 0.78, 0.8)})
        self.assertEqual(w["reason"][0], "STOP_GAP")
        self.assertAlmostEqual(w["net"][0], net(0.8))

    def test_timeout_and_costs(self):
        w = self.run_(edits={82: (1.0, 1.05, 0.99, 1.05)})
        self.assertEqual(w["reason"][0], "TIMEOUT")
        self.assertAlmostEqual(w["R72"][0], 0.05)
        self.assertAlmostEqual(w["net"][0], net(1.05))
        liquid = e8.window(
            one_coin(edits={82: (1.0, 1.05, 0.99, 1.05)}), np.array([0]), 10, np.array([2e7])
        )
        self.assertAlmostEqual(liquid["net"][0], net(1.05, 2e7))
        self.assertGreater(liquid["net"][0], w["net"][0])

    def test_missing_end_exits_at_the_last_close(self):
        w = self.run_(edits={79: (1.0, 1.1, 0.99, 1.1)}, absent=(80, 81, 82))
        self.assertEqual(w["reason"][0], "TIMEOUT")
        self.assertTrue(w["missing_end"][0])
        self.assertAlmostEqual(w["R72"][0], 0.1)

    def test_no_entry_bar(self):
        w = self.run_(absent=(11,))
        self.assertFalse(w["has_entry"][0])
        self.assertEqual(w["reason"][0], "NO_ENTRY")
        self.assertTrue(np.isnan(w["net"][0]))

    def test_outcome_reads_only_the_window(self):
        a = self.run_(edits={30: (1.0, 1.1, 0.95, 1.05)})
        b = self.run_(
            edits={
                30: (1.0, 1.1, 0.95, 1.05),
                10: (5, 9, 0.1, 0.2),
                83: (0.1, 9, 0.01, 7),
                5: (3, 4, 2, 3),
            }
        )
        for k in ("R72", "net", "U20", "U30", "bars"):
            np.testing.assert_array_equal(a[k], b[k])


class Controls(unittest.TestCase):
    def test_linked_coins_never_serve_as_controls(self):
        h, t1 = synth(n=40, days=110, jump_day=100)
        f = e8.features(h)
        _, P = e8.peer_events(h, f, period=period(h))
        self.assertGreater(len(P), 0)
        d1 = e8.score(h, f, P)

        def bump(rows):
            later = np.zeros_like(h.present)
            later[list(rows), t1 + 1 :] = True
            g = lambda a: np.where(later, a * 3, a)
            return e6.Hourly(
                h.symbols,
                h.start,
                h.present,
                g(h.open),
                g(h.high),
                g(h.low),
                g(h.close),
                h.quote,
                h.tb,
            )

        same = e8.score(bump([3]), f, P)  # coin 3 is in the leader's group: excluded from controls
        np.testing.assert_allclose(d1["ctrl_R72"], same["ctrl_R72"])
        other = e8.score(bump(range(4, 40)), f, P)  # unlinked coins are the controls
        self.assertFalse(np.allclose(d1["ctrl_R72"], other["ctrl_R72"]))
        self.assertTrue((d1["status"] == "SCORED").all())

    def test_report_and_gates_run_end_to_end(self):
        h, _ = synth(n=40, days=110, jump_day=100)
        f = e8.features(h)
        _, P = e8.peer_events(h, f, period=period(h))
        rep = e8.report(e8.score(h, f, P))
        g = e8.gates(rep)
        self.assertEqual(g["decision"], "INCONCLUSIVE")  # far fewer than 300 events
        self.assertFalse(g["gates"]["G0_sample"])
        self.assertIn("exposure", rep["trading_plan"])


class Gates(unittest.TestCase):
    def rep(self, **over):
        b = lambda est, p: {"estimate": est, "p_one_sided": p}
        r = {
            "events": 400,
            "scored": 400,
            "no_entry": 0,
            "no_controls": 0,
            "distinct_weeks": 80,
            "information": {"vs_controls": b(0.02, 0.001)},
            "moonshot": {"U20_difference": b(0.05, 0.001)},
            "trading_plan": {
                "mean_net_vs_zero": b(0.01, 0.01),
                "mean_net_minus_ctrl": 0.01,
                "win_rate_wilson95": [0.52, 0.6],
            },
            "by_year": {"2021": {"mean_excess": 0.01}, "2022": {"mean_excess": 0.02}},
            "without_two_busiest_weeks": {"mean_excess": 0.01},
        }
        r.update(over)
        return r

    def test_pass_and_high_win_rate(self):
        g = e8.gates(self.rep())
        self.assertEqual(g["decision"], "PASS")
        self.assertTrue(g["high_win_rate"])

    def test_any_failed_gate_fails(self):
        self.assertEqual(
            e8.gates(
                self.rep(by_year={"2021": {"mean_excess": 0.01}, "2022": {"mean_excess": -0.01}})
            )["decision"],
            "FAIL",
        )
        self.assertEqual(
            e8.gates(
                self.rep(information={"vs_controls": {"estimate": 0.02, "p_one_sided": 0.03}})
            )["decision"],
            "FAIL",
        )
        tp = {
            "mean_net_vs_zero": {"estimate": 0.01, "p_one_sided": 0.01},
            "mean_net_minus_ctrl": -0.001,
            "win_rate_wilson95": [0.6, 0.7],
        }
        self.assertEqual(e8.gates(self.rep(trading_plan=tp))["decision"], "FAIL")

    def test_small_sample_is_inconclusive(self):
        self.assertEqual(e8.gates(self.rep(scored=299))["decision"], "INCONCLUSIVE")
        self.assertEqual(e8.gates(self.rep(no_entry=30))["decision"], "INCONCLUSIVE")
