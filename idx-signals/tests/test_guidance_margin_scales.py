import unittest
from decimal import Decimal
from idxsig import guidance_margin_facts as facts
from idxsig import guidance_margin_reader as reader


class SourceUnitTests(unittest.TestCase):
    def evaluate(self, raw, tokens, unit):
        metric = {"unit": unit, "qualifier": "exact", **dict.fromkeys(reader._SLOTS)}
        slots = ("low", "high") if len(tokens) == 2 else ("point",)
        metric["form"] = "range" if len(tokens) == 2 else "point"
        for slot, token in zip(slots, tokens):
            metric[slot] = {"quote": raw, "token": token}
        bound = reader._bind_metric(metric, raw)
        audit = facts._Review()
        value = facts._metric(bound, raw, "USD_MILLIONS", "revenue", audit)
        return value, any(audit.issues.values())

    def test_table_units_and_shared_range(self):
        for raw, tokens, unit, value in [
            ("Revenue: $5.20B to $5.21B", ["$5.20B", "$5.21B"], "USD_BILLIONS", "5205"),
            ("Profit: $940M to $960M", ["$940M", "$960M"], "USD_MILLIONS", "950"),
            ("Sales of $83.5 to $84.5 billion", ["$83.5", "$84.5"], "USD_BILLIONS", "84000"),
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(self.evaluate(raw, tokens, unit), (Decimal(value), False))

    def test_wrong_absent_or_mixed_scale_is_flagged(self):
        for raw, tokens, unit in [
            ("Revenue: $5.20B", ["$5.20"], "USD_MILLIONS"),
            ("Revenue: $1M to $2B", ["$1M", "$2B"], "USD_BILLIONS"),
            ("Revenue: $1 or other segment: $2B", ["$1", "$2B"], "USD_BILLIONS"),
            ("Revenue: $55", ["$55"], "USD_BILLIONS"),
        ]:
            with self.subTest(raw=raw):
                self.assertTrue(self.evaluate(raw, tokens, unit)[1])
