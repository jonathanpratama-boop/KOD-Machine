"""The CRYPTO_CLOSE profile variant (E5 latency-pessimistic sensitivity: entry at the close of t+1).
Each test names the failure it guards against. Synthetic data only."""

import unittest
from dataclasses import asdict

import numpy as np

from idxsig.execution import STATUS, ExecConfig, execute
from idxsig.market import Fees
from idxsig.profiles import CRYPTO, CRYPTO_CLOSE, IDX, PROFILES, US, Profile
from tests.support import flat_market, rebuild

# The CRYPTO profile as recorded by the E2 / E4 runs, frozen here field by field. If this dict has to
# change, a recorded run no longer reproduces: that is a protocol event, not a refactor.
EXPECTED_CRYPTO = {
    "market": "CRYPTO",
    "currency": "USDT",
    "lot_size": 1,
    "price_limits": False,
    "band_edges": (0.01, 1, 100),
    "band_names": ("<0.01", "0.01-1", "1-100", ">100"),
    "fee_buy": 0.001,
    "fee_sell": 0.001,
    "cost_tiers": ((float("inf"), 0.001),),
    "notional": 5_000.0,
    "entry": "open",
    "venue": "Binance spot (reference prices; USDT pairs)",
    "assumption_note": "costs assumed: 0.1% taker fee + 0.1% slippage per side; sessions are UTC days",
    "short_carry_per_session": 0.0005,
    "short_note": "short side assumed: a perpetual-futures short at the spot reference price, funding "
    "0.05% per UTC day paid by the short (a conservative stand-in: after a pump longs "
    "usually pay), 0.1% fee + 0.1% slippage per side; perpetuals may not exist for "
    "every pair, and liquidation risk is not modelled",
}


class CryptoCloseProfile(unittest.TestCase):
    def test_crypto_profile_is_unchanged_field_by_field(self):
        """Guards against: adding the variant altering CRYPTO itself (any field), which would silently
        change every recorded E2 / E4 crypto run's inputs."""
        self.assertEqual(asdict(CRYPTO), EXPECTED_CRYPTO)
        self.assertEqual(
            set(Profile.__dataclass_fields__), set(EXPECTED_CRYPTO)
        )  # no field left unfrozen

    def test_crypto_close_is_registered_and_differs_only_in_entry(self):
        """Guards against: a variant that quietly carries a different cost, lot, band, carry or note (it
        would not be the single-change sensitivity the E5 protocol draft names), or one that is not
        reachable by its market name."""
        self.assertIs(PROFILES["CRYPTO_CLOSE"], CRYPTO_CLOSE)
        self.assertEqual(CRYPTO_CLOSE.entry, "close")
        self.assertEqual(CRYPTO.entry, "open")
        a, b = asdict(CRYPTO), asdict(CRYPTO_CLOSE)
        self.assertEqual({k for k in a if a[k] != b[k]}, {"entry"})
        self.assertEqual({**b, "entry": "open"}, EXPECTED_CRYPTO)

    def test_existing_registry_entries_are_untouched(self):
        """Guards against: the registry rewrite re-keying or replacing IDX / US / CRYPTO."""
        self.assertEqual(set(PROFILES), {"IDX", "US", "CRYPTO", "CRYPTO_CLOSE"})
        self.assertIs(PROFILES["IDX"], IDX)
        self.assertIs(PROFILES["US"], US)
        self.assertIs(PROFILES["CRYPTO"], CRYPTO)
        self.assertIsNot(PROFILES["CRYPTO"], CRYPTO_CLOSE)
        # Both share the market name CRYPTO: the harness's IDX/global branch, the sealed holdout and the
        # report's profile label all follow the market, not the registry key.
        self.assertEqual(CRYPTO_CLOSE.market, "CRYPTO")

    def test_costs_are_identical_one_tenth_percent_fee_plus_one_tenth_percent_tier_per_side(self):
        """Guards against: the sensitivity run paying different costs from the primary (0.1% fee + 0.1%
        tier per side, the recorded E2 config), which would confound entry timing with cost."""
        prices = np.array([0.001, 0.5, 1.0, 50.0, 100.0, 1e5])
        for prof in (CRYPTO, CRYPTO_CLOSE):
            self.assertEqual((prof.fee_buy, prof.fee_sell), (0.001, 0.001))
            self.assertEqual(prof.per_side_cost(prices).tolist(), [0.001] * len(prices))
            self.assertEqual(prof.cost_tiers, ((float("inf"), 0.001),))
        self.assertEqual(CRYPTO_CLOSE.short_carry_per_session, CRYPTO.short_carry_per_session)

    def test_variant_enters_at_the_close_of_t_plus_1_not_its_open(self):
        """Guards against: the variant's entry string not reaching the execution engine (still filled at
        the open), or the close entry being costed differently from the open entry."""
        t, d, a = flat_market(price=10.0, volume=1e6)
        a["open"] = np.full(a["close"].shape, 10.0)
        a["open"][0, 3] = 11.0  # the entry session gaps up at the open and closes back at 10
        m = rebuild(t, d, a)
        out = {}
        for name, prof in (("open", CRYPTO), ("close", CRYPTO_CLOSE)):
            cfg = ExecConfig(
                holding_days=3,
                lot_size=prof.lot_size,
                entry_price=prof.entry,
                notional=prof.notional,
                cost_tiers=prof.cost_tiers,
                fees=Fees(prof.fee_buy, prof.fee_sell),
            )
            out[name] = execute(m, np.array([0]), np.array([2]), cfg)
            self.assertEqual(STATUS[out[name]["status"][0]], "EXITED")
        self.assertEqual(out["open"]["entry_price"][0], 11.0)
        self.assertEqual(out["close"]["entry_price"][0], 10.0)
        self.assertEqual(out["open"]["shares"][0], 454)  # floor(5000 / 11)
        self.assertEqual(out["close"]["shares"][0], 500)  # floor(5000 / 10)
        per_side = 0.001 + 0.001
        self.assertAlmostEqual(
            out["open"]["net_return"][0], (10 * (1 - per_side)) / (11 * (1 + per_side)) - 1
        )
        self.assertAlmostEqual(out["close"]["net_return"][0], (1 - per_side) / (1 + per_side) - 1)


class CryptoCloseThroughTheHarness(unittest.TestCase):
    def test_backtest_run_uses_the_close_entry_and_the_same_sealed_holdout(self):
        """Guards against: backtest.run accepting market='CRYPTO_CLOSE' but filling at the open, reporting
        the wrong profile, or missing the global holdout seal that applies to the CRYPTO panel."""
        from idxsig.backtest import HoldoutSealed, RunConfig, run
        from tests.rulekit import module_rule, with_rule
        from tests.support import random_walk_panel

        df, meta = random_walk_panel(start="2023-10-02", n_sessions=120)
        df["open"] = df["previous"]  # an opening print distinct from the close on every session
        meta = {**meta, "default_start": "2023-10-02", "quality_tiers": [], "known_limitations": []}
        rule = module_rule(
            "EDGECC",
            """
def compute(m):
    out = np.zeros(m.shape)
    out[0, ::7] = 1.0
    return np.where(m.tradeable, out, np.nan)
""",
        )
        closes = df.set_index(["ticker", df["date"].astype(str)])["close"].astype(float)
        opens = df.set_index(["ticker", df["date"].astype(str)])["open"].astype(float)
        with with_rule(rule):
            with self.assertRaises(HoldoutSealed):
                run(
                    RunConfig("EDGECC", market="CRYPTO_CLOSE", ca_mode="adjusted", random_draws=5),
                    df,
                    meta,
                )
            common = dict(ca_mode="adjusted", random_draws=5, end="2023-12-29")
            at_close = run(RunConfig("EDGECC", market="CRYPTO_CLOSE", **common), df, meta)
            at_open = run(RunConfig("EDGECC", market="CRYPTO", **common), df, meta)
        s = at_close["summary"]
        self.assertEqual(s["config"]["market"], "CRYPTO_CLOSE")
        self.assertEqual((s["market"]["profile"], s["market"]["entry"]), ("CRYPTO", "close"))
        self.assertEqual(
            s["market"]["cost_assumption"], at_open["summary"]["market"]["cost_assumption"]
        )
        self.assertTrue(s["execution"]["price"].startswith("official close"))
        self.assertEqual(at_open["summary"]["market"]["entry"], "open")
        tc, to = at_close["trades"], at_open["trades"]
        self.assertEqual(tc["signal_date"].tolist(), to["signal_date"].tolist())
        exited = tc[tc["status"] == "EXITED"]
        self.assertGreater(len(exited), 0)
        for r in exited.itertuples():
            self.assertEqual(r.entry_price, closes[(r.ticker, r.entry_date)])
        for r in to[to["status"] == "EXITED"].itertuples():
            self.assertEqual(r.entry_price, opens[(r.ticker, r.entry_date)])


if __name__ == "__main__":
    unittest.main()
