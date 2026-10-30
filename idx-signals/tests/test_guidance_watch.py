import unittest

from idxsig import guidance_watch as w

INDEX = """Description:           Daily Index of EDGAR Dissemination Feed by Form Type
Form Type   Company Name                                                  CIK         Date Filed  File Name
---------------------------------------------------------------------------------------------------------------
10-Q        ACME CORP                                                     1234        20261016    edgar/data/1234/0001234-26-000010.txt
8-K         AGILENT TECHNOLOGIES INC                                      1090872     20261016    edgar/data/1090872/0001090872-26-000020.txt
8-K/A       SOME CO                                                       55          20261016    edgar/data/55/0000055-26-000001.txt
"""

HEADER = b"""<SEC-HEADER>0001090872-26-000020.hdr.sgml : 20261016
<ACCEPTANCE-DATETIME>20261016161502
ACCESSION NUMBER:\t\t0001090872-26-000020
CONFORMED SUBMISSION TYPE:\t8-K
ITEM INFORMATION:\t\tResults of Operations and Financial Condition
ITEM INFORMATION:\t\tFinancial Statements and Exhibits
"""

OLD = [
    "Agilent has increased its outlook and now expects revenue of $5.825 billion to $5.900 billion for fiscal "
    "year 2021."
]
NEW = [
    "Agilent has increased its outlook and now expects revenue in the range of $6.15 billion to $6.21 billion for "
    "fiscal year 2021."
]


class WatchTests(unittest.TestCase):
    def test_form_index_keeps_8k_rows(self):
        rows = w.form_index_8k(INDEX)
        self.assertEqual(
            [(r["form"], r["cik"], r["filed"]) for r in rows],
            [("8-K", 1090872, "2026-10-16"), ("8-K/A", 55, "2026-10-16")],
        )
        self.assertEqual(rows[0]["path"], "edgar/data/1090872/0001090872-26-000020.txt")

    def test_header_items(self):
        self.assertEqual(w.header_items(HEADER), {"2.02"})
        self.assertEqual(w.header_items(b"ITEM INFORMATION: Other Events\n"), set())

    def test_raise_against_prior_guidance(self):
        ev, state = w.revisions({}, 1090872, "A", "acc1", "2021-05-25T16:05:00", OLD)
        self.assertEqual(ev, [])
        ev, state = w.revisions(state, 1090872, "A", "acc2", "2021-08-17T16:05:00", NEW)
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["class"], "RAISE")
        self.assertAlmostEqual(ev[0]["level_change"], 6180 / 5862.5 - 1)
        self.assertEqual(state["1090872|2021|dollar"]["accession"], "acc2")

    def test_too_close_or_too_far_apart_is_no_event(self):
        _, state = w.revisions({}, 1, "X", "a", "2021-05-25T16:05:00", OLD)
        self.assertEqual(w.revisions(state, 1, "X", "b", "2021-05-27T16:05:00", NEW)[0], [])
        self.assertEqual(w.revisions(state, 1, "X", "b", "2022-01-25T16:05:00", NEW)[0], [])

    def test_mismatch_is_flagged_not_traded(self):
        _, state = w.revisions(
            {},
            1,
            "X",
            "a",
            "2021-05-25T16:05:00",
            ["The company expects full year 2021 revenue of $100 million."],
        )
        ev, _ = w.revisions(
            state,
            1,
            "X",
            "b",
            "2021-08-25T16:05:00",
            ["The company expects full year 2021 revenue of $300 million."],
        )
        self.assertEqual(ev[0]["class"], "MISMATCH")


if __name__ == "__main__":
    unittest.main()
