"""ADMISSION_v1: the fresh 10-15% filter on fixtures (no market data)."""

import importlib.util
import unittest
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from idxsig import crypto_replay as cr

_spec = importlib.util.spec_from_file_location(
    "admission", Path(__file__).resolve().parents[1] / "research/ADMISSION_v1/admission.py"
)
adm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adm)

D0 = date(2023, 3, 1)


def day(n):
    return (D0 + timedelta(days=n)).isoformat()


def sl(rows):
    """rows: (day offset, ticker, rank, p)."""
    return pd.DataFrame(
        [{"date": day(n), "ticker": t, "rank": r, "rank_score": p} for n, t, r, p in rows]
    )


def reasons(frame):
    e = adm.eligibility(frame)
    return {(r.date, r.ticker): r.reason for r in e.itertuples()}


class Filter(unittest.TestCase):
    def test_band_is_ten_inclusive_fifteen_exclusive(self):
        f = sl(
            [
                (0, "X", 1, 0.5),
                (1, "A", 1, 0.15),
                (1, "B", 2, 0.1499999),
                (1, "C", 3, 0.10),
                (1, "D", 4, 0.0999999),
            ]
        )
        r = reasons(f)
        self.assertEqual(r[(day(1), "A")], "AT_OR_ABOVE_BAND")
        self.assertEqual(r[(day(1), "B")], "ELIGIBLE")
        self.assertEqual(r[(day(1), "C")], "ELIGIBLE")
        self.assertEqual(r[(day(1), "D")], "BELOW_BAND")

    def test_yesterdays_symbol_is_not_fresh_whatever_its_band_yesterday(self):
        f = sl([(0, "A", 1, 0.40), (1, "A", 1, 0.12), (1, "B", 2, 0.12)])
        r = reasons(f)
        self.assertEqual(
            r[(day(1), "A")], "NOT_FRESH"
        )  # yesterday it was out of band; still not fresh
        self.assertEqual(r[(day(1), "B")], "ELIGIBLE")

    def test_a_calendar_day_gap_makes_the_symbol_fresh_again(self):
        f = sl([(0, "A", 1, 0.12), (1, "B", 1, 0.12), (2, "A", 1, 0.12)])
        self.assertEqual(
            reasons(f)[(day(2), "A")], "ELIGIBLE"
        )  # in the list two days ago, not yesterday

    def test_missing_prior_day_evidence_is_not_eligible(self):
        f = sl([(0, "A", 1, 0.12), (2, "B", 1, 0.12)])  # no list at all for day 1
        r = reasons(f)
        self.assertEqual(r[(day(0), "A")], "FRESHNESS_UNKNOWN")  # the first day: no earlier list
        self.assertEqual(r[(day(2), "B")], "FRESHNESS_UNKNOWN")

    def test_no_eligible_candidates_leaves_the_day_empty_and_never_refills(self):
        f = sl([(0, "Z", 1, 0.12), (1, "A", 1, 0.30), (1, "B", 2, 0.05), (1, "Z", 3, 0.12)])
        c = adm.challenger(f)
        self.assertEqual(c[c.date == day(1)].ticker.tolist(), [])

    def test_the_challenger_is_a_subset_of_the_original_five_keeping_ranks(self):
        f = sl(
            [
                (0, "Q", 1, 0.2),
                (1, "A", 1, 0.16),
                (1, "B", 2, 0.14),
                (1, "C", 3, 0.13),
                (1, "D", 4, 0.11),
                (1, "E", 5, 0.05),
            ]
        )
        c = adm.challenger(f)
        self.assertEqual(list(zip(c.ticker, c["rank"])), [("B", 2), ("C", 3), ("D", 4)])
        self.assertTrue(set(zip(c.date, c.ticker)) <= set(zip(f.date, f.ticker)))


class ThroughTheEngine(unittest.TestCase):
    def test_only_eligible_alerts_can_become_orders(self):
        first, last = D0, D0 + timedelta(days=20)
        cal = pd.date_range(first, last, freq="D")
        flat = pd.Series(100.0, index=cal)
        bars = {
            t: cr.Bars(flat, flat * 1.01, flat * 0.99, flat, pd.Series(True, index=cal))
            for t in "ABCDEQ"
        }
        f = sl(
            [
                (0, "Q", 1, 0.2),
                (1, "A", 1, 0.16),
                (1, "B", 2, 0.14),
                (1, "C", 3, 0.13),
                (1, "D", 4, 0.11),
                (1, "E", 5, 0.05),
            ]
        )
        acct = cr.run(adm.challenger(f)[["date", "ticker", "rank"]], bars, first, last, cr.Policy())
        orders = [
            (e["signal_day"], e["ticker"])
            for e in acct.events
            if e["type"] == "DECISION" and e["decision"] == "ORDER"
        ]
        self.assertEqual(orders, [(day(1), "B"), (day(1), "C"), (day(1), "D")])
        self.assertEqual(cr.check_invariants(acct) + cr.audit_trades(acct, bars), [])


if __name__ == "__main__":
    unittest.main()
