"""Catalyst family DILUTION_8K (idxsig.fam_dilution8k). Synthetic data only, no network. Each test names the failure it
guards against."""

from __future__ import annotations

import html
import json
import tempfile
import unittest
import warnings
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pandas as pd

from idxsig import catalysts as cr
from idxsig import fam_dilution8k as fd
from idxsig import paper
from idxsig import speculation as sp
from tests.test_catalysts import (
    FakeClient,
    build,
    features,
    json_lines,
    scan_record,
    set_closes,
    subs,
    us_market,
)

SIGNAL = "2026-10-29"
NOW = datetime(2026, 10, 29, 22, 50, tzinfo=timezone.utc)  # 18:50 New York (EDT): entry 2026-10-30
DILUTIVE = {
    f"T{i:02d}" for i in range(20, 40, 2)
}  # operating names with an S-3 in the last 90 days: never twins


def summary(items, acc="0000000000-26-000000") -> str:
    """The feed's summary as EDGAR sends it: HTML, escaped inside the XML."""
    body = f"<b>Filed:</b> 2026-10-29 <b>AccNo:</b> {acc} <b>Size:</b> 6 MB" + "".join(
        f" <br>Item {i}: Some item text" for i in items
    )
    return html.escape(body, quote=False)


def feed8k(entries) -> bytes:
    """entries: (form, name, cik, role, accepted, accession, items)"""
    parts = [
        '<?xml version="1.0" encoding="ISO-8859-1" ?><feed xmlns="http://www.w3.org/2005/Atom">'
    ]
    for form, name, cik, role, accepted, acc, items in entries:
        parts.append(
            f"<entry><title>{form} - {name} ({cik:010d}) ({role})</title>"
            f'<link rel="alternate" type="text/html" href="https://www.sec.gov/Archives/edgar/data/{cik}/'
            f'{acc.replace("-", "")}/{acc}-index.htm"/><summary type="html">{summary(items, acc)}</summary>'
            f"<updated>{accepted}</updated>"
            f'<category scheme="https://www.sec.gov/" label="form type" term="{form}"/></entry>'
        )
    return ("".join(parts) + "</feed>").encode()


ENTRIES = [
    (
        "8-K",
        "Alpha Inc",
        1000,
        "Filer",
        "2026-10-29T10:00:00-04:00",
        "0000000002-26-000001",
        ["3.02", "9.01"],
    ),
    (
        "8-K",
        "Beta Inc",
        1001,
        "Filer",
        "2026-10-29T17:00:00-04:00",
        "0000000002-26-000002",
        ["1.01", "3.02"],
    ),
    (
        "8-K",
        "Private Co",
        9999,
        "Filer",
        "2026-10-29T11:00:00-04:00",
        "0000000002-26-000003",
        ["3.02"],
    ),
    (
        "8-K",
        "Stale Inc",
        1059,
        "Filer",
        "2026-10-29T11:30:00-04:00",
        "0000000002-26-000004",
        ["3.02"],
    ),
    (
        "8-K/A",
        "Amended Inc",
        1005,
        "Filer",
        "2026-10-29T12:00:00-04:00",
        "0000000002-26-000005",
        ["3.02"],
    ),
    (
        "8-K",
        "Earnings Inc",
        1006,
        "Filer",
        "2026-10-29T12:10:00-04:00",
        "0000000002-26-000006",
        ["2.02", "9.01"],
    ),
    (
        "8-K",
        "Again Inc",
        1003,
        "Filer",
        "2026-10-29T12:30:00-04:00",
        "0000000002-26-000007",
        ["3.02"],
    ),
    (
        "8-K",
        "Fund Inc",
        1013,
        "Filer",
        "2026-10-29T13:00:00-04:00",
        "0000000002-26-000008",
        ["3.02"],
    ),
    (
        "8-K",
        "Holder LLC",
        7777,
        "Reporting",
        "2026-10-29T13:30:00-04:00",
        "0000000002-26-000010",
        ["3.02"],
    ),
    (
        "8-K",
        "Gamma Inc",
        1002,
        "Filer",
        "2026-10-29T13:30:00-04:00",
        "0000000002-26-000010",
        ["3.02"],
    ),
    (
        "8-K",
        "Old Inc",
        1008,
        "Filer",
        "2026-10-28T23:00:00-04:00",
        "0000000002-26-000009",
        ["3.02"],
    ),
]


def world(entries=ENTRIES):
    tmap = {
        "fields": ["cik", "name", "ticker", "exchange"],
        "data": [[1000 + i, f"Co {i}", f"T{i:02d}", "Nasdaq"] for i in range(60)],
    }
    routes = {
        fd.FEED_URL.format(start=0): (200, feed8k(entries)),
        fd.FEED_URL.format(start=100): (200, feed8k([])),
        cr.TICKERS_URL: (200, json.dumps(tmap).encode()),
    }
    for i in range(60):
        rows = (
            [("10-Q", "2026-08-10", "")]
            if i % 2 == 0 or i < 10
            else (
                [("N-CSR", "2026-08-10", ""), ("10-Q", "1995-06-12", "")]
                if i % 4 == 1
                else [("10-K", "2024-01-10", "")]
            )
        )
        if i == 3:
            rows.append(("8-K", "2026-09-15", "3.02,9.01"))  # an earlier Item 3.02: a repeat
        if i == 2:
            rows.append(("8-K/A", "2026-09-15", "3.02"))  # an amendment is not another 8-K
        if f"T{i:02d}" in DILUTIVE:
            rows.append(("S-3", "2026-09-20", ""))
        routes[cr.SUBMISSIONS_URL.format(cik=1000 + i)] = (200, subs(rows))
    return routes


def run(routes=None, now=NOW, session=SIGNAL, records=None, ledger=None, clock=None):
    with mock.patch.object(sp, "scan_features", return_value=features(session=session)):
        return fd.batch(
            now,
            FakeClient(routes or world()),
            ledger=[scan_record(session=session)] if ledger is None else ledger,
            records=records or [],
            clock=clock or (lambda: now),
        )


class Parsing(unittest.TestCase):
    def test_items_come_from_the_escaped_summary_and_amendments_are_not_events(self):
        """Guards against: an item read from the wrong field or left escaped, an 8-K/A or an 8-K without Item 3.02 taken
        for an event, or a non-Filer entry taken for the issuer."""
        raw = (
            "&lt;b&gt;Filed:&lt;/b&gt; 2026-10-28 &lt;b&gt;AccNo:&lt;/b&gt; 0001490906-26-000036 &lt;b&gt;Size:&lt;/b&gt; "
            "6 MB &lt;br&gt;Item 2.02: Results of Operations and Financial Condition &lt;br&gt;Item 9.01: Financial "
            "Statements and Exhibits"
        )
        body = (
            f'<feed><entry><title>8-K - Acme Corp (0001490906) (Filer)</title><link rel="alternate" '
            f'href="https://www.sec.gov/Archives/edgar/data/1490906/000149090626000036/0001490906-26-000036-index.htm"/>'
            f'<summary type="html">{raw}</summary><updated>2026-10-28T09:45:43-04:00</updated>'
            f'<category scheme="https://www.sec.gov/" label="form type" term="8-K"/></entry></feed>'
        ).encode()
        (e,) = fd.parse_feed(body)
        self.assertEqual(
            (e["items"], e["cik"], e["accession"], e["role"]),
            (["2.02", "9.01"], 1490906, "0001490906-26-000036", "Filer"),
        )
        self.assertEqual(
            fd.items_of_summary("Item 3.02: Unregistered Sales <br>Item 3.02: again"), ["3.02"]
        )
        evs = fd.events(fd.parse_feed(feed8k(ENTRIES)))
        accs = [e["accession"][-2:] for e in evs]
        self.assertNotIn("05", accs)  # 8-K/A
        self.assertNotIn("06", accs)  # no Item 3.02
        ten = next(e for e in evs if e["accession"].endswith("10"))
        self.assertEqual(
            ([f["cik"] for f in ten["filers"]], [o["cik"] for o in ten["others"]]), ([1002], [7777])
        )
        self.assertEqual(fd.issuer(ten, {1002: ["T02"]})["cik"], 1002)
        self.assertIsNone(fd.issuer({**ten, "filers": []}, {}))

    def test_repeat_rule_counts_only_other_item_302_8ks_in_the_90_days_before(self):
        """Guards against: the event itself, a same-day filing, an amendment or a 91-day-old filing counted as a repeat."""
        f = cr.e9.parse_submissions(
            subs(
                [
                    ("8-K", "2026-10-29", "3.02"),
                    ("8-K", "2026-08-01", "3.02,9.01"),
                    ("8-K", "2026-07-30", "3.02"),
                    ("8-K/A", "2026-09-01", "3.02"),
                    ("8-K", "2026-09-02", "2.02"),
                ]
            ),
            [],
        )
        self.assertEqual(
            [x.split("|")[2] for x in fd.earlier_302(f, "nope", SIGNAL)], ["2026-08-01"]
        )
        self.assertEqual(fd.earlier_302(f, "0000000000-26-000001", SIGNAL), [])
        self.assertEqual(fd.earlier_302(None, "x", SIGNAL), [])


class Batch(unittest.TestCase):
    def setUp(self):
        self.enterContext(warnings.catch_warnings())
        warnings.simplefilter("ignore")

    def test_every_event_gets_a_status_and_every_set_fires_short_side(self):
        """Guards against: an Item 3.02 8-K dropped without a record, a set that abstains, the wrong direction, or a
        set without its protocol binding and pre-entry move."""
        batch, sets = run()
        st = {e["accession"][-2:]: e["status"] for e in batch["events"]}
        # 05 (8-K/A), 06 (no Item 3.02) are not events; 09 was accepted before the window start
        self.assertEqual(
            st,
            {
                "01": "SEALED",
                "02": "SEALED",
                "03": "SKIP_NO_TICKER",
                "04": "SKIP_NOT_IN_UNIVERSE",
                "07": "SKIP_REPEAT_90D",
                "08": "SKIP_NOT_OPERATING",
                "10": "SEALED",
            },
        )
        fam, sha = cr.family_protocol("DILUTION_8K")
        by = {s["ticker"]: s for s in sets}
        self.assertEqual(set(by), {"T00", "T01", "T02"})
        self.assertEqual(
            by["T02"]["event"]["issuer_cik"], 1002
        )  # the Filer entry, not the reporting holder
        self.assertAlmostEqual(by["T00"]["coverage"]["inputs"]["pre_entry_move"], 0.05)
        self.assertEqual(
            by["T01"]["coverage"]["inputs"]["pre_entry_move"], 0.0
        )  # accepted after the close
        for s in sets:
            self.assertEqual(
                (s["coverage"]["class"], s["coverage"]["rules"], s["direction"]), ("FIRE", {}, -1)
            )
            self.assertEqual(s["set_id"], f"CAT-DILUTION_8K-{s['event_id']}")
            self.assertEqual(s["protocol"], {"id": fam["protocol_id"], "sha256": sha})
            self.assertEqual(
                (s["signal_session"], s["entry"]["session"], s["entry"]["basis"]),
                (SIGNAL, "2026-10-30", "open"),
            )
            self.assertEqual(s["entry_cutoff"], "2026-10-30T13:15:00Z")
            self.assertEqual(
                s["windows"], {"H20": {"kind": "plan", "entry_window": 1, "holding_sessions": 20}}
            )
            self.assertEqual(
                [(c["id"], c["prior"]) for c in s["cone"]],
                [
                    ("LOSES_TO_TWINS_20", 0.55),
                    ("GAIN0_20", 0.5),
                    ("FADE10_20", 0.5),
                    ("RUN30_20", 0.5),
                ],
            )
            self.assertNotIn("preregistration", s)
        self.assertEqual(batch["protocol"], {"id": fam["protocol_id"], "sha256": sha})
        self.assertFalse(batch["feed"]["coverage_gap"])
        self.assertEqual(
            len(batch["feed"]["pages"]), 1
        )  # page 0 already reaches before the window start

    def test_a_filing_the_register_saw_too_late_is_skipped(self):
        """Guards against: a filing whose reaction ran for a full session sealed as if it were prospective."""
        later = datetime(2026, 10, 30, 22, 50, tzinfo=timezone.utc)
        batch, sets = run(now=later, session="2026-10-30")
        st = {e["accession"][-2:]: e["status"] for e in batch["events"]}
        self.assertEqual((st["01"], st["02"], st["10"]), ("SKIP_LATE", "SEALED", "SKIP_LATE"))
        self.assertEqual([s["event"]["position"] for s in sets], ["DURING"])

    def test_twins_exclude_dilutive_names_funds_and_event_names(self):
        """Guards against: a twin with its own dilution filing, a fund twin, or a twin that is another event's name."""
        batch, sets = run()
        events = {
            "T00",
            "T01",
            "T02",
            "T03",
            "T13",
            "T58",
        }  # every event name with a ticker in the universe, the candidate
        rejected = []
        for s in sets:
            names = {t["ticker"] for t in s["twins"]}
            self.assertTrue(0 < len(names) <= cr.TWINS)
            self.assertFalse(events & names)
            self.assertFalse(DILUTIVE & names)
            self.assertTrue(all(int(t[1:]) % 2 == 0 or int(t[1:]) < 10 for t in names))
            self.assertLessEqual(len(s["twins_checked"]), cr.TWIN_CHECKS)
            rejected += [x["reason"] for x in s["twins_checked"] if not x["accepted"]]
        self.assertTrue(any("dilution" in r for r in rejected))
        self.assertEqual(
            [t["ticker"] for t in sets[0]["twins"]], [t["ticker"] for t in run()[1][0]["twins"]]
        )

    def test_refusals_and_no_filing_listed_twice(self):
        """Guards against: a set sealed after its entry cutoff, a batch without its scan, one filing sealed twice, or a
        second Item 3.02 of an issuer within 90 days of its sealed set."""
        with self.assertRaises(RuntimeError):
            run(clock=lambda: datetime(2026, 10, 30, 13, 15, tzinfo=timezone.utc))
        with self.assertRaises(RuntimeError):
            run(ledger=[scan_record(session="2026-10-28")])
        batch, sets = run()
        batch2, sets2 = run(records=[batch, *sets])
        self.assertEqual((batch2["events"], sets2), ([], []))
        self.assertFalse(batch2["feed"]["coverage_gap"])
        more = ENTRIES + [
            (
                "8-K",
                "Alpha Inc",
                1000,
                "Filer",
                "2026-10-29T18:00:00-04:00",
                "0000000002-26-000011",
                ["3.02"],
            )
        ]
        batch3, sets3 = run(routes=world(more), records=[batch, *sets])
        self.assertEqual(
            [(e["accession"][-2:], e["status"]) for e in batch3["events"]],
            [("11", "SKIP_REPEAT_90D")],
        )
        self.assertIn("earlier Item 3.02 8-K of the issuer", batch3["events"][0]["reason"])
        st = {e["accession"][-2:]: e["status"] for e in run(routes=world(more))[0]["events"]}
        self.assertEqual(
            (st["01"], st["11"]), ("SEALED", "SKIP_REPEAT_90D")
        )  # the first sealed in a batch wins

    def test_an_earlier_skipped_filing_of_the_issuer_still_makes_the_later_one_a_repeat(self):
        """Guards against: a second Item 3.02 8-K sealed because the issuer's first one, on the same day, was skipped
        (here too late for its session) and so never became a set."""
        later = datetime(2026, 10, 30, 22, 50, tzinfo=timezone.utc)
        more = ENTRIES + [
            (
                "8-K",
                "Alpha Inc",
                1000,
                "Filer",
                "2026-10-29T17:30:00-04:00",
                "0000000002-26-000012",
                ["3.02"],
            )
        ]
        batch, sets = run(routes=world(more), now=later, session="2026-10-30")
        st = {e["accession"][-2:]: e["status"] for e in batch["events"]}
        self.assertEqual((st["01"], st["12"]), ("SKIP_LATE", "SKIP_REPEAT_90D"))
        self.assertNotIn("CAT-DILUTION_8K-0000000002-26-000012", {s["set_id"] for s in sets})

    def test_no_share_class_of_the_event_company_is_its_twin_and_filers_are_listed_once(self):
        """Guards against: a twin that is the event company under another ticker (GOOG/GOOGL), or the same filer
        listed twice when the feed shifts between pages."""
        routes = world(ENTRIES + [ENTRIES[0]])  # Alpha's entry served twice
        tmap = json.loads(routes[cr.TICKERS_URL][1])
        tmap["data"] += [
            [1000, "Co 0", f"T{i:02d}", "Nasdaq"] for i in (40, 42, 44, 46, 48, 50)
        ]  # Alpha's other classes
        routes[cr.TICKERS_URL] = (200, json.dumps(tmap).encode())
        batch, sets = run(routes=routes)
        alpha = next(s for s in sets if s["ticker"] == "T00")
        self.assertFalse(
            {"T40", "T42", "T44", "T46", "T48", "T50"} & {t["ticker"] for t in alpha["twins"]}
        )
        self.assertEqual(len(alpha["event"]["filers"]), 1)

    def test_coverage_gaps(self):
        """Guards against: filings between the window start (or the last batch's newest entry) and the oldest entry read
        going unlisted while the batch says nothing was missed, or a read that never stops paging."""
        new_only = [e for e in ENTRIES if e[4] >= "2026-10-29"]
        for page0 in (feed8k(new_only), feed8k([])):
            routes = {**world(), fd.FEED_URL.format(start=0): (200, page0)}
            self.assertTrue(run(routes=routes)[0]["feed"]["coverage_gap"])
        routes = {
            **world(),
            **{fd.FEED_URL.format(start=100 * k): (200, feed8k(new_only)) for k in range(12)},
        }
        b = run(routes=routes)[0]
        self.assertEqual(
            (len(b["feed"]["pages"]), b["feed"]["coverage_gap"]), (fd.FEED_PAGES, True)
        )
        batch, sets = run()
        stale = {**batch, "feed": {**batch["feed"], "newest_entry": "2026-10-28T10:00:00-04:00"}}
        self.assertTrue(
            run(records=[stale])[0]["feed"]["coverage_gap"]
        )  # the read no longer reaches the last batch
        with self.assertRaises(RuntimeError):
            run(routes={**world(), fd.FEED_URL.format(start=0): (503, b"")})


class Ledger(unittest.TestCase):
    def setUp(self):
        self.enterContext(warnings.catch_warnings())
        warnings.simplefilter("ignore")

    def test_sets_verify_in_a_ledger_and_resolve_as_losers_to_their_twins(self):
        """Guards against: a set the register's verify() rejects (protocol, scan binding, batch listing, cutoff), or an
        avoid set graded on the wrong side of its twins."""
        batch, sets = run()
        scan = scan_record(session=SIGNAL)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalysts.jsonl"
            paper.append([batch, *sets], path=path)
            with (
                mock.patch.object(cr, "CAT_LEDGER", path),
                mock.patch.object(
                    paper,
                    "ledger_lines",
                    side_effect=lambda p=None: [scan] if p is None else json_lines(p),
                ),
                mock.patch.object(sp, "spec_lines", return_value=[]),
            ):
                self.assertEqual(cr.verify(), [])
        m, a = us_market(n_tickers=6, n_sessions=40)
        d = 10
        set_closes(
            a,
            0,
            d + 1,
            [24 - 0.3 * k for k in range(25)],
            opens=[25] + [24 - 0.3 * k for k in range(1, 25)],
        )
        m = build(m.tickers, m.dates, a)
        s = {
            **sets[0],
            "ticker": "U00",
            "signal_session": str(m.dates[d]),
            "signal": {**sets[0]["signal"], "close": 25.0},
            "twins": [{"ticker": f"U0{i}", "close": 25.0} for i in range(1, 6)],
        }
        r = cr.resolve_set(s, "H20", m, pd.DataFrame())
        self.assertEqual(
            (r["status"], r["family"], r["direction"], r["coverage"]),
            ("RESOLVED", "DILUTION_8K", -1, "FIRE"),
        )
        cone = {c["id"]: c["outcome"] for c in r["cone"]}
        self.assertEqual(
            cone,
            {"LOSES_TO_TWINS_20": True, "GAIN0_20": False, "FADE10_20": True, "RUN30_20": False},
        )
        self.assertLess(r["paired"]["diff"], 0)


if __name__ == "__main__":
    unittest.main()
