"""Market profiles (US, crypto) and the global panels. Each test names the failure it guards against."""

import unittest

import numpy as np
import pandas as pd

from idxsig.execution import STATUS, ExecConfig, execute
from idxsig.global_panel import _spikes
from idxsig.profiles import CRYPTO, IDX, US
from idxsig.rules import moonshot_g
from idxsig.rules.audit import audit_module
from tests.support import flat_market, rebuild


class Profiles(unittest.TestCase):
    def test_report_names_the_markets_own_price_bands(self):
        """Guards against: a US or crypto run report describing its price bands in rupiah (the
        2026-10-08 E2 runs did, though they matched on the right dollar / USDT edges)."""
        from idxsig import controls

        m = rebuild(*flat_market(n_tickers=6, n_sessions=30))
        feats = controls.features(m, "v2", US.band_edges)
        cov = controls.coverage(
            feats, np.array([0]), np.array([25]), np.array([0]), "v2", US.band_names
        )
        self.assertEqual(
            cov["features"]["price_band"]["description"], "close in <$1 / $1-5 / $5-20 / >$20"
        )
        idx = controls.coverage(feats, np.array([0]), np.array([25]), np.array([0]), "v2")
        self.assertIn("Rp200", idx["features"]["price_band"]["description"])

    def test_idx_profile_reproduces_the_original_constants(self):
        """Guards against: the market refactor changing IDX lots, fees, bands or entry."""
        self.assertEqual(
            (IDX.lot_size, IDX.fee_buy, IDX.fee_sell, IDX.entry, IDX.price_limits),
            (100, 0.0015, 0.0025, "close", True),
        )
        self.assertEqual(IDX.band(np.array([200.0, 201.0, 5000.0, 5001.0])).tolist(), [0, 1, 1, 2])

    def test_us_cost_tiers_charge_cheap_names_more(self):
        """Guards against: a $0.50 stock traded as if it cost what a $50 stock costs to trade."""
        self.assertEqual(
            US.per_side_cost(np.array([0.5, 1.0, 4.99, 5.0, 25.0])).tolist(),
            [0.015, 0.005, 0.005, 0.0015, 0.0005],
        )

    def test_next_open_entry_and_single_share_lots(self):
        """Guards against: US/crypto trades entered at the next close (missing the open), or rounded to
        IDX's 100-share lots."""
        t, d, a = flat_market(price=10.0, volume=1e6)
        a["open"] = np.full(a["close"].shape, 10.0)
        a["open"][0, 3] = 11.0  # gap up on the entry session
        m = rebuild(t, d, a)
        from idxsig.market import Fees

        cfg = ExecConfig(
            holding_days=3,
            lot_size=1,
            entry_price="open",
            notional=5000.0,
            cost_tiers=US.cost_tiers,
            fees=Fees(US.fee_buy, US.fee_sell),
        )
        out = execute(m, np.array([0]), np.array([2]), cfg)
        self.assertEqual(STATUS[out["status"][0]], "EXITED")
        self.assertEqual(out["entry_price"][0], 11.0)
        self.assertEqual(out["shares"][0], 454)  # floor(5000 / 11)
        expected = (10 * (1 - US.fee_sell - 0.0015)) / (11 * (1 + US.fee_buy + 0.0015)) - 1
        self.assertAlmostEqual(out["net_return"][0], expected)

    def test_markets_without_price_limits_have_no_locks(self):
        """Guards against: IDX auto-rejection limits applied to US or crypto bars (a +40% day 'locked')."""
        t, d, a = flat_market(price=10.0)
        a["close"][0, 4] = 14.0
        a["high"][0, 4] = 14.0
        a["prev"][0, 5:] = 14.0
        from idxsig.execution import Market

        m = Market.build(
            t,
            d,
            a["close"],
            a["prev"],
            a["high"],
            a["low"],
            a["volume"],
            a["value"],
            a["present"],
            price_limits=False,
        )
        self.assertFalse(m.lock_up.any() or m.lock_down.any())
        self.assertFalse(CRYPTO.price_limits or US.price_limits)


class GlobalPanel(unittest.TestCase):
    def test_one_day_spike_that_reverts_is_dropped_but_a_real_jump_is_kept(self):
        """Guards against: a bad print (x5 for one day) becoming a fake moonshot, while a jump that holds
        stays in the data."""
        df = pd.DataFrame(
            {
                "ticker": ["A"] * 5 + ["B"] * 5,
                "date": list(range(5)) * 2,
                "close": [10, 10, 50, 10, 10] + [10, 10, 50, 50, 50],
            }
        )
        self.assertEqual(_spikes(df).tolist(), [False, False, True, False, False] + [False] * 5)

    def test_tickers_that_look_like_missing_values_survive_a_round_trip(self):
        """Guards against: the Nasdaq symbol NA (and NAN, NULL) being read back as a missing ticker."""
        import tempfile
        from pathlib import Path

        df = pd.DataFrame(
            {
                "date": ["2024-01-02"] * 3,
                "ticker": ["NA", "NULL", "AAPL"],
                "source": "yahoo",
                "close": [1.0, 2.0, None],
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.csv.gz"
            df.to_csv(path, index=False, compression={"method": "gzip", "mtime": 0})
            back = pd.read_csv(
                path,
                parse_dates=["date"],
                dtype={"ticker": str, "source": str},
                keep_default_na=False,
                na_values=[""],
            )
        self.assertEqual(back["ticker"].tolist(), ["NA", "NULL", "AAPL"])
        self.assertTrue(np.isnan(back["close"].iloc[2]))

    def test_family_g_is_audit_clean_and_fixed(self):
        """Guards against: an E2 detector module that could read the future, or a family edited after analysis."""
        self.assertEqual(audit_module(moonshot_g), [])
        self.assertEqual(len(moonshot_g.FAMILY), 11)


if __name__ == "__main__":
    unittest.main()
