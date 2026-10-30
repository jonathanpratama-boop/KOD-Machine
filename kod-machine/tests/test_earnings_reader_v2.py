"""Release reader v4 on real development releases (tests/fixtures/releases_v2): table headings, statement precedence, labels, period resolution and outlook
sentences. Every expected figure was read from the release's own table row; the held-out set (evaluation/holdout_v1) is never used here."""

from decimal import Decimal
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from kod import earnings

FIX = Path(__file__).resolve().parent / "fixtures" / "releases_v2"
SOURCES = json.loads((FIX / "SOURCES.json").read_text())["files"]


def source(ticker, role="cur", tmp=None):
    rel = next(
        s for s in SOURCES if s["ticker"] == ticker and s["role"] == role and s["kind"] == "release"
    )
    hdr = next(
        s for s in SOURCES if s["ticker"] == ticker and s["role"] == role and s["kind"] == "headers"
    )
    raw = gzip.decompress((FIX / ticker.lower() / rel["stored_as"]).read_bytes())
    assert earnings.sha256_bytes(raw) == rel["sha256"], "fixture differs from the bytes SEC served"
    path = Path(tmp) / f"{ticker}-{role}.htm"
    path.write_bytes(raw)
    return earnings.prepare_source(
        str(path),
        rel["url"],
        sec_headers=str(FIX / ticker.lower() / hdr["stored_as"]),
        retrieved_at=rel["retrieved_at_utc"],
    )


def analyse(ticker, with_prior=False):
    with tempfile.TemporaryDirectory() as tmp:
        cur = source(ticker, "cur", tmp)
        pri = source(ticker, "pri", tmp) if with_prior else None
        return earnings.analyse(ticker, ticker, "XNAS", cur, pri, "2026-10-23T00:00:00Z", "public")


def figure(result, metric, basis=("UNSTATED", "GAAP")):
    values = {
        (Decimal(f["value"]), f["unit"])
        for f in result["facts"]
        if f["metric"] == metric and f["basis"] in basis
    }
    assert len(values) == 1, f"{metric}: {values}"
    return values.pop()


class TableHeadingTests(unittest.TestCase):
    def test_a_duration_heading_written_over_two_rows_and_a_caption_scale(self):
        r = analyse("TT")  # 'For the quarter' / 'ended June 30,'; '$, millions except EPS'
        self.assertIn(r["period"], ("Q2 2026", "quarter ended 2026-06-30"))
        self.assertEqual(figure(r, "revenue"), (Decimal("6353.5"), "millions"))
        self.assertEqual(
            figure(r, "net_income"), (Decimal("925.7"), "millions")
        )  # attributable to Trane, not the 935.3 total
        self.assertEqual(
            figure(r, "eps_diluted"), (Decimal("4.16"), "per_share")
        )  # 'Net earnings' under the diluted-per-share heading

    def test_month_and_day_on_one_row_and_years_on_the_next(self):
        r = analyse("BHE")
        self.assertEqual(r["period"], "quarter ended 2026-06-30")
        self.assertEqual(figure(r, "revenue"), (Decimal("755980"), "thousands"))
        self.assertEqual(figure(r, "eps_diluted"), (Decimal("0.55"), "per_share"))

    def test_week_based_periods_and_a_fiscal_quarter_label(self):
        r = analyse("SIG")  # '13 weeks ended'; 'Q2 Fiscal 2027'
        self.assertEqual(r["period"], "Q2 FY27")
        self.assertEqual(figure(r, "revenue"), (Decimal("1528.1"), "millions"))
        self.assertEqual(figure(r, "eps_diluted"), (Decimal("1.33"), "per_share"))

    def test_a_closing_parenthesis_in_its_own_cell_belongs_to_the_number(self):
        r = analyse("NUWE")
        self.assertEqual(figure(r, "net_income"), (Decimal("-4828"), "thousands"))
        self.assertEqual(figure(r, "eps_diluted"), (Decimal("-26.64"), "per_share"))


class StatementPrecedenceTests(unittest.TestCase):
    def test_segment_and_rounded_tables_do_not_compete_with_the_statement(self):
        r = analyse("AWI")
        self.assertEqual(
            figure(r, "revenue"), (Decimal("472.0"), "millions")
        )  # not the segments' 288.2 / 183.8 or the rounded 472
        self.assertEqual(
            figure(r, "net_income"), (Decimal("96.7"), "millions")
        )  # not the rounded 97
        codes = {i["code"] for i in r["issues"]}
        self.assertIn("NOT_THE_STATEMENT_FIGURE", codes)
        self.assertIn(
            "UNIT_SCALE_FROM_MATCHING_TABLE", codes
        )  # the statement states no scale; the highlights table does

    def test_a_fourth_quarter_release_whose_statement_is_annual(self):
        r = analyse(
            "CPB"
        )  # 'Fourth Quarter Fiscal 2026'; columns dated; statement of earnings is 12 months only
        self.assertEqual(r["period"], "quarter ended 2026-08-02")
        self.assertIn("Q4 FY26", r["period_resolution"]["aliases"])
        self.assertEqual(
            figure(r, "revenue", ("GAAP",)), (Decimal("2137"), "millions")
        )  # 'Net Sales' / 'As Reported (GAAP)'
        self.assertEqual(figure(r, "eps_diluted", ("GAAP",)), (Decimal("-0.23"), "per_share"))


class PeriodTests(unittest.TestCase):
    def test_a_fiscal_quarter_is_dated_by_the_publication_date(self):
        r = analyse("FICO")  # 'third quarter fiscal 2026', columns dated June 30
        self.assertEqual(r["period"], "quarter ended 2026-06-30")
        self.assertTrue(any("published" in e for e in r["period_resolution"]["evidence"]))
        self.assertEqual(figure(r, "eps_diluted"), (Decimal("10.45"), "per_share"))

    def test_three_and_six_months_ended_states_the_quarter(self):
        r = analyse("PENN")  # 'Reports Second Quarter Results' with no year
        self.assertEqual(r["period"], "quarter ended 2026-06-30")
        self.assertEqual(
            figure(r, "net_income"), (Decimal("33.1"), "millions")
        )  # attributable to PENN, not the 32.6 total
        self.assertEqual(figure(r, "eps_diluted"), (Decimal("0.24"), "per_share"))

    def test_a_mention_of_the_year_ago_quarter_does_not_unsettle_the_stated_one(self):
        r = analyse("NOTE")
        self.assertEqual(r["period"], "quarter ended 2026-06-30")


class OutlookTests(unittest.TestCase):
    def test_an_outlook_sentence_for_a_named_quarter_is_compared_after_restating_its_unit(self):
        r = analyse(
            "NOTE", with_prior=True
        )  # 'forecasts Q2 2026 revenue of $19.5 to $20.5 million'; actual in thousands
        [row] = [g for g in r["guidance_comparisons"] if g["metric"] == "revenue"]
        self.assertEqual(
            (Decimal(row["guidance_low"]), Decimal(row["guidance_high"]), row["unit"]),
            (Decimal("19500"), Decimal("20500"), "thousands"),
        )
        self.assertEqual(
            (Decimal(row["actual"]), row["position"]), (Decimal("19581"), "WITHIN_RANGE")
        )

    def test_sentence_reader_rules(self):
        doc = earnings.read_document(
            b"<html><body><p>Acme expects third quarter revenue of $1.0 billion to $1.1 billion and diluted EPS between $0.40 and $0.45. "
            b"Second quarter revenue was $950 million. Full-year revenue is expected to be $4.0 billion to $4.2 billion.</p></body></html>",
            "x.htm",
        )
        items = earnings._sentence_outlook(
            doc, ("USD", "x"), {"quarter": 2, "year": 2026, "fiscal": False}
        )
        got = {
            (g["metric"], g["target_period"], Decimal(g["low"]), Decimal(g["high"])) for g in items
        }
        self.assertEqual(
            got,
            {
                ("revenue", "Q3 2026", Decimal(1000), Decimal(1100)),
                ("eps_diluted", "Q3 2026", Decimal("0.4"), Decimal("0.45")),
            },
        )
        self.assertEqual(
            earnings._sentence_outlook(doc, ("USD", "x"), None), []
        )  # without the release's own quarter nothing is dated


class LabelTests(unittest.TestCase):
    def test_labels(self):
        cases = {
            "Net earnings": "net_income",
            "Net income (loss)": "net_income",
            "Net (loss) income": "net_income",
            "Net income (loss) attributable to PENN Entertainment, Inc.": "net_income_attributable",
            "Net loss attributable to non-controlling interest": None,
            "Net loss attributable to common shareholders": None,
            "Net earnings attributable to The Campbell's Company common shareholders - Diluted": None,
            "Diluted net earnings per share of common stock": "eps_diluted",
            "Basic and diluted loss per share": "eps_diluted",
            "Net loss per share attributable to Class A and Class B common stockholders, basic and diluted": "eps_diluted",
            "Net income (loss) per common share – assuming dilution": "eps_diluted",
            "EPS - Diluted": "eps_diluted",
            "Adjusted diluted net earnings per share": None,
            "Net loss per share from continuing operations, basic and diluted": None,
            "Revenues, net": "revenue",
            "Total operating revenues": "revenue",
        }
        for label, metric in cases.items():
            found = earnings.metric_for(label)
            self.assertEqual(found[0] if found else None, metric, label)
        self.assertEqual(
            earnings.metric_for("Diluted", "diluted earnings (loss) per share")[0], "eps_diluted"
        )
        self.assertIsNone(
            earnings.metric_for("Net earnings", "per common share data")
        )  # a per-share amount, not net income

    def test_a_loss_label_printed_without_a_sign_is_a_loss(self):
        doc = earnings.read_document(
            b"<html><body><p>Acme reports results for the quarter ended June 30, 2026.</p><p>(in thousands, except per share)</p><table>"
            b"<tr><td></td><td>Three Months Ended June 30,</td></tr><tr><td></td><td>2026</td><td>2025</td></tr>"
            b"<tr><td>Net loss</td><td>$4,828</td><td>$12,553</td></tr></table></body></html>",
            "x.htm",
        )
        facts, _ = earnings.extract_table_facts(doc)
        self.assertEqual(
            {f["value"] for f in facts if f["metric"] == "net_income"}, {"-4828", "-12553"}
        )


# ---------------------------------------------------------------- an adversarial review's wrong answers, each reproduced on a minimal release first


def _table(rows):
    return (
        "<table>"
        + "".join(
            "<tr>" + "".join(c if c.startswith("<td") else f"<td>{c}</td>" for c in r) + "</tr>"
            for r in rows
        )
        + "</table>"
    )


def _page(*parts):
    return (
        "<html><body>"
        + "".join(p if p.startswith("<") else f"<p>{p}</p>" for p in parts)
        + "</body></html>"
    )


def _run(
    html, published="2026-07-29T20:05:00Z", prior=None, prior_published="2026-04-29T20:05:00Z"
):
    with tempfile.TemporaryDirectory() as tmp:
        sources = []
        for name, body, pub in (("cur", html, published), ("pri", prior, prior_published)):
            if body is None:
                sources.append(None)
                continue
            path = Path(tmp) / f"{name}.htm"
            path.write_text(body)
            sources.append(
                earnings.prepare_source(
                    str(path),
                    f"https://www.sec.gov/x/{name}.htm",
                    published_at=pub,
                    retrieved_at="2026-10-23T00:00:00Z",
                )
            )
        return earnings.analyse(
            "Acme", "ACME", "XNAS", sources[0], sources[1], "2026-10-23T00:00:00Z", "public"
        )


HEAD = [
    ["", '<td colspan="2">Three months ended June 30,</td>'],
    ["(in millions, except per share data)", "2026", "2025"],
]
INTRO = (
    "Acme Corp. Reports Second Quarter 2026 Results",
    "Acme reported results for the quarter ended June 30, 2026.",
)


class ReviewFindingTests(unittest.TestCase):
    def test_a_rounded_highlights_table_is_not_taken_for_the_statement(self):
        summary = _table(
            HEAD
            + [
                ["Net sales", "$472", "$450"],
                ["Operating income", "$134", "$120"],
                ["Net earnings", "$97", "$80"],
                ["Diluted net earnings per share", "$2.26", "$1.80"],
            ]
        )
        statement = _table(
            HEAD
            + [
                ["Net sales", "$472.0", "$450.1"],
                ["Cost of goods sold", "250.0", "240.0"],
                ["Operating income", "133.8", "120.2"],
                ["Interest expense", "10.0", "10.0"],
                ["Earnings before income taxes", "123.8", "110.2"],
                ["Income tax expense", "27.1", "30.2"],
                ["Net earnings", "$96.7", "$80.0"],
                ["Net earnings per share:"],
                ["Basic", "$2.27", "$1.81"],
                ["Diluted", "2.26", "1.80"],
                ["Diluted shares", "42.8", "44.4"],
            ]
        )
        r = _run(
            _page(
                *INTRO,
                "Financial highlights",
                summary,
                "Consolidated Statements of Earnings",
                statement,
            )
        )
        self.assertEqual(figure(r, "net_income"), (Decimal("96.7"), "millions"))
        self.assertEqual(figure(r, "operating_income"), (Decimal("133.8"), "millions"))

    def test_a_statement_over_two_tables_keeps_net_income_attributable_to_the_company(self):
        summary = _table(
            HEAD
            + [
                ["Revenues", "$1,857.4", "$1,765.0"],
                ["Net income (loss)", "$32.6", "$(18.3)"],
                ["Diluted earnings (loss) per common share", "$0.24", "$(0.12)"],
            ]
        )
        part1 = _table(
            HEAD
            + [
                ["Total revenues", "1,857.4", "1,765.0"],
                ["Net income (loss)", "32.6", "(18.3)"],
                ["Net loss attributable to non-controlling interest", "0.5", "0.9"],
                ["Net income (loss) attributable to Acme Inc.", "$33.1", "$(17.4)"],
            ]
        )
        part2 = _table(HEAD + [["Diluted earnings (loss) per share", "$0.24", "$(0.12)"]])
        r = _run(
            _page(
                *INTRO,
                "Summary",
                summary,
                "Consolidated Statements of Operations",
                part1,
                "Page 7",
                part2,
            )
        )
        self.assertEqual(figure(r, "net_income"), (Decimal("33.1"), "millions"))

    def test_the_year_ago_quarter_mentioned_alone_does_not_become_the_period(self):
        table = _table(
            [
                ["", '<td colspan="2">Three Months Ended March 31,</td>'],
                ["(in millions, except per share)", "2026", "2025"],
                ["Revenue", "$1,050", "$900"],
                ["Net income", "$105", "$90"],
                ["Diluted earnings per share", "$1.05", "$0.90"],
            ]
        )
        r = _run(
            _page(
                "Acme Corp. Reports First Quarter 2026 Results",
                "Results for the first quarter ended March 31, 2025 included a $10 million gain.",
                "CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS",
                table,
            ),
            published="2026-04-29T20:05:00Z",
        )
        self.assertIsNone(r["period"])  # withheld, not the 2025 column

    def test_a_loss_named_only_in_the_heading_is_a_loss(self):
        r = _run(
            _page(
                *INTRO,
                "CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS",
                _table(
                    HEAD
                    + [
                        ["Revenue", "$1,000", "$900"],
                        ["Net loss", "$(500)", "$(400)"],
                        ["Net loss per share:"],
                        ["Basic and diluted", "$0.12", "$0.10"],
                    ]
                ),
            )
        )
        self.assertEqual(figure(r, "eps_diluted"), (Decimal("-0.12"), "per_share"))
        r = _run(
            _page(
                *INTRO,
                "CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS",
                _table(
                    HEAD
                    + [
                        ["Revenue", "$1,000", "$900"],
                        ["Net loss", "$(60)", "$(40)"],
                        ["Diluted loss per share"],
                        ["As Reported (GAAP)", "$0.23", "$0.15"],
                    ]
                ),
            )
        )
        self.assertEqual(figure(r, "eps_diluted", ("GAAP",)), (Decimal("-0.23"), "per_share"))

    def test_lines_attributable_to_others_are_not_the_company_net_income(self):
        r = _run(
            _page(
                *INTRO,
                "CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS",
                _table(
                    HEAD
                    + [
                        ["Revenue", "$1,000", "$900"],
                        ["Net income", "$500", "$400"],
                        ["Less: net income attributable to noncontrolling interests", "50", "40"],
                        ["Net income attributable to Series A preferred units", "30", "30"],
                        ["Net income per common unit - diluted", "$1.20", "$1.00"],
                    ]
                ),
            )
        )
        self.assertEqual(figure(r, "net_income"), (Decimal("500"), "millions"))
        for label in (
            "Net income attributable to Acme Inc. per diluted share",
            "Net income attributable to limited partners",
            "Net income attributable to Acme Holdings LLC unitholders",
            "Net income attributable to Acme, diluted",
        ):
            found = earnings.metric_for(label)
            self.assertNotEqual(found[0] if found else None, "net_income_attributable", label)

    def test_a_fiscal_quarter_label_printed_without_fy_is_not_merged_with_a_dated_column(self):
        statement = _table(
            [
                ["", '<td colspan="2">Three Months Ended</td>'],
                ["(in millions, except per share)", "June 30, 2026", "June 30, 2025"],
                ["Revenue", "$1,050", "$900"],
                ["Net income", "$105", "$90"],
                ["Diluted earnings per share", "$1.05", "$0.90"],
            ]
        )
        trend = _table(
            [
                ["(in millions)", "Q3 2026", "Q2 2026", "Q1 2026", "Q4 2025", "Q3 2025"],
                ["Revenue", "$1,050", "$1,000", "$980", "$950", "$900"],
            ]
        )
        r = _run(
            _page(
                "Acme Corp. Reports Third Quarter Fiscal 2026 Results",
                "CONSOLIDATED STATEMENTS OF OPERATIONS",
                statement,
                "Quarterly trend",
                trend,
            )
        )
        q2 = [
            f
            for f in r["other_period_figures"]
            if f["period"] == "Q2 2026" and f["metric"] == "revenue"
        ]
        self.assertEqual({Decimal(f["value"]) for f in q2}, {Decimal("1000")})

    def test_outlook_sentences_that_are_not_a_quarterly_outlook(self):
        own = {"quarter": 2, "year": 2026, "fiscal": False}

        def read(sentence):
            doc = earnings.read_document(
                f"<html><body><p>{sentence}</p></body></html>".encode(), "x.htm"
            )
            return {
                (
                    g["metric"],
                    g["target_period"],
                    Decimal(g["low"]) if g["low"] else None,
                    Decimal(g["high"]) if g["high"] else None,
                    Decimal(g["midpoint"]),
                )
                for g in earnings._sentence_outlook(doc, ("USD", "x"), own)
            }

        self.assertEqual(
            read(
                "Acme expects third quarter revenue of $1.0 billion to $1.1 billion and full-year diluted EPS of $4.00 to $4.20."
            ),
            {("revenue", "Q3 2026", Decimal(1000), Decimal(1100), Decimal(1050))},
        )
        self.assertEqual(
            read(
                "Acme expects fourth quarter and full-year 2026 revenue of $1.0 billion and $4.0 billion, respectively."
            ),
            set(),
        )
        self.assertEqual(
            read(
                "Acme expects third quarter revenue of $500 million and Adjusted EBITDA of $50 million to $60 million."
            ),
            {("revenue", "Q3 2026", None, None, Decimal(500))},
        )
        self.assertEqual(
            read(
                "Acme expects third quarter revenue to increase by $50 million to $70 million sequentially."
            ),
            set(),
        )
        self.assertEqual(
            read(
                "Acme expects third quarter revenue to grow 5% to 7%, and EPS of $0.40 to $0.45 for the full year."
            ),
            set(),
        )
        self.assertEqual(
            read(
                "We previously expected third quarter revenue of $1.0 billion to $1.1 billion and now expect $1.2 billion to $1.3 billion."
            ),
            set(),
        )
        self.assertEqual(
            read(
                "Second quarter revenue of $1.05 billion grew 10%, and the Company expects continued momentum in the second half."
            ),
            set(),
        )
        self.assertEqual(
            read(
                "We expect second quarter revenue to benefit from new product launches, following first quarter revenue of $950 million."
            ),
            set(),
        )
        self.assertEqual(
            read(
                "Building on second quarter momentum, Acme expects third quarter revenue of $1.0 billion to $1.1 billion."
            ),
            {("revenue", "Q3 2026", Decimal(1000), Decimal(1100), Decimal(1050))},
        )
        self.assertEqual(
            read("Acme expects third quarter net loss per share of $0.10 to $0.12."),
            {("eps_diluted", "Q3 2026", Decimal("-0.12"), Decimal("-0.10"), Decimal("-0.11"))},
        )


if __name__ == "__main__":
    unittest.main()
