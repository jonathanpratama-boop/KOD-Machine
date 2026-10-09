"""US_BREAKOUT_v1 signal and runner mechanics (idxsig/breakout.py). Synthetic markets only.

Each test names the failure it guards against."""

import unittest

import numpy as np

from idxsig import breakout as B
from tests.test_contract import market


def bars(n_sessions=100, edit=None):
    def e(a):
        a["close"][0] = 100.0 + np.arange(n_sessions) * 0.0   # flat history at $100
        a["prev"][0] = a["close"][0]
        a["open"][0] = a["close"][0]
        a["high"][0], a["low"][0] = a["close"][0] * 1.01, a["close"][0] * 0.99
        if edit:
            edit(a)
    return market(n_tickers=3, n_sessions=n_sessions, edit=e)


class Signal(unittest.TestCase):
    def test_strictly_above_the_prior_60_closes_only(self):
        """Guards against: a tie with the 60-session high, or the signal session's own close counting
        in its own level."""
        def edit(a):
            a["close"][0, 70] = 100.0     # equals the high: no signal
            a["close"][0, 71] = 100.01    # above: signal
        m = bars(edit=edit)
        level, raw, _ = B.levels_and_signals(m)
        self.assertFalse(raw[0, 70])
        self.assertTrue(raw[0, 71])
        self.assertEqual(level[0, 71], 100.0)

    def test_needs_sixty_listed_and_traded_prior_sessions(self):
        """Guards against: a signal on a young listing or after a stretch without trades."""
        def edit(a):
            a["close"][0, 65] = 101.0
            a["volume"][0, 20] = 0.0      # one untraded session inside the lookback of session 65
        _, raw, _ = B.levels_and_signals(bars(edit=edit))
        self.assertFalse(raw[0, 65])
        _, raw2, _ = B.levels_and_signals(bars(edit=lambda a: a["close"][0].__setitem__(40, 101.0)))
        self.assertFalse(raw2[0, 40])     # only 40 prior sessions

    def test_signals_never_read_later_sessions(self):
        """Guards against: lookahead. The signal at session s is the same on the market cut at s."""
        def edit(a):
            a["close"][0, 70] = 105.0
            a["close"][1, 80] = 120.0
            a["close"][0, 90] = 130.0
        m = bars(edit=edit)
        _, raw, _ = B.levels_and_signals(m)
        for s in (69, 70, 80, 85, 90):
            _, cut, _ = B.levels_and_signals(m.truncate(s))
            self.assertTrue(np.array_equal(cut[:, s], raw[:, s]))

    def test_cooldown_skips_repeat_signals_within_five_sessions(self):
        """Guards against: counting a run of consecutive new highs as independent trades."""
        raw = np.zeros((1, 30), dtype=bool)
        raw[0, [10, 11, 15, 16, 22]] = True
        self.assertEqual(list(np.flatnonzero(B.cooldown_mask(raw)[0])), [11, 15, 16])


class Cells(unittest.TestCase):
    def test_eligibility_floors_and_cells(self):
        """Guards against: ineligible names in the sample or the control pool."""
        c = B.cells(np.array([4.99, 5.0, 12.0, 50.0, 150.0, 50.0]), np.array([9e6, 9e5, 3e6, 3e7, 3e8, 1e6]))
        self.assertEqual(list(c), [-1, -1, 1 * 5 + 1, 2 * 5 + 3, 3 * 5 + 4, 2 * 5 + 0])


class Runner(unittest.TestCase):
    def test_one_trade_matches_the_contract_on_the_full_market(self):
        """Guards against: the one-name slice behaving differently from the full-market contract."""
        from idxsig import contract

        def edit(a):
            a["close"][0, 70] = 104.0
            a["high"][0, 70] = 104.5
            a["open"][0, 71] = 104.0
        m = bars(edit=edit)
        level, raw, _ = B.levels_and_signals(m)
        self.assertTrue(raw[0, 70])
        inv = float(level[0, 70])
        one = B.run_trade(m, 0, 70, inv)
        acc = contract.replay(m, {70: [(0, inv)]}, 70, 80)
        full = [c for c in acc.state["closed"] if c["ticker"] == "T000"][-1]
        for k in ("outcome", "entry_price", "exit_session", "exit_reason", "net_pnl_usd", "shares_filled"):
            self.assertEqual(one.get(k), full.get(k), k)

    def test_data_that_ends_first_is_open_not_a_result(self):
        """Guards against: scoring a trade whose exit is not in the data."""
        m = bars(n_sessions=72, edit=lambda a: a["close"][0].__setitem__(70, 104.0))
        r = B.run_trade(m, 0, 70, 98.0)       # fills at the $100 open; stop $98 never touched; hold unfinished
        self.assertEqual(r["outcome"], "OPEN")
        self.assertNotIn("net_pnl_usd", r)


if __name__ == "__main__":
    unittest.main()
