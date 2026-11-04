"""System invariants across input validation, journal replay and workstation output."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from idxsig.runtime import coordinator as c
from idxsig.runtime.demo import fixtures, T0, T1
from idxsig.runtime.storage import atomic_json, read_json


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "runtime"
        self.profile, self.snapshots = fixtures()
        self.p = self.base / "profile.json"
        atomic_json(self.p, self.profile)
        self.paths = []
        for i, value in enumerate(self.snapshots):
            path = self.base / f"input-{i}.json"
            atomic_json(path, value)
            self.paths.append(path)

    def run_cycle(self, i):
        return c.run_once(self.root, self.paths[i], self.p, (T0, T1)[i])

    def test_decision_then_later_fills_shared_account_and_retry(self):
        first = self.run_cycle(0)
        self.assertEqual(first["payload"]["account"]["fills"], [])
        self.assertEqual(len(first["payload"]["account"]["orders"]), 2)
        second = self.run_cycle(1)
        self.assertEqual(len(second["payload"]["account"]["fills"]), 2)
        self.assertEqual(second["payload"]["run"]["decision_status"], "ORIGINAL_DECISION_RETAINED")
        before = (self.root / "account/account.jsonl").read_bytes()
        self.assertEqual(self.run_cycle(1), second)
        self.assertEqual(self.run_cycle(0), first)
        self.assertEqual(before, (self.root / "account/account.jsonl").read_bytes())
        self.assertEqual(read_json(self.root / "snapshot.json"), second)
        self.assertEqual(c.verify(self.root)["runs"], 2)
        self.assertEqual(c.verify(self.root)["forward_trial_days"], 0)

    def test_bad_second_quote_is_rejected_before_any_account_write(self):
        self.snapshots[0]["quotes"][1]["bid"] = "149.001"
        atomic_json(self.paths[0], self.snapshots[0])
        with self.assertRaisesRegex(ValueError, "tick"):
            self.run_cycle(0)
        self.assertFalse((self.root / "pending.json").exists())
        self.assertFalse((self.root / "account/account.jsonl").exists())
        self.assertEqual(read_json(self.root / "last_attempt.json")["status"], "FAILED")

    def test_metadata_change_fails_before_new_fills(self):
        self.run_cycle(0)
        self.snapshots[1]["instruments"][0]["lot_step"] = "0.01"
        atomic_json(self.paths[1], self.snapshots[1])
        before = (self.root / "account/account.jsonl").read_bytes()
        with self.assertRaisesRegex(ValueError, "METADATA_CHANGED"):
            self.run_cycle(1)
        self.assertEqual(before, (self.root / "account/account.jsonl").read_bytes())
        self.assertEqual(c.status(self.root)["last_attempt"]["status"], "FAILED")

    def test_interruption_after_fills_recovers_without_duplicates(self):
        self.run_cycle(0)
        with patch.object(
            c.PaperAccount, "mark", side_effect=OSError("simulated interrupted write")
        ):
            with self.assertRaises(OSError):
                self.run_cycle(1)
        self.assertTrue((self.root / "pending.json").exists())
        with self.assertRaisesRegex(ValueError, "RECOVERY_REQUIRED"):
            self.run_cycle(0)
        recovered = self.run_cycle(1)
        self.assertEqual(len(recovered["payload"]["account"]["fills"]), 2)
        self.assertFalse((self.root / "pending.json").exists())
        self.assertTrue(c.verify(self.root)["ok"])

    def test_input_tamper_rejected_by_verify(self):
        first = self.run_cycle(0)
        saved = self.root / "inputs" / (first["payload"]["run"]["input_sha256"] + ".json")
        obj = read_json(saved)
        obj["quotes"][0]["bid"] = "148"
        atomic_json(saved, obj)
        with self.assertRaisesRegex(ValueError, "input hash"):
            c.verify(self.root)

    def test_queue_survives_quiet_cycle_and_map_coverage_is_fraction(self):
        first = self.run_cycle(0)
        self.assertEqual(len(first["payload"]["candidates"]), 2)
        self.snapshots[1]["bars"][-1]["close"] = "139"
        self.snapshots[1]["bars"][-1]["low"] = "138"
        self.snapshots[1]["bars"][39]["close"] = "139"
        self.snapshots[1]["bars"][39]["low"] = "138"
        atomic_json(self.paths[1], self.snapshots[1])
        second = self.run_cycle(1)
        self.assertEqual(second["payload"]["candidates"], first["payload"]["candidates"])
        self.assertTrue(
            all(g["coverage"] == 1 for g in second["payload"]["market_context"]["groups"])
        )

    def test_forward_profile_cannot_be_backdated_with_once(self):
        self.profile["execution_mode"] = "FORWARD_PAPER_CAPTURE"
        atomic_json(self.p, self.profile)
        with self.assertRaisesRegex(ValueError, "separate profiles"):
            self.run_cycle(0)

    def test_duplicate_json_input_is_rejected(self):
        self.paths[0].write_text('{"schema_version": "a", "schema_version": "b"}')
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.run_cycle(0)

    def test_capture_unavailable_is_json_blocked_without_fake_snapshot(self):
        import io
        from contextlib import redirect_stderr
        from idxsig.runtime.__main__ import main
        from idxsig.runtime.collect import PublicDataUnavailable

        errors = io.StringIO()
        with (
            patch(
                "idxsig.runtime.capture.collect_binance_spot",
                side_effect=PublicDataUnavailable("HTTP 451"),
            ),
            redirect_stderr(errors),
        ):
            result = main(["--root", str(self.root), "capture"])
        self.assertEqual(result, 1)
        self.assertEqual(json.loads(errors.getvalue())["status"], "BLOCKED")
        self.assertEqual(read_json(self.root / "last_attempt.json")["phase"], "PUBLIC_CAPTURE")
        self.assertFalse((self.root / "snapshot.json").exists())
        self.assertFalse((self.root / "account/account.jsonl").exists())

    def test_capture_two_source_backed_observations_use_actual_later_receipts(self):
        from datetime import datetime, timedelta, timezone
        from idxsig.runtime.capture import capture
        from idxsig.runtime.data import capture_raw_evidence, utc_text

        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        info = {
            "symbols": [
                {
                    "symbol": symbol,
                    "baseAsset": symbol[:-4],
                    "quoteAsset": "USDT",
                    "status": "TRADING",
                    "isSpotTradingAllowed": True,
                    "filters": [
                        {"filterType": "PRICE_FILTER", "tickSize": ".01"},
                        {
                            "filterType": "LOT_SIZE",
                            "stepSize": ".001",
                            "minQty": ".001",
                            "maxQty": "100",
                        },
                        {"filterType": "MIN_NOTIONAL", "minNotional": "5"},
                    ],
                }
                for symbol in ("BTCUSDT", "ETHUSDT")
            ]
        }
        candles = []
        for index in range(40):
            opening = today - timedelta(days=40 - index)
            px = str(100 + index)
            candles.append(
                [
                    int(opening.timestamp() * 1000),
                    px,
                    str(101 + index),
                    str(99 + index),
                    px,
                    "10000",
                    int((opening + timedelta(days=1, milliseconds=-1)).timestamp() * 1000),
                    "1000000",
                ]
            )

        def source(path, params, evidence_root, kind, **kwargs):
            raw = (
                info
                if kind == "binance_exchange_info"
                else candles
                if kind == "binance_klines"
                else {
                    "symbol": params["symbol"],
                    "bidPrice": "139.00",
                    "askPrice": "139.01",
                    "bidQty": "100",
                    "askQty": "100",
                }
            )
            stamp = utc_text(datetime.now(timezone.utc))
            record = capture_raw_evidence(
                json.dumps(raw).encode(),
                evidence_root,
                source_url="https://api.binance.com" + path,
                received_at=stamp,
                kind=kind,
                request={**params, "request_started_at": stamp},
            )
            return raw, record, stamp

        with patch("idxsig.runtime.collect._fetch", side_effect=source):
            result = capture(self.root, timestamp_decisions=False)
        payload = result["payload"]
        self.assertEqual(payload["run"]["mode"], "FORWARD_PAPER_CAPTURE")
        self.assertEqual(len(payload["account"]["fills"]), 2)
        self.assertEqual(payload["run"]["decision_status"], "ORIGINAL_DECISION_RETAINED")
        intents = {r["id"]: r for r in payload["account"]["orders"]}
        for fill in payload["account"]["fills"]:
            self.assertGreater(fill["received_at"], intents[fill["intent_id"]]["made_at"])
        self.assertNotIn(
            "max_notional", read_json(self.root / "profile.json")["instruments"]["BTCUSDT"]
        )
        self.assertTrue(c.verify(self.root)["ok"])
