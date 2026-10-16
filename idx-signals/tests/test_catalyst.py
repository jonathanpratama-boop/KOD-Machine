"""Synthetic tests for idxsig/catalyst.py (E9). No network."""
import json
import unittest

import pandas as pd

from idxsig import catalyst as C


def filings(rows):
    return pd.DataFrame(rows, columns=list(C.COLUMNS))


def row(acc, accepted, form, items=""):
    return (acc, accepted[:10], accepted, form, items, "doc.htm")


class Window(unittest.TestCase):
    def test_window_runs_from_the_prior_close_to_15_minutes_before_the_open(self):
        a, b = C.window("2021-04-26", "2021-04-28")
        self.assertEqual((a.hour, a.minute, str(a.date())), (16, 0, "2021-04-26"))
        self.assertEqual((b.hour, b.minute, str(b.date())), (9, 15, "2021-04-28"))
        self.assertEqual(a.utcoffset().total_seconds(), -4 * 3600)  # EDT

    def test_edges(self):
        a, b = C.window("2021-04-26", "2021-04-28")
        f = filings([row("1", "2021-04-26T16:00:00.000Z", "8-K")])
        self.assertEqual(C.classify(f, a, b, "ny")["class"], "UNDOCUMENTED")      # exactly at the prior close
        f = filings([row("1", "2021-04-26T16:00:01.000Z", "8-K")])
        self.assertEqual(C.classify(f, a, b, "ny")["class"], "DOCUMENTED")
        f = filings([row("1", "2021-04-28T09:15:00.000Z", "8-K")])
        self.assertEqual(C.classify(f, a, b, "ny")["class"], "DOCUMENTED")        # at the cutoff: known
        f = filings([row("1", "2021-04-28T09:15:01.000Z", "8-K")])
        self.assertEqual(C.classify(f, a, b, "ny")["class"], "UNDOCUMENTED")      # too late for the entry

    def test_convention_changes_the_clock(self):
        a, b = C.window("2021-04-26", "2021-04-28")
        f = filings([row("1", "2021-04-28T13:10:00.000Z", "8-K")])   # 13:10 UTC = 09:10 EDT
        self.assertEqual(C.classify(f, a, b, "utc")["class"], "DOCUMENTED")
        self.assertEqual(C.classify(f, a, b, "ny")["class"], "UNDOCUMENTED")
        self.assertRaises(ValueError, C.acceptance_ny, "2021-04-28T13:10:00.000Z", "local")

    def test_double_conversion_matches_the_probed_sgml_headers(self):
        # amendment 1: JSON = New York time converted to UTC twice (+8 h in summer, +10 h in winter)
        for js, sgml in (("2021-04-28T00:12:09.000Z", "20210427161209"), ("2022-12-17T02:15:08.000Z", "20221216161508"),
                         ("2021-01-30T03:24:00.000Z", "20210129172400"), ("2022-03-25T00:18:54.000Z", "20220324161854")):
            self.assertEqual(C.acceptance_ny(js, "double").strftime("%Y%m%d%H%M%S"), sgml)
            self.assertNotEqual(C.acceptance_ny(js, "utc").strftime("%Y%m%d%H%M%S"), sgml)


class Classes(unittest.TestCase):
    def setUp(self):
        self.a, self.b = C.window("2021-04-26", "2021-04-28")

    def test_dilution_wins_over_information(self):
        f = filings([row("1", "2021-04-27T08:00:00.000Z", "8-K", "8.01"),
                     row("2", "2021-04-27T17:30:00.000Z", "424B5")])
        r = C.classify(f, self.a, self.b, "ny")
        self.assertEqual(r["class"], "DILUTION")
        self.assertIn("424B5", r["evidence"])

    def test_item_302_is_dilution_and_other_items_are_information(self):
        f = filings([row("1", "2021-04-27T08:00:00.000Z", "8-K", "3.02,9.01")])
        self.assertEqual(C.classify(f, self.a, self.b, "ny")["class"], "DILUTION")
        f = filings([row("1", "2021-04-27T08:00:00.000Z", "8-K", "1.01,7.01,9.01")])
        r = C.classify(f, self.a, self.b, "ny")
        self.assertEqual((r["class"], r["items_8k"]), ("DOCUMENTED", "1.01;7.01;9.01"))

    def test_non_information_filings_leave_it_undocumented(self):
        f = filings([row("1", "2021-04-27T08:00:00.000Z", "4"), row("2", "2021-04-27T09:00:00.000Z", "S-8"),
                     row("3", "2021-04-27T10:00:00.000Z", "SC 13G")])
        r = C.classify(f, self.a, self.b, "ny")
        self.assertEqual((r["class"], r["n_filings_in_window"]), ("UNDOCUMENTED", 3))

    def test_foreign_issuer_6k_counts(self):
        f = filings([row("1", "2021-04-27T06:00:00.000Z", "6-K")])
        self.assertEqual(C.classify(f, self.a, self.b, "ny")["class"], "DOCUMENTED")

    def test_no_filings_at_all(self):
        self.assertEqual(C.classify(filings([]), self.a, self.b, "ny")["class"], "UNDOCUMENTED")

    def test_a_filing_without_an_acceptance_time_is_in_no_window(self):
        f = filings([row("1", "2021-04-27T08:00:00.000Z", "8-K", "8.01"), ("2", "2021-04-27", "", "424B5", "", "p.htm"),
                     ("3", "2021-04-27", None, "424B5", "", "p.htm")])
        r = C.classify(f, self.a, self.b, "double")
        self.assertEqual((r["class"], r["n_filings_in_window"]), ("DOCUMENTED", 1))
        self.assertEqual(C.accepted(f, "double").isna().tolist(), [False, True, True])
        self.assertFalse(C.later_documentation(f.iloc[1:], self.b, 4, "double"))

    def test_header_times_decide_when_given(self):
        # amendment 3: the SGML header (New York time) replaces the JSON field, whose convention varies
        self.assertEqual(C.header_acceptance(b"<SEC-HEADER>\n<ACCEPTANCE-DATETIME>20210427161209\n"), "20210427161209")
        self.assertIsNone(C.header_acceptance(b"<html>not found</html>"))
        t = C.acceptance_ny("20210427161209", "header")
        self.assertEqual((str(t), t.utcoffset().total_seconds()), ("2021-04-27 16:12:09-04:00", -4 * 3600))
        f = filings([row("1", "2021-04-28T00:12:09.000Z", "8-K", "2.02"), row("2", "2021-04-27T20:00:00.000Z", "424B5"),
                     row("3", "2021-04-27T20:00:00.000Z", "8-K", "8.01")])
        f["acceptanceHeader"] = ["20210427161209", "", "20210428091600"]  # 2: no header fetched; 3: after 09:15
        r = C.classify(f, self.a, self.b, "header")
        self.assertEqual((r["class"], r["n_filings_in_window"], r["items_8k"]), ("DOCUMENTED", 1, "2.02"))
        self.assertIn("2021-04-27T16:12:09 NY", r["evidence"])
        self.assertTrue(C.later_documentation(f, self.b, 4, "header"))

    def test_later_documentation_is_diagnostic_only(self):
        f = filings([row("1", "2021-04-29T16:30:00.000Z", "8-K", "8.01")])
        self.assertEqual(C.classify(f, self.a, self.b, "ny")["class"], "UNDOCUMENTED")
        self.assertTrue(C.later_documentation(f, self.b, 4, "ny"))
        self.assertFalse(C.later_documentation(f, self.b, 1, "ny"))


class Parsing(unittest.TestCase):
    def test_submissions_and_chunks(self):
        recent = {c: [] for c in C.COLUMNS}
        for c, v in zip(C.COLUMNS, ("0001-21-000001", "2021-04-27", "2021-04-27T08:00:00.000Z", "8-K", "8.01", "a.htm")):
            recent[c].append(v)
        main = {"filings": {"recent": recent, "files": [
            {"name": "CIK0000000001-submissions-001.json", "filingFrom": "2019-01-01", "filingTo": "2020-05-31"},
            {"name": "CIK0000000001-submissions-002.json", "filingFrom": "2020-06-01", "filingTo": "2022-01-31"}]}}
        chunk = {c: [] for c in C.COLUMNS if c != "items"}
        for c, v in zip([c for c in C.COLUMNS if c != "items"],
                        ("0001-20-000009", "2020-07-01", "2020-07-01T07:00:00.000Z", "6-K", "b.htm")):
            chunk[c].append(v)
        body = json.dumps(main).encode()
        self.assertEqual(C.chunk_names(body, "2020-06-01", "2023-01-31"), ["CIK0000000001-submissions-002.json"])
        nulls = {"accessionNumber": ["0001-20-000010"], "filingDate": ["2020-07-02"], "acceptanceDateTime": [None],
                 "form": ["8-K"], "items": [None], "primaryDocument": ["c.htm"]}
        df = C.parse_submissions(body, [json.dumps(chunk).encode(), json.dumps(recent).encode(),
                                        json.dumps(nulls).encode()])
        self.assertEqual(sorted(df.accessionNumber), ["0001-20-000009", "0001-20-000010", "0001-21-000001"])  # de-duplicated
        self.assertEqual(df.set_index("accessionNumber").loc["0001-20-000009", "items"], "")
        self.assertEqual(df.set_index("accessionNumber").loc["0001-20-000010", "acceptanceDateTime"], "")


if __name__ == "__main__":
    unittest.main()
