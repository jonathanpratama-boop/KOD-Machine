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
        self.assertEqual(
            len(sessions) - 1 - 18, 21
        )  # entry on the next session + 20 more still fits before the end

    def test_the_index_drops_rows_before_the_first_date_unseen(self):
        fi = load("fetch_index")
        body = (
            "<urlset>"
            "<url><loc>https://www.emitennews.com/news/a-old</loc><lastmod>2025-02-20</lastmod></url>"
            "<url><loc>https://www.emitennews.com/news/b-first</loc><lastmod>2025-03-03</lastmod></url>"
            "<url><loc>https://www.emitennews.com/news/c-later</loc><lastmod>2025-09-01T10:00:00+07:00</lastmod></url>"
            "<url><loc>https://www.emitennews.com/tag/d-not-news</loc><lastmod>2025-09-01</lastmod></url>"
            "</urlset>"
        )
        rows = fi.parse(body)
        self.assertEqual([r["slug"] for r in rows], ["b-first", "c-later"])
        self.assertEqual(rows[1]["date"], "2025-09-01")


class EventTableTests(unittest.TestCase):
    def setUp(self):
        self.tools = load("tools")
        self.articles = pd.DataFrame(
            {
                "url": [f"u{i}" for i in range(6)],
                "title": [f"t{i}" for i in range(6)],
                "html_sha256": ["h"] * 6,
                "posted_wib": [
                    "2025-02-28T10:00:00+07:00",
                    "2025-03-03T09:00:00+07:00",
                    "2025-06-01T10:00:00+07:00",
                    "2026-09-07T23:00:00+07:00",
                    "2026-09-08T09:00:00+07:00",
                    "2025-07-01T10:00:00+07:00",
                ],
                "body_head": ["b"] * 6,
                "failed": [False] * 6,
            }
        )
        self.labels = pd.DataFrame(
            {
                "item": range(6),
                "cls": ["INSIDER_BUY"] * 5 + ["SELL"],
                "issuer_ticker": ["AAAA", "BBBB", "CCCC", "DDDD", "EEEE", "FFFF"],
                "buyer": ["x"] * 6,
                "transaction_date": [None] * 6,
                "confidence": ["high", "high", "low", "medium", "high", "high"],
            }
        )

    def test_events_are_inside_the_window_confident_and_insider_buys(self):
        ev = self.tools.build_events(self.labels, self.articles)
        self.assertEqual(
            list(ev.ticker), ["BBBB", "DDDD"]
        )  # before FIRST, low confidence, after LAST and a SELL are all out

    def test_labelling_items_are_inside_the_window(self):
        its = self.tools.window_items(self.articles)
        self.assertEqual(sorted(it["item"] for it in its), [1, 2, 3, 5])


if __name__ == "__main__":
    unittest.main()


class GateTests(unittest.TestCase):
    def setUp(self):
        self.st = load("oot_stats")

    def frame(self, per_year):
        rows = []
        for year, (n, ex) in per_year.items():
            rows += [
                {
                    "posted_wib": f"{year}-05-0{1 + i % 9}T10:00:00+07:00",
                    "excess": ex,
                    "net_return": ex,
                }
                for i in range(n)
            ]
        return pd.DataFrame(rows)

    def stats(self, **kw):
        base = {
            "mean_excess": 0.02,
            "t_excess": 2.0,
            "mean_net": 0.01,
            "winsorised_net": 0.01,
            "mean_net_extra_cost": 0.002,
        }
        return {**base, **kw}

    def test_g1_is_the_one_sided_five_percent_line(self):
        f = self.frame({"2025": (30, 0.01), "2026": (30, 0.01)})
        self.assertFalse(self.st.gates(f, self.stats(t_excess=1.649))[0][self.st.G1])
        self.assertTrue(self.st.gates(f, self.stats(t_excess=1.65))[0][self.st.G1])
        self.assertFalse(
            self.st.gates(f, self.stats(t_excess=3.0, mean_excess=-0.001))[0][self.st.G1]
        )

    def test_years_with_fewer_than_20_events_do_not_count_for_g3(self):
        ok = self.frame({"2025": (30, 0.02), "2026": (10, -0.05)})
        self.assertTrue(self.st.gates(ok, self.stats())[0][self.st.G3])
        bad = self.frame({"2025": (30, 0.02), "2026": (25, -0.05)})
        self.assertFalse(self.st.gates(bad, self.stats())[0][self.st.G3])

    def test_the_reading_follows_the_protocol_in_order(self):
        f = self.frame({"2025": (30, 0.01), "2026": (30, 0.01)})
        g, _ = self.st.gates(f, self.stats(t_excess=2.4))
        self.assertEqual(self.st.reading(g, self.stats(t_excess=2.4)), "PASS")
        s = self.stats(t_excess=2.4, mean_net_extra_cost=-0.004)
        self.assertEqual(
            self.st.reading(self.st.gates(f, s)[0], s),
            "G1_HOLDS_G4_FAILS_TOO_SMALL_AFTER_FRICTIONS",
        )
        s = self.stats(t_excess=1.2)
        self.assertEqual(self.st.reading(self.st.gates(f, s)[0], s), "LEAN_WITHOUT_POWER")
        s = self.stats(t_excess=0.9)
        self.assertEqual(self.st.reading(self.st.gates(f, s)[0], s), "NO_SIGN_IT_PERSISTED")
        s = self.stats(t_excess=2.0, mean_excess=-0.01)
        self.assertEqual(self.st.reading(self.st.gates(f, s)[0], s), "NO_SIGN_IT_PERSISTED")

    def test_pooling_weights_by_precision(self):
        a = {
            "mean_excess": 0.03,
            "lo95_excess": 0.03 - 1.96 * 0.01,
            "hi95_excess": 0.03 + 1.96 * 0.01,
        }
        b = {"mean_excess": 0.00, "lo95_excess": -1.96 * 0.02, "hi95_excess": 1.96 * 0.02}
        p = self.st.pooled(a, b)
        self.assertAlmostEqual(p["weights"]["discovery"], 0.8)
        self.assertAlmostEqual(p["mean_excess"], 0.024)
        self.assertAlmostEqual(p["se"], (1 / (1 / 0.01**2 + 1 / 0.02**2)) ** 0.5)

    def test_tail_shares(self):
        f = pd.DataFrame({"excess": [10.0] + [1.0] * 19 + [-1.0] * 10})
        t = self.st.tail(f)
        self.assertAlmostEqual(t["top5_share_of_total_excess"], 14 / 19)
        self.assertAlmostEqual(t["mean_excess_without_top10"], 0.0)  # ten +1 and ten -1 remain
        self.assertAlmostEqual(t["share_excess_positive"], 20 / 30)
