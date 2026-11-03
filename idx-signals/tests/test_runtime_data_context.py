import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from idxsig.market_context import build_context, discover_candidates
from idxsig.runtime.collect import collect_binance_spot
from idxsig.runtime.data import (SCHEMA_VERSION, SnapshotError, capture_raw_evidence,
                                 load_recorded_snapshot, utc_text)


AS_OF = "2026-10-23T00:00:10Z"


def fixture(symbols=("BTCUSDT", "ETHUSDT", "AAAUSDT")):
    start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    instruments, bars = [], []
    for rank, symbol in enumerate(symbols):
        instruments.append({"venue": "BINANCE_SPOT", "symbol": symbol,
                            "base_asset": symbol[:-4], "quote_asset": "USDT", "asset_class": "crypto",
                            "tick_size": "0.01", "lot_step": "0.001", "min_notional": "5",
                            "trading_status": "TRADING"})
        for day in range(22):
            opening = start + timedelta(days=day)
            bars.append({"venue": "BINANCE_SPOT", "symbol": symbol,
                         "open_time": utc_text(opening), "close_time": utc_text(opening + timedelta(days=1, milliseconds=-1)),
                         "open": "100", "high": "110", "low": "90", "close": "105" if day == 21 else "100",
                         "base_volume": "10", "quote_volume": str(1000 * (rank + 1)),
                         "received_at": AS_OF, "evidence_id": "synthetic-candles"})
    return {"schema_version": SCHEMA_VERSION, "captured_at": AS_OF, "evidence_kind": "synthetic",
            "instruments": instruments, "bars": bars, "quotes": [], "evidence": []}


class DataContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path = self.root / "snapshot.json"

    def tearDown(self):
        self.tmp.cleanup()

    def load(self, obj, cutoff=AS_OF, evidence=None):
        self.path.write_text(json.dumps(obj))
        return load_recorded_snapshot(self.path, cutoff, evidence)

    def test_valid_snapshot_keeps_missing_quotes_explicit(self):
        result = self.load(fixture())
        self.assertEqual(len(result["validation"]["missing_quote_instruments"]), 3)
        self.assertFalse(result["validation"]["evidence_verified"])
        self.assertEqual(result["bars"][0]["open"], "100")

    def test_future_receipt_and_forming_bar_are_rejected(self):
        for field in ("received_at", "close_time"):
            obj = fixture()
            obj["bars"][-1][field] = "2026-10-24T00:00:00Z"
            with self.subTest(field=field), self.assertRaises(SnapshotError):
                self.load(obj)

    def test_historical_cutoff_cannot_use_later_capture(self):
        with self.assertRaisesRegex(SnapshotError, "captured after"):
            self.load(fixture(), "2026-10-22T23:59:59Z")

    def test_timezone_nonfinite_and_price_dimensions(self):
        cases = [("received_at", "2026-10-23T00:00:10"), ("open", "NaN"),
                 ("quote_volume", "Infinity"), ("low", "106"), ("base_volume", "-1")]
        for field, value in cases:
            obj = fixture()
            obj["bars"][-1][field] = value
            with self.subTest(field=field), self.assertRaises(SnapshotError):
                self.load(obj)

    def test_identical_and_revised_duplicates_fail(self):
        for revised in (False, True):
            obj = fixture()
            row = copy.deepcopy(obj["bars"][-1])
            if revised:
                row["close"] = "106"
            obj["bars"].append(row)
            with self.subTest(revised=revised), self.assertRaisesRegex(SnapshotError, "bar"):
                self.load(obj)

    def test_missing_volume_does_not_become_zero_or_measured_relative_volume(self):
        obj = fixture()
        obj["bars"][-2]["quote_volume"] = None
        result = self.load(obj)
        context = build_context(result, AS_OF)
        alt = next(m for m in context["members"] if m["symbol"] == "AAAUSDT")
        self.assertIsNone(alt["relative_volume"])
        self.assertIsNone(alt["prior_median_quote_turnover"])

    def test_context_does_not_bridge_a_missing_daily_bar(self):
        obj = fixture(("BTCUSDT",))
        del obj["bars"][-2]
        context = build_context(self.load(obj), AS_OF)
        self.assertIsNone(context["members"][0]["return_1d"])
        self.assertIsNone(context["groups"][0]["breadth"])

    def test_membership_excludes_signal_days_volume(self):
        obj = fixture(("AAAUSDT", "BBBUSDT", "CCCUSDT", "DDDUSDT", "EEEUSDT", "FFFUSDT"))
        before = build_context(self.load(obj), AS_OF)
        next(r for r in obj["bars"] if r["symbol"] == "AAAUSDT" and r["open_time"].startswith("2026-10-22"))["quote_volume"] = "999999999"
        after = build_context(self.load(obj), AS_OF)
        self.assertEqual({m["symbol"]: m["group_id"] for m in before["members"]},
                         {m["symbol"]: m["group_id"] for m in after["members"]})

    def test_candidate_cannot_create_its_own_peer_support(self):
        obj = fixture(("AAAUSDT", "BBBUSDT", "CCCUSDT", "DDDUSDT", "EEEUSDT", "FFFUSDT"))
        # Lowest two prior-turnover coins are peers. AAA rises while BBB is flat.
        for row in obj["bars"]:
            if row["symbol"] == "BBBUSDT":
                row["close"] = "100"
        snap = self.load(obj)
        context = build_context(snap, AS_OF)
        candidates = discover_candidates(snap, context, AS_OF)
        aaa = next(c for c in candidates if c["symbol"] == "AAAUSDT")
        self.assertEqual(aaa["peer_count"], 1)
        self.assertEqual(aaa["peer_participation"], "ISOLATED")
        self.assertFalse(aaa["entry_permission"])
        self.assertEqual(context["predictive_edges"], [])

    def test_stale_bars_remain_visible_but_do_not_generate_signals(self):
        obj = fixture(("BTCUSDT",))
        obj["captured_at"] = "2026-10-26T00:00:00Z"
        snap = self.load(obj, obj["captured_at"])
        context = build_context(snap, obj["captured_at"])
        self.assertEqual(context["members"][0]["status"], "STALE_BARS")
        self.assertEqual(discover_candidates(snap, context, obj["captured_at"]), [])

    def test_quote_source_time_unknown_and_staleness_are_explicit(self):
        obj = fixture(("BTCUSDT",))
        obj["quotes"] = [{"venue": "BINANCE_SPOT", "symbol": "BTCUSDT", "bid": "99", "ask": "101",
                          "bid_size": None, "ask_size": None, "source_time": None,
                          "received_at": "2026-10-22T23:00:00Z", "observation_id": "q1", "evidence_id": "synthetic"}]
        snap = self.load(obj)
        self.assertEqual(snap["validation"]["unknown_quote_source_times"], ["q1"])
        self.assertEqual(snap["validation"]["stale_quote_observations"], ["q1"])
        self.assertIsNone(snap["quotes"][0]["ask_size"])

    def test_public_snapshots_require_evidence(self):
        obj = fixture()
        obj["evidence_kind"] = "public_market"
        with self.assertRaisesRegex(SnapshotError, "evidence_root"):
            self.load(obj)

    def test_exact_raw_bytes_are_immutable_and_checked(self):
        record = capture_raw_evidence(b'{"sample":1}', self.root, source_url="https://api.binance.com/api/v3/exchangeInfo",
                                       received_at=AS_OF, kind="test")
        second = capture_raw_evidence(b'{"sample":1}', self.root, source_url="https://api.binance.com/api/v3/exchangeInfo",
                                       received_at=AS_OF, kind="test")
        self.assertEqual(record, second)
        obj = fixture(())
        obj["evidence"] = [record]
        self.load(obj, evidence=self.root)
        (self.root / record["path"]).write_bytes(b'{"sample":2}')
        with self.assertRaisesRegex(SnapshotError, "hash mismatch"):
            self.load(obj, evidence=self.root)

    def test_public_normalized_quote_tampering_is_rejected(self):
        stamp = AS_OF
        info = {"symbols": [{"symbol": "BTCUSDT", "baseAsset": "BTC", "quoteAsset": "USDT", "status": "TRADING",
                              "filters": [{"filterType": "PRICE_FILTER", "tickSize": ".01"},
                                          {"filterType": "LOT_SIZE", "stepSize": ".001"},
                                          {"filterType": "MIN_NOTIONAL", "minNotional": "5"}]}]}
        book = {"symbol": "BTCUSDT", "bidPrice": "99", "askPrice": "101", "bidQty": "2", "askQty": "3"}
        ev_info = capture_raw_evidence(json.dumps(info).encode(), self.root, source_url="https://api.binance.com/api/v3/exchangeInfo", received_at=stamp, kind="binance_exchange_info")
        ev_book = capture_raw_evidence(json.dumps(book).encode(), self.root, source_url="https://api.binance.com/api/v3/ticker/bookTicker", received_at=stamp, kind="binance_book_ticker")
        obj = fixture(("BTCUSDT",)); obj["bars"] = []; obj["evidence_kind"] = "public_market"
        obj["instruments"][0].update(metadata_received_at=stamp, evidence_id=ev_info["evidence_id"])
        obj["evidence"] = [ev_info, ev_book]
        obj["quotes"] = [{"venue": "BINANCE_SPOT", "symbol": "BTCUSDT", "bid": "99", "ask": "101",
                          "bid_size": "2", "ask_size": "3", "source_time": None, "received_at": stamp,
                          "observation_id": "book1", "evidence_id": ev_book["evidence_id"]}]
        self.load(obj, evidence=self.root)
        obj["quotes"][0]["ask"] = "100"
        with self.assertRaisesRegex(SnapshotError, "differs from raw"):
            self.load(obj, evidence=self.root)

    def test_no_network_without_explicit_collection_call(self):
        with patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("network attempted")):
            build_context(self.load(fixture()), AS_OF)
        with self.assertRaises(SnapshotError):
            collect_binance_spot(self.path, self.root, ["BTCUSDT?secret=bad"])

    def test_collector_excludes_forming_bar_and_preserves_raw_receipts(self):
        now = datetime.now(timezone.utc)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        info = {"symbols": [{"symbol": "BTCUSDT", "baseAsset": "BTC", "quoteAsset": "USDT", "status": "TRADING",
                              "isSpotTradingAllowed": True,
                              "filters": [{"filterType": "PRICE_FILTER", "tickSize": ".01"},
                                          {"filterType": "LOT_SIZE", "stepSize": ".001", "minQty": ".001", "maxQty": "100"},
                                          {"filterType": "MIN_NOTIONAL", "minNotional": "5"}]}]}
        candles = []
        for offset in range(-40, 1):
            opening = today + timedelta(days=offset)
            candles.append([int(opening.timestamp() * 1000), "100", "110", "90", "105", "10",
                            int((opening + timedelta(days=1, milliseconds=-1)).timestamp() * 1000), "1000"])
        book = {"symbol": "BTCUSDT", "bidPrice": "99", "askPrice": "101", "bidQty": "2", "askQty": "3"}

        def fake_fetch(path, params, evidence_root, kind, **kwargs):
            raw = info if kind == "binance_exchange_info" else candles if kind == "binance_klines" else book
            stamp = utc_text(datetime.now(timezone.utc))
            ev = capture_raw_evidence(json.dumps(raw).encode(), evidence_root,
                                      source_url="https://api.binance.com" + path, received_at=stamp,
                                      kind=kind, request={**params, "request_started_at": stamp})
            return raw, ev, stamp

        with patch("idxsig.runtime.collect._fetch", side_effect=fake_fetch), patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("network attempted")):
            result = collect_binance_spot(self.path, self.root, ["BTCUSDT"], days=40)
        self.assertEqual(len(result["bars"]), 40)
        self.assertEqual(result["collection"]["excluded_bars"][0]["reason"], "FORMING_BAR")
        self.assertTrue(result["validation"]["evidence_verified"])
        self.assertIsNone(result["quotes"][0]["source_time"])
        self.assertEqual(len(result["evidence"]), 3)

    def test_request_start_cannot_follow_receipt(self):
        obj = fixture(("BTCUSDT",))
        obj["quotes"] = [{"venue": "BINANCE_SPOT", "symbol": "BTCUSDT", "bid": "99", "ask": "101",
                          "bid_size": "1", "ask_size": "1", "source_time": None,
                          "received_at": AS_OF, "request_started_at": "2026-10-23T00:01:00Z",
                          "observation_id": "q1", "evidence_id": "synthetic"}]
        with self.assertRaisesRegex(SnapshotError, "request started after"):
            self.load(obj)


if __name__ == "__main__":
    unittest.main()
