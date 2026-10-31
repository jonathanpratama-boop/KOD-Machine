"""CRYPTO_ACCOUNT_v1: orders, fills, cancels, stops, time exits and cash from recorded spot quotes only (fixtures)."""

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


class CryptoAccount(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.ledger = Path(tmp.name) / "crypto_account.jsonl"
        p = mock.patch.object(ca, "LEDGER", self.ledger)
        p.start()
        self.addCleanup(p.stop)

    def _run(self, quotes, cands, now):
        if quotes:
            paper.append(quotes, path=self.ledger)
        new = ca.step(ca.lines(), cands, now)
        if new:
            paper.append(new, path=self.ledger)
        paper.append([ca.mark(ca.lines(), now)], path=self.ledger)
        return new

    def _types(self, new):
        return [
            (r["type"], r.get("status") or r.get("exit_reason") or r.get("reason", "")[:12])
            for r in new
            if r["type"] != ca.MARK
        ]

    def test_order_fill_stop_and_cash_reconcile(self):
        cands = [_decision("AAA", quote=100.0)]
        new = self._run([_quote("AAAUSDT", 100.4, 100.5, T0)], cands, T0)
        # the order and its fill at the decision quote's ask (100.5 <= limit 101.0) in the same step
        self.assertEqual(self._types(new), [("ACCT_ORDER", "")])
        order = next(r for r in ca.lines() if r["type"] == ca.ORDER)
        self.assertAlmostEqual(order["limit"], 101.0)
        self.assertLessEqual(order["planned_risk_usd"], 0.005 * ca.START_CASH + 1e-6)
        st = ca.account(ca.lines())
        self.assertAlmostEqual(st["reserved"], order["reserved_usd"])
        last_mark = [r for r in ca.lines() if r["type"] == ca.MARK][-1]
        self.assertAlmostEqual(
            last_mark["reserved"], round(order["reserved_usd"], 2)
        )  # the mark sees it
        self.assertEqual(st["equity"], ca.START_CASH)  # a reservation is not a loss
        new = self._run([], cands, T0 + timedelta(minutes=1))
        self.assertEqual(self._types(new), [("ACCT_ENTRY", "FILLED")])
        fill = new[0]
        self.assertEqual((fill["price"], fill["stop"]), (100.5, 100.5 * 0.95))
        # a later quote whose bid is through the stop: exits at that bid, below the stop
        new = self._run(
            [_quote("AAAUSDT", 94.0, 94.1, T0 + timedelta(hours=7))], cands, T0 + timedelta(hours=7)
        )
        self.assertEqual(self._types(new), [("ACCT_EXIT", "STOP")])
        exit_ = new[0]
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
        self._run([_quote("BBBUSDT", 9.99, 10.0, T0)], cands, T0)
        self._run([], cands, T0 + timedelta(minutes=1))
        self._run(
            [_quote("BBBUSDT", 10.4, 10.41, T0 + timedelta(days=2))], cands, T0 + timedelta(days=2)
        )
        st = ca.account(ca.lines())
        self.assertEqual((len(st["open"]), st["open"][0]["bid"]), (1, 10.4))
        self.assertGreater(st["unrealized"], 0)
        new = self._run(
            [_quote("BBBUSDT", 10.6, 10.61, T0 + timedelta(days=5, hours=1))],
            cands,
            T0 + timedelta(days=5, hours=1),
        )
        self.assertEqual(self._types(new), [("ACCT_EXIT", "TIME_EXIT")])
        self.assertGreater(new[0]["net_pnl_usd"], 0)
        self.assertEqual(ca.verify(), [])

    def test_cancel_before_the_fill_releases_the_reservation(self):
        cands = [_decision("CCC", quote=1.0)]
        self._run(
            [_quote("CCCUSDT", 1.05, 1.06, T0)], cands, T0
        )  # ask above the limit 1.01: no fill yet
        order = next(r for r in ca.lines() if r["type"] == ca.ORDER)
        paper.append(
            [
                ca.cancel(
                    ca.lines(), order["record_hash"], "owner cancel", T0 + timedelta(minutes=5)
                )
            ],
            path=self.ledger,
        )
        new = self._run(
            [_quote("CCCUSDT", 1.0, 1.005, T0 + timedelta(minutes=10))],
            cands,
            T0 + timedelta(minutes=10),
        )
        self.assertEqual(self._types(new), [])  # a cancelled order never fills
        st = ca.account(ca.lines())
        self.assertEqual(
            (st["cash"], st["reserved"], st["free_cash"]), (ca.START_CASH, 0.0, ca.START_CASH)
        )
        with self.assertRaises(ValueError):
            ca.cancel(ca.lines(), order["record_hash"], "again", T0 + timedelta(minutes=11))
        self.assertEqual(ca.verify(), [])

    def test_an_unfilled_order_expires(self):
        cands = [_decision("DDD", quote=1.0)]
        self._run([_quote("DDDUSDT", 1.05, 1.06, T0)], cands, T0)
        new = self._run(
            [_quote("DDDUSDT", 1.0, 1.005, T0 + timedelta(hours=2))], cands, T0 + timedelta(hours=2)
        )
        self.assertEqual(
            self._types(new), [("ACCT_ENTRY", "EXPIRED_UNFILLED")]
        )  # cheap again, but too late
        self.assertEqual(ca.account(ca.lines())["reserved"], 0.0)

    def test_pass_is_declined_and_never_bought(self):
        new = self._run([], [_decision("EEE", verdict="PASS")], T0)
        self.assertEqual(self._types(new), [("ACCT_DECLINE", "POLICY_PASS:")])
        self.assertEqual(ca.symbols_needed(ca.lines(), [_decision("EEE", verdict="PASS")]), [])
        self.assertEqual(ca.account(ca.lines())["cash"], ca.START_CASH)

    def test_a_buy_without_a_recorded_quote_is_declined(self):
        new = self._run([], [_decision("FFF")], T0)
        self.assertEqual(self._types(new), [("ACCT_DECLINE", "NO_QUOTE: no")])

    def test_the_risk_budget_caps_open_orders(self):
        cands = [_decision(t, quote=1.0, n=i) for i, t in enumerate(("G1", "G2", "G3", "G4"))]
        quotes = [_quote(f"{t}USDT", 1.05, 1.06, T0) for t in ("G1", "G2", "G3", "G4")]
        new = self._run(quotes, cands, T0)
        kinds = [r["type"] for r in new if r["type"] != ca.MARK]
        self.assertEqual(kinds, [ca.ORDER] * 3 + [ca.DECLINE])
        self.assertIn("LIMIT_", new[3]["reason"])

    def test_verify_catches_a_fill_off_the_recorded_ask(self):
        cands = [_decision("HHH", quote=100.0)]
        self._run([_quote("HHHUSDT", 100.4, 100.5, T0)], cands, T0)
        new = ca.settle(ca.lines(), T0 + timedelta(minutes=1))
        new[0]["price"] = 99.0
        paper.append(new, path=self.ledger)
        self.assertTrue(any("qualifying recorded ask" in p for p in ca.verify()))


if __name__ == "__main__":
    unittest.main()
