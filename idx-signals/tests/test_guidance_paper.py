import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from idxsig import guidance_paper as gp


def submission(acc, accepted, sentence):
    return (f"<SEC-HEADER>\n<ACCEPTANCE-DATETIME>{accepted}\nACCESSION NUMBER: {acc}\n"
            "ITEM INFORMATION:\t\tResults of Operations and Financial Condition\n</SEC-HEADER>\n"
            "<DOCUMENT>\n<TYPE>EX-99.1\n<TEXT>\n<p>" + sentence + "</p>\n</TEXT>\n</DOCUMENT>\n").encode()


OLD = ("Agilent has increased its outlook and now expects revenue of $5.825 billion to $5.900 billion for fiscal "
       "year 2021.")
NEW = ("Agilent has increased its outlook and now expects revenue in the range of $6.15 billion to $6.21 billion for "
       "fiscal year 2021.")


class FakeSec:
    def __init__(self):
        self.files = {}

    def day(self, d, rows):
        lines = ["Form Type   Company Name   CIK   Date Filed   File Name", "-" * 40]
        for form, cik, path, body in rows:
            lines.append(f"{form}        SOME COMPANY INC        {cik}        {d:%Y%m%d}    {path}")
            self.files[gp.ARCHIVES + path] = body
        self.files[gp.index_url(d)] = "\n".join(lines).encode()

    def get(self, url):
        return (200, self.files[url]) if url in self.files else (404, b"")


class PaperTests(unittest.TestCase):
    def setUp(self):
        self.sec = FakeSec()
        self.sec.day(date(2021, 5, 25), [("8-K", 1090872, "edgar/data/1090872/a-1.txt",
                                          submission("a-1", "20210525160500", OLD))])
        self.sec.day(date(2021, 8, 17), [("8-K", 1090872, "edgar/data/1090872/a-2.txt",
                                          submission("a-2", "20210817160500", NEW)),
                                         ("8-K", 99, "edgar/data/99/b-1.txt", submission("b-1", "20210817080000", NEW))])

    def test_raise_becomes_a_decision_only_for_universe_names(self):
        ciks = {1090872: "A"}
        _, _, state = gp.scan_day(date(2021, 5, 25), {}, self.sec.get, ciks)
        dec, ev, state = gp.scan_day(date(2021, 8, 17), state, self.sec.get, ciks,
                                     now=datetime(2021, 8, 17, 20, 0, tzinfo=timezone.utc))
        self.assertEqual([e["class"] for e in ev], ["RAISE"])
        self.assertEqual(len(dec), 1)
        d = dec[0]
        self.assertEqual((d["ticker"], d["accession"], d["terminal_decision"]), ("A", "a-2", "BUY ON TRIGGER"))
        self.assertEqual(d["acceptance_ny"], "2021-08-17T16:05:00")
        self.assertEqual(d["orders"], "none: paper only")

    def test_missing_index_day_is_empty(self):
        self.assertEqual(gp.scan_day(date(2021, 5, 29), {}, self.sec.get, {1090872: "A"})[:2], ([], []))

    def test_refuses_to_write_without_an_e10_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ledger.jsonl"
            saved = gp.E10_RESULT
            try:
                gp.E10_RESULT = Path(tmp) / "RESULT.json"
                with self.assertRaises(SystemExit):
                    gp.record([], [], date(2021, 8, 17), datetime.now(timezone.utc), dry_run=False, path=ledger)
                gp.E10_RESULT.write_text(json.dumps({"verdict": "FAIL"}))
                with self.assertRaises(SystemExit):
                    gp.record([], [], date(2021, 8, 17), datetime.now(timezone.utc), dry_run=False, path=ledger)
                self.assertFalse(ledger.exists())
                recs = gp.record([], [], date(2021, 8, 17), datetime.now(timezone.utc), dry_run=True, path=ledger)
                self.assertEqual(recs[0]["events"], "NO SIGNAL")
                self.assertFalse(ledger.exists())
            finally:
                gp.E10_RESULT = saved

    def test_e10_passed_reads_only_the_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "RESULT.json"
            self.assertFalse(gp.e10_passed(p))
            p.write_text(json.dumps({"verdict": "PASS"}))
            self.assertTrue(gp.e10_passed(p))


if __name__ == "__main__":
    unittest.main()
