"""PAPER_ACCOUNT_v1: ten candidate decisions end to end through exec_us, the NYSE calendar, and the ledger checks."""

import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

import numpy as np

from idxsig import calendar_us, paper
from idxsig import paper_account as acct

N_DAYS = 40


def _sessions(start="2026-08-03", n=N_DAYS):
    out = [date.fromisoformat(start)]
    while len(out) < n:
        out.append(calendar_us.next_session(out[-1]))
    return np.array([d.isoformat() for d in out])


DATES = _sessions()


def _series(s, after=(), volume=1e6, gap_at=None):
    """Flat at 10 before the signal session s; the signal bar closes 10 with low 9.6; then `after` bars (o, h, l, c)."""
    o, h, lo, c = (np.full(N_DAYS, x) for x in (10.0, 10.1, 9.9, 10.0))
    v, present = np.full(N_DAYS, volume), np.ones(N_DAYS, bool)
    o[s], h[s], lo[s], c[s] = 7.8, 10.2, 9.6, 10.0
    for i, bar in enumerate(after, start=s + 1):
        o[i], h[i], lo[i], c[i] = bar
    if gap_at is not None:
        present[gap_at], v[gap_at], o[gap_at] = False, 0, np.nan
    return o, h, lo, c, v, present


FLAT = (10.0, 10.1, 9.9, 10.0)
CASES = {  # ticker: (signal day, dump_tomorrow, series)
    "AAA": (20, 0.10, _series(20, [(10.0, 10.2, 9.8, 10.0)] + [FLAT] * 6)),  # fills, time exit
    "BBB": (20, 0.11, _series(20, [(10.0, 10.1, 9.8, 10.0), FLAT, (9.9, 9.95, 9.5, 9.7)])),  # stop
    "CCC": (
        20,
        0.12,
        _series(20, [(10.0, 10.1, 9.8, 10.0), (9.0, 9.2, 8.8, 9.1)]),
    ),  # gap through stop
    "DDD": (20, 0.13, _series(20, [FLAT] * 7)),  # fourth order of the session: declined
    "EEE": (21, 0.10, _series(21, [FLAT] * 7)),  # risk budget full: declined
    "FFF": (
        27,
        0.10,
        _series(27, [(10.5, 10.6, 10.3, 10.5)] * 7),
    ),  # BASE stop too wide, FIXED5 fills
    "GGG": (27, 0.11, _series(27, gap_at=28)),  # no opening print
    "HHH": (
        27,
        0.12,
        _series(27, [(9.5, 9.6, 9.4, 9.5)] + [FLAT] * 6),
    ),  # open at or below the stop
    "III": (28, 0.10, _series(28, [FLAT] * 7)),  # the owner skips it before the open
    "JJJ": (29, 0.10, _series(29, [FLAT] * 7, volume=0.0)),  # no liquidity: no plan
}


class TenDecisions(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.ledger = Path(tmp.name) / "paper_account.jsonl"
        self.clock = ["2026-08-03T23:00:00Z"]
        for target, name, value in (
            (acct, "LEDGER", self.ledger),
            (acct, "REPORT", Path(tmp.name) / "PAPER_ACCOUNT.md"),
            (acct, "utc_stamp", lambda: self.clock[0]),
        ):
            p = mock.patch.object(target, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.book = []

    def _book_plan(self, ticker):
        s, dump, _ = CASES[ticker]
        plan = {
            "type": "BOOK_PLAN",
            "set_id": f"SET-{ticker}",
            "ticker": ticker,
            "signal_session": DATES[s],
            "dump_tomorrow": dump,
            "verdict": "BUY_OK",
            "entry_cutoff": "2099-01-01T00:00:00Z",
            "record_hash": f"plan-{ticker}",
        }
        self.book.append(plan)

    def _bars_of(self, today):
        def bars_of(c):
            s, _, (o, h, lo, cl, v, present) = CASES[c["ticker"]]
            k = today + 1
            return acct.Bars(
                o[:k], h[:k], lo[:k], cl[:k], v[:k], present[:k], np.ones(k), s, DATES[:k]
            )

        return bars_of

    def _night(self, today):
        self.clock[0] = f"{DATES[today]}T23:00:00Z"
        now = datetime.fromisoformat(f"{DATES[today]}T23:00:00+00:00")
        new = acct.sync(acct.lines(), self.book, self._bars_of(today), now, DATES[today])
        if new:
            paper.append(new, path=self.ledger)

    def test_ten_candidates_end_to_end(self):
        for today in range(20, N_DAYS):
            for t, (s, _, _) in CASES.items():
                if s == today:
                    self._book_plan(t)
            self._night(today)
            if today == 28:  # the owner skips III after tonight's order, before the open
                self.book.append(
                    {
                        "type": "BOOK_CONFIRM",
                        "set_id": "SET-III",
                        "decision": "SKIP",
                        "made_at": f"{DATES[28]}T23:30:00Z",
                        "plan_record_hash": "plan-III",
                    }
                )
                self.clock[0] = f"{DATES[28]}T23:30:00Z"
                self._night(28)
        recs = acct.lines()
        self.assertEqual(acct.verify(), [])

        def outcome(arm, ticker):
            rs = [
                r
                for r in recs
                if r.get("arm") == arm and r.get("ticker") == ticker and r["type"] != acct.MARK
            ]
            return [
                r["type"]
                if r["type"] in (acct.ORDER, acct.CANCEL)
                else r.get("status") or r.get("exit_reason") or r["reason"][:20]
                for r in rs
            ]

        base = {t: outcome("BASE", t) for t in CASES}
        self.assertEqual(base["AAA"], ["ACCT_ORDER", "FILLED", "TIME_EXIT_AT_CLOSE"])
        self.assertEqual(base["BBB"], ["ACCT_ORDER", "FILLED", "STOP"])
        self.assertEqual(base["CCC"], ["ACCT_ORDER", "FILLED", "STOP_GAP_AT_OPEN"])
        self.assertTrue(base["DDD"][0].startswith("LIMIT_NEW_PER_SESS"))
        self.assertTrue(base["EEE"][0].startswith("LIMIT_PLANNED_RISK"))
        self.assertEqual(base["FFF"], ["ACCT_ORDER", "REJECTED_STOP_TOO_WIDE"])
        self.assertEqual(base["GGG"], ["ACCT_ORDER", "REJECTED_NOT_TRADED"])
        self.assertEqual(base["HHH"], ["ACCT_ORDER", "REJECTED_AT_OR_BELOW_STOP"])
        self.assertEqual(base["III"], ["ACCT_ORDER", "ACCT_CANCEL"])
        self.assertTrue(base["JJJ"][0].startswith("NO_PLAN"))
        self.assertEqual(outcome("FIXED5", "FFF"), ["ACCT_ORDER", "FILLED", "TIME_EXIT_AT_CLOSE"])

        # cash reconciles: start + realized, nothing open or reserved at the end
        for arm in acct.ARMS:
            st = acct.account_state(recs, arm)
            pnl = sum(r["net_pnl_usd"] for r in recs if r["type"] == acct.EXIT and r["arm"] == arm)
            self.assertAlmostEqual(st["cash"], acct.START_CASH + pnl, places=6)
            self.assertEqual((st["reserved"], st["open"]), (0.0, []))
        # the stop and the gap lose, the gap more than the stop; the risk at the stop was ~0.5% of equity
        exits = {r["ticker"]: r for r in recs if r["type"] == acct.EXIT and r["arm"] == "BASE"}
        self.assertLess(exits["CCC"]["net_pnl_usd"], exits["BBB"]["net_pnl_usd"] < 0)
        orders = {r["ticker"]: r for r in recs if r["type"] == acct.ORDER and r["arm"] == "BASE"}
        self.assertLessEqual(orders["AAA"]["planned_risk_usd"], 0.005 * acct.START_CASH + 1e-9)
        # a plan never counts as a purchase: the night it is placed, the cash is only reserved
        first_mark = next(r for r in recs if r["type"] == acct.MARK and r["arm"] == "BASE")
        self.assertEqual((first_mark["cash"], first_mark["realized"]), (acct.START_CASH, 0.0))
        self.assertIn("KOD paper account", acct.write_report().read_text())

    def test_ledger_checks_catch_a_late_order(self):
        rec = {
            "type": acct.ORDER,
            "arm": "BASE",
            "set_id": "S",
            "made_at": "2026-11-02T15:00:00Z",
            "entry_cutoff": "2026-11-02T14:30:00Z",
        }
        paper.append([rec], path=self.ledger)
        self.assertTrue(any("after the open" in p for p in acct.verify()))


class Calendar(unittest.TestCase):
    def test_open_moves_with_daylight_saving(self):
        self.assertEqual(calendar_us.open_utc("2026-10-30").hour, 13)
        self.assertEqual(calendar_us.open_utc("2026-11-02").hour, 14)

    def test_holidays_and_weekends_are_skipped(self):
        self.assertEqual(calendar_us.next_session("2026-10-30"), date(2026, 11, 2))
        self.assertEqual(calendar_us.next_session("2026-11-25"), date(2026, 11, 27))  # Thanksgiving
        self.assertEqual(calendar_us.next_session("2026-04-02"), date(2026, 4, 6))  # Good Friday
        self.assertEqual(
            calendar_us.next_session("2026-07-02"), date(2026, 7, 6)
        )  # 4 July on a Saturday
        self.assertNotIn(
            date(2021, 12, 31), calendar_us.holidays(2021)
        )  # no Friday close for a Saturday New Year

    def test_entry_cutoff_is_the_real_open(self):
        self.assertEqual(
            acct.entry_cutoff("2026-10-30"), datetime(2026, 11, 2, 14, 30, tzinfo=timezone.utc)
        )


if __name__ == "__main__":
    unittest.main()
