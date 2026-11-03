"""CRYPTO_REPLAY_v1: the daily-bar replay engine on fixtures (no market data)."""

import unittest
from datetime import date, timedelta

import pandas as pd

from idxsig import crypto_replay as cr

FIRST = date(2023, 3, 1)  # a Wednesday
LAST = date(2023, 3, 31)
P = cr.Policy()


def bars(spec: dict[date, tuple], first=FIRST, last=LAST) -> cr.Bars:
    """A coin's bars from {day: (open, high, low, close)}; every other day is missing."""
    cal = pd.date_range(first, last, freq="D")
    cols = {k: pd.Series(float("nan"), index=cal) for k in ("open", "high", "low", "close")}
    valid = pd.Series(False, index=cal)
    for d, (o, h, lo, c) in spec.items():
        ts = pd.Timestamp(d)
        for k, v in zip(("open", "high", "low", "close"), (o, h, lo, c)):
            cols[k].loc[ts] = v
        valid.loc[ts] = True
    return cr.Bars(cols["open"], cols["high"], cols["low"], cols["close"], valid)


def flat(price=100.0, first=FIRST, last=LAST, skip=()):
    return {
        first + timedelta(days=i): (price, price * 1.01, price * 0.99, price)
        for i in range((last - first).days + 1)
        if first + timedelta(days=i) not in skip
    }


def shortlist(rows):
    return pd.DataFrame([{"date": d.isoformat(), "ticker": t, "rank": r} for d, t, r in rows])


def d(n):
    return FIRST + timedelta(days=n)


def events(acct, kind):
    return [e for e in acct.events if e["type"] == kind]


class Machinery(unittest.TestCase):
    def assertClean(self, acct):
        self.assertEqual(cr.check_invariants(acct), [])
        self.assertTrue(cr.tested_accounting_crosscheck(acct)["match"])

    def test_reservation_fill_fees_and_time_exit(self):
        b = {"AAA": bars(flat())}
        acct = cr.run(shortlist([(d(0), "AAA", 1)]), b, FIRST, LAST, P)
        order = next(e for e in events(acct, "DECISION") if e["decision"] == "ORDER")
        # the night of the decision: cash only reserved
        self.assertEqual(acct.daily[0]["reserved"], order["notional"])
        self.assertEqual(acct.daily[0]["cash"], P.start_cash)
        self.assertAlmostEqual(order["notional"] * P.loss_fraction, P.risk * P.start_cash)
        fill = events(acct, "ENTRY")[0]
        self.assertEqual(fill["day"], d(1).isoformat())  # the next UTC open
        self.assertAlmostEqual(fill["fill_price"], 100.0 * (1 + P.slip))
        self.assertAlmostEqual(fill["units"] * fill["fill_price"] * (1 + P.fee), order["notional"])
        self.assertAlmostEqual(acct.daily[1]["reserved"], 0.0)
        ex = events(acct, "EXIT")[0]
        self.assertEqual(
            (ex["reason"], ex["bar_index"], ex["day"]), ("TIME_EXIT", 5, d(5).isoformat())
        )
        self.assertAlmostEqual(ex["fill_price"], 100.0 * (1 - P.slip))
        self.assertLess(ex["pnl"], 0)  # flat price: costs only
        self.assertAlmostEqual(acct.cash, P.start_cash + ex["pnl"])
        self.assertClean(acct)

    def test_stop_target_gap_and_ambiguous_bar(self):
        F = 100.0 * (1 + P.slip)
        stop, target = F * 0.95, F * 1.10
        spec = flat()
        spec_stop = {**spec, d(3): (100.0, 100.5, stop - 0.01, 99.0)}
        spec_target = {**spec, d(2): (100.0, target + 0.01, 99.5, 105.0)}
        spec_gap = {**spec, d(3): (90.0, 91.0, 89.0, 90.5)}
        spec_both = {**spec, d(2): (100.0, target + 1, stop - 1, 100.0)}
        spec_gap_up = {**spec, d(2): (120.0, 121.0, 119.0, 120.0)}
        cases = {
            "STOP": spec_stop,
            "TARGET": spec_target,
            "STOP_GAP": spec_gap,
            "AMBIG": spec_both,
            "TARGET_GAP": spec_gap_up,
        }
        for name, sp in cases.items():
            acct = cr.run(shortlist([(d(0), "AAA", 1)]), {"AAA": bars(sp)}, FIRST, LAST, P)
            ex = events(acct, "EXIT")[0]
            with self.subTest(name):
                if name == "STOP":
                    self.assertEqual((ex["reason"], ex["raw_price"]), ("STOP", stop))
                elif name == "TARGET":
                    self.assertEqual((ex["reason"], ex["raw_price"]), ("TARGET", target))
                elif name == "STOP_GAP":
                    self.assertEqual(
                        (ex["reason"], ex["raw_price"]), ("STOP_GAP", 90.0)
                    )  # worse than the stop
                    self.assertLess(ex["net_return"], -P.loss_fraction)
                elif name == "AMBIG":
                    self.assertEqual((ex["reason"], ex.get("ambiguous")), ("STOP", True))
                    self.assertEqual(acct.counters["ambiguous_bar"], 1)
                else:
                    self.assertEqual(
                        (ex["reason"], ex["raw_price"]), ("TARGET_GAP", target)
                    )  # no gap credit
                self.assertClean(acct)

    def test_entry_bar_stop_counts_as_bar_one(self):
        F = 100.0 * (1 + P.slip)
        sp = {**flat(), d(1): (100.0, 100.2, F * 0.95 - 0.01, 96.0)}
        acct = cr.run(shortlist([(d(0), "AAA", 1)]), {"AAA": bars(sp)}, FIRST, LAST, P)
        ex = events(acct, "EXIT")[0]
        self.assertEqual((ex["reason"], ex["bar_index"], ex["day"]), ("STOP", 1, d(1).isoformat()))

    def test_missing_entry_bar_is_rejected_and_releases_cash(self):
        b = {"AAA": bars(flat(skip={d(1)}))}
        acct = cr.run(shortlist([(d(0), "AAA", 1)]), b, FIRST, LAST, P)
        self.assertEqual(events(acct, "ENTRY")[0]["status"], "REJECTED_MISSING_ENTRY_BAR")
        self.assertEqual((acct.cash, acct.reserved), (P.start_cash, 0.0))
        self.assertEqual(events(acct, "EXIT"), [])
        self.assertClean(acct)

    def test_missing_bars_while_held_and_a_rolled_time_exit(self):
        b = {"AAA": bars(flat(skip={d(3), d(5)}))}  # d(5) is the deadline
        acct = cr.run(shortlist([(d(0), "AAA", 1)]), b, FIRST, LAST, P)
        ex = events(acct, "EXIT")[0]
        self.assertEqual((ex["reason"], ex["day"]), ("TIME_EXIT_ROLLED", d(6).isoformat()))
        self.assertEqual(acct.counters["missing_bar_while_held"], 2)
        self.assertEqual(acct.counters["time_exit_rolled"], 1)
        stale = [row for row in acct.daily if row["stale_marks"]]
        self.assertEqual([row["day"] for row in stale], [d(3).isoformat(), d(5).isoformat()])
        self.assertClean(acct)

    def test_duplicate_symbol_daily_limit_and_risk_limit(self):
        b = {t: bars(flat()) for t in ("A", "B", "C", "D", "E")}
        rows = [
            (d(0), "A", 1),
            (d(0), "B", 2),
            (d(0), "C", 3),
            (d(0), "D", 4),  # 4th: daily limit
            (d(1), "A", 1),  # held: duplicate
            (d(1), "E", 2),
        ]  # 3 open = 1.5%: risk limit
        acct = cr.run(shortlist(rows), b, FIRST, LAST, P)
        decisions = [
            (e["ticker"], e["signal_day"], e["decision"]) for e in events(acct, "DECISION")
        ]
        self.assertEqual(
            decisions[:6],
            [
                ("A", d(0).isoformat(), "ORDER"),
                ("B", d(0).isoformat(), "ORDER"),
                ("C", d(0).isoformat(), "ORDER"),
                ("D", d(0).isoformat(), "SKIP_DAILY_LIMIT"),
                ("A", d(1).isoformat(), "SKIP_DUPLICATE_SYMBOL"),
                ("E", d(1).isoformat(), "SKIP_RISK_LIMIT"),
            ],
        )
        self.assertLessEqual(max(row["open_positions"] for row in acct.daily), 3)
        self.assertClean(acct)

    def test_insufficient_cash(self):
        greedy = cr.Policy(risk=0.2, max_risk=1.0)  # a notional larger than the account
        acct = cr.run(shortlist([(d(0), "A", 1)]), {"A": bars(flat())}, FIRST, LAST, greedy)
        self.assertEqual(events(acct, "DECISION")[0]["decision"], "SKIP_INSUFFICIENT_CASH")
        self.assertClean(acct)

    def test_overlapping_positions_share_cash_and_reconcile(self):
        b = {t: bars(flat(100 + i)) for i, t in enumerate("ABC")}
        acct = cr.run(
            shortlist([(d(0), "A", 1), (d(1), "B", 1), (d(2), "C", 1)]), b, FIRST, LAST, P
        )
        self.assertEqual(max(row["open_positions"] for row in acct.daily), 3)
        self.assertEqual(len(events(acct, "EXIT")), 3)
        self.assertClean(acct)

    def test_weekends_are_trading_days(self):
        friday = date(2023, 3, 3)
        b = {"A": bars(flat())}
        acct = cr.run(shortlist([(friday - timedelta(days=1), "A", 1)]), b, FIRST, LAST, P)
        fill, ex = events(acct, "ENTRY")[0], events(acct, "EXIT")[0]
        self.assertEqual(fill["day"], friday.isoformat())
        self.assertEqual(
            ex["day"], (friday + timedelta(days=4)).isoformat()
        )  # Tuesday: Sat and Sun count

    def test_end_of_data_leaves_unresolved_and_unfilled(self):
        b = {"A": bars(flat()), "B": bars(flat())}
        acct = cr.run(
            shortlist([(LAST - timedelta(days=2), "A", 1), (LAST, "B", 1)]), b, FIRST, LAST, P
        )
        unresolved, unfilled = events(acct, "UNRESOLVED"), events(acct, "UNFILLED")
        self.assertEqual([u["ticker"] for u in unresolved], ["A"])
        self.assertEqual(unresolved[0]["valued_at_close_of"], LAST.isoformat())
        self.assertEqual([u["ticker"] for u in unfilled], ["B"])
        self.assertEqual(events(acct, "EXIT"), [])
        self.assertClean(acct)
        s = cr.summarize(acct)
        self.assertAlmostEqual(
            s["end_equity"], P.start_cash + s["realized_pnl"] + s["unrealized_pnl"]
        )

    def test_entry_delay_waits_one_more_bar(self):
        delayed = cr.Policy(entry_delay=1)
        acct = cr.run(shortlist([(d(0), "A", 1)]), {"A": bars(flat())}, FIRST, LAST, delayed)
        self.assertEqual(events(acct, "ENTRY")[0]["day"], d(2).isoformat())
        self.assertEqual(acct.daily[1]["reserved"], events(acct, "DECISION")[0]["notional"])
        self.assertClean(acct)

    def test_doubled_costs_lose_more_on_the_same_path(self):
        base = cr.run(shortlist([(d(0), "A", 1)]), {"A": bars(flat())}, FIRST, LAST, P)
        double = cr.run(
            shortlist([(d(0), "A", 1)]),
            {"A": bars(flat())},
            FIRST,
            LAST,
            cr.Policy(fee=0.002, slip=0.002),
        )
        self.assertLess(cr.summarize(double)["net_return"], cr.summarize(base)["net_return"])
        self.assertAlmostEqual(events(double, "DECISION")[0]["planned_risk"], P.risk * P.start_cash)

    def test_cash_only_reference_is_flat(self):
        acct = cr.run(None, {}, FIRST, LAST, P)
        self.assertEqual({row["equity"] for row in acct.daily}, {P.start_cash})

    def test_repeat_runs_are_identical(self):
        b = {t: bars(flat(100 + i)) for i, t in enumerate("ABCD")}
        sl = shortlist([(d(i), t, 1) for i, t in enumerate("ABCD")])
        self.assertEqual(
            cr.fingerprint(cr.run(sl, b, FIRST, LAST, P)),
            cr.fingerprint(cr.run(sl, b, FIRST, LAST, P)),
        )

    def test_bars_from_panel_marks_missing_and_incomplete_bars_invalid(self):
        panel = pd.DataFrame(
            [
                {
                    "date": "2023-03-01",
                    "ticker": "A",
                    "open": 1,
                    "high": 1,
                    "low": 1,
                    "close": 1,
                    "volume": 1,
                    "value": 1,
                    "complete_bar": True,
                },
                {
                    "date": "2023-03-02",
                    "ticker": "A",
                    "open": 1,
                    "high": 1,
                    "low": 1,
                    "close": 1,
                    "volume": 1,
                    "value": 1,
                    "complete_bar": False,
                },
                {
                    "date": "2023-03-04",
                    "ticker": "A",
                    "open": 1,
                    "high": 1,
                    "low": 1,
                    "close": 1,
                    "volume": 0,
                    "value": 1,
                    "complete_bar": True,
                },
            ]
        )
        b = cr.bars_from_panel(panel, date(2023, 3, 1), date(2023, 3, 5))["A"]
        self.assertEqual(
            [b.get(date(2023, 3, k)) is not None for k in range(1, 6)],
            [True, False, False, False, False],
        )
        self.assertEqual(b.last_close(date(2023, 3, 5)), (1.0, date(2023, 3, 1)))


if __name__ == "__main__":
    unittest.main()


class ReviewFixes(unittest.TestCase):
    """Pre-freeze review: planned-risk cap, independent trade audit, year-end valuation bounds."""

    def test_the_audit_rederives_every_trade_and_catches_a_tampered_exit(self):
        F = 100.0 * (1 + P.slip)
        spec = {**flat(), d(3): (100.0, 100.5, F * 0.95 - 0.01, 99.0)}
        b = {
            "A": bars(spec),
            "B": bars(flat(50.0)),
            "C": bars({**flat(80.0), d(4): (70.0, 71.0, 69.0, 70.5)}),
        }
        acct = cr.run(
            shortlist([(d(0), "A", 1), (d(0), "B", 2), (d(1), "C", 1)]), b, FIRST, LAST, P
        )
        self.assertEqual(cr.audit_trades(acct, b), [])
        tampered = next(e for e in acct.events if e["type"] == "EXIT")
        tampered["raw_price"] *= 1.01
        self.assertTrue(any("but the bars give" in x for x in cr.audit_trades(acct, b)))

    def test_a_small_loss_does_not_shrink_the_account_below_three_positions(self):
        dip = {**flat(), d(2): (100.0, 100.5, 98.0, 98.0)}  # A down 2% at the close of d(2)
        b = {"A": bars(dip), "B": bars(flat()), "C": bars(flat())}
        acct = cr.run(
            shortlist([(d(0), "A", 1), (d(1), "B", 1), (d(2), "C", 1)]), b, FIRST, LAST, P
        )
        self.assertEqual([e["decision"] for e in events(acct, "DECISION")], ["ORDER"] * 3)
        self.assertEqual(max(row["open_positions"] for row in acct.daily), 3)

    def test_an_open_gain_does_not_block_new_entries(self):
        up = {**flat(), d(2): (100.0, 109.0, 99.0, 109.0)}  # A up 9% at the close, below its target
        b = {"A": bars(up), "B": bars(flat())}
        acct = cr.run(shortlist([(d(0), "A", 1), (d(2), "B", 1)]), b, FIRST, LAST, P)
        self.assertEqual([e["decision"] for e in events(acct, "DECISION")], ["ORDER", "ORDER"])

    def test_year_end_positions_carry_valuation_bounds(self):
        b = {"A": bars(flat())}
        acct = cr.run(shortlist([(LAST - timedelta(days=2), "A", 1)]), b, FIRST, LAST, P)
        u = events(acct, "UNRESOLVED")[0]
        self.assertLess(u["value_if_stopped"], u["net_liquidation_value"])
        self.assertLess(u["net_liquidation_value"], u["value"])
        self.assertLess(u["value"], u["value_if_target"])
        self.assertEqual(u["bars_held"], 2)
        self.assertEqual(cr.audit_trades(acct, b), [])
