"""Offline provider-boundary regressions for pinned resumable datasets."""

import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from idxsig.provenance import PKG_ROOT
from idxsig.sources import binance, yahoo
from idxsig.sources.resume import CacheIntegrityError, ResumeMismatch, save_raw


class Clock(datetime):
    now_value = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz=None):
        return cls.now_value


YAHOO = json.dumps(
    {"chart": {"result": [{"timestamp": [1735689600], "meta": {}, "events": {}}]}}
).encode()
INFO = json.dumps(
    {
        "symbols": [
            {"symbol": "ABCUSDT", "status": "TRADING", "baseAsset": "ABC", "quoteAsset": "USDT"},
            {"symbol": "XYZUSDT", "status": "BREAK", "baseAsset": "XYZ", "quoteAsset": "USDT"},
        ]
    }
).encode()


class SourceResume(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="resume-test-", dir=PKG_ROOT)
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        Clock.now_value = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
        self.manifests = []

    def manifest(self, name, header, records):
        self.manifests.append((header, records))
        return self.root / name

    def yahoo_response(self, ticker, p2, **kwargs):
        return (
            200,
            YAHOO,
            yahoo.CHART.format(symbol=ticker + kwargs["suffix"], p1=kwargs["p1"], p2=p2),
        )

    def test_relative_window_resume_fetches_only_missing_with_original_bounds(self):
        out = self.root / "yahoo"
        calls = []

        def interrupted(ticker, p2, **kwargs):
            calls.append((ticker, p2, kwargs["p1"]))
            if ticker == "DEF":
                raise ConnectionError("injected interruption")
            return self.yahoo_response(ticker, p2, **kwargs)

        args = dict(tickers=["ABC", "DEF"], out_dir=out, days=30, prefix="recent", sleep=0)
        with (
            patch.object(yahoo, "datetime", Clock),
            patch.object(yahoo, "fetch_one", side_effect=interrupted),
        ):
            with self.assertRaises(ConnectionError):
                yahoo.fetch(**args)
        bound = json.loads((out / "_request.json").read_text())
        first = json.loads((out / "_progress.jsonl").read_text().splitlines()[0])
        Clock.now_value = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)
        with (
            patch.object(yahoo, "datetime", Clock),
            patch.object(yahoo, "fetch_one", side_effect=self.yahoo_response) as fetch,
            patch.object(yahoo, "write_manifest", side_effect=self.manifest),
        ):
            yahoo.fetch(**args)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(fetch.call_args.args, ("DEF", bound["window"]["p2"]))
        self.assertEqual(fetch.call_args.kwargs["p1"], bound["window"]["p1"])
        header, records = self.manifests[-1]
        self.assertEqual(header["coverage_window"], bound["window"])
        self.assertEqual(header["started_at"], bound["started_at"])
        self.assertEqual(next(r for r in records if r["ticker"] == "ABC"), first)

    def test_yahoo_changed_range_suffix_universe_or_days_refused(self):
        out = self.root / "yahoo"
        args = dict(tickers=["ABC"], out_dir=out, start="2025-01-01", prefix="history", sleep=0)
        with (
            patch.object(yahoo, "fetch_one", side_effect=self.yahoo_response),
            patch.object(yahoo, "write_manifest", side_effect=self.manifest),
        ):
            yahoo.fetch(**args)
        for change in (
            {"start": "2020-01-01"},
            {"suffix": ""},
            {"tickers": ["ABC", "DEF"]},
            {"start": None, "days": 30},
        ):
            with self.subTest(change=change), patch.object(yahoo, "fetch_one") as fetch:
                with self.assertRaises(ResumeMismatch):
                    yahoo.fetch(**{**args, **change})
                fetch.assert_not_called()

    def test_legacy_cache_requires_fresh_directory_without_touching_old_bytes(self):
        out = self.root / "legacy"
        out.mkdir()
        old = b'{"ticker":"ABC","first_date":"2025-01-01","http_status":200}\n'
        (out / "_progress.jsonl").write_bytes(old)
        with patch.object(yahoo, "fetch_one") as fetch:
            with self.assertRaisesRegex(ResumeMismatch, "no pinned request"):
                yahoo.fetch(["ABC"], out_dir=out, start="2020-01-01", prefix="history", sleep=0)
            fetch.assert_not_called()
        self.assertEqual((out / "_progress.jsonl").read_bytes(), old)
        self.assertFalse((out / "_request.json").exists())

    def test_missing_or_corrupt_success_is_never_silently_skipped(self):
        for missing in (False, True):
            out = self.root / str(missing)
            with patch.object(yahoo, "fetch_one", side_effect=self.yahoo_response):
                yahoo.fetch(["ABC"], out_dir=out, finalize=False, sleep=0)
            rec = json.loads((out / "_progress.jsonl").read_text())
            raw = PKG_ROOT / rec["path"]
            raw.unlink() if missing else raw.write_bytes(b"corrupt")
            with patch.object(yahoo, "fetch_one") as fetch:
                with self.assertRaises(CacheIntegrityError):
                    yahoo.fetch(["ABC"], out_dir=out, finalize=False, sleep=0)
                fetch.assert_not_called()

    def binance_response(self, url):
        if "exchangeInfo" in url:
            return 200, INFO
        return 200, json.dumps(
            [[1735689600000, "1", "1", "1", "1", "100", 1735775999999, "100"]]
        ).encode()

    def test_binance_resume_keeps_bounds_universe_and_original_observation_time(self):
        out = self.root / "binance"
        with (
            patch.object(binance, "datetime", Clock),
            patch.object(binance, "_get", side_effect=self.binance_response) as fetch,
            patch.object(binance, "write_manifest", side_effect=self.manifest),
        ):
            binance.fetch(out_dir=out, sleep=0, workers=1)
        original = self.manifests[-1]
        self.assertTrue(
            all("endTime=" in c.args[0] for c in fetch.call_args_list if "klines" in c.args[0])
        )
        Clock.now_value = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)
        with (
            patch.object(binance, "datetime", Clock),
            patch.object(binance, "_get") as fetch,
            patch.object(binance, "write_manifest", side_effect=self.manifest),
        ):
            binance.fetch(out_dir=out, sleep=0, workers=1)
            fetch.assert_not_called()
        header, records = self.manifests[-1]
        self.assertEqual(records, original[1])
        self.assertEqual(header["coverage_window"], original[0]["coverage_window"])
        self.assertEqual(
            header["coverage_window"]["end_ms"],
            int(datetime(2026, 10, 1, tzinfo=timezone.utc).timestamp() * 1000) - 1,
        )
        self.assertEqual(header["universe_sha256"], original[0]["universe_sha256"])
        self.assertEqual(header["started_at"], original[0]["started_at"])

    def test_binance_changed_parameters_and_corrupted_universe_refused(self):
        out = self.root / "binance"
        with (
            patch.object(binance, "_get", side_effect=self.binance_response),
            patch.object(binance, "write_manifest", side_effect=self.manifest),
        ):
            binance.fetch(out_dir=out, sleep=0, workers=1)
        for change in ({"start": "2019-01-01"}, {"quote": "BTC"}, {"only_trading": True}):
            with self.subTest(change=change), patch.object(binance, "_get") as fetch:
                with self.assertRaises(ResumeMismatch):
                    binance.fetch(out_dir=out, sleep=0, **change)
                fetch.assert_not_called()
        snap = json.loads((out / "_exchangeInfo.json").read_text())
        (PKG_ROOT / snap["path"]).write_bytes(b"corrupt")
        with patch.object(binance, "_get") as fetch:
            with self.assertRaises(CacheIntegrityError):
                binance.fetch(out_dir=out, sleep=0)
            fetch.assert_not_called()

    def test_failed_attempt_raw_bytes_are_preserved_when_later_response_differs(self):
        path = self.root / "ABC.error.json"
        first = save_raw(path, b"first failure")
        second = save_raw(path, b"later failure")
        self.assertNotEqual(first, second)
        self.assertEqual(first.read_bytes(), b"first failure")
        self.assertEqual(second.read_bytes(), b"later failure")


if __name__ == "__main__":
    unittest.main()
