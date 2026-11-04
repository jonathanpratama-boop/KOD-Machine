"""Catalyst Register families SEC13D_V2 and FORM4_SHARP (idxsig.fam_sec13d_v2, idxsig.fam_form4_sharp) and the engine
pieces they need (60-session statements, mechanism windows, child-set binding). Synthetic data only, no network.
Each test names the failure it guards against."""

from __future__ import annotations

import tempfile
import unittest
import warnings
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pandas as pd

from idxsig import catalysts as cr
from idxsig import fam_form4 as f4
from idxsig import fam_form4_sharp as fs
from idxsig import fam_sec13d_v2 as v2
from idxsig import paper
from idxsig import speculation as sp
from tests.test_catalysts import (
    NOW,
    SIGNAL,
    FakeClient,
    build,
    features,
    json_lines,
    scan_record,
    sec_world,
    set_closes,
    subs,
    us_market,
)
from tests.test_fam_form4 import D1, filing, line, world
from tests.test_fam_form4 import NOW as F4_NOW


def cover(
    persons,
    purpose="We may talk to the Board.",
    item5c="No Reporting Person has effected any transactions.",
):
    """A structured Schedule 13D primary document: persons are (cik or None, name, amount, percent)."""
    blocks = "".join(
        "<reportingPersonInfo>"
        + (
            f"<reportingPersonCIK>{cik:010d}</reportingPersonCIK>"
            if cik
            else "<reportingPersonNoCIK>Y</reportingPersonNoCIK>"
        )
        + f"<reportingPersonName>{name}</reportingPersonName><aggregateAmountOwned>{amount}</aggregateAmountOwned>"
        f"<percentOfClass>{pct}</percentOfClass></reportingPersonInfo>"
        for cik, name, amount, pct in persons
    )
    return (
        f"<edgarSubmission><formData><coverPageHeader/><reportingPersons>{blocks}</reportingPersons><items1To7>"
        f"<item4><transactionPurpose>{purpose}</transactionPurpose></item4>"
        f"<item5><transactionDesc>{item5c}</transactionDesc></item5></items1To7></formData></edgarSubmission>"
    ).encode()


def hashed(recs):
    """Records as the ledger would hold them (a record hash each)."""
    return [{**r, "record_hash": f"h{i:04d}"} for i, r in enumerate(recs)]


V2_EARLY = {**cr.family_protocol("SEC13D_V2")[0], "window_start": "2026-10-28T00:00:00-04:00"}
REAL_FAMILY_PROTOCOL = cr.family_protocol


def early_v2(name):
    """SEC13D_V2's protocol with its window opened a day early, so the shared 13D test filings fall inside it."""
    return (V2_EARLY, "sha") if name == "SEC13D_V2" else REAL_FAMILY_PROTOCOL(name)


class Statements(unittest.TestCase):
    def test_sixty_session_statements_grade_like_their_twenty_session_twins(self):
        """Guards against: a 60-session statement silently left ungraded, or graded as a twin-relative one when it is
        not (and the reverse)."""
        win = {"trade": {"net_return": 0.04}}
        self.assertTrue(cr.statement_outcome("GAIN0_60", None, 0, 0, win, [], 1))
        self.assertTrue(
            cr.statement_outcome("BEATS_TWINS_60", None, 0, 0, win, [0.0, 0.01, 0.05], 1)
        )
        self.assertFalse(cr.statement_outcome("FADE10_60", None, 0, 0, win, [], 1))
        self.assertIsNone(cr.statement_outcome("BEATS_TWINS_60", None, 0, 0, win, [], 1))
        self.assertTrue(cr.is_relative("BEATS_TWINS_60") and cr.is_relative("BEATS_TWINS_20"))
        self.assertFalse(cr.is_relative("GAIN0_60") or cr.is_relative("MECH_13DA_UP_60"))

    def test_h60_resolves_on_its_own_bars_and_grades_only_its_statements(self):
        """Guards against: a 60-session window resolved on 20 sessions of bars, or H20 statements graded on H60."""
        m, a = us_market(n_sessions=90)
        d = 10
        set_closes(
            a,
            0,
            d + 1,
            [26 + 0.1 * k for k in range(70)],
            opens=[25] + [26 + 0.1 * k for k in range(1, 70)],
        )
        m = build(m.tickers, m.dates, a)
        cone = [
            {"id": i, "prior": 0.5, "resolves_with": w}
            for i, w in (
                ("GAIN0_20", "H20"),
                ("BEATS_TWINS_60", "H60"),
                ("GAIN0_60", "H60"),
                ("MECH_13DA_UP_60", "M60"),
            )
        ]
        s = {
            "type": "CATALYST_SET",
            "family": "SEC13D_V2",
            "market": "US",
            "set_id": "CAT-V",
            "ticker": "U00",
            "signal_session": str(m.dates[d]),
            "signal": {"close": 25.0},
            "direction": 1,
            "coverage": {"class": "FIRE"},
            "twins": [{"ticker": "U01", "close": 25.0}],
            "cone": cone,
            "protocol": {"id": "p", "sha256": "s"},
            "windows": {
                "H20": {"kind": "plan", "entry_window": 1, "holding_sessions": 20},
                "H60": {"kind": "plan", "entry_window": 1, "holding_sessions": 60},
                "M60": {"kind": "mechanism", "calendar_days": 60},
            },
        }
        r = cr.resolve_set(s, "H60", m, pd.DataFrame())
        self.assertEqual(r["status"], "RESOLVED")
        self.assertEqual(
            {c["id"]: c["outcome"] for c in r["cone"]}, {"BEATS_TWINS_60": True, "GAIN0_60": True}
        )
        short, _ = us_market(n_sessions=60)
        self.assertIsNone(
            cr.resolve_set(
                {**s, "signal_session": str(short.dates[d])}, "H60", short, pd.DataFrame()
            )
        )

    def test_mechanism_windows_are_due_on_their_own_clock_and_never_in_the_price_pass(self):
        """Guards against: the price resolver tripping over a mechanism window, or a mechanism window due early."""
        s = {
            "type": "CATALYST_SET",
            "market": "US",
            "set_id": "CAT-M",
            "signal_session": "2026-10-28",
            "event": {"accepted": "2026-10-28T17:00:00-04:00"},
            "windows": {
                "H20": {"kind": "plan", "entry_window": 1, "holding_sessions": 20},
                "M60": {"kind": "mechanism", "calendar_days": 60},
                "M20": {"kind": "mechanism", "sessions": 20},
            },
        }
        self.assertEqual(cr.due("US", today="2026-12-27", records=[s]), [("CAT-M", "H20")])
        self.assertEqual(
            cr.due("US", today="2026-12-27", records=[s], mechanism=True), [("CAT-M", "M20")]
        )
        self.assertEqual(
            cr.due("US", today="2026-12-28", records=[s], mechanism=True),
            [("CAT-M", "M60"), ("CAT-M", "M20")],
        )
        done = {"type": "RESOLUTION", "set_id": "CAT-M", "window": "M20"}
        self.assertEqual(
            cr.due("US", today="2026-12-28", records=[s, done], mechanism=True), [("CAT-M", "M60")]
        )


class CoverPage(unittest.TestCase):
    def test_shares_come_from_the_person_with_the_largest_percent(self):
        """Guards against: shares implied from a small, coarsely rounded percent, or from a person without one."""
        cp = v2.cover_page(
            cover(
                [
                    (5000, "Fund A LP", "1000000.00", "5.0"),
                    (5001, "Fund A GP", "1200000", "6.0"),
                    (None, "John Doe", "0", "0.0"),
                ]
            )
        )
        self.assertEqual(len(cp["persons"]), 3)
        self.assertAlmostEqual(cp["implied_shares"], 20_000_000)
        self.assertEqual((cp["max_percent"], cp["implied_from"]["cik"]), (6.0, 5001))
        self.assertIsNone(cp["persons"][2]["cik"])
        self.assertIsNone(v2.cover_page(b"<edgarSubmission/>")["implied_shares"])

    def test_the_cover_page_rescues_an_unknown_size_but_never_overrides_xbrl(self):
        """Guards against: an issuer abstained on only because XBRL had no share count, a microcap passed because the
        cover page was rounded, or the cover page used when the XBRL fact exists."""
        parent = {
            "coverage": {
                "rules": {"DILUTION_RECENT": False, "MOVED_ALREADY": False, "MICROCAP": True},
                "inputs": {"shares_fact": None, "market_value_usd": None},
            }
        }
        big = v2.cover_page(cover([(5000, "F", "1000000", "5.0")]))  # 20M shares
        small = v2.cover_page(cover([(5000, "F", "100000", "5.0")]))  # 2M shares
        c = v2.coverage(parent, big, 12.0)
        self.assertEqual(
            (c["class"], c["inputs"]["shares_source"], c["inputs"]["market_value_usd"]),
            ("FIRE", "COVER_PAGE", 240e6),
        )
        self.assertEqual(v2.coverage(parent, small, 12.0)["reasons"], ["MICROCAP"])
        self.assertEqual(v2.coverage(parent, v2.cover_page(b""), 12.0)["reasons"], ["MV_UNKNOWN"])
        xbrl = {"coverage": {**parent["coverage"], "inputs": {"shares_fact": {"val": 1.0e6}}}}
        c = v2.coverage(xbrl, big, 12.0)
        self.assertEqual((c["inputs"]["shares_source"], c["reasons"]), ("XBRL", ["MICROCAP"]))

    def test_item4_strong_intent_ignores_boilerplate_and_item5c_reads_prices(self):
        """Guards against: every 13D tagged as activist for mentioning the board, or a price list misread."""
        body = cover(
            [(1, "F", "1", "5.0")],
            purpose="We intend to nominate directors and seek strategic alternatives.",
            item5c="On 10/20/2026 the Fund bought 10,000 shares at $12.50 and 5,000 at $13.50 per share.",
        )
        si = v2.strong_intent(None, body)
        self.assertEqual(
            (si["strong"], si["words"]), (True, ["nominate", "strategic alternatives"])
        )
        self.assertFalse(
            v2.strong_intent(
                None,
                cover([(1, "F", "1", "5.0")], purpose="We may talk to the Board and management."),
            )["strong"]
        )
        i5 = v2.item5c(body, 15.0)
        self.assertEqual((i5["prices"], i5["mean_price"], i5["no_transactions"]), (2, 13.0, False))
        self.assertAlmostEqual(i5["close_to_mean_price"], 15.0 / 13.0)
        self.assertTrue(v2.item5c(cover([(1, "F", "1", "5.0")]), 15.0)["no_transactions"])


class V2Batch(unittest.TestCase):
    def setUp(self):
        self.enterContext(warnings.catch_warnings())
        warnings.simplefilter("ignore")

    def world(self, xbrl_alpha=False):
        routes, shares = sec_world()
        if not xbrl_alpha:
            shares = {k: v for k, v in shares.items() if k != 1000}
        routes[cr.PRIMARY_DOC_URL.format(cik=1000, acc="000000000126000001")] = (
            200,
            cover([(5000, "Fund A LP", "1000000", "5.0")]),
        )
        routes[cr.PRIMARY_DOC_URL.format(cik=1001, acc="000000000126000002")] = (
            200,
            cover([(5001, "Fund B", "50000", "5.0")]),
        )
        routes[cr.PRIMARY_DOC_URL.format(cik=1004, acc="000000000126000008")] = (
            200,
            cover([(5004, "Fund C", "3000000", "9.9")]),
        )
        return routes, shares

    def seal(self, routes, shares, records=None, now=NOW):
        client = FakeClient(routes)
        with (
            mock.patch.object(sp, "scan_features", return_value=features()),
            mock.patch.object(cr, "share_points", side_effect=lambda c, cik: shares.get(cik, [])),
        ):
            pb, psets = cr.sec13d_batch(
                now, client, ledger=[scan_record()], records=[], clock=lambda: now
            )
            recs = hashed([*(records or []), pb, *psets])
            with mock.patch.object(cr, "family_protocol", side_effect=early_v2):
                b, sets = v2.batch(
                    now, client, ledger=[scan_record()], records=recs, clock=lambda: now
                )
        return recs, b, sets

    def test_a_filing_abstained_on_for_unknown_size_fires_in_v2_and_sec13d_is_untouched(self):
        """Guards against: the v2 family changing a SEC13D record, missing a SEC13D set, or keeping the MV_UNKNOWN
        abstention the cover page can resolve."""
        routes, shares = self.world()
        recs, b, sets = self.seal(routes, shares)
        parents = {s["set_id"]: s for s in recs if s["type"] == "CATALYST_SET"}
        alpha_v1 = parents["CAT-SEC13D-0000000001-26-000001"]
        self.assertEqual(alpha_v1["coverage"]["reasons"], ["MV_UNKNOWN"])
        by_parent = {s["parent"]["set_id"]: s for s in sets}
        self.assertEqual(set(by_parent), set(parents))
        alpha = by_parent[alpha_v1["set_id"]]
        self.assertEqual(
            (alpha["coverage"]["class"], alpha["coverage"]["inputs"]["shares_source"]),
            ("FIRE", "COVER_PAGE"),
        )
        self.assertEqual(alpha["parent"]["record_hash"], alpha_v1["record_hash"])
        self.assertEqual(
            (alpha["signal_session"], alpha["entry"], alpha["entry_cutoff"]),
            (alpha_v1["signal_session"], alpha_v1["entry"], alpha_v1["entry_cutoff"]),
        )
        self.assertEqual(set(alpha["windows"]), {"H20", "H60", "M60"})
        self.assertEqual(alpha["windows"]["M60"], {"kind": "mechanism", "calendar_days": 60})
        self.assertEqual([c["id"] for c in alpha["cone"]][-1], "MECH_13DA_UP_60")
        self.assertEqual(
            b["parent_batch"]["record_hash"],
            next(r for r in recs if r["type"] == "BATCH")["record_hash"],
        )
        self.assertTrue(all(e["status"] == "SEALED" for e in b["events"]))

    def test_twenty_twins_start_with_sec13ds_five(self):
        """Guards against: a v2 twin set drawn in another order (so v1 and v2 differ by more than the extra twins)."""
        routes, shares = self.world()
        recs, _, sets = self.seal(routes, shares)
        parents = {s["set_id"]: s for s in recs if s["type"] == "CATALYST_SET"}
        for s in sets:
            v1 = [t["ticker"] for t in parents[s["parent"]["set_id"]]["twins"]]
            mine = [t["ticker"] for t in s["twins"]]
            self.assertGreater(len(mine), len(v1))
            self.assertLessEqual(len(mine), cr.TWINS_20)
            if len(v1) == cr.TWINS:
                self.assertEqual(mine[: cr.TWINS], v1)
            self.assertFalse({s["ticker"], "T58"} & set(mine))

    def test_no_parent_batch_refuses_and_a_second_run_seals_nothing_twice(self):
        """Guards against: a v2 batch run before SEC13D's (sealing from nothing), or a set sealed twice."""
        routes, shares = self.world()
        with (
            mock.patch.object(sp, "scan_features", return_value=features()),
            self.assertRaisesRegex(RuntimeError, "run catalyst-seal --family SEC13D first"),
        ):
            v2.batch(NOW, FakeClient(routes), ledger=[scan_record()], records=[], clock=lambda: NOW)
        recs, b, sets = self.seal(routes, shares)
        client = FakeClient(routes)
        with (
            mock.patch.object(sp, "scan_features", return_value=features()),
            mock.patch.object(cr, "family_protocol", side_effect=early_v2),
        ):
            b2, sets2 = v2.batch(
                NOW,
                client,
                ledger=[scan_record()],
                records=hashed([*recs, b, *sets]),
                clock=lambda: NOW,
            )
        self.assertEqual((sets2, b2["events"]), ([], []))
        # a recorded skip is final: the document served later does not reopen it
        del routes[cr.PRIMARY_DOC_URL.format(cik=1001, acc="000000000126000002")]
        recs, b, sets = self.seal(routes, shares)
        routes.update(self.world()[0])
        with (
            mock.patch.object(sp, "scan_features", return_value=features()),
            mock.patch.object(cr, "family_protocol", side_effect=early_v2),
        ):
            b3, sets3 = v2.batch(
                NOW,
                FakeClient(routes),
                ledger=[scan_record()],
                records=hashed([*recs, b, *sets]),
                clock=lambda: NOW,
            )
        self.assertEqual((sets3, b3["events"]), ([], []))

    def test_a_missed_run_is_caught_up_from_an_earlier_parent_batch_of_the_same_entry(self):
        """Guards against: SEC13D sets of the evening batch lost to SEC13D_V2 because only the morning batch is read."""
        routes, shares = self.world()
        client = FakeClient(routes)
        morning = datetime(2026, 10, 29, 10, 20, tzinfo=timezone.utc)
        with (
            mock.patch.object(sp, "scan_features", return_value=features()),
            mock.patch.object(cr, "share_points", side_effect=lambda c, cik: shares.get(cik, [])),
        ):
            evening, esets = cr.sec13d_batch(
                NOW, client, ledger=[scan_record()], records=[], clock=lambda: NOW
            )
            recs = hashed([evening, *esets])
            mb, msets = cr.sec13d_batch(
                morning, client, ledger=[scan_record()], records=recs, clock=lambda: morning
            )
            recs = hashed([*recs, mb, *msets])
            with mock.patch.object(cr, "family_protocol", side_effect=early_v2):
                _, sets = v2.batch(
                    morning, client, ledger=[scan_record()], records=recs, clock=lambda: morning
                )
        self.assertEqual(msets, [])
        self.assertEqual({s["parent"]["set_id"] for s in sets}, {s["set_id"] for s in esets})

    def test_a_missing_primary_document_is_a_recorded_skip(self):
        """Guards against: a v2 set sealed without the cover page it is defined by, or the filing silently dropped."""
        routes, shares = self.world()
        del routes[cr.PRIMARY_DOC_URL.format(cik=1001, acc="000000000126000002")]
        _, b, sets = self.seal(routes, shares)
        st = {e["accession"][-1]: e["status"] for e in b["events"]}
        self.assertEqual(st, {"1": "SEALED", "2": "SKIP_NO_PRIMARY_DOC", "8": "SEALED"})
        self.assertEqual(len(sets), 2)

    def test_the_window_start_keeps_earlier_filings_out(self):
        """Guards against: a filing accepted before the family was frozen sealed into it."""
        routes, shares = self.world()
        client = FakeClient(routes)
        with (
            mock.patch.object(sp, "scan_features", return_value=features()),
            mock.patch.object(cr, "share_points", side_effect=lambda c, cik: shares.get(cik, [])),
        ):
            pb, psets = cr.sec13d_batch(
                NOW, client, ledger=[scan_record()], records=[], clock=lambda: NOW
            )
            b, sets = v2.batch(
                NOW, client, ledger=[scan_record()], records=hashed([pb, *psets]), clock=lambda: NOW
            )
        self.assertEqual((sets, b["window_start"]), ([], "2026-10-29T00:00:00-04:00"))


class V2Mechanism(unittest.TestCase):
    S = {
        "family": "SEC13D_V2",
        "market": "US",
        "set_id": "CAT-SEC13D_V2-A",
        "ticker": "T00",
        "signal_session": SIGNAL,
        "coverage": {"class": "FIRE"},
        "direction": 1,
        "protocol": {"id": "p", "sha256": "s"},
        "event": {
            "accepted": "2026-10-28T10:00:00-04:00",
            "subject_cik": 1000,
            "cover_page": {"persons": [{"cik": 5000}, {"cik": None}], "max_percent": 5.0},
        },
        "windows": {"M60": {"kind": "mechanism", "calendar_days": 60}},
        "cone": [
            {"id": "MECH_13DA_UP_60", "prior": 0.5, "resolves_with": "M60"},
            {"id": "GAIN0_20", "prior": 0.5, "resolves_with": "H20"},
        ],
    }

    def routes(self, amendments):
        """amendments: (filing date, reporting person CIK, percent) or (filing date, None, None) for an unreadable one."""
        rows = [("10-Q", "2026-08-10", "")] + [
            ("SCHEDULE 13D/A", day, "") for day, _, _ in amendments
        ]
        routes = {cr.SUBMISSIONS_URL.format(cik=1000): (200, subs(rows))}
        for i, (_, cik, pct) in enumerate(amendments, start=1):
            if cik is not None:
                routes[cr.PRIMARY_DOC_URL.format(cik=1000, acc=f"000000000026{i:06d}")] = (
                    200,
                    cover([(cik, "F", "1", pct)]),
                )
        return routes

    def outcome(self, amendments, today="2026-12-28", client=True):
        rec = v2.resolve_mechanism(
            self.S, "M60", [], FakeClient(self.routes(amendments)) if client else None, today=today
        )
        return None if rec is None else rec["cone"][0]["outcome"]

    def test_the_stake_must_rise_in_a_filing_by_the_same_holder_within_60_days(self):
        """Guards against: any amendment counted (a stake cut, another holder, or one after the window) as the
        mechanism working."""
        self.assertTrue(self.outcome([("2026-11-20", 5000, "7.5")]))
        self.assertFalse(self.outcome([("2026-11-20", 5000, "4.0")]))
        self.assertFalse(self.outcome([("2026-11-20", 6000, "9.0")]))
        self.assertFalse(self.outcome([("2026-12-28", 5000, "9.0")]))  # day 61
        self.assertFalse(self.outcome([]))

    def test_unreadable_sources_wait_then_record_ungraded_and_no_client_waits(self):
        """Guards against: an unreadable amendment graded false, or a statement left due forever."""
        self.assertIsNone(self.outcome([("2026-11-20", None, None)]))  # retried
        self.assertTrue(self.outcome([("2026-11-20", None, None), ("2026-11-21", 5000, "8")]))
        late = v2.resolve_mechanism(
            self.S,
            "M60",
            [],
            FakeClient(self.routes([("2026-11-20", None, None)])),
            today="2027-01-20",
        )
        self.assertIsNone(late["cone"][0]["outcome"])
        self.assertEqual([c["id"] for c in late["cone"]], ["MECH_13DA_UP_60"])
        self.assertIsNone(self.outcome([("2026-11-20", 5000, "7.5")], client=False))


class Sharp(unittest.TestCase):
    def test_band_edges_and_rules(self):
        """Guards against: an off-by-one at the USD 100k or 500k edge, or unknown dilution treated as none."""
        self.assertTrue(fs.sharp(False, 100_000)["VALUE_BAND"])
        self.assertFalse(fs.sharp(False, 500_000)["VALUE_BAND"])
        self.assertFalse(fs.sharp(False, 99_999.99)["sharp"])
        self.assertTrue(fs.sharp(True, 60_000)["sharp"])
        ok = fs.sharp(True, 60_000)
        self.assertEqual(fs.coverage(ok, [], {"routine": False})["class"], "FIRE")
        self.assertEqual(fs.coverage(ok, None, {"routine": False})["reasons"], ["DILUTION_RECENT"])
        self.assertEqual(
            fs.coverage(fs.sharp(False, 60_000), ["8-K|x|2026-10-20|3.02"], {"routine": True})[
                "reasons"
            ],
            ["NOT_SHARP", "DILUTION_RECENT", "ROUTINE"],
        )

    def test_holdings_increase_uses_the_post_transaction_amount(self):
        """Guards against: an increase computed against the wrong base, or invented when the holding is missing."""

        def post(after):
            return line(1000, 60.0).replace(
                "</transactionAmounts>",
                f"</transactionAmounts><postTransactionAmounts><sharesOwnedFollowingTransaction>"
                f"<value>{after}</value></sharesOwnedFollowingTransaction></postTransactionAmounts>",
            )

        xml = f4.form4_xml(filing(1000, lines=[post(3000), post(5000)]))
        self.assertEqual(
            fs.holdings_increase(xml),
            {"bought": 2000.0, "after": 5000.0, "increase": 2000.0 / 3000.0},
        )
        self.assertIsNone(fs.holdings_increase(f4.form4_xml(filing(1000)))["increase"])
        self.assertIsNone(
            fs.holdings_increase(f4.form4_xml(filing(1000, lines=[post(1000)])))["increase"]
        )


def owner_world(years_hit, code="P", owner_cik=9001, month="10"):
    """An owner's submissions with one Form 4 in October of each year in years_hit, carrying a `code` line."""
    rows = [("4", f"{y}-{month}-15", "") for y in years_hit]
    routes = {cr.SUBMISSIONS_URL.format(cik=owner_cik): (200, subs(rows))}
    for i, y in enumerate(years_hit):
        routes[fs.FILING_URL.format(cik=owner_cik, acc=f"0000000000-26-{i:06d}")] = (
            200,
            filing(1000, lines=[line(code=code, day=f"{y}-{month}-14")]),
        )
    return routes


class Routine(unittest.TestCase):
    def test_an_owner_who_trades_the_same_month_three_years_running_is_routine(self):
        """Guards against: a routine insider counted as informative, or a grant-only history counted as routine."""
        r = fs.owner_routine(FakeClient(owner_world([2023, 2024, 2025])), 9001, "2026-10-27")
        self.assertEqual((r["routine"], r["unknown"]), (True, False))
        self.assertFalse(
            fs.owner_routine(FakeClient(owner_world([2023, 2025])), 9001, "2026-10-27")["routine"]
        )
        self.assertFalse(
            fs.owner_routine(
                FakeClient(owner_world([2023, 2024, 2025], code="A")), 9001, "2026-10-27"
            )["routine"]
        )
        self.assertTrue(
            fs.owner_routine(
                FakeClient(owner_world([2023, 2024, 2025], code="S")), 9001, "2026-10-27"
            )["routine"]
        )
        self.assertFalse(
            fs.owner_routine(
                FakeClient(owner_world([2023, 2024, 2025], month="09")), 9001, "2026-10-27"
            )["routine"]
        )

    def test_an_unreadable_history_is_not_routine_and_says_so(self):
        """Guards against: an owner whose history could not be read abstained on as routine."""
        r = fs.owner_routine(FakeClient({}), 9001, "2026-10-27")
        self.assertEqual((r["routine"], r["unknown"]), (False, True))
        r = fs.owner_routine(FakeClient({}), None, "2026-10-27")
        self.assertEqual((r["routine"], r["unknown"]), (False, True))


class SharpBatch(unittest.TestCase):
    def setUp(self):
        self.enterContext(warnings.catch_warnings())
        warnings.simplefilter("ignore")

    def seal(self, routes, extra=None, mutate=None):
        ledger = [scan_record(session=D1), scan_record(session="2026-10-30")]
        client = FakeClient(routes)
        with mock.patch.object(
            sp, "scan_features", side_effect=lambda scan: features(session=scan["session"])
        ):
            pb, psets = f4.batch(F4_NOW, client, ledger=ledger, records=[], clock=lambda: F4_NOW)
            pb.pop("_side_file", None)
            recs = hashed([pb, *psets])
            if mutate:
                mutate(routes)
            routes.update(extra or {})
            b, sets = fs.batch(F4_NOW, client, ledger=ledger, records=recs, clock=lambda: F4_NOW)
        return recs, b, sets

    def test_each_form4_set_gets_a_sharp_set_with_its_rules_and_twenty_twins(self):
        """Guards against: a FORM4 set skipped, a director's USD 60k buy fired, or a top executive's buy abstained."""
        routes = world()
        recs, b, sets = self.seal(routes)
        parents = {s["set_id"]: s for s in recs if s["type"] == "CATALYST_SET"}
        self.assertEqual({s["parent"]["set_id"] for s in sets}, set(parents))
        by_issuer = {s["event"]["issuer_cik"]: s for s in sets}
        self.assertEqual(
            by_issuer[1000]["coverage"]["reasons"], ["NOT_SHARP"]
        )  # a director, USD 60,000
        self.assertEqual(
            by_issuer[1001]["coverage"]["class"], "FIRE"
        )  # a CFO among the buyers, USD 160,000
        self.assertEqual(by_issuer[1003]["coverage"]["class"], "FIRE")  # a CEO
        for s in sets:
            self.assertEqual(set(s["windows"]), {"H20", "H60", "M20"})
            self.assertEqual(s["plan"], "H60")
            self.assertGreater(len(s["twins"]), len(parents[s["parent"]["set_id"]]["twins"]))
            self.assertEqual(
                s["parent"]["record_hash"], parents[s["parent"]["set_id"]]["record_hash"]
            )
            self.assertFalse(
                s["coverage"]["inputs"]["routine"]["routine"]
            )  # no owner history served: not routine
        self.assertEqual(b["parent_batch"]["family"], "FORM4")

    def test_dilution_and_a_routine_buyer_abstain(self):
        """Guards against: a CEO's buy fired at an issuer that just sold stock, or a routine buyer's fired."""
        routes = world()
        routes[cr.SUBMISSIONS_URL.format(cik=1003)] = (
            200,
            subs([("10-Q", "2026-08-10", ""), ("8-K", "2026-10-21", "3.02")]),
        )
        extra = owner_world(
            [2023, 2024, 2025], owner_cik=9002
        )  # the CFO of issuer 1001 buys every October
        _, _, sets = self.seal(routes, extra=extra)
        by_issuer = {s["event"]["issuer_cik"]: s for s in sets}
        self.assertEqual(by_issuer[1003]["coverage"]["reasons"], ["DILUTION_RECENT"])
        # issuer 1001 has two buyers (9002 routine, 9012 not): not every buyer is routine, so it still fires
        self.assertEqual(by_issuer[1001]["coverage"]["class"], "FIRE")
        routine = {
            o["cik"]: o["routine"]
            for o in by_issuer[1001]["coverage"]["inputs"]["routine"]["owners"]
        }
        self.assertEqual(routine, {9002: True, 9012: False})

    def test_a_filing_whose_xml_changed_is_skipped(self):
        """Guards against: a sharp set built on a document other than the one FORM4 hashed."""

        def mutate(routes):
            routes[f4.ARCHIVE_URL.format(path="edgar/data/1000/0000000002-26-000001.txt")] = (
                200,
                filing(1000, lines=[line(999)]),
            )

        _, b, sets = self.seal(world(), mutate=mutate)
        st = {e["issuer_cik"]: e["status"] for e in b["events"]}
        self.assertEqual(st[1000], "SKIP_XML_CHANGED")
        self.assertNotIn(1000, {s["event"]["issuer_cik"] for s in sets})


class SecondBuy(unittest.TestCase):
    S = {
        "family": "FORM4_SHARP",
        "market": "US",
        "set_id": "CAT-FORM4_SHARP-A",
        "ticker": "T00",
        "signal_session": "2026-10-29",
        "coverage": {"class": "FIRE"},
        "direction": 1,
        "protocol": {"id": "p", "sha256": "s"},
        "event": {"issuer_cik": 1000, "filing_date": "2026-10-29"},
        "windows": {"M20": {"kind": "mechanism", "sessions": 20}},
        "cone": [{"id": "MECH_SECOND_BUY_20", "prior": 0.5, "resolves_with": "M20"}],
    }

    def batches(self, through="2026-11-27", missing=(), events=(), unreadable=()):
        days = [
            d
            for d in pd.bdate_range("2026-10-29", through).strftime("%Y-%m-%d")
            if cr.us_is_session(d)
        ]
        return [
            {
                "type": "BATCH",
                "family": "FORM4",
                "sealed_at": f"{d}T12:00:00Z",
                "unreadable": list(unreadable) if d == days[3] else [],
                "index_dates": [{"date": d, "status": "MISSING" if d in missing else "READ"}],
                "events": [
                    {"issuer_cik": c, "filing_date": fd, "accession": f"a-{fd}", "status": st}
                    for c, fd, st in events
                    if fd == d
                ],
            }
            for d in days
        ]

    def outcome(self, **kw):
        rec = fs.resolve_mechanism(self.S, "M20", self.batches(**kw))
        return "WAIT" if rec is None else rec["cone"][0]["outcome"]

    def test_a_later_purchase_on_the_issuer_within_20_sessions_counts_whatever_its_status(self):
        """Guards against: the event itself, another issuer, a buy after the 20th session, or a repeat FORM4 skipped
        counted the wrong way."""
        end = fs.session_after("2026-10-29", 20)
        self.assertEqual(end, "2026-11-27")  # 23 Oct-Nov weekdays less Thanksgiving (2026-11-26)
        self.assertTrue(self.outcome(events=[(1000, "2026-11-10", "SKIP_REPEAT_90D")]))
        self.assertFalse(
            self.outcome(events=[(1000, "2026-10-29", "SEALED"), (1001, "2026-11-10", "SEALED")])
        )
        self.assertFalse(
            self.outcome(through="2026-12-01", events=[(1000, "2026-11-30", "SEALED")])
        )

    def test_it_waits_for_every_date_and_records_a_gap_ungraded(self):
        """Guards against: a statement graded false before its dates were read, or false across a missing index."""
        self.assertEqual(self.outcome(through="2026-11-20"), "WAIT")
        self.assertIsNone(self.outcome(missing=("2026-11-12",)))
        self.assertIsNone(self.outcome(unreadable=("x|HTTP 500",)))
        self.assertTrue(
            self.outcome(missing=("2026-11-12",), events=[(1000, "2026-11-13", "SEALED")])
        )


class Statistics(unittest.TestCase):
    def test_the_decision_window_and_class_come_from_the_protocol(self):
        """Guards against: FORM4_SHARP's primary computed on H20 or on abstained sets."""
        fsp, fsha = cr.family_protocol("FORM4_SHARP")

        def res(sid, window, cls, diff, session):
            return {
                "type": "RESOLUTION",
                "family": "FORM4_SHARP",
                "set_id": sid,
                "window": window,
                "coverage": cls,
                "status": "RESOLVED",
                "signal_session": session,
                "direction": 1,
                "candidate": {"trade": {"net_return": diff}},
                "paired": {
                    "candidate_net": diff,
                    "diff": diff,
                    "twins_mean_net": 0.0,
                    "twins_median_net": 0.0,
                },
                "cone": [{"id": "BEATS_TWINS_60", "outcome": diff > 0, "prior": 0.5}],
            }

        rs = [
            res("a", "H60", "FIRE", 0.05, "2026-10-29"),
            res("b", "H60", "FIRE", 0.03, "2026-10-30"),
            res("c", "H20", "FIRE", -0.5, "2026-10-29"),
            res("d", "H60", "ABSTAIN", -0.5, "2026-10-29"),
        ]
        st = cr.family_statistics("FORM4_SHARP", fsp, fsha, [], rs, rs)
        self.assertEqual(
            (st["window"], st["coverage_class"], st["MEAN"]["n_paired"]), ("H60", "FIRE", 2)
        )
        self.assertEqual(st["WIN_RATE"]["wins"], 2)
        self.assertEqual(st["descriptive"]["H20_FIRE"]["n_paired"], 1)
        self.assertEqual(st["descriptive"]["H60_ABSTAIN"]["n_paired"], 1)
        self.assertEqual(st["descriptive"]["entry_weeks"], 1)
        sets = [
            {
                "set_id": "a",
                "family": "FORM4_SHARP",
                "signal_session": "2026-10-29",
                "coverage": {
                    "class": "FIRE",
                    "reasons": [],
                    "inputs": {"pct_increase": {"max": 0.1}},
                },
            },
            {
                "set_id": "b",
                "family": "FORM4_SHARP",
                "signal_session": "2026-10-30",
                "coverage": {
                    "class": "FIRE",
                    "reasons": [],
                    "inputs": {"pct_increase": {"max": 0.5}},
                },
            },
            {
                "set_id": "e",
                "family": "FORM4_SHARP",
                "signal_session": "2026-10-30",
                "coverage": {
                    "class": "FIRE",
                    "reasons": [],
                    "inputs": {"pct_increase": {"max": 0.3}},
                },
            },
            {
                "set_id": "d",
                "family": "FORM4_SHARP",
                "signal_session": "2026-10-29",
                "coverage": {
                    "class": "ABSTAIN",
                    "reasons": ["ROUTINE"],
                    "inputs": {"pct_increase": {"max": None}},
                },
            },
        ]
        st = cr.family_statistics("FORM4_SHARP", fsp, fsha, sets, rs, rs)
        self.assertEqual(st["descriptive"]["split ONLY_RULE=ROUTINE"]["n_paired"], 1)
        self.assertEqual(st["descriptive"]["split PCT_INCREASE=low"]["n_paired"], 1)
        self.assertEqual(st["descriptive"]["split PCT_INCREASE=high"]["n_paired"], 1)
        old = cr.family_statistics("FORM4", *cr.family_protocol("FORM4"), [], [], [])
        self.assertEqual(
            (old["window"], old["coverage_class"], old["descriptive"]), ("H20", None, {})
        )


class VerifyChild(unittest.TestCase):
    def test_a_child_set_must_bind_its_parent_by_hash_and_sessions(self):
        """Guards against: a v2 set whose parent was edited, swapped, or sealed for another session."""
        scan = scan_record()
        fams = cr.extra_families()
        base = {
            "type": "CATALYST_SET",
            "market": "US",
            "ticker": "T00",
            "signal_session": SIGNAL,
            "scan_id": scan["scan_id"],
            "scan_record_hash": scan["record_hash"],
            "features_sha256": "f" * 64,
            "windows": {"H20": {}},
            "entry_cutoff": "2026-10-29T13:15:00Z",
            "sealed_at": "2026-10-28T22:50:00Z",
            "entry": {"session": "2026-10-29"},
        }
        batch = {
            "type": "BATCH",
            "sealed_at": "2026-10-28T22:50:00Z",
            "events": [{"status": "SEALED", "set_id": k} for k in ("CAT-P", "CAT-C1", "CAT-C2")],
        }
        recs = [
            {**batch, "family": "SEC13D", "protocol": {"sha256": cr.protocol()[1]}},
            {
                **base,
                "family": "SEC13D",
                "set_id": "CAT-P",
                "protocol": {"sha256": cr.protocol()[1]},
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalysts.jsonl"
            stored = paper.append(recs, path=path)
            good = {"set_id": "CAT-P", "record_hash": stored[1]["record_hash"]}
            child = {**base, "family": "SEC13D_V2", "protocol": {"sha256": fams["SEC13D_V2"][1]}}
            paper.append(
                [
                    {**batch, "family": "SEC13D_V2", "protocol": {"sha256": fams["SEC13D_V2"][1]}},
                    {**child, "set_id": "CAT-C1", "parent": good},
                    {**child, "set_id": "CAT-C2", "parent": {**good, "record_hash": "0" * 64}},
                ],
                path=path,
            )
            with (
                mock.patch.object(cr, "CAT_LEDGER", path),
                mock.patch.object(
                    paper,
                    "ledger_lines",
                    side_effect=lambda p=None: [scan] if p is None else json_lines(p),
                ),
                mock.patch.object(sp, "spec_lines", return_value=[]),
            ):
                joined = "\n".join(cr.verify())
        self.assertIn("CAT-C2: binds no earlier SEC13D set", joined)
        self.assertNotIn("CAT-C1", joined)
        self.assertNotIn("CAT-P", joined)


if __name__ == "__main__":
    unittest.main()
