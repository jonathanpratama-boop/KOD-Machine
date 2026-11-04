"""MSCI_DELETION_OOT_v1 on fixtures: the page-aware MSCI parser, the sealed-window guard and the replication gates."""

import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1] / "research/MSCI_DELETION_OOT_v1"


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


be = load("oot_build_events", "build_events.py")
oot = load("oot", "oot.py")

PAGED = """MSCI INDONESIA INDEX
Additions                        Deletions
INDAH KIAT PULP & PAPER          BANK PEMBANGUNAN DAERAH
MERDEKA COPPER GOLD              ERAJAYA SWASEMBADA TBK

Page 2                     MSCI Global Small Cap Indexes - February 11, 2025   (c) MSCI 2025

SARIGUNA PRIMATIRTA             METRODATA ELECTRONICS
                                WIJAYA KARYA


MSCI PHILIPPINES INDEX
Additions                       Deletions
JG SUMMIT HOLDINGS              None
"""

FOOTER_THEN_NEXT_COUNTRY = """MSCI INDONESIA INDEX
Additions                                  Deletions
BARITO RENEWABLES ENERGY                   INDOFOOD CBP SUKSES
BUMI RESOURCES MINERALS                    KALBE FARMA

Page 1                                MSCI Global Standard Indexes - November 05, 2025

MSCI TAIWAN INDEX
Additions                                  Deletions
ASPEED TECHNOLOGY                          ACER
"""


class Parser(unittest.TestCase):
    def test_a_block_continues_after_a_page_footer_with_shifted_columns(self):
        adds, dels = be.indonesia_block(PAGED)
        self.assertEqual(
            adds, ["INDAH KIAT PULP & PAPER", "MERDEKA COPPER GOLD", "SARIGUNA PRIMATIRTA"]
        )
        self.assertEqual(
            dels,
            [
                "BANK PEMBANGUNAN DAERAH",
                "ERAJAYA SWASEMBADA TBK",
                "METRODATA ELECTRONICS",
                "WIJAYA KARYA",
            ],
        )

    def test_a_footer_followed_by_the_next_country_ends_the_block(self):
        adds, dels = be.indonesia_block(FOOTER_THEN_NEXT_COUNTRY)
        self.assertEqual(adds, ["BARITO RENEWABLES ENERGY", "BUMI RESOURCES MINERALS"])
        self.assertEqual(dels, ["INDOFOOD CBP SUKSES", "KALBE FARMA"])


class Window(unittest.TestCase):
    def test_no_entry_inside_the_sealed_holdout(self):
        sess = np.array(["2025-02-20", "2025-02-21", "2025-02-24"], dtype="datetime64[D]")
        ev = pd.DataFrame(
            [
                {
                    "review": "Feb25",
                    "side": "DEL",
                    "kind": "SC_EXIT",
                    "ticker": "AAAA",
                    "implementation_close": "2025-02-21",
                }
            ]
        )
        with self.assertRaises(RuntimeError):
            oot.oot_events(ev, sess)
        ev.loc[0, "implementation_close"] = "2025-02-24"
        self.assertEqual(oot.oot_events(ev, sess).entry_session.tolist(), ["2025-02-24"])


class Gates(unittest.TestCase):
    def res(self, net=0.02, exc=0.01, lb=-0.01, n=20, reviews=5, end=170.0):
        return {
            "primary": {
                "scored_with_controls": n,
                "by_review": {str(i): {} for i in range(reviews)},
                "mean_net": net,
                "mean_excess": exc,
                "boot_excess": {"lower_one_sided_95": lb},
            },
            "account": {"start": 160.0, "end_equity": end},
        }

    def test_verdicts(self):
        self.assertEqual(oot.gates(self.res())["verdict"], "CONFIRMED")
        self.assertEqual(oot.gates(self.res(lb=0.001))["verdict"], "CONFIRMED_STRONG")
        self.assertEqual(oot.gates(self.res(exc=-0.001))["verdict"], "NOT_CONFIRMED")
        self.assertEqual(oot.gates(self.res(end=150.0))["verdict"], "NOT_CONFIRMED")
        self.assertEqual(oot.gates(self.res(n=10))["verdict"], "INCONCLUSIVE")
        self.assertEqual(oot.gates(self.res(reviews=3))["verdict"], "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
