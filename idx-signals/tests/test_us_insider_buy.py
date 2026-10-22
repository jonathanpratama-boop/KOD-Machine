import importlib.util
import io
import sys
import unittest
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

UIB = Path(__file__).resolve().parents[1] / "research" / "US_INSIDER_BUY"


def load(name):
    if str(UIB) not in sys.path:
        sys.path.insert(0, str(UIB))
    spec = importlib.util.spec_from_file_location(f"uib_{name}", UIB / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tsv(header, rows):
    return "\t".join(header) + "\n" + "".join("\t".join(r) + "\n" for r in rows)


def archive(with_flag=True) -> zipfile.ZipFile:
    """A small synthetic Insider Transactions archive (the real tables have more columns; the reader needs these)."""
    sh = ["ACCESSION_NUMBER", "FILING_DATE", "DOCUMENT_TYPE", "ISSUERCIK", "ISSUERTRADINGSYMBOL"] + (["AFF10B5ONE"] if with_flag else [])

    def srow(acc, date, typ, cik, sym, flag="0"):
        return [acc, date, typ, cik, sym] + ([flag] if with_flag else [])

    sub = tsv(sh, [
        srow("A1", "05-JAN-2021", "4", "0000001000", "AAA"),            # officer buys 120k: the first event of AAA
        srow("A2", "06-JAN-2021", "4/A", "0000002000", "BBB"),          # amendment: not used
        srow("A3", "07-JAN-2021", "4", "0000003000", "CCC"),            # only a 10% owner
        srow("A4", "08-JAN-2021", "4", "0000004000", "DDD", "1"),       # 10b5-1 flag
        srow("A5", "09-JAN-2021", "3", "0000005000", "EEE"),            # a Form 3
        srow("A6", "10-JAN-2021", "4", "0000006000", "FFF"),            # officer, 10k only
        srow("A7", "04-FEB-2021", "4", "0000001000", "AAA"),            # AAA again 30 days later: chained out
        srow("A8", "15-APR-2021", "4", "0000001000", "AAA"),            # AAA again 100 days after A1: an event
        srow("A9", "11-JAN-2021", "4", "0000009000", "ZZZ"),            # issuer not in the ticker map
        srow("B1", "12-JAN-2021", "4", "0000007000", "GGG"),            # director, mixed lines: only the P common line counts
        srow("B2", "13-JAN-2021", "4", "0000008000", "HHH"),            # joint filing: a 10% fund and an officer, 60k
    ])
    oh = ["ACCESSION_NUMBER", "RPTOWNERCIK", "RPTOWNERNAME", "RPTOWNER_RELATIONSHIP", "RPTOWNER_TITLE"]
    own = tsv(oh, [
        ["A1", "1", "O One", "Officer", "Chief Executive Officer"], ["A2", "2", "O Two", "Officer", "CFO"], ["A3", "3", "Fund", "TenPercentOwner", ""],
        ["A4", "4", "O Four", "Officer", "CFO"], ["A5", "5", "O Five", "Officer", "CFO"], ["A6", "6", "O Six", "Officer", "Vice President"],
        ["A7", "1", "O One", "Officer", "CEO"], ["A8", "1", "O One", "Director,Officer", "Executive Vice President"], ["A9", "9", "O Nine", "Director", ""],
        ["B1", "10", "D Ten", "Director", ""], ["B2", "11", "Fund", "TenPercentOwner", ""], ["B2", "12", "O Twelve", "Officer", "Senior Vice-President"],
    ])
    nh = ["ACCESSION_NUMBER", "NONDERIV_TRANS_SK", "SECURITY_TITLE", "TRANS_DATE", "TRANS_CODE", "TRANS_SHARES", "TRANS_PRICEPERSHARE", "TRANS_ACQUIRED_DISP_CD"]
    trn = tsv(nh, [
        ["A1", "1", "Common Stock", "03-JAN-2021", "P", "10000", "12.00", "A"],            # 120,000
        ["A2", "1", "Common Stock", "04-JAN-2021", "P", "10000", "12.00", "A"],
        ["A3", "1", "Common Stock", "05-JAN-2021", "P", "10000", "12.00", "A"],
        ["A4", "1", "Common Stock", "06-JAN-2021", "P", "10000", "12.00", "A"],
        ["A5", "1", "Common Stock", "07-JAN-2021", "P", "10000", "12.00", "A"],
        ["A6", "1", "Common Stock", "08-JAN-2021", "P", "1000", "10.00", "A"],              # 10,000
        ["A7", "1", "Common Stock", "02-FEB-2021", "P", "10000", "12.00", "A"],
        ["A8", "1", "Class A Common Stock", "13-APR-2021", "P", "5000", "20.00", "A"],      # 100,000
        ["A9", "1", "Common Stock", "08-JAN-2021", "P", "10000", "12.00", "A"],
        ["B1", "1", "Common Stock", "10-JAN-2021", "P", "4000", "20.00", "A"],              # 80,000 counts
        ["B1", "2", "Common Stock", "10-JAN-2021", "S", "9000", "20.00", "D"],              # a sale
        ["B1", "3", "Common Stock", "10-JAN-2021", "A", "9000", "0", "A"],                  # an award
        ["B1", "4", "Common Stock", "10-JAN-2021", "M", "9000", "5.00", "A"],               # an option exercise
        ["B1", "5", "Series A Preferred Stock", "10-JAN-2021", "P", "9000", "20.00", "A"],  # preferred
        ["B1", "6", "Restricted Stock Units", "10-JAN-2021", "P", "9000", "20.00", "A"],    # units
        ["B1", "7", "Common Stock", "10-JAN-2021", "P", "9000", "20.00", "D"],              # disposed
        ["B1", "8", "Common Stock", "10-JAN-2021", "P", "9000", "0", "A"],                  # no price
        ["B1", "9", "Common Stock", "10-JAN-2021", "P", "0", "20.00", "A"],                 # no shares
        ["B2", "1", "Common Shares of Beneficial Interest", "31-DEC-2020", "P", "3000", "20.00", "A"],   # 60,000
    ])
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("SUBMISSION.tsv", sub)
        z.writestr("REPORTINGOWNER.tsv", own)
        z.writestr("NONDERIV_TRANS.tsv", trn)
        z.writestr("readme.htm", "<html></html>")
    return zipfile.ZipFile(io.BytesIO(buf.getvalue()))


CIKMAP = pd.Series({1000: "AAA", 2000: "BBB", 3000: "CCC", 4000: "DDD", 5000: "EEE", 6000: "FFF", 7000: "GGG", 8000: "HHH"})


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.lib = load("ib_lib")
        self.lines, self.count = self.lib.parse_quarter(archive())

    def test_only_code_p_acquired_common_priced_lines_of_form_4_are_kept(self):
        b1 = self.lines[self.lines.accession == "B1"]
        self.assertEqual(len(b1), 1)
        self.assertEqual(float(b1.value.iloc[0]), 80_000.0)
        self.assertNotIn("A2", set(self.lines.accession))             # a 4/A
        self.assertNotIn("A5", set(self.lines.accession))             # a Form 3
        c = self.count
        self.assertEqual(c["form4_submissions"], 9)
        self.assertLess(c["common_equity"], c["code_P_acquired"])      # preferred and units fall out here
        self.assertEqual(c["positive_shares_and_price"] - c["lines_out"], 0)

    def test_the_title_rule(self):
        for ok in ("Common Stock", "Class A Common Stock", "Ordinary Shares", "Common Shares of Beneficial Interest", "Capital Stock", "Stock"):
            self.assertTrue(self.lib.is_common(ok), ok)
        for no in ("Series A Preferred Stock", "Restricted Stock Units", "Stock Option (right to buy)", "Warrants", "Convertible Notes", "Depositary Shares", "Common Units", "", None):
            self.assertFalse(self.lib.is_common(no), no)

    def test_dates_are_iso_and_owner_flags_come_from_the_filing(self):
        a1 = self.lines[self.lines.accession == "A1"].iloc[0]
        self.assertEqual(a1.filing_date, "2021-01-05")
        self.assertEqual(a1.trans_date, "2021-01-03")
        self.assertTrue(a1.officer and a1.top_exec and not a1.director)
        b2 = self.lines[self.lines.accession == "B2"].iloc[0]
        self.assertEqual(b2.n_owners, 2)
        self.assertTrue(b2.tenpct and b2.officer)
        self.assertFalse(b2.top_exec)                                  # 'Senior Vice-President' is not a top executive
        a8 = self.lines[self.lines.accession == "A8"].iloc[0]
        self.assertTrue(a8.officer and a8.director and not a8.top_exec)  # 'Executive Vice President'

    def test_the_top_executive_title_rule(self):
        for t in ("President", "President and CEO", "Chief Financial Officer", "CFO", "Chief Executive Officer"):
            self.assertTrue(self.lib._TOP.search(t), t)
        for t in ("Vice President", "Executive Vice-President", "Senior Vice President, Sales", "Controller"):
            self.assertFalse(self.lib._TOP.search(t), t)

    def test_the_reader_works_without_the_10b5_column_and_names_a_missing_column(self):
        lines, _ = self.lib.parse_quarter(archive(with_flag=False))
        self.assertTrue((lines.aff10b5one == "").all())
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("SUBMISSION.tsv", "ACCESSION_NUMBER\tFILING_DATE\n")
            z.writestr("REPORTINGOWNER.tsv", "ACCESSION_NUMBER\n")
            z.writestr("NONDERIV_TRANS.tsv", "ACCESSION_NUMBER\n")
        with self.assertRaises(KeyError) as cm:
            self.lib.parse_quarter(zipfile.ZipFile(io.BytesIO(buf.getvalue())))
        self.assertIn("DOCUMENT_TYPE", str(cm.exception))


class EventTests(unittest.TestCase):
    def setUp(self):
        self.lib = load("ib_lib")
        self.lines, _ = self.lib.parse_quarter(archive())

    def test_purchase_filings_need_an_officer_or_director_no_10b5_flag_and_the_minimum_value(self):
        f = self.lib.purchase_filings(self.lines)
        self.assertEqual(set(f.accession), {"A1", "A7", "A8", "A9", "B1", "B2"})
        self.assertNotIn("A3", set(f.accession))                       # only a 10% owner
        self.assertNotIn("A4", set(f.accession))                       # 10b5-1
        self.assertNotIn("A6", set(f.accession))                       # 10,000 < 50,000
        self.assertEqual(float(f.set_index("accession").loc["B2", "total_value"]), 60_000.0)

    def test_chain_keeps_the_first_filing_and_one_ninety_days_after_it_not_one_at_thirty(self):
        events, funnel = self.lib.build_events(self.lines, CIKMAP)
        self.assertEqual(set(events.accession), {"A1", "A8", "B1", "B2"})      # A7 (30 days after A1) is chained out; A9's issuer has no ticker
        self.assertEqual(funnel["purchase_filings"], 6)
        self.assertEqual(funnel["with_panel_ticker"], 5)
        a8 = events.set_index("accession").loc["A8"]
        self.assertEqual((a8.public_date, a8.ticker, a8.stage), ("2021-04-15", "AAA", 1))

    def test_the_chain_compares_with_the_last_event_not_the_last_filing(self):
        d = pd.to_datetime("2021-01-04")
        rows = [{"accession": f"x{i}", "filing_date": (d + pd.Timedelta(days=45 * i)).strftime("%Y-%m-%d"), "issuer_cik": 1} for i in range(5)]
        kept = self.lib.chain_events(pd.DataFrame(rows))
        # events at day 0, 90 (the third filing), 180 (the fifth): a filing 45 days after an event is dropped, one 90 days after is kept
        self.assertEqual(list(kept.accession), ["x0", "x2", "x4"])
        self.assertEqual(self.lib.chain_events(pd.DataFrame(rows[:2] + [dict(rows[2], issuer_cik=2)])).shape[0], 2)    # another issuer starts its own chain... x1 dropped

    def test_stages_follow_the_filing_date_and_seed_filings_are_not_events(self):
        lines = self.lines.copy()
        # move A1 to the seed period (before stage 1) and A8 into 2023
        lines.loc[lines.accession == "A1", ["filing_date", "trans_date"]] = ["2020-12-30", "2020-12-28"]
        lines.loc[lines.accession == "A8", ["filing_date", "trans_date"]] = ["2023-02-01", "2023-01-30"]
        events, _ = self.lib.build_events(lines, CIKMAP)
        got = events.set_index("accession")
        self.assertNotIn("A1", got.index)                              # filed 2020-12-30: it seeds the chain only
        self.assertEqual(got.loc["A8", "stage"], 2)
        self.assertEqual(got.loc["B1", "stage"], 1)

    def test_lag_is_the_filing_date_minus_the_last_trade_date(self):
        events, _ = self.lib.build_events(self.lines, CIKMAP)
        self.assertEqual(int(events.set_index("accession").loc["A1", "lag_days"]), 2)


class StatsTests(unittest.TestCase):
    def setUp(self):
        self.st = load("ib_stats")

    def frame(self, n=3000, effect=0.0, seed=1):
        rng = np.random.default_rng(seed)
        d = pd.Timestamp("2021-01-04") + pd.to_timedelta(rng.integers(0, 720, n), unit="D")
        ex = rng.normal(effect, 0.25, n)
        return pd.DataFrame({"entry_date": d.strftime("%Y-%m-%d"), "excess": ex, "net_return": ex + 0.01, "control_mean": 0.01})

    def test_the_bootstrap_se_matches_the_analytic_cluster_se_for_a_mean(self):
        f = self.frame()
        w = self.st.week_id(f.entry_date)
        boot = self.st.Boot(w, 4000, 7)
        s = boot.mean(f.excess, w)
        by = {}
        for v, k in zip(f.excess - f.excess.mean(), w):
            by[k] = by.get(k, 0.0) + v
        se = float(np.sqrt(sum(x * x for x in by.values()))) / len(f)
        self.assertAlmostEqual(s["se"], se, delta=0.15 * se)

    def test_a_planted_excess_is_found_and_none_is_not(self):
        good, none = self.frame(effect=0.04), self.frame(effect=0.0)
        for f, expect in ((good, True), (none, False)):
            w = self.st.week_id(f.entry_date)
            s = self.st.Boot(w, 3000, 3).mean(f.excess, w)
            self.assertEqual(s["t"] >= 3.0, expect, s)

    def test_gates_need_every_condition(self):
        f = self.frame(effect=0.04)
        w = self.st.week_id(f.entry_date)
        stats = self.st.Boot(w, 3000, 3).mean(f.excess, w)
        gates, yr = self.st.stage1_gates(f, stats, {20: 0.01, 120: 0.05})
        self.assertTrue(all(gates.values()), (gates, yr))
        self.assertEqual(self.st.stage1_reading(gates, stats), "STAGE1_PASS: run stage 2")
        g2, _ = self.st.stage1_gates(f, stats, {20: -0.001, 120: 0.05})                     # sign flips at hold 20
        self.assertFalse(g2["G4_excess_gt_0_at_holds_20_and_120"])
        small = self.frame(effect=0.012, n=6000)                                            # real but below 2%
        w2 = self.st.week_id(small.entry_date)
        s2 = self.st.Boot(w2, 3000, 3).mean(small.excess, w2)
        g3, _ = self.st.stage1_gates(small, s2, {20: 0.01, 120: 0.01})
        self.assertFalse(g3["G2_excess_ge_2pct_and_winsorised_ge_1pct"])
        one_year = f[f.entry_date.str[:4] == "2021"]
        g4, yr4 = self.st.stage1_gates(one_year, stats, {20: 0.01, 120: 0.05})
        self.assertFalse(g4["G3_excess_gt_0_in_2021_and_2022"])
        self.assertEqual(yr4["2022"]["n"], 0)

    def test_the_readings(self):
        base = {"G1_excess_t_ge_3": False, "G2_excess_ge_2pct_and_winsorised_ge_1pct": False, "G3_excess_gt_0_in_2021_and_2022": False, "G4_excess_gt_0_at_holds_20_and_120": False}
        self.assertEqual(self.st.stage1_reading(base, {"mean": 0.01, "t": 2.0}), "LEAN_WITHOUT_SIZE: no stage 2")
        self.assertEqual(self.st.stage1_reading(base, {"mean": -0.01, "t": -2.0}), "NO_LARGE_EFFECT: no stage 2")
        self.assertEqual(self.st.stage1_reading(dict(base, G1_excess_t_ge_3=True), {"mean": 0.01, "t": 3.2}), "REAL_BUT_SMALL_OR_UNSTABLE: no stage 2")

    def test_go_rule_counts_total_and_each_year(self):
        f = self.frame(n=1600)
        ok, info = self.st.go_check(f)
        self.assertTrue(ok, info)
        ok2, _ = self.st.go_check(f[f.entry_date.str[:4] == "2021"])
        self.assertFalse(ok2)
        ok3, _ = self.st.go_check(self.frame(n=1000))
        self.assertFalse(ok3)

    def test_stage2_gates(self):
        self.assertTrue(all(self.st.stage2_gates({"mean": 0.012, "t": 1.7}).values()))
        self.assertFalse(all(self.st.stage2_gates({"mean": 0.008, "t": 2.5}).values()))
        self.assertFalse(all(self.st.stage2_gates({"mean": 0.02, "t": 1.0}).values()))


if __name__ == "__main__":
    unittest.main()
