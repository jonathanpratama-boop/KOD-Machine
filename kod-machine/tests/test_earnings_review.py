"""Regressions for the independent adversarial review of Gate A (periods, currency, table geometry). Each test is a reviewer's reproduced input; the assertion is
the corrected behaviour."""

import json
import time
import unittest

from kod import earnings
from tests.test_earnings import run, source

Q_TABLE = b"""<p>GAAP</p><p>Amounts in millions</p><table>
<tr><td></td><td>Q3 2024</td><td>Q3 2023</td></tr>
<tr><td>Revenue</td><td>$120</td><td>$100</td></tr>
<tr><td>Diluted earnings per share</td><td>$1.20</td><td>$1.00</td></tr></table>"""
DATED = b"""<p>GAAP</p><p>(in millions, except per share amounts)</p><table><tr><td></td><td colspan="2">Three Months Ended</td></tr>
<tr><td></td><td>September 30, 2024</td><td>September 30, 2023</td></tr><tr><td>Revenue</td><td>$120</td><td>$100</td></tr>
<tr><td>Diluted earnings per share</td><td>$1.20</td><td>$1.00</td></tr></table>"""


def page(*parts):
    return b"<html><body>" + b"".join(parts) + b"</body></html>"


def revenue(result, period=None):
    return [
        (f["period"], f["value"], f["currency"])
        for f in result["facts"]
        if f["metric"] == "revenue"
    ]


class PeriodReviewTests(unittest.TestCase):
    def test_a_year_ago_comparison_is_not_the_releases_statement(self):
        no_year = run(
            source(
                page(
                    b"<h1>Acme Reports Third Quarter Results</h1><p>Diluted EPS was $1.20, compared with third quarter 2023 earnings of $1.00.</p>",
                    Q_TABLE,
                )
            )
        )
        self.assertEqual((no_year["status"], no_year["period"]), ("PERIOD_UNRESOLVED", None))
        with_year = run(
            source(
                page(
                    b"<h1>Acme Reports Third Quarter 2024 Results</h1><p>Diluted EPS was $1.20, compared with third quarter 2023 earnings of $1.00.</p>",
                    Q_TABLE,
                )
            )
        )
        self.assertEqual(with_year["period"], "Q3 2024")

    def test_a_year_ago_quarter_ended_mention_is_ignored_and_order_does_not_matter(self):
        a = b"<p>Revenue grew 20% from $100 million in the quarter ended September 30, 2023.</p>"
        b = b"<p>Acme reported revenue of $120 million for the quarter ended September 30, 2024.</p>"
        first = run(source(page(b"<h1>Acme Reports Results</h1>", a, b, DATED)))
        second = run(source(page(b"<h1>Acme Reports Results</h1>", b, a, DATED)))
        self.assertEqual(first["period"], "quarter ended 2024-09-30")
        self.assertEqual(second["period"], first["period"])
        fiscal = page(
            b"<p>Acme Announces Financial Results for Third Quarter Fiscal 2025</p><p>Revenue of $35.1 billion, up 94% from $18.1 billion in the quarter ended October 29, 2023.</p>",
            b"<p>GAAP</p><p>($ in millions)</p><table><tr><td></td><td>Q3 FY25</td><td>Q3 FY24</td></tr><tr><td>Revenue</td><td>$35,082</td><td>$18,120</td></tr></table>",
        )
        result = run(source(fiscal))
        self.assertEqual(result["period"], "Q3 FY25")
        self.assertIsNone(
            result["facts"][0]["period_end"]
        )  # the year-ago date is never attached to the current quarter

    def test_a_letterhead_table_does_not_hide_the_headline(self):
        letter = b"<table><tr><td>NEWS RELEASE</td><td>Investor contact: Jane Doe, +1 555 0100</td></tr></table>"
        self.assertEqual(
            run(source(page(letter, b"<p>Acme Reports Third Quarter 2024 Results</p>", Q_TABLE)))[
                "period"
            ],
            "Q3 2024",
        )

    def test_an_analyst_record_never_overrules_the_release(self):
        raw = page(b"<h1>Acme Reports Third Quarter 2024 Results</h1>", Q_TABLE)
        result = earnings.analyse(
            "Acme",
            "ACME",
            "XNAS",
            source(raw),
            None,
            "2024-11-20T22:00:00Z",
            "public",
            period_override="Q3 2023",
        )
        self.assertEqual((result["status"], result["facts"]), ("PERIOD_UNRESOLVED", []))
        self.assertIn("contradicts the release", result["period_resolution"]["reason"])
        agree = earnings.analyse(
            "Acme",
            "ACME",
            "XNAS",
            source(raw),
            None,
            "2024-11-20T22:00:00Z",
            "public",
            period_override="Q3 2024",
        )
        self.assertEqual(
            (agree["period"], agree["period_resolution"]["basis"]),
            ("Q3 2024", "RELEASE_STATEMENT (analyst record agrees)"),
        )

    def test_a_stated_calendar_quarter_matches_its_dated_column(self):
        raw = page(
            b"<h1>Acme Reports Third Quarter 2024 Financial Results</h1><p>Revenue was $120 million, up 20% year over year.</p>",
            DATED,
        )
        self.assertEqual(run(source(raw))["period"], "quarter ended 2024-09-30")

    def test_ordinary_headline_wordings_and_future_sentences(self):
        nvda = page(
            b"<p>NVIDIA Announces Financial Results for Fourth Quarter and Fiscal 2025</p><p>NVIDIA today reported revenue for the fourth quarter ended January 26, 2025, of $39.3 billion.</p>",
            b"<p>GAAP</p><p>($ in millions)</p><table><tr><td></td><td>Q4 FY25</td><td>Q3 FY25</td><td>Q4 FY24</td></tr><tr><td>Revenue</td><td>$39,331</td><td>$35,082</td><td>$22,103</td></tr></table>",
        )
        self.assertEqual(run(source(nvda))["period"], "Q4 FY25")
        q4 = b"<table><tr><td></td><td>Q4 2024</td><td>Q4 2023</td></tr><tr><td>Revenue</td><td>$120</td><td>$100</td></tr></table>"
        self.assertEqual(
            run(
                source(
                    page(
                        b"<h1>Acme Reports Fourth Quarter and Full Year 2024 Results</h1><p>Amounts in millions</p>",
                        q4,
                    )
                )
            )["period"],
            "Q4 2024",
        )
        self.assertEqual(
            run(source(page(b"<h1>Acme Reports Q3 2024 Results</h1>", Q_TABLE)))["period"],
            "Q3 2024",
        )
        later = page(
            b"<h1>Acme Reports Third Quarter 2024 Results</h1><p>Fourth quarter 2024 results will be released on February 4, 2025.</p>",
            Q_TABLE,
        )
        self.assertEqual(run(source(later))["period"], "Q3 2024")

    def test_a_release_after_the_cutoff_shows_nothing_parsed_from_it(self):
        result = run(
            source(page(b"<h1>Acme Reports Third Quarter 2024 Results</h1>", Q_TABLE)),
            as_of="2024-11-20T20:00:00Z",
        )
        self.assertEqual(
            (result["period"], result["period_resolution"]),
            (None, {"status": "WITHHELD_BY_CUTOFF"}),
        )
        visible = json.dumps({k: v for k, v in result.items() if k != "workbench_report"})
        for leaked in ("Q3 2024", "RELEASE_STATEMENT", "Third Quarter"):
            self.assertNotIn(leaked, visible)
        self.assertNotIn("Q3 2024", earnings.render_note(result))

    def test_one_quarter_has_one_label_in_any_style(self):
        two = page(
            b"<h1>Acme Reports Third Quarter 2024 Results</h1><p>GAAP</p><p>Amounts in millions</p><table><tr><td></td><td>Q3'24</td><td>Q3'23</td></tr><tr><td>Revenue</td><td>$120</td><td>$100</td></tr></table>",
            Q_TABLE.replace(b"<tr><td>Revenue</td><td>$120</td><td>$100</td></tr>", b""),
        )
        result = run(source(two))
        self.assertEqual(result["period"], "Q3 2024")
        self.assertEqual({f["metric"] for f in result["facts"]}, {"revenue", "eps_diluted"})


class CurrencyReviewTests(unittest.TestCase):
    def test_a_currency_merely_mentioned_is_not_a_reporting_statement(self):
        for sentence in (
            b"<p>During the quarter Acme issued $500 million of senior notes denominated in euros.</p>",
            b"<p>Sales in Canada increased 5% in Canadian dollars.</p>",
            b"<p>Revenue in U.S. dollar terms grew 4% as the Canadian dollar weakened.</p>",
        ):
            with self.subTest(sentence=sentence):
                result = run(
                    source(page(b"<h1>Acme third-quarter 2024 results</h1>", sentence, Q_TABLE))
                )
                self.assertEqual({c for _, _, c in revenue(result)}, {"USD"})
                self.assertEqual(
                    result["facts"][0]["evidence"]["currency_basis"], "ASSUMED_FROM_$_SIGN"
                )

    def test_a_document_statement_is_not_outranked_by_a_nearby_remark(self):
        raw = page(
            b"<h1>Acme third-quarter 2024 results</h1><p>All amounts are in Canadian dollars unless otherwise noted.</p><p>a</p><p>b</p><p>c</p>",
            b"<p>Revenue in U.S. dollar terms grew 4% as the Canadian dollar weakened.</p>",
            Q_TABLE,
        )
        self.assertEqual({c for _, _, c in revenue(run(source(raw)))}, {"CAD"})

    def test_common_caption_forms_name_the_currency(self):
        for caption, code in (
            ("(millions of Canadian dollars, except per share amounts)", "CAD"),
            ("(C$ millions, except per share amounts)", "CAD"),
            ("(In C$ millions)", "CAD"),
            ("(CDN$ millions)", "CAD"),
            ("(Canadian dollars in millions)", "CAD"),
            ("(€ millions)", "EUR"),
            ("(RMB in millions)", "CNY"),
            ("(millions of Australian dollars)", "AUD"),
        ):
            self.assertEqual(set(earnings.currency_statements([caption])), {code}, caption)
        split = page(
            b"<h1>Acme third-quarter 2024 results</h1><p>GAAP</p><p>(in millions of Canadian<br>dollars, except per share amounts)</p>",
            Q_TABLE[len(b"<p>GAAP</p><p>Amounts in millions</p>") :],
        )
        self.assertEqual({c for _, _, c in revenue(run(source(split)))}, {"CAD"})
        boxed = page(
            b"<h1>Acme third-quarter 2024 results</h1><table><tr><td>(All amounts are in Canadian dollars unless otherwise stated.)</td></tr></table>",
            Q_TABLE,
        )
        self.assertEqual({c for _, _, c in revenue(run(source(boxed)))}, {"CAD"})

    def test_cross_release_rows_never_mix_currencies_and_assumptions_are_marked(self):
        cur = page(
            b"<h1>Acme third-quarter 2024 results</h1><p>GAAP</p><p>(in millions of U.S. dollars, except per share amounts)</p>",
            b"<table><tr><td></td><td>Q3 2024</td><td>Q3 2023</td></tr><tr><td>Revenue</td><td>$120</td><td>$100</td></tr></table>",
        )
        prior = source(
            page(
                b"<h1>Acme second-quarter 2024 results</h1><p>GAAP</p><p>(millions of Canadian dollars, except per share amounts)</p>",
                b"<table><tr><td></td><td>Q2 2024</td><td>Q2 2023</td></tr><tr><td>Revenue</td><td>$150</td><td>$140</td></tr></table>",
                b"<p>For the third quarter of 2024, Acme expects revenue to be approximately $160 million, plus or minus $5 million.</p>",
            ),
            "p.htm",
            "https://example.com/p.htm",
            "2024-08-20T21:00:00Z",
        )
        result = run(source(cur), prior)
        self.assertFalse(
            [p for p in result["prior_period"] if p["source"].startswith("figure from")]
        )
        self.assertEqual(result["guidance_comparisons"], [])

    def test_a_tables_own_symbol_scopes_its_unsigned_figures(self):
        raw = page(
            b"<h1>Acme third-quarter 2024 results</h1><p>GAAP</p><p>(in millions, except per share amounts)</p><table><tr><td></td><td>Q3 2024</td><td>Q3 2023</td></tr>"
            b"<tr><td>Revenue</td><td>C$120</td><td>100</td></tr><tr><td>Net income</td><td>30</td><td>25</td></tr></table>"
        )
        result = run(source(raw))
        self.assertEqual(
            {f["currency"] for f in result["facts"] + result["other_period_figures"]}, {"CAD"}
        )
        contradicted = earnings.analyse(
            "Acme", "ACME", "XTSE", source(raw), None, "2024-11-20T22:00:00Z", "public", None, "USD"
        )
        self.assertEqual({f["currency"] for f in contradicted["facts"]}, {None})

    def test_unknown_currencies_are_never_compared(self):
        cur = page(
            b"<h1>Acme third-quarter 2024 results</h1><p>All amounts are in Canadian dollars. Some amounts are reported in U.S. dollars.</p><p>a</p><p>b</p><p>c</p>",
            Q_TABLE,
        )
        prior = source(
            page(
                b"<h1>Acme second-quarter 2024 results</h1><p>All amounts are in euros. Some amounts are reported in U.S. dollars.</p>",
                b"<p>For the third quarter of 2024, Acme expects revenue to be approximately $118 million, plus or minus $5 million.</p>",
                Q_TABLE.replace(b"Q3", b"Q2"),
            ),
            "p.htm",
            "https://example.com/p.htm",
            "2024-08-20T21:00:00Z",
        )
        result = run(source(cur), prior)
        self.assertEqual(result["guidance_comparisons"], [])
        self.assertFalse([p for p in result["prior_period"] if p["unit"] != "percent"])

    def test_yen_sign_alone_is_not_a_currency(self):
        rmb = page(
            b"<h1>Acme third-quarter 2024 results</h1><p>All amounts in this release are in Renminbi (RMB) unless otherwise stated.</p><p>GAAP</p><p>(in millions)</p>"
            b"<table><tr><td></td><td>Q3 2024</td><td>Q3 2023</td></tr><tr><td>Revenue</td><td>\xc2\xa51,200</td><td>\xc2\xa51,000</td></tr></table>"
        )
        self.assertEqual({c for _, _, c in revenue(run(source(rmb)))}, {"CNY"})
        bare = page(
            b"<h1>Acme third-quarter 2024 results</h1><p>(in millions)</p><table><tr><td></td><td>Q3 2024</td><td>Q3 2023</td></tr><tr><td>Revenue</td><td>\xc2\xa51,200</td><td>\xc2\xa51,000</td></tr></table>"
        )
        fact = run(source(bare))["facts"][0]
        self.assertEqual((fact["currency"], fact["flags"][:1]), (None, ["CURRENCY_UNRESOLVED"]))

    def test_outlook_dollars_follow_the_tables_currency(self):
        outlook = "<p>Outlook Acme outlook for the fourth quarter of fiscal 2025:</p><p>Revenue is expected to be $120 million, plus or minus 5%.</p>"
        from tests.test_earnings import release

        result = run(
            source(
                release(
                    outlook=outlook,
                    units="(in millions of Canadian dollars, except per share amounts)",
                )
            )
        )
        self.assertEqual(
            (result["next_guidance"][0]["currency"], result["next_guidance"][0]["currency_basis"]),
            ("CAD", "SAME_AS_RELEASE_EVIDENCE"),
        )


class GeometryReviewTests(unittest.TestCase):
    HEAD = b"<p>Acme Reports Third Quarter 2024 Financial Results</p><p>Revenue for the third quarter ended September 30, 2024 was $120 million.</p><p>GAAP</p><p>(in millions, except per share amounts)</p>"

    def test_a_heading_describes_only_its_own_header_block(self):
        nine = page(
            self.HEAD,
            b'<table><tr><td></td><td colspan="2">Three Months Ended September 30,</td></tr><tr><td></td><td>2024</td><td>2023</td></tr><tr><td>Revenue</td><td>$120</td><td>$100</td></tr>'
            b"<tr><td>Nine months ended September 30,</td><td>2024</td><td>2023</td></tr><tr><td>Diluted earnings per share</td><td>$3.50</td><td>$2.90</td></tr></table>",
        )
        result = run(source(nine))
        self.assertEqual([f["metric"] for f in result["facts"]], ["revenue"])
        self.assertIn(
            ("eps_diluted", "9 months ended 2024-09-30"),
            {(f["metric"], f["period"]) for f in result["other_period_figures"]},
        )
        years = earnings.extract_table_facts(
            earnings.read_document(
                page(
                    b'<table><tr><td></td><td colspan="2">Years Ended December 31,</td></tr><tr><td></td><td>2024</td><td>2023</td></tr>'
                    b"<tr><td>Net income</td><td>$90</td><td>$70</td></tr></table>"
                )
            )
        )[0]
        self.assertEqual(
            {f["period"] for f in years},
            {"12 months ended 2024-12-31", "12 months ended 2023-12-31"},
        )

    def test_a_rowspan_basis_label_applies_to_the_rows_it_spans(self):
        raw = page(
            b"<p>Acme Reports Third Quarter 2024 Financial Results</p><p>GAAP and Non-GAAP Financial Summary</p><p>(in millions, except per share amounts)</p>"
            b'<table><tr><td colspan="2"></td><td>Q3 2024</td><td>Q3 2023</td></tr><tr><td rowspan="2">GAAP</td><td>Diluted earnings per share</td><td>$0.50</td><td>$0.40</td></tr>'
            b'<tr><td>Net income</td><td>$50</td><td>$40</td></tr><tr><td rowspan="2">Non-GAAP</td><td>Diluted earnings per share</td><td>$0.80</td><td>$0.70</td></tr>'
            b"<tr><td>Operating income</td><td>$95</td><td>$70</td></tr></table>"
        )
        op = next(f for f in run(source(raw))["facts"] if f["metric"] == "operating_income")
        self.assertEqual(op["basis"], "NON-GAAP")
        self.assertIn({"row": 4, "cell": 1, "columns": [0, 1]}, op["evidence"]["label_cells"])

    def test_a_row_of_counts_is_not_a_header(self):
        raw = page(
            self.HEAD,
            b'<table><tr><td></td><td colspan="2">Three Months Ended September 30,</td></tr><tr><td></td><td>2024</td><td>2023</td></tr><tr><td>Revenue</td><td>$120</td><td>$100</td></tr>'
            b"<tr><td>Stores open at period end</td><td>1205</td><td>1180</td></tr><tr><td>Net income</td><td>$12</td><td>$10</td></tr></table>",
        )
        result = run(source(raw))
        self.assertEqual({f["metric"] for f in result["facts"]}, {"revenue", "net_income"})
        self.assertFalse(
            [
                f
                for f in result["other_period_figures"]
                if "1205" in f["period"] or "1180" in f["period"]
            ]
        )

    def test_caption_elements_and_wrapper_tables_are_read_in_order(self):
        captioned = page(
            b"<p>Acme Reports Third Quarter 2024 Financial Results</p><p>GAAP</p><table><caption>Consolidated results (in millions of Canadian dollars, except per share amounts)</caption>",
            b"<tr><td></td><td>Q3 2024</td><td>Q3 2023</td></tr><tr><td>Revenue</td><td>$120</td><td>$100</td></tr></table>",
        )
        fact = run(source(captioned))["facts"][0]
        self.assertEqual((fact["currency"], fact["unit"]), ("CAD", "millions"))
        wrapped = page(
            b'<table width="100%"><tr><td><p>Acme Reports Third Quarter 2024 Financial Results</p><p>All amounts are in Canadian dollars, in millions except per-share amounts.</p>',
            Q_TABLE,
            b"</td></tr></table>",
        )
        result = run(source(wrapped))
        self.assertEqual((result["period"], result["facts"][0]["currency"]), ("Q3 2024", "CAD"))

    def test_a_percentage_is_never_an_amount(self):
        raw = page(
            b"<p>Acme Reports Third Quarter 2024 Financial Results</p>",
            Q_TABLE,
            b"<p>Results as a percentage of revenue</p><table><tr><td></td><td>Q3 2024</td><td>Q3 2023</td></tr>"
            b"<tr><td>Operating income</td><td>20.0%</td><td>17.0%</td></tr><tr><td>Net income</td><td>10.0%</td><td>8.0%</td></tr></table>",
        )
        result = run(source(raw))
        self.assertFalse(
            [f for f in result["facts"] if f["metric"] in ("operating_income", "net_income")]
        )
        self.assertIn("UNIT_AMBIGUOUS", {i["code"] for i in result["issues"]})

    def test_many_row_spanning_cells_are_read_in_linear_time(self):
        row = "<tr>" + '<td rowspan="2">1</td>' * 24 + "</tr>"
        doc = earnings.read_document(
            ("<html><body><table>" + row * 5000 + "</table></body></html>").encode()
        )
        start = time.monotonic()
        earnings.extract_table_facts(doc)
        self.assertLess(time.monotonic() - start, 10)

    def test_printed_order_reading_is_listed_and_points_at_the_real_cells(self):
        raw = page(
            b"<p>Acme Reports Third Quarter 2024 Financial Results</p><p>GAAP</p><p>(in millions)</p><table><tr><td></td><td>Q3 2024</td><td>Q3 2023</td></tr>"
            b"<tr><td>Revenue</td><td></td><td>$120</td><td>$100</td></tr></table>"
        )
        facts, issues = earnings.extract_table_facts(earnings.read_document(raw))
        rev = next(f for f in facts if f["period"] == "Q3 2024")
        self.assertEqual(rev["evidence"]["value_cells"], [{"row": 2, "cell": 3, "columns": [2, 3]}])
        self.assertIn("ALIGNED_BY_PRINTED_ORDER", {i["code"] for i in issues})

    def test_a_printed_change_is_checked_only_under_its_own_heading(self):
        raw = page(
            self.HEAD,
            b'<table><tr><td></td><td colspan="3">Three Months Ended September 30,</td><td colspan="3">Nine Months Ended September 30,</td></tr>'
            b"<tr><td></td><td>2024</td><td>2023</td><td>Y/Y</td><td>2024</td><td>2023</td><td>Y/Y</td></tr><tr><td>Revenue</td><td>$120</td><td>$100</td><td>Up 20%</td><td>$350</td><td>$300</td><td>Up 17%</td></tr></table>",
        )
        row = next(p for p in run(source(raw))["prior_period"] if p["metric"] == "revenue")
        self.assertEqual(row["printed_change_check"], {"printed": "Up 20%", "agrees": True})


if __name__ == "__main__":
    unittest.main()
