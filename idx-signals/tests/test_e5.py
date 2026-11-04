"""Experiment E5 study code (idxsig/e5.py), the draft protocol and the e5-* CLI. Synthetic panels only:
no real panel is loaded, no network, no harness run on real data, nothing reads the holdout. The draft
protocol research/E5/protocol.json is read for its shape and values; the tests that run the study use a
copy with synthetic panel hashes and reduced draw / resample counts (mechanics, not statistics)."""

import copy
import json
import tempfile
import types
import unittest
import warnings
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from idxsig import cli, e1, e3, e5, rules
from idxsig.backtest import HoldoutSealed, RunConfig, paired_excess, run
from idxsig.execution import Market
from idxsig.market import floor_tick
from idxsig.profiles import PROFILES
from idxsig.rules import moonshot_e5
from idxsig.rules.audit import audit_module
from tests.rulekit import module_rule, with_rule
from tests.support import flat_market, random_walk_panel, synthetic_registry

ROOT = Path(__file__).resolve().parents[1]
PROTO, PROTO_SHA = e5.protocol()
W, WF = moonshot_e5.FEATURE_WARMUP, moonshot_e5.WARMUP
FORMATS = {"IDX": "panel-v2", "US": "panel-global-v2-units", "CRYPTO": "panel-global-v1"}


# ------------------------------------------------------------------------------------------- fixtures
def e5_panel(market="IDX", n=30, start="2020-03-02", end="2023-12-29", seed=3, reset=None):
    """A random-walk panel in the market's shape with planted +20%x3 (U) and -9%x3 (D) runs; `reset`
    {ticker index: session index} plants a x25 unit reset (crypto) at that session."""
    rng = np.random.default_rng(seed)
    dates = pd.to_datetime(
        np.arange(np.datetime64(start, "D"), np.datetime64(end, "D") + 1, dtype="datetime64[D]")
    )
    dates = dates[dates.weekday < 5]
    idx = market == "IDX"
    rows = []
    for i in range(n):
        price = float(rng.choice([150, 480, 1500] if idx else [0.5, 3.0, 12.0, 50.0]))
        up = down = 0
        for d in range(len(dates)):
            prev = price
            if up == 0 and down == 0:
                r = rng.random()
                if r < 0.004:
                    up = 3
                elif r < 0.008:
                    down = 3
            if up:
                step, up = 0.20, up - 1
            elif down:
                step, down = -0.09, down - 1
            else:
                step = float(np.clip(rng.normal(0, 0.02), -0.06, 0.06))
            if (reset or {}).get(i) == d:
                step = 24.0
            price = prev * (1 + step)
            if idx:
                price = float(min(max(floor_tick(np.array([price]))[0], 60.0), 4500.0))
            else:
                price = round(max(price, 0.01), 4)
            vol = int(rng.integers(100_000, 1_000_000))
            rows.append(
                {
                    "date": dates[d],
                    "ticker": f"S{i:03d}",
                    "source": "synthetic",
                    "previous": prev,
                    "open": pd.NA if idx else prev,
                    "high": max(prev, price),
                    "low": min(prev, price),
                    "close": price,
                    "volume": vol,
                    "value": vol * price,
                    "frequency": 100,
                    "listed_shares": 10**9 if idx else np.nan,
                    "tradable_shares": 10**9 if idx else np.nan,
                }
            )
    df = pd.DataFrame(rows)
    if idx:
        for c in (
            "previous",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "value",
            "frequency",
            "listed_shares",
            "tradable_shares",
        ):
            df[c] = df[c].astype("Int64")
    else:
        df["open"] = df["open"].astype(float)
    if market == "US":
        df["unit_factor"] = 1.0
    meta = {
        "sha256": f"synthetic-{market}",
        "panel": "synthetic",
        "source_boundary": end,
        "format": FORMATS[market],
        "default_start": start,
        "quality_tiers": [],
        "known_limitations": [],
        "survivorship": "synthetic",
        "unit_quarantine": {"tickers": {}, "reason_counts": {}},
        "unit_schedule": None,
        "preprocessing": None,
        "first_session": str(dates[0].date()),
        "last_session": end,
    }
    return df, meta


def test_proto(over: dict | None = None) -> dict:
    """The draft protocol with synthetic panel hashes and reduced draw / resample counts; `over` maps
    dotted keys to replacement values."""
    p = copy.deepcopy(PROTO)
    for mk in e5.MARKETS:
        p["markets"][mk]["panel_sha256"] = f"synthetic-{mk}"
    p["matched_controls"]["detection_stage"]["draws"] = 20
    p["matched_controls"]["paired_statistic"]["resamples"] = 200
    p["stages"]["1_information"]["univariate"]["auc_bootstrap"] = 20
    p["harness"]["random_draws"] = 8
    p["harness"]["lookahead_cuts"] = 2
    for k, v in (over or {}).items():
        node = p
        keys = k.split(".")
        for key in keys[:-1]:
            node = node[key]
        node[keys[-1]] = v
    return p


def fake_reproduce(out: Path, meta: dict, status="REPRODUCED"):
    (out.parent / "reproduce").mkdir(parents=True, exist_ok=True)
    e3.write_json(
        out.parent / "reproduce" / "result.json", {"panel_sha256": meta["sha256"], "status": status}
    )


def frame_from_arrays(tickers, dates, a, opens=None, idx=True):
    rows = []
    for i, t in enumerate(tickers):
        for d, day in enumerate(dates):
            rows.append(
                {
                    "date": pd.Timestamp(day),
                    "ticker": str(t),
                    "source": "synthetic",
                    "previous": a["prev"][i, d],
                    "open": (opens[i, d] if opens is not None else pd.NA),
                    "high": a["high"][i, d],
                    "low": a["low"][i, d],
                    "close": a["close"][i, d],
                    "volume": a["volume"][i, d],
                    "value": a["value"][i, d],
                    "frequency": 100,
                    "listed_shares": 10**9 if idx else np.nan,
                    "tradable_shares": 10**9 if idx else np.nan,
                }
            )
    return pd.DataFrame(rows)


class Discovered:
    """One synthetic discovery per market, shared by the tests that need a fitted model (built lazily)."""

    cache = {}

    @classmethod
    def get(cls, market):
        if market not in cls.cache:
            warnings.simplefilter("ignore")
            df, meta = e5_panel(
                market,
                n=30,
                seed={"IDX": 3, "US": 4, "CRYPTO": 5}[market],
                reset={2: 300} if market == "CRYPTO" else None,
            )
            proto = test_proto()
            out = Path(tempfile.mkdtemp(prefix="idxsig-e5-")) / market / "discovery"
            fake_reproduce(out, meta)
            registry = synthetic_registry(df, meta) if market == "IDX" else None
            summary = e5.run_discovery(
                df, meta, registry, out, proto, "synthetic-sha", market, log=lambda *_: None
            )
            cls.cache[market] = {
                "df": df,
                "meta": meta,
                "proto": proto,
                "out": out,
                "summary": summary,
                "registry": registry,
                "model": json.loads((out / "model.json").read_text(encoding="utf-8")),
                "stage1": json.loads((out / "stage1.json").read_text(encoding="utf-8")),
                "gates": json.loads((out / "gates.json").read_text(encoding="utf-8")),
            }
        return cls.cache[market]


# ------------------------------------------------------------------------------------------- protocol
class ProtocolTests(unittest.TestCase):
    def test_draft_parses_and_every_key_e5_reads_is_present(self):
        self.assertEqual(PROTO["protocol_id"], "KOD-GLOBAL-E5-v1")
        self.assertIs(
            PROTO["frozen_before_analysis"], True
        )  # frozen in commit e1e57af (research/E5/PROTOCOL.md §Freeze)
        for path, _stage in e5.PROTOCOL_KEYS:
            for mk in e5.MARKETS:
                e5.get(PROTO, path.replace("<M>", mk))  # KeyError names a missing key
        with self.assertRaises(KeyError):
            e5.get(PROTO, "markets.IDX.no_such_key")
        for key in (
            "question",
            "null_hypothesis",
            "builds_on",
            "family",
            "learner",
            "features",
            "labels",
            "markets",
            "plans",
            "harness",
            "periods",
            "matched_controls",
            "stages",
            "admissibility",
            "validation",
            "consequences",
            "declared_leaks",
            "not_fixed_and_why",
            "search_size",
            "claims",
        ):
            self.assertIn(key, PROTO)

    def test_shape_e1_study_reads(self):
        self.assertEqual(PROTO["periods"]["discovery"], ["2020-07-01", "2022-12-31"])
        self.assertEqual(PROTO["periods"]["validation"], ["2023-01-01", "2023-12-31"])
        self.assertNotIn("ign", PROTO["weak_signals"]["binary"])
        self.assertNotIn(
            "data", PROTO
        )  # no single global panel_format: each market declares its own
        for mk, fmt in FORMATS.items():
            self.assertEqual(PROTO["markets"][mk]["panel_format"], fmt)
            self.assertIn(fmt, e1.PANEL_FORMATS)
        self.assertEqual(
            PROTO["markets"]["IDX"]["periods"]["discovery"], ["2021-01-22", "2022-12-30"]
        )
        self.assertEqual(
            PROTO["markets"]["IDX"]["periods"]["validation"], ["2023-01-02", "2023-12-29"]
        )
        self.assertEqual(
            PROTO["markets"]["CRYPTO"]["periods"]["discovery"], ["2020-07-01", "2022-12-31"]
        )
        self.assertEqual(PROTO["markets"]["IDX"]["discovery_years"], [2021, 2022])
        self.assertEqual(PROTO["markets"]["US"]["discovery_years"], [2020, 2021, 2022])

    def test_fixed_values_from_the_handoff_decisions(self):
        self.assertEqual(PROTO["harness"]["warmup_sessions"], moonshot_e5.WARMUP)
        self.assertEqual(PROTO["harness"]["warmup_sessions"], 65)
        self.assertEqual(list(PROTO["features"]["order"]), list(moonshot_e5.FEATURE_ORDER))
        self.assertEqual(PROTO["features"]["n_columns"], 41)
        mk = PROTO["markets"]
        self.assertEqual(mk["IDX"]["panel_manifest"], "panel-20261007T225823Z.json")
        self.assertTrue(mk["IDX"]["panel_sha256"].startswith("9d3a0718"))
        self.assertEqual(mk["IDX"]["registry_manifest"], "ca_registry-20261007T230210Z.json")
        self.assertEqual(mk["US"]["panel_manifest"], "panel_us_repair-20261008T114805Z.json")
        self.assertTrue(mk["US"]["panel_sha256"].startswith("8d3b7ce4"))
        self.assertEqual(mk["CRYPTO"]["panel_manifest"], "panel_crypto-20261008T003354Z.json")
        self.assertTrue(mk["CRYPTO"]["panel_sha256"].startswith("3dc12749"))
        for m in e5.MARKETS:  # the manifests are committed; their hashes are the protocol's
            manifest = json.loads(
                (ROOT / "data" / "manifests" / mk[m]["panel_manifest"]).read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["sha256"], mk[m]["panel_sha256"])
            self.assertEqual(manifest["format"], mk[m]["panel_format"])
            for run_dir in mk[m]["precondition_runs"]:
                self.assertEqual(e3.recorded_run(run_dir)["panel_sha256"], mk[m]["panel_sha256"])
        self.assertEqual(
            mk["IDX"]["precondition_runs"], ["results/runs/20261009T050040Z_MOONSHOT_E1_D1_v1.1"]
        )
        self.assertEqual(
            mk["US"]["precondition_runs"], ["results/runs/20261008T115656Z_MOONSHOT_E2_US_D1_v1"]
        )
        self.assertEqual(
            mk["CRYPTO"]["precondition_runs"],
            ["results/runs/20261008T005732Z_MOONSHOT_E2_CRYPTO_D1_v1"],
        )
        self.assertEqual(
            (mk["US"]["pool_units"], mk["IDX"]["pool_units"], mk["CRYPTO"]["pool_units"]),
            ("as_traded", "panel", "panel"),
        )
        self.assertEqual(
            (mk["IDX"]["primary_arm"], mk["CRYPTO"]["primary_arm"], mk["US"]["primary_arm"]),
            ("A", "B", None),
        )
        plans = PROTO["plans"]
        self.assertEqual(
            (
                plans["IDX"]["primary"]["fill_model"],
                plans["US"]["primary"]["fill_model"],
                plans["CRYPTO"]["primary"]["fill_model"],
            ),
            ("C", "B", "A"),
        )
        self.assertEqual(plans["CRYPTO"]["primary"]["jump_ratio"], 10.0)
        self.assertEqual(plans["US"]["primary"]["units"], "as_traded")
        self.assertEqual(plans["US"]["primary"]["quarantine"], "none")
        for m in e5.MARKETS:
            prof = PROFILES[m]
            pr = plans[m]["primary"]
            self.assertEqual(
                (pr["notional"], pr["fee_buy"], pr["fee_sell"]),
                (prof.notional, prof.fee_buy, prof.fee_sell),
            )
            self.assertEqual(
                (pr["entry_rule"], pr["exit_rule"], pr["holding_days"]), ("fixed", "fixed", 5)
            )
        self.assertEqual(
            [s["id"] for s in plans["IDX"]["sensitivities"]], ["fill_A", "one_tick_cost"]
        )
        self.assertEqual(
            [s["id"] for s in plans["US"]["sensitivities"]],
            ["fill_A_as_traded", "quarantine_unit_schedule", "stress_1_5pct_per_side"],
        )
        self.assertEqual(
            [s["id"] for s in plans["CRYPTO"]["sensitivities"]],
            ["participation_0_05_doubled_costs", "entry_at_close_t1"],
        )
        self.assertEqual(plans["CRYPTO"]["sensitivities"][1]["overrides"]["market"], "CRYPTO_CLOSE")
        h = PROTO["harness"]
        self.assertEqual(
            (
                h["random_draws"],
                h["seed"],
                h["controls_version"],
                h["controls_version_reported"],
                h["lookahead_cuts"],
            ),
            (200, 20261007, "v3", "v2", 12),
        )
        self.assertEqual(
            PROTO["selection"],
            {
                "note": PROTO["selection"]["note"],
                "min_scored": 200,
                "max_p_one_sided_vs_matched": 0.05,
                "min_scored_per_year": 50,
            },
        )
        self.assertEqual(PROTO["validation"]["min_scored"], {"IDX": 100, "US": 200, "CRYPTO": 100})
        self.assertEqual(
            PROTO["stages"]["4_validation"]["min_scored"], PROTO["validation"]["min_scored"]
        )
        self.assertEqual(PROTO["validation"]["claim_level"], "PROVISIONAL")
        g = PROTO["stages"]["1_information"]["gate_to_stage_2"]
        self.assertEqual((g["min_flags"], g["alpha"], g["min_flags_per_year"]), (200, 0.025, 50))
        self.assertEqual(
            PROTO["stages"]["1_information"]["primaries"],
            {"P1": ["IDX", "A"], "P2": ["CRYPTO", "B"]},
        )
        lr = PROTO["learner"]
        self.assertEqual(
            (
                lr["iterations"],
                lr["lambda_per_row"],
                lr["negative_subsample"],
                lr["negative_weight"],
                lr["seed"],
                lr["threshold_percentile"],
            ),
            (25, 0.001, 0.10, 10.0, 20261015, 99.5),
        )
        ps = PROTO["matched_controls"]["paired_statistic"]
        self.assertEqual(
            (ps["resamples"], ps["seed"], ps["cluster"]), (10000, 20261015, "signal_date")
        )
        ds = PROTO["matched_controls"]["detection_stage"]
        self.assertEqual((ds["pool_version"], ds["draws"], ds["seed"]), ("v3", 200, 20261008))
        self.assertEqual(PROTO["labels"]["unit_reset_censoring"]["markets"], ["CRYPTO"])
        self.assertEqual(len(PROTO["labels"]["unit_reset_censoring"]["known_cases_to_verify"]), 8)
        self.assertIn("6 fits", PROTO["search_size"])
        self.assertIn("no real orders", PROTO["claims"])
        self.assertEqual(
            PROTO["stages"]["0_reproduce"]["accepted_deviation"]["abs_tolerance"], 0.001
        )

    def test_harness_config_follows_the_protocol(self):
        cfg = e5.harness_config(PROTO, "IDX", "E5_CAND_IDX_A", "2020-10-15", "2022-12-30")
        self.assertEqual(
            (
                cfg.market,
                cfg.fill_model,
                cfg.ca_mode,
                cfg.units,
                cfg.notional,
                cfg.controls_version,
                cfg.lookahead_cuts,
                cfg.holding_days,
                cfg.entry_rule,
                cfg.exit_rule,
                cfg.tick_cost,
            ),
            ("IDX", "C", "registry", "panel", 10_000_000.0, "v3", 12, 5, "fixed", "fixed", False),
        )
        self.assertEqual(
            (cfg.random_draws, cfg.seed, cfg.overlap, cfg.data_end_exit),
            (200, 20261007, "skip", "last_close"),
        )
        specs = e5.run_specs(PROTO, "IDX")
        self.assertEqual(
            [s["id"] for s in specs], ["primary", "fill_A", "one_tick_cost", "controls_v2"]
        )
        tick = e5.harness_config(
            PROTO, "IDX", "E5_CAND_IDX_A", "2020-10-15", "2022-12-30", specs[2]["overrides"]
        )
        self.assertTrue(tick.tick_cost)
        v2 = e5.harness_config(
            PROTO, "IDX", "E5_CAND_IDX_A", "2020-10-15", "2022-12-30", specs[3]["overrides"]
        )
        self.assertEqual(v2.controls_version, "v2")
        self.assertFalse(specs[3]["judged"])
        us = e5.harness_config(PROTO, "US", "E5_CAND_US_A", "2020-03-30", "2022-12-31")
        self.assertEqual(
            (us.fill_model, us.units, us.quarantine, us.notional, us.ca_mode),
            ("B", "as_traded", "none", 5000.0, "adjusted"),
        )
        stress = e5.harness_config(
            PROTO,
            "US",
            "E5_CAND_US_A",
            "2020-03-30",
            "2022-12-31",
            e5.run_specs(PROTO, "US")[3]["overrides"],
        )
        self.assertAlmostEqual(stress.fee_buy, 0.015)
        self.assertAlmostEqual(stress.fee_sell, 0.0150278)
        cr = e5.harness_config(PROTO, "CRYPTO", "E5_CAND_CRYPTO_B", "2020-03-30", "2022-12-31")
        self.assertEqual(
            (cr.fill_model, cr.jump_ratio, cr.fee_buy, cr.market), ("A", 10.0, 0.001, "CRYPTO")
        )
        close = e5.harness_config(
            PROTO,
            "CRYPTO",
            "E5_CAND_CRYPTO_B",
            "2020-03-30",
            "2022-12-31",
            e5.run_specs(PROTO, "CRYPTO")[2]["overrides"],
        )
        self.assertEqual((close.market, close.fill_model), ("CRYPTO_CLOSE", "A"))
        with self.assertRaises(ValueError):
            e5.market_dir("CRYPTO_CLOSE")  # never a top-level market

    def test_assert_within_validation_refuses_any_end_past_the_validation_end(self):
        for mk, v_end in (
            ("IDX", "2023-12-29"),
            ("US", "2023-12-31"),
            ("CRYPTO", "2023-12-31"),
            ("CRYPTO_CLOSE", "2023-12-31"),
        ):
            e5.assert_within_validation(PROTO, mk, v_end)
            e5.assert_within_validation(PROTO, mk, "2022-12-30")
            for bad in ("2024-01-01", "2024-01-02", "2025-02-21", "2026-10-01"):
                with self.assertRaises(HoldoutSealed):
                    e5.assert_within_validation(PROTO, mk, bad)
        with self.assertRaises(HoldoutSealed):
            e5.assert_within_validation(
                PROTO, "IDX", "2023-12-30"
            )  # past the IDX validation end, before 2024
        with self.assertRaises(HoldoutSealed):
            e5.harness_config(PROTO, "IDX", "E5_CAND_IDX_A", "2023-10-01", "2024-01-05")
        df, meta = e5_panel("IDX", n=3, start="2023-06-01", end="2023-12-29")
        with self.assertRaises(HoldoutSealed):
            e5.window_for(
                test_proto({"markets.IDX.periods.validation": ["2023-01-02", "2024-01-05"]}),
                "IDX",
                e5.sessions_of(df),
                "validation",
            )


# ---------------------------------------------------------------------------------------- study
class StudyLoads(unittest.TestCase):
    def test_study_loads_the_draft_protocol_for_each_market(self):
        """Guards against: e1.Study refusing the draft (periods / weak_signals / panel_format shape)."""
        warnings.simplefilter("ignore")
        for mk in e5.MARKETS:
            df, meta = e5_panel(mk, n=8, start="2020-03-02", end="2023-12-29")
            st = e5.build_study(test_proto(), mk, df, meta)
            self.assertEqual(st.protocol_id, "KOD-GLOBAL-E5-v1")
            self.assertEqual(st.protocol_sha, PROTO_SHA)
            self.assertEqual(st.panel_format, FORMATS[mk])
            self.assertEqual(st.pool_version, "v3")
            self.assertEqual(st.pool_units, PROTO["markets"][mk]["pool_units"])
            self.assertEqual(
                st.study_options()["pool_keys"],
                ["price_band", "liquidity", "volatility", "market_cap"],
            )
            self.assertIs(st.family, moonshot_e5)
            self.assertTrue(np.isnan(st.sig["ign"]).all())
            self.assertEqual(set(moonshot_e5.FEATURE_ORDER) <= set(st.base_feats), True)
            w = st.e5_window
            start = PROTO["markets"][mk]["periods"]["discovery"][0]
            self.assertEqual(w["lead_in_sessions"], 65)
            self.assertFalse(w["lead_in_short"])
            sessions = e5.sessions_of(df)
            first = int(np.searchsorted(sessions, np.datetime64(start, "D")))
            self.assertEqual(w["start"], str(sessions[first - 65]))
            self.assertEqual(str(st.dates[0]), w["start"])
            self.assertEqual(str(st.dates[65]), w["first_period_session"])
            self.assertLessEqual(
                str(st.dates[-1]), PROTO["markets"][mk]["periods"]["validation"][1]
            )
            with self.assertRaises(ValueError):
                e5.build_study(test_proto(), mk, df, {**meta, "format": "panel-v1"})

    def test_a_short_panel_clips_the_lead_in_and_records_it(self):
        df, meta = e5_panel("IDX", n=3, start="2021-01-04", end="2023-12-29")
        w = e5.window_for(test_proto(), "IDX", e5.sessions_of(df), "discovery")
        self.assertTrue(w["lead_in_short"])
        self.assertLess(w["lead_in_sessions"], 65)
        self.assertEqual(w["start"], "2021-01-04")


# ---------------------------------------------------------------------------------------- labels
def designed_study(market="CRYPTO", n_sessions=140):
    """Three names, flat at 100 with a designed path on row 0: +40% over t+1..t+5 after session 90 (U),
    -30% after 110 (D); row 1 carries a x25 unit reset at 120 (crypto)."""
    t, d, a = flat_market(
        n_tickers=3, n_sessions=n_sessions, price=100.0, volume=1e6, start="2020-07-01"
    )
    close = a["close"]
    close[0, 92] = 115.0
    close[0, 93:] = 140.0
    close[0, 112] = 80.0
    close[0, 113:] = 70.0
    close[1, 120:] = 2500.0
    for i in range(3):
        a["prev"][i, 1:] = close[i, :-1]
        a["high"][i] = np.maximum(close[i], a["prev"][i]) * 1.005
        a["low"][i] = np.minimum(close[i], a["prev"][i]) * 0.995
        a["value"][i] = close[i] * a["volume"][i]
    opens = a["prev"].copy()
    df = frame_from_arrays(t, d, a, opens=opens, idx=False)
    df["open"] = df["open"].astype(float)
    meta = {
        "sha256": f"synthetic-{market}",
        "panel": "synthetic",
        "source_boundary": str(d[-1]),
        "format": FORMATS[market],
    }
    proto = test_proto()
    proto["markets"][market]["periods"]["discovery"] = ["2020-07-01", str(d[-1])]
    proto["markets"][market]["periods"]["validation"] = [str(d[-1]), str(d[-1])]
    proto["periods"]["discovery"] = ["2020-07-01", str(d[-1])]
    proto["periods"]["validation"] = [str(d[-1]), str(d[-1])]
    path = Path(tempfile.mkdtemp(prefix="idxsig-e5-proto-")) / "protocol.json"
    path.write_text(json.dumps(proto) + "\n", encoding="utf-8")
    study = e1.Study(
        df,
        meta,
        protocol_path=path,
        profile=PROFILES[market],
        family_module=moonshot_e5,
        pool_version="v3",
        panel_format=FORMATS[market],
    )
    return study, proto, df, meta


class LabelTests(unittest.TestCase):
    def test_u_and_d_on_the_reference_chain(self):
        warnings.simplefilter("ignore")
        st, proto, _, _ = designed_study("CRYPTO")
        lab = e5.labels(st, proto, "CRYPTO")
        u = lab["U"]
        self.assertEqual(u[0, 90], 1.0)  # 140/100 within t+1..t+5
        self.assertEqual(u[0, 88], 1.0)  # 89..93 reaches 140
        self.assertEqual(u[0, 87], 0.0)  # 88..92 reaches 115 only
        self.assertEqual(u[0, 86], 0.0)
        self.assertEqual(u[2, 90], 0.0)
        d, info = e5.d_label(lab, "CRYPTO", np.isfinite(u), proto)
        self.assertEqual(info["rule"], "fixed")
        self.assertAlmostEqual(info["threshold_min_ratio_minus_1"], 1 / 1.30 - 1)
        self.assertEqual(d[0, 110], 1.0)  # 70/140 = 0.5 <= 0.769
        self.assertEqual(d[0, 108], 1.0)  # 109..113 contains 112: 80/140 = 0.571
        self.assertEqual(d[0, 106], 0.0)  # 107..111: flat at 140
        self.assertEqual(d[0, 100], 0.0)
        self.assertTrue(np.isnan(u[:, -1]).all())  # no forward session

    def test_u_matches_e1_study_qraw_where_labelled(self):
        warnings.simplefilter("ignore")
        st, proto, _, _ = designed_study("US")
        lab = e5.labels(st, proto, "US")
        ok = lab["labelled"]
        np.testing.assert_array_equal(lab["U"][ok] == 1.0, st.qraw[0.30][ok])

    def test_idx_rate_matched_q_gives_equal_rates(self):
        warnings.simplefilter("ignore")
        df, meta = e5_panel("IDX", n=20, start="2020-10-01", end="2023-12-29", seed=7)
        proto = test_proto()
        st = e5.build_study(proto, "IDX", df, meta)
        lab = e5.labels(st, proto, "IDX")
        ev = e5.evaluable_mask(st, proto, "IDX", "discovery", lab)
        d, info = e5.d_label(lab, "IDX", ev, proto)
        self.assertEqual(info["rule"], "rate-matched")
        n = int(ev.sum())
        k = int(np.nansum(lab["U"][ev]))
        self.assertGreater(k, 0)
        self.assertEqual(
            int(np.nansum(d[ev])),
            int((lab["r5min"][ev] <= info["threshold_min_ratio_minus_1"]).sum()),
        )
        self.assertGreaterEqual(int(np.nansum(d[ev])), k)  # P(D) = P(U) up to ties
        self.assertLessEqual(
            int(np.nansum(d[ev])) - k,
            int((lab["r5min"][ev] == info["threshold_min_ratio_minus_1"]).sum()),
        )
        self.assertAlmostEqual(info["P_U"], k / n)
        self.assertEqual(info["evaluable_ticker_days"], n)

    def test_crypto_unit_reset_censors_labels_and_the_plan_window(self):
        warnings.simplefilter("ignore")
        st, proto, _, _ = designed_study("CRYPTO")
        lab = e5.labels(st, proto, "CRYPTO")
        self.assertEqual(
            lab["unit_resets"], [{"ticker": "T001", "date": str(st.dates[120]), "ratio": 25.0}]
        )
        self.assertTrue(np.isnan(lab["U"][1, 115:121]).all())  # r-5..r
        self.assertFalse(np.isnan(lab["U"][1, 114]))
        self.assertFalse(np.isnan(lab["U"][1, 121]))
        self.assertTrue(lab["censor_plan"][1, 114:120].all())  # t+1..t+6 contains 120
        self.assertFalse(lab["censor_plan"][1, 113])
        self.assertFalse(lab["censor_plan"][1, 120])
        self.assertFalse(lab["censor_plan"][0].any())
        off = e5.labels(
            st, proto, "US"
        )  # the censoring applies to the markets the protocol names only
        self.assertEqual(off["unit_resets"], [])
        self.assertFalse(np.isnan(off["U"][1, 118]))


# ---------------------------------------------------------------------------------------- learner
class LearnerTests(unittest.TestCase):
    def test_irls_recovers_a_planted_direction_and_is_reproducible(self):
        rng = np.random.default_rng(1)
        n = 4000
        X = rng.random((n, 41))
        y = (X[:, 3] - X[:, 7] + 0.1 * rng.standard_normal(n) > 0).astype(
            float
        )  # separable-ish on two columns
        w = np.ones(n)
        fit = e5.fit_logistic(X, y, w, lam=1e-3 * n, iterations=25)
        self.assertEqual(len(fit["coef"]), 41)
        self.assertGreater(fit["coef"][3], 1.0)
        self.assertLess(fit["coef"][7], -1.0)
        self.assertTrue(
            all(
                abs(c) < abs(fit["coef"][3]) / 3
                for i, c in enumerate(fit["coef"])
                if i not in (3, 7)
            )
        )
        self.assertTrue(np.isfinite(fit["deviance"]))
        again = e5.fit_logistic(X, y, w, lam=1e-3 * n, iterations=25)
        self.assertEqual(fit, again)
        X[:, 10] = 1.0  # a constant column collinear with the intercept: finite under the ridge
        fit_c = e5.fit_logistic(X, y, w, lam=1e-3 * n, iterations=25)
        self.assertTrue(np.isfinite(fit_c["coef"]).all())
        with self.assertRaises(ValueError):
            e5.fit_logistic(X, np.ones(n), w, 1.0, 5)

    def test_fit_label_subsamples_negatives_under_the_seed(self):
        rng = np.random.default_rng(2)
        shape = (10, 300)
        f = {k: rng.random(shape) for k in moonshot_e5.FEATURE_ORDER}
        n_idx, d_idx = np.nonzero(np.ones(shape, dtype=bool))
        y = (f["ret1_r"][n_idx, d_idx] > 0.97).astype(float)
        learner = dict(PROTO["learner"])
        a = e5.fit_label(f, n_idx, d_idx, y, learner, "U")
        b = e5.fit_label(f, n_idx, d_idx, y, learner, "U")
        self.assertEqual(a, b)
        self.assertEqual(a["n_positives"], int(y.sum()))
        self.assertEqual(a["n_negatives_sampled"], int(np.floor(0.10 * (len(y) - y.sum()))))
        self.assertEqual(a["n_rows_used"], a["n_positives"] + a["n_negatives_sampled"])
        self.assertAlmostEqual(a["lambda"], 1e-3 * a["n_rows_used"])
        self.assertEqual(a["negative_weight"], 10.0)
        self.assertGreater(a["coef"][0], 0)  # ret1_r drives the label
        other = e5.fit_label(f, n_idx, d_idx, y, {**learner, "seed": 1}, "U")
        self.assertNotEqual(a["coef"], other["coef"])
        zero = {**f, "gap_r": np.zeros(shape)}
        self.assertEqual(
            e5.fit_label(zero, n_idx, d_idx, y, learner, "U")["coef"][
                moonshot_e5.FEATURE_ORDER.index("gap_r")
            ],
            0.0,
        )
        self.assertEqual(
            e5.constant_columns(zero, np.ones(shape, dtype=bool))["gap_r"],
            {"constant": True, "value": 0.0},
        )
        self.assertFalse(
            e5.constant_columns(zero, np.ones(shape, dtype=bool))["ret1_r"]["constant"]
        )


# ------------------------------------------------------------------------------- thresholds and flags
class ThresholdFlagTests(unittest.TestCase):
    def test_threshold_is_the_discovery_percentile_and_flags_are_debounced(self):
        rng = np.random.default_rng(3)
        score = rng.standard_normal((20, 200))
        ev = np.zeros((20, 200), dtype=bool)
        ev[:, 80:150] = True
        thr = e5.threshold(score, ev, 99.5)
        self.assertEqual(thr, float(np.percentile(score[ev], 99.5)))
        t, d, a = flat_market(n_tickers=20, n_sessions=200)
        m = Market.build(
            t, d, a["close"], a["prev"], a["high"], a["low"], a["volume"], a["value"], a["present"]
        )
        flags = e5.arm_flags(score, thr, m)
        expect = moonshot_e5.flags(score, thr) & m.tradeable
        expect[:, :WF] = False
        np.testing.assert_array_equal(flags, expect)
        self.assertFalse(flags[:, :WF].any())
        with self.assertRaises(ValueError):
            e5.threshold(score, np.zeros_like(ev), 99.5)

    def test_stage1_flags_equal_the_harness_signals_of_the_candidate_rule(self):
        """Guards against: the Stage-1 flag set differing from what the harness would trade in Stage 2."""
        warnings.simplefilter("ignore")
        found = Discovered.get("IDX")
        model, proto = found["model"], found["proto"]
        st = e5.build_study(proto, "IDX", found["df"], found["meta"])
        scores = e5.arm_scores(st.base_feats, model)
        rule = rules.registry()["E5_CAND_IDX_A"]
        with e5.literals_from(model, "IDX"):
            sig = rule.compute(st.m)
        flags = e5.arm_flags(scores["A"], model["threshold_A"], st.m)
        np.testing.assert_array_equal(np.nan_to_num(sig, nan=0.0) == 1.0, flags)
        self.assertTrue(np.isnan(sig[:, :WF]).all())
        self.assertGreater(int(flags.sum()), 0)
        self.assertIsNone(dict(moonshot_e5.COEF_U)["IDX"])  # restored after the block
        self.assertEqual(
            np.nan_to_num(e5.arm_scores(st.base_feats, model)["B"], nan=0.0).shape, st.m.shape
        )


# --------------------------------------------------------------------------------------- paired stage 1
def toy_block(flags=300, mean_excess=0.01, p=0.001, clusters=50, by_year=None):
    return {
        "flags": flags,
        "plan_window": {
            "paired": {
                "n": flags,
                "n_clusters": clusters,
                "mean_excess": mean_excess,
                "p_one_sided": p,
            }
        },
        "by_year": by_year
        or {
            "2021": {"flags": 150, "mean_excess": 0.02},
            "2022": {"flags": 150, "mean_excess": 0.005},
        },
    }


class PairedStage1Tests(unittest.TestCase):
    def test_gate_rules_and_refusal_below_two_clusters(self):
        years = [2021, 2022]
        self.assertEqual(
            e5.stage1_gate(toy_block(), PROTO, years),
            {"judged": True, "passed": True, "reasons": []},
        )
        g = e5.stage1_gate(toy_block(clusters=1), PROTO, years)
        self.assertFalse(g["judged"])
        self.assertFalse(g["passed"])
        self.assertIn("not judged", g["reasons"][0])
        self.assertTrue(
            any(
                "flags 199" in r
                for r in e5.stage1_gate(toy_block(flags=199), PROTO, years)["reasons"]
            )
        )
        self.assertTrue(
            any(
                "not positive" in r
                for r in e5.stage1_gate(toy_block(mean_excess=-0.001), PROTO, years)["reasons"]
            )
        )
        self.assertTrue(
            any("p 0.03" in r for r in e5.stage1_gate(toy_block(p=0.03), PROTO, years)["reasons"])
        )
        bad_year = toy_block(
            by_year={
                "2021": {"flags": 250, "mean_excess": 0.02},
                "2022": {"flags": 50, "mean_excess": -0.01},
            }
        )
        self.assertTrue(any("2022" in r for r in e5.stage1_gate(bad_year, PROTO, years)["reasons"]))
        few = toy_block(
            by_year={
                "2021": {"flags": 251, "mean_excess": 0.02},
                "2022": {"flags": 49, "mean_excess": -0.01},
            }
        )
        self.assertTrue(
            e5.stage1_gate(few, PROTO, years)["passed"]
        )  # a year under 50 flags is not judged

    def test_paired_statistic_is_reproducible_under_the_seed(self):
        warnings.simplefilter("ignore")
        found = Discovered.get("IDX")
        a = found["stage1"]["arms"]["A"]["plan_window"]["paired"]
        again = json.loads(
            (Discovered.get("IDX")["out"] / "stage1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(a, again["arms"]["A"]["plan_window"]["paired"])
        self.assertEqual((a["resamples"], a["seed"], a["cluster"]), (200, 20261015, "signal_date"))
        dates = np.array(["2021-01-04", "2021-01-04", "2021-01-05", "2021-01-06"])
        rf = np.array([0.1, 0.2, 0.3, 0.4])
        rc = np.array([[0.0, 0.1, 0.0, np.nan], [0.0, 0.1, 0.2, np.nan]])
        frame = e5.paired_frame(dates, rf, rc, "signal_date")
        np.testing.assert_allclose(
            frame["matched_mean_net_return"].to_numpy(), [0.0, 0.1, 0.1, np.nan]
        )
        r1 = paired_excess(frame, resamples=500, seed=20261015)
        r2 = paired_excess(frame, resamples=500, seed=20261015)
        self.assertEqual(r1, r2)
        self.assertEqual((r1["n"], r1["n_clusters"]), (3, 2))
        self.assertAlmostEqual(r1["mean_excess"], (0.1 + 0.1 + 0.2) / 3)

    def test_ratio_bootstrap_and_a1_gate(self):
        num = np.array([1.0, 0.0, 1.0, 1.0])
        den = np.array([0.5, 0.5, 0.25, 0.25])
        r = e5.ratio_bootstrap(num, den, np.array(["a", "a", "b", "c"]), 300, 1)
        self.assertAlmostEqual(r["ratio"], 3 / 1.5)
        self.assertEqual(r["n_clusters"], 3)
        self.assertEqual(r, e5.ratio_bootstrap(num, den, np.array(["a", "a", "b", "c"]), 300, 1))
        block = {
            "E30": {
                "lift_vs_matched": 2.5,
                "p_one_sided_vs_matched": 0.01,
                "lift_vs_matched_ci95": [1.2, 4.0],
            }
        }
        self.assertEqual(
            e5.a1_gate(block, PROTO), {"passed": True, "reasons": [], "lift_ci95_excludes_1": True}
        )
        weak = {
            "E30": {
                "lift_vs_matched": 1.5,
                "p_one_sided_vs_matched": 0.2,
                "lift_vs_matched_ci95": [0.8, 2.5],
            }
        }
        g = e5.a1_gate(weak, PROTO)
        self.assertFalse(g["passed"])
        self.assertEqual(len(g["reasons"]), 2)
        self.assertFalse(g["lift_ci95_excludes_1"])


# ----------------------------------------------------------------------------------------- plan window
EDGE_RULE = """
def compute(m):
    out = np.zeros(m.shape)
    out[0, 10:11] = 1.0
    out[1, 12:13] = 1.0
    out[2, 20:21] = 1.0
    return np.where(m.tradeable, out, np.nan)
"""


class PlanWindowTests(unittest.TestCase):
    def _market(self, idx=True):
        t, d, a = flat_market(
            n_tickers=3,
            n_sessions=40,
            price=1000.0 if idx else 10.0,
            volume=5e6,
            start="2022-03-01",
        )
        rng = np.random.default_rng(5)
        for i in range(3):
            path = a["close"][i, 0] * np.cumprod(1 + rng.uniform(-0.03, 0.03, 40))
            if idx:
                path = floor_tick(path)
            a["close"][i] = path
            a["prev"][i, 1:] = path[:-1]
            a["high"][i] = np.maximum(path, a["prev"][i]) * 1.01
            a["low"][i] = np.minimum(path, a["prev"][i]) * 0.99
            a["value"][i] = path * a["volume"][i]
        opens = None if idx else a["prev"].copy()
        df = frame_from_arrays(t, d, a, opens=opens, idx=idx)
        if idx:
            for c in (
                "previous",
                "high",
                "low",
                "close",
                "volume",
                "value",
                "frequency",
                "listed_shares",
                "tradable_shares",
            ):
                df[c] = df[c].round().astype("Int64")
        else:
            df["open"] = df["open"].astype(float)
        meta = {
            "sha256": "synthetic",
            "panel": "synthetic",
            "source_boundary": str(d[-1]),
            "default_start": str(d[0]),
            "quality_tiers": [],
            "known_limitations": [],
            "survivorship": "synthetic",
        }
        return df, meta

    def test_plan_window_return_equals_the_harness_gross_return(self):
        """Fill-independent synthetic case: no lots, locks or costs bind, so the harness's gross return is
        exactly the reference-chain plan-window return (close entry on IDX, open entry on US)."""
        rule = module_rule("PWIN", EDGE_RULE)
        for market, idx, entry in (("IDX", True, "close"), ("US", False, "open")):
            df, meta = self._market(idx)
            m = Market.from_panel(df, price_limits=idx)
            r_plan = e5.plan_window_return(m, entry, 5)
            with with_rule(rule):
                if idx:
                    out = run(
                        RunConfig("PWIN", market="IDX", random_draws=2, fill_model="A"),
                        df,
                        meta,
                        ca_registry=synthetic_registry(df, meta),
                    )
                else:
                    out = run(
                        RunConfig(
                            "PWIN",
                            market="US",
                            ca_mode="adjusted",
                            random_draws=2,
                            fill_model="A",
                            notional=5000.0,
                            fee_buy=0.0,
                            fee_sell=0.0,
                        ),
                        df,
                        meta,
                    )
            trades = out["trades"]
            self.assertEqual(sorted(trades["status"].unique()), ["EXITED"])
            tick = pd.Index(m.tickers)
            for row in trades.itertuples(index=False):
                n, t = (
                    tick.get_loc(row.ticker),
                    int(np.searchsorted(m.dates, np.datetime64(row.signal_date))),
                )
                self.assertAlmostEqual(
                    float(row.gross_return),
                    float(r_plan[n, t]),
                    places=12,
                    msg=(market, row.ticker),
                )
            self.assertTrue(np.isnan(r_plan[:, 34:]).all())  # t + 6 past the window
            self.assertFalse(np.isnan(r_plan[:, :34]).any())


# ------------------------------------------------------------------------------------------- stage 2
def toy_row(**kw):
    base = {
        "scored": 300,
        "avg_net_return": 0.02,
        "p_one_sided_vs_matched": 0.01,
        "matched_random_avg_net_return": 0.0,
        "scored_2021": 150,
        "avg_net_return_2021": 0.03,
        "scored_2022": 150,
        "avg_net_return_2022": 0.01,
        "paired_net_n_clusters": 40,
        "paired_net_mean_excess": 0.02,
        "paired_net_p_one_sided": 0.001,
        "rule_minus_matched": 0.02,
        "run": "primary",
        "judged": True,
        "exit_subset_scored": 250,
        "exit_subset_avg_net_return": 0.015,
        "exit_subset_p_one_sided_vs_matched": 0.002,
        "exit_subset_paired_net_n_clusters": 35,
        "exit_subset_paired_net_mean_excess": 0.015,
        "exit_subset_scored_2021": 120,
        "exit_subset_avg_net_return_2021": 0.02,
        "exit_subset_scored_2022": 130,
        "exit_subset_avg_net_return_2022": 0.01,
    }
    base.update(kw)
    return base


def toy_sens(run="fill_A", diff=0.01, judged=True):
    return {"run": run, "judged": judged, "rule_minus_matched": diff}


class Stage2Tests(unittest.TestCase):
    def test_admissibility_composes_e3_paired_sensitivities_and_the_exit_subset(self):
        years = [2021, 2022]
        ok = e5.admissibility_stage2(toy_row(), [toy_sens(), toy_sens("tick", 0.001)], PROTO, years)
        self.assertEqual(ok, {"judged": True, "admissible": True, "reasons": []})
        self.assertEqual(e3.admissibility(toy_row(), PROTO, years), [])
        r = e5.admissibility_stage2(toy_row(scored=199), [toy_sens()], PROTO, years)
        self.assertTrue(any("scored 199" in x for x in r["reasons"]))
        r = e5.admissibility_stage2(
            toy_row(p_one_sided_vs_matched=0.06), [toy_sens()], PROTO, years
        )
        self.assertTrue(any("p vs matched" in x for x in r["reasons"]))  # e3's harness p, verbatim
        r = e5.admissibility_stage2(
            toy_row(paired_net_p_one_sided=0.03), [toy_sens()], PROTO, years
        )
        self.assertTrue(any("paired net p 0.03" in x for x in r["reasons"]))
        r = e5.admissibility_stage2(toy_row(), [toy_sens(diff=-0.001)], PROTO, years)
        self.assertTrue(any("sensitivity fill_A" in x for x in r["reasons"]))
        self.assertFalse(
            e5.admissibility_stage2(
                toy_row(), [toy_sens("controls_v2", -0.5, judged=False)], PROTO, years
            )["reasons"]
        )
        r = e5.admissibility_stage2(
            toy_row(exit_subset_avg_net_return=-0.01), [toy_sens()], PROTO, years
        )
        self.assertTrue(any("exit-capacity subset: average net" in x for x in r["reasons"]))
        r = e5.admissibility_stage2(toy_row(exit_subset_scored=150), [toy_sens()], PROTO, years)
        self.assertTrue(any("subset: scored 150" in x for x in r["reasons"]))
        r = e5.admissibility_stage2(
            toy_row(exit_subset_avg_net_return_2022=-0.01), [toy_sens()], PROTO, years
        )
        self.assertTrue(any("subset: average net return in 2022" in x for x in r["reasons"]))
        r = e5.admissibility_stage2(toy_row(paired_net_n_clusters=1), [toy_sens()], PROTO, years)
        self.assertFalse(r["judged"])
        self.assertFalse(r["admissible"])
        r = e5.admissibility_stage2(
            {k: v for k, v in toy_row().items() if not k.startswith("exit_subset_")},
            [],
            PROTO,
            years,
        )
        self.assertIn("exit-capacity subset missing", r["reasons"])

    def test_select_arm_prefers_the_primary_arm(self):
        adm = {"A": {"admissible": True}, "B": {"admissible": True}}
        rows = {"A": {"paired_net_mean_excess": 0.01}, "B": {"paired_net_mean_excess": 0.05}}
        self.assertEqual(e5.select_arm(adm, rows, "IDX", PROTO), "A")
        self.assertEqual(e5.select_arm(adm, rows, "CRYPTO", PROTO), "B")
        self.assertEqual(
            e5.select_arm(adm, rows, "US", PROTO), "B"
        )  # no primary: the larger excess
        self.assertEqual(
            e5.select_arm(
                {"A": {"admissible": False}, "B": {"admissible": True}}, rows, "IDX", PROTO
            ),
            "B",
        )
        self.assertIsNone(e5.select_arm({"A": {"admissible": False}}, rows, "IDX", PROTO))

    def test_harness_row_carries_the_paired_statistic_subset_and_bound(self):
        warnings.simplefilter("ignore")
        found = Discovered.get("CRYPTO")
        df, meta, proto, model = found["df"], found["meta"], found["proto"], found["model"]
        w = found["summary"]["window"]
        cfg = e5.harness_config(proto, "CRYPTO", "E5_CAND_CRYPTO_A", w["start"], w["end"])
        self.assertEqual((cfg.lookahead_cuts, cfg.random_draws, cfg.jump_ratio), (2, 8, 10.0))
        with e5.literals_from(model, "CRYPTO"):
            out = run(cfg, df, meta)
        self.assertEqual(out["summary"]["lookahead_check"]["mode"], "sampled")
        self.assertEqual(len(out["summary"]["lookahead_check"]["truncated_after"]), 2)
        m = Market.from_panel(df, price_limits=False).window(w["start"], w["end"])
        plan = {k: proto["plans"]["CRYPTO"]["primary"][k] for k in e5.PLAN_KEYS}
        row = e5.harness_row(
            out["summary"],
            out["trades"],
            "A",
            {"id": "primary", "judged": True},
            plan,
            [2020, 2021, 2022],
            proto,
            e5.volume_series(df),
            e5.u_lookup(m, 5, 1.30),
            "deadbeef",
        )
        self.assertEqual(
            (row["arm"], row["run"], row["plan_id"], row["literals_sha256"]),
            ("A", "primary", "A|fixed1|fixed|h5", "deadbeef"),
        )
        self.assertEqual(row["lookahead_mode"], "sampled")
        for k in (
            "paired_net_n",
            "paired_net_n_clusters",
            "paired_net_mean_excess",
            "paired_net_p_one_sided",
            "exit_subset_scored",
            "exit_subset_avg_net_return",
            "exit_subset_p_one_sided_vs_matched",
            "breakeven_p_star",
            "rule_minus_matched",
            "avg_gross_return",
            "exit_participation_median",
        ):
            self.assertIn(k, row)
        self.assertEqual(row["paired_net_n"], paired_excess(out["trades"], resamples=200)["n"])
        self.assertLessEqual(row["exit_subset_scored"], row["scored"])
        part = e5.exit_participation(out["trades"], e5.volume_series(df))
        scored = out["trades"]["status"].isin(e5.SCORED_STATUS).to_numpy()
        self.assertTrue(np.isfinite(part[scored]).all())
        self.assertTrue(np.isnan(part[~scored]).all())
        self.assertGreater(row["scored"], 0)
        # the exit-capacity subset re-states the row's own trades
        keep = (
            np.nan_to_num(part, nan=np.inf)
            <= proto["stages"]["2_execution"]["exit_participation_max"]
        )
        self.assertEqual(row["exit_subset_scored"], int((keep & scored).sum()))

    def test_reproduce_status_accepts_only_the_fourth_decimal_matched_deviation(self):
        dev = PROTO["stages"]["0_reproduce"]["accepted_deviation"]
        fields = PROTO["stages"]["0_reproduce"]["rule_side_fields"]
        want = {
            "signals": 1109,
            "scored": 251,
            "avg_net_return": -0.036355648777628986,
            "status_counts": {"EXITED": 251, "SKIP_LOT": 3},
            "matched_random_avg_net_return": -0.00440442963495353,
        }
        self.assertEqual(
            e5.reproduce_status(want, dict(want), fields, dev), (True, "IDENTICAL", "REPRODUCED")
        )
        near = {**want, "matched_random_avg_net_return": -0.004400107560502186}  # the E3 record
        self.assertEqual(
            e5.reproduce_status(want, near, fields, dev),
            (True, "DEVIATES_WITHIN_ACCEPTED_TOLERANCE", "REPRODUCED"),
        )
        far = {**want, "matched_random_avg_net_return": -0.0144}
        self.assertEqual(
            e5.reproduce_status(want, far, fields, dev), (True, "DEVIATES", "DEVIATES")
        )
        rule = {**want, "scored": 250}
        self.assertEqual(e5.reproduce_status(want, rule, fields, dev)[2], "DEVIATES")
        self.assertEqual(
            e5.reproduce_status(want, {**want, "avg_net_return": -0.0363556}, fields, dev)[2],
            "DEVIATES",
        )
        self.assertEqual(
            e5.reproduce_status(want, {**want, "status_counts": {"EXITED": 251}}, fields, dev)[2],
            "DEVIATES",
        )


# ---------------------------------------------------------------------------------------- freeze
def synthetic_model(market="IDX", seed=9):
    rng = np.random.default_rng(seed)
    return {
        "market": market,
        "coef_U": [float(x) for x in rng.standard_normal(41)],
        "intercept_U": -5.25,
        "coef_D": [float(x) for x in rng.standard_normal(41)],
        "intercept_D": -4.5,
        "threshold_A": 1.2345,
        "threshold_B": -0.5,
    }


class FreezeTests(unittest.TestCase):
    def test_freeze_writes_literals_once_and_refuses_twice(self):
        source = e5.MODULE_PATH.read_text(encoding="utf-8")
        model = synthetic_model("IDX")
        new = e5.freeze_source(source, model, "IDX", "A")
        lits = e5.module_literals(new)
        self.assertEqual(dict(lits["COEF_U"]["value"])["IDX"], tuple(model["coef_U"]))
        self.assertEqual(dict(lits["COEF_D"]["value"])["IDX"], tuple(model["coef_D"]))
        self.assertEqual(dict(lits["INTERCEPT_U"]["value"])["IDX"], -5.25)
        self.assertEqual(dict(lits["THRESHOLD_A"]["value"])["IDX"], 1.2345)
        self.assertEqual(dict(lits["THRESHOLD_B"]["value"])["IDX"], -0.5)
        self.assertIsNone(dict(lits["COEF_U"]["value"])["US"])
        self.assertEqual(lits["SELECTED"]["value"], (("IDX", "A"),))
        frozen = e5.load_module_from_text(new)
        self.assertEqual(e5.check_frozen(model, "IDX", frozen), [])
        self.assertEqual(audit_module(frozen), [])
        self.assertTrue(frozen.frozen("IDX_A") and frozen.frozen("IDX_B"))
        self.assertFalse(frozen.frozen("US_A"))
        self.assertEqual(
            {r.rule_id for r in frozen.rules()} - {r.rule_id for r in moonshot_e5.rules()},
            {"MOONSHOT_E5_IDX_D1"},
        )
        with self.assertRaises(RuntimeError):
            e5.freeze_source(new, model, "IDX", "A")  # literals already set
        us = e5.freeze_source(
            new, synthetic_model("US"), "US", None
        )  # a second market, no SELECTED entry
        self.assertEqual(e5.module_literals(us)["SELECTED"]["value"], (("IDX", "A"),))
        self.assertEqual(
            e5.check_frozen(synthetic_model("US"), "US", e5.load_module_from_text(us)), []
        )
        self.assertTrue(
            e5.check_frozen(synthetic_model("US", seed=1), "US", e5.load_module_from_text(us))
        )
        self.assertTrue(
            e5.check_frozen(model, "IDX")
        )  # the real module is unfrozen: validation refuses
        self.assertEqual(e5.check_frozen(model, "IDX")[0], "COEF_U[IDX] is None")

    def test_run_freeze_on_a_module_copy(self):
        tmp = Path(tempfile.mkdtemp(prefix="idxsig-e5-freeze-"))
        module_path = tmp / "moonshot_e5_copy.py"
        module_path.write_text(e5.MODULE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        disc = tmp / "CRYPTO" / "discovery"
        disc.mkdir(parents=True)
        model = synthetic_model("CRYPTO")
        e3.write_json(disc / "model.json", model)
        e3.write_json(disc / "gates.json", {"market": "CRYPTO", "selected_arm": "B"})
        out = tmp / "CRYPTO" / "freeze"
        result = e5.run_freeze(
            out, PROTO, PROTO_SHA, "CRYPTO", module_path=module_path, log=lambda *_: None
        )
        self.assertTrue((out / "result.json").exists())
        self.assertEqual(result["selected_arm"], "B")
        frozen = e5.load_module_from(module_path)
        self.assertEqual(e5.check_frozen(model, "CRYPTO", frozen), [])
        self.assertEqual(frozen.SELECTED, (("CRYPTO", "B"),))
        with self.assertRaises(RuntimeError):
            e5.run_freeze(
                tmp / "CRYPTO" / "freeze2",
                PROTO,
                PROTO_SHA,
                "CRYPTO",
                module_path=module_path,
                log=lambda *_: None,
            )
        self.assertFalse(
            (tmp / "CRYPTO" / "freeze2").exists()
        )  # refused before anything was written
        with self.assertRaises(RuntimeError):
            e5.run_freeze(
                tmp / "IDX" / "freeze",
                PROTO,
                PROTO_SHA,
                "IDX",
                module_path=module_path,
                discovery_dir=disc,
                log=lambda *_: None,
            )  # another market's discovery
        self.assertIsNone(moonshot_e5.SELECTED)  # the real module was never touched

    def test_validation_refuses_when_literals_differ_from_model_json(self):
        warnings.simplefilter("ignore")
        found = Discovered.get("IDX")
        out = found["out"].parent / "validation"
        with self.assertRaises(RuntimeError) as ctx:
            e5.run_validation(
                found["df"],
                found["meta"],
                found["registry"],
                out,
                found["proto"],
                "sha",
                "IDX",
                log=lambda *_: None,
            )
        self.assertIn("not discovery/model.json", str(ctx.exception))
        self.assertFalse(out.exists())
        toy = {
            "scored": 120,
            "avg_net_return": 0.01,
            "paired_net_n_clusters": 30,
            "paired_net_mean_excess": 0.01,
            "paired_net_p_one_sided": 0.01,
            "p_one_sided_vs_matched": 0.02,
        }
        det = {"precision_lo95": 0.05, "base_rate": 0.02}
        v = e5.validation_pass(toy, [toy_sens(diff=0.01)], det, PROTO, "IDX")
        self.assertEqual((v["passed"], v["claim_level"]), (True, "PROVISIONAL"))
        self.assertFalse(
            e5.validation_pass(toy, [toy_sens(diff=0.01)], det, PROTO, "US")["passed"]
        )  # US needs 200
        self.assertFalse(
            e5.validation_pass(toy, [toy_sens(diff=-0.01)], det, PROTO, "IDX")["passed"]
        )
        self.assertFalse(
            e5.validation_pass(toy, [], {"precision_lo95": 0.01, "base_rate": 0.02}, PROTO, "IDX")[
                "passed"
            ]
        )
        self.assertFalse(
            e5.validation_pass({**toy, "paired_net_n_clusters": 1}, [], det, PROTO, "IDX")["judged"]
        )

    def test_validation_targets_name_the_admissible_arms_and_the_gated_a1(self):
        adm, no = {"admissible": True}, {"admissible": False}
        self.assertEqual(
            e5.validation_targets({"selected_arm": "A", "stage2": {"A": adm, "B": adm}}, "IDX"),
            [("A", "MOONSHOT_E5_IDX_D1"), ("B", "E5_CAND_IDX_B")],
        )
        self.assertEqual(
            e5.validation_targets(
                {"selected_arm": "B", "stage2": {"A": no, "B": adm, "A1_CREEP_QUIET_NR": adm}},
                "CRYPTO",
            ),
            [("B", "MOONSHOT_E5_CRYPTO_D1"), ("A1_CREEP_QUIET_NR", "E5_CAND_A1_CREEP_QUIET_NR")],
        )
        self.assertEqual(
            e5.validation_targets(
                {"selected_arm": None, "stage2": {"A1_CREEP_QUIET_NR": adm}}, "US"
            ),
            [("A1_CREEP_QUIET_NR", "E5_CAND_A1_CREEP_QUIET_NR")],
        )
        self.assertEqual(
            e5.validation_targets({"selected_arm": None, "stage2": {"A": no}}, "US"), []
        )
        self.assertEqual(e5.validation_targets({"selected_arm": None, "stage2": {}}, "US"), [])
        found = Discovered.get("IDX")  # an unfrozen module refuses before the targets matter
        gates = {"market": "IDX", "selected_arm": None, "stage2": {}}
        tmp = Path(tempfile.mkdtemp(prefix="idxsig-e5-")) / "IDX"
        (tmp / "discovery").mkdir(parents=True)
        e3.write_json(tmp / "discovery" / "model.json", found["model"])
        e3.write_json(tmp / "discovery" / "gates.json", gates)
        with self.assertRaises(RuntimeError):
            e5.run_validation(
                found["df"],
                found["meta"],
                found["registry"],
                tmp / "validation",
                found["proto"],
                "sha",
                "IDX",
                log=lambda *_: None,
            )


# ------------------------------------------------------------------------------------ window invariance
class WindowInvariance(unittest.TestCase):
    def test_flags_at_a_session_do_not_depend_on_where_the_window_starts(self):
        """The module's own helpers, scored with a discovery model: the window moved by k sessions carries
        the same flags from its lead-in on (no name lists inside the window, so age is censored alike)."""
        warnings.simplefilter("ignore")
        found = Discovered.get("CRYPTO")
        model = found["model"]
        df, meta = found["df"], found["meta"]
        m = Market.from_panel(df, price_limits=False).window("2021-03-01", "2022-06-30")
        f_full = moonshot_e5.features(*[getattr(m, a) for a in moonshot_e5.FEATURE_ARGS])
        s_full = e5.arm_scores(f_full, model)
        for k in (1, 7, 20):
            part = m.slice(k, m.shape[1])
            f_part = moonshot_e5.features(*[getattr(part, a) for a in moonshot_e5.FEATURE_ARGS])
            s_part = e5.arm_scores(f_part, model)
            for arm in e5.ARMS:
                np.testing.assert_allclose(
                    s_part[arm][:, W:], s_full[arm][:, k + W :], err_msg=f"{arm} k={k}"
                )
                full = e5.arm_flags(s_full[arm], model[f"threshold_{arm}"], m)
                moved = e5.arm_flags(s_part[arm], model[f"threshold_{arm}"], part)
                np.testing.assert_array_equal(
                    moved[:, WF:], full[:, k + WF :], err_msg=f"{arm} k={k}"
                )
                self.assertFalse(moved[:, :WF].any())
            full_det = e5.detector_flags(f_full, m)
            moved_det = e5.detector_flags(f_part, part)
            for name in e5.DETECTORS:
                np.testing.assert_array_equal(
                    moved_det[name][:, WF:], full_det[name][:, k + WF :], err_msg=name
                )


# ---------------------------------------------------------------------------------------- discovery
class DiscoveryEndToEnd(unittest.TestCase):
    def test_idx_discovery_writes_every_file_and_the_gates(self):
        warnings.simplefilter("ignore")
        found = Discovered.get("IDX")
        out, model, stage1, gates, summary = (
            found["out"],
            found["model"],
            found["stage1"],
            found["gates"],
            found["summary"],
        )
        for name in (
            "model.json",
            "thresholds.json",
            "stage1.json",
            "univariate.csv",
            "flags.csv",
            "plans.csv",
            "gates.json",
            "summary.json",
        ):
            self.assertTrue((out / name).exists(), name)
        self.assertEqual(len(model["coef_U"]), 41)
        self.assertEqual(len(model["coef_D"]), 41)
        self.assertEqual(model["feature_order"], list(moonshot_e5.FEATURE_ORDER))
        self.assertEqual(model["D_label"]["rule"], "rate-matched")
        self.assertIn(
            "gap_r", model["constant_column_names"]
        )  # no opens on IDX: gap ranks 0.5 everywhere
        self.assertIn("gap_r2", model["constant_column_names"])
        self.assertEqual(model["constant_columns"]["gap_r"], {"constant": True, "value": 0.5})
        self.assertEqual(model["fit_U"]["seed"], 20261015)
        self.assertEqual(model["fit_U"]["iterations"], 25)
        thr = json.loads((out / "thresholds.json").read_text(encoding="utf-8"))
        self.assertEqual(
            (thr["threshold_A"], thr["threshold_B"]), (model["threshold_A"], model["threshold_B"])
        )
        self.assertEqual(thr["percentile"], 99.5)
        for arm in e5.ARMS:
            block = stage1["arms"][arm]
            for key in (
                "flags",
                "E30",
                "D30",
                "directional_ratio",
                "plan_window",
                "by_year",
                "pre_move_split",
                "by_regime",
                "auc_U",
                "auc_D",
                "gate",
                "threshold",
                "distinct_names",
            ):
                self.assertIn(key, block, (arm, key))
            self.assertEqual(set(block["by_year"]), {"2021", "2022"})
            self.assertEqual(block["gate"], gates["stage1"][arm])
            self.assertEqual(block["E30"]["base_rate"], stage1["base_rates"]["E30"])
            if block["flags"]:
                self.assertTrue(0 <= block["E30"]["precision"] <= 1)
        self.assertEqual(stage1["arms"]["A"]["primary"], "P1")
        self.assertIsNone(stage1["arms"]["B"]["primary"])
        self.assertIn("variance_detection_check", stage1["arms"]["A"])
        self.assertEqual(set(stage1["detectors"]), set(e5.DETECTORS))
        self.assertIn("a1_gate", stage1["detectors"]["A1_CREEP_QUIET_NR"])
        self.assertEqual(stage1["unit_resets"], [])
        self.assertEqual(stage1["entry_price"], "close")
        uni = pd.read_csv(out / "univariate.csv")
        self.assertEqual(list(uni["feature"]), list(moonshot_e5.RANKED + moonshot_e5.BINARY))
        self.assertIn("auc", uni.columns)
        self.assertIn("lift_vs_matched", uni.columns)
        flags = pd.read_csv(out / "flags.csv")
        self.assertEqual(set(flags["arm"]) <= set(e5.ARMS) | set(e5.DETECTORS), True)
        self.assertEqual(len(flags[flags["arm"] == "A"]), stage1["arms"]["A"]["flags"])
        plans = pd.read_csv(out / "plans.csv")
        ran = [a for a in e5.ARMS if gates["stage1"][a]["passed"]]
        if gates["a1"]["passed"]:
            ran.append("A1_CREEP_QUIET_NR")
        self.assertEqual(sorted(set(plans["arm"])) if len(plans) else [], sorted(ran))
        self.assertEqual(set(gates["stage2"]), set(ran))
        for name in ran:
            self.assertEqual(
                list(plans.loc[plans["arm"] == name, "run"]),
                ["primary", "fill_A", "one_tick_cost", "controls_v2"],
            )
            for run_id in ("primary", "fill_A", "one_tick_cost", "controls_v2"):
                self.assertTrue(
                    (out / "runs" / "IDX" / f"{name}_{run_id}.json").exists(), (name, run_id)
                )
            self.assertIn("admissible", gates["stage2"][name])
            tick = json.loads(
                (out / "runs" / "IDX" / f"{name}_one_tick_cost.json").read_text(encoding="utf-8")
            )
            self.assertTrue(tick["execution"]["tick_cost"]["enabled"])
            self.assertTrue(tick["config"]["tick_cost"])
            primary = json.loads(
                (out / "runs" / "IDX" / f"{name}_primary.json").read_text(encoding="utf-8")
            )
            self.assertNotIn("tick_cost", primary["execution"])
            self.assertFalse(primary["config"]["tick_cost"])
        self.assertFalse((out / "runs" / "CRYPTO_CLOSE").exists())
        self.assertEqual(summary["stage2_runs"], len(plans))
        self.assertEqual(
            summary["precondition"], {"status": "REPRODUCED", "accepted_deviation": False}
        )
        self.assertEqual(summary["window"]["lead_in_sessions"], 65)
        self.assertEqual(
            summary["study_options"],
            {
                "panel_format": "panel-v2",
                "pool_units": "panel",
                "pool_version": "v3",
                "pool_keys": ["price_band", "liquidity", "volatility", "market_cap"],
            },
        )
        self.assertIn("6 fits", summary["search_size"])
        self.assertEqual(summary["selected_arm"], gates["selected_arm"])
        self.assertIs(summary["frozen_before_analysis"], True)  # frozen in commit e1e57af

    def test_discovery_is_deterministic(self):
        warnings.simplefilter("ignore")
        found = Discovered.get("IDX")
        out2 = Path(tempfile.mkdtemp(prefix="idxsig-e5-")) / "IDX" / "discovery"
        fake_reproduce(out2, found["meta"])
        e5.run_discovery(
            found["df"],
            found["meta"],
            found["registry"],
            out2,
            found["proto"],
            "synthetic-sha",
            "IDX",
            log=lambda *_: None,
        )
        for name in (
            "model.json",
            "thresholds.json",
            "stage1.json",
            "univariate.csv",
            "flags.csv",
            "gates.json",
            "plans.csv",
        ):
            self.assertEqual((found["out"] / name).read_bytes(), (out2 / name).read_bytes(), name)

    def test_crypto_discovery_censors_the_reset_and_runs_the_close_sensitivity(self):
        warnings.simplefilter("ignore")
        found = Discovered.get("CRYPTO")
        stage1, model, gates = found["stage1"], found["model"], found["gates"]
        self.assertEqual(len(stage1["unit_resets"]), 1)
        self.assertEqual(stage1["unit_resets"][0]["ticker"], "S002")
        self.assertEqual(model["D_label"]["rule"], "fixed")
        self.assertIn("ara", model["constant_column_names"])  # no price limits off IDX
        self.assertIn(
            "gap_r", model["constant_column_names"]
        )  # the synthetic open is the previous close
        self.assertEqual(stage1["entry_price"], "open")
        self.assertNotIn("by_regime", stage1["arms"]["A"])
        self.assertEqual(stage1["arms"]["B"]["primary"], "P2")
        plans = pd.read_csv(found["out"] / "plans.csv")
        self.assertTrue(
            gates["stage2"],
            "the synthetic CRYPTO discovery should pass at least one arm to Stage 2",
        )
        for name in gates["stage2"]:
            runs = plans[plans["arm"] == name]
            self.assertEqual(
                list(runs["run"]),
                ["primary", "participation_0_05_doubled_costs", "entry_at_close_t1", "controls_v2"],
            )
            self.assertEqual(
                list(runs["market_profile"]), ["CRYPTO", "CRYPTO", "CRYPTO_CLOSE", "CRYPTO"]
            )
            self.assertEqual(list(runs["jump_ratio"]), [10.0] * 4)
            # the sensitivity profile's run summary is keyed by its own name inside the CRYPTO stage directory
            out = found["out"]
            self.assertTrue(
                (out / "runs" / "CRYPTO_CLOSE" / f"{name}_entry_at_close_t1.json").exists()
            )
            self.assertTrue((out / "runs" / "CRYPTO" / f"{name}_primary.json").exists())
            self.assertFalse((out / "runs" / "CRYPTO" / f"{name}_entry_at_close_t1.json").exists())
            close = json.loads(
                (out / "runs" / "CRYPTO_CLOSE" / f"{name}_entry_at_close_t1.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                (close["config"]["market"], close["market"]["profile"], close["market"]["entry"]),
                ("CRYPTO_CLOSE", "CRYPTO", "close"),
            )
            self.assertEqual(
                close["panel"]["panel_sha256"], found["meta"]["sha256"]
            )  # CRYPTO's panel

    def test_discovery_refuses_without_the_precondition_or_on_other_data(self):
        warnings.simplefilter("ignore")
        found = Discovered.get("IDX")
        out = Path(tempfile.mkdtemp(prefix="idxsig-e5-")) / "IDX" / "discovery"
        with self.assertRaises(RuntimeError):
            e5.run_discovery(
                found["df"],
                found["meta"],
                found["registry"],
                out,
                found["proto"],
                "sha",
                "IDX",
                log=lambda *_: None,
            )
        fake_reproduce(out, {"sha256": "other"})
        with self.assertRaises(RuntimeError):
            e5.run_discovery(
                found["df"],
                found["meta"],
                found["registry"],
                out,
                found["proto"],
                "sha",
                "IDX",
                log=lambda *_: None,
            )
        fake_reproduce(out, found["meta"], status="DEVIATES")
        with self.assertRaises(RuntimeError):
            e5.run_discovery(
                found["df"],
                found["meta"],
                found["registry"],
                out,
                found["proto"],
                "sha",
                "IDX",
                log=lambda *_: None,
            )
        self.assertFalse(out.exists())
        with self.assertRaises(RuntimeError):  # the panel is not the protocol's
            e5.run_discovery(
                found["df"],
                {**found["meta"], "sha256": "x"},
                found["registry"],
                out,
                found["proto"],
                "sha",
                "IDX",
                log=lambda *_: None,
            )


# ------------------------------------------------------------------------------------ tick-cost sensitivity
TICK_RULE = """
def compute(m):
    out = np.zeros(m.shape)
    out[0, 8::9] = 1.0
    out[2, 5::13] = 1.0
    return np.where(m.tradeable, out, np.nan)
"""


class TickCostTests(unittest.TestCase):
    """backtest.RunConfig.tick_cost / execution.ExecConfig.tick_cost (research/E5 IDX closing-auction spread
    sensitivity) is additive and default-off: the default path never reaches the tick-size code, its output
    is unchanged, and the sensitivity adds exactly one tick per side to the per-side costs."""

    def test_default_path_never_touches_the_tick_code_and_is_unchanged(self):
        from idxsig import execution, market as market_rules

        df, meta = random_walk_panel(n_tickers=6, n_sessions=90, seed=21)
        rule = module_rule("TICKED", TICK_RULE)
        reg = synthetic_registry(df, meta)
        cfg = RunConfig("TICKED", random_draws=4)
        self.assertFalse(cfg.tick_cost)
        self.assertFalse(execution.ExecConfig(holding_days=5).tick_cost)

        # execution.py reaches the tick table only through its `market` module name: a stand-in whose
        # tick_size raises (limits unchanged) proves the default path never calls it.
        def reached(*_a, **_k):
            raise AssertionError("tick code reached")

        stub = types.SimpleNamespace(
            limits=market_rules.limits,
            special_limits=market_rules.special_limits,
            tick_size=reached,
        )
        with with_rule(rule):
            plain = run(cfg, df, meta, ca_registry=reg)
            with mock.patch.object(execution, "market", stub):
                guarded = run(cfg, df, meta, ca_registry=reg)
                with self.assertRaises(AssertionError):
                    run(
                        RunConfig("TICKED", random_draws=4, tick_cost=True),
                        df,
                        meta,
                        ca_registry=reg,
                    )
            ticked = run(
                RunConfig("TICKED", random_draws=4, tick_cost=True), df, meta, ca_registry=reg
            )
        pd.testing.assert_frame_equal(plain["trades"], guarded["trades"])
        pd.testing.assert_frame_equal(plain["draws"], guarded["draws"])
        a, b = dict(plain["summary"]), dict(guarded["summary"])
        a.pop("computed_at", None), b.pop("computed_at", None)
        self.assertEqual(
            json.dumps(a, sort_keys=True, default=str), json.dumps(b, sort_keys=True, default=str)
        )
        self.assertNotIn("tick_cost", plain["summary"]["execution"])
        self.assertFalse(plain["summary"]["config"]["tick_cost"])
        self.assertIn("tick_cost", ticked["summary"]["execution"])
        self.assertTrue(ticked["summary"]["config"]["tick_cost"])
        t0, t1 = plain["trades"], ticked["trades"]
        self.assertEqual(
            list(t0["status"]), list(t1["status"])
        )  # fills, lots and locks are unchanged
        np.testing.assert_array_equal(t0["gross_return"].to_numpy(), t1["gross_return"].to_numpy())
        scored = t0["status"].isin(("EXITED", "EXIT_DATA_END")).to_numpy()
        self.assertGreater(int(scored.sum()), 0)
        entry, exit_ = t0["entry_price"].to_numpy(float), t0["exit_price"].to_numpy(float)
        shares, factor = t0["shares"].to_numpy(float), t0["share_factor"].to_numpy(float)
        fees = plain["summary"]["execution"]["fees"]
        cost = shares * entry * (1 + fees["buy"] + market_rules.tick_size(entry) / entry)
        proceeds = (
            shares * factor * exit_ * (1 - fees["sell"] - market_rules.tick_size(exit_) / exit_)
        )
        np.testing.assert_allclose(
            t1["net_return"].to_numpy(float)[scored], (proceeds / cost - 1)[scored], rtol=1e-12
        )
        self.assertTrue(
            (
                t1["net_return"].to_numpy(float)[scored] < t0["net_return"].to_numpy(float)[scored]
            ).all()
        )
        # the controls pay the tick too: the matched mean moves with the rule, never only one side
        self.assertTrue(
            (
                t1["matched_mean_net_return"].to_numpy(float)[scored]
                < t0["matched_mean_net_return"].to_numpy(float)[scored]
            ).all()
        )

    def test_tick_cost_is_refused_off_idx(self):
        df, meta = e5_panel("CRYPTO", n=4, start="2022-01-03", end="2022-12-30")
        rule = module_rule("TICKEDX", TICK_RULE)
        with with_rule(rule):
            with self.assertRaises(ValueError):
                run(
                    RunConfig(
                        "TICKEDX",
                        market="CRYPTO",
                        ca_mode="adjusted",
                        random_draws=2,
                        tick_cost=True,
                    ),
                    df,
                    meta,
                )


# --------------------------------------------------------------------------------------------- cli
class CliTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(
            e5.use_protocol, e5.PROTOCOL
        )  # the CLI points the module at the protocol it runs

    def test_subcommands_parse_and_refuse_a_dirty_tree(self):
        for cmd in ("e5-reproduce", "e5-discovery", "e5-freeze", "e5-validation"):
            with mock.patch(
                "idxsig.results.code_state", return_value={"commit": "abc", "dirty": True}
            ):
                with mock.patch("sys.stderr") as err:
                    self.assertEqual(cli.main([cmd, "--market", "IDX", "--protocol", "v1.1"]), 2)
            self.assertIn("commit idxsig/ first", "".join(str(c) for c in err.write.call_args_list))
        with mock.patch("sys.stderr"):
            with self.assertRaises(SystemExit):
                cli.main(["e5-discovery", "--market", "CRYPTO_CLOSE", "--protocol", "v1.1"])
            with self.assertRaises(SystemExit):
                cli.main(["e5-freeze", "--protocol", "v1.1"])  # --market is required
            with self.assertRaises(SystemExit):
                cli.main(
                    ["e5-discovery", "--market", "IDX"]
                )  # --protocol is required: no silent default
        with mock.patch(
            "idxsig.results.code_state", return_value={"commit": "abc", "dirty": False}
        ):
            with mock.patch(
                "idxsig.e5.run_freeze", side_effect=RuntimeError("nothing to freeze")
            ) as rf:
                with mock.patch("sys.stderr"):
                    self.assertEqual(
                        cli.main(["e5-freeze", "--market", "US", "--protocol", "v1.1"]), 2
                    )
            self.assertEqual(rf.call_args[0][3], "US")
            self.assertEqual(rf.call_args[0][0], e5.stage_dir("US", "freeze"))
            self.assertEqual(rf.call_args[0][0], e5.E5_DIR / "v1.1" / "US" / "freeze")

    def test_protocol_v1_is_refused_before_any_panel_is_read(self):
        """PR #8 review (2026-10-15): `--protocol v1` on the corrected code computed v1.1 numbers under the v1
        label. It now stops before the tree check, the panel load or any stage, and names the v1 commit."""
        with (
            mock.patch("idxsig.results.code_state", return_value={"commit": "abc", "dirty": False}),
            mock.patch("idxsig.panel.load") as load,
            mock.patch("idxsig.global_panel.load") as gload,
            mock.patch("idxsig.e5.run_reproduce") as rr,
            mock.patch("idxsig.e5.run_discovery") as rd,
            mock.patch("idxsig.e5.run_freeze") as rf,
            mock.patch("idxsig.e5.run_validation") as rv,
        ):
            for cmd in ("e5-reproduce", "e5-discovery", "e5-freeze", "e5-validation"):
                for mk in e5.MARKETS:
                    with mock.patch("sys.stderr") as err:
                        self.assertEqual(cli.main([cmd, "--market", mk, "--protocol", "v1"]), 2)
                    message = "".join(str(c) for c in err.write.call_args_list)
                    self.assertIn("git checkout d0ce9ba", message)
                    self.assertIn("--protocol v1.1", message)
        for called in (load, gload, rr, rd, rf, rv):
            called.assert_not_called()


class ImplementationCheckTests(unittest.TestCase):
    """PR #8 review (2026-10-15): this code implements protocol v1.1 only (53447ca changed two v1 definitions in
    place), and the v1.1 protocol listed ten raw feature inputs where moonshot_e5.FEATURE_ARGS takes eleven
    (listed_before). The frozen protocol is corrected by research/E5/v1.1/spec_errata.json, never edited."""

    V1 = e5.E5_DIR / "protocol.json"
    V11 = e5.E5_DIR / "v1.1" / "protocol.json"
    V1_SHA = "53b2ec815a0cc0922298d77968842140db7445afd3de2a08837aefdbfec413ad"
    V11_SHA = "61968b8c8bc11927f94d8ec7b60dc8d235b5f085532aa2176fb975d92cd65be5"

    def test_v1_1_is_the_protocol_this_code_implements(self):
        proto, sha = e5.protocol(self.V11)
        self.assertEqual(sha, self.V11_SHA)
        self.assertEqual(proto["protocol_id"], e5.IMPLEMENTS)
        eff = e5.check_implementation(proto, self.V11)
        self.assertEqual(tuple(eff["features"]["feature_args"]), moonshot_e5.FEATURE_ARGS)
        self.assertEqual(
            len(proto["features"]["feature_args"]), 10
        )  # the frozen file is read, never changed

    def test_v1_and_unknown_protocols_are_refused(self):
        proto, sha = e5.protocol(self.V1)
        self.assertEqual(sha, self.V1_SHA)
        with self.assertRaisesRegex(RuntimeError, "git checkout d0ce9ba"):
            e5.check_implementation(proto, self.V1)
        with self.assertRaisesRegex(RuntimeError, "unknown E5 protocol"):
            e5.check_implementation({**proto, "protocol_id": "KOD-GLOBAL-E5-v9"}, self.V1)

    def test_the_recorded_outputs_name_the_code_each_protocol_points_to(self):
        """v1's outputs were computed by f101023 / 06c2dda (idxsig/ identical to d0ce9ba, which the refusal
        names); v1.1's by 5d7be0c (idxsig/ identical to 53447ca)."""
        for mk in e5.MARKETS:
            for stage, name, commits in (
                ("reproduce", "result.json", ("f101023",)),
                ("discovery", "summary.json", ("06c2dda",)),
            ):
                rec = json.loads((e5.E5_DIR / mk / stage / name).read_text(encoding="utf-8"))
                self.assertEqual(rec["protocol_sha256"], self.V1_SHA)
                self.assertIn(rec["code"]["commit"][:7], commits)
                rec = json.loads(
                    (e5.E5_DIR / "v1.1" / mk / stage / name).read_text(encoding="utf-8")
                )
                self.assertEqual(rec["protocol_sha256"], self.V11_SHA)
                self.assertEqual(rec["code"]["commit"][:7], "5d7be0c")

    def test_erratum_s1_is_the_only_correction_and_it_matches_the_code(self):
        proto, sha = e5.protocol(self.V11)
        v1, _ = e5.protocol(self.V1)
        errata = json.loads((self.V11.parent / e5.SPEC_ERRATA).read_text(encoding="utf-8"))
        self.assertEqual(
            (errata["protocol_id"], errata["protocol_sha256"]), (proto["protocol_id"], sha)
        )
        (s1,) = errata["errata"]
        self.assertEqual(s1["path"], "features.feature_args")
        self.assertEqual(s1["as_frozen"], proto["features"]["feature_args"])
        self.assertEqual(
            s1["as_frozen"], v1["features"]["feature_args"]
        )  # v1.1 never touched the list
        self.assertEqual(s1["effective"], s1["as_frozen"] + ["listed_before"])
        self.assertEqual(
            proto["features"]["order"], list(moonshot_e5.FEATURE_ORDER)
        )  # the 41 columns: unchanged
        eff = e5.effective_protocol(proto, self.V11)
        self.assertEqual(tuple(eff["features"]["feature_args"]), moonshot_e5.FEATURE_ARGS)
        eff["features"]["feature_args"] = proto["features"]["feature_args"]
        self.assertEqual(eff, proto)  # nothing else differs

    def test_a_disagreement_is_refused(self):
        proto, _ = e5.protocol(self.V11)
        with tempfile.TemporaryDirectory() as tmp:
            path = (
                Path(tmp) / "protocol.json"
            )  # no errata beside it: the frozen ten disagree with the code
            with self.assertRaisesRegex(RuntimeError, "FEATURE_ARGS"):
                e5.check_implementation(proto, path)
            errata = Path(tmp) / e5.SPEC_ERRATA
            errata.write_text(
                json.dumps(
                    {
                        "protocol_id": proto["protocol_id"],
                        "errata": [
                            {
                                "id": "X",
                                "path": "features.feature_args",
                                "as_frozen": ["close"],
                                "effective": [],
                            }
                        ],
                    }
                )
            )
            with self.assertRaisesRegex(RuntimeError, "as frozen"):
                e5.check_implementation(proto, path)
            errata.write_text(json.dumps({"protocol_id": "KOD-GLOBAL-E5-v1", "errata": []}))
            with self.assertRaisesRegex(RuntimeError, "corrects"):
                e5.check_implementation(proto, path)
        with mock.patch.object(moonshot_e5, "FEATURE_ARGS", moonshot_e5.FEATURE_ARGS + ("extra",)):
            with self.assertRaisesRegex(RuntimeError, "FEATURE_ARGS"):
                e5.check_implementation(proto, self.V11)
        with mock.patch.object(moonshot_e5, "FEATURE_ORDER", moonshot_e5.FEATURE_ORDER[:-1]):
            with self.assertRaisesRegex(RuntimeError, "FEATURE_ORDER"):
                e5.check_implementation(proto, self.V11)


class PlanWindowEligibilityTests(unittest.TestCase):
    """Audit finding A (2026-10-14, research/E5/v1.1): a flag whose label window ended on the period's last
    session had its plan window, exit at t+1+H, scored with the first post-period close, for the flag and its
    matched controls alike (IDX witness: INPS, Arm A, 2022-12-23, exit 2023-01-02)."""

    def test_discovery_reads_nothing_after_the_period_end(self):
        warnings.simplefilter("ignore")
        found = Discovered.get("IDX")
        df, meta, proto, stage1 = found["df"], found["meta"], found["proto"], found["stage1"]
        elig = stage1["eligibility"]
        self.assertLess(
            elig["plan_window_eligible_ticker_days"], elig["label_eligible_ticker_days"]
        )
        self.assertEqual(elig["study_last_session"], stage1["window"]["last_period_session"])
        self.assertEqual(stage1["window"]["study_end"], stage1["window"]["period_end"])
        flags = pd.read_csv(found["out"] / "flags.csv")
        late = flags[flags["date"] > elig["last_plan_eligible_session"]]
        self.assertTrue(late["plan_return"].isna().all() and late["matched_plan_mean"].isna().all())
        for arm in e5.ARMS:
            block = stage1["arms"][arm]
            self.assertEqual(
                block["plan_window"]["flags_with_return"],
                int(flags[(flags["arm"] == arm) & flags["plan_return"].notna()].shape[0]),
            )
        # the witness, generalised: every close after the period end changes nothing in discovery
        end = np.datetime64(proto["markets"]["IDX"]["periods"]["discovery"][1], "D")
        pert = df.copy()
        after = pert["date"].to_numpy().astype("datetime64[D]") > end
        self.assertTrue(after.any())
        for c in ("close", "high", "low", "previous"):
            pert.loc[after, c] = (pert.loc[after, c].astype(float) * 1.5).round().astype("Int64")
        out = Path(tempfile.mkdtemp(prefix="idxsig-e5-pert-")) / "IDX" / "discovery"
        fake_reproduce(out, meta)
        e5.run_discovery(
            pert,
            meta,
            synthetic_registry(pert, meta),
            out,
            proto,
            "synthetic-sha",
            "IDX",
            log=lambda *_: None,
        )
        again = json.loads((out / "stage1.json").read_text(encoding="utf-8"))
        self.assertEqual(again, stage1)
        self.assertEqual(
            json.loads((out / "model.json").read_text(encoding="utf-8"))["coef_U"],
            found["model"]["coef_U"],
        )


if __name__ == "__main__":
    unittest.main()
