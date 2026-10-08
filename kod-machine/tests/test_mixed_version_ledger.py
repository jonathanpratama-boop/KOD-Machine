"""Pin the first real v3 card alongside the committed v1 seeds.

The legacy test already verifies the whole ledger, and deletion/tamper tests
already exercise the integrity checks. This fixture ensures that verification
cannot silently become seed-only again and pins the PARTIAL-v3 hash recipe.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from kod.hashing import sha256_obj
from kod.ledger import Ledger
from kod.verify import _rebuild_case_sha


KOD_ROOT = Path(__file__).resolve().parents[1]
ZEAL_CASE = "KOD-R-ZEAL-20250312"
# Frozen in the October 8 research card and append-only opens registry.
ZEAL_SHA = "ca0b25a539a74a50f71e64e5a3f68dfc9a1a53f0508e5600e6caa2ee658b673e"


class CommittedMixedVersionLedger(unittest.TestCase):
    def test_real_v3_card_is_present_and_rebuilds_to_its_frozen_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "kod.db"
            shutil.copy(KOD_ROOT / "var" / "kod.db", db)
            ledger = Ledger(db)
            try:
                rows = ledger.rows("SELECT * FROM cases WHERE case_id = ?", (ZEAL_CASE,))
                self.assertEqual(len(rows), 1, "the committed ledger must retain its first real v3 card")
                case = dict(rows[0])
                self.assertEqual(case["card_hash_version"], "KOD-CARD-v3")
                self.assertEqual(case["integrity_level"], "PARTIAL")
                self.assertEqual(case["card_sha"], ZEAL_SHA)
                frozen = json.loads((KOD_ROOT / "registry" / "cards" / f"{ZEAL_CASE}.json").read_text())
                self.assertEqual(sha256_obj(frozen), ZEAL_SHA)
                self.assertEqual(_rebuild_case_sha(ledger, case), ZEAL_SHA)
            finally:
                ledger.conn.close()


if __name__ == "__main__":
    unittest.main()
