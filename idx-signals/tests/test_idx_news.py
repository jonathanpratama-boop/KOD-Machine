import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1] / "research" / "IDX_INSIDER_NEWS"
sys.path.insert(0, str(BASE))


def load(name):
    spec = importlib.util.spec_from_file_location(f"idxnews_{name}", BASE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


collect, sample, score, batches = load("collect_labels"), load("audit_sample"), load("audit_score"), load("make_batches")


def labels(n_ins=60, n_oth=80):
    rows = [{"item": i, "cls": "INSIDER_BUY", "issuer_ticker": f"A{chr(65 + i % 26)}{chr(65 + i % 7)}{chr(65 + i % 5)}", "confidence": "high"} for i in range(n_ins)]
    rows += [{"item": n_ins + j, "cls": ["SELL", "OTHER", "MARKET_FLOW", "OUTSIDE_INVESTOR_BUY"][j % 4], "issuer_ticker": None, "confidence": "medium"}
             for j in range(n_oth)]
    return pd.DataFrame(rows)


class CollectTests(unittest.TestCase):
    def write(self, tmp, name, rows):
        (Path(tmp) / name).write_text(json.dumps(rows))

    def test_valid_batches_merge_and_cover_everything(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, "labels_batch_000.json", [{"item": 1, "cls": "INSIDER_BUY", "issuer_ticker": "BBCA", "buyer": "x", "transaction_date": None, "confidence": "high"}])
            self.write(tmp, "labels_batch_001.json", [{"item": 2, "cls": "SELL", "issuer_ticker": None, "buyer": "y", "transaction_date": "9 Mei 2022", "confidence": "low"}])
            df = collect.merge(Path(tmp), expected={1, 2})
            self.assertEqual(list(df.item), [1, 2])

    def test_bad_class_duplicate_missing_and_ticker_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, "labels_batch_000.json", [
                {"item": 1, "cls": "INSIDER", "issuer_ticker": "BBCA", "confidence": "high"},
                {"item": 2, "cls": "SELL", "issuer_ticker": "bbca", "confidence": "high"},
                {"item": 2, "cls": "SELL", "issuer_ticker": None, "confidence": "high"}])
            with self.assertRaises(ValueError) as cm:
                collect.merge(Path(tmp), expected={1, 2, 3})
            msg = str(cm.exception)
            for part in ("bad class", "bad ticker", "answered twice", "not answered"):
                self.assertIn(part, msg)


class AuditTests(unittest.TestCase):
    def test_sample_is_45_and_45_and_reproducible(self):
        a, b = sample.draw(labels()), sample.draw(labels())
        pd.testing.assert_frame_equal(a, b)
        self.assertEqual((a.cls == "INSIDER_BUY").sum(), 45)
        self.assertEqual((a.cls != "INSIDER_BUY").sum(), 45)
        self.assertEqual(sorted(a.audit_item), list(range(1, 91)))

    def answers(self, key, wrong_ins=0, missed=0, wrong_ticker=0):
        rows, w, mi, wt = [], 0, 0, 0
        for r in key.itertuples():
            cls, tk = r.cls, r.issuer_ticker
            if r.cls == "INSIDER_BUY":
                if w < wrong_ins:
                    cls, w = "OTHER", w + 1
                elif wt < wrong_ticker:
                    tk, wt = "ZZZZ", wt + 1
            elif mi < missed:
                cls, tk, mi = "INSIDER_BUY", "ABCD", mi + 1
            rows.append({"item": int(r.audit_item), "cls": cls, "issuer_ticker": tk})
        return pd.DataFrame(rows).rename(columns={"item": "audit_item"})

    def test_precision_is_the_lower_reviewers_and_gates_go(self):
        key = sample.draw(labels())[["audit_item", "item", "cls", "issuer_ticker", "confidence"]]
        res = score.score(key, [("A", self.answers(key, wrong_ins=4)), ("B", self.answers(key, wrong_ins=2, wrong_ticker=1))])
        self.assertAlmostEqual(res["reviewers"][0]["precision"], 41 / 45)
        self.assertAlmostEqual(res["reviewers"][1]["precision"], 42 / 45)
        self.assertAlmostEqual(res["lower_precision"], 41 / 45)
        self.assertTrue(res["audit_go"])
        bad = score.score(key, [("A", self.answers(key, wrong_ins=9)), ("B", self.answers(key))])
        self.assertAlmostEqual(bad["lower_precision"], 36 / 45)
        self.assertFalse(bad["audit_go"])

    def test_missed_share_and_kappa(self):
        key = sample.draw(labels())[["audit_item", "item", "cls", "issuer_ticker", "confidence"]]
        res = score.score(key, [("A", self.answers(key, missed=9)), ("B", self.answers(key))])
        self.assertAlmostEqual(res["reviewers"][0]["missed_share_among_others"], 9 / 45)
        self.assertAlmostEqual(res["reviewers"][1]["kappa_vs_labeller"], 1.0)
        self.assertLess(res["kappa_between_reviewers"], 1.0)

    def test_an_unanswered_item_is_an_error(self):
        key = sample.draw(labels())[["audit_item", "item", "cls", "issuer_ticker", "confidence"]]
        with self.assertRaises(ValueError):
            score.score(key, [("A", self.answers(key).iloc[:-1]), ("B", self.answers(key))])


class BatchTests(unittest.TestCase):
    def test_items_drop_failed_and_cut_the_body(self):
        df = pd.DataFrame([{"failed": False, "title": "t1", "posted_wib": "2022-05-13T06:45:00+07:00", "body_head": "x" * 900},
                           {"failed": True, "title": None, "posted_wib": None, "body_head": None},
                           {"failed": False, "title": "t3", "posted_wib": None, "body_head": "y"}])
        its = batches.items(df)
        self.assertEqual(len(its), 1)
        self.assertEqual(its[0]["posted_wib"], "2022-05-13 06:45")
        self.assertEqual(len(its[0]["body"]), 700)


if __name__ == "__main__":
    unittest.main()
