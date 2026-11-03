import unittest

import numpy as np

from idxsig.execution import STATUS, ExecConfig, execute
from tests.support import flat_market, rebuild

FLAT_NET = (1 - 0.0025) / (1 + 0.0015) - 1


def one(m, ticker=0, signal=2, **cfg):
    out = execute(
        m,
        np.array([ticker]),
        np.array([signal]),
        ExecConfig(holding_days=cfg.pop("holding", 3), **cfg),
    )
    return {k: v[0] for k, v in out.items()}


class ExecutionTests(unittest.TestCase):
    def test_flat_trade_pays_both_fees_and_uses_whole_lots(self):
        t, d, a = flat_market(price=3000.0)
        r = one(rebuild(t, d, a))
        self.assertEqual(STATUS[r["status"]], "EXITED")
        self.assertEqual(r["shares"], 3300)  # floor(10,000,000 / 300,000) = 33 lots
        self.assertAlmostEqual(r["net_return"], FLAT_NET)
        self.assertEqual(r["entry_idx"], 3)
        self.assertEqual(r["exit_idx"], 6)

    def test_lot_too_expensive_is_skipped(self):
        t, d, a = flat_market(price=150_000.0)
        self.assertEqual(STATUS[one(rebuild(t, d, a))["status"]], "SKIP_LOT")

    def test_participation_cap(self):
        t, d, a = flat_market(price=1000.0, volume=50_000.0)  # 10,000 shares wanted > 10% of 50,000
        self.assertEqual(STATUS[one(rebuild(t, d, a))["status"]], "SKIP_LIQUIDITY")

    def test_entry_locked_at_ara_is_refused(self):
        t, d, a = flat_market(price=1000.0)
        a["close"][0, 3] = 1250.0  # 1000 * 1.25 = regular ARA in 2024
        a["high"][0, 3] = 1250.0
        a["prev"][0, 4:] = 1250.0
        self.assertEqual(STATUS[one(rebuild(t, d, a))["status"]], "SKIP_ARA_LOCK")

    def test_one_price_bar_at_special_board_limit_is_a_lock(self):
        t, d, a = flat_market(price=1000.0)
        for k in ("close", "high", "low"):
            a[k][0, 3] = 1100.0
        self.assertEqual(STATUS[one(rebuild(t, d, a))["status"]], "SKIP_ARA_LOCK")

    def test_exit_locked_at_arb_rolls_forward(self):
        t, d, a = flat_market(price=1000.0)
        a["close"][0, 6] = 750.0  # regular ARB in 2024 (symmetric 25%)
        a["low"][0, 6] = 750.0
        a["prev"][0, 7] = 750.0
        a["close"][0, 7:] = 800.0
        a["prev"][0, 8:] = 800.0
        r = one(rebuild(t, d, a))
        self.assertEqual(r["exit_idx"], 7)
        self.assertEqual(r["rolled_sessions"], 1)
        self.assertAlmostEqual(r["net_return"], 0.8 * (1 - 0.0025) / (1 + 0.0015) - 1)

    def test_suspended_entry_is_skipped_and_suspended_exit_rolls(self):
        t, d, a = flat_market()
        a["volume"][0, 3] = 0
        self.assertEqual(STATUS[one(rebuild(t, d, a))["status"]], "SKIP_NOT_TRADED")
        t, d, a = flat_market()
        a["volume"][0, 6:9] = 0
        r = one(rebuild(t, d, a))
        self.assertEqual(r["exit_idx"], 9)

    def test_delisted_before_exit_exits_at_last_close_or_zero(self):
        t, d, a = flat_market()
        a["present"][0, 5:] = False
        a["volume"][0, 5:] = np.nan
        r = one(rebuild(t, d, a))
        self.assertEqual(STATUS[r["status"]], "EXIT_DATA_END")
        self.assertEqual(r["exit_idx"], 4)
        self.assertAlmostEqual(r["net_return"], FLAT_NET)
        r0 = one(rebuild(t, d, a), data_end_exit="zero")
        self.assertAlmostEqual(r0["net_return"], -1.0)

    def test_holding_past_the_data_is_incomplete(self):
        t, d, a = flat_market(n_sessions=6)
        self.assertEqual(STATUS[one(rebuild(t, d, a))["status"]], "INCOMPLETE")

    def test_split_scales_shares(self):
        t, d, a = flat_market(price=5000.0)
        a["prev"][0, 5] = 1000.0  # 1:5 split effective session 5
        a["close"][0, 5:] = 1000.0
        a["prev"][0, 6:] = 1000.0
        a["high"][0, 5:] = 1010.0
        a["low"][0, 5:] = 990.0
        r = one(rebuild(t, d, a))
        self.assertEqual(r["share_factor"], 5.0)
        self.assertAlmostEqual(r["net_return"], FLAT_NET)


if __name__ == "__main__":
    unittest.main()
