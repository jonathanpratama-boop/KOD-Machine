"""Experiment E5 rule module (rules/moonshot_e5): features, ranks, debounce, candidates. Synthetic data only.

No panel, no network, no harness run on real data. The KOD price_facts module is imported read-only
from kod-machine/research/ZEALAND_PILOT_v1/03_card to check the pre-spike block against its definitions.
"""

import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from idxsig import e1, rules
from idxsig.execution import Market
from idxsig.rules import moonshot_e1, moonshot_e5, moonshot_g
from idxsig.rules.audit import audit_module
from tests.support import flat_market, random_walk_panel

ROOT = Path(__file__).resolve().parents[2]
PRICE_FACTS = ROOT / "kod-machine" / "research" / "ZEALAND_PILOT_v1" / "03_card" / "price_facts.py"
W = moonshot_e5.FEATURE_WARMUP  # features() NaN before this column
WF = moonshot_e5.WARMUP  # compute() NaN before this column: the first flag a window can emit
ARM_NAMES = tuple(m + "_" + a for m in moonshot_e5.MARKETS for a in moonshot_e5.ARMS)


def load_price_facts():
    """kod-machine's price_facts module, read-only (measures() is pure; nothing on disk is read)."""
    spec = importlib.util.spec_from_file_location("_e5_test_price_facts", PRICE_FACTS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def feats(m):
    return moonshot_e5.features(*[getattr(m, a) for a in moonshot_e5.FEATURE_ARGS])


def open_panel(n_tickers=30, n_sessions=160, seed=5, **kw):
    """A US/crypto-shaped market: opening prices, no price limits."""
    df, _ = random_walk_panel(n_tickers=n_tickers, n_sessions=n_sessions, seed=seed, **kw)
    df["open"] = df["previous"]
    return Market.from_panel(df, price_limits=False)


def set_close(a, i, s, price, span=0.0):
    """Row i closes at `price` on session s and stays there; the next sessions reference it."""
    a["close"][i, s:] = price
    a["prev"][i, s + 1:] = price
    a["high"][i, s] = max(price, a["prev"][i, s]) * (1 + span)
    a["low"][i, s] = min(price, a["prev"][i, s]) * (1 - span)
    a["high"][i, s + 1:] = price * (1 + span)
    a["low"][i, s + 1:] = price * (1 - span)
    a["value"][i, s:] = a["close"][i, s:] * a["volume"][i, s:]


def build_open(t, d, a):
    return Market.build(t, d, a["close"], a["prev"], a["high"], a["low"], a["volume"], a["value"], a["present"],
                        None, opens=a["close"], price_limits=False)


def creep_quiet_market(n_sessions=90, seed=3):
    """Three names; row 0 carries a designed pre-spike episode: calm prices with a narrow range over
    sessions 74..80 and doubled volume over 76..80, so creep5v20 >= 1.5 and quiet hold at t = 78..80."""
    rng = np.random.default_rng(seed)
    t, d, a = flat_market(n_tickers=3, n_sessions=n_sessions, price=1000.0, volume=1_000_000.0)
    close = 1000.0 * np.cumprod(1 + rng.normal(0.0, 0.004, n_sessions))
    close[74:81] = close[73] * np.cumprod(1 + rng.normal(0.0, 0.0004, 7))
    close = np.round(close, 2)
    prev = np.concatenate([[1000.0], close[:-1]])
    span = np.where((np.arange(n_sessions) >= 74) & (np.arange(n_sessions) <= 80), 0.003, 0.012)
    volume = np.round(1_000_000.0 * (1 + rng.uniform(-0.1, 0.1, n_sessions)))
    volume[76:81] *= 2.0
    a["close"][0], a["prev"][0], a["volume"][0] = close, prev, volume
    a["high"][0] = np.maximum(close, prev) * (1 + span)
    a["low"][0] = np.minimum(close, prev) * (1 - span)
    a["value"][0] = close * volume
    return t, d, a


def bars_of(a, i, dates):
    return [{"open": float(a["prev"][i, s]), "high": float(a["high"][i, s]), "low": float(a["low"][i, s]),
             "close": float(a["close"][i, s]), "volume": float(a["volume"][i, s]), "date": str(dates[s])}
            for s in range(a["close"].shape[1])]


def frozen_us_a(coef_on=("ret1_r", "volr_r", "cpos_r"), threshold=2.0):
    """Synthetic literals for the US Arm A ranker (a test fixture, never a fit)."""
    coef = tuple(1.0 if name in coef_on else 0.0 for name in moonshot_e5.FEATURE_ORDER)
    return {"COEF_U": (("IDX", None), ("US", coef), ("CRYPTO", None)),
            "INTERCEPT_U": (("IDX", None), ("US", 0.0), ("CRYPTO", None)),
            "THRESHOLD_A": (("IDX", None), ("US", threshold), ("CRYPTO", None))}


class patched:
    """Temporarily replace module literals (restored afterwards, as test_e4 does with SELECTED)."""

    def __init__(self, **values):
        self.values = values

    def __enter__(self):
        self.saved = {k: getattr(moonshot_e5, k) for k in self.values}
        for k, v in self.values.items():
            setattr(moonshot_e5, k, v)

    def __exit__(self, *exc):
        for k, v in self.saved.items():
            setattr(moonshot_e5, k, v)


class ModuleTests(unittest.TestCase):
    def test_identity_and_literals(self):
        self.assertEqual(moonshot_e5.RULE_ID, "MOONSHOT_E5")
        self.assertEqual(moonshot_e5.VERSION, "v1")
        self.assertEqual(moonshot_e5.SIDE, "long")
        self.assertEqual(moonshot_e5.FEATURE_WARMUP, 60)
        self.assertEqual(moonshot_e5.DEBOUNCE, 5)
        self.assertEqual(moonshot_e5.WARMUP, 65)  # the harness lead-in: feature warm-up plus the debounce
        self.assertEqual(moonshot_e5.WARMUP, moonshot_e5.FEATURE_WARMUP + moonshot_e5.DEBOUNCE)
        self.assertEqual(moonshot_e5.FEATURE_ARGS,
                         ("close", "prev", "high", "low", "volume", "value", "present", "tradeable", "lock_up",
                          "open", "listed_before"))  # listed_before added by the v1.1 audit addendum (finding B)
        self.assertEqual(moonshot_e5.MARKETS, ("IDX", "US", "CRYPTO"))
        self.assertEqual(moonshot_e5.ARMS, ("A", "B"))
        self.assertEqual(moonshot_e5.CANDIDATES, ARM_NAMES + ("A0_CREEP_QUIET", "A1_CREEP_QUIET_NR"))
        self.assertEqual(tuple(name for name, _ in moonshot_e5.FAMILY), moonshot_e5.CANDIDATES)
        self.assertIsNone(moonshot_e5.SELECTED)
        for table in (moonshot_e5.COEF_U, moonshot_e5.COEF_D, moonshot_e5.INTERCEPT_U, moonshot_e5.INTERCEPT_D,
                      moonshot_e5.THRESHOLD_A, moonshot_e5.THRESHOLD_B):
            self.assertEqual(tuple(k for k, _ in table), moonshot_e5.MARKETS)
            self.assertTrue(all(v is None for _, v in table))  # placeholders until discovery freezes them
        expected = (tuple(n + "_r" for n in moonshot_e5.RANKED) + tuple(n + "_r2" for n in moonshot_e5.RANKED)
                    + moonshot_e5.BINARY)
        self.assertEqual(moonshot_e5.FEATURE_ORDER, expected)
        self.assertEqual(len(set(moonshot_e5.FEATURE_ORDER)), len(moonshot_e5.FEATURE_ORDER))
        self.assertEqual(moonshot_e5.RANKED, ("ret1", "rel1", "ret5", "ret20", "volr", "valr", "rngr", "cpos",
                                              "vol20", "dd60", "up5", "zero20", "age", "logval20", "gap",
                                              "creep5v20", "rngr5", "vc10_60"))
        self.assertEqual(moonshot_e5.BINARY, ("brk60", "ara", "quiet", "not_repriced", "rebase"))

    def test_registered_and_audited(self):
        self.assertEqual(audit_module(moonshot_e5), [])
        reg = rules.registry()
        for name in moonshot_e5.CANDIDATES:
            rule = reg[moonshot_e5.candidate_rule_id(name)]
            self.assertEqual((rule.kind, rule.holding_days, rule.plan, rule.version), ("DETECTOR", 5, None, "v1"))
            self.assertIs(rule.module, moonshot_e5)
        self.assertIn("E5_CAND_IDX_A", reg)
        self.assertIn("E5_CAND_CRYPTO_B", reg)
        self.assertIn("E5_CAND_A1_CREEP_QUIET_NR", reg)
        for market in moonshot_e5.MARKETS:
            self.assertNotIn(moonshot_e5.selected_rule_id(market), reg)
        # every rule registered before this module is still there, unchanged
        for rule_id in ("MOONSHOT_E1_D1", "MOONSHOT_E2_US_D1", "E3_CAND_F1_ARA", "E4_CAND_G2_RET30", "MOONSHOT_E4_D1",
                        "PLACEBO_COINFLIP"):
            self.assertIn(rule_id, reg)

    def test_selected_rules_appear_once_frozen(self):
        lit = frozen_us_a()
        with patched(SELECTED=(("US", "A"),), **lit):
            found = {r.rule_id: r for r in moonshot_e5.rules()}
            self.assertIn("MOONSHOT_E5_US_D1", found)
            self.assertEqual(found["MOONSHOT_E5_US_D1"].holding_days, 5)
            self.assertIn("Selected for US: arm A", found["MOONSHOT_E5_US_D1"].text)
            self.assertTrue(moonshot_e5.frozen("US_A"))
            self.assertFalse(moonshot_e5.frozen("US_B"))
            with self.assertRaises(RuntimeError):
                with patched(SELECTED=(("IDX", "A"),)):
                    moonshot_e5.rules()  # selecting an arm without literals is refused
        self.assertNotIn("MOONSHOT_E5_US_D1", {r.rule_id for r in moonshot_e5.rules()})


class FeatureTests(unittest.TestCase):
    def test_copied_features_match_the_g_and_e1_families(self):
        df, _ = random_walk_panel(n_tickers=30, n_sessions=160, seed=5)
        df["open"] = df["previous"]
        m = Market.from_panel(df)  # IDX limits on, so ara can hold
        ours = feats(m)
        g = moonshot_g.features(m.close, m.prev, m.high, m.low, m.volume, m.present, m.tradeable, m.open)
        for k in ("ret1", "rel1", "ret5", "ret20", "volr", "dd60", "cpos", "gap"):
            np.testing.assert_array_equal(ours[k][:, W:], g[k][:, W:], err_msg=k)
        np.testing.assert_array_equal(ours["brk60"][:, W:], g["brk60"][:, W:].astype(float))
        e = moonshot_e1.features(m.close, m.prev, m.high, m.low, m.volume, m.present, m.tradeable, m.lock_up)
        np.testing.assert_array_equal(ours["ara"][:, W:], e["ara"][:, W:].astype(float))
        self.assertTrue(np.isfinite(ours["gap"][:, W:]).any())

    def test_weak_signals_match_e1_study(self):
        df, meta = random_walk_panel(n_tickers=30, n_sessions=160, seed=11, ipo={3: 70}, delist={4: 120})
        study = e1.Study(df, {**meta, "format": "panel-v2"})
        m = study.m
        ours = feats(m)
        for k in ("valr", "rngr", "vol20", "up5", "logval20"):
            np.testing.assert_allclose(ours[k][:, W:], study.sig[k][:, W:], equal_nan=True, err_msg=k)
        first = np.where(m.present.any(axis=1), m.present.argmax(axis=1), m.shape[1])
        listed = np.arange(m.shape[1])[None, :] >= first[:, None]
        for k in ("age", "zero20"):
            on = listed[:, W:]
            np.testing.assert_allclose(ours[k][:, W:][on], study.sig[k][:, W:][on], err_msg=k)
            self.assertTrue(np.isnan(ours[k][:, W:][~on]).all(), k)

    def test_age_and_zero20_are_nan_before_listing(self):
        df, _ = random_walk_panel(n_tickers=10, n_sessions=160, seed=2, ipo={3: 70})
        m = Market.from_panel(df)
        f = feats(m)
        for k in ("age", "zero20"):
            self.assertTrue(np.isnan(f[k][3, :70]).all(), k)
            self.assertFalse((np.nan_to_num(f[k][3, :70], nan=1.0) <= 0).any(), k)  # never negative or 0 there
        self.assertEqual(f["age"][3, 70], 0.0)
        self.assertEqual(f["age"][3, 75], 5.0)
        self.assertEqual(f["zero20"][3, 70], 0.0)  # sessions before the listing are not present: none untraded
        self.assertEqual(f["age"][0, 100], 100.0)

    def test_warmup_masks_features_for_60_columns_and_compute_for_65(self):
        m = open_panel()
        f = feats(m)
        for k, v in f.items():
            self.assertEqual(v.shape, m.shape, k)
            self.assertTrue(np.isnan(v[:, :W]).all(), k)
        for k in ("ret1", "ret1_r", "ret1_r2", "brk60", "creep5v20", "quiet", "rebase", "vc10_60"):
            self.assertTrue(np.isfinite(f[k][:, W:]).any(), k)
        for k in moonshot_e5.FEATURE_ORDER:
            self.assertTrue(np.isfinite(f[k][:, W:]).all(), k)  # ranks and binaries are known from column 60 on
        reg = rules.registry()
        sig = reg["E5_CAND_A0_CREEP_QUIET"].compute(m)
        self.assertTrue(np.isnan(sig[:, :WF]).all())  # the debounce needs five known sessions after the warm-up
        self.assertTrue(np.isin(sig[:, WF:][m.tradeable[:, WF:]], (0.0, 1.0)).all())
        self.assertTrue(np.isfinite(sig[:, WF][m.tradeable[:, WF]]).all())
        short = rules.CausalSource(m).view(30)  # a view shorter than the warm-up: NaN throughout
        self.assertTrue(np.isnan(reg["E5_CAND_A0_CREEP_QUIET"].compute(short)).all())
        edge = rules.CausalSource(m).view(WF - 1)  # a view that ends inside the lead-in: NaN throughout too
        self.assertTrue(np.isnan(reg["E5_CAND_A0_CREEP_QUIET"].compute(edge)).all())

    def test_pre_spike_block_matches_zealand_price_facts(self):
        pf = load_price_facts()
        t, d, a = creep_quiet_market()
        m = Market.build(t, d, a["close"], a["prev"], a["high"], a["low"], a["volume"], a["value"], a["present"])
        self.assertFalse(m.lock_up[0].any())
        f = feats(m)
        states = moonshot_e5.detector_states(f)
        bars = bars_of(a, 0, d)
        seen = set()
        for s in range(W, m.shape[1]):
            ref = pf.measures(bars, s)
            self.assertAlmostEqual(f["creep5v20"][0, s], ref["volume_ratio_5_vs_20"], places=9, msg=s)
            self.assertAlmostEqual(f["rngr5"][0, s], ref["median_rngr_5"], places=9, msg=s)
            self.assertAlmostEqual(f["vol20"][0, s], ref["vol20"], places=9, msg=s)
            self.assertAlmostEqual(f["ret5"][0, s], ref["ret5"], places=9, msg=s)
            self.assertAlmostEqual(f["ret20"][0, s], ref["ret20"], places=9, msg=s)
            facts = ref["facts"]
            self.assertEqual(bool(f["quiet"][0, s]), facts["price_quiet_vs_own_range"], s)
            self.assertEqual(bool(f["not_repriced"][0, s]), not facts["price_already_repriced"], s)
            # KOD-DET-v0 VOLUME_CREEP_PRICE_QUIET (kod/detectors.py:72-86): SIGNAL iff both facts are True
            a0 = facts["volume_creep_before_story"] is True and facts["price_quiet_vs_own_range"] is True
            self.assertEqual(bool(states["A0_CREEP_QUIET"][0, s]), a0, s)
            self.assertEqual(bool(states["A1_CREEP_QUIET_NR"][0, s]), a0 and not facts["price_already_repriced"], s)
            seen.add(a0)
        self.assertEqual(seen, {True, False})  # the designed episode fires, the rest of the series does not
        self.assertTrue(states["A0_CREEP_QUIET"][0, 78:81].all())
        self.assertFalse(states["A0_CREEP_QUIET"][0, 60:77].any())
        self.assertFalse(states["A0_CREEP_QUIET"][1:].any())

    def test_vc10_60_is_the_volatility_ratio(self):
        m = open_panel()
        f = feats(m)
        logret = np.where(m.tradeable & (m.prev > 0), np.log(m.close / m.prev), np.where(m.present, 0.0, np.nan))
        frame = pd.DataFrame(logret.T)
        v10 = frame.rolling(10, min_periods=8).std().to_numpy().T
        v60 = frame.rolling(60, min_periods=45).std().to_numpy().T
        np.testing.assert_allclose(f["vc10_60"][:, W:], (v10 / v60)[:, W:], equal_nan=True)

    def test_rebase_reads_a_spike_6_to_40_sessions_back(self):
        t, d, a = flat_market(n_tickers=2, n_sessions=130, price=100.0, volume=1e6)
        set_close(a, 0, 70, 140.0, span=0.005)  # +40% session: pre 100, peak 140
        set_close(a, 0, 71, 115.0, span=0.005)  # retraced to 115 <= 100 + 0.5 * 40, held above 100
        f = feats(build_open(t, d, a))
        rebase = f["rebase"][0]
        self.assertTrue(np.isnan(rebase[:W]).all())
        self.assertFalse(rebase[W:76].any())  # the spike is fewer than 6 sessions back
        self.assertTrue(rebase[76:111].all())  # s0 = 70 lies in [t-40, t-6] for t = 76..110
        self.assertFalse(rebase[111:].any())
        self.assertFalse(f["rebase"][1, W:].any())
        high = flat_market(n_tickers=2, n_sessions=130, price=100.0, volume=1e6)
        set_close(high[2], 0, 70, 140.0, span=0.005)
        set_close(high[2], 0, 71, 125.0, span=0.005)  # above the half-retrace line: not re-based
        self.assertFalse(feats(build_open(*high))["rebase"][0, W:].any())
        dip = flat_market(n_tickers=2, n_sessions=130, price=100.0, volume=1e6)
        set_close(dip[2], 0, 70, 140.0, span=0.005)
        set_close(dip[2], 0, 71, 115.0, span=0.005)
        set_close(dip[2], 0, 100, 95.0, span=0.005)  # below the pre-spike level
        set_close(dip[2], 0, 101, 115.0, span=0.005)
        r = feats(build_open(*dip))["rebase"][0]
        self.assertFalse(r[100:105].any())  # the dip sits inside t-4..t
        self.assertTrue(r[105:111].all())

    def test_rebase_takes_an_ara_lock_as_the_idx_spike(self):
        t, d, a = flat_market(n_tickers=2, n_sessions=130, price=1000.0, volume=1e6)
        set_close(a, 0, 70, 1250.0, span=0.0)  # +25%: locked at the ARA limit, below the +30% line
        set_close(a, 0, 71, 1100.0, span=0.005)
        m = Market.build(t, d, a["close"], a["prev"], a["high"], a["low"], a["volume"], a["value"], a["present"])
        self.assertTrue(m.lock_up[0, 70])
        f = feats(m)
        self.assertTrue(f["rebase"][0, 76:111].all())
        no_limits = build_open(t, d, a)  # the same bars without price limits: a +25% day is no spike
        self.assertFalse(feats(no_limits)["rebase"][0, W:].any())


class RankTests(unittest.TestCase):
    def test_rank_masks_by_present_and_tradeable_and_fills_nan(self):
        n = W + 2
        x = np.full((5, n), np.nan)
        x[:, W] = [3.0, 1.0, 2.0, np.nan, 5.0]
        x[:, W + 1] = [1.0, 1.0, 2.0, 7.0, 9.0]
        present = np.ones((5, n), dtype=bool)
        present[4] = False  # listed later: never in the pool
        tradeable = present.copy()
        tradeable[3, W + 1] = False  # present, untraded: out of the pool for that session
        f = {k: x for k in moonshot_e5.RANKED}
        f.update({k: np.zeros((5, n)) for k in moonshot_e5.BINARY})
        r = moonshot_e5.rank_features(f, present, tradeable)
        self.assertEqual(set(r), set(moonshot_e5.FEATURE_ORDER))
        np.testing.assert_allclose(r["ret1_r"][:, W], [2.5 / 3, 0.5 / 3, 1.5 / 3, 0.5, 0.5])
        np.testing.assert_allclose(r["ret1_r"][:, W + 1], [1.0 / 3, 1.0 / 3, 2.5 / 3, 0.5, 0.5])  # ties average
        np.testing.assert_allclose(r["ret1_r2"][:, W:], r["ret1_r"][:, W:] ** 2)
        self.assertTrue(np.isnan(r["ret1_r"][:, :W]).all())
        self.assertTrue(np.isnan(r["brk60"][:, :W]).all())
        np.testing.assert_array_equal(r["brk60"][:, W:], 0.0)
        empty = moonshot_e5.rank_features(f, np.zeros_like(present), np.zeros_like(present))
        np.testing.assert_array_equal(empty["ret1_r"][:, W:], 0.5)  # nobody in the pool: the median rank

    def test_ranks_are_prefix_first(self):
        """Column s of every ranked feature is the same whether or not later sessions and names are in view."""
        m = open_panel(n_tickers=20, n_sessions=100, seed=9, ipo={7: 80})
        src = rules.CausalSource(m)
        full = feats(src.view(m.shape[1] - 1))
        for d in (W, W + 5, 85, 99):
            view = src.view(d)
            part = feats(view)
            k = view.shape[0]
            for key in moonshot_e5.FEATURE_ORDER + moonshot_e5.RANKED:
                np.testing.assert_array_equal(part[key][:, d], full[key][:k, d], err_msg=f"{key} at {d}")


class FlagTests(unittest.TestCase):
    def test_score_is_a_logit_over_feature_order(self):
        n = W + 1
        ranked = {k: np.full((2, n), i * 0.1) for i, k in enumerate(moonshot_e5.FEATURE_ORDER)}
        coef = tuple(float(i) for i in range(len(moonshot_e5.FEATURE_ORDER)))
        s = moonshot_e5.score(ranked, coef, -1.5)
        self.assertAlmostEqual(s[0, W], -1.5 + sum(i * i * 0.1 for i in range(len(coef))))
        with self.assertRaises(ValueError):
            moonshot_e5.score(ranked, coef[:-1], 0.0)
        ranked["ret1_r"][0, W] = np.nan
        self.assertTrue(np.isnan(moonshot_e5.score(ranked, coef, 0.0)[0, W]))

    def test_debounce_flags_the_first_session_above_after_five_known_below(self):
        s = np.full((6, 20), 0.0)
        s[0, [5, 6, 12, 16]] = 1.0  # 5: five below before it; 6: the session before was above; 12: 7..11 below
        s[1, :] = 1.0  # always above: never a first entry with five sessions below
        s[2, :5] = np.nan  # no score: unknown, NOT outside the set, so 5 has no known history and never flags
        s[2, 5] = 1.0
        s[2, 11] = 1.0  # 6..10 are five known sessions below: this is the first flag the row can carry
        s[3, 2] = 1.0  # fewer than five sessions of history: no flag
        s[4, 9] = np.nan  # a NaN inside the trailing five: 12 is not an entry after five known sessions below
        s[4, 12] = 1.0
        s[4, 18] = 1.0  # 13..17 known and below: flagged
        s[5, 7] = np.nan  # a NaN session is never itself a flag, and the run 8..12 below makes 13 an entry
        s[5, 13] = 1.0
        flags = moonshot_e5.flags(s, 1.0)
        self.assertEqual(sorted(np.flatnonzero(flags[0])), [5, 12])
        self.assertFalse(flags[1].any())
        self.assertEqual(list(np.flatnonzero(flags[2])), [11])
        self.assertFalse(flags[3].any())
        self.assertEqual(list(np.flatnonzero(flags[4])), [18])
        self.assertEqual(list(np.flatnonzero(flags[5])), [13])
        self.assertEqual(flags.dtype, bool)
        known = np.isfinite(s)
        state = known & (np.nan_to_num(s, nan=-np.inf) >= 1.0)
        np.testing.assert_array_equal(moonshot_e5.debounce(state, known), flags)
        np.testing.assert_array_equal(moonshot_e5.debounce(state[:2]), flags[:2])  # known=None: every session known
        prefix = moonshot_e5.flags(s[:, :13], 1.0)  # trailing: a shorter window changes no earlier column
        np.testing.assert_array_equal(prefix, flags[:, :13])
        # a window that starts inside a NaN stretch sees nothing that the full window does not: the
        # first column a window can flag has five known sessions below behind it, wherever it starts
        later = moonshot_e5.flags(s[:, 3:], 1.0)
        np.testing.assert_array_equal(later[:, 5:], flags[:, 8:])
        self.assertFalse(later[:, :5].any())

    def test_flags_are_window_invariant_from_the_lead_in(self):
        """The same session carries the same flag whether the window starts 0 or 20 sessions earlier: no
        burst of every in-set name at the first evaluable column (the reviewer's probe, frozen)."""
        m = open_panel(n_tickers=30, n_sessions=200, seed=5)
        lo = 20
        with patched(**frozen_us_a(threshold=1.9)):
            f_full, f_part = feats(m), feats(m.slice(lo, m.shape[1]))
            s_full = moonshot_e5.arm_score(f_full, "US", "A")
            np.testing.assert_allclose(s_full[:, lo + W:], moonshot_e5.arm_score(f_part, "US", "A")[:, W:])
            full, part = moonshot_e5.family_flags(f_full), moonshot_e5.family_flags(f_part)
            for name in ("US_A", "A0_CREEP_QUIET", "A1_CREEP_QUIET_NR"):
                self.assertFalse(full[name][:, :WF].any(), name)  # nothing before five known sessions
                self.assertFalse(part[name][:, :WF].any(), name)
                np.testing.assert_array_equal(full[name][:, lo + WF:], part[name][:, WF:], err_msg=name)
            in_set = np.isfinite(s_full) & (np.nan_to_num(s_full, nan=-np.inf) >= 1.9)
            self.assertGreater(int(in_set[:, W].sum()), 1)  # several names are in the set at the first scored column
            self.assertFalse(full["US_A"][:, W].any())  # ... and none of them is a flag there (the old burst)
            first = full["US_A"][:, WF]  # at the first flaggable column only true entries after five sessions out
            self.assertTrue((~in_set[:, W:WF][first]).all())
            self.assertTrue(in_set[:, WF][first].all())
            self.assertGreater(int(full["US_A"].sum()), 0)
            rule = rules.registry()["E5_CAND_US_A"]
            a, b = rule.compute(m), rule.compute(m.slice(lo, m.shape[1]))
            np.testing.assert_array_equal(a[:, lo + WF:], b[:, WF:])
            self.assertTrue(np.isnan(a[:, :WF]).all())
            self.assertTrue(np.isnan(b[:, :WF]).all())

    def test_unfrozen_arms_have_no_flags_and_their_rules_refuse_to_run(self):
        m = open_panel(n_tickers=10, n_sessions=90)
        f = feats(m)
        flags = moonshot_e5.family_flags(f)
        self.assertEqual(set(flags), set(moonshot_e5.CANDIDATES))
        for name in ARM_NAMES:
            self.assertFalse(flags[name].any(), name)
            self.assertFalse(moonshot_e5.frozen(name))
            self.assertIsNone(moonshot_e5.arm_score(f, *name.split("_")))
            with self.assertRaises(RuntimeError) as ctx:
                rules.registry()[moonshot_e5.candidate_rule_id(name)].compute(m)
            self.assertIn(name, str(ctx.exception))
            self.assertIn("frozen", str(ctx.exception))
        for name in ("A0_CREEP_QUIET", "A1_CREEP_QUIET_NR"):
            self.assertTrue(moonshot_e5.frozen(name))
            rules.registry()[moonshot_e5.candidate_rule_id(name)].compute(m)

    def test_frozen_arm_is_causal_and_debounced(self):
        m = open_panel(n_tickers=30, n_sessions=160, seed=5)
        lit = frozen_us_a(threshold=2.0)
        with patched(**lit):
            self.assertTrue(moonshot_e5.frozen("US_A"))
            self.assertFalse(moonshot_e5.frozen("US_B"))  # Arm B also needs the D fit
            f = feats(m)
            s = moonshot_e5.arm_score(f, "US", "A")
            expect = f["ret1_r"] + f["volr_r"] + f["cpos_r"]
            np.testing.assert_allclose(s[:, W:], expect[:, W:])
            self.assertEqual(moonshot_e5.arm_threshold("US", "A"), 2.0)
            flags = moonshot_e5.family_flags(f)["US_A"]
            np.testing.assert_array_equal(flags, moonshot_e5.flags(s, 2.0))
            self.assertGreater(flags.sum(), 0)
            rule = rules.registry()["E5_CAND_US_A"]
            sig, info = rules.causal_signals(rule, m)  # prefix-first: raises LookaheadError on any difference
            self.assertEqual(info["full_window_mismatches"], 0)
            self.assertEqual(info["source_audit"], "passed")
            np.testing.assert_array_equal(sig[:, WF:], np.where(m.tradeable, flags.astype(float), np.nan)[:, WF:])
            self.assertTrue(np.isnan(sig[:, :WF]).all())
            self.assertFalse(flags[:, :WF].any())  # the mask hides nothing: no flag exists before the lead-in
            self.assertGreater(np.nansum(sig), 0)
            with patched(THRESHOLD_B=(("IDX", None), ("US", 0.0), ("CRYPTO", None)),
                         COEF_D=lit["COEF_U"], INTERCEPT_D=lit["INTERCEPT_U"]):
                self.assertTrue(moonshot_e5.frozen("US_B"))
                b = moonshot_e5.arm_score(f, "US", "B")  # logit_U - logit_D, here identical fits: zero
                np.testing.assert_allclose(b[:, W:], 0.0, atol=1e-12)
                self.assertFalse(moonshot_e5.family_flags(f)["US_B"][:, :WF].any())

    def test_creep_quiet_rules_are_causal_and_debounced(self):
        t, d, a = creep_quiet_market()
        m = Market.build(t, d, a["close"], a["prev"], a["high"], a["low"], a["volume"], a["value"], a["present"])
        reg = rules.registry()
        states = moonshot_e5.detector_states(feats(m))
        for name in ("A0_CREEP_QUIET", "A1_CREEP_QUIET_NR"):
            sig, _ = rules.causal_signals(reg[moonshot_e5.candidate_rule_id(name)], m)
            known = np.isfinite(feats(m)["quiet"])
            expect = np.where(m.tradeable, moonshot_e5.debounce(states[name], known).astype(float), np.nan)
            expect[:, :WF] = np.nan
            np.testing.assert_array_equal(sig, expect)
            self.assertEqual(list(np.flatnonzero(sig[0] == 1.0)), [78])  # one flag per episode, at its first session
            self.assertFalse((sig[1:] == 1.0).any())
            # the same episode, seen from a window that starts 10 sessions later: the same single flag
            later, _ = rules.causal_signals(reg[moonshot_e5.candidate_rule_id(name)], m.slice(10, m.shape[1]))
            np.testing.assert_array_equal(later[:, WF:], sig[:, 10 + WF:])
            self.assertEqual(list(np.flatnonzero(later[0] == 1.0)), [68])



class ListingAgeTests(unittest.TestCase):
    """Audit finding B (2026-10-14, research/E5/v1.1): age was counted from the window's first column, so a
    window start past a listing changed same-date age ranks and scores beyond the warm-up; the existing
    invariance fixture had every name listed before the window."""

    def _market_with_a_listing(self, listed_at=30, n_sessions=220):
        df, _ = random_walk_panel(n_tickers=30, n_sessions=n_sessions, seed=7)
        df["open"] = df["previous"]
        dates = np.array(sorted(df["date"].unique()))
        name = sorted(df["ticker"].unique())[3]
        df = df[~((df["ticker"] == name) & (df["date"].to_numpy() < dates[listed_at]))]
        return Market.from_panel(df, price_limits=False), name

    def test_market_carries_sessions_listed_before_through_slice(self):
        m, name = self._market_with_a_listing(30)
        i = list(m.tickers).index(name)
        self.assertEqual(int(m.listed_before[i]), 0)
        part = m.slice(45, m.shape[1])
        self.assertEqual(int(part.listed_before[i]), 15)
        self.assertEqual(int(part.listed_before[0]), 45)
        again = part.slice(10, part.shape[1])
        self.assertEqual(int(again.listed_before[i]), 25)
        self.assertEqual(int(again.listed_before[0]), 55)
        self.assertEqual(int(m.truncate(100).listed_before[i]), 0)

    def test_age_ranks_and_scores_survive_a_window_start_after_a_listing(self):
        m, name = self._market_with_a_listing(30)
        i = list(m.tickers).index(name)
        lo = 45
        part = m.slice(lo, m.shape[1])
        with patched(**frozen_us_a(coef_on=("age_r", "ret1_r", "volr_r"), threshold=1.9)):
            f_full, f_part = feats(m), feats(part)
            raw_full = moonshot_e5.raw_features(*[getattr(m, a) for a in moonshot_e5.FEATURE_ARGS])
            raw_part = moonshot_e5.raw_features(*[getattr(part, a) for a in moonshot_e5.FEATURE_ARGS])
            np.testing.assert_allclose(raw_full["age"][:, lo:], raw_part["age"], equal_nan=True)  # before the warm-up blank
            self.assertEqual(raw_full["age"][i, lo], float(lo - 30))
            self.assertTrue(np.isnan(raw_full["age"][i, 29]))
            self.assertEqual(raw_full["age"][0, lo], float(lo))  # listed at the panel start: left-censored count
            np.testing.assert_allclose(f_full["age_r"][:, lo + W:], f_part["age_r"][:, W:], equal_nan=True)
            s_full, s_part = moonshot_e5.arm_score(f_full, "US", "A"), moonshot_e5.arm_score(f_part, "US", "A")
            np.testing.assert_allclose(s_full[:, lo + W:], s_part[:, W:], equal_nan=True)
            rule = rules.registry()["E5_CAND_US_A"]
            a, b = rule.compute(m), rule.compute(part)
            np.testing.assert_array_equal(a[:, lo + WF:], b[:, WF:])
        # the defect, reproduced: age counted from the window start (no listing history) moves the ranks
        args = [getattr(part, a) for a in moonshot_e5.FEATURE_ARGS]
        args[-1] = np.zeros(part.shape[0], dtype=np.int64)
        f_old = moonshot_e5.features(*args)
        self.assertFalse(np.allclose(f_old["age_r"][:, W:], f_full["age_r"][:, lo + W:], equal_nan=True))

    def test_features_refuse_an_unknown_listing_history(self):
        m, _ = self._market_with_a_listing(30)
        args = [getattr(m, a) for a in moonshot_e5.FEATURE_ARGS]
        args[-1] = None
        with self.assertRaises(ValueError):
            moonshot_e5.features(*args)


if __name__ == "__main__":
    unittest.main()
