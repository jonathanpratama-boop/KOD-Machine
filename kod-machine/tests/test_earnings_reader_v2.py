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
    rel = next(s for s in SOURCES if s["ticker"] == ticker and s["role"] == role and s["kind"] == "release")
    hdr = next(s for s in SOURCES if s["ticker"] == ticker and s["role"] == role and s["kind"] == "headers")
    raw = gzip.decompress((FIX / ticker.lower() / rel["stored_as"]).read_bytes())
    assert earnings.sha256_bytes(raw) == rel["sha256"], "fixture differs from the bytes SEC served"
    path = Path(tmp) / f"{ticker}-{role}.htm"
    path.write_bytes(raw)
    return earnings.prepare_source(str(path), rel["url"], sec_headers=str(FIX / ticker.lower() / hdr["stored_as"]), retrieved_at=rel["retrieved_at_utc"])


def analyse(ticker, with_prior=False):
    with tempfile.TemporaryDirectory() as tmp:
        cur = source(ticker, "cur", tmp)
        pri = source(ticker, "pri", tmp) if with_prior else None
        return earnings.analyse(ticker, ticker, "XNAS", cur, pri, "2026-10-23T00:00:00Z", "public")


def figure(result, metric, basis=("UNSTATED", "GAAP")):
    values = {(Decimal(f["value"]), f["unit"]) for f in result["facts"] if f["metric"] == metric and f["basis"] in basis}
    assert len(values) == 1, f"{metric}: {values}"
    return values.pop()


class TableHeadingTests(unittest.TestCase):
    def test_a_duration_heading_written_over_two_rows_and_a_caption_scale(self):
        r = analyse("TT")                                         # 'For the quarter' / 'ended June 30,'; '$, millions except EPS'
        self.assertIn(r["period"], ("Q2 2026", "quarter ended 2026-06-30"))
        self.assertEqual(figure(r, "revenue"), (Decimal("6353.5"), "millions"))
        self.assertEqual(figure(r, "net_income"), (Decimal("925.7"), "millions"))     # attributable to Trane, not the 935.3 total
        self.assertEqual(figure(r, "eps_diluted"), (Decimal("4.16"), "per_share"))  # 'Net earnings' under the diluted-per-share heading

    def test_month_and_day_on_one_row_and_years_on_the_next(self):
        r = analyse("BHE")
        self.assertEqual(r["period"], "quarter ended 2026-06-30")
        self.assertEqual(figure(r, "revenue"), (Decimal("755980"), "thousands"))
        self.assertEqual(figure(r, "eps_diluted"), (Decimal("0.55"), "per_share"))

    def test_week_based_periods_and_a_fiscal_quarter_label(self):
        r = analyse("SIG")                                        # '13 weeks ended'; 'Q2 Fiscal 2027'
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
        self.assertEqual(figure(r, "revenue"), (Decimal("472.0"), "millions"))          # not the segments' 288.2 / 183.8 or the rounded 472
        self.assertEqual(figure(r, "net_income"), (Decimal("96.7"), "millions"))        # not the rounded 97
        codes = {i["code"] for i in r["issues"]}
        self.assertIn("NOT_THE_STATEMENT_FIGURE", codes)
        self.assertIn("UNIT_SCALE_FROM_MATCHING_TABLE", codes)                           # the statement states no scale; the highlights table does

    def test_a_fourth_quarter_release_whose_statement_is_annual(self):
        r = analyse("CPB")                                        # 'Fourth Quarter Fiscal 2026'; columns dated; statement of earnings is 12 months only
        self.assertEqual(r["period"], "quarter ended 2026-08-02")
        self.assertIn("Q4 FY26", r["period_resolution"]["aliases"])
        self.assertEqual(figure(r, "revenue", ("GAAP",)), (Decimal("2137"), "millions"))  # 'Net Sales' / 'As Reported (GAAP)'
        self.assertEqual(figure(r, "eps_diluted", ("GAAP",)), (Decimal("-0.23"), "per_share"))


class PeriodTests(unittest.TestCase):
    def test_a_fiscal_quarter_is_dated_by_the_publication_date(self):
        r = analyse("FICO")                                       # 'third quarter fiscal 2026', columns dated June 30
        self.assertEqual(r["period"], "quarter ended 2026-06-30")
        self.assertTrue(any("published" in e for e in r["period_resolution"]["evidence"]))
        self.assertEqual(figure(r, "eps_diluted"), (Decimal("10.45"), "per_share"))

    def test_three_and_six_months_ended_states_the_quarter(self):
        r = analyse("PENN")                                       # 'Reports Second Quarter Results' with no year
        self.assertEqual(r["period"], "quarter ended 2026-06-30")
        self.assertEqual(figure(r, "net_income"), (Decimal("33.1"), "millions"))        # attributable to PENN, not the 32.6 total
        self.assertEqual(figure(r, "eps_diluted"), (Decimal("0.24"), "per_share"))

    def test_a_mention_of_the_year_ago_quarter_does_not_unsettle_the_stated_one(self):
        r = analyse("NOTE")
        self.assertEqual(r["period"], "quarter ended 2026-06-30")


class OutlookTests(unittest.TestCase):
    def test_an_outlook_sentence_for_a_named_quarter_is_compared_after_restating_its_unit(self):
        r = analyse("NOTE", with_prior=True)                      # 'forecasts Q2 2026 revenue of $19.5 to $20.5 million'; actual in thousands
        [row] = [g for g in r["guidance_comparisons"] if g["metric"] == "revenue"]
        self.assertEqual((Decimal(row["guidance_low"]), Decimal(row["guidance_high"]), row["unit"]), (Decimal("19500"), Decimal("20500"), "thousands"))
        self.assertEqual((Decimal(row["actual"]), row["position"]), (Decimal("19581"), "WITHIN_RANGE"))

    def test_sentence_reader_rules(self):
        doc = earnings.read_document(b"<html><body><p>Acme expects third quarter revenue of $1.0 billion to $1.1 billion and diluted EPS between $0.40 and $0.45. "
                                     b"Second quarter revenue was $950 million. Full-year revenue is expected to be $4.0 billion to $4.2 billion.</p></body></html>", "x.htm")
        items = earnings._sentence_outlook(doc, ("USD", "x"), {"quarter": 2, "year": 2026, "fiscal": False})
        got = {(g["metric"], g["target_period"], Decimal(g["low"]), Decimal(g["high"])) for g in items}
        self.assertEqual(got, {("revenue", "Q3 2026", Decimal(1000), Decimal(1100)), ("eps_diluted", "Q3 2026", Decimal("0.4"), Decimal("0.45"))})
        self.assertEqual(earnings._sentence_outlook(doc, ("USD", "x"), None), [])          # without the release's own quarter nothing is dated


class LabelTests(unittest.TestCase):
    def test_labels(self):
        cases = {"Net earnings": "net_income", "Net income (loss)": "net_income", "Net (loss) income": "net_income",
                 "Net income (loss) attributable to PENN Entertainment, Inc.": "net_income_attributable",
                 "Net loss attributable to non-controlling interest": None, "Net loss attributable to common shareholders": None,
                 "Net earnings attributable to The Campbell's Company common shareholders - Diluted": None,
                 "Diluted net earnings per share of common stock": "eps_diluted", "Basic and diluted loss per share": "eps_diluted",
                 "Net loss per share attributable to Class A and Class B common stockholders, basic and diluted": "eps_diluted",
                 "Net income (loss) per common share – assuming dilution": "eps_diluted", "EPS - Diluted": "eps_diluted",
                 "Adjusted diluted net earnings per share": None, "Net loss per share from continuing operations, basic and diluted": None,
                 "Revenues, net": "revenue", "Total operating revenues": "revenue"}
        for label, metric in cases.items():
            found = earnings.metric_for(label)
            self.assertEqual(found[0] if found else None, metric, label)
        self.assertEqual(earnings.metric_for("Diluted", "diluted earnings (loss) per share")[0], "eps_diluted")
        self.assertIsNone(earnings.metric_for("Net earnings", "per common share data"))      # a per-share amount, not net income

    def test_a_loss_label_printed_without_a_sign_is_a_loss(self):
        doc = earnings.read_document(b"<html><body><p>Acme reports results for the quarter ended June 30, 2026.</p><p>(in thousands, except per share)</p><table>"
                                     b"<tr><td></td><td>Three Months Ended June 30,</td></tr><tr><td></td><td>2026</td><td>2025</td></tr>"
                                     b"<tr><td>Net loss</td><td>$4,828</td><td>$12,553</td></tr></table></body></html>", "x.htm")
        facts, _ = earnings.extract_table_facts(doc)
        self.assertEqual({f["value"] for f in facts if f["metric"] == "net_income"}, {"-4828", "-12553"})


if __name__ == "__main__":
    unittest.main()
