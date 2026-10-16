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
        r[c, t1 - 23:t1 + 1] += np.log(1.35) / 24
        quote[c, t1 - 23:t1 + 1] *= 5
    close = 10 * np.exp(np.cumsum(r, axis=1))
    opn = np.concatenate([close[:, :1], close[:, :-1]], axis=1)
    high = np.maximum(close, opn) * 1.002
    low = np.minimum(close, opn) * 0.998
    tb = quote * 0.5
    present = np.ones((n, T), dtype=bool)
    h = e6.Hourly([f"C{i:02d}USDT" for i in range(n)], START, present, opn, high, low, close, quote, tb)
    return h, t1


def perturb_after(h, hour):
    later = np.arange(h.present.shape[1])[None, :] > hour
    g = lambda a, m=1.7: np.where(later, a * m + 0.3, a)
    present = h.present.copy()
    present[5, hour + 1:] = False
    return e6.Hourly(h.symbols, h.start, present, g(h.open), g(h.high, 1.9), g(h.low, 1.5), g(h.close),
                     g(h.quote, 3.0), g(h.tb, 2.0))


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
        self.assertTrue(raw[0, hits[0]:t1 + 1].any())
        self.assertFalse(lead[1:, :].any())

    def test_peers_are_the_linked_coins_that_have_not_moved(self):
        h, t1 = synth(moved_peer=3)
        f = e8.features(h)
        L, P = e8.peer_events(h, f, period=period(h))
        self.assertEqual(set(L["leader"].tolist()), {0, 3})  # the coin that moved with it is a leader too
        got = set(P["peer"].tolist())
        self.assertEqual(got, {1, 2})                    # neither leader is anyone's peer
        self.assertEqual(len(P), 2)                      # one event per coin even when two leaders name it
        self.assertTrue((P["link"] >= e8.LINK_MIN).all())
        self.assertTrue((P["res24"] <= e8.PEER_RES_MAX).all())

    def test_signal_ignores_every_later_bar(self):
        h, t1 = synth()
        cut = t1 + 2
        f1, f2 = e8.features(h), e8.features(perturb_after(h, cut))
        for k in ("elig", "r24", "res24", "res", "vol24", "liq", "vol30h"):
            np.testing.assert_array_equal(np.nan_to_num(np.asarray(f1[k], float)[:, :cut + 1], nan=-9),
                                          np.nan_to_num(np.asarray(f2[k], float)[:, :cut + 1], nan=-9), k)
        p = (period(h)[0], str(h.start + pd.Timedelta(hours=cut)))
        _, P1 = e8.peer_events(h, f1, period=p, hold=0)
        _, P2 = e8.peer_events(perturb_after(h, cut), f2, period=p, hold=0)
        pd.testing.assert_frame_equal(P1.reset_index(drop=True), P2.reset_index(drop=True))
        self.assertGreater(len(P1), 0)

    def test_link_window_stops_where_the_leader_move_starts(self):
        h, t1 = synth()
        f = e8.features(h)
        ret2 = f["ret"].copy()
        ret2[:, t1 - 22:t1 + 1] = np.random.default_rng(9).normal(0, 1, ret2[:, t1 - 22:t1 + 1].shape)
        cand = np.ones(len(h.symbols), dtype=bool)
        cand[0] = False
        a, _ = e8.links(f["ret"], f["mkt"], 0, t1, cand)
        b, _ = e8.links(ret2, f["mkt"], 0, t1, cand)
        np.testing.assert_array_equal(a, b)
        self.assertTrue(np.isnan(a[0]))
        self.assertTrue((a[[1, 2, 3]] > 0.3).all())          # same group
        self.assertTrue((np.abs(a[4:]) < 0.15).all())         # unrelated coins

    def test_low_beta_coins_are_not_linked_by_the_market(self):
        """Amendment 1: two low-beta coins with independent news must not look linked."""
        rng = np.random.default_rng(11)
        n, T = 30, 24 * 120
        mkt = rng.normal(0, 0.01, T)
        beta = np.ones(n)
        beta[[0, 1]] = 0.1
        r = beta[:, None] * mkt[None, :] + rng.normal(0, 0.004, (n, T))
        med = np.median(r, axis=0)
        res = r - med[None, :]                                # the original median residual
        cand = np.ones(n, dtype=bool)
        cand[0] = False
        t = 24 * 100
        lk, _ = e8.links(r, med, 0, t, cand)
        lo, hi = t - 743, t - 23
        naive = np.corrcoef(res[0, lo:hi], res[1, lo:hi])[0, 1]
        self.assertGreater(naive, 0.5)                        # the defect amendment 1 removes
        self.assertLess(abs(lk[1]), 0.15)

    def test_asset_backed_tokens_are_never_loaded(self):
        self.assertIn("PAXG", e8.ASSET_BACKED)
        self.assertIn("BKRW", e8.ASSET_BACKED)

    def test_eligibility_needs_history_liquidity_and_no_long_gap(self):
        h, _ = synth()
        present = h.present.copy()
        present[7, 24 * 50:24 * 60] = False              # a 10-day gap
        h2 = e6.Hourly(h.symbols, h.start, present, *(np.where(present, a, np.nan) for a in
                                                       (h.open, h.high, h.low, h.close, h.quote, h.tb)))
        f = e8.features(h2)
        self.assertFalse(f["elig"][:, : 24 * 60].any())   # under 60 complete days for everyone
        self.assertFalse(f["elig"][7, 24 * 61:24 * 110].any())  # gap within the last 60 days ... and history
        self.assertTrue(f["elig"][8, 24 * 70])

    def test_discovery_refuses_2023(self):
        with self.assertRaises(e6.HoldoutError):
            e8.load("unused.jsonl", last_hour=pd.Timestamp("2023-01-01 00:00", tz="UTC"))


if __name__ == "__main__":
    unittest.main()
