"""LEARNER_v1 (idxsig.learner). Synthetic records only. Each test names the failure it guards against."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from idxsig import learner as ln
from idxsig import paper

T0 = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)


def cset(sid, family="FORM4_SHARP", top_exec=False, value=60_000.0, cutoff="2026-10-30T13:15:00Z", session="2026-10-29",
         cone=None, hash_="h"):
    cone = cone or [{"id": "BEATS_TWINS_60", "prior": 0.5}, {"id": "GAIN0_60", "prior": 0.5},
                    {"id": "MECH_SECOND_BUY_20", "prior": 0.5}]
    return {"type": "CATALYST_SET", "set_id": sid, "family": family, "record_hash": f"{hash_}{sid}", "entry_cutoff": cutoff,
            "signal_session": session, "direction": 1, "signal": {"close": 30.0, "adv20_value": 2e7, "volr": 1.0},
            "coverage": {"class": "FIRE", "rules": {}, "inputs": {"top_exec": top_exec, "total_value": value, "n_owners": 1}},
            "event": {}, "cone": cone}


def res(sid, outcomes, resolved_at, window="H60"):
    return {"type": "RESOLUTION", "set_id": sid, "window": window, "status": "RESOLVED", "resolved_at": resolved_at,
            "cone": [{"id": k, "prior": 0.5, "outcome": v} for k, v in outcomes.items()]}


def world(n=200, signal=True, resolved_at="2026-12-01T00:00:00Z"):
    """n resolved sets where top executives beat their twins and others do not (if signal)."""
    recs = []
    rng = np.random.default_rng(1)
    for i in range(n):
        te = bool(i % 2)
        beat = te if signal else bool(rng.integers(0, 2))
        recs.append(cset(f"S{i}", top_exec=te, session=f"2026-11-{1 + i % 28:02d}"))
        recs.append(res(f"S{i}", {"BEATS_TWINS_60": beat, "GAIN0_60": beat}, resolved_at))
    return recs


class Learning(unittest.TestCase):
    def test_with_no_outcomes_it_publishes_the_sealed_priors(self):
        """Guards against: a learner that is confident before it has seen a single result."""
        recs = [cset("A")]
        (f,) = ln.forecast_records(T0, recs, [])
        self.assertEqual(f["alpha"], 0.0)
        for v in f["forecasts"].values():
            self.assertAlmostEqual(v["raw"], v["prior"])
            self.assertAlmostEqual(v["published"], v["prior"])

    def test_it_learns_a_real_pattern_but_does_not_publish_it_until_earned(self):
        """Guards against: a pattern in the data not learned at all, or published with confidence the learner has not
        earned on forward forecasts."""
        recs = world(200) + [cset("NEW_TE", top_exec=True, cutoff="2026-12-02T13:15:00Z"),
                             cset("NEW_X", top_exec=False, cutoff="2026-12-02T13:15:00Z")]
        now = datetime(2026, 12, 2, 12, 0, tzinfo=timezone.utc)
        fs = {f["set_id"]: f for f in ln.forecast_records(now, recs, [])}
        te, x = fs["NEW_TE"]["forecasts"]["BEATS_TWINS_60"], fs["NEW_X"]["forecasts"]["BEATS_TWINS_60"]
        self.assertGreater(te["raw"], 0.65)  # heavy shrinkage (lambda 20): it moves, cautiously, on 200 outcomes
        self.assertLess(x["raw"], 0.35)
        self.assertEqual(fs["NEW_TE"]["alpha"], 0.0)  # no forward record yet
        self.assertAlmostEqual(te["published"], 0.5)

    def test_outcomes_resolved_after_the_forecast_are_never_used(self):
        """Guards against: peeking, the learner training on results that did not exist when it forecast."""
        recs = world(200, resolved_at="2026-12-05T00:00:00Z") + [cset("NEW", top_exec=True, cutoff="2026-12-02T13:15:00Z")]
        now = datetime(2026, 12, 2, 12, 0, tzinfo=timezone.utc)
        (f,) = [f for f in ln.forecast_records(now, recs, []) if f["set_id"] == "NEW"]
        self.assertEqual(f["trained"]["rows"], {})
        self.assertAlmostEqual(f["forecasts"]["BEATS_TWINS_60"]["raw"], 0.5)

    def test_confidence_is_earned_from_forward_skill_and_lost_without_it(self):
        """Guards against: alpha rising on luck, or on forecasts scored against outcomes known when they were made."""
        good = [{"prior": 0.5, "raw": 0.8 if y else 0.2, "published": 0.5, "y": float(y), "session": "s"} for y in [1, 0] * 150]
        a, info = ln.alpha_from(good)
        self.assertEqual(a, 1.0)
        self.assertGreater(info["skill"], 0.05)
        bad = [{**p, "raw": 1 - p["raw"]} for p in good]
        self.assertEqual(ln.alpha_from(bad)[0], 0.0)
        few = good[:30]
        self.assertAlmostEqual(ln.alpha_from(few)[0], 30 / 300)

    def test_triangulated_needs_both_the_catalyst_and_the_beat(self):
        """Guards against: a set credited as a catalyst call when the stock rose but the stated catalyst never came."""
        recs = [cset("A"), res("A", {"BEATS_TWINS_60": True}, "2026-12-20T00:00:00Z"),
                res("A", {"MECH_SECOND_BUY_20": False}, "2026-12-01T00:00:00Z", window="M20")]
        rows = ln.training_rows(recs, "2027-01-01T00:00:00Z")
        self.assertEqual([r[2] for r in rows[ln.TRI]], [0.0])
        self.assertAlmostEqual(rows[ln.TRI][0][1], ln._logit(0.25))
        recs[2]["cone"][0]["outcome"] = None
        self.assertNotIn(ln.TRI, ln.training_rows(recs, "2027-01-01T00:00:00Z"))

    def test_gains_are_split_into_earned_and_lucky(self):
        """Guards against: a rising market counted as the machine's skill."""
        recs = [cset("E"), res("E", {"GAIN0_60": True, "BEATS_TWINS_60": True}, "2026-12-01T00:00:00Z"),
                res("E", {"MECH_SECOND_BUY_20": True}, "2026-12-01T00:00:00Z", window="M20"),
                cset("M"), res("M", {"GAIN0_60": True, "BEATS_TWINS_60": False}, "2026-12-01T00:00:00Z"),
                res("M", {"MECH_SECOND_BUY_20": True}, "2026-12-01T00:00:00Z", window="M20"),
                cset("C"), res("C", {"GAIN0_60": True, "BEATS_TWINS_60": True}, "2026-12-01T00:00:00Z"),
                res("C", {"MECH_SECOND_BUY_20": False}, "2026-12-01T00:00:00Z", window="M20")]
        e = ln.earned_vs_lucky(recs, "2027-01-01T00:00:00Z")
        self.assertEqual((e["earned"], e["lucky"]), (1, 2))
        self.assertEqual(e["lucky_reasons"], {"market_or_sector_carried_it": 1, "stated_catalyst_never_came": 1})


class Timing(unittest.TestCase):
    def test_one_forecast_per_set_and_never_after_the_cutoff(self):
        """Guards against: a set forecast twice, or forecast once its entry price is already known."""
        recs = [cset("A"), cset("LATE", cutoff="2026-10-30T11:00:00Z")]
        fs = ln.forecast_records(T0, recs, [])
        self.assertEqual([f["set_id"] for f in fs], ["A"])
        self.assertEqual(ln.forecast_records(T0, recs, fs), [])


class Verify(unittest.TestCase):
    def test_late_forecasts_wrong_sets_and_peeking_are_caught(self):
        """Guards against: a forecast after the cutoff, bound to an edited set, or trained on later outcomes."""
        recs = world(60, resolved_at="2026-12-05T00:00:00Z") + [cset("A", cutoff="2026-12-10T13:15:00Z")]
        now = datetime(2026, 12, 10, 12, 0, tzinfo=timezone.utc)
        (good,) = [f for f in ln.forecast_records(now, recs, []) if f["set_id"] == "A"]
        late = {**good, "set_id": "S1", "set_record_hash": "hS1", "made_at": "2026-12-11T00:00:00Z"}
        wrong = {**good, "set_id": "S2", "set_record_hash": "not-the-hash"}
        peek = {**good, "set_id": "S3", "set_record_hash": "hS3", "made_at": "2026-12-01T00:00:00Z"}  # before the outcomes existed
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "learner.jsonl"
            paper.append([good, late, wrong, peek], path=path)
            joined = "\n".join(ln.verify(path, recs))
        self.assertNotIn("A:", joined)
        self.assertIn("S1: forecast made at", joined)
        self.assertIn("S2: forecast binds no sealed set", joined)
        self.assertIn("S3: weights do not reproduce", joined)


class Report(unittest.TestCase):
    def test_statistics_and_render_with_and_without_data(self):
        """Guards against: a report that crashes before the first outcome, or hides the earned-confidence level."""
        st = ln.statistics([], [], "2026-10-30T00:00:00Z")
        self.assertEqual((st["alpha"], st["forecasts"]), (0.0, 0))
        md = ln.render(st)
        self.assertIn("Earned confidence (alpha): 0.00", md)
        self.assertIn("accumulating", md)


if __name__ == "__main__":
    unittest.main()
