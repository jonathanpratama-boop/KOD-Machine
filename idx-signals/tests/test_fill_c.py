"""FILL-C-v1: decision-time capacity for IDX closing-auction entries
(research/IDX_CAUSAL_CAPACITY_v1/PROTOCOL.md). Synthetic markets only.

Each test names the failure it guards against."""

import unittest

import numpy as np

from idxsig.execution import STATUS, ExecConfig, close_capacity, execute
from tests.support import flat_market, rebuild
from tests.test_corporate_actions import registry, reset_market


def one(m, sig, notional=10_000_000.0, fill_model="C"):
    out = execute(m, np.array([0]), np.array([sig]),
                  ExecConfig(holding_days=4, notional=notional, ca_mode="registry", fill_model=fill_model))
    return {k: v[0] for k, v in out.items()}


def registered(m):
    return m.with_registry(registry(m))


class Causality(unittest.TestCase):
    def test_entry_session_volume_is_not_used(self):
        """Guards against: sizing on the entry session's final volume, which includes the very auction
        the order joins. A thin past and a heavy entry day: A fills, C does not."""
        t, d, a = flat_market(volume=10_000.0)
        a["volume"][0, 5] = 10_000_000.0
        m = registered(rebuild(t, d, a))
        self.assertEqual(STATUS[one(m, 4, fill_model="A")["status"]], "EXITED")
        self.assertEqual(STATUS[one(m, 4)["status"]], "SKIP_LIQUIDITY")  # 10,000 shares > 10% of 10,000

    def test_a_dead_entry_day_does_not_block_a_liquid_name(self):
        """Guards against: skipping a name that was liquid when the decision was made because its
        entry day turned out quiet (known only after the close)."""
        t, d, a = flat_market()
        a["volume"][0, 5] = 1_000.0
        m = registered(rebuild(t, d, a))
        self.assertEqual(STATUS[one(m, 4, fill_model="A")["status"]], "SKIP_LIQUIDITY")
        self.assertEqual(STATUS[one(m, 4)["status"]], "EXITED")

    def test_sessions_after_the_signal_do_not_change_capacity(self):
        """Guards against: a window that reaches past the signal session."""
        t, d, a = flat_market()
        base = close_capacity(a["volume"], a["present"], np.ones((3, 20)), np.zeros((3, 20), int),
                              [0], [9], [10])[0][0]
        a["volume"][0, 10:] = 1.0
        later = close_capacity(a["volume"], a["present"], np.ones((3, 20)), np.zeros((3, 20), int),
                               [0], [9], [10])[0][0]
        self.assertEqual(base, later)
        self.assertEqual(base, 1_000_000.0)

    def test_listed_sessions_without_trades_count_as_zero(self):
        """Guards against: a median over traded days only, which overstates capacity for names that
        rarely trade."""
        t, d, a = flat_market()
        a["volume"][0, :12] = 0.0  # 12 of the 20 window sessions listed but untraded
        cap = close_capacity(a["volume"], a["present"], np.ones((3, 20)), np.zeros((3, 20), int), [0], [19], [19])[0]
        self.assertEqual(cap[0], 0.0)


class ShareUnits(unittest.TestCase):
    def test_split_between_signal_and_entry(self):
        """Guards against: pre-split volume compared with post-split shares. A verified 1:2 split on the
        entry session doubles the window's volume in entry-session shares."""
        m = registered(reset_market(2.0, share_ratio=2.0))  # price 500 from session 5
        r = one(m, 4, notional=500.0 * 150_000)  # 150,000 shares: above 10% of 1m, below 10% of 2m
        self.assertEqual(STATUS[r["status"]], "EXITED")
        self.assertEqual(r["shares"], 150_000)
        cap, unknown = close_capacity(m.volume, m.present, m.reg_factor, m.reg_unresolved, [0], [4], [5])
        self.assertEqual((cap[0], unknown[0]), (2_000_000.0, False))

    def test_reverse_split_between_signal_and_entry(self):
        """Guards against: a 5:1 consolidation leaving capacity five times too large."""
        m = registered(reset_market(0.2, share_ratio=0.2))  # price 5,000 from session 5
        r = one(m, 4, notional=5_000.0 * 30_000)  # 30,000 shares: above 10% of 200,000
        self.assertEqual(STATUS[r["status"]], "SKIP_LIQUIDITY")
        cap, _ = close_capacity(m.volume, m.present, m.reg_factor, m.reg_unresolved, [0], [4], [5])
        self.assertAlmostEqual(cap[0], 200_000.0)

    def test_split_inside_the_window(self):
        """Guards against: mixing units when the split falls inside the 20 sessions. Every session is
        put into post-split shares, so the median is the post-split volume."""
        m = registered(reset_market(2.0, share_ratio=2.0, at=5))
        cap, unknown = close_capacity(m.volume, m.present, m.reg_factor, m.reg_unresolved, [0], [12], [13])
        self.assertEqual((cap[0], unknown[0]), (2_000_000.0, False))

    def test_unverified_reset_makes_units_unknown(self):
        """Guards against: guessing the units across a reset the registry cannot explain."""
        m = registered(reset_market(2.0))  # a 2x reset with no share-count change: UNRESOLVED
        self.assertEqual(STATUS[one(m, 4)["status"]], "SKIP_CAPACITY_UNKNOWN")
        self.assertEqual(STATUS[one(m, 4, fill_model="A")["status"]], "EXITED")  # A never looked
        # Once the reset is at or before the window's first session, the window is in one unit.
        cap, unknown = close_capacity(m.volume, m.present, m.reg_factor, m.reg_unresolved, [0], [19], [19], window=10)
        self.assertEqual((cap[0], unknown[0]), (2_000_000.0, False))


class Scope(unittest.TestCase):
    def test_only_close_entries_in_panel_units_with_a_registry(self):
        """Guards against: C silently running where its share units are undefined."""
        m = rebuild(*flat_market())
        with self.assertRaises(ValueError):
            execute(m, np.array([0]), np.array([4]), ExecConfig(holding_days=4, ca_mode="registry", fill_model="C"))
        with self.assertRaises(ValueError):
            execute(registered(m), np.array([0]), np.array([4]),
                    ExecConfig(holding_days=4, ca_mode="registry", fill_model="C", entry_price="open"))

    def test_status_appended_so_old_codes_keep_their_meaning(self):
        """Guards against: renumbering the statuses recorded runs were written with."""
        self.assertEqual(STATUS[10:12], ("SKIP_LIQUIDITY", "SKIP_CAPACITY_UNKNOWN"))
        self.assertEqual(STATUS[12:], ("SKIP_NO_TRIGGER",))  # E3 plans: appended, never inserted
        self.assertEqual(STATUS.index("SKIP_NO_ENTRY_SESSION"), 6)


if __name__ == "__main__":
    unittest.main()
