"""Adversarial boundaries shared by the operating runner and market adapters."""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from idxsig.runtime import account, data, storage
from tests.test_runtime_account import profile, quote, bars, T0
from tests.test_runtime_data_context import fixture, AS_OF


class RuntimeIntegrityTests(unittest.TestCase):
    def test_duplicate_market_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "snapshot.json"
            text = json.dumps(fixture())
            path.write_text(text.replace('"evidence_kind": "synthetic"',
                                         '"evidence_kind": "public_market", "evidence_kind": "synthetic"'))
            with self.assertRaises(data.SnapshotError):
                data.load_recorded_snapshot(path, AS_OF)

    def test_snapshot_digest_identifies_exact_parsed_bytes(self):
        raw = json.dumps(fixture()).encode()
        with patch.object(Path, "read_bytes", side_effect=[raw, b"changed"] ) as read:
            result = data.load_recorded_snapshot("unused.json", AS_OF)
        self.assertEqual(read.call_count, 1)
        self.assertEqual(result["snapshot_sha256"], hashlib.sha256(raw).hexdigest())

    def test_quote_cannot_smuggle_future_processing_clock(self):
        obj = fixture(("BTCUSDT",))
        obj["quotes"] = [{"venue": "BINANCE_SPOT", "symbol": "BTCUSDT", "bid": "100", "ask": "101",
                          "bid_size": "10", "ask_size": "10", "received_at": AS_OF,
                          "at": "2099-01-01T00:00:00Z", "source_time": None,
                          "evidence_id": "synthetic", "observation_id": "q1"}]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "snapshot.json"
            path.write_text(json.dumps(obj))
            with self.assertRaisesRegex(data.SnapshotError, "processing clock"):
                data.load_recorded_snapshot(path, AS_OF)

    def test_public_instrument_must_keep_raw_economic_limits(self):
        raw = {"symbols": [{"symbol": "BTCUSDT", "baseAsset": "BTC", "quoteAsset": "USDT",
                "status": "TRADING", "filters": [
                    {"filterType": "PRICE_FILTER", "tickSize": ".01"},
                    {"filterType": "LOT_SIZE", "stepSize": ".001", "minQty": ".001", "maxQty": "10"},
                    {"filterType": "NOTIONAL", "minNotional": "5", "maxNotional": "1000"}]}]}
        with tempfile.TemporaryDirectory() as folder:
            ev = data.capture_raw_evidence(json.dumps(raw).encode(), folder,
                    source_url="https://api.binance.com/api/v3/exchangeInfo", received_at=AS_OF,
                    kind="binance_exchange_info")
            obj = fixture(("BTCUSDT",)); obj.update(bars=[], evidence_kind="public_market", evidence=[ev])
            obj["instruments"][0].update(metadata_received_at=AS_OF, evidence_id=ev["evidence_id"],
                    min_qty=".001", max_qty="10", max_notional="1000")
            path = Path(folder) / "snapshot.json"
            path.write_text(json.dumps(obj))
            data.load_recorded_snapshot(path, AS_OF, folder)
            for key in ("min_qty", "max_qty", "max_notional"):
                omitted = copy.deepcopy(obj); del omitted["instruments"][0][key]
                path.write_text(json.dumps(omitted))
                with self.subTest(key=key), self.assertRaises(data.SnapshotError):
                    data.load_recorded_snapshot(path, AS_OF, folder)

    def test_complete_json_without_commit_newline_cannot_be_appended(self):
        with tempfile.TemporaryDirectory() as folder:
            with storage.locked(folder):
                storage.append_receipt(folder, {"id": "one"})
                path = Path(folder) / "runs.jsonl"
                damaged = path.read_bytes()[:-1]
                path.write_bytes(damaged)
                with self.assertRaisesRegex(ValueError, "torn"):
                    storage.append_receipt(folder, {"id": "two"})
                self.assertEqual(path.read_bytes(), damaged)

    def test_duplicate_profile_instrument_cannot_override_constraints(self):
        p = profile()
        p["instruments"] = [{"symbol": s, **v} for s, v in p["instruments"].items()]
        p["instruments"].append(copy.deepcopy(p["instruments"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            account._validate_profile(p)

    def test_public_quote_with_unknown_generation_time_cannot_prove_future_fill(self):
        with tempfile.TemporaryDirectory() as folder:
            a = account.PaperAccount(folder, profile("public_market"))
            for symbol in account.SYMBOLS:
                a.observe(quote(symbol, kind="public_market", source_time=None))
            a.decide("2026-11-01", bars("public_market"), T0)
            result = a.observe(quote("BTCUSDT", 11, kind="public_market", source_time=None))
            self.assertEqual(result["fills"], [])
            self.assertIn("UNKNOWN_REQUEST_START", [b["reason"] for b in result["blocked"]])
            # Missing request chronology affects execution; it does not erase
            # the observed quote or turn current mark availability into zero.
            self.assertIsNotNone(result["account"]["nav"])

    def test_duplicate_ledger_key_rejected_even_if_hash_still_matches(self):
        with tempfile.TemporaryDirectory() as folder:
            a = account.PaperAccount(folder, profile())
            a.observe(quote("BTCUSDT"))
            path = Path(folder) / "account.jsonl"
            raw = path.read_text()
            # The ordinary JSON parser would discard the first duplicate and
            # reconstruct exactly the original, valid hashed command.
            altered = raw.replace('"initial_cash":"1000"',
                                  '"initial_cash":"999999","initial_cash":"1000"', 1)
            self.assertNotEqual(raw, altered)
            path.write_text(altered)
            with self.assertRaisesRegex(ValueError, "duplicate"):
                a.verify()

    def test_capture_two_mocked_public_observations_keeps_causal_fills(self):
        from idxsig.runtime.capture import capture
        from idxsig.runtime.coordinator import verify
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        info = {"symbols": [{"symbol": symbol, "baseAsset": symbol[:-4], "quoteAsset": "USDT",
                 "status": "TRADING", "isSpotTradingAllowed": True, "filters": [
                    {"filterType": "PRICE_FILTER", "tickSize": ".01"},
                    {"filterType": "LOT_SIZE", "stepSize": ".001", "minQty": ".001", "maxQty": "1000"},
                    {"filterType": "NOTIONAL", "minNotional": "5", "maxNotional": "100000"}]}
                 for symbol in account.SYMBOLS]}
        candles = []
        for n in range(120):
            opened = today - timedelta(days=120-n)
            price = str(100 + n)
            candles.append([int(opened.timestamp()*1000), price, str(101+n), str(99+n), price,
                            "100", int((opened+timedelta(days=1,milliseconds=-1)).timestamp()*1000), "100000"])

        def public_fixture(path, params, evidence_root, kind, **kwargs):
            started = data.utc_text(datetime.now(timezone.utc))
            raw = info if kind == "binance_exchange_info" else candles if kind == "binance_klines" else {
                "symbol": params["symbol"], "bidPrice": "220", "askPrice": "220", "bidQty": "100", "askQty": "100"}
            ev = data.capture_raw_evidence(json.dumps(raw).encode(), evidence_root,
                   source_url="https://api.binance.com"+path, received_at=data.utc_text(datetime.now(timezone.utc)),
                   kind=kind, request={**params, "request_started_at": started})
            return raw, ev, started

        with tempfile.TemporaryDirectory() as folder:
            with patch("idxsig.runtime.collect._fetch", side_effect=public_fixture), patch(
                    "urllib.request.OpenerDirector.open", side_effect=AssertionError("unexpected network")):
                result = capture(folder)
            account_view = result["payload"]["account"]
            self.assertEqual(len(account_view["fills"]), 2)
            for fill in account_view["fills"]:
                order = next(o for o in account_view["orders"] if o["id"] == fill["intent_id"])
                self.assertLess(data.parse_time(order["made_at"]), data.parse_time(fill["received_at"]))
                self.assertIsNone(fill["source_time"])
                self.assertTrue(fill["simulation_only"])
            self.assertEqual(verify(folder)["runs"], 2)


if __name__ == "__main__":
    unittest.main()
