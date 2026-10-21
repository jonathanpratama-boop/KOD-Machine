import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

OOT = Path(__file__).resolve().parents[1] / "research" / "IDX_INSIDER_NEWS_OOT"


def load(name):
    if str(OOT) not in sys.path:
        sys.path.insert(0, str(OOT))
    spec = importlib.util.spec_from_file_location(f"idxnews_oot_{name}", OOT / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class WindowTests(unittest.TestCase):
    def test_the_last_posting_date_is_the_22nd_last_session(self):
        common = load("oot_common")
        sessions = np.busday_offset(np.datetime64("2026-08-03", "D"), np.arange(40), roll="forward")
        self.assertEqual(common.last_posting_date(sessions), str(sessions[18]))
        self.assertEqual(len(sessions) - 1 - 18, 21)                 # entry on the next session + 20 more still fits before the end

    def test_the_index_drops_rows_before_the_first_date_unseen(self):
        fi = load("fetch_index")
        body = ("<urlset>"
                "<url><loc>https://www.emitennews.com/news/a-old</loc><lastmod>2025-02-20</lastmod></url>"
                "<url><loc>https://www.emitennews.com/news/b-first</loc><lastmod>2025-03-03</lastmod></url>"
                "<url><loc>https://www.emitennews.com/news/c-later</loc><lastmod>2025-09-01T10:00:00+07:00</lastmod></url>"
                "<url><loc>https://www.emitennews.com/tag/d-not-news</loc><lastmod>2025-09-01</lastmod></url>"
                "</urlset>")
        rows = fi.parse(body)
        self.assertEqual([r["slug"] for r in rows], ["b-first", "c-later"])
        self.assertEqual(rows[1]["date"], "2025-09-01")


class EventTableTests(unittest.TestCase):
    def setUp(self):
        self.tools = load("tools")
        self.articles = pd.DataFrame({
            "url": [f"u{i}" for i in range(6)], "title": [f"t{i}" for i in range(6)], "html_sha256": ["h"] * 6,
            "posted_wib": ["2025-02-28T10:00:00+07:00", "2025-03-03T09:00:00+07:00", "2025-06-01T10:00:00+07:00", "2026-09-07T23:00:00+07:00",
                           "2026-09-08T09:00:00+07:00", "2025-07-01T10:00:00+07:00"],
            "body_head": ["b"] * 6, "failed": [False] * 6})
        self.labels = pd.DataFrame({
            "item": range(6), "cls": ["INSIDER_BUY"] * 5 + ["SELL"], "issuer_ticker": ["AAAA", "BBBB", "CCCC", "DDDD", "EEEE", "FFFF"],
            "buyer": ["x"] * 6, "transaction_date": [None] * 6, "confidence": ["high", "high", "low", "medium", "high", "high"]})

    def test_events_are_inside_the_window_confident_and_insider_buys(self):
        ev = self.tools.build_events(self.labels, self.articles)
        self.assertEqual(list(ev.ticker), ["BBBB", "DDDD"])          # before FIRST, low confidence, after LAST and a SELL are all out

    def test_labelling_items_are_inside_the_window(self):
        its = self.tools.window_items(self.articles)
        self.assertEqual(sorted(it["item"] for it in its), [1, 2, 3, 5])


if __name__ == "__main__":
    unittest.main()
