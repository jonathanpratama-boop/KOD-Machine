"""CRYPTO_ACCOUNT_v1.1: orders, fills, cancels, stops, time exits and cash from recorded spot quotes only, run through
the same cycle the command uses, with a controlled clock and quote feed (fixtures). Includes the v1.1 regressions:
failed fetches, stale quotes and impossible timestamps."""

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from idxsig import crypto_account as ca
from idxsig import paper

T0 = datetime(2026, 11, 1, 0, 30, tzinfo=timezone.utc)


def _decision(ticker, verdict="BUY ON TRIGGER", quote=100.0, n=0):
    return {
        "type": "DECISION",
        "market": "CRYPTO",
        "decision_id": f"SCAN-CRYPTO-2026-10-31-{ticker}",
        "decision": verdict,
        "reason": "frozen policy reason",
        "instrument": {"ticker": ticker},
        "signal_session": "2026-10-31",
        "decided_at": f"2026-11-01T00:2{n}:00Z",
        "verified_price": {"quote": quote},
        "record_hash": f"decision-{ticker}",
    }


def _quote(symbol, bid, ask, t):
    return {
        "type": ca.QUOTE,
        "account": ca.ACCOUNT_ID,
        "symbol": symbol,
        "bid": bid,
        "ask": ask,
        "observed_at": ca._stamp(t),
        "source": "fixture",
    }


class Market:
    """A clock and a spot book. Each fetch observes at the current time, then one second passes."""

    def __init__(self):
        self.t = T0
        self.book: dict[str, tuple[float, float]] = {}

    def clock(self):
        return self.t

    def fetch(self, symbols):
        def get(sym):
            if sym not in self.book:
                raise ConnectionError("no answer")
            bid, ask = self.book[sym]
            return bid, ask, "fixture"

        with mock.patch.object(ca, "utc_stamp", lambda: ca._stamp(self.t)):
            out = ca.fetch_quotes(symbols, get)
        self.t += timedelta(seconds=1)
        return out


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.ledger = Path(tmp.name) / "crypto_account.jsonl"
        p = mock.patch.object(ca, "LEDGER", self.ledger)
        p.start()
        self.addCleanup(p.stop)
        self.m = Market()

    def append(self, recs, **kwargs):
        return paper.append(recs, path=self.ledger, **kwargs)

    def run_cycle(self, cands, advance=timedelta(0)):
        self.m.t += advance
        return ca.cycle(cands, self.m.fetch, self.m.clock, self.append)

    @staticmethod
    def kinds(run):
        return [
            (
                r["type"],
                r.get("status") or r.get("exit_reason") or r.get("reason", "").split(":")[0],
            )
            for r in run["events"]
        ]

    def of(self, kind):
        return [r for r in ca.lines() if r["type"] == kind]


class Lifecycle(Base):
    def test_order_fill_stop_and_cash_reconcile(self):
        cands = [_decision("AAA", quote=100.0)]
        self.m.book["AAAUSDT"] = (100.4, 100.5)
        run = self.run_cycle(cands)
        # ordered on the fresh decision quote, filled on the quote observed right after the order
        self.assertEqual(self.kinds(run), [("ACCT_ORDER", ""), ("ACCT_ENTRY", "FILLED")])
        order, fill = self.of(ca.ORDER)[0], self.of(ca.ENTRY)[0]
        self.assertAlmostEqual(order["limit"], 101.0)
        self.assertLessEqual(order["planned_risk_usd"], 0.005 * ca.START_CASH + 1e-6)
        self.assertGreaterEqual(fill["filled_at"], order["made_at"])
        self.assertNotEqual(fill["quote_record_hash"], order["decision_quote_record_hash"])
        self.assertEqual((fill["price"], fill["stop"]), (100.5, 100.5 * 0.95))
        self.assertEqual(fill["deadline"], ca._stamp(ca._t(fill["filled_at"]) + ca.HOLD))
        self.assertEqual(run["mark"]["reserved"], 0.0)  # the mark is taken after the fill
        self.assertEqual(ca.verify(), [])
        # a later quote with its bid through the stop: exits at that bid, below the stop
        self.m.book["AAAUSDT"] = (94.0, 94.1)
        run = self.run_cycle(cands, timedelta(hours=7))
        self.assertEqual(self.kinds(run), [("ACCT_EXIT", "STOP")])
        exit_ = self.of(ca.EXIT)[0]
        self.assertEqual(exit_["price"], 94.0)
        qty = order["quantity"]
        expected = qty * 94.0 * (1 - ca.FEE) - qty * 100.5 * (1 + ca.FEE)
        self.assertAlmostEqual(exit_["net_pnl_usd"], expected, places=6)
        st = ca.account(ca.lines())
        self.assertAlmostEqual(st["cash"], ca.START_CASH + exit_["net_pnl_usd"], places=6)
        self.assertEqual(
            (st["reserved"], st["open"], st["realized"]), (0.0, [], exit_["net_pnl_usd"])
        )
        self.assertEqual(ca.verify(), [])

    def test_time_exit_at_the_first_quote_after_the_deadline(self):
        cands = [_decision("BBB", quote=10.0)]
        self.m.book["BBBUSDT"] = (9.99, 10.0)
        self.run_cycle(cands)
        self.m.book["BBBUSDT"] = (10.4, 10.41)
        self.run_cycle(cands, timedelta(days=2))
        st = ca.account(ca.lines())
        self.assertEqual((len(st["open"]), st["open"][0]["bid"]), (1, 10.4))
        self.assertGreater(st["unrealized"], 0)
        self.m.book["BBBUSDT"] = (10.6, 10.61)
        run = self.run_cycle(cands, timedelta(days=3, hours=1))
        self.assertEqual(self.kinds(run), [("ACCT_EXIT", "TIME_EXIT")])
        self.assertGreater(run["events"][0]["net_pnl_usd"], 0)
        self.assertAlmostEqual(run["events"][0]["hours_after_deadline"], 1.0, places=1)
        self.assertEqual(ca.verify(), [])

    def test_cancel_before_the_fill_releases_the_reservation(self):
        cands = [_decision("CCC", quote=1.0)]
        self.m.book["CCCUSDT"] = (1.05, 1.06)  # above the limit 1.01: no fill
        run = self.run_cycle(cands)
        self.assertEqual(self.kinds(run), [("ACCT_ORDER", "")])
        self.assertGreater(run["mark"]["reserved"], 0)  # the mark sees the reservation
        order = self.of(ca.ORDER)[0]
        self.m.t += timedelta(minutes=5)
        self.append([ca.cancel(ca.lines(), order["record_hash"], "owner cancel", self.m.t)])
        self.m.book["CCCUSDT"] = (1.0, 1.005)
        run = self.run_cycle(cands, timedelta(minutes=5))
        self.assertEqual(self.kinds(run), [])  # a cancelled order never fills
        st = ca.account(ca.lines())
        self.assertEqual(
            (st["cash"], st["reserved"], st["free_cash"]), (ca.START_CASH, 0.0, ca.START_CASH)
        )
        with self.assertRaises(ValueError):
            ca.cancel(ca.lines(), order["record_hash"], "again", self.m.t)
        self.assertEqual(ca.verify(), [])

    def test_an_unfilled_order_expires(self):
        cands = [_decision("DDD", quote=1.0)]
        self.m.book["DDDUSDT"] = (1.05, 1.06)
        self.run_cycle(cands)
        self.m.book["DDDUSDT"] = (1.0, 1.005)  # cheap again, but after the order expired
        run = self.run_cycle(cands, timedelta(hours=2))
        self.assertEqual(self.kinds(run), [("ACCT_ENTRY", "EXPIRED_UNFILLED")])
        self.assertIn("1 quote(s) observed, 0 fetch failure(s)", run["events"][0]["reason"])
        self.assertEqual(ca.account(ca.lines())["reserved"], 0.0)

    def test_pass_is_declined_and_never_bought(self):
        run = self.run_cycle([_decision("EEE", verdict="PASS")])
        self.assertEqual(self.kinds(run), [("ACCT_DECLINE", "POLICY_PASS")])
        self.assertEqual(ca.symbols_needed(ca.lines(), [_decision("EEE", verdict="PASS")]), [])
        self.assertEqual(ca.account(ca.lines())["cash"], ca.START_CASH)

    def test_the_risk_budget_caps_open_orders(self):
        tickers = ("G1", "G2", "G3", "G4")
        cands = [_decision(t, quote=1.0, n=i) for i, t in enumerate(tickers)]
        for t in tickers:
            self.m.book[f"{t}USDT"] = (1.05, 1.06)
        run = self.run_cycle(cands)
        self.assertEqual([k for k, _ in self.kinds(run)], [ca.ORDER] * 3 + [ca.DECLINE])
        self.assertIn("LIMIT_", run["events"][3]["reason"])


class StaleQuotes(Base):
    """v1.1 regressions: a failed fetch never becomes a fill, an old quote never becomes a decision or a fill."""

    def test_failed_current_fetch_never_reserves_on_one_minute_old_cache(self):
        self.append([_quote("AAAUSDT", 99.0, 99.1, T0 - timedelta(minutes=1))])
        before = ca.account(ca.lines())
        run = self.run_cycle([_decision("AAA")])
        self.assertEqual(self.kinds(run), [(ca.DECLINE, "NO_FRESH_QUOTE")])
        self.assertIn("the fetch failed", run["events"][0]["reason"])
        self.assertEqual(len(self.of(ca.QUOTE_ERROR)), 1)
        self.assertEqual((self.of(ca.ORDER), self.of(ca.ENTRY)), ([], []))
        self.assertEqual(ca.account(ca.lines()), before)
        self.assertEqual(run["mark"]["reserved"], 0.0)
        self.assertEqual(ca.verify(), [])

    def test_failed_fetch_preserves_existing_pending_reservation(self):
        cands = [_decision("AAA")]
        self.m.book["AAAUSDT"] = (101.5, 101.6)
        self.run_cycle(cands)
        before = ca.account(ca.lines())
        del self.m.book["AAAUSDT"]
        run = self.run_cycle(cands, timedelta(minutes=1))
        self.assertEqual(self.kinds(run), [])
        self.assertEqual(ca.account(ca.lines()), before)
        self.assertEqual((self.of(ca.ENTRY), self.of(ca.CANCEL)), ([], []))
        self.assertEqual(ca.verify(), [])

    def test_failed_fetch_preserves_open_position_without_fabricated_exit(self):
        cands = [_decision("AAA")]
        self.m.book["AAAUSDT"] = (99.0, 99.1)
        self.run_cycle(cands)
        before = ca.account(ca.lines())
        del self.m.book["AAAUSDT"]
        run = self.run_cycle(cands, timedelta(minutes=1))
        self.assertEqual(self.kinds(run), [])
        self.assertEqual(ca.account(ca.lines()), before)
        self.assertEqual(self.of(ca.EXIT), [])
        self.assertEqual(ca.verify(), [])

    def test_same_second_failure_and_recovery_follow_ledger_order(self):
        self.append([_quote("AAAUSDT", 99.0, 99.1, T0)])
        self.append(self.m.fetch(["AAAUSDT"]))  # real failure at the same second
        self.assertIsNone(ca.fresh_quote(ca.lines(), "AAAUSDT", self.m.t)[0])
        self.append([_quote("AAAUSDT", 99.0, 99.2, T0)])
        self.assertIsNotNone(ca.fresh_quote(ca.lines(), "AAAUSDT", self.m.t)[0])

    def test_future_failure_does_not_block_current_quote(self):
        self.append([_quote("AAAUSDT", 99.0, 99.1, T0)])
        self.m.t += timedelta(hours=1)
        self.append(self.m.fetch(["AAAUSDT"]))
        self.assertIsNotNone(ca.fresh_quote(ca.lines(), "AAAUSDT", T0)[0])

    def test_later_success_recovers_without_retrying_declined_decision(self):
        cands = [_decision("AAA")]
        self.append([_quote("AAAUSDT", 99.0, 99.1, T0 - timedelta(minutes=1))])
        self.run_cycle(cands)
        self.m.book["AAAUSDT"] = (99.0, 99.1)
        self.assertEqual(self.kinds(self.run_cycle(cands)), [])
        new = {**cands[0], "decision_id": "new-independent-decision"}
        self.assertEqual(self.kinds(self.run_cycle([new])), [(ca.ORDER, ""), (ca.ENTRY, "FILLED")])
        self.assertEqual(ca.verify(), [])

    def test_v12_verifier_flags_order_after_failure_but_preserves_v11(self):
        self.append([_quote("AAAUSDT", 99.0, 99.1, T0 - timedelta(minutes=1))])
        order = ca.decide(ca.lines(), [_decision("AAA")], T0)[0]
        self.append(self.m.fetch(["AAAUSDT"]))
        self.append([order])  # intentionally bypass the new eligibility gate
        self.assertTrue(any("no eligible decision quote" in p for p in ca.verify()))
        # Historical version semantics are not retroactively rewritten.
        legacy = [{**r, "rules": "CRYPTO_ACCOUNT_v1.1"} if r["type"] == ca.ORDER else r
                  for r in ca.lines()]
        with mock.patch.object(ca, "lines", return_value=legacy):
            self.assertEqual(ca.verify(), [])

    def test_failed_fetch_is_recorded_and_the_buy_declined(self):
        run = self.run_cycle([_decision("FFF")])  # the feed does not answer for FFF
        errors = self.of(ca.QUOTE_ERROR)
        self.assertEqual([e["symbol"] for e in errors], ["FFFUSDT"])
        self.assertIn("ConnectionError", errors[0]["error"])
        self.assertEqual(self.kinds(run), [("ACCT_DECLINE", "NO_FRESH_QUOTE")])
        self.assertIn("the fetch failed at", run["events"][0]["reason"])
        self.assertEqual(self.of(ca.ORDER), [])

    def test_a_ten_day_old_quote_is_not_used_when_the_fetch_fails(self):
        # Ace's case: an old cached quote under the limit, and today's fetch fails
        old = T0 - timedelta(days=10)
        self.append([_quote("AAAUSDT", 99.0, 99.1, old)])
        run = self.run_cycle([_decision("AAA", quote=100.0)])
        self.assertEqual(self.kinds(run), [("ACCT_DECLINE", "NO_FRESH_QUOTE")])
        reason = run["events"][0]["reason"]
        self.assertIn("the fetch failed", reason)
        self.assertIn(f"newest recorded quote is from {ca._stamp(old)}", reason)
        self.assertEqual((self.of(ca.ORDER), self.of(ca.ENTRY)), ([], []))

    def test_quotes_from_before_the_order_or_after_the_clock_cannot_fill_it(self):
        self.m.book["AAAUSDT"] = (101.5, 101.6)  # above the limit at the decision
        self.run_cycle([_decision("AAA", quote=100.0)])
        order = self.of(ca.ORDER)[0]
        self.append(
            [_quote("AAAUSDT", 99.0, 99.1, T0 - timedelta(days=10))]
        )  # the old cache, appended late
        self.assertEqual(ca.settle(ca.lines(), self.m.t), [])  # still pending, nothing back-dated
        self.append(
            [_quote("AAAUSDT", 99.0, 99.1, self.m.t + timedelta(minutes=30))]
        )  # stamped in the future
        self.assertEqual(ca.settle(ca.lines(), self.m.t), [])
        self.assertIsNone(ca.fresh_quote(ca.lines(), "AAAUSDT", T0 - timedelta(days=1))[0])
        self.assertEqual(ca.account(ca.lines())["reserved"], order["reserved_usd"])

    def test_failed_fetches_while_an_order_lives_expire_it_explicitly(self):
        cands = [_decision("AAA", quote=100.0)]
        self.m.book["AAAUSDT"] = (101.5, 101.6)
        self.run_cycle(cands)
        del self.m.book["AAAUSDT"]
        self.run_cycle(cands, timedelta(minutes=30))
        run = self.run_cycle(cands, timedelta(hours=1))
        self.assertEqual(self.kinds(run), [("ACCT_ENTRY", "EXPIRED_UNFILLED")])
        self.assertIn("1 fetch failure(s)", run["events"][0]["reason"])
        self.assertEqual(ca.verify(), [])

    def test_exit_waits_for_a_fresh_quote_and_records_how_late(self):
        cands = [_decision("BBB", quote=10.0)]
        self.m.book["BBBUSDT"] = (9.99, 10.0)
        self.run_cycle(cands)
        del self.m.book["BBBUSDT"]  # the deadline passes while the feed is down
        run = self.run_cycle(cands, timedelta(days=5, hours=2))
        self.assertEqual(self.kinds(run), [])  # no exit on an old price
        self.assertIn("waiting for a fresh quote", ca.render(ca.lines()))
        self.m.book["BBBUSDT"] = (10.2, 10.21)
        run = self.run_cycle(cands, timedelta(hours=10))
        self.assertEqual(self.kinds(run), [("ACCT_EXIT", "TIME_EXIT")])
        self.assertGreater(run["events"][0]["hours_after_deadline"], 11.9)
        self.assertEqual(ca.verify(), [])


class LedgerChecks(Base):
    """verify() rejects fills and exits that could not have happened."""

    def _pending(self, ticker):
        self.m.book[f"{ticker}USDT"] = (101.5, 101.6)  # no fill in the run
        self.run_cycle([_decision(ticker, quote=100.0)])
        return self.of(ca.ORDER)[0]

    def _entry(self, order, quote, **fields):
        return {
            "type": ca.ENTRY,
            "account": ca.ACCOUNT_ID,
            "arm": ca.ARM,
            "set_id": order["set_id"],
            "ticker": order["ticker"],
            "order_record_hash": order["record_hash"],
            "status": "FILLED",
            "price": quote["ask"],
            "shares": order["quantity"],
            "cost_in": ca.FEE,
            "stop": quote["ask"] * 0.95,
            "filled_at": quote["observed_at"],
            "deadline": ca._stamp(ca._t(quote["observed_at"]) + ca.HOLD),
            "quote_record_hash": quote["record_hash"],
            "recorded_at": ca._stamp(self.m.t),
            **fields,
        }

    def test_a_fill_off_the_recorded_ask_is_flagged(self):
        order = self._pending("HHH")
        q = self.of(ca.QUOTE)[-1]
        self.append([self._entry(order, q, price=99.0)])
        self.assertTrue(any("qualifying recorded ask" in p for p in ca.verify()))

    def test_a_back_dated_fill_with_a_past_deadline_is_flagged(self):
        order = self._pending("JJJ")
        (old,) = self.append([_quote("JJJUSDT", 99.0, 99.1, T0 - timedelta(days=10))])
        self.append([self._entry(order, old)])
        problems = ca.verify()
        self.assertTrue(
            any("not observed while the order was live" in p for p in problems), problems
        )

    def test_a_deadline_not_from_the_fill_is_flagged(self):
        order = self._pending("KKK")
        self.m.book["KKKUSDT"] = (100.0, 100.1)
        (q,) = self.append(self.m.fetch(["KKKUSDT"]))
        self.append([self._entry(order, q, deadline=ca._stamp(T0 - timedelta(days=5)))])
        problems = ca.verify()
        self.assertTrue(any("holding deadline not from the fill" in p for p in problems), problems)

    def test_a_time_exit_before_the_deadline_is_flagged(self):
        self.m.book["AAAUSDT"] = (100.4, 100.5)
        self.run_cycle([_decision("AAA", quote=100.0)])
        order, fill = self.of(ca.ORDER)[0], self.of(ca.ENTRY)[0]
        self.m.t += timedelta(hours=1)
        (later,) = self.append(self.m.fetch(["AAAUSDT"]))
        self.append(
            [
                {
                    "type": ca.EXIT,
                    "account": ca.ACCOUNT_ID,
                    "arm": ca.ARM,
                    "set_id": order["set_id"],
                    "ticker": "AAA",
                    "order_record_hash": order["record_hash"],
                    "exit_reason": "TIME_EXIT",
                    "price": later["bid"],
                    "cost_out": ca.FEE,
                    "exited_at": later["observed_at"],
                    "quote_record_hash": later["record_hash"],
                    "net_pnl_usd": 0.0,
                    "net_return": 0.0,
                    "recorded_at": ca._stamp(self.m.t),
                }
            ]
        )
        self.assertGreater(fill["deadline"], later["observed_at"])
        self.assertTrue(any("time exit before the deadline" in p for p in ca.verify()))


if __name__ == "__main__":
    unittest.main()
