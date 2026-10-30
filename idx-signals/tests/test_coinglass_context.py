"""CoinGlass context regressions: data availability is not market history time."""

from datetime import datetime, timedelta, timezone
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from idxsig import coinglass as cg
from idxsig.provenance import sha256_bytes
from idxsig.sources.coinglass import CoinGlassError, CoinGlassResponse, ENDPOINTS


NOW = datetime(2026, 10, 30, 12, tzinfo=timezone.utc)
STEP = 14_400_000
NOW_MS = int(NOW.timestamp() * 1000)
TIME = NOW_MS - STEP
STAMP = "2026-10-30T12:00:00.000Z"


def price(t=TIME, close="100", volume="0"):
    return {
        "time": t,
        "open": "100",
        "high": "110",
        "low": "90",
        "close": close,
        "volume_usd": volume,
    }


def params(**changes):
    return {
        "symbol": "BTCUSDT",
        "exchange": "Binance",
        "interval": "4h",
        "limit": 10,
        "start_time": TIME - STEP * 9,
        "end_time": TIME,
        **changes,
    }


class Client:
    def __init__(self, rows=None, denied=()):
        self.rows = rows or {"price": [price()], "rsi": [{"time": TIME, "rsi_value": "59.3"}]}
        self.denied = denied
        self.calls = []

    def request(self, endpoint, **request):
        self.calls.append((endpoint, request))
        if endpoint in self.denied:
            raise CoinGlassError(
                "plan",
                "CoinGlass endpoint or interval is unavailable on this API plan",
                http_status=200,
                provider_code="401",
            )
        data = self.rows[endpoint]
        raw = json.dumps({"code": "0", "data": data}, allow_nan=False).encode()
        return CoinGlassResponse(
            data,
            raw,
            {
                "endpoint": endpoint,
                "path": ENDPOINTS[endpoint].path,
                "params": request,
                "requested_at": STAMP,
                "observed_at": STAMP,
                "http_status": 200,
                "attempts": 1,
                "provider_code": "0",
                "sha256": sha256_bytes(raw),
            },
        )


class Normalization(unittest.TestCase):
    def test_numbers_nulls_zero_sorting_and_same_row_deduplication(self):
        a, b = price(TIME - STEP, volume=None), price()
        result = cg.normalize_history("price", [b, a, b], params(), STAMP)
        self.assertEqual([r["time"] for r in result["rows"]], [TIME - STEP, TIME])
        self.assertIsNone(result["rows"][0]["volume_usd"])
        self.assertEqual(result["rows"][1]["volume_usd"], 0.0)
        self.assertEqual(result["rows"][1]["close"], 100.0)

    def test_unclosed_and_out_of_window_rows_do_not_become_observations(self):
        data = [price(TIME - 20 * STEP), price(), price(NOW_MS)]
        result = cg.normalize_history("price", data, params(end_time=NOW_MS), STAMP)
        self.assertEqual([r["time"] for r in result["rows"]], [TIME])
        self.assertEqual(result["discarded_outside_window_or_unclosed"], 2)

    def test_conflicting_duplicate_rows_are_refused(self):
        with self.assertRaisesRegex(ValueError, "conflicting duplicate"):
            cg.normalize_history("price", [price(), price(close="101")], params(), STAMP)

    def test_seconds_boolean_nonfinite_and_wrong_instrument_are_refused(self):
        changes = (
            {"time": TIME // 1000},
            {"time": True},
            {"close": True},
            {"close": "NaN"},
            {"close": "Infinity"},
            {"symbol": "ETHUSDT"},
            {"exchange": "Bybit"},
            {"interval": "1h"},
        )
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                cg.normalize_history("price", [{**price(), **change}], params(), STAMP)

    def test_invalid_domains_and_missing_documented_fields_are_refused(self):
        cases = [
            ("price", {**price(), "low": "105"}),
            ("price", {**price(), "close": "0"}),
            ("open_interest", {"time": TIME, "open": -1, "high": 1, "low": -1, "close": 0}),
            (
                "liquidations",
                {"time": TIME, "long_liquidation_usd": -1, "short_liquidation_usd": 0},
            ),
            ("rsi", {"time": TIME, "rsi_value": 101}),
            (
                "long_short",
                {
                    "time": TIME,
                    "global_account_long_percent": 90,
                    "global_account_short_percent": 90,
                    "global_account_long_short_ratio": 1,
                },
            ),
            ("rsi", {"time": TIME}),
        ]
        for endpoint, row in cases:
            with self.subTest(endpoint=endpoint, row=row), self.assertRaises(ValueError):
                cg.normalize_history(endpoint, [row], params(), STAMP)

    def test_negative_funding_and_macd_keep_native_units(self):
        funding = {"time": TIME, "open": "-0.01", "high": "0.02", "low": "-0.03", "close": "-0.02"}
        result = cg.normalize_history("funding", [funding], params(), STAMP)
        self.assertEqual(result["rows"][0]["close"], -0.02)
        self.assertIn("native", result["units"])
        self.assertEqual(
            cg.normalize_history("macd", [{"time": TIME, "macd_value": -20}], params(), STAMP)[
                "rows"
            ][0]["macd_value"],
            -20,
        )


class SavedContext(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="coinglass-context-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "data"
        original = cg._moment
        self.clock = patch.object(
            cg, "_moment", side_effect=lambda value=None: NOW if value is None else original(value)
        )
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def capture(self, client=None, **kwargs):
        return cg.capture(
            client or Client(),
            **{"datasets": ("price", "rsi"), "root": self.root, "limit": 10, **kwargs},
        )

    def revise_document(self, manifest, mutation):
        lines = [json.loads(line) for line in manifest.read_text().splitlines()]
        document_path = next(self.root.glob("raw/coinglass/*/context.json"))
        document = json.loads(document_path.read_text())
        mutation(document)
        payload = json.dumps(document, sort_keys=True, allow_nan=False).encode()
        document_path.write_bytes(payload)
        next(r for r in lines[1:] if r["kind"] == "normalized")["sha256"] = sha256_bytes(payload)
        manifest.write_text("\n".join(json.dumps(line) for line in lines) + "\n")

    def test_saved_context_is_usable_and_request_window_is_shared(self):
        client = Client()
        manifest = self.capture(client)
        context = cg.latest_context(manifest)
        self.assertTrue(context["all_requested_ready"])
        self.assertEqual(context["datasets"]["price"]["values"]["volume_usd"], 0)
        self.assertEqual(context["datasets"]["rsi"]["values"]["rsi_value"], 59.3)
        requests = [p for _, p in client.calls]
        self.assertEqual(requests[0]["end_time"], requests[1]["end_time"])
        self.assertEqual(requests[0]["start_time"], requests[1]["start_time"])
        self.assertEqual(requests[1]["window"], 14)
        self.assertEqual(cg.load_snapshot(manifest)["observed_at"], STAMP)
        self.assertEqual(context["datasets"]["rsi"]["params"]["window"], 14)

    def test_inconsistent_client_data_is_refused_before_manifest_publication(self):
        class Inconsistent(Client):
            def request(self, endpoint, **request):
                response = super().request(endpoint, **request)
                return CoinGlassResponse([price(close="101")], response.raw, response.metadata)

        with self.assertRaisesRegex(ValueError, "raw response"):
            self.capture(Inconsistent())
        self.assertEqual(list(self.root.glob("manifests/*.jsonl")), [])

    def test_manifest_paths_work_with_existing_verify_data_hash_checker(self):
        from idxsig import provenance

        manifest = self.capture()
        with patch.object(provenance, "PKG_ROOT", self.root.parent):
            self.assertEqual(provenance.check_files(manifest), [])

    def test_plan_denial_remains_unavailable_and_never_zero(self):
        manifest = self.capture(Client(denied=("rsi",)))
        context = cg.latest_context(manifest)
        self.assertFalse(context["all_requested_ready"])
        self.assertEqual(context["datasets"]["price"]["status"], "ready")
        self.assertEqual(context["datasets"]["rsi"]["status"], "unavailable")
        self.assertEqual(context["datasets"]["rsi"]["reason"], "plan")
        self.assertNotIn("values", context["datasets"]["rsi"])

    def test_historical_timestamp_cannot_backdate_availability(self):
        manifest = self.capture()
        earlier = NOW - timedelta(seconds=1)
        context = cg.latest_context(manifest, asof=earlier)
        self.assertTrue(
            all(r["status"] == "not_yet_observed" for r in context["datasets"].values())
        )
        self.assertTrue(all("values" not in r for r in context["datasets"].values()))
        with self.assertRaisesRegex(ValueError, "not been observed"):
            cg.history_frame(manifest, asof=earlier)

    def test_stale_null_and_empty_data_have_distinct_readiness(self):
        client = Client(rows={"price": [price(volume=None)], "rsi": []})
        manifest = self.capture(client)
        now = cg.latest_context(manifest)
        self.assertEqual(now["datasets"]["price"]["status"], "incomplete")
        self.assertIsNone(now["datasets"]["price"]["values"]["volume_usd"])
        self.assertEqual(now["datasets"]["rsi"]["status"], "empty")
        later = cg.latest_context(manifest, asof=NOW + timedelta(hours=12))
        self.assertEqual(later["datasets"]["price"]["status"], "stale")

    def test_raw_corruption_is_detected(self):
        manifest = self.capture()
        path = next(self.root.glob("raw/coinglass/*/price.json"))
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            cg.load_snapshot(manifest)

    def test_normalized_rewrite_with_fresh_hash_still_fails_raw_replay(self):
        manifest = self.capture()
        self.revise_document(
            manifest, lambda doc: doc["datasets"]["price"]["rows"][0].update(close=101)
        )
        with self.assertRaisesRegex(ValueError, "reproduce"):
            cg.load_snapshot(manifest)

    def test_mixed_instrument_metadata_is_detected(self):
        manifest = self.capture()
        self.revise_document(
            manifest,
            lambda doc: doc["datasets"]["rsi"]["metadata"]["params"].update(symbol="ETHUSDT"),
        )
        with self.assertRaisesRegex(ValueError, "context"):
            cg.load_snapshot(manifest)

    def test_path_escape_is_refused(self):
        manifest = self.capture()
        lines = [json.loads(line) for line in manifest.read_text().splitlines()]
        lines[1]["path"] = "../outside.json"
        manifest.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
        with self.assertRaisesRegex(ValueError, "path"):
            cg.load_snapshot(manifest)

    def test_outer_join_never_fills_missing_intervals(self):
        client = Client(
            rows={
                "price": [price(TIME - 2 * STEP), price()],
                "rsi": [{"time": TIME - STEP, "rsi_value": 20}],
            }
        )
        manifest = self.capture(client)
        frame = cg.history_frame(manifest)
        self.assertEqual(frame.index.tolist(), [TIME - 2 * STEP, TIME - STEP, TIME])
        self.assertTrue(
            frame.loc[TIME - STEP, "price.close"] != frame.loc[TIME - STEP, "price.close"]
        )
        self.assertTrue(frame.loc[TIME, "rsi.rsi_value"] != frame.loc[TIME, "rsi.rsi_value"])
        self.assertEqual(frame.attrs["observed_at"], STAMP)
        self.assertEqual(cg.latest_context(manifest)["datasets"]["price"]["missing_intervals"], 1)

    def test_invalid_configuration_is_rejected_before_network(self):
        for kwargs in (
            {"interval": "2h"},
            {"limit": True},
            {"end": "2026-10-30T12:00:00"},
            {"end": NOW + timedelta(seconds=1)},
        ):
            client = Client()
            with self.subTest(kwargs=kwargs), self.assertRaises((ValueError, CoinGlassError)):
                self.capture(client, **kwargs)
            self.assertEqual(client.calls, [])

    def test_cli_access_check_discloses_partial_plan_access(self):
        from idxsig.cli import main
        from idxsig.sources import coinglass as source

        output = StringIO()
        with (
            patch.object(source, "CoinGlassClient", return_value=Client(denied=("rsi",))),
            patch("sys.stdout", output),
        ):
            result = main(["coinglass-check"])
        document = json.loads(output.getvalue())
        self.assertEqual(result, 2)
        self.assertEqual(document["datasets"]["price"]["status"], "accessible")
        self.assertEqual(document["datasets"]["rsi"]["reason"], "plan")

    def test_cli_report_and_verify_do_not_require_a_key_or_network(self):
        from idxsig.cli import main
        from idxsig.sources import coinglass as source

        manifest = self.capture()
        for command in ("coinglass-report", "coinglass-verify"):
            output = StringIO()
            with (
                self.subTest(command=command),
                patch.dict(os.environ, {}, clear=True),
                patch.object(
                    source, "CoinGlassClient", side_effect=AssertionError("reader started network")
                ),
                patch("sys.stdout", output),
            ):
                self.assertEqual(main([command, "--manifest", str(manifest)]), 0)
            self.assertIsInstance(json.loads(output.getvalue()), dict)


if __name__ == "__main__":
    unittest.main()
