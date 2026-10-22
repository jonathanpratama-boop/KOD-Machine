"""Adversarial correctness and provenance regressions for the analyst workstation."""

import json
import unittest

from kod import earnings
from tests.test_earnings import release, source, run


def tables(*documents):
    fragments = []
    for raw in documents:
        text = raw.decode()
        fragments.append(text[text.index("<table>"):text.index("</table>") + 8])
    return ("<html><body><p>Acme Announces Financial Results for Third Quarter Fiscal 2025</p>" + "".join(fragments) + "</body></html>").encode()


def prior(outlook=""):
    return source(release(title="Acme Announces Financial Results for Second Quarter Fiscal 2025", headers="Q2 FY25 | Q1 FY25 | Q2 FY24", outlook=outlook),
                  "prior.htm", "https://example.com/prior.htm", "2024-08-28T21:00:00Z")


OUTLOOK = '<p>Outlook Acme outlook for the third quarter of fiscal 2025:</p><p>Revenue is expected to be $100 million, plus or minus 5%.</p>'


def transposed(values):
    row = "".join(f"<td>{value}</td>" for value in values)
    return ("<html><p>Results for the quarter ended September 30, 2024</p><table>"
            "<tr><td>Three Months Ended September 30,</td></tr>"
            "<tr><td>($ in millions)</td><td>Revenue</td><td>Operating Income</td><td>Net Income</td><td>Diluted Earnings Per Share</td></tr>"
            f"<tr><td>2024 As Reported (GAAP)</td>{row}</tr>"
            "<tr><td>2023 As Reported (GAAP)</td><td>$56,517</td><td>$26,895</td><td>$22,291</td><td>$2.99</td></tr>"
            "</table></html>").encode()


class EarningsRepairTests(unittest.TestCase):
    def test_transposed_missing_empty_or_extra_values_never_shift_metrics(self):
        for values in (("$65,585", "$24,667", "$3.30"),
                       ("$65,585", "", "$24,667", "$3.30"),
                       ("$65,585", "$30,552", "$24,667", "$3.30", "$999")):
            with self.subTest(values=values):
                facts, issues = earnings.extract_table_facts(earnings.read_document(transposed(values)))
                self.assertEqual([f for f in facts if f["period"] == "quarter ended 2024-09-30"], [])
                self.assertIn("COLUMN_COUNT_MISMATCH", {i["code"] for i in issues})

    def test_valid_transposed_row_retains_all_four_correct_metrics(self):
        facts, _ = earnings.extract_table_facts(earnings.read_document(transposed(("$65,585", "$30,552", "$24,667", "$3.30"))))
        current = {f["metric"]: f["value"] for f in facts if f["period"] == "quarter ended 2024-09-30"}
        self.assertEqual(current, {"revenue": "65585", "operating_income": "30552", "net_income": "24667", "eps_diluted": "3.3"})

    def test_invalid_current_transposed_row_does_not_relabel_last_year_as_current(self):
        with self.assertRaises(earnings.EarningsError):
            run(source(transposed(("$65,585", "$24,667", "$3.30"))))

    def test_current_actual_conflict_blocks_only_affected_calculations_in_both_orders(self):
        for documents in ((release(rev="$110"), release(rev="$90")), (release(rev="$90"), release(rev="$110"))):
            with self.subTest(first=documents[0]):
                result = run(source(tables(*documents)), prior(OUTLOOK))
                self.assertEqual({f["value"] for f in result["facts"] if f["metric"] == "revenue"}, {"110", "90"})
                self.assertFalse([g for g in result["guidance_comparisons"] if g["metric"] == "revenue"])
                self.assertFalse([p for p in result["prior_period"] if p["metric"] == "revenue"])
                self.assertTrue([p for p in result["prior_period"] if p["metric"] == "eps_diluted"])
                self.assertTrue(any("conflict" in w["reason"].lower() for w in result["guidance_not_compared"]))

    def test_conflicting_prior_actual_does_not_produce_a_sequential_change(self):
        for documents in ((release(rev2="$100"), release(rev2="$95")), (release(rev2="$95"), release(rev2="$100"))):
            result = run(source(tables(*documents)))
            self.assertFalse([p for p in result["prior_period"] if p["metric"] == "revenue" and p["relation"] == "SEQUENTIAL"])
            self.assertTrue([p for p in result["prior_period"] if p["metric"] == "revenue" and p["relation"] == "YEAR_OVER_YEAR"])

    def test_conflicting_earlier_actual_does_not_fill_a_missing_sequential_comparison(self):
        current_facts, _ = earnings.extract_table_facts(earnings.read_document(release()))
        current_facts = [f for f in current_facts if f["period"] != "Q2 FY25"]
        earlier_facts, _ = earnings.extract_table_facts(earnings.read_document(tables(release(headers="Q2 FY25 | Q1 FY25 | Q2 FY24", rev="$100"), release(headers="Q2 FY25 | Q1 FY25 | Q2 FY24", rev="$90"))))
        rows = earnings.prior_period_comparisons(current_facts, "Q3 FY25", earlier_facts, "Q2 FY25")
        self.assertFalse([p for p in rows if p["metric"] == "revenue" and p["relation"] == "SEQUENTIAL"])

    def test_conflicting_guidance_ranges_are_withheld_in_either_order(self):
        guidance = ['<p>Revenue is expected to be $100 million, plus or minus 5%.</p>', '<p>Revenue is expected to be $200 million, plus or minus 5%.</p>']
        for lines in (guidance, list(reversed(guidance))):
            result = run(source(release()), prior('<p>Outlook Acme outlook for the third quarter of fiscal 2025:</p>' + "".join(lines)))
            self.assertFalse([g for g in result["guidance_comparisons"] if g["metric"] == "revenue"])
            self.assertTrue(any("conflict" in w["reason"].lower() for w in result["guidance_not_compared"]))
            self.assertNotIn("The company guides", " ".join(earnings.questions(result)))

    def test_same_value_with_different_units_is_not_deduplicated_or_compared(self):
        result = run(source(tables(release(), release(units="($ in thousands, except earnings per share)"))))
        revenue = [f for f in result["facts"] if f["metric"] == "revenue"]
        self.assertEqual({f["unit"] for f in revenue}, {"millions", "thousands"})
        for row in result["prior_period"]:
            self.assertEqual(row["unit"], row["evidence"][0]["unit"])
            self.assertEqual(row["unit"], row["evidence"][1]["unit"])

    def test_comparison_markdown_includes_document_and_exact_row_provenance(self):
        # Remove a comparative column from the source itself so sequential values
        # must come from the separate earlier release, not a modified result dict.
        raw = release().replace(b"<td>Q2 FY25</td>", b"").replace(b"<td>$100</td>", b"").replace(b"<td>48.0</td><td>%</td>", b"").replace(b"<td>$1.00</td>", b"")
        result = run(source(raw), prior(OUTLOOK))
        rows = [p for p in result["prior_period"] if p["source"].startswith("figure from")]
        self.assertTrue(rows)
        note = earnings.render_note(result)
        self.assertIn("| Source |", note)
        self.assertIn("figure from the comparison release", note)
        self.assertIn("(<https://example.com/prior.htm>)", note)
        for row in rows:
            self.assertEqual(row["evidence"][0]["source_url"], "https://example.com/rel.htm")
            self.assertEqual(row["evidence"][1]["source_url"], "https://example.com/prior.htm")
            self.assertIn("document_sha256", row["evidence"][1])

    def test_conflicting_eps_is_not_selected_for_analyst_questions(self):
        raw = tables(release(eps="$1.10"), release(eps="$9.99"), release(eps="$2.00", basis="NON-GAAP"))
        result = run(source(raw))
        self.assertFalse(any("Non-GAAP diluted EPS differs" in q for q in earnings.questions(result)))

    def test_conflicting_next_guidance_does_not_generate_a_selected_midpoint_question(self):
        outlook = OUTLOOK + '<p>Revenue is expected to be $200 million, plus or minus 5%.</p>'
        result = run(source(release(outlook=outlook)))
        self.assertEqual(len(result["next_guidance"]), 2)
        self.assertIn("GUIDANCE_CONFLICT", {i["code"] for i in result["issues"]})
        self.assertFalse(any("The company guides" in q for q in earnings.questions(result)))

    def test_zero_current_revenue_does_not_crash_the_analyst_questions(self):
        result = run(source(release(rev="$0", outlook=OUTLOOK)))
        self.assertIsInstance(earnings.questions(result), list)
        self.assertFalse(any("against the quarter just reported" in q for q in earnings.questions(result)))

    def test_future_comparison_conflict_diagnostics_do_not_leak_into_cutoff_output(self):
        future = prior()
        future["doc"] = earnings.read_document(tables(release(rev="$991234"), release(rev="$889876")), "prior.htm")
        future["published_at"] = "2024-11-21T21:00:00Z"
        result = run(source(release()), future)
        self.assertFalse(result["comparison_issues"])
        self.assertNotIn("991234", json.dumps(result))
        self.assertNotIn("889876", json.dumps(result))

    def test_cutoff_excluded_headline_and_conflict_figures_are_not_in_structured_note(self):
        raw = tables(release(rev="$991234"), release(rev="$889876")).replace(b"<body>", b"<body><p>SECRET_FUTURE_EARNINGS revenue for the quarter ended October 27, 2024 was $991234 million.</p>")
        result = run(source(raw), as_of="2024-11-20T20:00:00Z")
        serialized = json.dumps(result)
        self.assertNotIn("SECRET_FUTURE_EARNINGS", serialized)
        self.assertNotIn('"991234"', serialized)
        self.assertNotIn('"889876"', serialized)
        self.assertEqual(result["facts"], [])


if __name__ == "__main__":
    unittest.main()
