"""Offline account integration: economic invariants and adversarial event order."""

import hashlib
import importlib.util
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from idxsig.runtime.account import PaperAccount, SYMBOLS
from idxsig.runtime import account as runtime

D = Decimal
T0 = "2026-11-02T00:00:10Z"


def profile(kind="synthetic", **changes):
    venue = "SYNTHETIC_SPOT" if kind == "synthetic" else "BINANCE_SPOT"
    p = {
        "id": "TEST_ACCOUNT_" + kind,
        "evidence_type": kind,
        "venue": venue,
        "quote_currency": "USDT",
        "initial_cash": "1000",
        "fee_rate": "0.001",
        "slippage": "0",
        "max_quote_age": 120,
        "expiry": 3600,
        "initialized_at": T0,
        "instruments": {
            s: {
                "tick_size": "0.01",
                "lot_step": "0.001",
                "min_notional": "5",
                "trading_status": "TRADING",
                "metadata_received_at": "2026-11-01T00:00:00Z",
                "evidence_id": "metadata:fixture",
            }
            for s in SYMBOLS
        },
    }
    p.update(changes)
    return p


def quote(symbol, second=10, *, bid=None, ask_size="100", kind="synthetic", **extra):
    bid = bid or ("100" if symbol == "BTCUSDT" else "200")
    t = f"2026-11-02T00:00:{second:02d}Z"
    q = {
        "symbol": symbol,
        "venue": "SYNTHETIC_SPOT" if kind == "synthetic" else "BINANCE_SPOT",
        "evidence_type": kind,
        "bid": bid,
        "ask": bid,
        "bid_size": "100",
        "ask_size": ask_size,
        "source_time": t,
        "received_at": t,
        "evidence_id": f"quote:{symbol}:{second}",
        "observation_id": f"obs:{symbol}:{second}",
    }
    q.update(extra)
    return q


def bars(kind="synthetic", signal_date="2026-11-01"):
    end = date.fromisoformat(signal_date)
    out = {}
    for symbol in SYMBOLS:
        rows = []
        for i in range(40):
            day = end - timedelta(days=39 - i)
            start = datetime.combine(day, datetime.min.time(), timezone.utc)
            finish = start + timedelta(days=1)
            value = D("100") + i + D(i % 3) / 3
            rows.append(
                {
                    "symbol": symbol,
                    "venue": "SYNTHETIC_SPOT" if kind == "synthetic" else "BINANCE_SPOT",
                    "evidence_type": kind,
                    "open_time": runtime.stamp(start),
                    "close_time": runtime.stamp(finish),
                    "open": str(value),
                    "high": str(value + 1),
                    "low": str(value - 1),
                    "close": str(value),
                    "received_at": runtime.stamp(finish),
                    "base_volume": "10000",
                    "quote_volume": "1000000",
                    "evidence_id": f"bars:{symbol}:{day}",
                }
            )
        out[symbol] = rows
    return out


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = profile()
        self.a = PaperAccount(self.tmp.name, self.p)

    def ready(self, acct=None, kind="synthetic"):
        acct = acct or self.a
        for s in SYMBOLS:
            acct.observe(quote(s, kind=kind))
        return acct.decide("2026-11-01", bars(kind), T0)

    def filled(self):
        self.ready()
        for s in SYMBOLS:
            self.a.observe(quote(s, 11))
        return self.a.snapshot("2026-11-02T00:00:11Z")

    def test_construction_and_failed_input_do_not_fabricate_account(self):
        self.assertEqual(self.a.snapshot(T0)["status"], "UNINITIALIZED")
        bad = quote("BTCUSDT", bid="NaN")
        with self.assertRaises(ValueError):
            self.a.observe(bad)
        self.assertFalse((Path(self.tmp.name) / "account.jsonl").exists())

    def test_shared_cash_and_realized_fee_conservation(self):
        s = self.filled()
        a = s["account"]
        self.assertEqual(len(s["fills"]), 2)
        self.assertLessEqual(D(a["gross_fraction"]), 1)
        self.assertGreaterEqual(D(a["cash_available"]), 0)
        debits = sum((-D(f["cash_change"]) for f in s["fills"]), D(0))
        self.assertEqual(D(a["cash_total"]) + debits, D("1000"))
        self.assertEqual(D(a["nav"]) + D(s["realized_fees"]), D("1000"))
        self.assertTrue(all(f["simulation_only"] for f in s["fills"]))

    def test_decision_quote_never_fills_and_retry_is_byte_identical(self):
        self.ready()
        old = Path(self.tmp.name, "account.jsonl").read_bytes()
        self.a.observe(quote("BTCUSDT"))
        self.assertEqual(Path(self.tmp.name, "account.jsonl").read_bytes(), old)
        self.assertEqual(self.a.snapshot(T0)["fills"], [])
        self.a.decide("2026-11-01", bars(), T0)
        self.assertEqual(Path(self.tmp.name, "account.jsonl").read_bytes(), old)

    def test_later_receipt_cannot_resurrect_request_started_before_intent(self):
        self.ready()
        out = self.a.observe(
            quote("BTCUSDT", 11, source_time=None, request_started_at="2026-11-02T00:00:09Z")
        )
        self.assertFalse(out["fills"])
        self.assertIn("INELIGIBLE_TIME", [b["reason"] for b in out["blocked"]])

    def test_partial_ioc_obeys_available_size_and_arbitrary_lot_step(self):
        self.p["instruments"]["BTCUSDT"]["lot_step"] = "0.003"
        self.a = PaperAccount(self.tmp.name, self.p)
        self.ready()
        out = self.a.observe(quote("BTCUSDT", 11, ask_size="0.1555"))
        self.assertEqual(D(out["fills"][0]["quantity"]), D("0.153"))
        self.assertEqual(
            self.a.snapshot("2026-11-02T00:00:11Z")["intents"][0]["status"], "IOC_COMPLETE"
        )

    def test_minimum_notional_refuses_dust_without_fake_fill(self):
        self.ready()
        out = self.a.observe(quote("BTCUSDT", 11, ask_size="0.001"))
        self.assertEqual(out["fills"], [])
        self.assertIn("VENUE_SIZE_OR_NOTIONAL", [b["reason"] for b in out["blocked"]])
        self.assertEqual(D(out["account"]["cash_total"]), D("1000"))

    def test_unknown_liquidity_leaves_pending(self):
        self.ready()
        out = self.a.observe(quote("BTCUSDT", 11, ask_size=None))
        self.assertEqual(out["fills"], [])
        self.assertIn("UNKNOWN_LIQUIDITY", [b["reason"] for b in out["blocked"]])

    def test_stale_other_holding_blocks_increased_risk_fill(self):
        self.ready()
        self.a.observe(quote("BTCUSDT", 11))
        out = self.a.observe(
            quote(
                "ETHUSDT",
                12,
                source_time="2026-11-02T00:03:00Z",
                received_at="2026-11-02T00:03:00Z",
            )
        )
        self.assertEqual(out["fills"], [])
        self.assertIn("UNKNOWN_AGGREGATE_NAV_AT_FILL", [b["reason"] for b in out["blocked"]])

    def test_venue_maximum_quantity_and_notional_bound_fill(self):
        self.p["instruments"]["BTCUSDT"].update(max_qty="0.2", max_notional="15")
        self.a = PaperAccount(self.tmp.name, self.p)
        self.ready()
        out = self.a.observe(quote("BTCUSDT", 11))
        self.assertEqual(D(out["fills"][0]["quantity"]), D("0.15"))

    def test_slippage_price_rounds_adversely_to_tick(self):
        self.p["slippage"] = "0.00001"
        self.a = PaperAccount(self.tmp.name, self.p)
        self.ready()
        out = self.a.observe(quote("BTCUSDT", 11))
        self.assertEqual(D(out["fills"][0]["price"]), D("100.01"))

    def test_concurrent_duplicate_fill_observations_commit_once(self):
        from concurrent.futures import ThreadPoolExecutor

        self.ready()
        q = quote("BTCUSDT", 11)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(PaperAccount(self.tmp.name, self.p).observe, q) for _ in range(2)
            ]
            results = [f.result() for f in futures]
        self.assertEqual(results[0], results[1])
        self.assertEqual(len(self.a.snapshot("2026-11-02T00:00:11Z")["fills"]), 1)

    def test_stale_held_mark_propagates_unknown_nav(self):
        self.filled()
        s = self.a.snapshot("2026-11-02T00:03:00Z")
        self.assertIsNone(s["account"]["nav"])
        self.assertEqual(set(s["account"]["missing_marks"]), set(SYMBOLS))

    def test_profile_and_currency_cannot_mix_on_restart(self):
        self.filled()
        with self.assertRaises(ValueError):
            PaperAccount(self.tmp.name, profile("public_market"))
        bad = profile(quote_currency="USD")
        with self.assertRaises(ValueError):
            PaperAccount(self.tmp.name, bad)

    def test_public_observation_keeps_unknown_exchange_time_and_simulation_label(self):
        with tempfile.TemporaryDirectory() as path:
            a = PaperAccount(path, profile("public_market"))
            self.ready(a, "public_market")
            r = a.observe(
                quote(
                    "BTCUSDT",
                    11,
                    kind="public_market",
                    source_time=None,
                    request_started_at="2026-11-02T00:00:10.500000Z",
                )
            )
            f = r["fills"][0]
            self.assertIsNone(f["source_time"])
            self.assertEqual(f["evidence"], "recorded_top_of_book_simulated_fill")
            self.assertTrue(f["simulation_only"])

    def test_future_missing_and_cross_profile_bars_rejected_before_decision(self):
        self.ready()
        original = Path(self.tmp.name, "account.jsonl").read_bytes()
        for mutate in (
            lambda b: b["BTCUSDT"].pop(),
            lambda b: b["BTCUSDT"][-1].update(received_at="2026-11-03T00:00:00Z"),
            lambda b: b["BTCUSDT"][-1].update(evidence_type="public_market"),
        ):
            b = bars()
            mutate(b)
            with self.assertRaises(ValueError):
                self.a.decide("2026-11-01", b, T0)
            self.assertEqual(Path(self.tmp.name, "account.jsonl").read_bytes(), original)

    def test_kill_persists_and_does_not_fill_on_triggering_quote(self):
        self.filled()
        self.a.observe(quote("BTCUSDT", 20, bid="40"))
        st = self.a.snapshot("2026-11-02T00:00:20Z")
        self.assertEqual(st["status"], "KILLED")
        self.assertEqual(len(st["fills"]), 2)
        restart = PaperAccount(self.tmp.name, self.p)
        out = restart.observe(quote("BTCUSDT", 21, bid="40"))
        self.assertTrue(all(f["side"] == "SELL" for f in out["fills"]))
        self.assertEqual(restart.snapshot("2026-11-02T00:00:21Z")["status"], "KILLED")

    def test_late_daily_mark_is_unknown_and_snapshot_cannot_time_travel(self):
        self.filled()
        out = self.a.daily_mark("2026-11-02", "2026-11-02T00:10:00Z")
        self.assertEqual(out["status"], "MISSED_CUTOFF")
        self.assertIsNone(out["sample"]["nav"])
        with self.assertRaises(ValueError):
            self.a.snapshot(T0)

    def test_torn_or_tampered_journal_fails_closed(self):
        self.filled()
        path = Path(self.tmp.name) / "account.jsonl"
        raw = path.read_bytes()
        path.write_bytes(raw + b'{"unfinished":')
        with self.assertRaises(ValueError):
            self.a.verify()
        self.assertEqual(path.read_bytes(), raw + b'{"unfinished":')

    def test_original_sources_match_pinned_manifest(self):
        folder = Path(runtime.__file__).parent / "vendor/reviewed_trend"
        p = json.loads((folder / "PROVENANCE.json").read_text())
        for name, expected in p["original_files"].items():
            self.assertEqual(hashlib.sha256((folder / name).read_bytes()).hexdigest(), expected)

    def test_shared_synthetic_economics_match_reviewed_core_when_constraints_nonbinding(self):
        path = Path(runtime.__file__).parent / "vendor/reviewed_trend/paper_candidate.py"
        spec = importlib.util.spec_from_file_location("reviewed_for_parity", path)
        old = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(old)
        # Same costs, prices, allocation and lot precision. Tick rounding and
        # venue bounds are intentionally nonbinding for this parity sequence.
        p = profile(precision=3)
        self.a = PaperAccount(self.tmp.name, p)
        self.ready()
        oldst, _ = old.apply(
            None,
            {
                "op": "init",
                "at": T0,
                "account_id": p["id"],
                "mode": "synthetic_spot_only",
                "initial_cash": "1000",
                "scenario": runtime._scenario(runtime._validate_profile(p)),
            },
        )
        for s in SYMBOLS:
            q, at = runtime._quote(quote(s), runtime._validate_profile(p))
            oldst, _ = old.apply(oldst, {"op": "observe", "at": at, "evidence": q})
        b = runtime._bars(bars(), "2026-11-01", T0, runtime._validate_profile(p))
        for rows in b["payload"].values():
            for row in rows:
                row["published_at"] = row["received_at"]
        b["payload_sha256"] = old.sha(b["payload"])
        oldst, _ = old.apply(
            oldst, {"op": "decision", "at": T0, "signal_date": "2026-11-01", "evidence": b}
        )
        for s in SYMBOLS:
            q, at = runtime._quote(quote(s, 11), runtime._validate_profile(p))
            oldst, _ = old.apply(oldst, {"op": "observe", "at": at, "evidence": q})
            self.a.observe(quote(s, 11))
        actual = self.a.ledger.state()
        self.assertEqual(actual["cash_total"], oldst["cash_total"])
        self.assertEqual(actual["holdings"], oldst["holdings"])
        self.assertEqual(actual["realized_fees"], oldst["realized_fees"])


if __name__ == "__main__":
    unittest.main()
