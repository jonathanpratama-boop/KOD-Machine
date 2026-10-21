import gzip
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd

from idxsig import microstructure as ms
from idxsig import paper

DAY_START = 20_000 * ms.DAY            # an exact UTC midnight (2024-10-04)
N_ALL = (ms.DAY + ms.POST_MS) // ms.MINUTE


class BookTests(unittest.TestCase):
    ASKS = [(100.0, 1.0), (101.0, 2.0)]
    BIDS = [(99.0, 1.0), (98.0, 2.0)]
    MID = 99.5

    def test_buy_inside_first_level(self):
        f = ms.book_fill(self.ASKS, 100.0, self.MID, "buy")
        self.assertTrue(f["complete"])
        self.assertAlmostEqual(f["vwap"], 100.0)
        self.assertAlmostEqual(f["slippage_bps"], (100.0 / 99.5 - 1) * 1e4, places=2)

    def test_buy_walks_two_levels(self):
        f = ms.book_fill(self.ASKS, 200.0, self.MID, "buy")
        units = 1.0 + 100.0 / 101.0
        self.assertAlmostEqual(f["vwap"], 200.0 / units)
        self.assertAlmostEqual(f["slippage_bps"], (200.0 / units / 99.5 - 1) * 1e4, places=2)

    def test_buy_too_big_is_flagged_not_hidden(self):
        f = ms.book_fill(self.ASKS, 1000.0, self.MID, "buy")           # the book holds 100 + 202 = 302
        self.assertFalse(f["complete"])
        self.assertAlmostEqual(f["filled_fraction"], 0.302, places=6)

    def test_sell_walks_two_levels(self):
        f = ms.book_fill(self.BIDS, 199.0, self.MID, "sell")           # 2 units at the mid
        self.assertTrue(f["complete"])
        self.assertAlmostEqual(f["vwap"], (99.0 + 98.0) / 2)
        self.assertAlmostEqual(f["slippage_bps"], (1 - 98.5 / 99.5) * 1e4, places=2)

    def test_unknown_side_rejected(self):
        with self.assertRaises(ValueError):
            ms.book_fill(self.ASKS, 10.0, self.MID, "hold")

    def test_depth_within(self):
        self.assertAlmostEqual(ms.depth_within(self.ASKS, self.MID, 0.0101), 100.0)
        self.assertAlmostEqual(ms.depth_within(self.ASKS, self.MID, 0.02), 100.0 + 202.0)

    def test_metrics(self):
        raw = {"bids": [["99", "1"], ["98", "2"], ["97", "0"]], "asks": [["100", "1"], ["101", "2"]]}
        m = ms.book_metrics(raw, sizes=(100.0, 100.0, 250.0))
        self.assertAlmostEqual(m["mid"], 99.5)
        self.assertAlmostEqual(m["spread_bps"], 1 / 99.5 * 1e4, places=2)
        self.assertEqual(m["levels"], [2, 2])                          # the zero-quantity level is dropped
        self.assertEqual(sorted(m["fills"]), ["100", "250"])
        self.assertTrue(m["fills"]["100"]["buy"]["complete"])
        self.assertIsNone(ms.book_metrics({"bids": [], "asks": [["1", "1"]]}))


def synthetic_bars(first_minute=-360, drop=(), post_step_at=1500):
    """Previous close 100 at the minute before the day. Day: flat 100 until minute 720, then 125; one spike high of 130
    at minute 900. After the day: 125 for the first hour, 150 from there."""
    rows = []
    for m in range(first_minute, N_ALL):
        if m in drop:
            continue
        if m < 0:
            c = 100.0
        elif m < 720:
            c = 100.0
        elif m < 1440 + 60:
            c = 125.0
        else:
            c = 150.0
        h = 130.0 if m == 900 else c
        rows.append([DAY_START + m * ms.MINUTE, c, h, c, c, 10.0, 10.0 * c, 1])
    return pd.DataFrame(rows, columns=["t", "o", "h", "l", "c", "v", "qv", "n"])


class TimelineTests(unittest.TestCase):
    def test_metrics(self):
        bars = synthetic_bars()
        m = ms.timeline_metrics(bars, DAY_START, DAY_START + ms.DAY + ms.POST_MS)
        self.assertTrue(m["base_is_previous_close"])
        self.assertAlmostEqual(m["ret_day"], 0.25)
        self.assertAlmostEqual(m["peak_ret"], 0.30)
        self.assertEqual(m["peak_minute"], 900)
        self.assertAlmostEqual(m["giveback_from_peak"], 125 / 130 - 1)
        self.assertEqual(m["cross_minute"], {"10": 720, "20": 720, "30": None})   # closes only, never the spike high
        self.assertAlmostEqual(m["ret_last_1h"], 0.0)
        self.assertAlmostEqual(m["post_close_ret"]["60m"], 0.0)
        self.assertAlmostEqual(m["post_close_ret"]["240m"], 0.2)
        self.assertAlmostEqual(m["post_close_ret"]["1440m"], 0.2)
        self.assertEqual(m["minutes_with_trades"], 1440)
        self.assertAlmostEqual(m["volume_share_last_1h"], 60 * 1250.0 / sum(
            10.0 * (100.0 if k < 720 else 125.0) for k in range(1440)))

    def test_horizons_are_never_extrapolated(self):
        bars = synthetic_bars()
        m = ms.timeline_metrics(bars, DAY_START, DAY_START + ms.DAY + 100 * ms.MINUTE)
        self.assertAlmostEqual(m["post_close_ret"]["60m"], 0.0)
        self.assertIsNone(m["post_close_ret"]["240m"])
        self.assertIsNone(m["post_close_ret"]["1440m"])

    def test_gaps_carry_the_last_close_and_count_as_no_trade(self):
        gap = set(range(1000, 1101))
        m = ms.timeline_metrics(synthetic_bars(drop=gap), DAY_START, DAY_START + ms.DAY + ms.POST_MS)
        self.assertEqual(m["minutes_with_trades"], 1440 - 101)
        self.assertAlmostEqual(m["ret_day"], 0.25)

    def test_no_previous_bar_falls_back_to_the_day_open(self):
        m = ms.timeline_metrics(synthetic_bars(first_minute=0), DAY_START, DAY_START + ms.DAY + ms.POST_MS)
        self.assertFalse(m["base_is_previous_close"])
        self.assertAlmostEqual(m["ret_day"], 0.25)

    def test_empty_day(self):
        bars = synthetic_bars(first_minute=-360)
        bars = bars[bars["t"] < DAY_START]
        self.assertIn("error", ms.timeline_metrics(bars, DAY_START, DAY_START + ms.DAY + ms.POST_MS))


def fake_get(depth, bars):
    """Stand-in for the network: server time, one depth response and klines cut from `bars` by the query."""

    def _get(url, retries=3, timeout=25):
        u = urlparse(url)
        q = parse_qs(u.query)
        if u.path.endswith("/time"):
            return {"serverTime": 1_700_000_000_000}
        if u.path.endswith("/depth"):
            return depth
        if u.path.endswith("/klines"):
            lo, hi = int(q["startTime"][0]), int(q["endTime"][0])
            sel = bars[(bars["t"] >= lo) & (bars["t"] <= hi)].head(int(q["limit"][0]))
            return [[int(r.t), str(r.o), str(r.h), str(r.l), str(r.c), str(r.v), int(r.t) + 59_999, str(r.qv), int(r.n),
                     "0", "0", "0"] for r in sel.itertuples()]
        raise AssertionError(url)

    return _get


class SidecarTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        self.ledger, self.sidecar = self.tmp / "ledger.jsonl", self.tmp / "crypto.jsonl"
        self.scan_id = "SCAN-CRYPTO-2024-10-04-G2_RET30"
        decision = {"type": "DECISION", "scan_id": self.scan_id, "decision_id": self.scan_id + "-ABC",
                    "instrument": {"pair": "ABCUSDT", "ticker": "ABC"}, "decided_at": "2024-10-05T00:25:24Z",
                    "signal_session": "2024-10-04", "verified_price": {"close": 125.0, "quote": 126.0},
                    "plan": {"costs_per_side": [0.002, 0.002],
                             "scenarios": [{"position_usdt": 389.886}, {"position_usdt": 779.773}]}}
        paper.append([{"type": "SCAN", "market": "CRYPTO", "scan_id": self.scan_id, "session": "2024-10-04"}, decision], path=self.ledger)
        self.depth = {"bids": [["99", "50"], ["98", "100"]], "asks": [["100", "50"], ["101", "100"]]}
        self.patches = [mock.patch.object(ms, "RAW", self.tmp / "raw"), mock.patch.object(ms, "rel", lambda p: str(p)),
                        mock.patch.object(ms, "_get", fake_get(self.depth, synthetic_bars(first_minute=-360)))]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def run_scan(self, **kw):
        return ms.run_for_scan(self.scan_id, ledger=self.ledger, sidecar=self.sidecar, **kw)

    def test_records_chain_and_hash(self):
        written = self.run_scan()
        recs = paper.ledger_lines(self.sidecar)
        self.assertEqual([r["type"] for r in recs], ["BOOK", "TIMELINE"])
        self.assertEqual(ms.verify(self.sidecar), [])
        self.assertIn(self.sidecar, written)
        book, tl = recs
        self.assertEqual(book["plan_sizes_usdt"], [389.89, 779.77])
        self.assertIn("389.89", book["book"]["fills"])
        self.assertAlmostEqual(book["assumed_cost_per_side"], 0.002)
        self.assertGreater(book["offset_s"], 0)                              # taken now, decided in 2024: long after
        self.assertTrue(tl["retrospective"])
        self.assertAlmostEqual(tl["metrics"]["ret_day"], 0.25)
        with gzip.open(book["raw"]["path"], "rt") as fh:
            self.assertEqual(json.load(fh), self.depth)

    def test_rerun_adds_nothing(self):
        self.run_scan()
        n = len(paper.ledger_lines(self.sidecar))
        self.assertEqual(self.run_scan(), [])
        self.assertEqual(len(paper.ledger_lines(self.sidecar)), n)

    def test_backfill_skips_books(self):
        self.run_scan(books=False)
        self.assertEqual([r["type"] for r in paper.ledger_lines(self.sidecar)], ["TIMELINE"])

    def test_catch_up_waits_for_the_full_path_and_never_takes_a_book(self):
        day_end = datetime(2024, 10, 5, tzinfo=timezone.utc)
        too_early = day_end + timedelta(hours=ms.TIMELINE_AFTER_H) - timedelta(minutes=1)
        self.assertEqual(ms.catch_up(too_early, self.ledger, self.sidecar), [])
        self.assertEqual(paper.ledger_lines(self.sidecar), [])
        written = ms.catch_up(day_end + timedelta(hours=ms.TIMELINE_AFTER_H), self.ledger, self.sidecar)
        recs = paper.ledger_lines(self.sidecar)
        self.assertEqual([r["type"] for r in recs], ["TIMELINE"])
        self.assertIn(self.sidecar, written)
        self.assertFalse(recs[0]["retrospective"])                         # built a day after the decision
        self.assertAlmostEqual(recs[0]["metrics"]["post_close_ret"]["1440m"], 0.2)
        self.assertEqual(ms.catch_up(day_end + timedelta(days=9), self.ledger, self.sidecar), [])

    def test_timelines_can_be_left_for_later(self):
        self.run_scan(timelines=False)
        self.assertEqual([r["type"] for r in paper.ledger_lines(self.sidecar)], ["BOOK"])

    def test_tampering_is_detected(self):
        self.run_scan()
        raw = Path(paper.ledger_lines(self.sidecar)[0]["raw"]["path"])
        raw.write_bytes(raw.read_bytes() + b"x")
        self.assertTrue(any("does not match" in p for p in ms.verify(self.sidecar)))
        lines = self.sidecar.read_text().splitlines()
        self.sidecar.write_text(lines[0].replace('"offset_s"', '"offset_x"') + "\n" + "\n".join(lines[1:]) + "\n")
        self.assertTrue(any("record_hash" in p for p in ms.verify(self.sidecar)))

    def test_a_rate_limit_stops_the_book_without_a_record(self):
        def limited(url, retries=3, timeout=25):
            raise RuntimeError("rate limited by Binance (HTTP 429)")

        with mock.patch.object(ms, "_get", limited):
            self.assertEqual(self.run_scan(), [])
        self.assertEqual(paper.ledger_lines(self.sidecar), [])

    def test_only_crypto_scans(self):
        with self.assertRaises(ValueError):
            ms.scan_decisions("SCAN-2026-10-20-F1_ARA", self.ledger)

    def test_summary(self):
        self.run_scan()
        # the book was taken years after the decision: counted as recorded, not as a decision-time book
        s = ms.summarize(self.sidecar)
        self.assertEqual(s["books"]["recorded"], 1)
        self.assertEqual(s["books"]["at_decision_time"], 0)
        self.assertEqual(s["timelines"]["recorded"], 1)
        self.assertAlmostEqual(s["timelines"]["ret_day"]["median"], 0.25)
        self.assertEqual(s["timelines"]["minute_of_first_30pct_close"]["n"], 0)
        recs = paper.ledger_lines(self.sidecar)
        recs[0]["offset_s"] = 12.0
        self.sidecar.write_text("".join(json.dumps(r) + "\n" for r in recs))
        s = ms.summarize(self.sidecar)
        self.assertEqual(s["books"]["at_decision_time"], 1)
        self.assertIsNotNone(s["books"]["by_size_usdt"]["1000"]["buy"]["n"])


if __name__ == "__main__":
    unittest.main()
