import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from idxsig.guidance_margin_directory import refresh, listed_issuer, company_key
from idxsig.guidance_margin_identity import resolve_identity


class DirectoryTests(unittest.TestCase):
    def test_daily_snapshot_and_publishing_account(self):
        data = json.dumps(
            {
                "fields": ["cik", "ticker", "exchange", "name"],
                "data": [
                    [1474432, "P", "NYSE", "Everpure, Inc."],
                    [100, "LOW", "NYSE", "LOWES COMPANIES INC"],
                ],
            }
        ).encode()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            at = datetime(2026, 11, 19, tzinfo=timezone.utc)
            snapshot = refresh(root, at=at, fetcher=lambda u: data)
            self.assertEqual(
                refresh(root, at=at, fetcher=lambda u: self.fail("repeated download")),
                snapshot,
            )
            result = resolve_identity("NYSE: P", "Everpure", directory=snapshot)
            self.assertEqual(result["issuer_cik"], "1474432")
            self.assertTrue(
                (root / "issuer_directory_sources" / result["sources"][0]["sha256"]).is_file()
            )
            self.assertIsNone(resolve_identity("NYSE: P", "Another Company", directory=snapshot))
            self.assertIsNone(
                resolve_identity("NYSE: P and NYSE: LOW", "Everpure", directory=snapshot)
            )
            self.assertEqual(
                resolve_identity("NYSE: LOW", "Lowe's Companies, Inc.", directory=snapshot)[
                    "issuer_cik"
                ],
                "100",
            )

    def test_current_conflict_blocks_old_static_alias(self):
        snapshot = {"listings": {"HD": ["1234", "Other Co", "NYSE"]}}
        self.assertIsNone(resolve_identity("NYSE: HD", "The Home Depot", directory=snapshot))
        self.assertIsNone(
            resolve_identity(
                "NYSE: HD",
                "The Home Depot",
                directory={"listings": {}, "unresolved_tickers": ["HD"]},
            )
        )

    def test_distinct_share_classes_and_wire_names(self):
        self.assertEqual(listed_issuer("Everpure, Inc. Class A common stock"), "Everpure, Inc.")
        self.assertEqual(
            company_key("Kulicke and Soffa Industries, Inc."),
            company_key("Kulicke & Soffa Industries Inc"),
        )
        self.assertNotEqual(company_key("Target Hospitality Corp"), company_key("Target Corp"))
