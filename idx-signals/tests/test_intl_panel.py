"""INTL universe mapping and profiles (LEAD_LADDER_INTL_v1), on a synthetic eToro snapshot."""

import json
import tempfile
import unittest
from pathlib import Path

from idxsig import intl_panel


def proto_for(snapshot: Path) -> dict:
    p = intl_panel.protocol()
    from idxsig.provenance import sha256_file

    p["etoro_snapshot"]["sha256"] = sha256_file(snapshot)
    return p


class IntlTests(unittest.TestCase):
    def test_universe_maps_symbols_and_skips_others(self):
        rows = [{"InstrumentTypeID": 5, "ExchangeID": 21, "SymbolFull": "00001.HK"},
                {"InstrumentTypeID": 5, "ExchangeID": 21, "SymbolFull": "1810.HK"},
                {"InstrumentTypeID": 5, "ExchangeID": 31, "SymbolFull": "BHP.ASX"},
                {"InstrumentTypeID": 5, "ExchangeID": 11, "SymbolFull": "BMPS-old"},
                {"InstrumentTypeID": 5, "ExchangeID": 7, "SymbolFull": "VOD.L", "IsInternalInstrument": True},
                {"InstrumentTypeID": 1, "ExchangeID": 6, "SymbolFull": "EURUSD"},
                {"InstrumentTypeID": 5, "ExchangeID": 6, "SymbolFull": "SAP.DE"}]
        with tempfile.TemporaryDirectory() as d:
            snap = Path(d) / "i.json"
            snap.write_text(json.dumps({"InstrumentDisplayDatas": rows}))
            p = proto_for(snap)
            self.assertEqual(intl_panel.universe("HK", p, snap), ["0001", "1810"])
            self.assertEqual(intl_panel.universe("AU", p, snap), ["BHP"])
            self.assertEqual(intl_panel.universe("IT", p, snap), [])
            self.assertEqual(intl_panel.universe("UK", p, snap), [])
            self.assertEqual(intl_panel.universe("DE", p, snap), ["SAP"])

    def test_snapshot_hash_is_checked(self):
        with tempfile.TemporaryDirectory() as d:
            snap = Path(d) / "i.json"
            snap.write_text(json.dumps({"InstrumentDisplayDatas": []}))
            with self.assertRaises(RuntimeError):
                intl_panel.universe("DE", intl_panel.protocol(), snap)

    def test_profiles_use_local_band_edges_and_no_price_limits(self):
        for m in intl_panel.protocol()["markets"]:
            prof = intl_panel.profile(m)
            self.assertFalse(prof.price_limits)
            self.assertEqual(len(prof.band_names), len(prof.band_edges) + 1)
        self.assertEqual(intl_panel.profile("JP").band_edges, (150, 750, 3000))


if __name__ == "__main__":
    unittest.main()
