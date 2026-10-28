"""Catalyst Register v1 (idxsig.catalysts). Synthetic data only, no network. Each test names the failure it guards
against."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import warnings
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist
from unittest import mock

import numpy as np
import pandas as pd

from idxsig import catalysts as cr
from idxsig import paper
from idxsig import speculation as sp
from test_speculation import build, set_closes, us_market

SIGNAL = "2026-10-28"
NOW = datetime(2026, 10, 28, 22, 50, tzinfo=timezone.utc)  # 18:50 New York (EDT): entry 2026-10-29


class FakeClient:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get(self, url):
        self.calls.append(url)
        return self.routes.get(url, (404, b""))


def feed(entries) -> bytes:
    """entries: (form, name, cik, role, accepted, accession)"""
    parts = ['<?xml version="1.0" encoding="ISO-8859-1" ?><feed xmlns="http://www.w3.org/2005/Atom">']
    for form, name, cik, role, accepted, acc in entries:
        parts.append(f'<entry><title>{form} - {name} ({cik:010d}) ({role})</title>'
                     f'<link rel="alternate" type="text/html" href="https://www.sec.gov/Archives/edgar/data/{cik}/'
                     f'{acc.replace("-", "")}/{acc}-index.htm"/><updated>{accepted}</updated>'
                     f'<category scheme="https://www.sec.gov/" label="form type" term="{form}"/></entry>')
    return ("".join(parts) + "</feed>").encode()


def subs(rows) -> bytes:
    """rows: (form, filingDate, items)"""
    cols = {c: [] for c in ("accessionNumber", "filingDate", "acceptanceDateTime", "form", "items", "primaryDocument")}
    for i, (form, day, items) in enumerate(rows):
        cols["accessionNumber"].append(f"0000000000-26-{i:06d}")
        cols["filingDate"].append(day)
        cols["acceptanceDateTime"].append(f"{day}T12:00:00.000Z")
        cols["form"].append(form)
        cols["items"].append(items)
        cols["primaryDocument"].append("x.htm")
    return json.dumps({"filings": {"recent": cols}}).encode()


def features(n=60, session=SIGNAL, selected="G2_RET30") -> pd.DataFrame:
    rng = np.random.default_rng(5)
    rows = []
    for i in range(n):
        rows.append({"ticker": f"T{i:02d}", "session": session, "fresh": True, "eligible": i != 59, "close": 12.0,
                     "previous": 12.0, "open": 12.0, "adv20_value": float(rng.uniform(1e6, 2e6)), "ret20": 0.0, "dd60": -0.1,
                     "volr": 1.0, "ret1": 0.0, "ret5": 0.0, "cpos": 0.5, "high": 12.0, "low": 12.0, "volume": 1e5,
                     selected: i == 58})
    df = pd.DataFrame(rows)
    df.loc[df["ticker"] == "T00", "previous"] = 12.0 / 1.05
    df.loc[df["ticker"] == "T04", "previous"] = 12.0 / 1.20
    return df


def scan_record(market="US", session=SIGNAL) -> dict:
    scan = {"type": "SCAN", "market": market, "scan_id": f"SCAN-{market}-{session}-G2_RET30", "session": session,
            "detector": {"selected": "G2_RET30"}, "candidates_ranked": ["T58"], "flags": {"G2_RET30": ["T58"]},
            "features_file": "paper/scans/test/features.csv", "features_sha256": "f" * 64}
    scan["record_hash"] = hashlib.sha256(json.dumps(scan, sort_keys=True).encode()).hexdigest()
    return scan


def sec_world():
    entries = [
        ("SCHEDULE 13D", "Alpha Inc", 1000, "Subject", "2026-10-28T10:00:00-04:00", "0000000001-26-000001"),
        ("SCHEDULE 13D", "Fund A LP", 5000, "Filed by", "2026-10-28T10:00:00-04:00", "0000000001-26-000001"),
        ("SCHEDULE 13D", "Beta Inc", 1001, "Subject", "2026-10-28T17:00:00-04:00", "0000000001-26-000002"),
        ("SCHEDULE 13D", "Private Co", 9999, "Subject", "2026-10-28T11:00:00-04:00", "0000000001-26-000003"),
        ("SCHEDULE 13D", "Stale Inc", 1059, "Subject", "2026-10-28T11:30:00-04:00", "0000000001-26-000004"),
        ("SCHEDULE 13D", "Late Inc", 1002, "Subject", "2026-10-27T15:00:00-04:00", "0000000001-26-000005"),
        ("SCHEDULE 13D/A", "Amended Inc", 1005, "Subject", "2026-10-28T12:00:00-04:00", "0000000001-26-000006"),
        ("SCHEDULE 13D", "Again Inc", 1003, "Subject", "2026-10-28T12:30:00-04:00", "0000000001-26-000007"),
        ("SCHEDULE 13D", "Moved Inc", 1004, "Subject", "2026-10-28T13:00:00-04:00", "0000000001-26-000008"),
        ("SCHEDULE 13D", "Old Inc", 1006, "Subject", "2026-10-27T23:00:00-04:00", "0000000001-26-000009"),
    ]
    tmap = {"fields": ["cik", "name", "ticker", "exchange"], "data": [[1000 + i, f"Co {i}", f"T{i:02d}", "Nasdaq"] for i in range(60)]}
    routes = {cr.FEED_URL.format(start=0): (200, feed(entries)), cr.FEED_URL.format(start=100): (200, feed([])),
              cr.TICKERS_URL: (200, json.dumps(tmap).encode())}
    for i in range(60):
        rows = [("10-Q", "2026-08-10", "")] if i % 2 == 0 or i < 10 else (
            [("N-CSR", "2026-08-10", ""), ("10-Q", "1995-06-12", "")] if i % 4 == 1 else [("10-K", "2024-01-10", "")])
        if i == 1:
            rows.append(("8-K", "2026-10-20", "3.02,9.01"))
        if i == 3:
            rows.append(("SCHEDULE 13D", "2026-09-15", ""))
        if i == 12:
            rows.append(("SCHEDULE 13D", "2026-10-01", ""))
        routes[cr.SUBMISSIONS_URL.format(cik=1000 + i)] = (200, subs(rows))
    routes[cr.PRIMARY_DOC_URL.format(cik=1000, acc="000000000126000001")] = (
        200, b"<item4><transactionPurpose>We may talk to the Board about a merger.</transactionPurpose></item4>")
    shares = {1000: [{"end": "2026-06-30", "val": 1.0e7, "filed": "2026-08-10"}],
              1001: [{"end": "2026-06-30", "val": 1.0e7, "filed": "2026-08-10"}]}
    return routes, shares


class Parsing(unittest.TestCase):
    def test_originals_keep_subject_and_filers_and_drop_amendments(self):
        """Guards against: an amendment counted as an event, or the filer taken for the subject."""
        routes, _ = sec_world()
        ev = cr.originals(cr.parse_feed(routes[cr.FEED_URL.format(start=0)][1]))
        accs = [e["accession"] for e in ev]
        self.assertNotIn("0000000001-26-000006", accs)
        a = next(e for e in ev if e["accession"] == "0000000001-26-000001")
        self.assertEqual(a["subject"], {"cik": 1000, "name": "Alpha Inc"})
        self.assertEqual(a["filed_by"], ["Fund A LP"])
        self.assertEqual(accs, sorted(accs, key=lambda x: next(e["accepted"] for e in ev if e["accession"] == x)) or accs)

    def test_entry_session_and_acceptance_position_follow_new_york_time(self):
        """Guards against: a UTC-date entry, a weekend entry, or an acceptance placed on the wrong side of a close."""
        self.assertEqual(cr.us_entry_session(datetime(2026, 10, 28, 13, 0, tzinfo=timezone.utc)), "2026-10-28")  # 09:00 EDT
        self.assertEqual(cr.us_entry_session(datetime(2026, 10, 28, 13, 20, tzinfo=timezone.utc)), "2026-10-29")  # 09:20 EDT
        self.assertEqual(cr.us_entry_session(datetime(2026, 10, 30, 22, 0, tzinfo=timezone.utc)), "2026-11-02")  # Friday evening
        self.assertEqual(cr.us_cutoff("2026-11-02"), datetime(2026, 11, 2, 14, 15, tzinfo=timezone.utc))  # EST after 1 November
        self.assertEqual(cr.us_entry_session(datetime(2026, 11, 25, 23, 0, tzinfo=timezone.utc)), "2026-11-27")  # Thanksgiving
        self.assertEqual(cr.us_prev_session("2026-11-27"), "2026-11-25")
        self.assertEqual(cr.acceptance_position(datetime.fromisoformat("2026-11-26T12:00:00-05:00"), "2026-11-25"), "AFTER")
        at = datetime.fromisoformat
        self.assertEqual(cr.acceptance_position(at("2026-10-27T16:00:00-04:00"), SIGNAL), "LATE")
        self.assertEqual(cr.acceptance_position(at("2026-10-27T16:00:01-04:00"), SIGNAL), "DURING")
        self.assertEqual(cr.acceptance_position(at("2026-10-28T16:00:00-04:00"), SIGNAL), "DURING")
        self.assertEqual(cr.acceptance_position(at("2026-10-28T16:30:00-04:00"), SIGNAL), "AFTER")

    def test_rule_inputs(self):
        """Guards against: a dilution filing outside the 20 sessions, a same-day 13D counted as a repeat, a share count
        filed after sealing, or a missing market value that lets a set fire."""
        f = cr.e9.parse_submissions(subs([("8-K", "2026-10-01", "3.02"), ("8-K", "2026-09-30", "3.02"),
                                          ("424B5", "2026-10-28", ""), ("SCHEDULE 13D", "2026-10-28", ""),
                                          ("SC 13D", "2026-08-01", ""), ("10-K", "2026-03-01", "")]), [])
        dil = cr.dilution_filings(f, SIGNAL, SIGNAL)
        self.assertEqual([x.split("|")[0] + x.split("|")[2] for x in dil], ["8-K2026-10-01", "424B52026-10-28"])
        self.assertEqual(len(cr.earlier_13d(f, "nope", SIGNAL)), 1)  # the SC 13D of 1 August, not the same-day one
        self.assertTrue(cr.is_operating(f, SIGNAL))
        self.assertFalse(cr.is_operating(f, "2028-01-01"))  # the last 10-K is older than 550 days
        fund = cr.e9.parse_submissions(subs([("10-Q", "2026-05-01", ""), ("N-CSR", "2026-09-01", "")]), [])
        self.assertFalse(cr.is_operating(fund, SIGNAL))
        pts = [{"end": "2026-06-30", "val": 2e6, "filed": "2026-08-01"}, {"end": "2026-09-30", "val": 9e9, "filed": "2026-11-01"}]
        mv, p = cr.market_value(pts, 10.0, SIGNAL)
        self.assertEqual((mv, p["end"]), (2e7, "2026-06-30"))
        self.assertEqual(cr.coverage([], 1.0, None)["reasons"], ["MV_UNKNOWN"])
        self.assertEqual(cr.coverage([], 1.0, 6e7)["class"], "FIRE")
        self.assertEqual(cr.coverage([], 1.15, 6e7)["reasons"], ["MOVED_ALREADY"])


class SecBatch(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore")

    def run_batch(self, clock=None, records=None, ledger=None, now=NOW, session=SIGNAL):
        routes, shares = sec_world()
        client = FakeClient(routes)
        with mock.patch.object(sp, "scan_features", return_value=features(session=session)), \
                mock.patch.object(cr, "share_points", side_effect=lambda c, cik: shares.get(cik, [])):
            return cr.sec13d_batch(now, client, ledger=[scan_record(session=session)] if ledger is None else ledger,
                                   records=records or [], clock=clock or (lambda: now)), client

    def test_a_filing_the_register_saw_too_late_is_skipped_not_sealed(self):
        """Guards against: a filing whose reaction already ran for a full session sealed as if it were prospective."""
        later = datetime(2026, 10, 29, 22, 50, tzinfo=timezone.utc)
        (batch, sets), _ = self.run_batch(now=later, session="2026-10-29")
        st = {e["accession"][-1]: e["status"] for e in batch["events"]}
        self.assertEqual((st["1"], st["2"], st["8"]), ("SKIP_LATE", "SEALED", "SKIP_LATE"))
        self.assertEqual([s["event"]["position"] for s in sets], ["DURING"])

    def test_every_original_gets_a_status_and_the_rules_decide_fire_or_abstain(self):
        """Guards against: a filing dropped without a record, a set without its rule inputs, or a late filing sealed
        as if it were prospective."""
        (batch, sets), _ = self.run_batch()
        st = {e["accession"][-1]: e["status"] for e in batch["events"]}
        # 5 and 9 were accepted before the window start (2026-10-28 00:00 New York): never listed, never sealed
        self.assertEqual(st, {"1": "SEALED", "2": "SEALED", "3": "SKIP_NO_TICKER", "4": "SKIP_NOT_IN_UNIVERSE",
                              "7": "SKIP_REPEAT_90D", "8": "SEALED"})
        by = {s["ticker"]: s for s in sets}
        self.assertEqual(by["T00"]["coverage"]["class"], "FIRE")
        self.assertAlmostEqual(by["T00"]["coverage"]["inputs"]["pre_entry_move"], 0.05)
        self.assertEqual(by["T00"]["event"]["item4"]["intent_words"], ["board", "merger"])
        self.assertEqual(by["T01"]["coverage"]["reasons"], ["DILUTION_RECENT"])
        self.assertEqual(by["T01"]["coverage"]["inputs"]["pre_entry_move"], 0.0)  # accepted after the close
        self.assertEqual(set(by["T04"]["coverage"]["reasons"]), {"MOVED_ALREADY", "MV_UNKNOWN"})
        for s in sets:
            self.assertEqual((s["signal_session"], s["entry"]["session"]), (SIGNAL, "2026-10-29"))
            self.assertEqual(s["entry_cutoff"], "2026-10-29T13:15:00Z")
            self.assertEqual(s["windows"], {"H20": {"kind": "plan", "entry_window": 1, "holding_sessions": 20}})
            self.assertEqual([c["id"] for c in s["cone"]], ["GAIN0_20", "BEATS_TWINS_20", "FADE10_20", "RUN30_20"])
            self.assertEqual([c["prior"] for c in s["cone"]], [0.55, 0.5, 0.5, 0.5])
        self.assertFalse(batch["feed"]["coverage_gap"])

    def test_twins_are_matched_event_free_operating_issuers_and_never_an_event_name(self):
        """Guards against: a twin that is a fund, a twin with its own 13D, or a twin that is another event's name."""
        (batch, sets), _ = self.run_batch()
        events = {"T00", "T01", "T04", "T58"}
        for s in sets:
            names = [t["ticker"] for t in s["twins"]]
            self.assertEqual(len(names), 5)
            self.assertFalse(events & set(names))
            for t in names:
                i = int(t[1:])
                self.assertTrue(i % 2 == 0 or i < 10, t)  # operating issuers only (no fund, no stale 10-K)
                self.assertNotEqual(t, "T12")  # its own original 13D in the last 90 days
            rejected = [x for x in s["twins_checked"] if not x["accepted"]]
            self.assertTrue(all(x["reason"] for x in rejected))
        again, _ = self.run_batch()
        self.assertEqual([t["ticker"] for t in sets[0]["twins"]], [t["ticker"] for t in again[1][0]["twins"]])

    def test_a_batch_refuses_after_the_cutoff_and_without_the_signal_scan_and_lists_nothing_twice(self):
        """Guards against: a set sealed after its entry, a set without its scan, or one filing sealed twice."""
        with self.assertRaises(RuntimeError):
            self.run_batch(clock=lambda: datetime(2026, 10, 29, 13, 16, tzinfo=timezone.utc))
        with self.assertRaises(RuntimeError):
            self.run_batch(ledger=[scan_record(session="2026-10-27")])
        (batch, sets), _ = self.run_batch()
        (batch2, sets2), _ = self.run_batch(records=[batch, *sets])
        self.assertEqual((batch2["events"], sets2), ([], []))
        self.assertFalse(batch2["feed"]["coverage_gap"])
        stale = {**batch, "feed": {**batch["feed"], "newest_entry": "2026-10-20T10:00:00-04:00"}}
        (batch3, _), _ = self.run_batch(records=[stale])
        self.assertTrue(batch3["feed"]["coverage_gap"])  # the feed no longer reaches back to the last batch


class IdxIndex(unittest.TestCase):
    def events_file(self, tmp: Path, changes) -> Path:
        p = tmp / "events.json"
        p.write_text(json.dumps({"review_id": "R1", "announced": "2026-10-27", "effective": "2026-11-02", "changes": changes}))
        return p

    def test_directions_windows_and_twins(self):
        """Guards against: a run-up window that crosses the effective date, a removed name given the added sign, a
        name both added and removed, or a twin that is itself in the review."""
        with tempfile.TemporaryDirectory(dir=paper.PKG_ROOT) as tmp:
            p = self.events_file(Path(tmp), [
                {"ticker": "T00", "index": "LQ45", "change": "ADD", "confidence": "CONFIRMED"},
                {"ticker": "T01", "index": "IDX30", "change": "DELETE", "confidence": "SINGLE_SOURCE"},
                {"ticker": "T02", "index": "IDX30", "change": "ADD", "confidence": "CONFIRMED"},
                {"ticker": "T02", "index": "IDX80", "change": "DELETE", "confidence": "CONFIRMED"}])
            f = features()
            f["close"] = 1000.0
            scan = scan_record(market="IDX")
            with mock.patch.object(sp, "scan_features", return_value=f):
                batch, sets = cr.idx_index_batch(p, datetime(2026, 10, 28, 11, 0, tzinfo=timezone.utc), ledger=[scan], records=[])
                with self.assertRaises(RuntimeError):
                    cr.idx_index_batch(p, datetime(2026, 10, 29, 1, 45, tzinfo=timezone.utc), ledger=[scan], records=[])
        by = {s["ticker"]: s for s in sets}
        self.assertEqual({e["ticker"]: e["status"] for e in batch["events"]}, {"T00": "SEALED", "T01": "SEALED", "T02": "SKIP_MIXED"})
        self.assertEqual((by["T00"]["direction"], by["T01"]["direction"]), (1, -1))
        self.assertEqual(by["T00"]["windows"], {"RUNUP": {"kind": "plan", "entry_window": 1, "holding_sessions": 1},
                                                "POST20": {"kind": "plan", "entry_window": 2, "holding_sessions": 20}})
        self.assertEqual(by["T01"]["event"]["confidence"], "SINGLE_SOURCE")
        self.assertEqual(by["T00"]["entry_cutoff"], "2026-10-29T01:45:00Z")
        for s in sets:
            self.assertFalse({"T00", "T01", "T02", "T58"} & {t["ticker"] for t in s["twins"]})


class Resolution(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore")

    def test_h20_pairs_the_candidate_with_its_twins_and_grades_the_cone(self):
        """Guards against: twins under another plan, a relative statement graded for twins, or a window resolved
        before its bars exist."""
        m, a = us_market(n_sessions=40)
        d = 10
        set_closes(a, 0, d + 1, [26 + k for k in range(25)], opens=[25] + [26 + k for k in range(1, 25)])
        m = build(m.tickers, m.dates, a)
        proto = cr.protocol()[0]["families"]["SEC13D"]
        s = {"type": "CATALYST_SET", "family": "SEC13D", "market": "US", "set_id": "CAT-X", "ticker": "U00",
             "signal_session": str(m.dates[d]), "signal": {"close": 25.0}, "direction": 1,
             "coverage": {"class": "FIRE"}, "twins": [{"ticker": "U01", "close": 25.0}, {"ticker": "U02", "close": 25.0}],
             "windows": {"H20": {"kind": "plan", "entry_window": 1, "holding_sessions": 20}},
             "cone": [{"id": c["id"], "prior": 0.5, "resolves_with": "H20"} for c in proto["cone"]],
             "protocol": {"id": "KOD-CATALYST-REGISTER-v1", "sha256": "s"}}
        r = cr.resolve_set(s, "H20", m, pd.DataFrame())
        self.assertEqual((r["status"], r["coverage"], r["family"]), ("RESOLVED", "FIRE", "SEC13D"))
        self.assertEqual(r["candidate"]["trade"]["entry_price"], 25.0)
        self.assertGreater(r["paired"]["diff"], 0.5)
        cone = {c["id"]: c for c in r["cone"]}
        self.assertEqual({k: v["outcome"] for k, v in cone.items()},
                         {"GAIN0_20": True, "BEATS_TWINS_20": True, "FADE10_20": False, "RUN30_20": True})
        self.assertNotIn("twins_rate", cone["BEATS_TWINS_20"])
        self.assertEqual(cone["GAIN0_20"]["twins_rate"], 0.0)
        short, _ = us_market(n_sessions=30)
        self.assertIsNone(cr.resolve_set({**s, "signal_session": str(short.dates[d])}, "H20", short, pd.DataFrame()))

    def test_index_statements_follow_the_sign_of_the_change(self):
        """Guards against: a removal graded as if it had been an addition."""
        self.assertTrue(cr.statement_outcome("WITH_FLOW_RUNUP", None, 0, 0, {"trade": {"net_return": -0.03}}, [0.0, 0.01], -1))
        self.assertFalse(cr.statement_outcome("WITH_FLOW_RUNUP", None, 0, 0, {"trade": {"net_return": -0.03}}, [0.0, 0.01], 1))
        self.assertTrue(cr.statement_outcome("REVERSAL_POST20", None, 0, 0, {"trade": {"net_return": -0.03}}, [0.0], 1))


class Looks(unittest.TestCase):
    def test_boundaries_match_the_spending_function_and_the_floor(self):
        """Guards against: a first look judged at the floor instead of its stricter spending boundary, or code and the
        frozen protocol disagreeing."""
        rule = cr.protocol()[0]["families"]["SEC13D"]["decision_rule"]
        z = NormalDist().inv_cdf(0.975)
        spend = [NormalDist().inv_cdf(1 - 2 * (1 - NormalDist().cdf(z / f ** 0.5))) for f in (0.25, 0.5, 1.0)]
        self.assertEqual(rule["boundaries"]["t_min"], [round(max(3.0, x), 2) for x in spend])
        st = {"n_paired": 70, "n_sessions": 20, "t": 3.5, "p_one_sided": 0.001, "mean_net": 0.01}
        self.assertFalse(cr.look_verdict(st, rule)["eligible"])  # 3.5 < 3.75 at the first look
        self.assertTrue(cr.look_verdict({**st, "n_paired": 130}, rule)["eligible"])
        self.assertFalse(cr.look_verdict({**st, "n_paired": 130, "mean_net": -0.01}, rule)["eligible"])
        self.assertEqual(cr.look_verdict({**st, "n_sessions": 10}, rule)["verdict"], "accumulating (no look reached)")
        self.assertEqual(cr.look_verdict({**st, "n_paired": 300, "t": 1.0}, rule)["verdict"], "FAIL at the final look")

    def test_code_constants_are_the_protocols(self):
        """Guards against: a threshold changed in code but not in the frozen protocol (or the reverse)."""
        text = json.dumps(cr.protocol()[0])
        for needle in ("at least 1.15 x the close", "USD 50 million", "90 calendar days", "19th weekday", "at most 15 names",
                       "28 calendar days"):
            self.assertIn(needle, text)
        self.assertEqual((cr.MOVED_ALREADY, cr.MICROCAP_USD, cr.REPEAT_DAYS, cr.DILUTION_SESSIONS, cr.TWIN_CHECKS,
                          cr.EN_DILUTION_DAYS), (1.15, 50e6, 90, 20, 15, 28))


class Tags(unittest.TestCase):
    def test_dilution_tags_for_us_and_idx_and_only_before_the_cutoff(self):
        """Guards against: a tag computed after the set's entry, a tag on a set sealed before the protocol, or an
        unreadable source recorded as 'no dilution'."""
        routes, _ = sec_world()
        specs = [{"type": "SPECULATION_SET", "market": "US", "set_id": "SPEC-A", "ticker": "T01", "signal_session": SIGNAL,
                  "sealed_at": "2026-10-28T22:00:00Z", "entry_cutoff": "2026-10-29T13:30:00Z", "record_hash": "h1"},
                 {"type": "SPECULATION_SET", "market": "IDX", "set_id": "SPEC-B", "ticker": "ABCD", "signal_session": SIGNAL,
                  "sealed_at": "2026-10-28T10:30:00Z", "entry_cutoff": "2026-10-29T01:45:00Z", "record_hash": "h2"},
                 {"type": "SPECULATION_SET", "market": "US", "set_id": "SPEC-OLD", "ticker": "T01", "signal_session": "2026-10-27",
                  "sealed_at": "2026-10-27T23:00:00Z", "entry_cutoff": "2026-10-28T13:30:00Z", "record_hash": "h0"},
                 {"type": "SPECULATION_SET", "market": "CRYPTO", "set_id": "SPEC-C", "ticker": "X", "signal_session": SIGNAL,
                  "sealed_at": "2026-10-28T00:30:00Z", "entry_cutoff": "2026-10-29T02:00:00Z", "record_hash": "h3"}]
        now = datetime(2026, 10, 29, 2, 0, tzinfo=timezone.utc)
        todo = cr.pending_tags(now, specs, [])
        self.assertEqual([s["set_id"] for s in todo], ["SPEC-A"])
        early = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
        self.assertEqual([s["set_id"] for s in cr.pending_tags(early, specs, [])], ["SPEC-A", "SPEC-B"])
        sitemap = (b"<url><loc>https://www.emitennews.com/news/abcd-rights-issue-hmetd-rp1-triliun</loc>"
                   b"<lastmod>2026-10-20T10:00:00+07:00</lastmod></url>")
        tags = cr.dilution_tags(early, cr.pending_tags(early, specs, []), FakeClient(routes), en_fetch=lambda url: sitemap,
                                clock=lambda: early)
        self.assertEqual([(t["set_id"], t["value"]) for t in tags], [("SPEC-A", True), ("SPEC-B", True)])
        self.assertIn("3.02", tags[0]["evidence"][0])
        broken = cr.dilution_tags(early, [specs[1]], None, en_fetch=lambda url: (_ for _ in ()).throw(OSError()), clock=lambda: early)
        self.assertIsNone(broken[0]["value"])
        with self.assertRaises(RuntimeError):
            cr.dilution_tags(early, [specs[1]], None, en_fetch=lambda url: sitemap,
                             clock=lambda: datetime(2026, 10, 29, 2, 0, tzinfo=timezone.utc))


class Verify(unittest.TestCase):
    def test_chain_cutoff_batch_listing_and_tag_binding_are_checked(self):
        """Guards against: a set sealed late, a set no batch lists, a tag after the set's cutoff, or an edited line."""
        proto_sha = cr.protocol()[1]
        scan = scan_record()
        base = {"type": "CATALYST_SET", "family": "SEC13D", "market": "US", "ticker": "T00", "signal_session": SIGNAL,
                "scan_id": scan["scan_id"], "scan_record_hash": scan["record_hash"], "features_sha256": "f" * 64,
                "windows": {"H20": {}}, "protocol": {"sha256": proto_sha}, "entry_cutoff": "2026-10-29T13:15:00Z"}
        batch = {"type": "BATCH", "family": "SEC13D", "sealed_at": "2026-10-28T22:50:00Z", "protocol": {"sha256": proto_sha},
                 "feed": {"coverage_gap": False}, "events": [{"status": "SEALED", "set_id": "CAT-1"}]}
        recs = [batch, {**base, "set_id": "CAT-1", "sealed_at": "2026-10-28T22:50:00Z"},
                {**base, "set_id": "CAT-2", "sealed_at": "2026-10-29T13:20:00Z"},
                {"type": "TAG", "tag": "DILUTION_RECENT", "set_id": "SPEC-A", "set_record_hash": "h1",
                 "sealed_at": "2026-10-29T14:00:00Z", "set_entry_cutoff": "2026-10-29T13:30:00Z"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalysts.jsonl"
            paper.append(recs, path=path)
            specs = [{"type": "SPECULATION_SET", "set_id": "SPEC-A", "record_hash": "h1"}]
            with mock.patch.object(cr, "CAT_LEDGER", path), mock.patch.object(paper, "ledger_lines",
                                                                              side_effect=lambda p=None: [scan] if p is None else json_lines(p)), \
                    mock.patch.object(sp, "spec_lines", return_value=specs):
                problems = cr.verify()
            joined = "\n".join(problems)
            self.assertIn("CAT-2: sealed at", joined)
            self.assertIn("CAT-2: not listed as SEALED", joined)
            self.assertIn("SPEC-A: tag sealed at", joined)
            self.assertNotIn("CAT-1:", joined)
            lines = path.read_text().splitlines()
            lines[1] = lines[1].replace('"T00"', '"T99"')
            path.write_text("\n".join(lines) + "\n")
            with mock.patch.object(cr, "CAT_LEDGER", path), mock.patch.object(paper, "ledger_lines",
                                                                              side_effect=lambda p=None: [scan] if p is None else json_lines(p)), \
                    mock.patch.object(sp, "spec_lines", return_value=specs):
                self.assertTrue(any("record_hash does not match" in p for p in cr.verify()))


def json_lines(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


if __name__ == "__main__":
    unittest.main()
