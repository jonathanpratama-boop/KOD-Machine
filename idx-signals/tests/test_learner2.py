"""LEARNER_v2 (idxsig.learner2). Synthetic records unless a test says otherwise. Each test names the failure it guards
against."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import numpy as np

from idxsig import learner2 as ln
from idxsig import paper

SHARP_CONE = [{"id": "BEATS_TWINS_60", "prior": 0.5, "resolves_with": "H60"},
              {"id": "GAIN0_60", "prior": 0.5, "resolves_with": "H60"},
              {"id": "BEATS_TWINS_20", "prior": 0.5, "resolves_with": "H20"},
              {"id": "RUN30_20", "prior": 0.5, "resolves_with": "H20"},
              {"id": "MECH_SECOND_BUY_20", "prior": 0.5, "resolves_with": "M20"}]
SEC13D_CONE = [{"id": "GAIN0_20", "prior": 0.55, "resolves_with": "H20"},
               {"id": "BEATS_TWINS_20", "prior": 0.5, "resolves_with": "H20"},
               {"id": "RUN30_20", "prior": 0.5, "resolves_with": "H20"}]


def cset(sid, family="FORM4_SHARP", top_exec=False, cutoff="2026-10-30T13:15:00Z", session="2026-10-29", ticker=None,
         direction=1, cone=None, parent=None, ret20=0.0, market="US"):
    s = {"type": "CATALYST_SET", "set_id": sid, "family": family, "market": market, "ticker": ticker or f"T{sid}",
         "record_hash": f"h{sid}", "entry_cutoff": cutoff, "signal_session": session, "direction": direction,
         "signal": {"close": 30.0, "adv20_value": 2e7, "volr": 1.0, "ret20": ret20, "cpos": 0.5},
         "coverage": {"class": "FIRE", "rules": {}, "inputs": {"top_exec": top_exec, "total_value": 60_000.0, "n_owners": 1}},
         "event": {}, "cone": cone or SHARP_CONE}
    if parent:
        s["parent"] = {"set_id": parent, "record_hash": f"h{parent}"}
    return s


def res(sid, outcomes, resolved_at, window="H60", family="FORM4_SHARP"):
    return {"type": "RESOLUTION", "set_id": sid, "family": family, "window": window, "status": "RESOLVED",
            "resolved_at": resolved_at, "cone": [{"id": k, "prior": 0.5, "outcome": v} for k, v in outcomes.items()]}


def world(n=200, signal=True, resolved_at="2026-12-01T00:00:00Z", seed=1):
    """n resolved FORM4_SHARP sets: top executives beat their twins and the others do not (if signal)."""
    rng = np.random.default_rng(seed)
    recs = []
    for i in range(n):
        te = bool(i % 2)
        beat = te if signal else bool(rng.integers(0, 2))
        recs.append(cset(f"S{i}", top_exec=te, session=f"2026-11-{1 + i % 28:02d}"))
        recs.append(res(f"S{i}", {"BEATS_TWINS_60": beat, "GAIN0_60": True}, resolved_at))
    return recs


NOW = datetime(2026, 12, 2, 12, 0, tzinfo=timezone.utc)


class NoHistory(unittest.TestCase):
    """Synthetic worlds without the warm start, so each test sees only its own records."""

    def setUp(self):
        p = mock.patch.object(ln, "history_rows", lambda: ())
        p.start()
        self.addCleanup(p.stop)


class Anchor(NoHistory):
    def test_with_no_outcomes_it_publishes_the_frozen_priors(self):
        """Guards against: a learner that is confident before it has seen a single result."""
        (f,) = ln.forecast_records(datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc), [cset("A")], [])
        for stmt, fc in f["forecasts"].items():
            self.assertAlmostEqual(fc["raw"], fc["p0"], places=6, msg=stmt)
            self.assertAlmostEqual(fc["published"], fc["p0"], places=6, msg=stmt)
            self.assertFalse((fc.get("call") or {}).get("side"))
        self.assertIn(ln.TRI, f["forecasts"])
        self.assertAlmostEqual(f["forecasts"][ln.TRI]["p0"], 0.25)

    def test_learning_a_base_rate_earns_no_skill(self):
        """Guards against v1's fake pass: a placeholder prior of 0.5 on a statement that is true 10% of the time, which
        a base-rate learner 'beats' without telling any two sets apart."""
        rng = np.random.default_rng(3)
        recs = []
        for i in range(300):
            recs.append(cset(f"S{i}", top_exec=bool(rng.integers(0, 2)), session=f"2026-11-{1 + i % 28:02d}"))
            recs.append(res(f"S{i}", {"MECH_SECOND_BUY_20": bool(rng.random() < 0.1)}, "2026-12-01T00:00:00Z",
                            window="M20"))
        recs += [cset(f"N{i}", top_exec=bool(i % 2), cutoff="2026-12-02T13:15:00Z") for i in range(20)]
        fs = [f for f in ln.forecast_records(NOW, recs, []) if f["set_id"].startswith("N")]
        anchor = fs[0]["forecasts"]["MECH_SECOND_BUY_20"]["anchor"]
        self.assertLess(anchor, 0.15)  # the anchor learned the base rate too
        for f in fs:
            fc = f["forecasts"]["MECH_SECOND_BUY_20"]
            self.assertAlmostEqual(fc["anchor"], anchor)
            self.assertLess(abs(fc["deviation"]), 0.2)  # no feature carries information: it barely moves
            self.assertIsNone(fc["call"]["side"])

    def test_absolute_statements_are_the_anchor_and_never_skill(self):
        """Guards against: credit for a stock that rose with the market (GAIN0, RUN30)."""
        recs = world(200) + [cset("NEW", top_exec=True, cutoff="2026-12-02T13:15:00Z")]
        (f,) = [f for f in ln.forecast_records(NOW, recs, []) if f["set_id"] == "NEW"]
        g = f["forecasts"]["GAIN0_60"]
        self.assertEqual(g["kind"], "ABSOLUTE")
        self.assertEqual((g["raw"], g["published"]), (g["anchor"], g["anchor"]))
        self.assertGreater(g["anchor"], 0.9)  # every GAIN0_60 came true: the anchor knows, and that is not skill
        later = recs + [res("NEW", {"GAIN0_60": True, "BEATS_TWINS_60": False}, "2027-03-01T00:00:00Z")]
        pairs = ln.forward_pairs(later, [f], "2027-03-02T00:00:00Z")
        self.assertEqual({p["statement"] for p in pairs}, {"BEATS_TWINS_60"})


class Learning(NoHistory):
    def test_it_learns_discrimination_but_does_not_publish_it_until_earned(self):
        """Guards against: a real pattern not learned at all, or published with confidence the learner has not earned."""
        recs = world(200) + [cset("TE", top_exec=True, cutoff="2026-12-02T13:15:00Z"),
                             cset("X", top_exec=False, cutoff="2026-12-02T13:15:00Z")]
        fs = {f["set_id"]: f for f in ln.forecast_records(NOW, recs, [])}
        te, x = fs["TE"]["forecasts"]["BEATS_TWINS_60"], fs["X"]["forecasts"]["BEATS_TWINS_60"]
        self.assertGreater(te["raw"], te["anchor"] + 0.1)
        self.assertLess(x["raw"], x["anchor"] - 0.1)
        self.assertAlmostEqual((te["raw"] + x["raw"]) / 2, te["anchor"], delta=0.03)  # centred: no base-rate channel
        self.assertEqual(fs["TE"]["gate"]["RELATIVE"]["alpha"], 0.0)  # no forward record yet
        self.assertAlmostEqual(te["published"], te["anchor"])
        self.assertEqual(te["call"], {"side": "BACK", "live": False})  # a shadow call, scored but not published
        self.assertEqual(x["call"], {"side": "AVOID", "live": False})
        self.assertEqual(te["why"][0]["feature"], "top_exec")

    def test_a_shift_between_history_and_the_live_sets_moves_no_forecast(self):
        """Guards against: a back door to base-rate credit. History where 20% of buyers are top executives and a slope
        that rewards them, then live sets that are all top executives: measured from history's average, every live
        forecast would move up together; measured from the live population, none moves."""
        rng = np.random.default_rng(5)
        hist = []
        for i in range(400):
            te = rng.random() < 0.2
            x = ln.features(cset(f"H{i}", top_exec=te))
            hist.append(ln.Row("RELATIVE", "FORM4_SHARP:BEATS_TWINS_60", "hist:test", x, 0.5,
                               float(rng.random() < (0.75 if te else 0.4)), 1.0))
        live = [cset(f"L{i}", top_exec=True, cutoff="2026-12-02T13:15:00Z") for i in range(10)]
        with mock.patch.object(ln, "history_rows", lambda: tuple(hist)):
            fs = ln.forecast_records(NOW, live, [])
            state = ln.train(live, "2026-12-02T12:00:00Z")
        self.assertGreater(state.models["RELATIVE"].deviation("FORM4_SHARP:BEATS_TWINS_60", ln.features(live[0]))[0], 0.1)
        devs = [f["forecasts"]["BEATS_TWINS_60"]["deviation"] for f in fs]
        self.assertTrue(all(abs(d) < 1e-9 for d in devs), devs)

    def test_outcomes_resolved_after_the_forecast_are_never_used(self):
        """Guards against: peeking, the learner training on results that did not exist when it forecast."""
        recs = world(200, resolved_at="2026-12-05T00:00:00Z") + [cset("NEW", top_exec=True, cutoff="2026-12-02T13:15:00Z")]
        (f,) = [f for f in ln.forecast_records(NOW, recs, []) if f["set_id"] == "NEW"]
        self.assertEqual(f["training"]["live_rows"], {})
        self.assertAlmostEqual(f["forecasts"]["BEATS_TWINS_60"]["raw"], 0.5)

    def test_a_parent_and_its_child_share_one_events_weight(self):
        """Guards against: one filing counted twice because two families sealed it."""
        recs = [cset("P", family="SEC13D", cone=SEC13D_CONE),
                cset("C", family="SEC13D_V2", parent="P", cone=SEC13D_CONE),
                res("P", {"BEATS_TWINS_20": True}, "2026-12-01T00:00:00Z", "H20", "SEC13D"),
                res("C", {"BEATS_TWINS_20": True}, "2026-12-01T00:00:00Z", "H20", "SEC13D_V2")]
        rows = [r for r in ln.live_rows(recs, "2027-01-01T00:00:00Z") if r.kind == "RELATIVE"]
        self.assertEqual(sorted(r.w for r in rows), [0.5, 0.5])

    def test_triangulated_needs_both_the_catalyst_and_the_beat(self):
        """Guards against: a catalyst call credited when the stock beat its twins but the stated catalyst never came."""
        recs = [cset("A"), res("A", {"BEATS_TWINS_60": True}, "2026-12-20T00:00:00Z"),
                res("A", {"MECH_SECOND_BUY_20": False}, "2026-12-01T00:00:00Z", window="M20")]
        tri = [r for r in ln.live_rows(recs, "2027-01-01T00:00:00Z") if r.kind == "TRIANGULATED"]
        self.assertEqual([(r.y, r.p0) for r in tri], [(0.0, 0.25)])
        recs[2]["cone"][0]["outcome"] = None
        self.assertFalse([r for r in ln.live_rows(recs, "2027-01-01T00:00:00Z") if r.kind == "TRIANGULATED"])


class Features(unittest.TestCase):
    def test_price_features_are_signed_by_the_calls_direction(self):
        """Guards against: a short call read as if the stock's fall were a move against it."""
        dil = cset("D", family="DILUTION_8K", direction=-1, ret20=-0.3)
        f = dict(zip(ln.FEATURES, ln.features(dil)))
        self.assertAlmostEqual(f["s_ret20"], 1.0)
        self.assertAlmostEqual(dict(zip(ln.FEATURES, ln.features(cset("L", ret20=-0.3))))["s_ret20"], -1.0)

    def test_triangulation_counts_only_earlier_events_on_the_same_issuer(self):
        """Guards against: a feature that knows about events sealed after the set."""
        recs = [cset("A", family="SEC13D", ticker="XYZ", session="2026-11-02", cone=SEC13D_CONE),
                cset("B", family="FORM4", ticker="XYZ", session="2026-11-20"),
                cset("C", family="DILUTION_8K", ticker="XYZ", session="2026-12-01", direction=-1),
                cset("D", family="FORM4_SHARP", ticker="XYZ", session="2026-11-20", parent="B"),
                cset("E", family="FORM4", ticker="XYZ", session="2027-06-01")]
        t = ln.tri_counts(recs)
        self.assertEqual(t["A"], (0, 0, 0))
        self.assertEqual(t["B"], (0, 1, 0))  # the 13D agrees
        self.assertEqual(t["C"], (0, 0, 2))  # two distinct long events disagree (B and its child D are one)
        self.assertEqual(t["D"], (0, 1, 0))  # its own parent is the same event, not a repeat
        self.assertEqual(t["E"], (0, 0, 0))  # outside 90 days


class Gate(unittest.TestCase):
    @staticmethod
    def pairs(q, n, seed, start=0):
        rng = np.random.default_rng(seed)
        out = []
        for i in range(n):
            y = float(rng.integers(0, 2))
            right = rng.random() < q
            out.append({"kind": "RELATIVE", "session": f"s{start + i:05d}", "window": "H20", "event_key": f"e{start + i}",
                        "statement": "BEATS_TWINS_20",
                        "resolved_at": f"2027-{start + i:05d}", "w": 1.0, "y": y, "anchor": 0.5,
                        "raw": 0.5 + (0.1 if right else -0.1) * (2 * y - 1)})
        return out

    def test_luck_rarely_opens_the_gate_even_when_checked_every_time(self):
        """Guards against: confidence from a lucky streak, the risk of a gate checked daily for years."""
        opened = 0
        for seed in range(40):
            ps = self.pairs(0.55, 400, seed)  # zero true skill: the mean Brier gain is 0
            opened += any(ln.gate(ps[:t], "RELATIVE")[0] > 0 for t in range(30, 401, 5))
        self.assertLessEqual(opened, 4)

    def test_real_skill_opens_it_and_losing_the_skill_closes_it(self):
        """Guards against: a gate that never opens, or stays open after the edge is gone."""
        opened = sum(ln.gate(self.pairs(0.65, 400, seed), "RELATIVE")[0] > 0 for seed in range(20))
        self.assertGreaterEqual(opened, 14)
        ps = self.pairs(0.65, 400, 7) + self.pairs(0.45, 150, 8, start=400)
        self.assertEqual(ln.gate(ps, "RELATIVE")[0], 0.0)

    def test_an_observation_never_changes_once_it_exists(self):
        """Guards against: a recorded observation re-weighted when the same filing's other set resolves later, which
        would rewrite the sequence the confidence bound assumes is fixed."""
        a = {"kind": "RELATIVE", "session": "s1", "window": "H20", "event_key": "E", "statement": "BEATS_TWINS_20",
             "resolved_at": "2027-01-05T00:00:00Z", "y": 1.0, "anchor": 0.5, "raw": 0.7}
        b = {**a, "event_key": "F", "raw": 0.4, "y": 0.0}
        first = ln.observations([a, b])
        late = {**a, "resolved_at": "2027-01-09T00:00:00Z", "raw": 0.2}  # E's other set, resolved later
        self.assertEqual(ln.observations([a, b, late])[0], first[0])
        self.assertEqual(len(ln.observations([a, b, late])), 2)
        same = {**a, "raw": 0.2}  # resolved together: one event, weighted once inside the observation
        (o,) = ln.observations([a, same])
        self.assertAlmostEqual(o[0], ((0.25 - 0.09) + (0.25 - 0.64)) / 2)

    def test_below_thirty_observations_it_stays_shut(self):
        self.assertEqual(ln.gate(self.pairs(1.0, 29, 1), "RELATIVE")[0], 0.0)


class EndToEnd(NoHistory):
    @staticmethod
    def run_world(skill, days=110, per_day=4, seed=0):
        """Sets sealed every weekday, forecast before entry, resolved 28 days later; returns the statistics."""
        from datetime import timedelta
        cone = [{"id": "BEATS_TWINS_20", "prior": 0.5, "resolves_with": "H20"},
                {"id": "GAIN0_20", "prior": 0.5, "resolves_with": "H20"}]
        rng = np.random.default_rng(seed)
        recs, lrecs, pending = [], [], []
        start = datetime(2027, 1, 4, tzinfo=timezone.utc)
        for d in range(days):
            day = start + timedelta(days=d)
            if day.weekday() >= 5:
                continue
            sess = day.date().isoformat()
            for k in range(per_day):
                te = bool(rng.random() < 0.5)
                s = cset(f"{sess}-{k}", family="FORM4", top_exec=te, session=sess, cone=cone,
                         cutoff=(day + timedelta(days=1)).strftime("%Y-%m-%dT13:15:00Z"))
                s["sealed_at"] = f"{sess}T23:00:00Z"
                recs.append(s)
                pending.append((day + timedelta(days=28), s["set_id"], bool(rng.random() < 0.5 + (skill if te else -skill)),
                                bool(rng.random() < 0.7)))
            now = day + timedelta(hours=23, minutes=30)
            recs += [res(sid, {"BEATS_TWINS_20": beat, "GAIN0_20": gain}, due.strftime("%Y-%m-%dT10:00:00Z"), "H20", "FORM4")
                     for due, sid, beat, gain in pending if due <= now]
            pending = [x for x in pending if x[0] > now]
            lrecs += ln.forecast_records(now, recs, lrecs)
        return ln.statistics(recs, lrecs, (start + timedelta(days=days + 1)).strftime("%Y-%m-%dT00:00:00Z"))

    def test_the_loop_rewards_real_discrimination_and_nothing_else(self):
        """Guards against: a learner whose sealed forecasts, resolutions and scoring do not join up, or that is credited
        in a world where nothing predicts the outcome (while every stock rose 70% of the time)."""
        skilled, blind = self.run_world(0.15), self.run_world(0.0)
        self.assertGreaterEqual(skilled["gates"]["RELATIVE"][1]["observations"], 30)
        bt = skilled["per_statement"]["FORM4:BEATS_TWINS_20"]
        self.assertLess(bt["brier_raw"], bt["brier_anchor"])
        self.assertGreater(skilled["claim"]["t"], 1.5)
        self.assertEqual(skilled["calls"], {})  # 240 outcomes: it leans the right way but is not yet sure enough to call
        self.assertEqual(blind["gates"]["RELATIVE"][0], 0.0)
        self.assertLess(abs(blind["claim"]["t"]), 2.0)
        self.assertEqual({k.split(":")[1] for k in blind["per_statement"]}, {"BEATS_TWINS_20"})  # GAIN0 never scored


class Calls(unittest.TestCase):
    def test_calls_need_a_margin_and_certainty_and_go_live_only_with_earned_confidence(self):
        """Guards against: a call made on a lean, or published before the learner has earned it."""
        self.assertEqual(ln.call_of(0.6, 0.2, 0.0), {"side": "BACK", "live": False})
        self.assertEqual(ln.call_of(0.6, 0.2, 1.0), {"side": "BACK", "live": True})
        self.assertEqual(ln.call_of(0.6, 0.5, 1.0), {"side": None, "live": False})  # not sure enough
        self.assertEqual(ln.call_of(0.3, 0.01, 1.0), {"side": None, "live": False})  # not far enough
        self.assertEqual(ln.call_of(-0.6, 0.2, 0.5), {"side": "AVOID", "live": False})  # published move 0.3 < margin


class History(unittest.TestCase):
    def test_the_warm_start_is_pinned_pre_2024_and_capped(self):
        """Guards against: a warm start that was swapped, reaches the sealed holdout, or outweighs the live record."""
        build = json.loads((ln.HISTORY.parent / "BUILD.json").read_text())
        self.assertEqual(build["events_csv_gz"], ln.HISTORY_SHA256)
        self.assertLess(build["signal_dates"][1], "2024-01-01")
        rows = ln.history_rows()
        for k in ln.SKILL_KINDS:
            self.assertLessEqual(sum(r.w for r in rows if r.kind == k), ln.N_CAP + 1e-6)
        self.assertTrue(all(r.icpt.startswith("hist:") for r in rows))  # its own intercepts: never the live anchor
        with mock.patch.object(ln, "HISTORY_SHA256", "0" * 64):
            ln.history_rows.cache_clear()
            with self.assertRaises(RuntimeError):
                ln.history_rows()
        ln.history_rows.cache_clear()

    def test_protocol_numbers_are_the_modules(self):
        """Guards against: the code and the frozen protocol drifting apart."""
        p, _ = ln.protocol()
        m = p["model"]
        self.assertEqual(p["warm_start"]["sha256"], ln.HISTORY_SHA256)
        self.assertEqual(p["warm_start"]["weight_cap"], ln.N_CAP)
        self.assertEqual(m["features"], list(ln.FEATURES))
        self.assertEqual((m["lambda_shared"], m["lambda_task"], m["lambda_own"]),
                         (ln.LAMBDA_SHARED, ln.LAMBDA_TASK, ln.LAMBDA_OWN))
        self.assertAlmostEqual(m["intercept_prior_sd"], 1.5)
        self.assertEqual(p["earned_confidence"]["numbers"], ln.GATE)
        self.assertEqual(p["calls"]["numbers"], ln.CALL)
        self.assertEqual(p["triangles"], {k: list(v) for k, v in ln.TRIANGLES.items()})


class Verify(NoHistory):
    def test_late_forecasts_wrong_sets_and_peeking_are_caught(self):
        """Guards against: a forecast after the cutoff, bound to an edited set, or trained on later outcomes."""
        recs = world(60, resolved_at="2026-12-05T00:00:00Z") + [cset("A", cutoff="2026-12-10T13:15:00Z", top_exec=True)]
        now = datetime(2026, 12, 10, 12, 0, tzinfo=timezone.utc)
        (good,) = [f for f in ln.forecast_records(now, recs, []) if f["set_id"] == "A"]
        late = {**good, "set_id": "S1", "set_record_hash": "hS1", "made_at": "2026-12-11T00:00:00Z"}
        wrong = {**good, "set_id": "S2", "set_record_hash": "not-the-hash"}
        peek = {**good, "set_id": "S3", "set_record_hash": "hS3", "made_at": "2026-12-01T00:00:00Z"}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "learner_v2.jsonl"
            paper.append([good, late, wrong, peek], path=path)
            joined = "\n".join(ln.verify(path, recs))
        self.assertNotIn("A:", joined)
        self.assertIn("S1: forecast made at", joined)
        self.assertIn("S2: forecast binds no sealed set", joined)
        self.assertIn("S3: forecasts do not reproduce", joined)

    def test_an_edited_number_is_caught(self):
        """Guards against: a sealed forecast whose numbers were changed afterwards to look better."""
        recs = world(60) + [cset("A", cutoff="2026-12-10T13:15:00Z", top_exec=True)]
        now = datetime(2026, 12, 10, 12, 0, tzinfo=timezone.utc)
        (f,) = [f for f in ln.forecast_records(now, recs, []) if f["set_id"] == "A"]
        f["forecasts"]["BEATS_TWINS_60"]["raw"] += 0.01
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "learner_v2.jsonl"
            paper.append([f], path=path)
            self.assertIn("A: forecasts do not reproduce", "\n".join(ln.verify(path, recs)))


class Report(NoHistory):
    def test_statistics_and_render_with_and_without_data(self):
        """Guards against: a report that crashes before the first outcome, or hides the earned-confidence level."""
        st = ln.statistics([], [], "2026-10-30T00:00:00Z")
        self.assertEqual((st["forecasts"], st["pairs"]), (0, 0))
        md = ln.render(st)
        self.assertIn("| RELATIVE | 0.00 |", md)
        self.assertIn("accumulating", md)
        recs = world(80) + [cset("A", cutoff="2026-12-10T13:15:00Z", top_exec=True)]
        (f,) = [f for f in ln.forecast_records(datetime(2026, 12, 10, 12, 0, tzinfo=timezone.utc), recs, [])
                if f["set_id"] == "A"]
        recs += [res("A", {"BEATS_TWINS_60": True, "GAIN0_60": True}, "2027-03-01T00:00:00Z")]
        st = ln.statistics(recs, [f], "2027-03-02T00:00:00Z")
        self.assertEqual(st["pairs"], 1)
        self.assertIn("shadow_BACK", st["calls"])
        self.assertIn("What it believes now", ln.render(st))


if __name__ == "__main__":
    unittest.main()
