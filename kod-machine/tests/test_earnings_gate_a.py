"""Gate A of the Company Decision Dossier: the earnings reader must not mislabel periods, durations or currencies.

The three synthetic releases below are the build instruction's diagnostic appendix. Before this repair the reader called Q3 2024 a prior period of Q3 2023 (column order
decided the current period), read an annual figure as quarterly (column spans were ignored) and labelled Canadian-dollar amounts as US dollars. The assertions state the
corrected behaviour, not the earlier output. The metamorphic tests check that harmless changes to a table (column order, a split currency cell, an unrelated annual
table, whitespace) do not change what is read.
"""

import json
import unittest
from unittest import mock

from kod import earnings
from tests.test_earnings import release, source, run

ASCENDING = b"""<html><body><h1>Acme third-quarter 2024 results</h1>
<p>GAAP</p><p>Amounts in millions</p><table>
<tr><td></td><td>Q3 2023</td><td>Q3 2024</td></tr>
<tr><td>Revenue</td><td>$100</td><td>$120</td></tr>
<tr><td>Diluted earnings per share</td><td>$1.00</td><td>$1.20</td></tr>
</table></body></html>"""

UNEQUAL = b"""<html><body><h1>Acme financial results</h1>
<p>GAAP</p><p>Amounts in millions</p><table>
<tr><td></td><th colspan="1">Three Months Ended</th><th colspan="3">Twelve Months Ended</th></tr>
<tr><td></td><td>September 30, 2024</td><td>December 31, 2023</td><td>December 31, 2022</td><td>December 31, 2021</td></tr>
<tr><td>Revenue</td><td>$120</td><td>$400</td><td>$350</td><td>$300</td></tr>
</table></body></html>"""

CAD = b"""<html><body><h1>Acme third-quarter 2024 results</h1>
<p>GAAP</p><p>All amounts are in Canadian dollars, in millions except per-share amounts.</p><table>
<tr><td></td><td>Q3 2024</td><td>Q3 2023</td></tr>
<tr><td>Revenue</td><td>$120</td><td>$100</td></tr>
<tr><td>Diluted earnings per share</td><td>$1.20</td><td>$1.00</td></tr>
</table></body></html>"""


def facts_of(raw):
    return earnings.extract_table_facts(earnings.read_document(raw, "t.htm"))


def by_period(facts, metric="revenue"):
    return {f["period"]: f["value"] for f in facts if f["metric"] == metric}


def semantic(result):
    """What an analyst reads from a note, independent of table numbering and quotes."""
    return {
        "period": result["period"],
        "facts": sorted(
            (f["metric"], f["basis"], f["period"], f["value"], f["unit"], f["currency"])
            for f in result["facts"]
        ),
        "prior": sorted(
            (
                p["metric"],
                p["basis"],
                p["prior_period"],
                p["relation"],
                p["actual"],
                p["prior_actual"],
                p["difference_pct"],
            )
            for p in result["prior_period"]
        ),
    }


def spanned(columns, title="Acme Reports Third Quarter 2024 Financial Results", extra_table=""):
    """An SEC-style table: each period heading spans three columns ('$', number, padding), as generated filings print them. columns: [(label, revenue, eps)]."""
    head = "".join(f'<td colspan="3">{label}</td>' for label, _, _ in columns)
    rev = "".join(f"<td>$</td><td>{r}</td><td></td>" for _, r, _ in columns)
    eps = "".join(f"<td>$</td><td>{e}</td><td></td>" for _, _, e in columns)
    return (
        f"<html><body><p>{title}</p><p>(in millions, except per share amounts)</p><table>"
        f'<tr><td colspan="2"></td>{head}</tr>'
        f'<tr><td colspan="2">Revenue</td>{rev}</tr>'
        f'<tr><td colspan="2">Diluted earnings per share</td>{eps}</tr>'
        f"</table>{extra_table}</body></html>"
    ).encode()


QUARTERS = [
    ("Q3 2024", "6,819", "0.47"),
    ("Q2 2024", "5,835", "0.16"),
    ("Q3 2023", "5,800", "0.18"),
]


class AppendixRegressionTests(unittest.TestCase):
    def test_ascending_columns_report_q3_2024_and_compare_it_with_q3_2023(self):
        result = run(source(ASCENDING))
        self.assertEqual(result["period"], "Q3 2024")
        self.assertEqual(
            {f["metric"]: f["value"] for f in result["facts"]},
            {"revenue": "120", "eps_diluted": "1.2"},
        )
        rev = [p for p in result["prior_period"] if p["metric"] == "revenue"]
        self.assertEqual(
            [
                (p["prior_period"], p["prior_actual"], p["difference_pct"], p["relation"])
                for p in rev
            ],
            [("Q3 2023", "100", "20", "YEAR_OVER_YEAR")],
        )
        self.assertEqual(result["period_resolution"]["evidence"], ["third-quarter 2024 results"])

    def test_no_later_column_is_ever_called_prior(self):
        # Q4 FY25 is printed beside the reported Q3 FY25 (as a forecast or a later restatement could be): it is neither prior nor compared.
        result = run(source(release(headers="Q3 FY25 | Q4 FY25 | Q3 FY24")))
        self.assertEqual(result["period"], "Q3 FY25")
        self.assertEqual({p["prior_period"] for p in result["prior_period"]}, {"Q3 FY24"})
        self.assertIn("Q4 FY25", {f["period"] for f in result["other_period_figures"]})
        bundle_periods = {
            (c["period"], e["role"])
            for card in result["workbench_report"]["search_results"]
            for c in card["comparisons"]
            for e in c["evidence"]
        }
        self.assertNotIn(("Q4 FY25", "PRIOR"), bundle_periods)

    def test_unequal_column_spans_keep_each_duration(self):
        facts, issues = facts_of(UNEQUAL)
        self.assertEqual(
            by_period(facts),
            {
                "quarter ended 2024-09-30": "120",
                "12 months ended 2023-12-31": "400",
                "12 months ended 2022-12-31": "350",
                "12 months ended 2021-12-31": "300",
            },
        )
        result = run(source(UNEQUAL))
        # The release never states which quarter it reports, so nothing is labelled current and nothing is compared.
        self.assertEqual(
            (result["status"], result["period"], result["prior_period"]),
            ("PERIOD_UNRESOLVED", None, []),
        )
        self.assertIn("quarter ended 2024-09-30", result["period_resolution"]["candidates"])

    def test_unequal_column_spans_never_compare_a_quarter_with_a_year(self):
        stated = UNEQUAL.replace(
            b"<h1>Acme financial results</h1>",
            b"<p>Acme reported revenue for the third quarter ended September 30, 2024.</p>",
        )
        result = run(source(stated))
        self.assertEqual(result["period"], "quarter ended 2024-09-30")
        self.assertEqual(result["prior_period"], [])
        self.assertEqual({f["period_kind"] for f in result["other_period_figures"]}, {"12 months"})

    def test_explicit_canadian_dollar_statement_is_the_reporting_currency(self):
        result = run(source(CAD))
        for f in result["facts"]:
            self.assertEqual(
                (f["currency"], f["evidence"]["currency_basis"]), ("CAD", "TABLE_STATEMENT")
            )
            self.assertNotIn("CURRENCY_ASSUMED_USD_FROM_$_SIGN", f["flags"])
        self.assertEqual(result["reporting_currency"]["currencies"], ["CAD"])
        self.assertIn("CAD", earnings.render_note(result))


class GeometryTests(unittest.TestCase):
    def test_layout_places_rowspan_and_colspan_cells(self):
        rows = [
            [
                {"text": "a", "colspan": 1, "rowspan": 2, "cell": 1, "tag": "td"},
                {"text": "b", "colspan": 2, "rowspan": 1, "cell": 2, "tag": "td"},
            ],
            [
                {"text": "c", "colspan": 1, "rowspan": 1, "cell": 1, "tag": "td"},
                {"text": "d", "colspan": 1, "rowspan": 1, "cell": 2, "tag": "td"},
            ],
        ]
        placed = {
            c["text"]: (c["r0"], c["r1"], c["c0"], c["c1"], c["row"], c["cell"])
            for c in earnings.layout(rows)
        }
        self.assertEqual(
            placed,
            {
                "a": (0, 2, 0, 1, 1, 1),
                "b": (0, 1, 1, 3, 1, 2),
                "c": (1, 2, 1, 2, 2, 1),
                "d": (1, 2, 2, 3, 2, 2),
            },
        )

    def test_overlapping_spans_reject_the_table_visibly(self):
        raw = (
            b"<html><p>Acme Reports Third Quarter 2024 Financial Results</p><table>"
            b'<tr><td></td><td rowspan="2">Q3 2024</td><td>Q3 2023</td></tr>'
            b'<tr><td colspan="3">Revenue</td></tr>'
            b"<tr><td>Revenue</td><td>$120</td><td>$100</td></tr></table></html>"
        )
        facts, issues = facts_of(raw)
        self.assertEqual(facts, [])
        issue = next(i for i in issues if i["code"] == "TABLE_LAYOUT_REJECTED")
        self.assertIn("overlaps", issue["detail"])
        self.assertIn(
            "Revenue | $120 | $100", earnings.read_document(raw)["text"]
        )  # its text is still searchable

    def test_unsupported_or_oversized_spans_reject_the_table(self):
        for attr in (b'colspan="0"', b'colspan="9999"', b'rowspan="two"', b'colspan="-1"'):
            raw = (
                b"<html><p>Acme Reports Third Quarter 2024 Financial Results</p><table><tr><td></td><td "
                + attr
                + b">Q3 2024</td><td>Q3 2023</td></tr>"
                b"<tr><td>Revenue</td><td>$120</td><td>$100</td></tr></table></html>"
            )
            with self.subTest(attr=attr):
                facts, issues = facts_of(raw)
                self.assertEqual(facts, [])
                self.assertIn("TABLE_LAYOUT_REJECTED", {i["code"] for i in issues})

    def test_bounds_are_enforced_without_reading_the_rest_of_a_huge_table(self):
        with mock.patch.object(earnings, "MAX_TABLE_ROWS", 2):
            doc = earnings.read_document(release())
        self.assertEqual(doc["tables"], [])
        self.assertIn("more than 2 rows", doc["rejected_tables"][0]["reason"])
        self.assertIn("TABLE_NOT_READ", {i["code"] for i in earnings.extract_table_facts(doc)[1]})
        with mock.patch.object(earnings, "MAX_GRID_COLUMNS", 3):
            self.assertIsNotNone(earnings.read_document(release())["tables"][0]["grid_problem"])

    def test_a_nested_table_is_read_as_its_own_table(self):
        inner = release().split(b"<table>")[1].split(b"</table>")[0]
        raw = (
            b"<html><p>Acme Announces Financial Results for Third Quarter Fiscal 2025</p><p>third quarter ended October 27, 2024</p><table><tr><td>Layout<table>"
            + inner
            + b"</table></td></tr></table></html>"
        )
        facts, _ = facts_of(raw)
        self.assertEqual(by_period(facts)["Q3 FY25"], "110")

    def test_provenance_points_to_the_original_cells(self):
        facts, _ = facts_of(spanned(QUARTERS))
        rev = next(f for f in facts if f["metric"] == "revenue" and f["period"] == "Q2 2024")
        ev = rev["evidence"]
        self.assertEqual(ev["alignment"], "GRID")
        self.assertEqual(
            ev["value_cells"],
            [{"row": 2, "cell": 5, "columns": [5, 6]}, {"row": 2, "cell": 6, "columns": [6, 7]}],
        )
        self.assertEqual(ev["header_cells"], [{"row": 1, "cell": 3, "columns": [5, 8]}])
        self.assertEqual(ev["label_cells"], [{"row": 2, "cell": 1, "columns": [0, 2]}])

    def test_a_lone_dollar_sign_under_another_column_is_not_read_as_a_value(self):
        # The header spans one column per period but the row splits '$' from its number: the geometry puts '$' under Q3 and '110' under Q2.
        raw = (
            b"<html><p>Acme Reports Third Quarter 2024 Financial Results</p><p>(in millions)</p><table>"
            b'<tr><td></td><td colspan="1">Q3 2024</td><td colspan="1">Q2 2024</td><td colspan="2">Q3 2023</td></tr>'
            b"<tr><td>Revenue</td><td>$</td><td>110</td><td>$</td><td>100</td></tr></table></html>"
        )
        facts, issues = facts_of(raw)
        self.assertEqual(by_period(facts), {})
        self.assertIn("COLUMN_ALIGNMENT_UNCLEAR", {i["code"] for i in issues})

    def test_a_blank_cell_is_a_missing_value_not_a_shift(self):
        raw = spanned(QUARTERS).replace(
            b"<td>$</td><td>5,835</td><td></td>", b"<td></td><td></td><td></td>"
        )
        facts, _ = facts_of(raw)
        self.assertEqual(by_period(facts), {"Q3 2024": "6819", "Q3 2023": "5800"})

    def test_segment_rows_are_not_the_company_figure(self):
        raw = (
            b"<html><p>Acme Reports Third Quarter 2024 Financial Results</p><p>(Millions)</p><table>"
            b"<tr><td></td><td>Q3 2024</td><td>Q3 2023</td></tr>"
            b"<tr><td>Segment information</td></tr><tr><td>Data Center</td></tr><tr><td>Net revenue</td><td>$3,549</td><td>$1,598</td></tr>"
            b"<tr><td>Client</td></tr><tr><td>Net revenue</td><td>$1,881</td><td>$1,453</td></tr></table></html>"
        )
        facts, issues = facts_of(raw)
        self.assertEqual(facts, [])
        self.assertIn("BREAKDOWN_ROWS_NOT_READ", {i["code"] for i in issues})
        unlabeled = raw.replace(b"<tr><td>Segment information</td></tr>", b"")
        facts, issues = facts_of(unlabeled)
        self.assertEqual(facts, [])
        self.assertIn("REPEATED_ROW_LABEL", {i["code"] for i in issues})

    def test_parenthesised_scale_captions_are_read(self):
        for caption in (
            "(Millions except per share amounts and percentages)",
            "(In millions)",
            "($ in millions)",
            "(Dollars in millions)",
        ):
            self.assertEqual(earnings.unit_scale(caption), "millions", caption)
        self.assertIsNone(earnings.unit_scale("(Unaudited)"))

    def test_negative_and_symbol_forms_are_parsed_strictly(self):
        self.assertEqual(earnings.parse_number("$(1,234)")[0], -1234)
        self.assertEqual(earnings.parse_number("(1.5)%")[0:3:2], (-1.5, "percent"))
        self.assertEqual(earnings.parse_number("C$1.20")[1], "C$")
        for bad in ("(1,234", "1,2,3", "12,34", "$", "—", "1.2.3"):
            self.assertIsNone(earnings.parse_number(bad), bad)


class MetamorphicTests(unittest.TestCase):
    def test_reversing_equivalent_columns_preserves_the_result(self):
        forward, backward = (
            run(source(spanned(QUARTERS))),
            run(source(spanned(list(reversed(QUARTERS))))),
        )
        self.assertEqual(semantic(forward), semantic(backward))
        self.assertEqual(forward["period"], "Q3 2024")
        self.assertEqual(
            {p["relation"] for p in forward["prior_period"]}, {"YEAR_OVER_YEAR", "SEQUENTIAL"}
        )

    def test_splitting_or_joining_a_currency_cell_preserves_the_result(self):
        joined = spanned(QUARTERS)
        for label, rev, eps in QUARTERS:
            joined = joined.replace(
                f"<td>$</td><td>{rev}</td>".encode(), f'<td colspan="2">${rev}</td>'.encode()
            )
        self.assertEqual(semantic(run(source(joined))), semantic(run(source(spanned(QUARTERS)))))
        # In a table written without spans, a split '$' cell is read in printed order exactly as the joined form.
        split = (
            release()
            .replace(b"<td>$110</td>", b"<td>$</td><td>110</td>")
            .replace(b"<td>$100</td>", b"<td>$</td><td>100</td>")
            .replace(b"<td>$90</td>", b"<td>$</td><td>90</td>")
        )
        self.assertEqual(semantic(run(source(split))), semantic(run(source(release()))))

    def test_an_unrelated_annual_table_changes_nothing_about_the_quarter(self):
        annual = (
            '<table><tr><td></td><td colspan="2">Twelve Months Ended</td></tr><tr><td></td><td>December 31, 2023</td><td>December 31, 2022</td></tr>'
            "<tr><td>Revenue</td><td>$22,680</td><td>$23,601</td></tr></table>"
        )
        base, more = (
            run(source(spanned(QUARTERS))),
            run(source(spanned(QUARTERS, extra_table=annual))),
        )
        self.assertEqual(semantic(base), semantic(more))
        self.assertIn(
            ("12 months ended 2023-12-31", "22680"),
            {(f["period"], f["value"]) for f in more["other_period_figures"]},
        )

    def test_harmless_whitespace_and_line_breaks_preserve_the_result(self):
        noisy = (
            spanned(QUARTERS)
            .replace(b"Diluted earnings per share", b"Diluted\n   earnings  per <br>share")
            .replace(b"Q3 2023", b" Q3\n2023 ")
            .replace(b"<tr>", b"\n  <tr>")
        )
        self.assertEqual(semantic(run(source(noisy))), semantic(run(source(spanned(QUARTERS)))))

    def test_one_conflicting_metric_leaves_the_others_available(self):
        second = spanned(
            [
                ("Q3 2024", "9,999", "0.47"),
                ("Q2 2024", "5,835", "0.16"),
                ("Q3 2023", "5,800", "0.18"),
            ]
        ).decode()
        table = second[second.index("<table>") : second.index("</table>") + len("</table>")]
        result = run(
            source(
                spanned(
                    QUARTERS, extra_table="<p>(in millions, except per share amounts)</p>" + table
                )
            )
        )
        self.assertIn("FIGURE_CONFLICT", {i["code"] for i in result["issues"]})
        self.assertFalse([p for p in result["prior_period"] if p["metric"] == "revenue"])
        self.assertTrue([p for p in result["prior_period"] if p["metric"] == "eps_diluted"])


class PeriodResolutionTests(unittest.TestCase):
    def test_a_headline_end_date_identifies_a_calendar_quarter_column(self):
        raw = ASCENDING.replace(
            b"<h1>Acme third-quarter 2024 results</h1>",
            b"<p>Acme reported revenue for the third quarter ended September 30, 2024, of $120 million.</p>",
        )
        self.assertEqual(run(source(raw))["period"], "Q3 2024")

    def test_contradicting_statements_withhold_the_note(self):
        raw = ASCENDING.replace(
            b"</h1>", b"</h1><p>Acme reported revenue for the quarter ended June 30, 2024.</p>"
        )
        result = run(source(raw))
        self.assertEqual(result["status"], "PERIOD_UNRESOLVED")
        self.assertIn(
            "does not end calendar quarter 3 of 2024", result["period_resolution"]["reason"]
        )
        two = ASCENDING.replace(
            b"</h1>", b"</h1><p>Acme Reports Second Quarter 2024 Financial Results</p>"
        )
        self.assertIn("different quarters", run(source(two))["period_resolution"]["reason"])

    def test_an_announced_future_call_is_not_a_statement_of_the_reported_quarter(self):
        raw = ASCENDING.replace(
            b"</h1>",
            b"</h1><p>Acme will report fourth quarter 2024 financial results on February 4, 2025.</p>",
        )
        self.assertEqual(run(source(raw))["period"], "Q3 2024")

    def test_the_analyst_can_record_the_period_and_the_record_is_kept(self):
        override = {
            "period": "quarter ended 2024-09-30",
            "recorded_by": "analyst",
            "recorded_at": "2024-11-02T09:00:00Z",
            "rationale": "first column heading of the filing",
        }
        result = earnings.analyse(
            "Acme",
            "ACME",
            "XNAS",
            source(UNEQUAL),
            None,
            "2024-11-20T22:00:00Z",
            "public",
            period_override=override,
        )
        self.assertEqual(
            (result["period"], result["period_resolution"]["basis"]),
            ("quarter ended 2024-09-30", "ANALYST_OVERRIDE"),
        )
        self.assertEqual(result["analyst_inputs"]["period"], override)
        self.assertIn("chosen by the analyst", earnings.render_note(result))
        wrong = earnings.analyse(
            "Acme",
            "ACME",
            "XNAS",
            source(UNEQUAL),
            None,
            "2024-11-20T22:00:00Z",
            "public",
            period_override="Q9 2024",
        )
        self.assertEqual(wrong["status"], "PERIOD_UNRESOLVED")

    def test_earlier_and_relation_never_order_incompatible_periods(self):
        q3, q4 = earnings.qn_period("Q3 2024"), earnings.qn_period("Q4 2024")
        fiscal = earnings.qn_period("Q2 FY24")
        from datetime import date

        dated = earnings.dated_period("quarter", date(2024, 6, 30))
        self.assertIsNone(earnings.relation(q3, q4))
        self.assertFalse(earnings.earlier(q4, q3))
        self.assertIsNone(earnings.earlier(fiscal, q3))
        self.assertIsNone(earnings.earlier(dated, q3))
        self.assertIsNone(
            earnings.relation(
                earnings.dated_period("quarter", date(2024, 9, 30)),
                earnings.dated_period("12 months", date(2023, 12, 31)),
            )
        )

    def test_a_withheld_note_hides_figures_after_the_cutoff(self):
        result = run(source(UNEQUAL), as_of="2024-11-20T20:00:00Z")
        self.assertEqual(result["other_period_figures"], [])
        self.assertNotIn(
            "400", json.dumps({k: v for k, v in result.items() if k != "workbench_report"})
        )


class CurrencyTests(unittest.TestCase):
    def test_a_currency_symbol_printed_with_the_figure_is_its_evidence(self):
        result = run(source(release(rev="C$110")))
        rev = next(f for f in result["facts"] if f["metric"] == "revenue")
        self.assertEqual(
            (rev["currency"], rev["evidence"]["currency_basis"]), ("CAD", "CELL_SYMBOL")
        )

    def test_a_document_statement_far_from_the_table_applies(self):
        statement = b"<p>All dollar amounts in this release are expressed in Canadian dollars unless otherwise noted.</p><p>Highlights</p><p>Strong quarter</p><p>Details follow</p>"
        raw = release().replace(b"<body>", b"<body>" + statement)
        rev = next(f for f in run(source(raw))["facts"] if f["metric"] == "revenue")
        self.assertEqual(
            (rev["currency"], rev["evidence"]["currency_basis"]), ("CAD", "DOCUMENT_STATEMENT")
        )

    def test_conflicting_statements_leave_the_currency_unresolved(self):
        raw = release(
            extra="Amounts are in Canadian dollars. Some amounts are reported in U.S. dollars."
        )
        result = run(source(raw))
        rev = next(f for f in result["facts"] if f["metric"] == "revenue")
        self.assertIsNone(rev["currency"])
        self.assertIn("CURRENCY_UNRESOLVED", rev["flags"])
        self.assertIn("CURRENCY_CONFLICT", {i["code"] for i in result["issues"]})

    def test_the_analyst_record_fills_a_gap_and_never_overrules_a_statement(self):
        filled = earnings.analyse(
            "Acme",
            "ACME",
            "XTSE",
            source(release()),
            None,
            "2024-11-20T22:00:00Z",
            "public",
            None,
            {
                "currency": "CAD",
                "recorded_by": "analyst",
                "rationale": "filing cover page states Canadian dollars",
            },
        )
        rev = next(f for f in filled["facts"] if f["metric"] == "revenue")
        self.assertEqual(
            (rev["currency"], rev["evidence"]["currency_basis"]), ("CAD", "ANALYST_OVERRIDE")
        )
        self.assertEqual(
            filled["analyst_inputs"]["reporting_currency"]["rationale"],
            "filing cover page states Canadian dollars",
        )
        contradicted = earnings.analyse(
            "Acme", "ACME", "XTSE", source(CAD), None, "2024-11-20T22:00:00Z", "public", None, "USD"
        )
        self.assertEqual({f["currency"] for f in contradicted["facts"]}, {None})
        self.assertIn(
            "contradicts",
            next(i for i in contradicted["issues"] if i["code"] == "CURRENCY_CONFLICT")["detail"],
        )
        agreeing = earnings.analyse(
            "Acme", "ACME", "XTSE", source(CAD), None, "2024-11-20T22:00:00Z", "public", None, "CAD"
        )
        self.assertEqual(
            {f["evidence"]["currency_basis"] for f in agreeing["facts"]},
            {"TABLE_STATEMENT (analyst override agrees)"},
        )
        with self.assertRaises(earnings.EarningsError):
            earnings.analyst_currency("Canadian")

    def test_constant_currency_and_a_bare_dollar_are_not_statements(self):
        self.assertEqual(
            earnings.currency_statements(
                ["Revenue increased 11% (up 10% in constant currency)", "Revenue was $65.6 billion"]
            ),
            {},
        )
        self.assertEqual(
            earnings.currency_statements(["(in millions of U.S. dollars, except per share data)"]),
            {"USD": "(in millions of U.S. dollars, except per share data)"},
        )
        self.assertEqual(
            set(earnings.currency_statements(["(CAD millions)", "in thousands of euros"])),
            {"CAD", "EUR"},
        )

    def test_guidance_dollars_take_the_documents_currency(self):
        outlook = "<p>Outlook Acme outlook for the third quarter of fiscal 2025:</p><p>Revenue is expected to be $100 million, plus or minus 5%.</p>"
        items, _ = earnings.extract_guidance(
            earnings.read_document(
                release(outlook=outlook, extra="All amounts are in Canadian dollars.")
            )
        )
        self.assertEqual(
            (items[0]["currency"], items[0]["currency_basis"]), ("CAD", "SAME_AS_RELEASE_EVIDENCE")
        )
        items, _ = earnings.extract_guidance(earnings.read_document(release(outlook=outlook)))
        self.assertEqual(
            (items[0]["currency"], items[0]["currency_basis"]), ("USD", "ASSUMED_FROM_$_SIGN")
        )


if __name__ == "__main__":
    unittest.main()
