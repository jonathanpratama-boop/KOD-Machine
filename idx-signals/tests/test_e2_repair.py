"""E2-US repair: as-traded units, fill models, quarantine and split evidence. Synthetic 2020
data only; no market files, no network. Each test names the failure it guards against."""

import unittest
import warnings
from datetime import date

import numpy as np
import pandas as pd

from idxsig import controls, us_actions
from idxsig.execution import STATUS, ExecConfig, Market, execute
from idxsig.profiles import US
from idxsig.rules import CausalSource

SEC_FEE = US.fee_sell


def bars(n_sessions=10, open_=3.0, close=3.0, volume=1_000_000.0, tickers=("SYN",)):
    dates = pd.date_range("2020-01-01", periods=n_sessions, freq="B")
    rows = [dict(date=d, ticker=t, source="synthetic", previous=close, open=open_, high=close, low=close, close=close,
                 volume=volume, value=volume * close) for t in tickers for d in dates]
    return pd.DataFrame(rows)


def cfg(**kw):
    base = dict(holding_days=2, notional=5000.0, entry_price="open", lot_size=1, cost_tiers=US.cost_tiers,
                ca_mode="adjusted", fees=__import__("idxsig.market", fromlist=["Fees"]).Fees(US.fee_buy, US.fee_sell))
    base.update(kw)
    return ExecConfig(**base)


def one(m, c):
    out = execute(m, np.array([0]), np.array([0]), c)
    return {k: (v[0] if hasattr(v, "__len__") else v) for k, v in out.items()}


class AsTradedUnits(unittest.TestCase):
    def test_panel_units_keep_the_original_contract(self):
        """Guards against: the repair changing what an original-contract run computes."""
        m = Market.from_panel(bars(), price_limits=False)
        out = one(m, cfg())
        self.assertEqual(STATUS[out["status"]], "EXITED")
        self.assertEqual(out["shares"], 1666)  # floor(5000 / 3.00)
        tier = 0.005  # $1-5
        self.assertAlmostEqual(out["net_return"], (1 - SEC_FEE - tier) / (1 + tier) - 1)

    def test_later_reverse_split_restores_the_traded_tier_and_share_count(self):
        """Guards against: a $0.30 stock that later reverse-split 1:10 being costed as a $3 stock."""
        m = Market.from_panel(bars(), price_limits=False)
        m = m.with_units(np.full(m.shape, 0.1))
        out = one(m, cfg(units="as_traded"))
        self.assertAlmostEqual(out["entry_price_as_traded"], 0.3)
        self.assertEqual(out["shares_as_traded"], 16666)  # floor(5000 / 0.30)
        tier = 0.015  # under $1
        self.assertAlmostEqual(out["net_return"], (1 - SEC_FEE - tier) / (1 + tier) - 1)

    def test_skip_lot_from_rescaled_prices_disappears(self):
        """Guards against: a share that cost $0.60 counted as unaffordable because later reverse
        splits show it at $6,000 (all 154 SKIP_LOT attempts of the original US run)."""
        df = bars(open_=6000.0, close=6000.0)
        m = Market.from_panel(df, price_limits=False)
        self.assertEqual(STATUS[one(m, cfg())["status"]], "SKIP_LOT")
        m = m.with_units(np.full(m.shape, 1e-4))
        out = one(m, cfg(units="as_traded"))
        self.assertEqual(STATUS[out["status"]], "EXITED")
        self.assertEqual(out["shares_as_traded"], 8333)

    def test_exit_is_costed_in_its_own_session_units(self):
        """Guards against: one tier for both sides when a split falls inside the holding window."""
        m = Market.from_panel(bars(open_=15.0, close=15.0), price_limits=False)
        f = np.ones(m.shape)
        f[:, :2] = 2.0  # 2:1 split effective at session 2: sessions 0-1 traded at 30
        out = one(m.with_units(f), cfg(units="as_traded"))
        self.assertAlmostEqual(out["entry_price_as_traded"], 30.0)  # entry at session 1
        self.assertAlmostEqual(out["exit_price_as_traded"], 15.0)   # exit at session 3
        self.assertAlmostEqual(out["net_return"], (1 - SEC_FEE - 0.0015) / (1 + 0.0005) - 1)

    def test_as_traded_needs_factors_and_valid_ones(self):
        m = Market.from_panel(bars(), price_limits=False)
        with self.assertRaises(ValueError):
            one(m, cfg(units="as_traded"))
        with self.assertRaises(ValueError):
            m.with_units(np.zeros(m.shape))

    def test_rule_view_cannot_see_unit_factor(self):
        """Guards against: a detector reading factors built from later corporate actions."""
        m = Market.from_panel(bars(), price_limits=False).with_units(np.full((1, 10), 0.5))
        view = CausalSource(m).view(5)
        with self.assertRaises(AttributeError):
            view.unit_factor

    def test_price_band_uses_the_traded_price(self):
        m = Market.from_panel(bars(open_=6.0, close=6.0), price_limits=False).with_units(np.full((1, 10), 0.1))
        self.assertEqual(int(controls.features(m, "v2", US.band_edges)["price_band"][0, 5]), 2)        # $5-20
        self.assertEqual(int(controls.features(m, "v2", US.band_edges, as_traded=True)["price_band"][0, 5]), 0)


class FillModels(unittest.TestCase):
    def market(self, entry_volume):
        df = bars(n_sessions=30)
        df.loc[df["date"] == df["date"].unique()[21], ["volume", "value"]] = [entry_volume, entry_volume * 3.0]
        m = Market.from_panel(df, price_limits=False)
        return m.with_units(np.ones(m.shape))

    def run_at(self, m, model):
        out = execute(m, np.array([0]), np.array([20]), cfg(units="as_traded", fill_model=model))
        return STATUS[out["status"][0]]

    def test_model_a_depends_on_the_entry_sessions_final_volume(self):
        """Reproduces Hermes's finding: same opening, different end-of-day volume, different fill."""
        self.assertEqual(self.run_at(self.market(10_000.0), "A"), "SKIP_LIQUIDITY")
        self.assertEqual(self.run_at(self.market(1_000_000.0), "A"), "EXITED")

    def test_model_b_decides_from_volume_known_at_the_decision(self):
        """Guards against: an opening fill accepted or refused by volume printed after the open."""
        self.assertEqual(self.run_at(self.market(10_000.0), "B"), self.run_at(self.market(1_000_000.0), "B"))
        self.assertEqual(self.run_at(self.market(10_000.0), "B"), "EXITED")

    def test_model_b_refuses_when_recent_volume_is_too_thin(self):
        df = bars(n_sessions=30, volume=10_000.0)  # 10% of 10,000 shares < 1,666 shares
        m = Market.from_panel(df, price_limits=False).with_units(np.ones((1, 30)))
        out = execute(m, np.array([0]), np.array([20]), cfg(units="as_traded", fill_model="B"))
        self.assertEqual(STATUS[out["status"][0]], "SKIP_LIQUIDITY")

    def test_model_b_counts_listed_days_without_trades_as_zero(self):
        """Guards against: capacity read from the few days a thin name happened to trade."""
        df = bars(n_sessions=30)
        days = df["date"].unique()
        df.loc[df["date"].isin(days[1:20:2]) | df["date"].isin(days[2:19:4]), ["volume", "value"]] = [0.0, 0.0]
        m = Market.from_panel(df, price_limits=False).with_units(np.ones((1, 30)))
        out = execute(m, np.array([0]), np.array([20]), cfg(units="as_traded", fill_model="B"))
        self.assertEqual(STATUS[out["status"][0]], "SKIP_LIQUIDITY")  # median of 20 sessions is 0

    def test_model_b_requires_as_traded_open_entries(self):
        m = Market.from_panel(bars(), price_limits=False)
        with self.assertRaises(ValueError):
            one(m, cfg(fill_model="B"))


class SplitEvidence(unittest.TestCase):
    def test_effective_session_is_already_in_new_units(self):
        """Guards against: an off-by-one at the split boundary (Yahoo stamps 09:30 on the new-units session)."""
        ev = pd.DataFrame([{"effective_session": "2020-01-03", "numerator": 1.0, "denominator": 10.0}])
        f = us_actions.unit_factors(np.array(["2020-01-02", "2020-01-03", "2020-01-06"], dtype="datetime64[D]"), ev)
        self.assertEqual(f.tolist(), [0.1, 1.0, 1.0])

    def test_price_adjustments_are_not_called_splits(self):
        self.assertEqual(us_actions.classify_ratio(1, 10), "SPLIT")
        self.assertEqual(us_actions.classify_ratio(3, 2), "SPLIT")
        self.assertEqual(us_actions.classify_ratio(1, 250), "SPLIT")
        self.assertEqual(us_actions.classify_ratio(1281, 1000), "NOT_A_SPLIT")  # GE HealthCare spin-off
        self.assertEqual(us_actions.classify_ratio(1019, 1000), "NOT_A_SPLIT")

    def test_filing_must_state_the_same_ratio(self):
        """Guards against: corroborating a 1:10 provider record with a filing about a 1:20 split."""
        text = ("The Board approved a 1-for-20 reverse stock split. The common stock will begin trading on a "
                "split-adjusted basis at the open on March 6, 2023.")
        good = us_actions.judge(text, 1, 20, date(2023, 3, 6))
        self.assertTrue(good["ratio_ok"] and good["date_ok"])
        self.assertFalse(us_actions.judge(text, 1, 10, date(2023, 3, 6))["ratio_ok"])
        self.assertFalse(us_actions.judge(text, 1, 20, date(2023, 3, 7))["date_ok"])

    def test_phrasings(self):
        cases = {
            "one (1) post-consolidation share for every ten (10) pre-consolidation shares": (1, 10),
            "every twenty-five (25) shares of common stock issued and outstanding will be combined into one (1) share": (1, 25),
            "a three-for-two stock split": (3, 2),
            "a 1:35 reverse split": (1, 35),
        }
        for text, pair in cases.items():
            with self.subTest(text=text):
                self.assertIn(pair, us_actions.ratios_in(text))

    def test_reversed_wording_needs_reverse_words(self):
        """'10-for-1 reverse split' is a common misstatement of 1-for-10; accept it only with
        reverse/consolidation wording, never for a forward split record."""
        self.assertTrue(us_actions.judge("a 10-for-1 reverse stock split", 1, 10, date(2023, 1, 3))["ratio_ok"])
        self.assertFalse(us_actions.judge("a 10-for-1 stock split", 1, 10, date(2023, 1, 3))["ratio_ok"])


class RepairRun(unittest.TestCase):
    def panel(self):
        rng = np.random.default_rng(3)
        dates = pd.date_range("2020-01-01", periods=60, freq="B")
        rows = []
        for i in range(60):
            p = 4.0
            for k, d in enumerate(dates):
                prev = p
                step = 0.4 if (i in (3, 7) and k == 40) else rng.normal(0, 0.01)
                p = prev * (1 + step)
                rows.append(dict(date=d, ticker=f"T{i:02d}", source="synthetic", previous=prev, open=prev, high=max(p, prev),
                                 low=min(p, prev), close=p, volume=1e6, value=1e6 * p, frequency=np.nan,
                                 listed_shares=np.nan, tradable_shares=np.nan, unit_factor=0.5 if i == 3 else 1.0,
                                 qa_reverting_spike=0))
        df = pd.DataFrame(rows)
        meta = {"sha256": "0" * 64, "panel": "synthetic", "source_boundary": "2020-03-24", "default_start": "2020-01-01",
                "survivorship": "synthetic", "quality_tiers": [{"tier": "US_SURVIVOR", "from": "2020-01-01",
                                                                 "to": "2020-03-24"}],
                "known_limitations": [], "preprocessing": "causal-close-v2",
                "unit_quarantine": {"tickers": {"T07": ["NO_EVIDENCE"]}, "reason_counts": {"NO_EVIDENCE": 1}}}
        return df, meta

    def test_quarantine_removes_names_from_both_sides(self):
        """Guards against: excluding a name from the detector but still drawing it as a control."""
        from idxsig.backtest import RunConfig, run

        warnings.simplefilter("ignore")
        df, meta = self.panel()
        base = dict(rule_id="MOONSHOT_E2_US_D1", market="US", ca_mode="adjusted", notional=5000.0, fee_buy=0.0,
                    fee_sell=US.fee_sell, random_draws=20, units="as_traded")
        kept = run(RunConfig(**base), df, meta)
        dropped = run(RunConfig(**base, quarantine="unit_schedule"), df, meta)
        self.assertEqual(set(kept["trades"]["ticker"]), {"T03", "T07"})
        self.assertEqual(set(dropped["trades"]["ticker"]), {"T03"})
        self.assertEqual(dropped["summary"]["repair"]["quarantine"]["tickers_excluded"], 1)
        self.assertEqual(dropped["summary"]["universe"]["tickers_ever_evaluable"],
                         kept["summary"]["universe"]["tickers_ever_evaluable"] - 1)
        row = dropped["trades"].iloc[0]
        self.assertAlmostEqual(row["entry_price_as_traded"], row["entry_price"] * 0.5)
        self.assertIn("qa_sensitivity", dropped["summary"]["repair"])


if __name__ == "__main__":
    unittest.main()


class FakeSec:
    """Serves EDGAR search and documents from a dict; nothing leaves the machine."""

    def __init__(self, docs):
        self.docs = docs

    def get(self, url):
        import json as _json

        if url.startswith("https://efts.sec.gov"):
            hits = [{"_id": f"0000000000-23-00000{i}:{name}", "_source": {"form": "8-K", "file_date": "2023-03-01",
                                                                           "file_type": "8-K"}}
                    for i, name in enumerate(self.docs)]
            return 200, _json.dumps({"hits": {"hits": hits}}).encode()
        name = url.rsplit("/", 1)[-1]
        return 200, self.docs[name].encode()


class Coverage(unittest.TestCase):
    def test_jump_rows_are_found_and_marked(self):
        panel = pd.DataFrame({"ticker": ["A", "A", "B", "C"], "date": pd.to_datetime(["2023-03-06"] * 4),
                              "close": [10.0, 10.0, 1.0, 10.5], "previous": [1.0, 1.0, 2.5, 10.0]}).iloc[[0, 2, 3]]
        ev = pd.DataFrame([{"ticker": "B", "effective_session": "2023-03-06"}])
        rows = us_actions.jump_rows(panel, ev, "2023-01-03", "2023-12-29")
        self.assertEqual(rows["ticker"].tolist(), ["A", "B"])  # C moved 5%: not a jump
        self.assertEqual(rows["on_record_session"].tolist(), [False, True])

    def test_an_unrecorded_split_is_caught_only_with_filing_evidence(self):
        """Guards against: a fake +900% day from a split the provider never adjusted for, and
        against calling a genuine move a split without a filing that says so."""
        no_events = pd.DataFrame(columns=["ticker", "effective_session"])
        dated = FakeSec({"a.htm": "a 1-for-10 reverse stock split effective at the open on March 6, 2023"})
        res = us_actions.check_jump(dated, {"A": 1}, no_events, "A", "2023-03-06", 9.6, False)
        self.assertEqual(res["status"], "MISSING_PROVIDER_SPLIT")
        silent = FakeSec({"a.htm": "the company announced a partnership"})
        self.assertEqual(us_actions.check_jump(silent, {"A": 1}, no_events, "A", "2023-03-06", 9.6, False)["status"],
                         "NO_SPLIT_EVIDENCE")
        wrong = FakeSec({"a.htm": "a 1-for-2 reverse stock split effective March 6, 2023"})  # x2, not x9.6
        self.assertEqual(us_actions.check_jump(wrong, {"A": 1}, no_events, "A", "2023-03-06", 9.6, False)["status"],
                         "NO_SPLIT_EVIDENCE")
        near = pd.DataFrame([{"ticker": "A", "effective_session": "2023-03-08"}])
        self.assertEqual(us_actions.check_jump(dated, {"A": 1}, near, "A", "2023-03-06", 9.6, False)["status"],
                         "PROVIDER_DATE_MISMATCH")
        self.assertEqual(us_actions.check_jump(dated, {}, no_events, "A", "2023-03-06", 9.6, False)["status"], "NO_CIK")
