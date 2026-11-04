import hashlib
from decimal import Decimal
import io
import json
import re
import contextlib
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from kod import earnings
from kod.earnings import EarningsError

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "earnings_demo"
CUR_URL = "https://www.sec.gov/Archives/edgar/data/1045810/000104581024000315/q3fy25pr.htm"
PRI_URL = "https://www.sec.gov/Archives/edgar/data/1045810/000104581024000262/q2fy25pr.htm"


def release(
    rev="$110",
    rev2="$100",
    eps="$1.10",
    margin="50.0",
    outlook="",
    title="Acme Announces Financial Results for Third Quarter Fiscal 2025",
    extra="",
    headers="Q3 FY25 | Q2 FY25 | Q3 FY24",
    units="($ in millions, except earnings per share)",
    basis="GAAP",
    label="Revenue",
):
    cells = "".join(f"<td>{c}</td>" for c in headers.split(" | "))
    return f"""<html><body><p>{title}</p>
<p>Acme today reported revenue for the third quarter ended October 27, 2024, of $0.1 billion, up 10% from the previous quarter. {extra}</p>
<table><tr><td></td></tr><tr><td>{basis}</td></tr><tr><td>{units}</td>{cells}<td>Q/Q</td></tr>
<tr><td>{label}</td><td>{rev}</td><td>{rev2}</td><td>$90</td><td>Up 10%</td></tr>
<tr><td>Gross margin</td><td>{margin}</td><td>%</td><td>48.0</td><td>%</td><td>47.0</td><td>%</td><td>Up 2.0 pts</td></tr>
<tr><td>Diluted earnings per share*</td><td>{eps}</td><td>$1.00</td><td>$0.90</td><td>Up 10%</td></tr></table>
{outlook}</body></html>""".encode()


def source(
    raw,
    name="rel.htm",
    url="https://example.com/rel.htm",
    pub="2024-11-20T21:00:00Z",
    obs="2026-10-22T14:00:00Z",
):
    doc = earnings.read_document(raw, name)
    return {
        "doc": doc,
        "source_url": url,
        "published_at": pub,
        "published_basis": "supplied",
        "observed_at": obs,
        "observed_basis": "supplied",
        "title": "t",
    }


def run(primary, comparison=None, as_of="2024-11-20T22:00:00Z", mode="public", consensus=None):
    return earnings.analyse(
        "Acme Corp", "ACME", "XNAS", primary, comparison, as_of, mode, consensus
    )


class RealDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src = {s["file"]: s for s in json.loads((DEMO / "SOURCES.json").read_text())}
        for name, s in src.items():
            assert hashlib.sha256((DEMO / name).read_bytes()).hexdigest() == s["sha256"], name
        cls.cur = earnings.prepare_source(
            str(DEMO / "current_q3fy25pr.htm"),
            CUR_URL,
            sec_headers=str(DEMO / "current_0001045810-24-000315-index-headers.html"),
            retrieved_at="2026-10-22T14:40:11Z",
        )
        cls.pri = earnings.prepare_source(
            str(DEMO / "prior_q2fy25pr.htm"),
            PRI_URL,
            sec_headers=str(DEMO / "prior_0001045810-24-000262-index-headers.html"),
            retrieved_at="2026-10-22T14:40:12Z",
        )
        cls.res = run(cls.cur, cls.pri)

    def fact(self, metric, basis):
        return next(f for f in self.res["facts"] if f["metric"] == metric and f["basis"] == basis)

    def test_figures_from_the_real_release(self):
        self.assertEqual((self.res["period"], self.res["ticker"]), ("Q3 FY25", "ACME"))
        self.assertEqual(self.fact("revenue", "GAAP")["value"], "35082")
        self.assertEqual(self.fact("eps_diluted", "GAAP")["value"], "0.78")
        self.assertEqual(self.fact("eps_diluted", "NON-GAAP")["value"], "0.81")
        self.assertEqual(self.fact("gross_margin", "NON-GAAP")["value"], "75")
        for f in self.res["facts"]:
            self.assertIn(f["evidence"]["quote"], self.cur["doc"]["text"])

    def test_published_time_is_the_sec_acceptance_time_not_the_download_time(self):
        self.assertEqual(
            self.cur["published_at"], "2024-11-20T21:21:20Z"
        )  # 16:21:20 New York (EST)
        self.assertEqual(
            self.pri["published_at"], "2024-08-28T20:21:16Z"
        )  # 16:21:16 New York (EDT)
        self.assertEqual(self.cur["observed_at"], "2026-10-22T14:40:11Z")

    def test_guidance_comparison_uses_the_earlier_outlook_and_states_the_position(self):
        rev = next(g for g in self.res["guidance_comparisons"] if g["metric"] == "revenue")
        self.assertEqual(
            (rev["guidance_midpoint"], rev["guidance_low"], rev["guidance_high"], rev["position"]),
            ("32500", "31850", "33150", "ABOVE_RANGE"),
        )
        gm = [g for g in self.res["guidance_comparisons"] if g["metric"] == "gross_margin"]
        self.assertEqual({g["position"] for g in gm}, {"WITHIN_RANGE"})
        self.assertEqual(self.res["next_guidance"][0]["target_period"], "Q4 FY25")

    def test_prior_period_is_labelled_separately_and_agrees_with_printed_changes(self):
        rows = [
            p for p in self.res["prior_period"] if p["metric"] == "revenue" and p["basis"] == "GAAP"
        ]
        self.assertEqual({r["relation"] for r in rows}, {"SEQUENTIAL", "YEAR_OVER_YEAR"})
        self.assertTrue(
            all(r["label"] == "ACTUAL vs PRIOR-PERIOD ACTUAL" for r in self.res["prior_period"])
        )
        checked = [
            p["printed_change_check"]["agrees"]
            for p in self.res["prior_period"]
            if p["printed_change_check"]
        ]
        self.assertTrue(checked and all(checked))
        self.assertTrue(
            all(c["agrees"] for c in self.res["consistency_with_comparison"])
            and self.res["consistency_with_comparison"]
        )

    def test_note_says_consensus_unknown_and_never_fabricates_one(self):
        note = earnings.render_note(self.res)
        self.assertIn("CONSENSUS UNKNOWN", note)
        self.assertEqual(self.res["consensus"], [])
        self.assertIn("Interpretation: none offered", note)
        for word in ("buy", "sell", "probability"):
            self.assertNotIn(f" {word} ", note.lower().replace("buy/sell", ""))


MORE = DEMO / "more"


def load_more(ticker):
    d = MORE / ticker
    src = json.loads((d / "SOURCES.json").read_text())
    for s in src:
        assert hashlib.sha256((d / s["file"]).read_bytes()).hexdigest() == s["sha256"], s["file"]
    url = {s["role"]: s["url"] for s in src if s["kind"] == "release"}
    got = {}
    for role in ("cur", "pri"):
        got[role] = earnings.prepare_source(
            str(d / f"{role}.htm"),
            url[role],
            sec_headers=str(d / f"{role}_headers.html"),
            retrieved_at=next(s for s in src if s["role"] == role)["retrieved_at_utc_file_mtime"],
        )
    return got


class OtherLayoutTests(unittest.TestCase):
    """Three real releases with other table layouts (frozen under examples/earnings_demo/more/): AMD (headers without a label cell, change columns between periods, basis in a heading
    above the table), Apple (dated columns under 'Three/Twelve Months Ended', no basis stated), Microsoft (periods down the rows, metrics across the top)."""

    @classmethod
    def setUpClass(cls):
        cls.res = {
            t: run(
                *(lambda d: (d["cur"], d["pri"]))(load_more(t)),
                as_of="2026-10-22T20:00:00Z",
                mode="observed",
            )
            for t in ("amd", "aapl", "msft")
        }

    def value(self, t, metric, basis):
        return next(
            f["value"]
            for f in self.res[t]["facts"]
            if f["metric"] == metric and f["basis"] == basis
        )

    def test_amd_columns_are_labelled_by_their_headers_not_by_position(self):
        r = self.res["amd"]
        self.assertEqual(r["period"], "Q3 2024")  # the first version printed "Q3 FY23" here
        self.assertEqual(
            (
                self.value("amd", "revenue", "GAAP"),
                self.value("amd", "eps_diluted", "GAAP"),
                self.value("amd", "eps_diluted", "NON-GAAP"),
            ),
            ("6819", "0.47", "0.92"),
        )
        yoy = next(
            p
            for p in r["prior_period"]
            if p["metric"] == "revenue"
            and p["basis"] == "GAAP"
            and p["relation"] == "YEAR_OVER_YEAR"
        )
        seq = next(
            p
            for p in r["prior_period"]
            if p["metric"] == "revenue" and p["basis"] == "GAAP" and p["relation"] == "SEQUENTIAL"
        )
        self.assertEqual(
            (yoy["prior_period"], yoy["prior_actual"], seq["prior_period"], seq["prior_actual"]),
            ("Q3 2023", "5800", "Q2 2024", "5835"),
        )
        self.assertTrue(
            all(
                p["printed_change_check"]["agrees"]
                for p in r["prior_period"]
                if p["printed_change_check"]
            )
        )

    def test_amd_basis_comes_from_the_heading_above_the_table(self):
        self.assertEqual(
            (
                self.value("amd", "gross_margin", "GAAP"),
                self.value("amd", "gross_margin", "NON-GAAP"),
            ),
            ("50", "54"),
        )

    def test_amd_earlier_outlook_is_compared_with_the_right_basis(self):
        g = {(x["metric"], x["basis"]): x for x in self.res["amd"]["guidance_comparisons"]}
        rev = next(v for k, v in g.items() if k[0] == "revenue")
        self.assertEqual(
            (rev["guidance_low"], rev["guidance_high"], rev["position"]),
            ("6400", "7000", "WITHIN_RANGE"),
        )
        self.assertEqual(g[("gross_margin", "NON-GAAP")]["guidance_midpoint"], "53.5")
        self.assertNotIn(("gross_margin", "GAAP"), g)

    def test_apple_dated_columns_use_the_duration_heading_and_never_mix_quarter_with_year(self):
        r = self.res["aapl"]
        self.assertEqual(r["period"], "quarter ended 2024-09-28")
        self.assertEqual(
            (
                self.value("aapl", "revenue", "UNSTATED"),
                self.value("aapl", "net_income", "UNSTATED"),
                self.value("aapl", "eps_diluted", "UNSTATED"),
            ),
            ("94930", "14736", "0.97"),
        )
        self.assertTrue(
            all(p["prior_period"].startswith("quarter ended") for p in r["prior_period"])
        )
        self.assertIn(
            "12 months ended 2024-09-28", {f["period"] for f in r["other_period_figures"]}
        )
        self.assertIn(
            "BASIS_NOT_STATED", next(f for f in r["facts"] if f["metric"] == "revenue")["flags"]
        )

    def test_apple_share_count_is_not_read_as_earnings_per_share(self):
        eps = [
            f
            for f in self.res["aapl"]["facts"] + self.res["aapl"]["other_period_figures"]
            if f["metric"] == "eps_diluted"
        ]
        self.assertTrue(eps and all(Decimal(f["value"]) < 100 for f in eps))
        self.assertNotIn("FIGURE_CONFLICT", {i["code"] for i in self.res["aapl"]["issues"]})

    def test_apple_dollar_sign_on_the_first_row_only_still_gives_a_currency(self):
        self.assertEqual(
            next(f for f in self.res["aapl"]["facts"] if f["metric"] == "revenue")["currency"],
            "USD",
        )

    def test_sequential_comparison_can_come_from_the_earlier_release_and_says_so(self):
        seq = [
            p
            for p in self.res["aapl"]["prior_period"]
            if p["relation"] == "SEQUENTIAL" and p["metric"] == "revenue"
        ]
        self.assertEqual(
            (seq[0]["prior_period"], seq[0]["prior_actual"]), ("quarter ended 2024-06-29", "85777")
        )
        self.assertIn("comparison release", seq[0]["source"])
        self.assertIsNone(seq[0]["printed_change_check"])

    def test_microsoft_periods_down_the_rows_and_metrics_across_the_top(self):
        r = self.res["msft"]
        self.assertEqual(r["period"], "quarter ended 2024-09-30")
        self.assertEqual(
            (
                self.value("msft", "revenue", "GAAP"),
                self.value("msft", "operating_income", "GAAP"),
                self.value("msft", "net_income", "GAAP"),
                self.value("msft", "eps_diluted", "GAAP"),
            ),
            ("65585", "30552", "24667", "3.3"),
        )
        yoy = next(
            p
            for p in r["prior_period"]
            if p["metric"] == "revenue" and p["relation"] == "YEAR_OVER_YEAR"
        )
        self.assertEqual(
            (yoy["prior_period"], yoy["prior_actual"]), ("quarter ended 2023-09-30", "56517")
        )

    def test_no_guidance_is_invented_where_the_release_gives_none(self):
        for t in ("aapl", "msft"):
            self.assertEqual(self.res[t]["guidance_comparisons"], [])
            self.assertEqual(self.res[t]["next_guidance"], [])
            self.assertIn("CONSENSUS UNKNOWN", earnings.render_note(self.res[t]))

    def test_every_evidence_quote_is_in_the_document_text(self):
        for t in ("amd", "aapl", "msft"):
            src = load_more(t)["cur"]["doc"]["text"]
            for f in self.res[t]["facts"] + self.res[t]["other_period_figures"]:
                self.assertIn(f["evidence"]["quote"], src)

    def test_rows_with_a_different_value_count_are_skipped_and_listed(self):
        raw = release().replace(
            b"<td>$90</td><td>Up 10%</td></tr>\n<tr><td>Gross", b"</tr>\n<tr><td>Gross"
        )
        res = run(source(raw))
        self.assertIn("COLUMN_COUNT_MISMATCH", {i["code"] for i in res["issues"]})
        self.assertNotIn("revenue", {f["metric"] for f in res["facts"]})


class ExtractionTests(unittest.TestCase):
    def test_normal_synthetic_release(self):
        res = run(source(release()))
        f = {(x["metric"], x["basis"]): x for x in res["facts"]}
        self.assertEqual(
            (
                f[("revenue", "GAAP")]["value"],
                f[("revenue", "GAAP")]["unit"],
                f[("revenue", "GAAP")]["currency"],
            ),
            ("110", "millions", "USD"),
        )
        self.assertEqual(f[("gross_margin", "GAAP")]["unit"], "percent")
        self.assertIn("CURRENCY_ASSUMED_USD_FROM_$_SIGN", f[("revenue", "GAAP")]["flags"])

    def test_currency_override_is_applied_without_the_assumption_flag(self):
        res = earnings.analyse(
            "Acme",
            "ACME",
            "XTSE",
            source(release()),
            None,
            "2024-11-20T22:00:00Z",
            "public",
            None,
            "CAD",
        )
        rev = next(f for f in res["facts"] if f["metric"] == "revenue")
        self.assertEqual(rev["currency"], "CAD")
        self.assertNotIn("CURRENCY_ASSUMED_USD_FROM_$_SIGN", rev["flags"])

    def test_unreadable_row_is_skipped_and_listed_not_guessed(self):
        res = run(source(release(rev="n/m")))
        self.assertNotIn("revenue", {f["metric"] for f in res["facts"]})
        self.assertIn("UNREADABLE_ROW", {i["code"] for i in res["issues"]})

    def test_gross_margin_without_percent_sign_is_not_extracted(self):
        raw = release().replace(b"<td>50.0</td><td>%</td>", b"<td>50.0</td>")
        res = run(source(raw))
        self.assertNotIn("gross_margin", {f["metric"] for f in res["facts"]})
        self.assertIn("UNIT_AMBIGUOUS", {i["code"] for i in res["issues"]})

    def test_missing_unit_scale_is_flagged(self):
        res = run(source(release(units="($)")))
        rev = next(f for f in res["facts"] if f["metric"] == "revenue")
        self.assertEqual(rev["unit"], "unscaled")
        self.assertIn("UNIT_SCALE_UNKNOWN", rev["flags"])
        self.assertIn("UNIT_SCALE_UNSTATED", {i["code"] for i in res["issues"]})

    def test_headline_conflict_with_table_is_kept_visible(self):
        res = run(source(release(rev="$250", extra="GAAP earnings per diluted share was $9.99.")))
        codes = {i["code"] for i in res["issues"]}
        self.assertIn("HEADLINE_TABLE_CONFLICT", codes)
        self.assertEqual(next(f for f in res["facts"] if f["metric"] == "revenue")["value"], "250")

    def test_period_text_conflict_withholds_the_note(self):
        # The text reports the third quarter; the columns are Q2 FY25, Q1 FY25 and Q2 FY24. No column may be labelled current under a guess.
        res = run(source(release(headers="Q2 FY25 | Q1 FY25 | Q2 FY24")))
        self.assertEqual(
            (res["status"], res["period"], res["facts"], res["prior_period"]),
            ("PERIOD_UNRESOLVED", None, [], []),
        )
        issue = next(i for i in res["issues"] if i["code"] == "PERIOD_UNRESOLVED")
        self.assertIn("is not one of the quarter columns", issue["detail"])
        self.assertIn("reported period is unresolved", earnings.render_note(res))

    def test_unsupported_inputs_have_actionable_errors(self):
        for raw, hint in (
            (b"%PDF-1.7 binary", "PDF is not supported"),
            (b"   ", "empty file"),
            (b"plain words only", "not HTML"),
            (b"<html><body><p>hello</p></body></html>", "no earnings summary table"),
        ):
            with self.assertRaises(EarningsError) as cm:
                run(source(raw)) if hint == "no earnings summary table" else earnings.read_document(
                    raw, "x"
                )
            self.assertIn(hint, str(cm.exception))

    def test_malformed_html_does_not_traceback(self):
        raw = (
            b"<html><table><tr><td>Revenue<td>$1<tr><td>x</table></div></p><table><tr>"
            + b"<td>" * 50
        )
        doc = earnings.read_document(raw, "bad.htm")
        self.assertIsInstance(doc["text"], str)


class ComparisonTests(unittest.TestCase):
    OUT = (
        "<p>Outlook Acme’s outlook for the third quarter of fiscal 2025 is as follows:</p><p>• Revenue is expected to be $100 million, plus or minus 5%.</p>"
        "<p>• GAAP and non-GAAP gross margins are expected to be 49.0% and 50.0%, respectively, plus or minus 50 basis points.</p>"
    )

    def prior(self, outlook):
        return source(
            release(
                outlook=outlook,
                title="Acme Announces Financial Results for Second Quarter Fiscal 2025",
                headers="Q2 FY25 | Q1 FY25 | Q2 FY24",
            ).replace(b"third quarter ended", b"second quarter ended"),
            "prior.htm",
            "https://example.com/prior.htm",
            "2024-08-28T21:00:00Z",
        )

    def test_guidance_compares_matching_period_unit_and_basis_only(self):
        res = run(source(release()), self.prior(self.OUT))
        by = {(g["metric"], g["basis"]): g for g in res["guidance_comparisons"]}
        self.assertEqual(by[("revenue", "GAAP")]["position"], "ABOVE_RANGE")  # 110 vs 100 +/- 5%
        self.assertEqual(
            by[("gross_margin", "GAAP")]["position"], "ABOVE_RANGE"
        )  # 50.0 vs 49.0 +/- 0.5
        self.assertEqual(by[("gross_margin", "GAAP")]["difference_unit"], "percentage points")

    def test_guidance_for_another_period_is_withheld(self):
        res = run(
            source(release()), self.prior(self.OUT.replace("third quarter", "fourth quarter"))
        )
        self.assertEqual(res["guidance_comparisons"], [])
        self.assertTrue(any("not Q3 FY25" in w["reason"] for w in res["guidance_not_compared"]))

    def test_guidance_unit_mismatch_is_withheld_not_converted(self):
        res = run(
            source(release(units="($ in thousands, except earnings per share)")),
            self.prior(self.OUT),
        )
        self.assertFalse([g for g in res["guidance_comparisons"] if g["metric"] == "revenue"])
        self.assertTrue(
            any("unit or currency mismatch" in w["reason"] for w in res["guidance_not_compared"])
        )

    def test_guidance_does_not_mix_gaap_and_adjusted(self):
        out = "<p>Outlook Acme outlook for the third quarter of fiscal 2025:</p><p>GAAP and non-GAAP gross margins are expected to be 40.0% and 60.0%, respectively.</p>"
        res = run(source(release()), self.prior(out))
        gm = next(
            g
            for g in res["guidance_comparisons"]
            if g["metric"] == "gross_margin" and g["basis"] == "GAAP"
        )
        self.assertEqual(
            gm["guidance_midpoint"], "40.0".rstrip("0").rstrip(".")
        )  # GAAP guidance only, not the 60.0 adjusted figure
        self.assertEqual(gm["position"], "NO_RANGE_GIVEN")

    def test_guidance_requires_the_comparison_to_precede_the_release(self):
        late = self.prior(self.OUT)
        late["published_at"] = "2024-11-21T00:00:00Z"
        res = run(source(release()), late, as_of="2024-11-22T00:00:00Z")
        self.assertEqual(res["guidance_comparisons"], [])
        self.assertTrue(any("strictly before" in w["reason"] for w in res["guidance_not_compared"]))

    def test_unknown_comparison_publication_blocks_guidance(self):
        unk = self.prior(self.OUT)
        unk["published_at"] = None
        res = run(source(release()), unk)
        self.assertEqual(res["guidance_comparisons"], [])

    def test_restated_prior_figure_is_reported_as_different(self):
        prior = self.prior(self.OUT)
        res = run(
            source(release(rev2="$101")), prior
        )  # current release prints Q2 revenue 101; earlier release printed 110 for Q2? (its Q2 column is "$110")
        bad = [c for c in res["consistency_with_comparison"] if not c["agrees"]]
        self.assertTrue(bad)
        self.assertIn("DIFFERENT", earnings.render_note(res))

    def test_printed_change_disagreement_is_flagged(self):
        raw = release().replace(
            b"Up 10%</td></tr>\n<tr><td>Gross", b"Up 30%</td></tr>\n<tr><td>Gross"
        )
        res = run(source(raw))
        rev = next(
            p
            for p in res["prior_period"]
            if p["metric"] == "revenue" and p["relation"] == "SEQUENTIAL"
        )
        self.assertFalse(rev["printed_change_check"]["agrees"])


class ConsensusTests(unittest.TestCase):
    def file(self, rows):
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(rows, f)
        f.close()
        self.addCleanup(Path(f.name).unlink)
        return f.name

    def row(self, **kw):
        base = {
            "metric": "revenue",
            "basis": "GAAP",
            "period": "Q3 FY25",
            "value": "105",
            "unit": "millions",
            "currency": "USD",
            "published_at": "2024-11-19T12:00:00Z",
            "observed_at": "2024-11-19T12:05:00Z",
            "source_url": "https://example.com/consensus",
            "publisher": "Example Research",
            "text": "Consensus revenue for Q3 FY25 is $105 million",
            "quote": "Consensus revenue for Q3 FY25 is $105 million",
        }
        base.update(kw)
        return base

    def cons(self, rows):
        res = run(source(release()), consensus=self.file(rows))
        return res, res["consensus"]

    def test_pre_release_compatible_consensus_gives_a_surprise(self):
        res, cons = self.cons([self.row()])
        self.assertEqual((cons[0]["status"], cons[0]["difference"]), ("OK", "5"))
        self.assertNotIn("CONSENSUS UNKNOWN", earnings.render_note(res))

    def test_consensus_published_after_the_result_is_not_used(self):
        res, cons = self.cons([self.row(published_at="2024-11-20T21:30:00Z", observed_at=None)])
        self.assertEqual(cons[0]["status"], "INSUFFICIENT_DATA")
        self.assertIsNone(cons[0]["difference"])

    def test_consensus_with_different_unit_or_currency_or_period_is_not_compared(self):
        for kw in ({"unit": "billions"}, {"currency": "CAD"}, {"period": "Q4 FY25"}):
            res, cons = self.cons([self.row(**kw)])
            self.assertTrue(all(c["status"] != "OK" for c in cons), kw)

    def test_conflicting_consensus_values_are_a_conflict_not_an_average(self):
        res, cons = self.cons(
            [
                self.row(),
                self.row(
                    value="107",
                    text="Consensus revenue is $107 million",
                    quote="Consensus revenue is $107 million",
                    source_url="https://example.com/c2",
                ),
            ]
        )
        self.assertEqual(cons[0]["status"], "DATA_CONFLICT")

    def test_bad_consensus_file_is_an_actionable_error(self):
        with self.assertRaises(EarningsError):
            run(source(release()), consensus=self.file({"not": "a list"}))
        with self.assertRaises(EarningsError):
            run(source(release()), consensus=self.file([{"metric": "revenue"}]))


class CutoffTests(unittest.TestCase):
    def test_before_publication_the_note_withholds_all_figures(self):
        res = run(source(release()), as_of="2024-11-20T20:00:00Z")
        note = earnings.render_note(res)
        self.assertEqual(res["facts"], [])
        self.assertIn("Result withheld by the information cutoff", note)
        self.assertIn("published_after_cutoff", note.replace("\\", ""))
        self.assertNotIn("| Revenue |", note)

    def test_unknown_publication_time_is_not_replaced_by_download_time(self):
        src = source(release())
        src["published_at"] = None
        res = run(src)
        self.assertEqual(res["facts"], [])
        self.assertIn("publication_time_unknown", res["cutoff"]["excluded"]["current-release"])

    def test_observed_mode_requires_retrieval_before_the_cutoff_public_mode_does_not(self):
        late = source(release(), obs="2026-10-22T14:00:00Z")
        self.assertEqual(run(late, mode="observed", as_of="2024-11-21T00:00:00Z")["facts"], [])
        pub = run(late, mode="public", as_of="2024-11-21T00:00:00Z")
        self.assertTrue(pub["facts"])
        self.assertIn("Historical reconstruction", earnings.render_note(pub))

    def test_local_file_without_a_recorded_retrieval_time_uses_the_load_time(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "rel.htm"
            p.write_bytes(release())
            s = earnings.prepare_source(
                str(p),
                "https://example.com/rel.htm",
                published_at="2024-11-20T21:00:00Z",
                now="2026-10-23T00:00:00Z",
            )
            self.assertEqual(s["observed_at"], "2026-10-23T00:00:00Z")
            self.assertIn("unknown", s["observed_basis"])
            self.assertEqual(s["published_at"], "2024-11-20T21:00:00Z")

    def test_sec_header_without_a_time_gives_unknown_publication(self):
        with tempfile.TemporaryDirectory() as d:
            p, h = Path(d) / "rel.htm", Path(d) / "h.html"
            p.write_bytes(release())
            h.write_text("<html>no acceptance here</html>")
            s = earnings.prepare_source(str(p), sec_headers=str(h))
            self.assertIsNone(s["published_at"])
            self.assertIn("UNKNOWN", s["published_basis"])


class SafetyTests(unittest.TestCase):
    EVIL = "<script>alert(1)</script> [click](javascript:alert(1)) ![x](http://evil/x.png) `code` | pipe"

    def test_untrusted_text_is_escaped_in_the_note(self):
        res = run(source(release(extra=self.EVIL, title=self.EVIL)))
        res["company"] = self.EVIL
        res["headline"]["paragraph"] = self.EVIL
        note = earnings.render_note(res)
        self.assertNotIn("<script", note)
        for line in note.splitlines():
            if line.startswith(("- current:", "- comparison:")):
                continue
            self.assertIsNone(re.search(r"(?<!\\)\]\(", line), line)
            self.assertIsNone(re.search(r"(?<!\\)!\[", line), line)
            self.assertNotIn("`code`", line.replace("\\`", ""))

    def test_pipes_in_untrusted_text_do_not_add_table_columns(self):
        res = run(source(release(extra="pipe | here")))
        res["facts"][0]["evidence"]["quote"] += " | extra | pipes"
        blocks, cur = [], []
        for line in earnings.render_note(res).splitlines():
            if line.startswith("|"):
                cur.append(len(re.split(r"(?<!\\)\|", line)))
            elif cur:
                blocks.append(cur)
                cur = []
        self.assertTrue(blocks)
        for widths in blocks:
            self.assertEqual(len(set(widths)), 1, widths)

    def test_links_only_for_validated_https_sources(self):
        res = run(source(release(), url="https://example.com/a b.htm"))
        note = earnings.render_note(res)
        self.assertIn("(<https://example.com/a%20b.htm>)", note)
        local = earnings.render_note(run(source(release(), url=earnings.LOCAL_URL + "x.htm")))
        self.assertIn("no public URL supplied", local)
        self.assertNotIn("example.invalid)", local)

    def test_fetch_refuses_plain_http_and_requires_a_sec_contact(self):
        with self.assertRaises(EarningsError):
            earnings.fetch_url("http://www.sec.gov/x.htm")
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(EarningsError) as cm:
                earnings.fetch_url("https://www.sec.gov/Archives/x.htm")
        self.assertIn("KOD_SEC_CONTACT", str(cm.exception))

    def test_sec_headers_url_is_derived_from_the_accession_folder(self):
        self.assertEqual(
            earnings.sec_headers_url(CUR_URL),
            "https://www.sec.gov/Archives/edgar/data/1045810/0001045810-24-000315-index-headers.html".replace(
                "data/1045810/", "data/1045810/000104581024000315/"
            ),
        )
        self.assertIsNone(earnings.sec_headers_url("https://example.com/x.htm"))


class CommandTests(unittest.TestCase):
    def snapshot(self):
        out = {}
        for sub in ("var", "registry"):
            for p in sorted((ROOT / sub).rglob("*")):
                if p.is_file():
                    out[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
        return out

    def test_command_writes_only_its_output_and_leaves_protected_records_alone(self):
        before = self.snapshot()
        with tempfile.TemporaryDirectory() as d:
            argv = [
                "--company",
                "NVIDIA Corporation",
                "--ticker",
                "NVDA",
                "--venue",
                "XNAS",
                "--document",
                str(DEMO / "current_q3fy25pr.htm"),
                "--source-url",
                CUR_URL,
                "--sec-headers",
                str(DEMO / "current_0001045810-24-000315-index-headers.html"),
                "--retrieved-at",
                "2026-10-22T14:40:11Z",
                "--comparison-document",
                str(DEMO / "prior_q2fy25pr.htm"),
                "--comparison-source-url",
                PRI_URL,
                "--comparison-sec-headers",
                str(DEMO / "prior_0001045810-24-000262-index-headers.html"),
                "--comparison-retrieved-at",
                "2026-10-22T14:40:12Z",
                "--as-of",
                "2024-11-20T22:00:00Z",
                "--mode",
                "public",
                "--out-dir",
                d,
            ]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(earnings.main(argv), 0)
            self.assertEqual(sorted(p.name for p in Path(d).iterdir()), ["note.json", "note.md"])
            note = (Path(d) / "note.md").read_text()
            data = json.loads((Path(d) / "note.json").read_text())
            self.assertIn("CONSENSUS UNKNOWN", note)
            self.assertFalse(data["entry_permission"])
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(earnings.main(argv), 0)  # deterministic and repeatable
            self.assertEqual((Path(d) / "note.md").read_text(), note)
        self.assertEqual(self.snapshot(), before)

    def test_errors_exit_2_without_a_traceback(self):
        with tempfile.TemporaryDirectory() as d, mock.patch("sys.stderr") as err:
            code = earnings.main(
                [
                    "--company",
                    "A",
                    "--ticker",
                    "A",
                    "--document",
                    str(Path(d) / "missing.htm"),
                    "--out-dir",
                    d,
                ]
            )
        self.assertEqual(code, 2)
        self.assertIn(
            "earnings note error: cannot read", "".join(c.args[0] for c in err.write.call_args_list)
        )

    def test_existing_workbench_command_is_unchanged(self):
        from kod import workbench

        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(
                workbench.main(
                    [
                        "--input",
                        str(ROOT / "examples" / "workbench_demo.json"),
                        "--as-of",
                        "2026-10-22T08:00:00Z",
                        "--query",
                        "revenue",
                    ]
                ),
                0,
            )


if __name__ == "__main__":
    unittest.main()
