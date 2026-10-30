from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("collect_premove_crypto", Path(__file__).resolve().parents[2] / "tools" / "collect_premove_crypto.py")
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


def bar(t=collector.START_MS, close="11"):
    return [t, "10", "12", "9", close, "100", t + collector.DAY_MS - 1, "1000", 10, "50", "500", "0"]


class PremoveCollector(unittest.TestCase):
    def test_archive_catalog_namespace_and_pagination(self):
        body = b'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><IsTruncated>true</IsTruncated><NextMarker>data/spot/monthly/klines/ZZZUSDT/</NextMarker><CommonPrefixes><Prefix>data/spot/monthly/klines/BTCUSDT/</Prefix></CommonPrefixes></ListBucketResult>'
        pairs, marker, more = collector.catalog_page(body)
        self.assertEqual(pairs, ["BTCUSDT"])
        self.assertEqual(marker, "data/spot/monthly/klines/ZZZUSDT/")
        self.assertTrue(more)

    def test_universe_excludes_stable_and_existing_leveraged_filter(self):
        self.assertTrue(collector.eligible_pair("BTCUSDT"))
        for pair in ("BTCBUSD", "USDCUSDT", "BTCUPUSDT", "ETHDOWNUSDT", "USDT"):
            self.assertFalse(collector.eligible_pair(pair))

    def test_panel_rows_preserve_units_duplicates_and_large_moves(self):
        rows = [bar(collector.START_MS + collector.DAY_MS), bar(), bar()]
        frame = collector.rows_frame(rows, "BTCUSDT")
        self.assertEqual(len(frame), 2)
        self.assertEqual(frame.date.tolist(), ["2020-01-01", "2020-01-02"])
        self.assertEqual(frame.value.iloc[0], 1000)
        self.assertEqual(frame.volume.iloc[0], 100)
        move = bar(collector.START_MS + 2 * collector.DAY_MS)
        move[1:5] = ["110", "120", "90", "110"]
        # A future reversal cannot retroactively remove the large-move row.
        self.assertEqual(len(collector.rows_frame([bar(), move, bar(collector.START_MS + 3 * collector.DAY_MS)], "XUSDT")), 3)

    def test_sealed_and_invalid_rows_are_rejected(self):
        invalid = [bar(1704067200000), bar(1577750400000), bar(collector.START_MS + 1)]
        nonfinite = bar(); nonfinite[4] = "NaN"; invalid.append(nonfinite)
        bad = bar(); bad[2] = "9"; invalid.append(bad)
        for row in invalid:
            with self.subTest(row=row):
                with self.assertRaises(ValueError): collector.rows_frame([row], "BTCUSDT")
        with self.assertRaises(ValueError): collector.rows_frame([bar(), bar(close="10")], "BTCUSDT")

    def test_short_delisting_day_is_preserved_and_flagged(self):
        short = bar(collector.START_MS + collector.DAY_MS)
        short[6] = short[0] + 9 * 3600 * 1000 - 1
        frame = collector.rows_frame([bar(), short], "DELISTEDUSDT")
        self.assertEqual(frame.complete_bar.tolist(), [True, False])
        self.assertEqual(len(frame), 2)
        short[6] = short[0] - 1
        with self.assertRaises(ValueError): collector.rows_frame([short], "DELISTEDUSDT")

    def test_reuse_verifies_bytes_and_preserves_observation_time(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root) / "old"; out = Path(root) / "new"
            base.mkdir(); out.mkdir()
            body = json.dumps([bar()]).encode()
            rec = {"url": "https://example.test/exact?end=2023", "path": "raw/pair.json",
                   "sha256": collector.digest(body), "bytes": len(body), "observed_at": "original-time"}
            collector.publish_bytes(base / rec["path"], body)
            collector.dump(base / "records" / "pair.json", {"requests": [rec]})
            client = collector.Collector(out, base)
            actual, recorded = client.get(rec["url"], "raw/copied.json")
            self.assertEqual(actual, body)
            self.assertEqual(recorded["observed_at"], "original-time")
            self.assertEqual((out / "raw/copied.json").read_bytes(), body)
            self.assertNotIn("https://example.test/exact?end=2024", client.cache)
            (base / rec["path"]).write_bytes(b"corrupt")
            with self.assertRaises(ValueError): client.get(rec["url"], "raw/corrupt.json")

    def test_empty_window_is_not_failure(self):
        with tempfile.TemporaryDirectory() as root:
            client = collector.Collector(root)
            client.get = lambda url, path: (b"[]", {"url": url, "path": path})
            result, frame = client.pair("NEWUSDT")
            self.assertEqual(result["status"], "empty_in_window")
            self.assertTrue(frame.empty)

    def test_reused_universe_is_derived_from_verified_catalog(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root) / "old"; out = Path(root) / "new"
            base.mkdir(); out.mkdir()
            body = b'<ListBucketResult><IsTruncated>false</IsTruncated><CommonPrefixes><Prefix>data/spot/monthly/klines/BTCUSDT/</Prefix></CommonPrefixes></ListBucketResult>'
            rec = {"url": "https://example.test/catalog", "path": "catalog/page-0.xml", "sha256": collector.digest(body), "bytes": len(body)}
            collector.publish_bytes(base / rec["path"], body)
            collector.dump(base / "UNIVERSE.json", {"pairs": ["BTCUSDT"], "catalog_pages": [rec]})
            client = collector.Collector(out, base)
            self.assertEqual(client.universe(), ["BTCUSDT"])
            self.assertEqual((out / "UNIVERSE.json").read_bytes(), (base / "UNIVERSE.json").read_bytes())
            (base / "UNIVERSE.json").write_text(json.dumps({"pairs": ["BTCUSDT", "ETHUSDT"], "catalog_pages": [rec]}))
            with self.assertRaises(ValueError): collector.Collector(Path(root) / "bad", base).universe()

    def test_failed_pair_is_explicit_and_never_a_synthetic_zero(self):
        with tempfile.TemporaryDirectory() as root:
            client = collector.Collector(root)
            def fail(url, path):
                raise TimeoutError("provider unavailable")
            client.get = fail
            result, frame = client.pair("GONEUSDT")
            self.assertEqual(result["status"], "failed")
            self.assertIsNone(frame)
            self.assertEqual(result["error_type"], "TimeoutError")


if __name__ == "__main__":
    unittest.main()
