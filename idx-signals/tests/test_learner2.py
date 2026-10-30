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

SHARP_CONE = [
    {"id": "BEATS_TWINS_60", "prior": 0.5, "resolves_with": "H60"},
    {"id": "GAIN0_60", "prior": 0.5, "resolves_with": "H60"},
    {"id": "BEATS_TWINS_20", "prior": 0.5, "resolves_with": "H20"},
    {"id": "RUN30_20", "prior": 0.5, "resolves_with": "H20"},
    {"id": "MECH_SECOND_BUY_20", "prior": 0.5, "resolves_with": "M20"},
]
SEC13D_CONE = [
    {"id": "GAIN0_20", "prior": 0.55, "resolves_with": "H20"},
    {"id": "BEATS_TWINS_20", "prior": 0.5, "resolves_with": "H20"},
    {"id": "FADE10_20", "prior": 0.5, "resolves_with": "H20"},
    {"id": "RUN30_20", "prior": 0.5, "resolves_with": "H20"},
]


def cset(
    sid,
    family="FORM4_SHARP",
    top_exec=False,
    cutoff="2026-10-30T13:15:00Z",
    session="2026-10-29",
    ticker=None,
    direction=1,
    cone=None,
    parent=None,
    ret20=0.0,
    market="US",
):
    s = {
        "type": "CATALYST_SET",
        "set_id": sid,
        "family": family,
        "market": market,
        "ticker": ticker or f"T{sid}",
        "record_hash": f"h{sid}",
        "entry_cutoff": cutoff,
        "signal_session": session,
        "direction": direction,
        "signal": {"close": 30.0, "adv20_value": 2e7, "volr": 1.0, "ret20": ret20, "cpos": 0.5},
        "coverage": {
            "class": "FIRE",
            "rules": {},
            "inputs": {"top_exec": top_exec, "total_value": 60_000.0, "n_owners": 1},
        },
        "event": {},
        "cone": cone or SHARP_CONE,
    }
    if parent:
        s["parent"] = {"set_id": parent, "record_hash": f"h{parent}"}
    return s


def res(sid, outcomes, resolved_at, window="H60", family="FORM4_SHARP"):
    return {
        "type": "RESOLUTION",
        "set_id": sid,
        "family": family,
        "window": window,
        "status": "RESOLVED",
        "resolved_at": resolved_at,
        "cone": [{"id": k, "prior": 0.5, "outcome": v} for k, v in outcomes.items()],
    }


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
        (f,) = ln.forecast_records(
            datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc), [cset("A")], []
        )
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
            recs.append(
                cset(
                    f"S{i}", top_exec=bool(rng.integers(0, 2)), session=f"2026-11-{1 + i % 28:02d}"
                )
            )
            recs.append(
                res(
                    f"S{i}",
                    {"MECH_SECOND_BUY_20": bool(rng.random() < 0.1)},
                    "2026-12-01T00:00:00Z",
                    window="M20",
                )
            )
        recs += [
            cset(f"N{i}", top_exec=bool(i % 2), cutoff="2026-12-02T13:15:00Z") for i in range(20)
        ]
        fs = [f for f in ln.forecast_records(NOW, recs, []) if f["set_id"].startswith("N")]
        anchor = fs[0]["forecasts"]["MECH_SECOND_BUY_20"]["anchor"]
        self.assertLess(anchor, 0.15)  # the anchor learned the base rate too
        for f in fs:
            fc = f["forecasts"]["MECH_SECOND_BUY_20"]
            self.assertAlmostEqual(fc["anchor"], anchor)
            self.assertLess(
                abs(fc["deviation"]), 0.2
            )  # no feature carries information: it barely moves
            self.assertIsNone(fc["call"]["side"])

    def test_absolute_statements_are_the_anchor_and_never_skill(self):
        """Guards against: credit for a stock that rose with the market (GAIN0, RUN30)."""
        recs = world(200) + [cset("NEW", top_exec=True, cutoff="2026-12-02T13:15:00Z")]
        (f,) = [f for f in ln.forecast_records(NOW, recs, []) if f["set_id"] == "NEW"]
        g = f["forecasts"]["GAIN0_60"]
        self.assertEqual(g["kind"], "ABSOLUTE")
        self.assertEqual((g["raw"], g["published"]), (g["anchor"], g["anchor"]))
        self.assertGreater(
            g["anchor"], 0.9
        )  # every GAIN0_60 came true: the anchor knows, and that is not skill
        later = recs + [
            res("NEW", {"GAIN0_60": True, "BEATS_TWINS_60": False}, "2027-03-01T00:00:00Z")
        ]
        pairs = ln.forward_pairs(later, [f], "2027-03-02T00:00:00Z")
        self.assertEqual({p["statement"] for p in pairs}, {"BEATS_TWINS_60"})


class Learning(NoHistory):
    def test_it_learns_discrimination_but_does_not_publish_it_until_earned(self):
        """Guards against: a real pattern not learned at all, or published with confidence the learner has not earned."""
        recs = world(200) + [
            cset("TE", top_exec=True, cutoff="2026-12-02T13:15:00Z"),
            cset("X", top_exec=False, cutoff="2026-12-02T13:15:00Z"),
        ]
        fs = {f["set_id"]: f for f in ln.forecast_records(NOW, recs, [])}
        te, x = fs["TE"]["forecasts"]["BEATS_TWINS_60"], fs["X"]["forecasts"]["BEATS_TWINS_60"]
        self.assertGreater(te["raw"], te["anchor"] + 0.1)
        self.assertLess(x["raw"], x["anchor"] - 0.1)
        self.assertAlmostEqual(
            (te["raw"] + x["raw"]) / 2, te["anchor"], delta=0.03
        )  # centred: no base-rate channel
        self.assertEqual(fs["TE"]["gate"]["RELATIVE/60"]["alpha"], 0.0)  # no forward record yet
        self.assertAlmostEqual(te["published"], te["anchor"])
        self.assertEqual(
            te["call"],
            {
                "side": "BACK",
                "live": False,  # a shadow call, scored but not published
                "thesis": "it beats its twins over 60 sessions",
            },
        )
        self.assertEqual(
            x["call"],
            {"side": "AVOID", "live": False, "thesis": "not: it beats its twins over 60 sessions"},
        )
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
            hist.append(
                ln.Row(
                    "RELATIVE",
                    "FORM4_SHARP:BEATS_TWINS_60",
                    "hist:test",
                    x,
                    0.5,
                    float(rng.random() < (0.75 if te else 0.4)),
                    1.0,
                )
            )
        live = [cset(f"L{i}", top_exec=True, cutoff="2026-12-02T13:15:00Z") for i in range(10)]
        with mock.patch.object(ln, "history_rows", lambda: tuple(hist)):
            fs = ln.forecast_records(NOW, live, [])
            state = ln.train(live, "2026-12-02T12:00:00Z")
        self.assertGreater(
            state.models["RELATIVE"].deviation("FORM4_SHARP:BEATS_TWINS_60", ln.features(live[0]))[
                0
            ],
            0.1,
        )
        devs = [f["forecasts"]["BEATS_TWINS_60"]["deviation"] for f in fs]
        self.assertTrue(all(abs(d) < 1e-9 for d in devs), devs)

    def test_outcomes_resolved_after_the_forecast_are_never_used(self):
        """Guards against: peeking, the learner training on results that did not exist when it forecast."""
        recs = world(200, resolved_at="2026-12-05T00:00:00Z") + [
            cset("NEW", top_exec=True, cutoff="2026-12-02T13:15:00Z")
        ]
        (f,) = [f for f in ln.forecast_records(NOW, recs, []) if f["set_id"] == "NEW"]
        self.assertEqual(f["training"]["live_rows"], {})
        self.assertAlmostEqual(f["forecasts"]["BEATS_TWINS_60"]["raw"], 0.5)

    def test_a_parent_and_its_child_share_one_events_weight(self):
        """Guards against: one filing counted twice because two families sealed it."""
        recs = [
            cset("P", family="SEC13D", cone=SEC13D_CONE),
            cset("C", family="SEC13D_V2", parent="P", cone=SEC13D_CONE),
            res("P", {"BEATS_TWINS_20": True}, "2026-12-01T00:00:00Z", "H20", "SEC13D"),
            res("C", {"BEATS_TWINS_20": True}, "2026-12-01T00:00:00Z", "H20", "SEC13D_V2"),
        ]
        rows = [r for r in ln.live_rows(recs, "2027-01-01T00:00:00Z") if r.kind == "RELATIVE"]
        self.assertEqual(sorted(r.w for r in rows), [0.5, 0.5])

    def test_triangulated_needs_both_the_catalyst_and_the_beat(self):
        """Guards against: a catalyst call credited when the stock beat its twins but the stated catalyst never came."""
        recs = [
            cset("A"),
            res("A", {"BEATS_TWINS_60": True}, "2026-12-20T00:00:00Z"),
            res("A", {"MECH_SECOND_BUY_20": False}, "2026-12-01T00:00:00Z", window="M20"),
        ]
        tri = [r for r in ln.live_rows(recs, "2027-01-01T00:00:00Z") if r.kind == "TRIANGULATED"]
        self.assertEqual([(r.y, r.p0) for r in tri], [(0.0, 0.25)])
        recs[2]["cone"][0]["outcome"] = None
        self.assertFalse(
            [r for r in ln.live_rows(recs, "2027-01-01T00:00:00Z") if r.kind == "TRIANGULATED"]
        )


SPEC_CONE = [
    {"id": "RUN30_5", "prior": 0.15, "resolves_with": "BASE5"},
    {"id": "FADE10_5", "prior": 0.4, "resolves_with": "BASE5"},
    {"id": "GAIN0_5", "prior": 0.43, "resolves_with": "BASE5"},
    {"id": "BEATS_TWINS_5", "prior": 0.5, "resolves_with": "BASE5"},
    {"id": "RUN30_20", "prior": 0.5, "resolves_with": "PATH20"},
    {"id": "DOUBLE_20", "prior": 0.5, "resolves_with": "PATH20"},
]


def move(sid, run, run_twins, fade, fade_twins, at="2026-12-01T00:00:00Z", k=5, window="BASE5"):
    return {
        "type": "RESOLUTION",
        "set_id": sid,
        "window": window,
        "status": "RESOLVED",
        "resolved_at": at,
        "cone": [
            {"id": f"RUN30_{k}", "prior": 0.5, "outcome": run, "twins_rate": run_twins},
            {"id": f"FADE10_{k}", "prior": 0.5, "outcome": fade, "twins_rate": fade_twins},
        ],
    }


class Moves(NoHistory):
    """v2.1: the owner's "I just care if it gets it right, and its thesis on even a pump and dump or whatnot is
    right"."""

    def test_a_move_counts_only_when_most_of_the_twins_did_not_make_it(self):
        """Guards against: a pump the market made credited to the machine."""
        outc = ln.outcomes(
            [
                move("A", True, 0.1, False, 0.0),
                move("B", True, 0.6, False, 0.0),
                move("C", False, None, False, None),
                move("D", True, None, True, 0.2),
            ],
            "2027-01-01T00:00:00Z",
        )
        get = lambda sid, st: (ln.outcome_of(outc, sid, "SPEC_US", st) or (None,))[0]  # noqa: E731
        self.assertEqual([get(x, "PUMP30_5") for x in "ABCD"], [True, False, False, None])
        self.assertEqual([get(x, "DUMP10_5") for x in "ABCD"], [False, False, False, True])

    def test_a_pump_and_dump_needs_both_moves_to_be_its_own(self):
        """Guards against: a half-right thesis (it pumped but never dumped, or the dump was a market sell-off) counted
        as a correct pump-and-dump call."""
        outc = ln.outcomes(
            [
                move("A", True, 0.1, True, 0.2),
                move("B", True, 0.1, False, 0.0),
                move("C", True, 0.1, True, 0.7),
            ],
            "2027-01-01T00:00:00Z",
        )
        self.assertEqual(
            [ln.outcome_of(outc, x, "SPEC_US", "PUMP_AND_DUMP_5")[0] for x in "ABC"],
            [True, False, False],
        )

    def test_raw_moves_get_the_anchor_and_their_own_versions_are_learned(self):
        """Guards against: the raw RUN30/FADE10 (which a market-wide move makes true) scored as skill, or the pump and
        dump statements left out."""
        st = dict(ln.statements(cset("P", family="SEC13D", cone=SEC13D_CONE)))
        self.assertEqual(st["PUMP30_20"], "H20")
        self.assertIn("DUMP10_20", st)
        self.assertEqual(st["PUMP_AND_DUMP_20"], "H20")
        self.assertEqual(
            (ln.kind_of("RUN30_20"), ln.kind_of("PUMP30_20"), ln.kind_of("PUMP_AND_DUMP_5")),
            (None, "PATH", "PATH"),
        )

    def test_speculation_sets_are_forecast_with_their_frozen_priors(self):
        """Guards against: the Speculation Register's movers (where pumps and dumps happen) left out, or priors made
        up for them."""
        raw = {
            "type": "SPECULATION_SET",
            "set_id": "SPEC-SCAN-US-X",
            "market": "US",
            "ticker": "XYZ",
            "record_hash": "hX",
            "entry_cutoff": "2026-10-30T13:30:00Z",
            "signal_session": "2026-10-29",
            "sealed_at": "2026-10-29T23:00:00Z",
            "signal": {"close": 5.0, "adv20_value": 1e6, "volr": 20.0, "ret1": 0.4, "cpos": 0.9},
            "cone": SPEC_CONE,
            "twins": [],
        }
        s = ln.as_set(raw)
        self.assertEqual((s["type"], s["family"], s["direction"]), ("CATALYST_SET", "SPEC_US", 1))
        (f,) = ln.forecast_records(datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc), [s], [])
        fc = f["forecasts"]
        self.assertAlmostEqual(
            fc["PUMP30_5"]["p0"], round(0.15370018975332067, 6)
        )  # the protocol's US number
        self.assertAlmostEqual(fc["PUMP_AND_DUMP_5"]["p0"], round(0.15370018975332067 * 0.403, 6))
        self.assertAlmostEqual(fc["PUMP100_20"]["p0"], 0.5)  # DOUBLE_20 is "running"
        self.assertEqual(
            {k for k, v in fc.items() if v["kind"] == "PATH"},
            {"PUMP30_5", "DUMP10_5", "PUMP30_20", "PUMP100_20", "PUMP_AND_DUMP_5"},
        )

    def test_a_short_calls_moves_are_read_on_the_price(self):
        """Guards against: a stock that fell read as having moved 'up' for a pump statement because the call was short."""
        x = ln.features(cset("D", family="DILUTION_8K", direction=-1, ret20=-0.3))
        i = ln.FEATURES.index("s_ret20")
        self.assertAlmostEqual(ln.view(x, "RELATIVE", -1)[i], 1.0)  # in the call's direction
        self.assertAlmostEqual(ln.view(x, "PATH", -1)[i], -1.0)  # on the price

    def test_one_pump_model_is_shared_across_families_and_horizons(self):
        """Guards against: what the machine learns about pumps in one register not reaching the other."""
        rows = [
            ln.Row(
                "PATH",
                "SEC13D:PUMP30_20",
                "SEC13D:PUMP30_20",
                np.eye(len(ln.FEATURES))[i % 3],
                0.1,
                float(i % 3 == 0),
                1.0,
            )
            for i in range(90)
        ]
        m = ln.Model("PATH", rows)
        self.assertEqual(m.groups, ["PUMP"])
        w, _ = m.slope("SPEC_US:PUMP30_5")  # never seen: it inherits the shared PUMP block
        self.assertGreater(float(np.abs(w).sum()), 0.0)
        self.assertEqual(
            float(np.abs(m.slope("SPEC_US:DUMP10_5")[0]).sum()), 0.0
        )  # a different move: nothing

    def test_theses_are_graded_in_full(self):
        """Guards against: a call credited when only part of its thesis came true, or when the market made the move."""
        full = ln.outcomes(
            [
                move("A", True, 0.1, False, 0.0),
                move("B", True, 0.8, False, 0.0),
                move("C", True, 0.1, True, 0.1),
            ],
            "2027-01-01T00:00:00Z",
        )
        pd_ = {"statement": "PUMP_AND_DUMP_5", "family": "SPEC_US"}
        self.assertEqual(
            ln.thesis_grade(full, {**pd_, "set_id": "A", "y": 0.0}, "BACK"), "partly"
        )  # pumped, no dump
        self.assertEqual(ln.thesis_grade(full, {**pd_, "set_id": "C", "y": 1.0}, "BACK"), "right")
        pump = {"statement": "PUMP30_5", "family": "SPEC_US"}
        self.assertEqual(
            ln.thesis_grade(full, {**pump, "set_id": "B", "y": 0.0}, "BACK"), "market_made_it"
        )
        self.assertEqual(ln.thesis_grade(full, {**pump, "set_id": "A", "y": 1.0}, "AVOID"), "wrong")
        self.assertEqual(ln.thesis("PUMP_AND_DUMP_5", "BACK")[:16], "a pump and dump:")
        self.assertEqual(
            ln.thesis("DUMP10_5", "AVOID"),
            "not: its 5-session plan loses at least 10%, and most of its twins do not",
        )


class Hygiene(NoHistory):
    def test_a_revision_replaces_what_it_revises(self):
        """Guards against the review's finding: an UNRESOLVABLE or ungraded revision leaving the stale outcome in."""
        first = res("A", {"BEATS_TWINS_60": True}, "2026-12-01T00:00:00Z")
        bad = {
            "type": "RESOLUTION",
            "set_id": "A",
            "window": "H60",
            "status": "UNRESOLVABLE",
            "resolved_at": "2026-12-02T00:00:00Z",
        }
        self.assertIn(("A", "BEATS_TWINS_60"), ln.outcomes([first], "2027-01-01T00:00:00Z"))
        self.assertNotIn(("A", "BEATS_TWINS_60"), ln.outcomes([first, bad], "2027-01-01T00:00:00Z"))

    def test_only_valid_forecasts_are_scored(self):
        """Guards against the review's finding: duplicate, late or unbound forecasts counted in the gate and claim."""
        recs = world(60) + [cset("A", cutoff="2026-12-10T13:15:00Z", top_exec=True)]
        (f,) = [
            f
            for f in ln.forecast_records(
                datetime(2026, 12, 10, 12, 0, tzinfo=timezone.utc), recs, []
            )
            if f["set_id"] == "A"
        ]
        later = recs + [
            res("A", {"BEATS_TWINS_60": True, "GAIN0_60": True}, "2027-03-01T00:00:00Z")
        ]
        late = {**f, "made_at": "2026-12-11T00:00:00Z"}
        unbound = {**f, "set_record_hash": "x"}
        for extra in ([f, f], [late], [unbound]):
            n = len(
                [
                    p
                    for p in ln.forward_pairs(later, extra, "2027-03-02T00:00:00Z")
                    if p["statement"] == "BEATS_TWINS_60"
                ]
            )
            self.assertEqual(n, 1 if extra == [f, f] else 0)

    def test_newton_converges_far_from_the_prior(self):
        """Guards against the review's finding: undamped Newton stuck at a prior far from the data."""
        for p0, y in ((0.99, 0.0), (0.05, 1.0)):
            rows = [ln.Row("ABSOLUTE", "T:X", "T:X", np.zeros(3), p0, y, 1.0) for _ in range(200)]
            p = float(ln._sigmoid(ln._logit(p0) + ln.anchor_fit(rows)))
            self.assertLess(abs(p - y), 0.05)

    def test_earlier_means_sealed_earlier_across_both_registers(self):
        """Guards against the review's finding: a speculation set counted as earlier than a catalyst set it followed."""
        a = cset("A", family="SEC13D", ticker="XYZ", session="2026-11-02", cone=SEC13D_CONE)
        a["sealed_at"] = "2026-11-03T00:00:00Z"
        b = ln.as_set(
            {
                "type": "SPECULATION_SET",
                "set_id": "SPEC-B",
                "market": "US",
                "ticker": "XYZ",
                "record_hash": "hB",
                "signal_session": "2026-11-01",
                "sealed_at": "2026-11-02T00:00:00Z",
                "entry_cutoff": "2026-11-02T13:30:00Z",
                "signal": {},
                "cone": SPEC_CONE,
            }
        )
        t = ln.tri_counts([a, b])  # the catalyst ledger first, as all_records() reads them
        self.assertEqual((t["SPEC-B"], t["A"]), ((0, 0, 0), (0, 1, 0)))


class Features(unittest.TestCase):
    def test_price_features_are_signed_by_the_calls_direction(self):
        """Guards against: a short call read as if the stock's fall were a move against it."""
        dil = cset("D", family="DILUTION_8K", direction=-1, ret20=-0.3)
        f = dict(zip(ln.FEATURES, ln.features(dil)))
        self.assertAlmostEqual(f["s_ret20"], 1.0)
        self.assertAlmostEqual(
            dict(zip(ln.FEATURES, ln.features(cset("L", ret20=-0.3))))["s_ret20"], -1.0
        )

    def test_triangulation_counts_only_earlier_events_on_the_same_issuer(self):
        """Guards against: a feature that knows about events sealed after the set."""
        recs = [
            cset("A", family="SEC13D", ticker="XYZ", session="2026-11-02", cone=SEC13D_CONE),
            cset("B", family="FORM4", ticker="XYZ", session="2026-11-20"),
            cset("C", family="DILUTION_8K", ticker="XYZ", session="2026-12-01", direction=-1),
            cset("D", family="FORM4_SHARP", ticker="XYZ", session="2026-11-20", parent="B"),
            cset("E", family="FORM4", ticker="XYZ", session="2027-06-01"),
        ]
        t = ln.tri_counts(recs)
        self.assertEqual(t["A"], (0, 0, 0))
        self.assertEqual(t["B"], (0, 1, 0))  # the 13D agrees
        self.assertEqual(
            t["C"], (0, 0, 2)
        )  # two distinct long events disagree (B and its child D are one)
        self.assertEqual(t["D"], (0, 1, 0))  # its own parent is the same event, not a repeat
        self.assertEqual(t["E"], (0, 0, 0))  # outside 90 days


class Gate(unittest.TestCase):
    ASOF = "2099-01-05T00:00:00Z"

    @staticmethod
    def pairs(q, n, seed, start=0):
        """One forward pair resolving in each of n consecutive weeks; right with probability q (q 0.55 is no skill)."""
        from datetime import date, timedelta

        rng = np.random.default_rng(seed)
        out = []
        for i in range(n):
            y, right = float(rng.integers(0, 2)), rng.random() < q
            day = date(2027, 1, 6) + timedelta(weeks=start + i)
            out.append(
                {
                    "kind": "RELATIVE",
                    "session": day.isoformat(),
                    "window": "H20",
                    "event_key": f"e{start + i}",
                    "statement": "BEATS_TWINS_20",
                    "set_id": f"s{start + i}",
                    "resolved_at": f"{day.isoformat()}T10:00:00Z",
                    "w": 1.0,
                    "y": y,
                    "anchor": 0.5,
                    "raw": 0.5 + (0.1 if right else -0.1) * (2 * y - 1),
                }
            )
        return out

    @staticmethod
    def overlapping(rng, n, k, mean=0.0):
        """Weekly gains that share k weeks of windows: each the average of k consecutive shocks."""
        e = rng.normal(0, 1, n + k)
        return np.convolve(e, np.ones(k) / k, mode="valid")[:n] * 2 + mean

    def test_luck_rarely_opens_the_gate_even_when_checked_every_week(self):
        """Guards against: confidence from a lucky streak, the risk of a gate checked every week for years."""
        rng = np.random.default_rng(0)
        opened = sum(
            any(o for _, o, _ in ln.gate_path(rng.normal(0, 1, 400), 1, 3)) for _ in range(40)
        )
        self.assertLessEqual(opened, 2)

    def test_overlapping_windows_do_not_fake_confidence(self):
        """Guards against the review's finding: weeks that share a market window counted as independent evidence
        (zero-skill gains with 4- and 12-week overlap opened the v2 gate in 55% and 68% of runs)."""
        rng = np.random.default_rng(1)
        opened20 = sum(
            any(o for _, o, _ in ln.gate_path(self.overlapping(rng, 400, 4), 1, 3))
            for _ in range(40)
        )
        blocks = lambda x: x[: len(x) // 4 * 4].reshape(-1, 4).mean(1)  # noqa: E731
        opened60 = sum(
            any(o for _, o, _ in ln.gate_path(blocks(self.overlapping(rng, 1600, 12)), 4, 2))
            for _ in range(40)
        )
        self.assertLessEqual(opened20, 4)
        self.assertLessEqual(opened60, 4)

    def test_real_skill_opens_it_and_losing_the_skill_closes_it(self):
        """Guards against: a gate that never opens, or stays open after the edge is gone (the review measured v2 still
        open in 40-52% of runs once the skill had fallen to zero)."""
        rng = np.random.default_rng(2)
        opened = sum(ln.gate_path(rng.normal(0.5, 1, 200), 1, 3)[-1][1] for _ in range(20))
        self.assertGreaterEqual(opened, 16)
        still = sum(
            ln.gate_path(np.concatenate([rng.normal(0.5, 1, 150), rng.normal(0, 1, 150)]), 1, 3)[
                -1
            ][1]
            for _ in range(20)
        )
        self.assertLessEqual(still, 4)

    def test_pairs_become_weekly_observations_through_the_gate(self):
        """Guards against: the pairs-to-gate path not joining up (signature, class routing, alpha)."""
        a, info = ln.gate(self.pairs(0.9, 60, 3), "RELATIVE/20", self.ASOF)
        self.assertEqual(info["observations"], 60)
        self.assertGreater(a, 0.0)
        self.assertEqual(
            ln.gate(self.pairs(0.9, 60, 3), "RELATIVE/60", self.ASOF)[1]["observations"], 0
        )
        self.assertEqual(
            ln.gate(self.pairs(1.0, 29, 1), "RELATIVE/20", self.ASOF)[0], 0.0
        )  # below 30 weeks: shut

    def test_an_observation_never_changes_once_it_exists(self):
        """Guards against the review's finding: one market day split into many observations by the second it was
        stamped, a parent and child counted twice when they resolve apart, and a week still filling up counted."""
        a = {
            "kind": "RELATIVE",
            "session": "s1",
            "window": "H20",
            "event_key": "E",
            "statement": "BEATS_TWINS_20",
            "set_id": "A",
            "resolved_at": "2027-01-05T00:00:01Z",
            "y": 1.0,
            "anchor": 0.5,
            "raw": 0.7,
        }
        b = {
            **a,
            "event_key": "F",
            "set_id": "B",
            "raw": 0.4,
            "y": 0.0,
            "resolved_at": "2027-01-05T00:00:02Z",
        }
        (o,) = ln.observations([a, b], "2027-01-11T00:00:00Z")
        self.assertEqual(o[2], 2)  # two seconds apart, one week: one observation
        late = {
            **a,
            "set_id": "A2",
            "resolved_at": "2027-01-20T00:00:00Z",
            "raw": 0.2,
        }  # the same filing's other set
        obs = ln.observations([a, b, late], "2027-02-01T00:00:00Z")
        self.assertEqual(
            (len(obs), obs[0]), (1, o)
        )  # counted once, where it first resolved; nothing rewritten
        self.assertEqual(
            ln.observations([a, b], "2027-01-08T00:00:00Z"), []
        )  # that week has not ended


class EndToEnd(NoHistory):
    @staticmethod
    def run_world(skill, days=180, per_day=4, seed=0):
        """Sets sealed every weekday, forecast before entry, resolved 28 days later; returns the statistics."""
        from datetime import timedelta

        cone = [
            {"id": "BEATS_TWINS_20", "prior": 0.5, "resolves_with": "H20"},
            {"id": "GAIN0_20", "prior": 0.5, "resolves_with": "H20"},
        ]
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
                s = cset(
                    f"{sess}-{k}",
                    family="FORM4",
                    top_exec=te,
                    session=sess,
                    cone=cone,
                    cutoff=(day + timedelta(days=1)).strftime("%Y-%m-%dT13:15:00Z"),
                )
                s["sealed_at"] = f"{sess}T23:00:00Z"
                recs.append(s)
                pending.append(
                    (
                        day + timedelta(days=28),
                        s["set_id"],
                        bool(rng.random() < 0.5 + (skill if te else -skill)),
                        bool(rng.random() < 0.7),
                    )
                )
            now = day + timedelta(hours=23, minutes=30)
            recs += [
                res(
                    sid,
                    {"BEATS_TWINS_20": beat, "GAIN0_20": gain},
                    due.strftime("%Y-%m-%dT10:00:00Z"),
                    "H20",
                    "FORM4",
                )
                for due, sid, beat, gain in pending
                if due <= now
            ]
            pending = [x for x in pending if x[0] > now]
            lrecs += ln.forecast_records(now, recs, lrecs)
        return (
            ln.statistics(
                recs, lrecs, (start + timedelta(days=days + 7)).strftime("%Y-%m-%dT00:00:00Z")
            ),
            recs,
            lrecs,
        )

    def test_the_loop_rewards_real_discrimination_and_nothing_else(self):
        """Guards against: a learner whose sealed forecasts, resolutions and scoring do not join up, or that is credited
        in a world where nothing predicts the outcome (while every stock rose 70% of the time)."""
        (skilled, recs, lrecs), (blind, _, _) = self.run_world(0.15), self.run_world(0.0)
        self.assertGreaterEqual(skilled["gates"]["RELATIVE/20"][1]["observations"], 15)
        bt = skilled["per_statement"]["FORM4:BEATS_TWINS_20"]
        self.assertLess(bt["brier_raw"], bt["brier_anchor"])
        self.assertGreater(skilled["claim"]["mean_gain"], 0.0)
        self.assertLess(
            blind["per_statement"]["FORM4:BEATS_TWINS_20"]["brier_anchor"] + 0.002,
            blind["per_statement"]["FORM4:BEATS_TWINS_20"]["brier_raw"] + 0.01,
        )
        self.assertEqual(blind["gates"]["RELATIVE/20"][0], 0.0)
        self.assertEqual(
            {k.split(":")[1] for k in blind["per_statement"]}, {"BEATS_TWINS_20"}
        )  # GAIN0 never scored
        with tempfile.TemporaryDirectory() as tmp:  # and every one of its forecasts verifies
            path = Path(tmp) / "learner_v2.jsonl"
            paper.append(lrecs, path=path)
            self.assertEqual(ln.verify(path, recs), [])


class Calls(unittest.TestCase):
    def test_calls_need_a_margin_and_certainty_and_go_live_only_with_earned_confidence(self):
        """Guards against: a call made on a lean, or published before the learner has earned it."""
        self.assertEqual(ln.call_of(0.6, 0.2, 0.0), {"side": "BACK", "live": False})
        self.assertEqual(ln.call_of(0.6, 0.2, 1.0), {"side": "BACK", "live": True})
        self.assertEqual(
            ln.call_of(0.6, 0.5, 1.0), {"side": None, "live": False}
        )  # not sure enough
        self.assertEqual(
            ln.call_of(0.3, 0.01, 1.0), {"side": None, "live": False}
        )  # not far enough
        self.assertEqual(
            ln.call_of(-0.6, 0.2, 0.5), {"side": "AVOID", "live": False}
        )  # published move 0.3 < margin


class History(unittest.TestCase):
    def test_the_warm_start_is_pinned_pre_2024_and_capped(self):
        """Guards against: a warm start that was swapped, reaches the sealed holdout, or outweighs the live record."""
        build = json.loads((ln.HISTORY.parent / "BUILD.json").read_text())
        self.assertEqual(build["events_csv_gz"], ln.HISTORY_SHA256)
        self.assertLess(build["signal_dates"][1], "2024-01-01")
        rows = ln.history_rows()
        for k in ln.SKILL_KINDS:
            self.assertLessEqual(sum(r.w for r in rows if r.kind == k), ln.N_CAP + 1e-6)
        self.assertTrue(
            all(r.icpt.startswith("hist:") for r in rows)
        )  # its own intercepts: never the live anchor
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
        self.assertEqual(
            (m["lambda_shared"], m["lambda_task"], m["lambda_own"]),
            (ln.LAMBDA_SHARED, ln.LAMBDA_TASK, ln.LAMBDA_OWN),
        )
        self.assertAlmostEqual(m["intercept_prior_sd"], 1.5)
        self.assertEqual(p["earned_confidence"]["numbers"], ln.GATE)
        self.assertEqual(
            {k: tuple(v) for k, v in p["earned_confidence"]["blocks"].items()}, ln.BLOCKS
        )
        self.assertEqual(tuple(p["claim"]["block"]), ln.CLAIM_BLOCK)
        self.assertEqual(p["calls"]["numbers"], ln.CALL)
        self.assertEqual(p["triangles"], {k: list(v) for k, v in ln.TRIANGLES.items()})
        self.assertEqual(p["protocol_id"], "KOD-LEARNER-v2.2")
        self.assertEqual(p["statements"]["own_move_threshold"], ln.OWN_MOVE)
        self.assertEqual(set(p["statements"]["skill_kinds"]), set(ln.SKILL_KINDS))


class Verify(NoHistory):
    NOW = datetime(2026, 12, 10, 12, 0, tzinfo=timezone.utc)

    def sealed(self, recs):
        (f,) = [f for f in ln.forecast_records(self.NOW, recs, []) if f["set_id"] == "A"]
        return f

    def check(self, recs, forecasts):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "learner_v2.jsonl"
            paper.append(forecasts, path=path)
            return "\n".join(ln.verify(path, recs))

    def test_late_forecasts_wrong_sets_and_peeking_are_caught(self):
        """Guards against: a forecast after the cutoff, bound to an edited set, or trained on later outcomes."""
        recs = world(60, resolved_at="2026-12-05T00:00:00Z") + [
            cset("A", cutoff="2026-12-10T13:15:00Z", top_exec=True)
        ]
        good = self.sealed(recs)
        late = {**good, "set_id": "S1", "set_record_hash": "hS1", "made_at": "2026-12-11T00:00:00Z"}
        wrong = {**good, "set_id": "S2", "set_record_hash": "not-the-hash"}
        peek = {**good, "set_id": "S3", "set_record_hash": "hS3", "made_at": "2026-10-29T00:00:00Z"}
        joined = self.check(recs, [good, late, wrong, peek])
        self.assertNotIn("A:", joined)
        self.assertIn("S1: forecast made at", joined)
        self.assertIn("S2: forecast binds no sealed set", joined)
        self.assertIn("S3: does not reproduce", joined)

    def test_every_field_scoring_reads_is_bound(self):
        """Guards against the review's finding: a losing statement relabelled ABSOLUTE, a session moved or a family
        renamed, each of which v2's verify let through (the last one crashed every later run)."""
        recs = world(60) + [cset("A", cutoff="2026-12-10T13:15:00Z", top_exec=True)]
        f = self.sealed(recs)
        for edit in (
            lambda r: r["forecasts"]["BEATS_TWINS_60"].update(kind="ABSOLUTE"),
            lambda r: r.update(signal_session="2026-11-02"),
            lambda r: r.update(family="FORM4"),
            lambda r: r["forecasts"]["BEATS_TWINS_60"].update(
                raw=r["forecasts"]["BEATS_TWINS_60"]["raw"] + 0.01
            ),
        ):
            g = json.loads(json.dumps(f))
            edit(g)
            self.assertIn("A: does not reproduce", self.check(recs, [g]))
        self.assertEqual(self.check(recs, [f]), "")

    def test_the_forecast_is_bound_to_the_ledger_state_it_saw(self):
        """Guards against the review's findings: a forecast claiming a ledger state that never existed, and a false
        alarm on an honest forecast when a resolution stamped before it was appended after it."""
        recs = world(60) + [cset("A", cutoff="2026-12-10T13:15:00Z", top_exec=True)]
        f = self.sealed(recs)
        backdated = recs + [
            res("S7", {"BEATS_TWINS_60": True}, "2026-12-10T11:59:00Z")
        ]  # appended after the forecast
        self.assertEqual(self.check(backdated, [f]), "")
        g = json.loads(json.dumps(f))
        g["inputs"]["records"][1] = "not-the-head"
        self.assertIn("A: the ledger state it records", self.check(recs, [g]))


class Report(NoHistory):
    def test_statistics_and_render_with_and_without_data(self):
        """Guards against: a report that crashes before the first outcome, or hides the earned-confidence level."""
        st = ln.statistics([], [], "2026-10-30T00:00:00Z")
        self.assertEqual((st["forecasts"], st["pairs"]), (0, 0))
        md = ln.render(st)
        self.assertIn("| RELATIVE/20 | 0.00 |", md)
        self.assertIn("accumulating", md)
        recs = world(80) + [cset("A", cutoff="2026-12-10T13:15:00Z", top_exec=True)]
        (f,) = [
            f
            for f in ln.forecast_records(
                datetime(2026, 12, 10, 12, 0, tzinfo=timezone.utc), recs, []
            )
            if f["set_id"] == "A"
        ]
        recs += [res("A", {"BEATS_TWINS_60": True, "GAIN0_60": True}, "2027-03-01T00:00:00Z")]
        st = ln.statistics(recs, [f], "2027-03-02T00:00:00Z")
        self.assertEqual(st["pairs"], 1)
        self.assertIn("shadow_BACK", st["calls"])
        self.assertIn("What it believes now", ln.render(st))


if __name__ == "__main__":
    unittest.main()


class RegisterWindows(unittest.TestCase):
    def test_v2_2_ignores_windows_its_protocol_does_not_name(self):
        """Guards against: a register version adding a window (NEXT1, v1.1) and the frozen learner silently forecasting
        and scoring statements outside its protocol."""
        s = {
            "family": "SPEC_US",
            "cone": [
                {"id": "RUN30_5", "resolves_with": "BASE5"},
                {"id": "FADE10_5", "resolves_with": "BASE5"},
                {"id": "DOWN10_1", "resolves_with": "NEXT1"},
                {"id": "BEATS_TWINS_1", "resolves_with": "NEXT1"},
            ],
        }
        ids = [stmt for stmt, _ in ln.statements(s)]
        self.assertIn("PUMP30_5", ids)
        self.assertIn("PUMP_AND_DUMP_5", ids)
        self.assertNotIn("DOWN10_1", ids)
        self.assertNotIn("BEATS_TWINS_1", ids)
