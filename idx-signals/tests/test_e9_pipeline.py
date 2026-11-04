"""End-to-end check of research/E9's entry builder, runner and verifier on a synthetic panel (no real data, no
network): the runner's reproduction checks pass, and the independent verifier agrees with every decisive number."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from idxsig import global_panel

E9_CODE = Path(__file__).resolve().parents[1] / "research" / "E9"
REAL_META = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "manifests"
    / "panel_us_repair-20261008T114805Z.json"
)


def load(name):
    spec = importlib.util.spec_from_file_location(f"e9_{name}", E9_CODE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def synthetic(seed=11, n=36, days=330):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-05-01", periods=days)
    rows = []
    for k in range(n):
        p = 1.5 + 40 * rng.random()
        thin = k % 9 == 0  # a few names too thin to fill
        for d in dates:
            r = rng.normal(0.0, 0.05)
            if rng.random() < 0.025:
                r = 0.30 + 0.6 * rng.random()  # a G2_RET30 day
            prev, p = p, max(0.05, p * (1 + r))
            o = prev * (1 + rng.normal(0, 0.02))
            vol = (
                float(rng.integers(200, 2_000)) if thin else float(rng.integers(100_000, 3_000_000))
            )
            rows.append(
                (
                    d,
                    f"T{k:02d}",
                    "synthetic",
                    prev,
                    o,
                    max(o, p) * 1.01,
                    min(o, p) * 0.99,
                    p,
                    vol,
                    vol * p,
                    1e7,
                    1.0 if k % 5 else 0.5,
                )
            )
    df = pd.DataFrame(
        rows,
        columns=[
            "date",
            "ticker",
            "source",
            "previous",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "value",
            "listed_shares",
            "unit_factor",
        ],
    )
    df.loc[df.groupby("ticker").head(1).index, "previous"] = np.nan
    real = json.loads(REAL_META.read_text()) if REAL_META.exists() else {}
    meta = {
        "sha256": "synthetic",
        "market": "US",
        "default_start": "2020-05-01",
        "source_boundary": "2021-08-20",
        "survivorship": "synthetic",
        "quality_tiers": real.get(
            "quality_tiers", [{"from": "2020-01-01", "to": "2030-12-31", "tier": "TIER_1"}]
        ),
        "unit_quarantine": {
            "tickers": {"T03": ["MENTION_ONLY"], "T07": ["RATIO_CONFIRMED"]},
            "reason_counts": {},
        },
        "unit_schedule": None,
        "preprocessing": None,
        "known_limitations": [],
        "panel": "synthetic",
    }
    return df, meta


class Pipeline(unittest.TestCase):
    def test_entries_runner_and_verifier_agree(self):
        ME, R, V = load("make_entries"), load("run_test"), load("verify_result")
        panel, meta = synthetic()
        with tempfile.TemporaryDirectory() as tmp:
            e9 = Path(tmp) / "research" / "E9"
            (e9 / "feasibility_a3").mkdir(parents=True)
            fake_load = lambda manifest: (panel.copy(), json.loads(json.dumps(meta)))  # noqa: E731
            with (
                mock.patch.object(global_panel, "load", fake_load),
                mock.patch.object(ME, "OUT", e9 / "entries"),
            ):
                self.assertEqual(ME.main(), 0)
                S = pd.read_csv(
                    e9 / "entries" / "signals.csv",
                    dtype={"ticker": str},
                    keep_default_na=False,
                    na_values=[""],
                )
                A = S[S.j >= 0].reset_index(drop=True)
                rng = np.random.default_rng(5)
                cls = rng.choice(
                    ["DOCUMENTED", "UNDOCUMENTED", "DILUTION", "NO_CIK", "NO_HEADER"],
                    size=len(A),
                    p=[0.3, 0.45, 0.15, 0.05, 0.05],
                )
                K = pd.DataFrame(
                    {
                        "j": A.j,
                        "ticker": A.ticker,
                        "signal_date": A.signal_date,
                        "status": A.status,
                        "class": cls,
                        "window_covered": rng.random(len(A)) > 0.05,
                        "etoro_listed_now": rng.random(len(A)) > 0.2,
                        "later_documented_4d": rng.random(len(A)) > 0.7,
                        "forms": np.where(cls == "DOCUMENTED", "8-K", ""),
                        "items_8k": np.where(cls == "DOCUMENTED", "8.01", ""),
                    }
                )
                K.to_csv(
                    e9 / "feasibility_a3" / "classes.csv.gz",
                    index=False,
                    compression={"method": "gzip", "mtime": 0},
                )
                proto = {
                    "protocol_id": "E9_SYNTHETIC",
                    "hashes": {},
                    "statistics": {"resamples": 400, "seed": 3},
                    "costs": {
                        "stress_extra_per_side": 0.005,
                        "unit_uncertain_tier_per_side": 0.015,
                    },
                    "secondary": {"holding_days": 20},
                    "exposure": {"capital_usd": 100000.0},
                    "acceptance": {"years": ["2020", "2021"]},
                }
                (e9 / "protocol.json").write_text(json.dumps(proto))
                with (
                    mock.patch.object(R, "E9", e9),
                    mock.patch.object(R, "OUT", e9 / "results"),
                    mock.patch.object(R, "ROOT", Path(tmp)),
                ):
                    self.assertEqual(R.main(), 0)
                    with self.assertRaises(SystemExit):  # the test runs once
                        R.main()
            res = json.loads((e9 / "results" / "RESULT.json").read_text())
            mine, harness = res["reproduction"]["control_pooled_mean_vs_harness"]
            self.assertAlmostEqual(mine, harness, places=12)
            D = pd.read_csv(
                e9 / "results" / "trades.csv.gz",
                dtype={"ticker": str},
                keep_default_na=False,
                na_values=[""],
            )
            self.assertEqual(len(D), len(A))
            scored = D.status.isin(["EXITED", "EXIT_DATA_END"])
            self.assertGreater(int(scored.sum()), 30)
            self.assertTrue(
                D.loc[D.ticker.isin(["T03", "T07"]), "unit_uncertain"].astype(str).eq("True").all()
            )
            self.assertTrue((D.loc[scored, "net_bound"] <= D.loc[scored, "net"] + 1e-12).all())
            self.assertTrue((D.loc[scored, "net_stress"] < D.loc[scored, "net"]).all())
            n_doc = int(
                ((D["class"] == "DOCUMENTED") & scored & D.covered.astype(str).eq("True")).sum()
            )
            self.assertEqual(res["scored_by_class"]["DOCUMENTED"], n_doc)
            with mock.patch.object(V, "E9", e9):
                self.assertEqual(V.main(), 0)


if __name__ == "__main__":
    unittest.main()
