"""PREMOVE_SHADOW_v1: the shuffled control, frozen-model reload, live-bar completeness and ledger checks."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from idxsig import paper, premove_shadow as shadow
from idxsig.premove_core import fit_model


def _frame(n=6, lookback=20, seed=1):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        row = {"ticker": f"T{i}USDT", "date": pd.Timestamp("2026-10-01") + pd.Timedelta(days=i)}
        for k in ("return", "range", "volume"):
            for lag in range(lookback):
                row[f"seq_{k}_{lag:02d}"] = rng.normal()
        rows.append(row)
    return pd.DataFrame(rows)


class ShuffledControl(unittest.TestCase):
    def test_each_day_keeps_its_three_observations_together(self):
        f = _frame()
        g = shadow.shuffle_windows(f)
        for i in range(len(f)):
            before = {
                tuple(f.loc[i, f"seq_{k}_{lag:02d}"] for k in ("return", "range", "volume"))
                for lag in range(20)
            }
            after = {
                tuple(g.loc[i, f"seq_{k}_{lag:02d}"] for k in ("return", "range", "volume"))
                for lag in range(20)
            }
            self.assertEqual(before, after)

    def test_order_changes_per_row_and_is_repeatable(self):
        f = _frame()
        a, b = shadow.shuffle_windows(f), shadow.shuffle_windows(f)
        pd.testing.assert_frame_equal(a, b)
        cols = [f"seq_return_{lag:02d}" for lag in range(20)]
        orders = [
            tuple(list(f.loc[i, cols]).index(v) for v in a.loc[i, cols]) for i in range(len(f))
        ]
        self.assertGreater(len(set(orders)), 1)  # not one common permutation
        self.assertFalse(np.allclose(a[cols].to_numpy(), f[cols].to_numpy()))

    def test_input_is_not_modified(self):
        f = _frame()
        copy = f.copy()
        shadow.shuffle_windows(f)
        pd.testing.assert_frame_equal(f, copy)


class FrozenModels(unittest.TestCase):
    def test_a_record_reloads_to_the_same_predictions(self):
        rng = np.random.default_rng(3)
        n = 300
        rows = pd.DataFrame(
            {
                "a": rng.normal(size=n),
                "b": rng.normal(size=n),
                "s1": rng.normal(size=n),
                "s2": rng.normal(size=n),
            }
        )
        cls = rng.integers(0, 3, n)
        for k, t in enumerate(("up_first", "down_first", "neither")):
            rows[t] = (cls == k).astype(float)
        model = fit_model(rows, ("a", "b"), ("s1", "s2"), pca_components=2, ridge=1.0)
        again = shadow.model_from_record(json.loads(json.dumps(model.record())))
        np.testing.assert_allclose(model.predict(rows), again.predict(rows))

    def test_the_pinned_frozen_models_load(self):
        frozen = json.loads(shadow.FROZEN.read_text())
        for name in ("summary", "sequence"):
            m = shadow.model_from_record(frozen[name])
            self.assertEqual(m.coefficients.shape[0], 3)


class LiveBars(unittest.TestCase):
    def test_a_bar_still_open_at_download_is_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            day = 86_400_000
            start = 1_793_232_000_000  # 2026-10-29 00:00 UTC
            klines = [
                [
                    start + i * day,
                    "1",
                    "2",
                    "0.5",
                    "1.5",
                    "10",
                    start + (i + 1) * day - 1,
                    "15",
                    1,
                    "0",
                    "0",
                    "0",
                ]
                for i in range(2)
            ]
            (root / "AAAUSDT.json").write_text(json.dumps(klines))
            header = {"manifest": "binance_recent-test.jsonl", "n_files": 1}
            rec = {
                "symbol": "AAAUSDT",
                "base_asset": "AAA",
                "http_status": 200,
                "path": str(root / "AAAUSDT.json"),
                "downloaded_at": "2026-10-30T00:25:00Z",
            }
            man = root / "m.jsonl"
            man.write_text(json.dumps(header) + "\n" + json.dumps(rec) + "\n")
            with mock.patch.object(shadow, "PKG_ROOT", Path("/")):
                panel, _ = shadow.live_panel(man)
            self.assertEqual(
                panel.set_index("date")["complete_bar"].to_dict(),
                {"2026-10-29": True, "2026-10-30": False},
            )

    def test_stable_and_leveraged_pairs_are_left_out(self):
        self.assertIn("USDC", shadow.STABLE)
        self.assertTrue(shadow.LEVERAGED.search("BTCUP"))


class LedgerChecks(unittest.TestCase):
    def _ledger(self, records):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "premove_shadow.jsonl"
        paper.append(records, path=path)
        return path

    def test_sealed_twice_and_sealed_before_close_are_flagged(self):
        f = {
            "type": shadow.FORECAST,
            "decision_date": "2026-10-30",
            "made_at": "2026-10-30T23:00:00Z",
        }
        path = self._ledger([f, {**f, "made_at": "2026-10-31T00:30:00Z"}])
        with mock.patch.object(shadow, "LEDGER", path):
            problems = shadow.verify()
        self.assertTrue(any("sealed twice" in p for p in problems), problems)
        self.assertTrue(any("before the day closed" in p for p in problems), problems)

    def test_a_resolution_must_point_at_its_forecast(self):
        f = {
            "type": shadow.FORECAST,
            "decision_date": "2026-10-30",
            "made_at": "2026-10-31T00:30:00Z",
        }
        path = self._ledger([f])
        stored = paper.ledger_lines(path)[0]
        paper.append(
            [
                {
                    "type": shadow.RESOLUTION,
                    "decision_date": "2026-10-30",
                    "forecast_record_hash": "0" * 64,
                    "resolved_at": "2026-11-05T00:30:00Z",
                }
            ],
            path=path,
        )
        with mock.patch.object(shadow, "LEDGER", path):
            self.assertTrue(any("does not point" in p for p in shadow.verify()))
        self.assertTrue(stored["record_hash"])


class Analysis(unittest.TestCase):
    def test_block_bootstrap_brackets_a_known_difference(self):
        rng = np.random.default_rng(5)
        a = pd.Series(rng.random(200) * 0.1 + 0.05)
        b = a - 0.02
        r = shadow.paired_block_bootstrap(a, b, block=10, draws=500, seed=1)
        self.assertAlmostEqual(r["diff"], 0.02, places=9)
        self.assertLessEqual(r["lo95"], 0.02 + 1e-9)
        self.assertGreaterEqual(r["hi95"], 0.02 - 1e-9)

    def test_too_few_days_give_no_interval(self):
        r = shadow.paired_block_bootstrap(
            pd.Series([0.2, 0.0]), pd.Series([0.0, 0.0]), block=10, draws=10, seed=1
        )
        self.assertIsNone(r["lo95"])


if __name__ == "__main__":
    unittest.main()
