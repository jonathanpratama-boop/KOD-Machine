"""Prospective paper ledger (no orders). Synthetic data only. Each test names the failure it
guards against."""

import tempfile
import unittest
import warnings
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from idxsig import paper
from idxsig.rules import moonshot_e1 as family

VALIDATED = {"precision": 0.08, "lift_vs_matched_random": 3.0, "p_one_sided_vs_matched": 0.005,
             "trading": {"p_one_sided": 0.01, "avg_net_return": 0.02, "matched_random_avg_net_return": 0.0, "run_id": "t"}}
DETECTION_ONLY = {**VALIDATED, "trading": {"p_one_sided": 1.0, "avg_net_return": -0.04,
                                           "matched_random_avg_net_return": -0.005, "run_id": "t"}}


def frame(n=60, s=80, spike=None, price=1000, adv_volume=2_000_000, tail=None):
    """Flat-ish names; spike = (ticker index, session index) gets volume x10 and +20%; tail: closes after it."""
    rng = np.random.default_rng(0)
    dates = pd.to_datetime(np.busday_offset(np.datetime64("2026-06-01", "D"), np.arange(s), roll="forward"))
    rows = []
    for i in range(n):
        p = float(price)
        for d in range(s):
            prev = p
            vol = int(adv_volume * rng.uniform(0.8, 1.2))
            step = rng.normal(0, 0.005)
            if spike and i == spike[0] and d == spike[1]:
                step, vol = 0.20, vol * 10
            if spike and tail and i == spike[0] and d > spike[1]:
                step = tail
            p = max(round(prev * (1 + step)), 50)
            rows.append({"date": dates[d], "ticker": f"T{i:03d}", "source": "yahoo", "previous": prev, "open": np.nan,
                         "high": max(prev, p), "low": min(prev, p), "close": p, "volume": vol, "value": vol * p,
                         "frequency": np.nan, "listed_shares": np.nan, "tradable_shares": np.nan})
    return pd.DataFrame(rows)


DATA = {"manifest": "synthetic", "manifest_sha256": "0" * 64, "http_status": {f"T{i:03d}": 200 for i in range(60)}}


class PaperScan(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore")
        self.sel = mock.patch.object(family, "SELECTED", "F3_VOL5_RET10")
        self.sel.start()

    def tearDown(self):
        self.sel.stop()

    def test_no_signal_day_is_still_a_record(self):
        """Guards against: quiet days leaving no trace, so the scan history looks better than it was."""
        out = paper.scan_frame(frame(), DATA)
        self.assertEqual(out["scan"]["result"], "NO SIGNAL")
        self.assertEqual(out["decisions"], [])
        self.assertEqual(out["scan"]["data"]["fresh_for_session"], 60)
        self.assertIn("F2_IGNITION_D", out["scan"]["flags"])

    def test_every_candidate_reaches_a_terminal_decision(self):
        """Guards against: candidates left undecided, BUY without validated evidence, and plans missing
        the trigger, chase limit, invalidation, sizing or maximum loss."""
        df = frame(spike=(7, 79))
        unvalidated = paper.scan_frame(df, DATA)["decisions"]
        self.assertEqual([d["decision"] for d in unvalidated], ["PASS"])
        passed = paper.scan_frame(df, DATA, validation=DETECTION_ONLY)["decisions"][0]
        self.assertEqual(passed["decision"], "PASS")
        self.assertIn("executable plan", passed["reason"])  # detection alone never buys
        d = paper.scan_frame(df, DATA, validation=VALIDATED)["decisions"][0]
        self.assertEqual(d["decision"], "BUY ON TRIGGER")
        self.assertTrue(d["primary"])
        plan = d["plan"]
        for key in ("entry_trigger", "max_chase_price", "invalidation", "sizing_formula", "scenarios", "expiry",
                    "horizon_sessions", "would_change_decision"):
            self.assertIn(key, plan)
        self.assertLess(plan["invalidation"], d["verified_price"]["close"])
        for sc in plan["scenarios"]:
            self.assertLessEqual(sc["max_planned_loss_idr"], sc["risk_budget_idr"] * 1.0001)
            self.assertEqual(sc["shares"] % 100, 0)
        self.assertIn("falsified_if", d["prediction"])

    def test_untradeable_candidate_is_not_executable_with_the_reason(self):
        """Guards against: a plan for a name where no lot fits the liquidity or risk caps."""
        d = paper.scan_frame(frame(spike=(7, 79), price=200_000, adv_volume=300), DATA, validation=VALIDATED)["decisions"][0]
        self.assertEqual(d["decision"], "NOT EXECUTABLE")
        self.assertIn("no whole lot fits", d["reason"])

    def test_ledger_chain_detects_any_edit(self):
        """Guards against: a decision rewritten after the outcome is known."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            paper.append([{"type": "SCAN", "x": 1}, {"type": "DECISION", "decision": "PASS"}], path=path)
            paper.append([{"type": "OUTCOME", "y": 2}], path=path)
            self.assertEqual(paper.verify_chain(path), [])
            path.write_text(path.read_text().replace('"PASS"', '"BUY ON TRIGGER"'))
            self.assertTrue(paper.verify_chain(path))
            with self.assertRaisesRegex(RuntimeError, "chain is broken"):
                paper.append([{"type": "SCAN"}], path=path)

    def test_scoring_separates_discovery_from_the_decision(self):
        """Guards against: a rejected name that then ran being scored as a good call (or vice versa)."""
        base = frame(spike=(7, 74), s=75)
        scan = paper.scan_frame(base, DATA)
        passed = scan["decisions"][0]
        self.assertIsNone(paper.score(passed, paper._market(base)))  # window still open
        ran = frame(spike=(7, 74), s=82, tail=0.08)
        out = paper.score(passed, paper._market(ran))
        self.assertTrue(out["discovery"]["E30"])
        self.assertEqual(out["decision_verdict"], "MISSED GAIN (rejected, plan would have profited)")
        bought = paper.scan_frame(base, DATA, validation=VALIDATED)["decisions"][0]
        res = paper.score(bought, paper._market(ran))
        self.assertEqual(res["decision_verdict"], "PROFIT")
        self.assertGreater(res["execution"]["paper_trade"]["net_return"], 0)


if __name__ == "__main__":
    unittest.main()
