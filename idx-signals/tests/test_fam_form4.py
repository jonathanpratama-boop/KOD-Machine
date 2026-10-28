"""Catalyst Register family FORM4 (idxsig.fam_form4). Synthetic data only, no network. Each test names the failure it
guards against."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import warnings
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pandas as pd

from idxsig import catalysts as cr
from idxsig import fam_form4 as f4
from idxsig import paper
from idxsig import speculation as sp
from tests.test_catalysts import FakeClient, build, features, json_lines, scan_record, set_closes, subs, us_market

D1, D2 = "2026-10-29", "2026-10-30"  # the first two index dates of the window (Thursday, Friday)
NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)  # 08:00 New York: entry 2026-10-30, signal 2026-10-29
NOW2 = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)  # 07:00 New York (EST): entry 2026-11-02, signal 2026-10-30


def owner(cik="9001", name="Jane Doe", director="1", officer="0", title="", tenpct="0", other="0") -> str:
    return (f"<reportingOwner><reportingOwnerId><rptOwnerCik>{cik}</rptOwnerCik><rptOwnerName>{name}</rptOwnerName>"
            f"</reportingOwnerId><reportingOwnerRelationship><isDirector>{director}</isDirector><isOfficer>{officer}</isOfficer>"
            f"<officerTitle>{title}</officerTitle><isTenPercentOwner>{tenpct}</isTenPercentOwner><isOther>{other}</isOther>"
            "</reportingOwnerRelationship></reportingOwner>")


def line(shares=1000, price=60.0, code="P", ad="A", title="Common Stock", day="2026-10-27") -> str:
    return (f"<nonDerivativeTransaction><securityTitle><value>{title}</value></securityTitle><transactionDate><value>{day}"
            f"</value></transactionDate><transactionCoding><transactionFormType>4</transactionFormType><transactionCode>{code}"
            f"</transactionCode><equitySwapInvolved>0</equitySwapInvolved></transactionCoding><transactionAmounts>"
            f"<transactionShares><value>{shares}</value></transactionShares><transactionPricePerShare><value>{price}</value>"
            f"</transactionPricePerShare><transactionAcquiredDisposedCode><value>{ad}</value></transactionAcquiredDisposedCode>"
            "</transactionAmounts></nonDerivativeTransaction>")


def filing(issuer: int, owners=None, lines=None, aff=None, raw: str | None = None) -> bytes:
    """A filing's full text with its ownershipDocument between <XML> and </XML>."""
    doc = raw if raw is not None else (
        '<?xml version="1.0"?><ownershipDocument><schemaVersion>X0508</schemaVersion><documentType>4</documentType>'
        + (f"<aff10b5One>{aff}</aff10b5One>" if aff is not None else "")
        + f"<issuer><issuerCik>{issuer:010d}</issuerCik><issuerName>Co {issuer}</issuerName>"
        f"<issuerTradingSymbol>S{issuer}</issuerTradingSymbol></issuer>"
        + "".join(owners or [owner()]) + "<nonDerivativeTable>" + "".join(lines or [line()]) + "</nonDerivativeTable>"
        "</ownershipDocument>")
    return f"<SEC-DOCUMENT>\n<DOCUMENT>\n<TYPE>4\n<TEXT>\n<XML>\n{doc}\n</XML>\n</TEXT>\n</DOCUMENT>\n</SEC-DOCUMENT>\n".encode()


FOOTNOTED = ('<?xml version="1.0"?><ownershipDocument><documentType>4</documentType><aff10b5One>false</aff10b5One>'
             "<issuer><issuerCik>0000001003</issuerCik><issuerName>Gamma Corp</issuerName><issuerTradingSymbol>T03</issuerTradingSymbol></issuer>"
             + owner(cik="9003", name="Ann Boss", director="false", officer="TRUE", title="President and CEO")
             + "<nonDerivativeTable><nonDerivativeTransaction><securityTitle><value>Class A Common Stock</value>"
             "<footnoteId id=\"F1\"/></securityTitle><transactionDate><value>2026-10-26</value></transactionDate>"
             "<transactionCoding><transactionFormType>4</transactionFormType><transactionCode>P</transactionCode>"
             "<footnoteId id=\"F2\"/></transactionCoding><transactionAmounts><transactionShares><value>2,000</value>"
             "</transactionShares><transactionPricePerShare><value>30.25<footnoteId id=\"F3\"/></value></transactionPricePerShare>"
             "<transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode></transactionAmounts>"
             "</nonDerivativeTransaction></nonDerivativeTable><footnotes><footnote id=\"F3\">A weighted average price.</footnote>"
             "</footnotes></ownershipDocument>")


def acc(k: int) -> str:
    return f"0000000002-26-{k:06d}"


def index_body(day: str, rows) -> bytes:
    """rows: (form, company, cik, accession); the fixed-width daily form index with its header."""
    head = ["Description:           Daily Index of EDGAR Dissemination Feed by Form Type", "Last Data Received:    Oct 29, 2026",
            "Comments:              webmaster@sec.gov", " ", " ",
            "Form Type   Company Name                                                  CIK         Date Filed  File Name", "-" * 120]
    body = [f"{form:<12}{name:<62}{cik:<12}{day.replace('-', ''):<12}edgar/data/{cik}/{a}.txt" for form, name, cik, a in rows]
    return ("\n".join(head + body) + "\n").encode("latin-1")


def d1_filings() -> dict[int, tuple[int, bytes | None]]:
    """accession number -> (issuer CIK, full text); None is a filing the archive does not serve."""
    return {
        1: (1000, filing(1000)),  # a director buys 1,000 x 60: SEALED
        2: (1001, filing(1001, [owner(cik="9002", officer="1", director="0", title="CFO")], [line(500, 60.0), line(500, 60.0)])),
        3: (1001, filing(1001, [owner(cik="9012")], [line(1000, 100.0)])),  # same issuer, same date: summed into 2
        4: (1002, filing(1002, lines=[line(code="S")])),
        5: (1002, filing(1002, lines=[line(ad="D")])),
        6: (1002, filing(1002, lines=[line(title="Series A Preferred Stock")])),
        7: (1002, filing(1002, [owner(director="0", tenpct="1")])),
        8: (1002, filing(1002, aff="1")),
        9: (1002, filing(1002, lines=[line(49_999, 1.0)])),
        10: (9999, filing(9999)),  # no ticker
        11: (1059, filing(1059)),  # T59: not eligible in the scan
        12: (1005, filing(1005)),  # a fund: not an operating issuer
        13: (1002, filing(1002, raw="<ownershipDocument><issuer>")),
        14: (1002, None),
        16: (1003, filing(1003, raw=FOOTNOTED)),
    }


def world(index: dict[str, list] | None = None, docs: dict[int, tuple[int, bytes | None]] | None = None):
    docs = d1_filings() if docs is None else docs
    if index is None:
        rows = [("4", f"Co {cik} Holdings Inc", cik, acc(k)) for k, (cik, _) in docs.items()]
        rows.insert(1, ("4", "Jane Doe", 9001, acc(1)))  # the same filing listed under its reporting owner too
        rows.append(("4/A", "Amended Co Inc", 1004, acc(15)))
        rows.append(("10-Q", "Some Co", 1004, acc(17)))
        index = {D1: rows}
    tmap = {"fields": ["cik", "name", "ticker", "exchange"], "data": [[1000 + i, f"Co {i}", f"T{i:02d}", "Nasdaq"] for i in range(60)]}
    routes = {cr.TICKERS_URL: (200, json.dumps(tmap).encode())}
    for day, rows in index.items():
        routes[f4.index_url(day)] = (200, index_body(day, rows))
    for k, (cik, body) in docs.items():
        if body is not None:
            routes[f4.ARCHIVE_URL.format(path=f"edgar/data/{cik}/{acc(k)}.txt")] = (200, body)
    for i in range(60):
        rows = [("N-CSR", "2026-08-10", ""), ("10-Q", "2026-08-10", "")] if i == 5 else [("10-Q", "2026-08-10", "")]
        routes[cr.SUBMISSIONS_URL.format(cik=1000 + i)] = (200, subs(rows))
    return routes


def run(routes, now=NOW, records=None, clock=None, ledger=None):
    ledger = [scan_record(session=D1), scan_record(session=D2)] if ledger is None else ledger
    with mock.patch.object(sp, "scan_features", side_effect=lambda scan: features(session=scan["session"])):
        return f4.batch(now, FakeClient(routes), ledger=ledger, records=records or [], clock=clock or (lambda: now))


class Parsing(unittest.TestCase):
    def test_index_lines_are_read_from_the_right_so_names_with_spaces_survive(self):
        """Guards against: a company name with spaces shifting the CIK or file name, a header line taken for a filing,
        or a filing listed twice (issuer and owner rows) read twice."""
        body = index_body(D1, [("4", "SOME CO  INC /DE/", 1234567, acc(1)), ("4", "Doe John A", 7654321, acc(1)),
                               ("4/A", "OTHER CO", 1, acc(2)), ("SC 13D", "X Y Z", 2, acc(3))])
        rows = f4.parse_index(body)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0], {"form": "4", "company": "SOME CO  INC /DE/", "cik": 1234567, "date_filed": D1,
                                   "file_name": f"edgar/data/1234567/{acc(1)}.txt", "accession": acc(1)})
        self.assertEqual([r["form"] for r in rows], ["4", "4", "4/A", "SC"])  # the form type is the first token
        self.assertEqual([r["accession"] for r in f4.form4_filings(rows)], [acc(1)])
        self.assertEqual(f4.parse_index(b"4  ACME  CORP  12  2026-10-29  edgar/data/12/x.txt\n")[0]["date_filed"], D1)
        self.assertEqual(f4.index_url("2026-10-27"), "https://www.sec.gov/Archives/edgar/daily-index/2026/QTR4/form.20261027.idx")
        self.assertEqual(f4.index_url("2027-03-31"), "https://www.sec.gov/Archives/edgar/daily-index/2027/QTR1/form.20270331.idx")

    def test_xml_values_with_footnotes_and_every_boolean_spelling(self):
        """Guards against: a footnote reference glued to a price, 'true'/'TRUE' read as false, or the issuer CIK lost."""
        doc = f4.parse_form4(f4.form4_xml(filing(1003, raw=FOOTNOTED)))
        self.assertEqual((doc["issuer_cik"], doc["issuer_name"], doc["symbol"], doc["aff10b5one"]), (1003, "Gamma Corp", "T03", False))
        self.assertEqual(doc["owners"][0] | {}, {"cik": "9003", "name": "Ann Boss", "director": False, "officer": True,
                                                 "tenpct": False, "other": False, "title": "President and CEO"})
        self.assertEqual(doc["lines"], [{"title": "Class A Common Stock", "date": "2026-10-26", "code": "P", "shares": 2000.0,
                                         "price": 30.25, "ad": "A"}])
        why, summary = f4.purchase_test(doc)
        self.assertIsNone(why)
        self.assertEqual((summary["total_value"], summary["top_exec"]), (60_500.0, True))
        self.assertTrue(f4.parse_form4(f4.form4_xml(filing(1, aff="true")))["aff10b5one"])
        self.assertTrue(f4.parse_form4(f4.form4_xml(filing(1, aff="1")))["aff10b5one"])
        self.assertFalse(f4.parse_form4(f4.form4_xml(filing(1, aff="0")))["aff10b5one"])
        self.assertFalse(f4.parse_form4(f4.form4_xml(filing(1)))["aff10b5one"])  # older schema: no element
        ns = filing(1, raw='<ownershipDocument xmlns="urn:x"><issuer><issuerCik>42</issuerCik></issuer></ownershipDocument>')
        self.assertEqual(f4.parse_form4(f4.form4_xml(ns))["issuer_cik"], 42)
        for bad in (b"<html>no xml</html>", filing(1, raw="<ownershipDocument><issuer>"),
                    filing(1, raw="<ownershipDocument><issuer></issuer></ownershipDocument>")):
            with self.assertRaises(ValueError):
                f4.parse_form4(f4.form4_xml(bad))

    def test_every_exclusion_of_test_26(self):
        """Guards against: a sale, a disposal, a preferred or derivative title, a 10% holder alone, a 10b5-1 plan trade or a
        filing just under USD 50,000 counted as an insider purchase; or several small lines not summed."""
        def why(body):
            return f4.purchase_test(f4.parse_form4(f4.form4_xml(body)))[0]
        docs = d1_filings()
        self.assertEqual([why(docs[k][1]) for k in (4, 5, 6, 7, 8, 9)],
                         ["NO_PURCHASE_LINE", "NO_PURCHASE_LINE", "NO_PURCHASE_LINE", "NO_OFFICER_OR_DIRECTOR", "PLAN_10B5_1",
                          "BELOW_USD_50000"])
        self.assertEqual(why(filing(1, [owner(director="0", other="1")])), "NO_OFFICER_OR_DIRECTOR")
        self.assertEqual(why(filing(1, lines=[line(title="Warrants to buy Common Stock")])), "NO_PURCHASE_LINE")
        self.assertEqual(why(filing(1, lines=[line(price=0)])), "NO_PURCHASE_LINE")
        self.assertIsNone(why(filing(1, lines=[line(50_000, 1.0)])))  # exactly USD 50,000 qualifies
        self.assertIsNone(why(filing(1, [owner(director="0", officer="1", title="VP"), owner(cik="2", director="0", tenpct="1")])))
        self.assertEqual(why(filing(1, lines=[line(500, 60.0)])), "BELOW_USD_50000")  # one 30k line alone
        self.assertIsNone(why(docs[2][1]))  # two 30k lines: 60k
        mixed = filing(1, lines=[line(500, 60.0), line(5000, 60.0, code="S"), line(400, 60.0)])
        self.assertEqual(f4.purchase_test(f4.parse_form4(f4.form4_xml(mixed)))[1]["total_value"], 54_000.0)

    def test_the_rules_are_test_26s_and_the_protocols(self):
        """Guards against: a copy of the purchase rules drifting from research/US_INSIDER_BUY/ib_lib.py, or a threshold
        changed in code but not in the frozen protocol."""
        s = importlib.util.spec_from_file_location("ib_check", cr.PKG_ROOT / "research" / "US_INSIDER_BUY" / "ib_lib.py")
        ib = importlib.util.module_from_spec(s)
        s.loader.exec_module(ib)
        self.assertEqual((f4.TOP.pattern, f4.TOP.flags), (ib._TOP.pattern, ib._TOP.flags))
        for t in ("Common Stock", "Class A Common Stock", "Ordinary Shares", "Series B Preferred", "Stock Option", "ADS"):
            self.assertEqual(f4.is_common(t), ib.is_common(t), t)
        text = json.dumps(cr.family_protocol("FORM4")[0])
        for needle in ("USD 50,000", "90 calendar days", "at most 15 checked", "'4/A' is not used", "aff10b5One"):
            self.assertIn(needle, text)
        self.assertEqual((f4.MIN_VALUE, f4.REPEAT_DAYS, cr.TWIN_CHECKS, cr.TWINS), (50_000.0, 90, 15, 5))


class Batch(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore")

    def test_every_purchase_event_gets_a_status_and_the_rest_are_counted(self):
        """Guards against: an event dropped without a record, two filings of one issuer on one date sealed twice, an
        amendment read, a non-purchase listed one by one, or a set missing what resolve_set and verify need."""
        batch, sets = run(world())
        st = {e["accession"][-2:]: e["status"] for e in batch["events"]}
        self.assertEqual(st, {"01": "SEALED", "02": "SEALED", "10": "SKIP_NO_TICKER", "11": "SKIP_NOT_IN_UNIVERSE",
                              "12": "SKIP_NOT_OPERATING", "16": "SEALED"})
        self.assertEqual(batch["counts"], {"SKIP_NOT_PURCHASE": 6, "SKIP_PARSE_FAILED": 1, "SKIP_UNREADABLE": 1})
        self.assertEqual(batch["not_purchase_reasons"], {"NO_PURCHASE_LINE": 3, "NO_OFFICER_OR_DIRECTOR": 1, "PLAN_10B5_1": 1,
                                                         "BELOW_USD_50000": 1})
        self.assertEqual(batch["unreadable"], [f"{acc(14)}|HTTP 404"])
        self.assertTrue(batch["coverage_gap"])
        self.assertEqual(batch["filings_xml"]["n"], 13)  # 15 filings, one unreadable, one unparsable
        (d,) = batch["index_dates"]
        self.assertEqual((d["date"], d["status"], d["form4_lines"], d["form4_filings"]), (D1, "READ", 16, 15))
        self.assertEqual(len(d["sha256"]), 64)
        by = {s["ticker"]: s for s in sets}
        t01 = by["T01"]
        self.assertEqual((t01["event"]["accessions"], t01["coverage"]["inputs"]["total_value"], t01["coverage"]["inputs"]["n_owners"]),
                         ([acc(2), acc(3)], 160_000.0, 2))
        self.assertTrue(t01["coverage"]["inputs"]["top_exec"])  # the CFO
        self.assertEqual(by["T03"]["coverage"]["inputs"], {"total_value": 60_500.0, "n_owners": 1, "top_exec": True, "lag_days": 3})
        self.assertEqual(by["T00"]["coverage"]["inputs"]["top_exec"], False)
        for s in sets:
            self.assertEqual(s["set_id"], f"CAT-FORM4-{s['event_id']}")
            self.assertEqual((s["family"], s["market"], s["direction"], s["plan"]), ("FORM4", "US", 1, "H20"))
            self.assertEqual((s["signal_session"], s["entry"]["session"], s["entry"]["basis"]), (D1, D2, "open"))
            self.assertEqual((s["entry_cutoff"], s["sealed_at"]), ("2026-10-30T13:15:00Z", "2026-10-30T12:00:00Z"))
            self.assertEqual(s["event"]["public_date"], s["event"]["filing_date"])
            self.assertEqual((s["coverage"]["class"], s["coverage"]["rules"], s["coverage"]["reasons"]), ("FIRE", {}, []))
            self.assertEqual(s["windows"], {"H20": {"kind": "plan", "entry_window": 1, "holding_sessions": 20}})
            self.assertEqual([c["id"] for c in s["cone"]], ["BEATS_TWINS_20", "GAIN0_20", "FADE10_20", "RUN30_20"])
            self.assertEqual([c["prior"] for c in s["cone"]], [0.5] * 4)
            self.assertEqual(s["protocol"], {"id": "KOD-CATALYST-FAMILY-FORM4-v1", "sha256": cr.family_protocol("FORM4")[1]})
            self.assertEqual(s["twins_seed"], cr.set_seed(s["set_id"]))
            names = {t["ticker"] for t in s["twins"]}
            self.assertEqual(len(names), 5)
            self.assertFalse(names & {"T00", "T01", "T03", "T05", "T58"})  # events, the fund, the scan's candidate
            self.assertTrue(all("close" in t for t in s["twins"]))
            self.assertIn("FORM4 ", cr.card(s))
        self.assertEqual(run(world())[1][0]["twins"], sets[0]["twins"])  # seeded: the same twins again

    def test_an_issuer_sealed_within_90_days_is_a_repeat_in_a_later_batch(self):
        """Guards against: a second purchase of the same issuer sealed weeks after the first (test 26 chains per issuer),
        or an index date read twice."""
        b1, s1 = run(world())
        docs2 = {21: (1000, filing(1000, lines=[line(2000, 50.0)])), 22: (1004, filing(1004))}
        routes = world()
        routes.update(world(index={D2: [("4", f"Co {c}", c, acc(k)) for k, (c, _) in docs2.items()]}, docs=docs2))
        b2, s2 = run(routes, now=NOW2, records=[b1, *s1])
        self.assertEqual([d["date"] for d in b2["index_dates"]], [D2])
        self.assertEqual({e["accession"][-2:]: e["status"] for e in b2["events"]}, {"21": "SKIP_REPEAT_90D", "22": "SEALED"})
        self.assertEqual([s["ticker"] for s in s2], ["T04"])
        self.assertFalse(b2["coverage_gap"])

    def test_an_unpublished_index_is_pending_and_its_filings_are_late_when_read(self):
        """Guards against: a date whose index was not yet published skipped for good, or a filing read a session too late
        sealed as if the plan could still enter after it."""
        routes = world()
        early = {k: v for k, v in routes.items() if k != f4.index_url(D1)}
        b1, s1 = run(early)
        self.assertEqual((b1["index_dates"][0]["status"], b1["index_dates"][0]["http_status"], b1["pending_dates"]), ("PENDING", 404, [D1]))
        self.assertEqual((b1["events"], s1, b1["counts"]), ([], [], {}))
        docs2 = {22: (1004, filing(1004))}
        routes.update(world(index={D2: [("4", "Co 1004", 1004, acc(22))]}, docs=docs2))
        b2, s2 = run(routes, now=NOW2, records=[b1])
        self.assertEqual([(d["date"], d["status"]) for d in b2["index_dates"]], [(D1, "READ"), (D2, "READ")])
        st = {e["accession"][-2:]: e["status"] for e in b2["events"]}
        self.assertEqual((st["01"], st["02"], st["16"], st["22"]), ("SKIP_LATE", "SKIP_LATE", "SKIP_LATE", "SEALED"))
        self.assertEqual([s["signal_session"] for s in s2], [D2])

    def test_refuses_after_the_cutoff_and_without_the_signal_scan(self):
        """Guards against: a set sealed after its entry cutoff, or a set without the scan its twins come from."""
        with self.assertRaises(RuntimeError):
            run(world(), clock=lambda: datetime(2026, 10, 30, 13, 15, tzinfo=timezone.utc))
        with self.assertRaises(RuntimeError):
            run(world(), ledger=[scan_record(session="2026-10-28")])
        b, s = run(world(index={D1: []}, docs={}), clock=lambda: datetime(2026, 10, 30, 13, 20, tzinfo=timezone.utc))
        self.assertEqual((b["events"], s), ([], []))  # an empty batch is still recorded


class Ledger(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore")

    def test_verify_accepts_the_batch_then_its_sets(self):
        """Guards against: FORM4 records that the register's own verifier rejects (protocol hash, scan binding, listing,
        cutoff)."""
        batch, sets = run(world())
        scans = [scan_record(session=D1)]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalysts.jsonl"
            paper.append([batch, *sets], path=path)
            with mock.patch.object(cr, "CAT_LEDGER", path), \
                    mock.patch.object(paper, "ledger_lines", side_effect=lambda p=None: scans if p is None else json_lines(p)), \
                    mock.patch.object(sp, "spec_lines", return_value=[]):
                self.assertEqual(cr.verify(), [])
                stats = cr.statistics()
        fam = stats["families"]["FORM4"]
        self.assertEqual((fam["n_sets"], fam["events_seen"]["SEALED"], fam["events_seen"]["SKIP_NOT_PURCHASE"]), (3, 3, 6))

    def test_resolve_set_grades_beats_twins_on_a_synthetic_market(self):
        """Guards against: a FORM4 set that the resolver cannot pair with its twins or grade."""
        _, sets = run(world())
        m, a = us_market(n_sessions=40)
        d = 10
        set_closes(a, 0, d + 1, [26 + k for k in range(25)], opens=[25] + [26 + k for k in range(1, 25)])
        m = build(m.tickers, m.dates, a)
        s = {**sets[0], "ticker": "U00", "signal_session": str(m.dates[d]), "signal": {"close": 25.0},
             "twins": [{"ticker": f"U0{i}", "close": 25.0} for i in range(1, 6)]}
        r = cr.resolve_set(s, "H20", m, pd.DataFrame())
        self.assertEqual((r["status"], r["family"], r["coverage"]), ("RESOLVED", "FORM4", "FIRE"))
        cone = {c["id"]: c["outcome"] for c in r["cone"]}
        self.assertEqual(cone, {"BEATS_TWINS_20": True, "GAIN0_20": True, "FADE10_20": False, "RUN30_20": True})
        self.assertEqual(r["paired"]["twins_traded"], 5)


if __name__ == "__main__":
    unittest.main()
