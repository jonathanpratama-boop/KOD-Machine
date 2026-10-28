"""KILL_TEST_2020_2022 (research/CATALYST_REGISTER_v1/KILL_TEST_2020_2022): kt_lib's pure rules and collect.py's flow
with a fake client. Synthetic data only, no network. Each test names the failure it guards against."""

from __future__ import annotations

import contextlib
import gzip
import importlib.util
import io
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1] / "research" / "CATALYST_REGISTER_v1" / "KILL_TEST_2020_2022"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"kill_test_{name}", BASE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


kt = _load("kt_lib")
NY = kt.NY


def idx_line(form, name, cik, day, acc):
    return f"{form:<17}{name:<62}{cik:<12}{day}  edgar/data/{cik}/{acc}.txt         \n"


def header(acc, accepted, subject, filer, subject_first=False, sgml=True):
    """An -index-headers.html page: the SGML block in a comment and the text block in <PRE>, FILED BY first unless
    subject_first."""
    subj = f"<SUBJECT-COMPANY>\n<COMPANY-DATA>\n<CONFORMED-NAME>{subject[1]}\n<CIK>{subject[0]:010d}\n</COMPANY-DATA>\n</SUBJECT-COMPANY>\n"
    filed = f"<FILED-BY>\n<COMPANY-DATA>\n<CONFORMED-NAME>{filer[1]}\n<CIK>{filer[0]:010d}\n</COMPANY-DATA>\n</FILED-BY>\n"
    tsubj = (f"SUBJECT COMPANY:\t\n\n\tCOMPANY DATA:\t\n\t\tCOMPANY CONFORMED NAME:\t\t\t{subject[1]}\n"
             f"\t\tCENTRAL INDEX KEY:\t\t\t{subject[0]:010d}\n\n")
    tfiled = (f"FILED BY:\t\t\n\n\tCOMPANY DATA:\t\n\t\tCOMPANY CONFORMED NAME:\t\t\t{filer[1]}\n"
              f"\t\tCENTRAL INDEX KEY:\t\t\t{filer[0]:010d}\n\n")
    block = (subj + filed) if subject_first else (filed + subj)
    text = (tsubj + tfiled) if subject_first else (tfiled + tsubj)
    sg = f"<!--\n<SEC-HEADER>{acc}.hdr.sgml : 20200702\n<ACCEPTANCE-DATETIME>{accepted}\n{block}</SEC-HEADER>\n-->\n" if sgml else ""
    return (f"<HTML><HEAD><TITLE>SEC EDGAR Submission {acc}</TITLE>\n{sg}</HEAD><BODY>\n<PRE>&lt;SEC-HEADER&gt;{acc}.hdr.sgml\n"
            f"&lt;ACCEPTANCE-DATETIME&gt;{accepted}\nACCESSION NUMBER:\t\t{acc}\nCONFORMED SUBMISSION TYPE:\tSC 13D\n\n"
            f"{text}&lt;/SEC-HEADER&gt;\n</PRE></BODY></HTML>").encode()


def sessions(start="2020-06-01", end="2022-12-30", holidays=("2020-07-03",)):
    days = pd.bdate_range(start, end).strftime("%Y-%m-%d")
    return np.array([d for d in days if d not in holidays])


def ny(s):
    return datetime.fromisoformat(s).replace(tzinfo=NY)


class FormIndex(unittest.TestCase):
    def test_only_original_sc13d_rows_are_kept_once_per_accession(self):
        lines = ["Form Type   Company Name   CIK   Date Filed  File Name\n", "-" * 140 + "\n",
                 idx_line("SC 13D", "Alpha  Holdings Inc", 1000, "2020-07-06", "0000000001-20-000001"),
                 idx_line("SC 13D", "Fund A LP", 5000, "2020-07-06", "0000000001-20-000001"),
                 idx_line("SC 13D/A", "Beta Inc", 1001, "2020-07-07", "0000000001-20-000002"),
                 idx_line("SC 13G", "Gamma Inc", 1002, "2020-07-07", "0000000001-20-000003"),
                 idx_line("SC 13D", "Delta Inc", 1003, "2020-07-08", "0000000001-20-000004")]
        kept = [x for x in lines if kt.is_13d_line(x)]
        self.assertEqual(len(kept), 4)  # the pre-filter keeps amendments; the parser decides
        rows = [kt.parse_form_line(x) for x in kept]
        self.assertEqual(rows[0]["name"], "Alpha  Holdings Inc")  # a double space inside a name survives
        orig = kt.originals(rows)
        self.assertEqual([o["accession"] for o in orig], ["0000000001-20-000001", "0000000001-20-000004"])
        self.assertEqual(orig[0]["index_ciks"], [1000, 5000])
        self.assertIsNone(kt.parse_form_line(lines[0]))
        self.assertEqual(kt.header_url(1000, "0000000001-20-000001"), "https://www.sec.gov/Archives/edgar/data/1000/"
                         "000000000120000001/0000000001-20-000001-index-headers.html")
        self.assertEqual(kt.quarter_url("2021Q3"), "https://www.sec.gov/Archives/edgar/full-index/2021/QTR3/form.idx")


class Header(unittest.TestCase):
    def test_the_subject_is_read_whichever_section_comes_first(self):
        for subject_first in (False, True):
            for sgml in (True, False):
                h = kt.parse_header(header("0000000001-20-000001", "20200702135103", (1508475, "Subject Co"),
                                           (1758419, "Filer LP"), subject_first, sgml))
                self.assertEqual(h["subject_cik"], 1508475, (subject_first, sgml))
                self.assertEqual(h["subject_name"], "Subject Co")
                self.assertEqual(h["filed_by"], ["Filer LP"])
                self.assertEqual(h["accepted"], "2020-07-02T13:51:03-04:00")  # New York, EDT

    def test_a_page_without_acceptance_or_subject_gives_nothing(self):
        self.assertEqual(kt.parse_header(None), {"accepted": None, "subject_cik": None, "subject_name": None, "filed_by": []})
        h = kt.parse_header(b"<HTML><PRE>FILED BY:\n\t\tCENTRAL INDEX KEY:\t\t0000005000\n</PRE></HTML>")
        self.assertIsNone(h["subject_cik"])
        self.assertIsNone(h["accepted"])


class Timing(unittest.TestCase):
    S = sessions()

    def test_entry_is_the_first_panel_session_whose_0915_is_after_acceptance(self):
        self.assertEqual(kt.entry_session(ny("2020-07-01T09:14:59"), self.S), "2020-07-01")
        self.assertEqual(kt.entry_session(ny("2020-07-01T09:15:00"), self.S), "2020-07-02")  # at 09:15 is too late
        self.assertEqual(kt.entry_session(ny("2020-07-02T17:00:00"), self.S), "2020-07-06")  # holiday Friday and weekend
        self.assertEqual(kt.entry_session(ny("2020-07-04T11:00:00"), self.S), "2020-07-06")  # a Saturday
        self.assertIsNone(kt.entry_session(ny("2022-12-30T10:00:00"), self.S))  # past the panel
        self.assertEqual(kt.prev_session("2020-07-06", self.S), "2020-07-02")

    def test_position_during_or_after_the_signal_close(self):
        acc = ny("2020-07-02T15:59:00")
        e = kt.entry_session(acc, self.S)
        s = kt.prev_session(e, self.S)
        self.assertEqual((e, s), ("2020-07-06", "2020-07-02"))
        self.assertEqual(kt.position(acc, s, kt.prev_session(s, self.S)), "DURING")
        acc = ny("2020-07-06T08:00:00")  # pre-open Monday: entry that Monday, signal Thursday, AFTER its close
        e = kt.entry_session(acc, self.S)
        s = kt.prev_session(e, self.S)
        self.assertEqual((e, s, kt.position(acc, s, kt.prev_session(s, self.S))), ("2020-07-06", "2020-07-02", "AFTER"))
        self.assertEqual(kt.position(ny("2020-07-01T15:00:00"), "2020-07-02", "2020-07-01"), "LATE")


def stored(rows):
    """Stored rule inputs from (form, filingDate, items) rows, through encode_filings as collect.py writes them."""
    df = pd.DataFrame([{"form": f, "filingDate": d, "items": i, "accessionNumber": f"0000000000-20-{k:06d}"}
                       for k, (f, d, i) in enumerate(rows)])
    return kt.encode_filings(df)


class Rules(unittest.TestCase):
    def test_dilution_window_runs_from_the_19th_weekday_before_the_signal_to_acceptance(self):
        # signal 2020-07-30 (Thu): 19 weekdays before is 2020-07-03; acceptance 2020-07-31 09:00
        dil, op = stored([("424B5", "2020-07-03", ""), ("10-Q", "2020-05-10", "")])
        acc = ny("2020-07-31T09:00:00")
        c = kt.rules(dil, op, "2020-06-30|2020-08-01|10000000", "2020-07-30", acc, "AFTER", 10.0, 10.0, 10.0)
        self.assertTrue(c["rules"]["DILUTION_RECENT"])
        dil, op = stored([("424B5", "2020-07-02", ""), ("8-K", "2020-07-31", "3.02"), ("8-K", "2020-07-29", "2.02")])
        c = kt.rules(dil, op, "", "2020-07-30", acc, "AFTER", 10.0, 10.0, 10.0)
        self.assertEqual(len(c["inputs"]["dilution_filings"]), 1)  # the same-day 3.02 8-K; 07-02 is too early
        dil, op = stored([("8-K", "2020-08-03", "3.02")])  # after acceptance
        self.assertFalse(kt.rules(dil, op, "", "2020-07-30", acc, "AFTER", 10, 10, 10)["rules"]["DILUTION_RECENT"])

    def test_moved_already_is_the_signal_move_during_and_never_after(self):
        acc = ny("2020-07-30T11:00:00")
        shares = "2020-06-30|2020-07-15|10000000"
        moved = kt.rules("", "", shares, "2020-07-30", acc, "DURING", 11.5, 10.0, 11.5)
        self.assertTrue(moved["rules"]["MOVED_ALREADY"])
        self.assertAlmostEqual(moved["inputs"]["pre_entry_move"], 0.15)
        self.assertFalse(kt.rules("", "", shares, "2020-07-30", acc, "DURING", 11.49, 10.0, 11.49)["rules"]["MOVED_ALREADY"])
        self.assertFalse(kt.rules("", "", shares, "2020-07-30", acc, "AFTER", 20.0, 10.0, 20.0)["rules"]["MOVED_ALREADY"])

    def test_microcap_uses_the_latest_fact_filed_by_acceptance_and_the_as_traded_close(self):
        acc = ny("2020-07-30T11:00:00")
        shares = "2020-03-31|2020-05-01|4000000;2020-06-30|2020-08-05|100000000"  # the larger fact is filed later
        c = kt.rules("", "", shares, "2020-07-30", acc, "AFTER", 5.0, 5.0, 10.0)
        self.assertEqual(c["inputs"]["market_value_usd"], 4e7)  # 4M shares x 10.0 as traded
        self.assertTrue(c["rules"]["MICROCAP"])
        self.assertEqual(c["class"], "ABSTAIN")
        c = kt.rules("", "", "2020-03-31|2020-05-01|6000000", "2020-07-30", acc, "AFTER", 5.0, 5.0, 10.0)
        self.assertEqual((c["class"], c["reasons"]), ("FIRE", []))
        c = kt.rules("", "", "", "2020-07-30", acc, "AFTER", 5.0, 5.0, 10.0)
        self.assertEqual(c["reasons"], ["MV_UNKNOWN"])
        self.assertEqual(kt.decode_shares(kt.encode_shares(kt.decode_shares(shares))), kt.decode_shares(shares))

    def test_operating_issuer_on_the_stored_forms(self):
        self.assertTrue(kt.operating(*stored([("10-Q", "2019-03-01", "")]), "2020-08-01"))
        self.assertFalse(kt.operating(*stored([("10-K", "2019-01-01", "")]), "2020-08-01"))  # 578 days before
        self.assertFalse(kt.operating(*stored([("10-Q", "2020-05-01", ""), ("N-CSR", "2020-02-01", "")]), "2020-08-01"))
        self.assertFalse(kt.operating("", "", "2020-08-01"))
        dil, op = stored([("S-3", "2019-12-31", ""), ("S-3", "2020-01-02", ""), ("8-K", "2020-03-01", "7.01")])
        self.assertEqual([x.split("|")[0] for x in dil.split(";")], ["S-3"])  # from 2020-01-01, is_dilution only
        self.assertEqual(op, "")


class Repeat(unittest.TestCase):
    def test_the_90_day_chain_counts_dropped_filings_and_the_first_one_wins(self):
        ev = pd.DataFrame([
            ("A1", 1, "2020-04-10T10:00:00-04:00"), ("A2", 1, "2020-06-20T10:00:00-04:00"),
            ("A3", 1, "2020-09-10T10:00:00-04:00"), ("A4", 1, "2021-01-05T10:00:00-05:00"),
            ("B1", 2, "2020-06-20T10:00:00-04:00"), ("B0", 2, "2020-06-20T10:00:00-04:00"),
            ("C1", None, "2020-06-20T10:00:00-04:00")], columns=["accession", "subject_cik", "accepted"])
        rep = kt.repeats(ev)
        # A2 within 90 days of A1; A3 is 82 days after A2 (A2 itself dropped, still counts); A4 is 117 days after A3
        self.assertEqual(rep.tolist(), ["", "A1", "A2", "", "B0", "", ""])


class Funnel(unittest.TestCase):
    def test_drops_in_the_protocol_order_and_classes_from_the_bars(self):
        S = sessions()
        base = {"date_filed": "2020-07-06", "subject_cik": 10, "tickers": "AAA", "shares": "2020-06-30|2020-07-01|100000000",
                **dict(zip(("dilution", "opforms"), stored([("10-Q", "2020-05-01", "")])))}
        rows = [{**base, "accession": "N", "accepted": None},
                {**base, "accession": "SEED", "date_filed": "2020-06-30", "accepted": "2020-06-30T10:00:00-04:00", "subject_cik": 11},
                {**base, "accession": "LATE", "date_filed": "2022-12-01", "accepted": "2022-12-01T10:00:00-05:00", "subject_cik": 12},
                {**base, "accession": "NOTK", "accepted": "2020-07-06T10:00:00-04:00", "tickers": "ZZZ;YYY", "subject_cik": 13},
                {**base, "accession": "F1", "accepted": "2020-07-06T10:00:00-04:00", "tickers": "ZZZ;AAA"},
                {**base, "accession": "R1", "accepted": "2020-08-06T10:00:00-04:00"},
                {**base, "accession": "NOP", "accepted": "2020-07-06T10:00:00-04:00", "subject_cik": 14, "tickers": "BBB",
                 "opforms": "N-CSR|2020-05-01"},
                {**base, "accession": "MOV", "accepted": "2020-07-08T11:00:00-04:00", "subject_cik": 15, "tickers": "CCC"},
                {**base, "accession": "GAP", "accepted": "2020-07-08T11:00:00-04:00", "subject_cik": 16, "tickers": "DDD"}]
        ev = kt.funnel(pd.DataFrame(rows), S, {"AAA", "BBB", "CCC", "DDD"})
        self.assertEqual(ev.set_index("accession")["drop"].to_dict(),
                         {"N": "SKIP_NO_HEADER", "SEED": "SKIP_SEED_ONLY", "LATE": "SKIP_OUTSIDE_WINDOW",
                          "NOTK": "SKIP_NO_TICKER", "F1": "", "R1": "SKIP_REPEAT_90D", "NOP": "SKIP_NOT_OPERATING",
                          "MOV": "", "GAP": ""})
        self.assertEqual(ev.set_index("accession").loc["F1", "ticker"], "AAA")  # the first panel ticker in SEC order
        closes = {("AAA", "2020-07-06"): (10.0, 10.0), ("AAA", "2020-07-02"): (10.0, 10.0),
                  ("CCC", "2020-07-08"): (12.0, 12.0), ("CCC", "2020-07-07"): (10.0, 10.0), ("DDD", "2020-07-08"): (5.0, 5.0)}
        out = kt.classify(ev, lambda t, d: closes.get((t, d))).set_index("accession")
        self.assertEqual(out.loc["F1", "cls"], "FIRE")
        self.assertEqual(out.loc["F1", "position"], "DURING")
        self.assertEqual((out.loc["MOV", "cls"], out.loc["MOV", "MOVED_ALREADY"]), ("ABSTAIN", True))
        self.assertEqual(out.loc["GAP", "drop"], "SKIP_NO_SIGNAL_BAR")  # DURING without the previous close


class Statistic(unittest.TestCase):
    def test_bootstrap_clusters_iso_weeks_and_is_reproducible(self):
        days = ["2021-01-04", "2021-01-05", "2021-01-11", "2021-01-12", "2021-01-19"]
        w = kt.week_id(days)
        self.assertEqual(w.tolist(), [202101, 202101, 202102, 202102, 202103])
        v = [0.02, 0.04, -0.01, 0.01, 0.05]
        a, b = kt.Boot(w, 2000, 7).mean(v, w), kt.Boot(w, 2000, 7).mean(v, w)
        self.assertEqual(a, b)
        self.assertAlmostEqual(a["mean"], 0.022)
        self.assertEqual(a["weeks"], 3)
        self.assertGreater(a["t"], 0)
        self.assertAlmostEqual(a["p_one_sided"], kt.p_one_sided(a["t"]))
        with self.assertRaises(ValueError):
            kt.Boot(w[:2], 100, 7).mean(v, w)
        f = pd.DataFrame({"excess": v, "entry_date": days, "net_return": v, "control_mean": [0.0] * 5})
        d = kt.describe(f)
        self.assertEqual((d["n"], d["win_rate"]), (5, 0.8))
        lo, hi = d["win_rate_wilson95"]
        self.assertTrue(lo < 0.8 < hi)
        self.assertEqual(kt.describe(f.iloc[:1]), {"n": 1})

    def test_go_rule_and_verdict(self):
        self.assertEqual(kt.verdict(299, 0.5), "INCONCLUSIVE")
        self.assertEqual(kt.verdict(300, 0.0), "KILL")
        self.assertEqual(kt.verdict(300, -0.01), "KILL")
        self.assertEqual(kt.verdict(301, 0.0001), "NOT_KILLED")
        res = pd.DataFrame({"status": ["EXITED", "EXITED", "SKIP_OVERLAP", "EXITED"], "control_n": [3, 0, 3, 1],
                            "excess": [0.1, np.nan, np.nan, -0.2]})
        self.assertEqual(len(kt.scored(res)), 2)

    def test_constants_are_the_protocols(self):
        p = json.loads((BASE / "protocol.json").read_text())
        self.assertEqual((kt.REPEAT_DAYS, kt.OPERATING_DAYS, kt.DILUTION_SESSIONS, kt.MOVED_ALREADY, kt.MICROCAP_USD),
                         (p["repeat_days"], p["operating_days"], p["dilution_sessions"], p["moved_already"], p["microcap_usd"]))
        self.assertEqual((kt.SEED_ONLY_BEFORE, kt.ENTRY_FROM, kt.ENTRY_TO),
                         (p["filings"]["seed_only_before"], p["filings"]["entry_from"], p["filings"]["entry_to"]))
        self.assertEqual(kt.GO_MIN, p["statistic"]["go_min_scored"])
        self.assertEqual(kt.FORM, p["filings"]["form"])


class FakeClient:
    """get(url) and lines(url, keep) from routes, logging every call as the real client does."""

    def __init__(self, routes):
        self.routes, self.log = routes, []

    def get(self, url):
        st, body = self.routes.get(url, (404, b""))
        self.log.append([url, st, "x", len(body)])
        return st, body if st == 200 else b""

    def lines(self, url, keep):
        st, body = self.routes.get(url, (404, b""))
        self.log.append([url, st, "x", len(body)])
        return st, [x for x in io.StringIO(body.decode()) if keep(x)] if st == 200 else []


def subs_body(rows, files=(), prefix="0000000009-20"):
    cols = {c: [] for c in ("accessionNumber", "filingDate", "acceptanceDateTime", "form", "items", "primaryDocument")}
    for i, (form, day, items) in enumerate(rows):
        for c, v in zip(cols, (f"{prefix}-{i:06d}", day, f"{day}T12:00:00.000Z", form, items, "x.htm")):
            cols[c].append(v)
    return json.dumps({"filings": {"recent": cols, "files": list(files)}}).encode()


class Collect(unittest.TestCase):
    def test_collection_writes_one_row_per_original_with_its_inputs_and_logs_every_request(self):
        collect = _load("collect")
        q = json.loads((BASE / "protocol.json").read_text())["filings"]["quarters"]
        routes = {}
        filings = {"2020Q3": [("SC 13D", "Fund", 5000, "2020-07-06", "0000000001-20-000001", 1000, "20200706100000"),
                              ("SC 13D", "Fund", 5000, "2020-07-07", "0000000001-20-000002", 2000, "20200707100000"),
                              ("SC 13D/A", "Fund", 5000, "2020-07-07", "0000000001-20-000003", 1000, "20200707100000"),
                              ("SC 13D", "Fund", 5000, "2020-07-08", "0000000001-20-000004", 3000, None)]}
        for quarter in q:
            body = "Form Type   Company Name\n" + "".join(idx_line(f, n, c, d, a) for f, n, c, d, a, _, _ in filings.get(quarter, []))
            body += idx_line("SC 13G", "Other", 7, "2020-07-01", "0000000001-20-000099")
            body += idx_line("SC 13D/A", "Other", 7, "2020-07-01", "0000000001-20-000098")  # every quarter has 13D rows
            routes[kt.quarter_url(quarter)] = (200, body.encode())
            for f, n, c, d, a, subj, accepted in filings.get(quarter, []):
                if accepted:
                    routes[kt.header_url(c, a)] = (200, header(a, accepted, (subj, f"Co {subj}"), (c, n)))
        tmap = {"fields": ["cik", "name", "ticker", "exchange"], "data": [[1000, "Co", "AAA", "Nasdaq"], [1000, "Co", "AAA.B", "Nasdaq"]]}
        routes[collect.cr.TICKERS_URL] = (200, json.dumps(tmap).encode())
        routes[collect.cr.SUBMISSIONS_URL.format(cik=1000)] = (200, subs_body(
            [("10-Q", "2020-05-10", ""), ("8-K", "2020-06-25", "3.02")],
            files=[{"name": "CIK0000001000-submissions-001.json", "filingFrom": "2015-01-01", "filingTo": "2019-01-01"},
                   {"name": "CIK0000001000-submissions-000.json", "filingFrom": "2001-01-01", "filingTo": "2014-12-31"}]))
        chunk = json.loads(subs_body([("10-K", "2018-12-01", "")], prefix="0000000009-18"))["filings"]["recent"]
        routes["https://data.sec.gov/submissions/CIK0000001000-submissions-001.json"] = (200, json.dumps(chunk).encode())
        routes["https://data.sec.gov/api/xbrl/companyconcept/CIK0000001000/dei/EntityCommonStockSharesOutstanding.json"] = (
            200, json.dumps({"units": {"shares": [{"end": "2020-03-31", "val": 5e6, "filed": "2020-05-10"},
                                                  {"end": "2023-03-31", "val": 6e6, "filed": "2023-05-10"}]}}).encode())
        client = FakeClient(routes)
        with tempfile.TemporaryDirectory() as tmp:
            ev_path, log_path = Path(tmp) / "events.csv.gz", Path(tmp) / "COLLECT.json"
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(collect.collect(client, ev_path, log_path), 0)
            ev = pd.read_csv(io.BytesIO(gzip.decompress(ev_path.read_bytes())), dtype=str, keep_default_na=False)
            log = json.loads(log_path.read_text())
        self.assertEqual(ev["accession"].tolist(), ["0000000001-20-000001", "0000000001-20-000002", "0000000001-20-000004"])
        a = ev.iloc[0]
        self.assertEqual((a["subject_cik"], a["tickers"], a["filed_by"], a["drop_reason"]), ("1000", "AAA;AAA-B", "Fund", ""))
        self.assertEqual(a["accepted"], "2020-07-06T10:00:00-04:00")
        self.assertEqual(a["dilution"].split("|")[:2], ["8-K", "2020-06-25"])
        self.assertEqual(a["opforms"], "10-K|2018-12-01;10-Q|2020-05-10")  # the overlapping chunk only
        self.assertEqual(a["shares"], "2020-03-31|2020-05-10|5000000")  # facts filed after 2022 are not kept
        self.assertEqual(ev.iloc[1]["drop_reason"], "SKIP_NO_TICKER")
        self.assertEqual(ev.iloc[2]["drop_reason"], "SKIP_NO_HEADER")
        self.assertNotIn("CIK0000001000-submissions-000.json", " ".join(u for u, *_ in log["requests"]["log"]))
        self.assertEqual(log["funnel"]["filings_original_sc13d"], 3)
        self.assertEqual(log["funnel"]["operating_kept"], 1)
        self.assertEqual(log["header_failures"], 1)
        self.assertEqual(log["requests"]["n"], len(client.log))
        self.assertFalse(log["reads_prices"])
        self.assertNotIn("@", log["user_agent"])



class Runner(unittest.TestCase):
    def test_trial_file_reads_no_return_without_go_and_states_the_verdict_with_it(self):
        run = _load("run")
        res = {"verdict": "INCONCLUSIVE", "run_at": "2026-10-29T00:00:00Z", "go": {"scored_fire": 120}}
        t = run.trial(res)
        self.assertIsNone(t["one_sided_p"])
        self.assertTrue(t["outcome"].startswith("INCONCLUSIVE"))
        self.assertEqual((t["counted"], t["variants_searched"], t["id"]),
                         (True, 1, "CATALYST_REGISTER_v1_SEC13D_KILL_TEST_2020_2022"))
        pr = {"n": 400, "mean": -0.01, "se": 0.005, "t": -2.0, "lo95": -0.02, "hi95": 0.0, "median": -0.02,
              "win_rate": 0.45, "p_one_sided": 0.977}
        t = run.trial({"verdict": "KILL", "run_at": "2026-10-29T00:00:00Z", "primary": pr})
        self.assertEqual(t["one_sided_p"], 0.977)
        self.assertTrue(t["outcome"].startswith("KILL"))
        ev = pd.DataFrame({"drop": ["", "", "SKIP_NO_HEADER"], "cls": ["FIRE", "ABSTAIN", ""], "position": ["AFTER", "DURING", None],
                           "DILUTION_RECENT": [False, True, False], "MOVED_ALREADY": [False] * 3, "MICROCAP": [False] * 3,
                           "MV_UNKNOWN": [False] * 3})
        c = run.counts(ev)
        self.assertEqual((c["FIRE"], c["ABSTAIN"], c["drops"]["SKIP_NO_HEADER"], c["rules"]["DILUTION_RECENT"]), (1, 1, 1, 1))


if __name__ == "__main__":
    unittest.main()
