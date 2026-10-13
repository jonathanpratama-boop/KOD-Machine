"""US pipeline milestone: corporate-action verification, approval, shared execution, 5% rule.
Synthetic data only; no ledger, network or committed market files are written."""

import json
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from idxsig import exec_us, execution, paper, us_actions
from tests.test_paper_markets import DATA, gframe

KEY = ["ticker", "effective_session", "numerator", "denominator"]


def events(*rows):
    cols = KEY + ["payload_sha256"]
    return pd.DataFrame([dict(zip(cols, r)) for r in rows], columns=cols)


def schedule(*rows):
    cols = KEY + ["payload_sha256", "status"]
    return pd.DataFrame([dict(zip(cols, r)) for r in rows], columns=cols)


class Verification(unittest.TestCase):
    """Each relevant provider event needs exactly one matching record; nothing missing is silent."""

    def recon(self, ev, sc, accepted=("VERIFIED",), read_through="2023-12-29", window=None):
        return us_actions.reconcile_schedule(ev, sc, "2023-01-03", {"AAA", "BBB"}, accepted, read_through, window)

    def test_missing_record_is_unresolved_not_accepted(self):
        ev = events(("AAA", "2024-05-01", 1.0, 10.0, "h1"), ("BBB", "2024-06-01", 2.0, 1.0, "h2"))
        out = self.recon(ev, schedule(("AAA", "2024-05-01", 1.0, 10.0, "h1", "VERIFIED")))
        by = dict(zip(out["ticker"], out["status"]))
        self.assertEqual(by["AAA"], "VERIFIED")
        self.assertEqual(by["BBB"], "UNRESOLVED_NO_RECORD")
        self.assertFalse(out.set_index("ticker").loc["BBB", "accepted"])

    def test_duplicate_records_are_unresolved(self):
        ev = events(("AAA", "2024-05-01", 1.0, 10.0, "h1"))
        sc = schedule(("AAA", "2024-05-01", 1.0, 10.0, "h1", "VERIFIED"), ("AAA", "2024-05-01", 1.0, 10.0, "h1", "NO_EVIDENCE"))
        self.assertEqual(self.recon(ev, sc)["status"].tolist(), ["UNRESOLVED_DUPLICATE_RECORD"])

    def test_record_from_a_different_payload_is_unresolved(self):
        ev = events(("AAA", "2024-05-01", 1.0, 10.0, "h1"))
        sc = schedule(("AAA", "2024-05-01", 1.0, 10.0, "OTHER", "VERIFIED"))
        self.assertEqual(self.recon(ev, sc)["status"].tolist(), ["UNRESOLVED_PAYLOAD_MISMATCH"])

    def test_events_before_the_window_and_of_other_names_are_out_of_scope(self):
        ev = events(("AAA", "2022-05-01", 1.0, 10.0, "h"), ("ZZZ", "2024-05-01", 1.0, 10.0, "h"))
        self.assertEqual(len(self.recon(ev, schedule())), 0)

    def test_share_count_records_inside_the_window_are_not_accepted(self):
        ev = events(("AAA", "2023-06-01", 1.0, 10.0, "h1"), ("BBB", "2024-06-01", 1.0, 10.0, "h2"))
        sc = schedule(("AAA", "2023-06-01", 1.0, 10.0, "h1", "SHARES_CONFIRMED"),
                      ("BBB", "2024-06-01", 1.0, 10.0, "h2", "SHARES_CONFIRMED"))
        out = self.recon(ev, sc, accepted=us_actions.RESEARCH_ACCEPTED, window="2023-12-29")
        by = dict(zip(out["ticker"], out["status"]))
        self.assertEqual(by["AAA"], "UNRESOLVED_SHARES_OUTSIDE_WINDOW")
        self.assertEqual(by["BBB"], "SHARES_CONFIRMED")

    def test_share_counts_refused_for_a_panel_reading_past_their_window(self):
        ev = events(("AAA", "2024-06-01", 1.0, 10.0, "h"))
        sc = schedule(("AAA", "2024-06-01", 1.0, 10.0, "h", "SHARES_CONFIRMED"))
        with self.assertRaisesRegex(ValueError, "permitted for panels reading through 2023-12-29"):
            self.recon(ev, sc, accepted=us_actions.RESEARCH_ACCEPTED, read_through="2024-12-31", window="2023-12-29")
        with self.assertRaisesRegex(ValueError, "declares no share-count window"):
            self.recon(ev, sc, accepted=us_actions.RESEARCH_ACCEPTED, window=None)

    def test_inputs_are_bound_by_hash_not_name(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(us_actions, "PKG_ROOT", Path(tmp)):
            raw = Path(tmp) / "yahoo_us-x.jsonl"
            raw.write_text("raw\n")
            rows = Path(tmp) / "sched.csv"
            rows.write_text("ticker\n")
            cov_rows = Path(tmp) / "cov.csv"
            cov_rows.write_text("ticker\n")
            good = {"raw_manifest": raw.name, "raw_manifest_sha256": us_actions.sha256_path(raw),
                    "schedule": "sched.csv", "schedule_sha256": us_actions.sha256_path(rows)}
            cov = {"raw_manifest": raw.name, "raw_manifest_sha256": us_actions.sha256_path(raw),
                   "rows": "cov.csv", "rows_sha256": us_actions.sha256_path(cov_rows)}
            us_actions.check_bound_inputs(raw, good, cov)  # all bound: no error
            with self.assertRaisesRegex(RuntimeError, "different raw manifest"):
                us_actions.check_bound_inputs(raw, {**good, "raw_manifest_sha256": "0" * 64})
            with self.assertRaisesRegex(RuntimeError, "schedule rows differ"):
                us_actions.check_bound_inputs(raw, {**good, "schedule_sha256": "0" * 64})
            with self.assertRaisesRegex(RuntimeError, "coverage was built from a different raw manifest"):
                us_actions.check_bound_inputs(raw, good, {**cov, "raw_manifest_sha256": "0" * 64})
            with self.assertRaisesRegex(RuntimeError, "coverage rows differ"):
                us_actions.check_bound_inputs(raw, good, {**cov, "rows_sha256": "0" * 64})


class Capacity(unittest.TestCase):
    """FILL-B-v2: every session's volume in the entry session's share units."""

    def series(self, ratio, split_at=10, n=25, traded_before=1000.0):
        # ratio = new shares per old share (2.0 forward 2:1, 0.1 reverse 1:10). True traded shares are
        # traded_before before the split and traded_before x ratio after; the provider's adjusted
        # volume is in the latest units: traded_before x ratio every day. F = ratio before the split.
        adj_volume = np.full((1, n), traded_before * ratio)
        uf = np.where(np.arange(n) < split_at, ratio, 1.0)[None, :]
        present = np.ones((1, n), bool)
        return adj_volume, present, uf

    def test_forward_and_reverse_splits_keep_capacity_in_entry_units(self):
        for ratio, split_at in ((2.0, 10), (2.0, 16), (0.1, 10), (0.1, 16)):
            vol, present, uf = self.series(ratio, split_at)
            s, e = 20, 21  # the 20-session window 1..20 spans the split at 10
            v2 = execution.decision_capacity(vol, present, uf, [0], [s], [e])[0]
            self.assertAlmostEqual(v2, 1000.0 * ratio)  # all sessions in post-split (entry) shares
            self.assertAlmostEqual(exec_us.capacity_shares(vol[0], present[0], uf[0], s), 1000.0 * ratio)

    def test_a_split_between_signal_and_entry_converts_the_shares(self):
        vol, present, uf = self.series(2.0, split_at=21)  # effective on the entry session
        cap = exec_us.capacity_shares(vol[0], present[0], uf[0], 20)
        self.assertAlmostEqual(cap, 1000.0)  # signal-session shares
        self.assertAlmostEqual(execution.decision_capacity(vol, present, uf, [0], [20], [21])[0], 2000.0)

    def test_v1_mixed_units_are_kept_only_for_reproduction(self):
        """FILL-B-v1 put pre-split sessions in pre-split shares: documents the defect B2 fixes."""
        vol, present, uf = self.series(0.1, split_at=16)  # 15 of the 20 sessions before a 1:10 reverse split
        vol_v1 = np.where(present, vol / uf, np.nan)[0, 1:21]
        self.assertAlmostEqual(float(np.nanmedian(vol_v1)), 1000.0)  # pre-split shares: 10x the entry-unit capacity
        self.assertAlmostEqual(execution.decision_capacity(vol, present, uf, [0], [20], [21])[0], 100.0)


class FivePercentRule(unittest.TestCase):
    def bars(self, open_e, n=10):
        o = np.full(n, 100.0)
        o[1] = open_e
        return o, o + 2, o - 1, o.copy(), np.full(n, 1e6), np.ones(n, bool), np.ones(n)

    def test_signal_100_stop_95_entry_110_is_rejected(self):
        plan = exec_us.make_plan(100.0, 95.0, 1e6)
        self.assertEqual(plan["max_entry"], 100.0)  # 95 / 0.95: the highest entry with a 5% stop
        res = exec_us.execute(*self.bars(110.0), 0, plan)
        self.assertEqual(res["status"], "REJECTED_STOP_TOO_WIDE")
        self.assertAlmostEqual(res["stop_distance_at_open"], 15 / 110)

    def test_an_entry_inside_the_band_is_filled_and_sized_at_the_permitted_entry(self):
        plan = exec_us.make_plan(100.0, 95.0, 1e6)
        risk = plan["risk_per_share"]
        self.assertAlmostEqual(risk, 5.0 + 100.0 * (plan["cost_in_at_max_entry"] + plan["cost_out_at_max_entry"]))
        self.assertLessEqual(plan["shares"] * risk, 0.01 * exec_us.SPEC.equity_usd)
        self.assertLessEqual(plan["shares"] * plan["max_entry"], 0.20 * exec_us.SPEC.equity_usd)
        res = exec_us.execute(*self.bars(99.0), 0, plan)
        self.assertEqual(res["status"], "FILLED")
        self.assertLessEqual(res["stop_distance_at_entry"], 0.05)

    def test_policy_v3_allowed_wider_stops_v5_does_not(self):
        warnings.simplefilter("ignore")
        df = gframe(spike=(7, 79))
        v3 = paper.scan_frame(df, DATA, market="US", policy=paper.POLICY_ID_V3)["decisions"][0]
        v5 = paper.scan_frame(df, DATA, market="US")["decisions"][0]
        close = v3["verified_price"]["close"]
        self.assertLessEqual(v3["plan"]["invalidation"], close * 0.95)  # v3: 5-15% below the signal close
        self.assertEqual(v5["policy"]["policy_id"], "PAPER-POLICY-v5")
        p = v5["plan"]
        self.assertLessEqual((p["max_entry"] - p["invalidation"]) / p["max_entry"], 0.05 + 1e-9)


class Approval(unittest.TestCase):
    DET = {"precision": 0.05, "lift_vs_matched_random": 5.0, "p_one_sided_vs_matched": 0.001}

    def pinned(self, market, trading):
        pin = {"run_id": "R1", "config_sha256": "c" * 64, "execution": paper.PLAN_EXECUTION[market]}
        return mock.patch.dict(paper.APPROVAL_PINS, {market: pin}), {
            **self.DET, "trading": {"run_id": "R1", "config_sha256": "c" * 64, **trading}}

    def test_a_losing_strategy_beating_a_worse_baseline_is_not_approved(self):
        patch, ev = self.pinned("US", {"avg_net_return": -0.01, "matched_random_avg_net_return": -0.03,
                                       "p_one_sided": 0.001})
        with patch:
            ok, why = paper.approval(ev, "US")
        self.assertFalse(ok)
        self.assertIn("not positive", why)

    def test_positive_but_not_above_baseline_is_not_approved(self):
        patch, ev = self.pinned("US", {"avg_net_return": 0.01, "matched_random_avg_net_return": 0.02,
                                       "p_one_sided": 0.001})
        with patch:
            self.assertFalse(paper.approval(ev, "US")[0])

    def test_positive_significant_and_above_baseline_is_approved(self):
        patch, ev = self.pinned("US", {"avg_net_return": 0.02, "matched_random_avg_net_return": 0.0,
                                       "p_one_sided": 0.001})
        with patch:
            self.assertEqual(paper.approval(ev, "US"), (True, "approved"))

    def test_changed_config_or_other_execution_is_not_approved(self):
        patch, ev = self.pinned("US", {"avg_net_return": 0.02, "matched_random_avg_net_return": 0.0,
                                       "p_one_sided": 0.001})
        with patch:
            ev["trading"]["config_sha256"] = "d" * 64
            self.assertIn("no longer has the pinned configuration", paper.approval(ev, "US")[1])
        with mock.patch.dict(paper.APPROVAL_PINS, {"US": {"run_id": "R1", "config_sha256": "c" * 64,
                                                          "execution": "something else"}}):
            ev["trading"]["config_sha256"] = "c" * 64
            self.assertIn("did not test the execution", paper.approval(ev, "US")[1])

    def test_appending_a_run_does_not_change_the_evidence(self):
        """Guards against: the evidence lookup taking the LAST matching run in RUNS.jsonl."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "results").mkdir()
            runs = []
            for run_id, avg in (("20260101T000000Z_X_v1", -0.02), ("20260102T000000Z_X_v1", 0.05)):
                d = root / "results" / "runs" / run_id
                d.mkdir(parents=True)
                cfg = {"start": "2023-01-01", "end": "2023-12-31", "run": run_id}
                (d / "summary.json").write_text(json.dumps({
                    "run_id": run_id, "config": cfg, "rule": {"text": "Selected: G2_RET30"},
                    "rule_trades": {"scored": 10, "fill_rate": 1.0, "status_counts": {}},
                    "random_matched": {"avg_net_return": {"observed": avg, "random_mean": 0.0,
                                                          "p_value_one_sided": 0.001}}}))
                runs.append({"dir": f"results/runs/{run_id}"})
            (root / "results" / "RUNS.jsonl").write_text("\n".join(json.dumps(r) for r in runs) + "\n")
            pin = {"run_id": "20260101T000000Z_X_v1",
                   "config_sha256": paper.config_sha256({"start": "2023-01-01", "end": "2023-12-31",
                                                         "run": "20260101T000000Z_X_v1"}),
                   "execution": paper.PLAN_EXECUTION["US"]}
            with mock.patch.object(paper, "PKG_ROOT", root), mock.patch.dict(paper.APPROVAL_PINS, {"US": pin}):
                t = paper._pinned_trading("US")
            self.assertEqual(t["run_id"], "20260101T000000Z_X_v1")  # not the later, better-looking run
            self.assertEqual(t["config_sha256"], pin["config_sha256"])
            self.assertFalse(paper.approval({**self.DET, "trading": t}, "US")[0])


class SharedExecution(unittest.TestCase):
    """The paper scorer and the historical replay are the same code: same bars, same outcome."""

    CASES = ((-0.06, 0.01), (-0.24, 0.01), (-0.24, -0.03), (-0.25, 0.01))  # rejected, filled, filled, filled

    def case(self, gap, tail):
        warnings.simplefilter("ignore")
        base = gframe(spike=(7, 70), tail=tail, gap=gap)
        cut = base[base["date"] <= base["date"].unique()[70]]
        dec = paper.scan_frame(cut, DATA, market="US")["decisions"][0]
        return base, dec

    def test_identical_inputs_give_identical_paper_and_replay_outcomes(self):
        statuses = set()
        for gap, tail in self.CASES:
            base, dec = self.case(gap, tail)
            self.assertEqual(dec["plan"]["exec_plan"]["exec_version"], exec_us.EXEC_VERSION)
            m = paper._market(base, "US")
            paper_out = paper.score(dec, m, price_units=None)
            n = list(m.tickers).index(dec["instrument"]["ticker"])
            s = int(np.flatnonzero(m.dates.astype(str) == dec["signal_session"])[0])
            replay = exec_us.replay(m.with_units(np.ones(m.shape)), [(n, s)], exec_us.signal_low_invalidation)[0]
            self.assertEqual(replay["plan"], dec["plan"]["exec_plan"])
            self.assertEqual(replay["result"], paper_out["execution"])
            statuses.add(paper_out["execution"]["status"])
        self.assertEqual(statuses, {"FILLED", "REJECTED_STOP_TOO_WIDE"})

    def test_a_verified_reverse_split_in_the_hold_gives_the_same_outcome_both_ways(self):
        """Paper converts units with the SEC-verified split schedule, replay with the panel's
        unit_factor: same bars, same answer, and the same as with no split at all."""
        base, dec = self.case(-0.24, 0.01)
        m0 = paper._market(base, "US")
        plain = paper.score(dec, m0, price_units=None)["execution"]
        dates = sorted(base["date"].unique())
        eff = str(pd.Timestamp(dates[73]).date())
        split = base.copy()
        rows = split["ticker"] == dec["instrument"]["ticker"]
        for col in ("previous", "open", "high", "low", "close"):
            split.loc[rows, col] *= 10  # the provider rescales the whole history after a 1:10 reverse split
        split.loc[rows, "volume"] /= 10
        m = paper._market(split, "US")
        units = {"convention": "SPLIT_ONLY", "actions": [{"effective_session": eff, "new_shares": 1.0,
                                                           "old_shares": 10.0}],
                 "adjustment_reference": str(m.dates[-1]), "coverage_complete": True, "rtol": 1e-6}
        paper_out = paper.score(dec, m, price_units=units)["execution"]
        n = list(m.tickers).index(dec["instrument"]["ticker"])
        sidx = int(np.flatnonzero(m.dates.astype(str) == dec["signal_session"])[0])
        uf = np.ones(m.shape)
        uf[n, m.dates.astype(str) < eff] = 0.1
        replay = exec_us.replay(m.with_units(uf), [(n, sidx)], exec_us.signal_low_invalidation)[0]["result"]
        for out in (paper_out, replay):
            self.assertEqual(out["status"], plain["status"])
            self.assertEqual(out["exit_reason"], plain["exit_reason"])
            for key in ("entry_price_as_traded", "gross_return", "entry_cost_rate"):
                self.assertAlmostEqual(out[key], plain[key], places=9)
        for key in ("net_return", "exit_cost_rate", "exit_price_as_traded", "net_pnl_usd"):
            self.assertAlmostEqual(paper_out[key], replay[key], places=9)
        # after a 1:10 reverse split the shares are sold at 10x the price, in that price's cost tier
        self.assertNotEqual(paper_out["exit_cost_rate"], plain["exit_cost_rate"])
        self.assertAlmostEqual(paper_out["exit_price_as_traded"], 10 * plain["exit_price_as_traded"], places=6)

    def test_entry_is_the_next_open_never_the_signal_close(self):
        base, dec = self.case(-0.24, 0.01)
        m = paper._market(base, "US")
        out = paper.score(dec, m, price_units=None)["execution"]
        n = list(m.tickers).index(dec["instrument"]["ticker"])
        s = int(np.flatnonzero(m.dates.astype(str) == dec["signal_session"])[0])
        self.assertEqual(out["status"], "FILLED")
        self.assertEqual(out["entry_session_index"], s + 1)
        self.assertAlmostEqual(out["entry_price_as_traded"], m.open[n, s + 1])
        self.assertNotAlmostEqual(out["entry_price_as_traded"], m.close[n, s])


class ExitRules(unittest.TestCase):
    def run_bars(self, lows, opens=None, closes=None):
        n = 10
        o = np.array(opens or [100.0] * n)
        c = np.array(closes or [100.0] * n)
        lo = np.array(lows)
        h = np.maximum(o, c) + 1
        plan = exec_us.make_plan(100.0, 96.0, 1e6)
        return exec_us.execute(o, h, lo, c, np.full(n, 1e6), np.ones(n, bool), np.ones(n), 0, plan)

    def test_resting_stop_fills_at_the_stop_intraday(self):
        r = self.run_bars([99, 99, 99, 95.5, 99, 99, 99, 99, 99, 99])
        self.assertEqual((r["exit_reason"], r["exit_price_as_traded"]), ("STOP", 96.0))

    def test_gap_through_the_stop_fills_at_the_open(self):
        opens = [100.0] * 10
        opens[3] = 94.0
        r = self.run_bars([99, 99, 99, 93.0, 99, 99, 99, 99, 99, 99], opens=opens)
        self.assertEqual((r["exit_reason"], r["exit_price_as_traded"]), ("STOP_GAP_AT_OPEN", 94.0))

    def test_time_exit_at_the_planned_close_and_excursions_are_separate(self):
        closes = [100.0, 100.0, 103.0, 101.0, 102.0, 104.0, 105.0, 100.0, 100.0, 100.0]
        r = self.run_bars([99] * 10, closes=closes)
        self.assertEqual(r["exit_reason"], "TIME_EXIT_AT_CLOSE")
        self.assertEqual(r["exit_session_index"], 1 + exec_us.SPEC.exit_after_sessions)
        self.assertAlmostEqual(r["gross_return"], 105.0 / 100.0 - 1)
        self.assertIn("not executable", r["close_excursion"]["note"])
        self.assertIn("not executable", r["intraday_excursion"]["note"])
        self.assertGreater(r["intraday_excursion"]["max_high"], r["net_return"])


if __name__ == "__main__":
    unittest.main()
