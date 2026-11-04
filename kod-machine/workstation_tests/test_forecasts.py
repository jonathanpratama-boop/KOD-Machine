"""Forecast replay: sealed KOD market forecasts shown as of a moment, outcome only on request, tampering refused."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from kod.workstation.forecasts import ForecastArchive, ForecastUnavailable, _canonical
from kod.workstation.web import create_app

SET = "SPEC-SCAN-US-2026-01-05-G2_RET30-ABCD"
SEALED, MADE, CUTOFF, RESOLVED = (
    "2026-01-05T22:58:00Z",
    "2026-01-05T23:00:00Z",
    "2026-01-06T13:30:00Z",
    "2026-01-06T22:50:00Z",
)


def chain(records):
    out, previous = [], None
    for record in records:
        body = {**record, "prev_hash": previous}
        body["record_hash"] = hashlib.sha256(_canonical(body).encode()).hexdigest()
        out.append(body)
        previous = body["record_hash"]
    return out


def write(path, records):
    path.write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in records), encoding="utf-8"
    )


def ledgers(root: Path, *, resolution=True):
    register = chain(
        [
            {
                "type": "SPECULATION_SET",
                "set_id": SET,
                "market": "US",
                "ticker": "ABCD",
                "signal_session": "2026-01-05",
                "sealed_at": SEALED,
                "entry_cutoff": CUTOFF,
                "register": "spec-register-v1.1",
                "signal": {"close": 1.5, "ret1": 0.42},
                "twins": [{"ticker": t} for t in ("AAA", "BBB", "CCC")],
                "twins_match_level": "band+liq",
            }
        ]
        + (
            [
                {
                    "type": "RESOLUTION",
                    "set_id": SET,
                    "window": "NEXT1",
                    "resolved_at": RESOLVED,
                    "status": "RESOLVED",
                    "cone": [{"id": "DOWN10_1", "outcome": 1, "twins_rate": 0.0}],
                }
            ]
            if resolution
            else []
        )
    )
    forecast = chain(
        [
            {
                "type": "LEARNER3_FORECAST",
                "learner": "LEARNER-v2.4",
                "set_id": SET,
                "set_record_hash": register[0]["record_hash"],
                "ticker": "ABCD",
                "signal_session": "2026-01-05",
                "entry_cutoff": CUTOFF,
                "made_at": MADE,
                "features": {"s_ret1": 3.0},
                "provenance": {"manifest": {"file": "x.jsonl"}, "responses": {"a": "200:x"}},
                "forecasts": {
                    "NEXT_DUMP10_1": {
                        "raw": 0.71,
                        "anchor": 0.5,
                        "bench": 0.55,
                        "published": 0.5,
                        "call": {},
                        "why": [{"label": "RSI(14)", "logit": 0.4}],
                    },
                    "DUMP10_5": {
                        "raw": 0.6,
                        "anchor": 0.4,
                        "bench": 0.45,
                        "published": 0.4,
                        "call": {},
                        "why": [],
                    },
                },
            }
        ]
    )
    write(root / "speculations.jsonl", register)
    write(root / "learner_v3.jsonl", forecast)
    (root / "timestamps").mkdir()
    (root / "timestamps" / f"{forecast[0]['record_hash']}.freetsa.tsr").write_bytes(b"x")
    return register, forecast


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        ledgers(self.root)
        self.archive = ForecastArchive(self.root)

    def test_navigation_carries_no_probabilities_or_outcomes(self):
        self.assertEqual(
            self.archive.forecasts(),
            [{"set_id": SET, "ticker": "ABCD", "signal_session": "2026-01-05", "made_at": MADE}],
        )

    def test_nothing_before_the_set_is_sealed(self):
        s = self.archive.snapshot(SET, "2026-01-05T22:00:00Z", reveal_outcome=True)
        self.assertIsNone(s["set"])
        self.assertIsNone(s["forecast"])
        self.assertIsNone(s["outcome"])

    def test_set_before_forecast(self):
        s = self.archive.snapshot(SET, "2026-01-05T22:59:00Z")
        self.assertEqual(s["set"]["twins"], ["AAA", "BBB", "CCC"])
        self.assertIsNone(s["forecast"])

    def test_forecast_after_it_was_made_with_headline_first(self):
        s = self.archive.snapshot(SET, CUTOFF)
        self.assertEqual(s["forecast"]["statements"][0]["statement"], "NEXT_DUMP10_1")
        self.assertEqual(s["forecast"]["statements"][0]["raw"], 0.71)
        self.assertEqual(s["integrity"]["external_timestamps"], ["freetsa"])

    def test_outcome_needs_both_a_request_and_a_recording_by_the_cutoff(self):
        self.assertIsNone(self.archive.snapshot(SET, "2026-01-07T00:00:00Z")["outcome"])
        self.assertIsNone(
            self.archive.snapshot(SET, "2026-01-06T20:00:00Z", reveal_outcome=True)["outcome"]
        )
        graded = self.archive.snapshot(SET, "2026-01-07T00:00:00Z", reveal_outcome=True)["outcome"]
        self.assertEqual(
            graded,
            [
                {
                    "window": "NEXT1",
                    "statement": "DOWN10_1",
                    "outcome": True,
                    "twins_rate": 0.0,
                    "resolved_at": RESOLVED,
                }
            ],
        )

    def test_a_tampered_record_is_refused(self):
        path = self.root / "learner_v3.jsonl"
        record = json.loads(path.read_text())
        record["forecasts"]["NEXT_DUMP10_1"]["raw"] = 0.99
        write(path, [record])
        with self.assertRaises(ForecastUnavailable):
            self.archive.snapshot(SET, CUTOFF)

    def test_a_forecast_pointing_at_another_set_is_refused(self):
        path = self.root / "learner_v3.jsonl"
        record = json.loads(path.read_text())
        record = {k: v for k, v in record.items() if k not in ("record_hash", "prev_hash")}
        write(path, chain([{**record, "set_record_hash": "0" * 64}]))
        with self.assertRaises(ForecastUnavailable):
            self.archive.snapshot(SET, CUTOFF)

    def test_a_timestamp_without_a_zone_is_rejected(self):
        with self.assertRaises(ValueError):
            self.archive.snapshot(SET, "2026-01-06 13:30")


class WebTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        paper = Path(self.tmp.name) / "paper"
        paper.mkdir()
        ledgers(paper)
        self.client = TestClient(
            create_app(Path(self.tmp.name) / "ws", testing=True, offline=True, forecast_dir=paper)
        )
        self.addCleanup(self.client.close)

    def test_page_withholds_then_reveals(self):
        self.assertIn('href="/forecasts"', self.client.get("/").text)
        page = self.client.get(
            "/forecasts", params={"set_id": SET, "as_of": "2026-01-05T22:00:00Z"}
        ).text
        self.assertIn("No forecast yet at this moment", page)
        page = self.client.get(
            "/forecasts", params={"set_id": SET, "as_of": "2026-01-07T00:00:00Z"}
        ).text
        self.assertIn("71%", page)
        self.assertNotIn("did not happen", page)
        self.assertNotIn("DOWN10_1</b>", page)
        page = self.client.get(
            "/forecasts",
            params={"set_id": SET, "as_of": "2026-01-07T00:00:00Z", "reveal": "outcome"},
        ).text
        self.assertIn("NEXT1 · DOWN10_1", page)

    def test_unknown_forecast_is_404(self):
        self.assertEqual(self.client.get("/forecasts", params={"set_id": "nope"}).status_code, 404)


class RealLedgerTest(unittest.TestCase):
    """The repository's own sealed INLF forecast (2026-10-29), read as of the entry cutoff."""

    def test_inlf(self):
        archive = ForecastArchive()
        if not (archive.paper / "learner_v3.jsonl").exists():
            self.skipTest("idx-signals ledger not present")
        sid = "SPEC-SCAN-US-2026-10-29-G2_RET30-INLF"
        s = archive.snapshot(sid, "2026-10-30T13:30:00Z")
        self.assertEqual(s["forecast"]["statements"][0]["raw"], 0.744317)
        self.assertEqual(s["set"]["twins"], ["RETO", "ONCO", "VERI", "ARBE", "ZENA"])
        self.assertIsNone(archive.snapshot(sid, "2026-10-29T22:00:00Z")["forecast"])


if __name__ == "__main__":
    unittest.main()
