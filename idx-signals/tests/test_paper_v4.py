"""Paper policy v4: IDX decisions under a validated E3 (detector, plan) pair. Synthetic data only.
Each test names the failure it guards against."""

import unittest
import warnings
from unittest import mock

import numpy as np

from idxsig import paper
from idxsig.market import floor_tick
from idxsig.rules import moonshot_e1, moonshot_e3
from tests.test_paper import DATA, VALIDATED, frame

PLAN = {"entry_rule": "confirm", "entry_window": 3, "exit_rule": "stop_ref", "holding_days": 3}
E3 = {
    "detector": "F1_ARA",
    "plan": PLAN,
    "run_id": "t-e3",
    "protocol_id": "KOD-IDX-E3-v1",
    "plan_text": "buy at the first close in s+1..s+3 above the signal close; sell at the first close at or below "
    "the signal session's reference price, else the close of the 3th session after entry",
    "result": "research/E3/validation/result.json",
    "result_sha256": "0" * 64,
    "detection_path": None,
}
SELECTED = ("F1_ARA", "confirm", 3, "stop_ref", 3)


def lock_at_ara(df, ticker, session):
    """Make `ticker` close locked at the regular ARA limit on `session` (index into the sessions)."""
    dates = sorted(df["date"].unique())
    sel = (df["ticker"] == ticker) & (df["date"] == dates[session])
    prev = float(df.loc[sel, "previous"].iloc[0])
    close = float(floor_tick(np.array([prev * 1.25]))[0])  # <= Rp5,000 band, 2026 regime
    df.loc[sel, ["close", "high"]] = close
    df.loc[sel, "low"] = min(prev, close)
    df.loc[sel, "volume"] = df.loc[sel, "volume"] * 10
    df.loc[sel, "value"] = df.loc[sel, "volume"] * close
    nxt = (df["ticker"] == ticker) & (df["date"] > dates[session])
    df.loc[nxt, "previous"] = close  # keep the chain consistent for whatever follows
    return close


def set_path(df, ticker, session, closes):
    """Closes of `ticker` from `session`+1 on, each session's reference = the prior close."""
    dates = sorted(df["date"].unique())
    prev = float(df.loc[(df["ticker"] == ticker) & (df["date"] == dates[session]), "close"].iloc[0])
    for k, close in enumerate(closes, start=1):
        close = int(round(close))  # integer rupiah, as the frame's prices are
        sel = (df["ticker"] == ticker) & (df["date"] == dates[session + k])
        df.loc[sel, "previous"] = prev
        df.loc[sel, "close"] = close
        df.loc[sel, "high"] = max(prev, close)
        df.loc[sel, "low"] = min(prev, close)
        df.loc[sel, "value"] = df.loc[sel, "volume"] * close
        prev = close


class V4(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore")
        self.patches = [
            mock.patch.object(paper, "e3_plan", lambda: E3),
            mock.patch.object(moonshot_e3, "SELECTED", SELECTED),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_without_a_validated_pair_the_policy_is_v3s(self):
        """Guards against: v4 changing IDX decisions when E3 has not frozen and validated anything."""
        self.assertEqual(paper.POLICY_ID_V4, "PAPER-POLICY-v4")
        with (
            mock.patch.object(paper, "e3_plan", lambda: None),
            mock.patch.object(moonshot_e1, "SELECTED", "F3_VOL5_RET10"),
        ):
            d = paper.scan_frame(
                frame(spike=(7, 79)), DATA, validation=VALIDATED, policy=paper.POLICY_ID_V4
            )["decisions"][0]
        self.assertEqual(d["detector"]["rule_id"], "MOONSHOT_E1_D1")
        self.assertNotIn("execution_plan", d["plan"])
        self.assertIsNotNone(d["plan"]["max_chase_price"])

    def test_scan_runs_the_e3_detector_and_decisions_carry_its_plan(self):
        """Guards against: a validated plan existing while decisions still describe the v3 next-close plan."""
        df = frame(spike=(7, 79))
        close = lock_at_ara(df, "T007", 79)
        out = paper.scan_frame(df, DATA, validation=VALIDATED, policy=paper.POLICY_ID_V4)
        self.assertEqual(out["scan"]["detector"]["rule_id"], "MOONSHOT_E3_D1")
        self.assertEqual(out["scan"]["detector"]["selected"], "F1_ARA")
        self.assertTrue(out["scan"]["scan_id"].endswith("-F1_ARA"))
        self.assertEqual(set(out["scan"]["flags"]), {"F1_ARA", "F7_ARA_VOL3", "F8_ARA_EARLY"})
        self.assertEqual(out["scan"]["flags"]["F1_ARA"], ["T007"])
        d = out["decisions"][0]
        self.assertEqual(d["decision"], "BUY ON TRIGGER")
        self.assertIn("E3", d["reason"])
        plan = d["plan"]
        self.assertEqual(plan["execution_plan"], PLAN)
        self.assertIsNone(plan["max_chase_price"])
        self.assertEqual(len(plan["entry_sessions"]), 3)
        self.assertIn("first session among", plan["entry_trigger"])
        self.assertIn(f"Rp{close:g}", plan["entry_trigger"])
        self.assertEqual(plan["horizon_sessions"], 3)
        self.assertIn(plan["entry_sessions"][-1], plan["expiry"])
        previous = float(
            df.loc[(df["ticker"] == "T007") & (df["date"] == df["date"].max()), "previous"].iloc[0]
        )
        self.assertAlmostEqual(plan["invalidation"], float(floor_tick(np.array([previous]))[0]))
        self.assertIn("reference price", plan["exit"])
        for sc in plan["scenarios"]:
            self.assertLessEqual(sc["max_planned_loss_idr"], sc["risk_budget_idr"] * 1.0001)
            self.assertEqual(sc["shares"] % 100, 0)
        unvalidated = paper.scan_frame(df, DATA, policy=paper.POLICY_ID_V4)["decisions"][0]
        self.assertEqual(unvalidated["decision"], "PASS")
        self.assertEqual(unvalidated["plan"]["execution_plan"], PLAN)

    def test_plan_without_a_stop_sizes_on_one_locked_session(self):
        """Guards against: a plan with no price stop producing no invalidation and therefore no size."""
        e3 = {**E3, "plan": {**PLAN, "exit_rule": "first_down"}}
        df = frame(spike=(7, 79))
        lock_at_ara(df, "T007", 79)
        with mock.patch.object(paper, "e3_plan", lambda: e3):
            d = paper.scan_frame(df, DATA, validation=VALIDATED, policy=paper.POLICY_ID_V4)[
                "decisions"
            ][0]
        self.assertEqual(d["decision"], "BUY ON TRIGGER")
        self.assertIsNone(d["plan"]["invalidation"])
        self.assertGreater(d["plan"]["sizing_stop"], 0)
        self.assertIn("no price stop", d["plan"]["invalidation_rule"])
        self.assertTrue(d["plan"]["scenarios"][-1]["shares"] > 0)

    def _world(self, s=84):
        """One frame: the decision is made on its first 75 sessions, the bars that score it on all of them
        (frame() draws its random walk per ticker, so two frames of different length differ in prices)."""
        world = frame(spike=(7, 74), s=s)
        lock_at_ara(world, "T007", 74)
        return world

    def _decision(self, validation=VALIDATED, world=None):
        world = self._world() if world is None else world
        dates = sorted(world["date"].unique())
        base = world[world["date"] <= dates[74]].copy()
        return paper.scan_frame(base, DATA, validation=validation, policy=paper.POLICY_ID_V4)[
            "decisions"
        ][0]

    def _bars(self, closes, s=84):
        world = self._world(s=s)
        set_path(world, "T007", 74, closes)
        return paper._market(world)

    def test_plan_decisions_are_scored_by_the_harness_model(self):
        """Guards against: outcomes of a validated plan computed by a different rule than the one validated."""
        d = self._decision()
        self.assertEqual(d["decision"], "BUY ON TRIGGER")
        signal_close = d["verified_price"]["close"]
        ref = int(d["plan"]["invalidation"])  # the signal session's reference price, tick-floored
        self.assertLess(ref, signal_close)
        up = int(round(signal_close * 1.05))
        # confirm triggers on the first close above the signal close (session +1); no stop; horizon exit at +4
        closes = [up, up - 10, up - 20, up - 30, up - 40, up - 50, up - 60]
        res = paper.score(d, self._bars(closes))
        trade = res["execution"]["paper_trade"]
        self.assertEqual(res["execution"]["harness_status"], "EXITED")
        self.assertEqual(trade["entry_lag_sessions"], 1)
        self.assertEqual(trade["entry_price"], up)
        self.assertEqual(trade["exit_reason"], "horizon")
        self.assertAlmostEqual(
            trade["net_return"], ((up - 30) / up) * (1 - 0.0025) / (1 + 0.0015) - 1, places=6
        )
        self.assertEqual(res["decision_verdict"], "LOSS")
        self.assertIn("plan-harness-v1", res["scoring_version"])
        # the stop: a close at or below the signal session's reference price ends the trade there. The
        # fall from +5% to the reference is more than one session's lower limit (15%), so take three.
        with mock.patch.object(
            paper, "e3_plan", lambda: {**E3, "plan": {**PLAN, "holding_days": 5}}
        ):
            d5 = self._decision()
        bars = self._bars([up, int(up * 0.9), int(up * 0.81), ref, ref + 5, ref, ref, ref])
        stopped = paper.score(d5, bars)
        self.assertEqual(stopped["execution"]["paper_trade"]["exit_reason"], "stop_ref")
        self.assertEqual(stopped["execution"]["paper_trade"]["entry_session"], str(bars.dates[75]))
        self.assertEqual(stopped["execution"]["paper_trade"]["exit_session"], str(bars.dates[78]))
        self.assertAlmostEqual(
            stopped["execution"]["paper_trade"]["net_return"],
            (ref / up) * (1 - 0.0025) / (1 + 0.0015) - 1,
            places=6,
        )
        # a stop session locked at the lower limit (a fall of more than 15% in one session): the sale
        # rolls to the next session where it is possible, and the outcome says so
        locked = paper.score(d5, self._bars([up, int(up * 0.9), ref, ref + 5, ref, ref, ref, ref]))
        self.assertIn(
            "stop_ref (rolled 1 session", locked["execution"]["paper_trade"]["exit_reason"]
        )
        self.assertEqual(locked["execution"]["paper_trade"]["exit_session"], str(bars.dates[78]))
        # no close above the signal close within three sessions: no trade, a BUY is NOT FILLED
        none = paper.score(d, self._bars([int(signal_close * 0.99)] * 7))
        self.assertIsNone(none["execution"]["paper_trade"])
        self.assertEqual(none["execution"]["harness_status"], "SKIP_NO_TRIGGER")
        self.assertEqual(none["decision_verdict"], "NOT FILLED")
        passed = self._decision(validation=None)
        self.assertEqual(passed["decision"], "PASS")
        rejected = paper.score(
            passed,
            self._bars([up, int(up * 1.1), int(up * 1.2), int(up * 1.3)] + [int(up * 1.3)] * 3),
        )
        self.assertEqual(
            rejected["decision_verdict"], "MISSED GAIN (rejected, plan would have profited)"
        )

    def test_open_plan_windows_are_not_scored(self):
        """Guards against: a conditional entry judged 'no trigger' before its window has elapsed."""
        d = self._decision()
        self.assertIsNone(
            paper.score(d, self._bars([int(d["verified_price"]["close"] * 0.99)], s=76))
        )
        self.assertEqual(paper._span(d), 6)  # max(window 3 + hold 3, 1 + horizon 5)
        wide = {
            **d,
            "plan": {**d["plan"], "execution_plan": {**PLAN, "entry_window": 3, "holding_days": 5}},
        }
        self.assertEqual(paper._span(wide), 8)
        self.assertEqual(paper._span({"plan": {}}), 6)


if __name__ == "__main__":
    unittest.main()
