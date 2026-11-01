"""The PAPER_ACCOUNT_v1 report repair: balances from every current record, dated valuations, nothing written back."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from idxsig import cli, paper
from idxsig import paper_account as acct
from idxsig import paper_account_report as report
from idxsig.provenance import PKG_ROOT, sha256_file


def _order(ticker, reserved=950.0, risk=50.0):
    return {"type": acct.ORDER, "account": acct.ACCOUNT_ID, "arm": "BASE", "set_id": f"SET-{ticker}",
            "ticker": ticker, "signal_session": "2026-11-02", "source": "KOD", "dump_tomorrow": 0.3,
            "entry_cutoff": "2026-11-03T14:30:00Z", "made_at": "2026-11-02T23:00:00Z",
            "plan": {"shares": 95, "max_entry": 10.0}, "reserved_usd": reserved, "planned_risk_usd": risk}


def _follow(kind, order, **fields):
    return {"type": kind, "account": acct.ACCOUNT_ID, "arm": "BASE", "set_id": order["set_id"],
            "ticker": order["ticker"], "order_record_hash": order["record_hash"],
            "recorded_at": "2026-11-03T22:50:00Z", "made_at": "2026-11-03T22:50:00Z", **fields}


FILL = {"status": "FILLED", "entry_session": "2026-11-03", "price": 10.0, "shares": 95, "stop": 9.5,
        "cost_in": 0.002, "time_exit_session": "2026-11-10"}


class Report(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.ledger = Path(tmp.name) / "paper_account.jsonl"
        self.out = Path(tmp.name) / "PAPER_ACCOUNT.md"
        for target, name, value in ((acct, "LEDGER", self.ledger), (acct, "REPORT", self.out),
                                    (report, "REPORT", self.out)):
            p = mock.patch.object(target, name, value)
            p.start()
            self.addCleanup(p.stop)

    def _add(self, *records):
        return paper.append(list(records), path=self.ledger)

    def _base(self):
        return report.summary(acct.lines(), "BASE")

    def test_1_pending_order_reserves_cash_without_changing_equity(self):
        self._add(_order("AAA", reserved=944.49))
        s = self._base()
        self.assertEqual((s["cash"], s["reserved"], s["pending"]), (10_000.0, 944.49, 1))
        self.assertAlmostEqual(s["free_cash"], 9055.51)
        self.assertEqual(s["equity"], 10_000.0)
        self.assertIn("$944.49", report.render(acct.lines()))

    def test_2_a_cancel_in_the_same_session_releases_the_reservation(self):
        (o,) = self._add(_order("AAA"))
        self._add(_follow(acct.CANCEL, o, reason="the owner skipped this spike before the open"))
        s = self._base()
        self.assertEqual((s["reserved"], s["free_cash"], s["pending"], s["cancelled"]), (0.0, 10_000.0, 0, 1))

    def test_3_a_rejected_entry_leaves_no_purchase_and_no_reservation(self):
        (o,) = self._add(_order("AAA"))
        self._add(_follow(acct.ENTRY, o, status="REJECTED_STOP_TOO_WIDE", reason="open above the limit"))
        s = self._base()
        self.assertEqual((s["cash"], s["reserved"], s["open"], s["rejected"]), (10_000.0, 0.0, [], 1))

    def test_4_and_7_a_fill_pays_cash_and_an_unvalued_position_is_flagged(self):
        (o,) = self._add(_order("AAA"))
        self._add(_follow(acct.ENTRY, o, **FILL))
        s = self._base()
        self.assertAlmostEqual(s["cash"], 10_000.0 - 95 * 10.0 * 1.002)
        self.assertEqual((s["reserved"], len(s["open"]), s["filled"]), (0.0, 1, 1))
        self.assertIn("carried at its entry price", report.render(acct.lines()))

    def test_5_a_recorded_price_decline_shows_in_unrealized_and_equity(self):
        (o,) = self._add(_order("AAA"))
        self._add(_follow(acct.ENTRY, o, **FILL))
        self._add({"type": acct.MARK, "account": acct.ACCOUNT_ID, "arm": "BASE", "session": "2026-11-04",
                   "equity": 9000.0, "made_at": "2026-11-04T22:50:00Z",
                   "open_positions": [{"order_record_hash": o["record_hash"], "mark_return": -0.10}]})
        s = self._base()
        self.assertAlmostEqual(s["open_value"], 95 * 10.0 * 0.90)
        self.assertAlmostEqual(s["equity"], s["cash"] + 855.0)
        self.assertLess(s["unrealized"], -95 - 1e-9)
        text = report.render(acct.lines())
        self.assertIn("valued at the close of 2026-11-04 (-10.00% since entry)", text)
        self.assertNotIn("carried at its entry price", text)

    def test_6_an_exit_closes_the_position_and_cash_reconciles(self):
        (o,) = self._add(_order("AAA"))
        self._add(_follow(acct.ENTRY, o, **FILL))
        self._add(_follow(acct.EXIT, o, exit_session="2026-11-05", exit_reason="STOP", price=9.5,
                          cost_out=0.002, net_return=-0.0539, net_pnl_usd=-51.21))
        s = self._base()
        self.assertAlmostEqual(s["cash"], 10_000.0 - 51.21)
        self.assertEqual((s["realized"], s["open"], s["unrealized"], s["closed"]), (-51.21, [], 0.0, 1))
        self.assertIn("-$51.21", report.render(acct.lines()))

    def test_8_rendering_twice_is_identical_and_writes_no_record(self):
        (o,) = self._add(_order("AAA"))
        self._add(_follow(acct.ENTRY, o, **FILL))
        before = sha256_file(self.ledger)
        first, second = report.write_report().read_text(), report.write_report().read_text()
        self.assertEqual(first, second)
        self.assertEqual(sha256_file(self.ledger), before)

    def test_9_both_command_paths_use_this_renderer(self):
        self._add(_order("AAA", reserved=944.49), _order("BBB", reserved=952.66))
        with mock.patch("sys.stdout"):
            cli.main(["paper-account-report"])
        self.assertEqual(self.out.read_text(), report.render(acct.lines()))
        self.assertIn("$1,897.15", self.out.read_text())
        source = (PKG_ROOT / "idxsig" / "cli.py").read_text()
        self.assertEqual(source.count("paper_account_report.write_report()"), 2)
        self.assertNotIn("acct.write_report()", source)

    def test_drawdown_is_dated_from_recorded_marks(self):
        for session, equity in (("2026-11-03", 10_100.0), ("2026-11-04", 9_595.0), ("2026-11-05", 9_900.0)):
            self._add({"type": acct.MARK, "account": acct.ACCOUNT_ID, "arm": "BASE", "session": session,
                       "equity": equity, "open_positions": [], "made_at": f"{session}T22:50:00Z"})
        worst, when = report.drawdown(acct.lines(), "BASE")
        self.assertAlmostEqual(worst, 9_595.0 / 10_100.0 - 1)
        self.assertEqual(when, "2026-11-04")


class Preservation(unittest.TestCase):
    def test_10_the_frozen_files_keep_their_fingerprints(self):
        root = PKG_ROOT / "research" / "PAPER_ACCOUNT_v1" / "protocol.json"
        pins = json.loads(root.read_text())["pins"]
        for path, digest in pins.items():
            self.assertEqual(sha256_file(PKG_ROOT / path), digest, path)


if __name__ == "__main__":
    unittest.main()
