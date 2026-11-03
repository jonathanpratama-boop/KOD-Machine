"""PAPER_BOOK_v1: plans before the cutoff, owner confirms, results from the register, books, the planned look."""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from idxsig import paper, paper_book as book


def _forecast(ticker, raw, session="2026-10-30", cutoff="2026-11-02T13:30:00Z"):
    return {
        "type": "LEARNER3_FORECAST",
        "set_id": f"SPEC-{session}-{ticker}",
        "ticker": ticker,
        "signal_session": session,
        "entry_cutoff": cutoff,
        "made_at": "2026-10-30T23:00:00Z",
        "forecasts": {"NEXT_DUMP10_1": {"raw": raw}},
    }


class Book(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.forecasts = root / "learner_v3.jsonl"
        self.ledger = root / "paper_book.jsonl"
        paper.append(
            [
                _forecast("AAA", 0.30),
                _forecast("BBB", 0.70),
                _forecast("OLD", 0.30, session="2026-10-29"),
            ],
            path=self.forecasts,
        )
        for target, value in (
            (book.learner3, ("LEDGER", self.forecasts)),
            (book, ("LEDGER", self.ledger)),
            (book, ("REPORT", root / "PAPER_BOOK.md")),
        ):
            p = mock.patch.object(target, value[0], value[1])
            p.start()
            self.addCleanup(p.stop)
        self.now = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)
        # The scenario's decision clock and actual recording clock must agree.
        # Otherwise these fixed forecasts become late merely as calendar time passes.
        clock = mock.patch.object(book, "utc_stamp", return_value="2026-10-31T12:00:00Z")
        clock.start()
        self.addCleanup(clock.stop)

    def _plan(self):
        paper.append(book.plan_records(self.now), path=self.ledger)

    def test_plans_cover_new_forecasts_only_and_use_the_cutoff(self):
        recs = book.plan_records(self.now)
        self.assertEqual(
            {r["ticker"]: r["verdict"] for r in recs}, {"AAA": "BUY_OK", "BBB": "DONT_BUY"}
        )
        paper.append(recs, path=self.ledger)
        self.assertEqual(book.plan_records(self.now), [])
        self.assertEqual(book.verify(), [])

    def test_no_plan_after_the_entry_cutoff(self):
        late = datetime(2026, 11, 2, 13, 30, tzinfo=timezone.utc)
        self.assertEqual(book.plan_records(late), [])

    def test_actual_late_recording_is_still_rejected_by_verification(self):
        with mock.patch.object(book, "utc_stamp", return_value="2026-11-03T12:00:00Z"):
            self._plan()
        self.assertEqual(len(book.verify()), 2)
        self.assertTrue(all("planned after its entry cutoff" in p for p in book.verify()))

    def test_owner_confirm_before_the_cutoff_only(self):
        self._plan()
        rec = book.confirm_record("bbb", "BUY", self.now)
        self.assertEqual((rec["ticker"], rec["decision"]), ("BBB", "BUY"))
        with self.assertRaises(ValueError):
            book.confirm_record("BBB", "BUY", datetime(2026, 11, 3, tzinfo=timezone.utc))
        with self.assertRaises(ValueError):
            book.confirm_record("ZZZ", "BUY", self.now)

    def test_results_come_from_base5_resolutions_and_fill_the_books(self):
        self._plan()
        paper.append([book.confirm_record("BBB", "BUY", self.now)], path=self.ledger)
        resolutions = [
            {
                "type": "RESOLUTION",
                "register": "spec-register-v1.1",
                "set_id": "SPEC-2026-10-30-AAA",
                "window": "BASE5",
                "status": "RESOLVED",
                "candidate": {
                    "status": "TRADED",
                    "trade": {
                        "net_return": 0.05,
                        "entry_session": "2026-11-02",
                        "exit_session": "2026-11-09",
                    },
                },
            },
            {
                "type": "RESOLUTION",
                "register": "spec-register-v1.1",
                "set_id": "SPEC-2026-10-30-BBB",
                "window": "NEXT1",
                "status": "RESOLVED",
            },
        ]
        with mock.patch.object(book.speculation, "spec_lines", return_value=resolutions):
            recs = book.result_records()
        self.assertEqual([(r["ticker"], r["net_return"]) for r in recs], [("AAA", 0.05)])
        paper.append(recs, path=self.ledger)
        rows = book.trades()
        self.assertEqual(book.book_summary(rows, "KOD")["pnl"], 50.0)
        self.assertEqual(book.book_summary(rows, "OWNER")["open"], 1)
        self.assertEqual(book.book_summary(rows, "ALL")["positions"], 2)
        self.assertEqual(book.verify(), [])
        self.assertIn("KOD paper book", book.write_report().read_text())


class PlannedLook(unittest.TestCase):
    def _rows(self, n, dont_net, ok_net):
        return [
            {
                "session": f"s{i // 5}",
                "verdict": "DONT_BUY" if i % 2 else "BUY_OK",
                "net": dont_net if i % 2 else ok_net,
            }
            for i in range(n)
        ]

    def test_not_reached_before_300_trades(self):
        self.assertIsNone(book.planned_look(self._rows(299, -0.05, 0.01)))

    def test_reached_and_judged_on_the_first_300(self):
        look = book.planned_look(self._rows(400, -0.05, 0.01))
        self.assertEqual(look["trades"], 300)
        self.assertTrue(look["dont_buy_works"])
        self.assertTrue(look["kod_makes_money"])
        self.assertFalse(book.planned_look(self._rows(300, 0.02, -0.01))["kod_makes_money"])


if __name__ == "__main__":
    unittest.main()
