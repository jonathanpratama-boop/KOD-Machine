"""SPLIT_ARTIFACT_V11: descriptive tag ledger and report disclosure (written from the interface spec only)."""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from idxsig import split_flags, paper_book as book, paper_book_report, paper_input_health, paper

HEADING = (
    "## Secondary view: sets tagged SPLIT_ARTIFACT_V11 excluded "
    "(display only, the frozen verdict above is unchanged)"
)
KEYS = {"type", "rule", "set_id", "ticker", "market", "signal_session", "recorded_ret1",
        "flag", "split", "split_adjusted_ret1", "basis", "assessed_at"}


def ev(day, n=1, d=10):
    return {"effective_session": day, "numerator": n, "denominator": d, "provider_ratio": f"{n}:{d}"}


def ts(*a):
    return int(datetime(*a, tzinfo=timezone.utc).timestamp())


def payload(unix, n=1, d=10):
    return {"chart": {"result": [{"events": {"splits": {str(unix): {
        "date": unix, "numerator": n, "denominator": d, "splitRatio": f"{n}:{d}"}}}}]}}


def set_rec(sid="US-1", ticker="TOPS", close=9.84, prev=1.0, session="2026-11-09"):
    return {"set_id": sid, "ticker": ticker, "market": "US", "signal_session": session,
            "signal": {"close": close, "previous": prev}, "decision": {}}


class Classify(unittest.TestCase):
    def test_tops(self):
        h = split_flags.classify(9.84, [ev("2026-11-06")], "2026-11-09")
        self.assertEqual((h["k"], h["split_adjusted_ret1"]), (10, -0.016))

    def test_atyr(self):
        h = split_flags.classify(39.84, [ev("2026-10-29", 1, 40)], "2026-10-30")
        self.assertEqual((h["k"], h["split_adjusted_ret1"]), (40, -0.004))

    def test_whlr_hit_is_the_signal_day_event(self):
        h = split_flags.classify(6.53, [ev("2026-09-22", 1, 9), ev("2026-10-30", 1, 6)], "2026-10-30")
        self.assertEqual(h["k"], 6)
        self.assertEqual(h["effective_session"], "2026-10-30")
        self.assertEqual(h["split_adjusted_ret1"], round(6.53 / 6 - 1, 4))

    def test_xxii(self):
        h = split_flags.classify(45.95, [ev("2026-06-12", 1, 20), ev("2026-11-05", 1, 58)], "2026-11-05")
        self.assertEqual(h["k"], 58)
        self.assertAlmostEqual(h["split_adjusted_ret1"], -0.208, places=3)

    def test_real_spike_moving_away_from_no_move_is_none(self):
        # 1.5/10 - 1 = -0.85 < 0.30 but |ln 0.15| > |ln 1.5|: the third condition fails.
        self.assertIsNone(split_flags.classify(1.5, [ev("2026-11-06")], "2026-11-09"))

    def test_window_bounds(self):
        def c(day):
            return split_flags.classify(9.84, [ev(day)], "2026-11-09")

        self.assertIsNone(c("2026-10-29"))  # 11 days before
        self.assertIsNone(c("2026-10-30"))  # exactly 10 days: exclusive lower bound
        self.assertIsNotNone(c("2026-10-31"))
        self.assertIsNotNone(c("2026-11-09"))  # on the signal date
        self.assertIsNone(c("2026-11-10"))  # after the signal date

    def test_forward_split_none(self):
        self.assertIsNone(split_flags.classify(1.4, [ev("2026-11-06", 2, 1)], "2026-11-09"))

    def test_degenerate_inputs_never_raise(self):
        for ratio, events in ((9.84, [ev("2026-11-06", 0, 10)]), (0, [ev("2026-11-06")]),
                              (-2.0, [ev("2026-11-06")]), (9.84, [])):
            self.assertIsNone(split_flags.classify(ratio, events, "2026-11-09"))

    def test_newest_qualifying_event_wins(self):
        # ratio 9.84: 1:10 gives 0.984, 1:8 gives 1.23 (+23% < 30%, closer to 1): both qualify.
        h = split_flags.classify(9.84, [ev("2026-11-03", 1, 10), ev("2026-11-06", 1, 8)], "2026-11-09")
        self.assertEqual((h["effective_session"], h["k"]), ("2026-11-06", 8))
        h = split_flags.classify(9.84, [ev("2026-11-06", 1, 8), ev("2026-11-03", 1, 10)], "2026-11-09")
        self.assertEqual(h["effective_session"], "2026-11-06")


class Label(unittest.TestCase):
    def test_label(self):
        self.assertEqual(split_flags.label(9.84, {"k": 10}), "ARTIFACT_V11")
        self.assertEqual(split_flags.label(4.0, None), "INDETERMINATE")
        self.assertEqual(split_flags.label(48.28, None), "INDETERMINATE")
        self.assertEqual(split_flags.label(3.99, None), "NOT_FLAGGED")
        self.assertEqual(split_flags.label(1.5, None), "NOT_FLAGGED")


class ProviderSplits(unittest.TestCase):
    def test_reverse_split(self):
        out = split_flags.provider_splits(payload(ts(2026, 11, 6, 14, 30)))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["effective_session"], "2026-11-06")
        self.assertEqual(out[0]["denominator"] / out[0]["numerator"], 10)
        self.assertEqual(out[0]["provider_ratio"], "1:10")

    def test_new_york_date_not_utc_date(self):
        out = split_flags.provider_splits(payload(ts(2026, 11, 7, 2, 0)))
        self.assertEqual(out[0]["effective_session"], "2026-11-06")

    def test_malformed_payloads(self):
        for bad in (None, {}, {"chart": None}, {"chart": {"result": None}}, {"chart": {"result": [{}]}},
                    {"chart": {"result": [{"events": None}]}}, "oops",
                    {"chart": {"result": None, "error": {"code": "Not Found"}}},
                    {"finance": {"error": "Too Many Requests"}}):
            self.assertEqual(split_flags.provider_splits(bad), [])


class FlagRecord(unittest.TestCase):
    def test_tops_like(self):
        r = split_flags.flag_record(set_rec(), payload(ts(2026, 11, 6, 14, 30)), "basis-x", "2026-11-11T00:00:00Z")
        self.assertEqual(set(r), KEYS)
        self.assertNotIn("prev_hash", r)
        self.assertNotIn("record_hash", r)
        self.assertEqual((r["type"], r["rule"]), ("SPLIT_FLAG", "SPLIT_ARTIFACT_V11"))
        self.assertEqual((r["flag"], r["split"], r["recorded_ret1"]), ("ARTIFACT_V11", "2026-11-06 1:10", 8.84))
        self.assertEqual((r["basis"], r["assessed_at"]), ("basis-x", "2026-11-11T00:00:00Z"))

    def test_no_payload_is_not_assessed(self):
        r = split_flags.flag_record(set_rec(), None, "b", "t")
        self.assertEqual((r["flag"], r["split"], r["split_adjusted_ret1"]), ("NOT_ASSESSED", "", None))

    def test_normal_spike_not_flagged(self):
        r = split_flags.flag_record(set_rec(close=1.5), {"chart": {"result": [{}]}}, "b", "t")
        self.assertEqual((r["flag"], r["split"], r["split_adjusted_ret1"]), ("NOT_FLAGGED", "", None))


class Pending(unittest.TestCase):
    def test_only_unflagged_us_sealed_sets(self):
        a, b, c = set_rec("US-A"), set_rec("US-B"), set_rec("US-C")
        idx = dict(set_rec("IDX-1"), market="IDX")
        crypto = dict(set_rec("CR-1"), market="CRYPTO")
        resolution = {"type": "RESOLUTION", "set_id": "US-R", "market": "US"}
        flags = [{"type": "SPLIT_FLAG", "set_id": "US-B", "flag": "NOT_FLAGGED"}]
        out = split_flags.pending([c, idx, a, crypto, resolution, b], flags)
        self.assertEqual([s["set_id"] for s in out], ["US-C", "US-A"])


class Ledger(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "split_flags.jsonl"
        p = mock.patch.object(split_flags, "FLAGS_LEDGER", self.path)
        p.start()
        self.addCleanup(p.stop)

    def _write(self, *recs):
        paper.append(list(recs), path=self.path)

    @staticmethod
    def _flag(sid, flag="ARTIFACT_V11", rule="SPLIT_ARTIFACT_V11"):
        return {"type": "SPLIT_FLAG", "rule": rule, "set_id": sid, "flag": flag}

    def test_missing_file_is_empty(self):
        self.assertEqual(split_flags.flagged_set_ids(), set())

    def test_labels(self):
        self._write(self._flag("A"), self._flag("B", "INDETERMINATE"), self._flag("C", "NOT_FLAGGED"))
        self.assertEqual(split_flags.flagged_set_ids(), {"A"})
        self.assertEqual(split_flags.flagged_set_ids(labels=("ARTIFACT_V11", "INDETERMINATE")), {"A", "B"})

    def test_verify_sound(self):
        self._write(self._flag("A"), self._flag("B", "NOT_ASSESSED"))
        self.assertEqual(split_flags.verify(specs=[set_rec("A"), set_rec("B")]), [])

    def test_verify_problems(self):
        specs = [set_rec("A"), set_rec("B"), set_rec("C")]
        cases = {
            "duplicate": [self._flag("A"), {**self._flag("A"), "basis": "second look"}],  # paper.append collapses identical payloads
            "bad flag": [self._flag("A", "MAYBE")],
            "bad rule": [self._flag("A", rule="OTHER_RULE")],
            "unknown set": [self._flag("ZZZ")],
        }
        for name, recs in cases.items():
            with self.subTest(name):
                self.path.unlink(missing_ok=True)
                self._write(*recs)
                self.assertTrue(split_flags.verify(specs=specs), name)


class Report(unittest.TestCase):
    ROWS = [
        dict(set_id="S1", ticker="AAA", session="2026-10-29", dump_tomorrow=0.3, verdict="BUY_OK", owner="BUY", status="CLOSED", net=0.05),
        dict(set_id="S2", ticker="TOPS", session="2026-10-30", dump_tomorrow=0.7, verdict="DONT_BUY", owner="SKIP", status="CLOSED", net=-0.02),
        dict(set_id="S3", ticker="CCC", session="2026-11-02", dump_tomorrow=0.4, verdict="BUY_OK", owner="BUY", status="OPEN", net=None),
    ]

    def setUp(self):
        for target, name, val in (
            (book, "utc_stamp", "2026-11-11T00:00:00Z"),
            (split_flags, "FLAGS_LEDGER", Path(tempfile.gettempdir()) / "no-such-split-flags.jsonl"),
        ):
            p = mock.patch.object(target, name, **({"return_value": val} if name == "utc_stamp" else {"new": val}))
            p.start()
            self.addCleanup(p.stop)

    def _frozen(self):
        return paper_input_health.add_banner(book.render(self.ROWS), paper_input_health.unassessed())

    def test_untagged_output_equals_frozen_renderer_plus_banner(self):
        out = paper_book_report.render(self.ROWS)
        self.assertNotIn("Secondary view", out)
        self.assertEqual(out, self._frozen())
        with mock.patch.object(split_flags, "flagged_set_ids", return_value=set()):
            self.assertEqual(paper_book_report.render(self.ROWS), out)

    def test_tagged_set_appends_secondary_view(self):
        base = paper_book_report.render(self.ROWS)
        with mock.patch.object(split_flags, "flagged_set_ids", return_value={"S2"}):
            out = paper_book_report.render(self.ROWS)
        self.assertTrue(out.startswith(base))
        tail = out[len(base):]
        self.assertIn(HEADING, tail)
        self.assertTrue(out.rstrip().endswith(tail.rstrip()))
        section = out[out.index(HEADING):]
        self.assertIn("TOPS", section)
        rest = [r for r in self.ROWS if r["set_id"] != "S2"]
        for b in book.BOOKS:
            s = book.book_summary(rest, b)
            lines = [ln for ln in section.splitlines() if b in ln]
            self.assertTrue(lines, b)
            line = lines[0]
            for key in ("positions", "closed", "wins"):
                self.assertIn(str(s[key]), line, (b, key))
            self.assertIn(f"{s['pnl']:+,.0f}", line, b)


if __name__ == "__main__":
    unittest.main()
