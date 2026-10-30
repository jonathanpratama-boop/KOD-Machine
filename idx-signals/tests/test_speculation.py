"""Speculation Register v1 (idxsig.speculation). Synthetic data only, no network. Each test names the failure it
guards against."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import warnings
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from idxsig import paper, speculation as sp
from idxsig.execution import Market

PLAN = sp.windows()["BASE5"]


def us_market(n_tickers=8, n_sessions=40, price=25.0, start="2026-10-01") -> tuple[Market, dict]:
    """Every name trades every session at `price`; opens equal closes. Mutate `a` then build() again."""
    dates = np.busday_offset(np.datetime64(start, "D"), np.arange(n_sessions), roll="forward")
    shape = (n_tickers, n_sessions)
    a = {"close": np.full(shape, price), "prev": np.full(shape, price), "high": np.full(shape, price * 1.01),
         "low": np.full(shape, price * 0.99), "volume": np.full(shape, 100_000.0), "value": np.full(shape, price * 100_000),
         "present": np.ones(shape, dtype=bool), "open": np.full(shape, price)}
    tickers = np.array([f"U{i:02d}" for i in range(n_tickers)])
    return build(tickers, dates, a), a


def build(tickers, dates, a, price_limits=False) -> Market:
    a["prev"] = np.concatenate([a["close"][:, :1], a["close"][:, :-1]], axis=1)  # previous = prior close
    a["value"] = a["close"] * a["volume"]
    return Market.build(tickers, dates, a["close"], a["prev"], a["high"], a["low"], a["volume"], a["value"], a["present"],
                        None, opens=a["open"], price_limits=price_limits)


def set_closes(a, row, start, closes, opens=None):
    for k, c in enumerate(closes):
        a["close"][row, start + k] = c
        a["high"][row, start + k] = max(c, a["close"][row, start + k - 1]) * 1.001
        a["low"][row, start + k] = min(c, a["close"][row, start + k - 1]) * 0.999
        a["open"][row, start + k] = opens[k] if opens is not None else c


def net(gross, fee_in, fee_out):
    return (1 + gross) * (1 - fee_out) / (1 + fee_in) - 1


class StudentT(unittest.TestCase):
    def test_one_sided_p_matches_tables(self):
        """Guards against: a wrong t tail would move every look's verdict (stdlib implementation, no scipy)."""
        self.assertAlmostEqual(sp.t_sf(2.0, 10), 0.0367, places=4)
        self.assertAlmostEqual(sp.t_sf(3.0, 14), 0.00478, places=5)
        self.assertAlmostEqual(sp.t_sf(0.0, 5), 0.5, places=6)
        self.assertAlmostEqual(sp.t_sf(-1.5, 20), 0.9254, places=4)
        self.assertAlmostEqual(sp.t_sf(1.96, 10 ** 6), 0.025, places=3)


class Simulation(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore")

    def test_base5_enters_at_the_open_and_exits_at_the_fifth_close_with_tiered_costs(self):
        """Guards against: entering at the close, exiting a session early, or costing a $25 name as a $1 name."""
        m, a = us_market()
        d = 10
        set_closes(a, 0, d + 1, [26, 27, 28, 29, 30, 31, 32], opens=[25.5, 27, 28, 29, 30, 31, 32])
        m = build(m.tickers, m.dates, a)
        r = sp.simulate(m, 0, d, PLAN, "US")
        t = r["trade"]
        self.assertEqual(r["status"], "TRADED")
        self.assertEqual((t["entry_basis"], t["entry_price"], t["entry_lag_sessions"]), ("open", 25.5, 1))
        self.assertEqual(t["exit_session"], str(m.dates[d + 6]))
        self.assertEqual(t["exit_reason"], "horizon")
        self.assertAlmostEqual(t["gross_return"], 31 / 25.5 - 1)
        self.assertAlmostEqual(t["net_return"], net(31 / 25.5 - 1, 0.0005, 0.0005 + 0.0000278))
        self.assertAlmostEqual(t["mfe"], 31 / 25.5 - 1)
        self.assertAlmostEqual(t["mae"], 26 / 25.5 - 1)
        self.assertEqual(t["sessions_held"], 5)

    def test_window_still_open_returns_none(self):
        """Guards against: resolving a window from bars that do not reach its exit."""
        m, a = us_market(n_sessions=14)
        self.assertIsNone(sp.simulate(m, 0, 10, PLAN, "US"))
        self.assertIsNone(sp.simulate(m, 0, 13, PLAN, "US"))

    def test_idx_entry_refused_when_locked_at_ara_and_sale_rolls_while_locked_at_arb(self):
        """Guards against: buying a name nobody sells, or selling into a locked-down close."""
        from tests.support import flat_market, rebuild

        tickers, dates, a = flat_market(n_tickers=2, n_sessions=30, price=1000.0)
        d = 10
        a["close"][0, d + 1] = 1250  # +25% on a Rp1,000 reference: locked at the upper limit
        a["high"][0, d + 1] = 1250
        a["prev"][0, d + 2:] = 1250
        a["close"][0, d + 2:] = 1250
        a["high"][0, d + 2:] = 1262
        a["low"][0, d + 2:] = 1240
        m = rebuild(tickers, dates, a)
        self.assertTrue(m.lock_up[0, d + 1])
        r = sp.simulate(m, 0, d, PLAN, "IDX")
        self.assertEqual(r["status"], "NOT_FILLABLE")
        tickers, dates, a = flat_market(n_tickers=2, n_sessions=30, price=1000.0)
        x = d + 6
        a["close"][1, x] = 750  # -25%: locked at the lower limit on the exit session
        a["low"][1, x] = 750
        a["prev"][1, x + 1:] = 750
        a["close"][1, x + 1:] = 760
        a["high"][1, x + 1:] = 770
        a["low"][1, x + 1:] = 750
        m = rebuild(tickers, dates, a)
        self.assertTrue(m.lock_down[1, x])
        r = sp.simulate(m, 1, d, PLAN, "IDX")
        self.assertEqual(r["trade"]["exit_session"], str(m.dates[x + 1]))
        self.assertIn("rolled 1", r["trade"]["exit_reason"])
        self.assertAlmostEqual(r["trade"]["gross_return"], 760 / 1000 - 1)
        self.assertAlmostEqual(r["trade"]["net_return"], net(760 / 1000 - 1, 0.0015, 0.0025))

    def test_a_vanished_name_is_sold_at_its_last_close_only_after_the_grace_period(self):
        """Guards against: a delisted name staying open forever, or being sold before the market has moved on."""
        m, a = us_market(n_sessions=40)
        d = 10
        a["present"][0, d + 4:] = False
        a["close"][0, d + 3] = 20
        m = build(m.tickers, m.dates, a)
        r = sp.simulate(m, 0, d, PLAN, "US")
        self.assertEqual(r["trade"]["exit_reason"], "data end")
        self.assertEqual(r["trade"]["exit_session"], str(m.dates[d + 3]))
        short, a2 = us_market(n_sessions=d + 6 + 5)
        a2["present"][0, d + 4:] = False
        short = build(short.tickers, short.dates, a2)
        self.assertIsNone(sp.simulate(short, 0, d, PLAN, "US"))

    def test_crypto_fixed_entry_is_the_sealing_quote_and_needs_one(self):
        """Guards against: a crypto plan entering at a kline open that nobody could have traded at decision time."""
        m, a = us_market(price=0.5)
        d = 10
        set_closes(a, 0, d + 1, [0.6] * 7)
        m = build(m.tickers, m.dates, a)
        r = sp.simulate(m, 0, d, PLAN, "CRYPTO", quote=0.55)
        self.assertEqual((r["trade"]["entry_basis"], r["trade"]["entry_price"]), ("quote", 0.55))
        self.assertAlmostEqual(r["trade"]["net_return"], net(0.6 / 0.55 - 1, 0.002, 0.002))
        self.assertEqual(sp.simulate(m, 0, d, PLAN, "CRYPTO", quote=None)["status"], "NOT_FILLABLE")

    def test_a_crypto_redenomination_inside_the_window_is_not_a_move(self):
        """Guards against: a 1000x redenomination scored as a 1000x gain (the refuters' COCOS/DREP/LUNA cases)."""
        m, a = us_market(price=0.5, n_sessions=45)
        d = 10
        set_closes(a, 0, d + 1, [0.5, 0.5, 500.0, 500.0, 500.0, 500.0, 500.0] + [500.0] * 20)
        m = build(m.tickers, m.dates, a)
        self.assertEqual(sp.simulate(m, 0, d, PLAN, "CRYPTO", quote=0.5)["status"], "REDENOMINATION")
        self.assertTrue(sp.redenominated(m, 0, d, 20, "CRYPTO"))
        self.assertFalse(sp.redenominated(m, 0, d, 20, "US"))  # a US split is handled by verified units, not here
        self.assertFalse(sp.redenominated(m, 1, d, 20, "CRYPTO"))

    def test_statement_outcomes_follow_the_path_the_trade_and_the_twins(self):
        """Guards against: a statement graded on the wrong horizon, without a position, or without its twins' rate."""
        m, a = us_market(n_sessions=45)
        d = 10
        a["close"][0, d] = 10
        set_closes(a, 0, d + 1, [11, 12, 13.5, 12, 11] + [12] * 10 + [21] + [12] * 5)
        a["close"][1, d] = 10
        set_closes(a, 1, d + 1, [9, 8, 8, 8, 8] + [8] * 16)
        a["close"][2, d] = 10
        set_closes(a, 2, d + 1, [10, 10, 14, 14, 14] + [14] * 16)
        m = build(m.tickers, m.dates, a)
        base = sp.simulate(m, 0, d, PLAN, "US")
        twins = [(1, sp.simulate(m, 1, d, PLAN, "US")), (2, sp.simulate(m, 2, d, PLAN, "US"))]
        statements = [{"id": s["id"], "prior": 0.3, "resolves_with": s["resolves_with"]} for s in sp.protocol()[0]["cone"]]
        out = {c["id"]: c for c in sp.cone_outcomes(statements, "BASE5", m, d, (0, base), twins)}
        self.assertEqual(set(out), {"RUN30_5", "FADE10_5", "GAIN0_5", "BEATS_TWINS_5"})
        self.assertTrue(out["RUN30_5"]["outcome"])  # 13.5 / 10
        self.assertAlmostEqual(out["RUN30_5"]["twins_rate"], 0.5)  # twin 2 reached 14 / 10, twin 1 did not
        self.assertFalse(out["FADE10_5"]["outcome"])
        self.assertAlmostEqual(out["FADE10_5"]["twins_rate"], 0.5)  # twin 1 fell 20%
        self.assertEqual(out["GAIN0_5"]["outcome"], base["trade"]["net_return"] > 0)
        self.assertFalse(out["BEATS_TWINS_5"]["outcome"])  # 11/11 = 0 gross vs twins -20% and +40%: median +10%
        self.assertAlmostEqual(out["RUN30_5"]["brier"], (0.3 - 1) ** 2)
        path = {c["id"]: c for c in sp.cone_outcomes(statements, "PATH20", m, d, (0, None), [(1, None), (2, None)])}
        self.assertEqual(set(path), {"RUN30_20", "DOUBLE_20"})
        self.assertTrue(path["DOUBLE_20"]["outcome"])  # 21 / 10 inside 20 sessions
        self.assertEqual(path["DOUBLE_20"]["twins_rate"], 0.0)
        nothing = {"status": "NOT_FILLABLE", "trade": None}
        out = {c["id"]: c for c in sp.cone_outcomes(statements, "BASE5", m, d, (0, nothing), twins)}
        self.assertIsNone(out["FADE10_5"]["outcome"])
        self.assertIsNone(out["BEATS_TWINS_5"]["brier"])
        self.assertIsNotNone(out["RUN30_5"]["outcome"])


def features_frame(n=60, selected="G2_RET30", candidate="C00", seed=3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        t = f"C{i:02d}"
        close = float(rng.choice([0.5, 3.0, 12.0, 50.0]))
        rows.append({"ticker": t, "session": "2026-10-27", "fresh": True, "eligible": i % 15 != 14,
                     "close": close, "previous": close / 1.3 if t == candidate else close,
                     "adv20_value": float(rng.uniform(1e4, 1e7)), "ret20": float(rng.normal(0, 0.1)),
                     "dd60": float(-rng.uniform(0, 0.6)), "volr": float(rng.uniform(0.5, 5)), "ret1": 0.0,
                     "ret5": 0.0, "cpos": 0.5, "high": close, "low": close, "volume": 1000.0,
                     selected: t in (candidate, "C01")})
    df = pd.DataFrame(rows)
    df.loc[df["ticker"] == candidate, "close"] = 12.0
    df.loc[df["ticker"] == "C05", "fresh"] = False
    return df


class Twins(unittest.TestCase):
    def test_twins_are_matched_eligible_unflagged_names_drawn_deterministically(self):
        """Guards against: a twin that is itself a candidate, a stale or ineligible name, a different price band,
        or a draw that depends on the run."""
        f = features_frame()
        twins, level = sp.draw_twins(f, "C00", ["C00", "C01"], "G2_RET30", "US", seed=7)
        names = [t["ticker"] for t in twins]
        self.assertEqual(len(names), 5)
        self.assertEqual(len(set(names)), 5)
        self.assertNotIn("C00", names)
        self.assertNotIn("C01", names)
        self.assertNotIn("C05", names)
        self.assertTrue(all(f.loc[f["ticker"] == t, "eligible"].iloc[0] for t in names))
        band = sp.PROFILES["US"].band(np.array([12.0]))[0]
        self.assertTrue(all(t["band"] == band for t in twins))
        self.assertIn(level, ("band+liq+mom+dd", "band+liq+mom", "band+liq", "band", "same session only"))
        again, _ = sp.draw_twins(f, "C00", ["C00", "C01"], "G2_RET30", "US", seed=7)
        self.assertEqual(names, [t["ticker"] for t in again])
        other, _ = sp.draw_twins(f, "C00", ["C00", "C01"], "G2_RET30", "US", seed=8)
        self.assertNotEqual(names, [t["ticker"] for t in other])

    def test_idx_twins_exclude_names_under_rp50(self):
        """Guards against: a twin on the special board, which the plan could not trade."""
        f = features_frame()
        f["close"] = 40.0
        f.loc[f["ticker"].isin(["C00", "C07", "C08", "C09", "C10", "C11"]), "close"] = 120.0
        twins, _ = sp.draw_twins(f, "C00", ["C00", "C01"], "G2_RET30", "IDX", seed=1)
        self.assertTrue(all(t["close"] >= 50 for t in twins))
        self.assertEqual(len(twins), 5)


def ledger_records(market="US", session="2026-10-27", ticker="C00", decision="PASS"):
    scan = {"type": "SCAN", "market": market, "scan_id": f"SCAN-{market}-{session}-G2_RET30", "session": session,
            "detector": {"selected": "G2_RET30", "rule_id": "MOONSHOT_E2_US_D1", "version": "v1", "module_sha256": "x"},
            "flags": {"G2_RET30": [ticker, "C01"]}, "candidates_ranked": [ticker, "C01"],
            "features_file": "paper/scans/test/features.csv", "features_sha256": "f" * 64}
    scan["record_hash"] = hashlib.sha256(json.dumps(scan, sort_keys=True).encode()).hexdigest()
    dec = {"type": "DECISION", "market": market, "decision_id": f"{scan['scan_id']}-{ticker}", "scan_id": scan["scan_id"],
           "instrument": {"ticker": ticker}, "signal_session": session, "decision": decision,
           "verified_price": {"close": 12.0, "session": session, "quote": 0.5 if market == "CRYPTO" else None},
           "detector": scan["detector"], "policy": {"policy_id": "PAPER-POLICY-v4", "sha256": "p"}}
    dec["record_hash"] = hashlib.sha256(json.dumps(dec, sort_keys=True).encode()).hexdigest()
    return scan, dec


class Sealing(unittest.TestCase):
    def test_a_set_binds_the_ledger_and_carries_the_protocol_priors(self):
        """Guards against: a set without provenance, or priors typed by hand instead of taken from the protocol."""
        scan, dec = ledger_records()
        now = datetime(2026, 10, 27, 23, 50, tzinfo=timezone.utc)
        s = sp.build_set(dec, scan, features_frame(), [scan, dec], [], now)
        self.assertEqual(s["set_id"], "SPEC-" + dec["decision_id"])
        self.assertEqual(s["decision_record_hash"], dec["record_hash"])
        self.assertEqual(s["scan_record_hash"], scan["record_hash"])
        self.assertEqual(s["entry_cutoff"], "2026-10-28T13:30:00Z")
        self.assertEqual(s["entry"]["basis"], "open")
        self.assertEqual((s["plan"], s["windows"]), ("BASE5", ["BASE5", "PATH20", "NEXT1"]))  # v1.1 (ADDENDUM_1)
        cone = {c["id"]: c for c in s["cone"]}
        self.assertAlmostEqual(cone["RUN30_5"]["prior"], 0.15370018975332067)
        self.assertEqual(cone["FADE10_5"]["prior"], 0.403)
        self.assertEqual(cone["BEATS_TWINS_5"]["prior"], 0.5)
        self.assertEqual(cone["RUN30_20"]["prior"], 0.5)
        self.assertIn("running base rate (n 0", cone["RUN30_20"]["prior_source"])
        self.assertEqual(len(s["twins"]), 5)
        self.assertEqual(s["protocol"]["sha256"], sp.protocol()[1])
        self.assertEqual(s["tag"]["hot_day"], None)  # fewer than ten earlier scans
        self.assertEqual(s["signal"]["close"], 12.0)

    def test_sealing_after_the_cutoff_is_refused(self):
        """Guards against: recording a 'speculation' once its entry has happened."""
        scan, dec = ledger_records()
        late = datetime(2026, 10, 28, 13, 30, tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            sp.build_set(dec, scan, features_frame(), [scan, dec], [], late)
        self.assertEqual(sp.pending_decisions("US", late, [scan, dec], []), [])
        early = datetime(2026, 10, 28, 13, 29, tzinfo=timezone.utc)
        self.assertEqual([d["decision_id"] for d, _ in sp.pending_decisions("US", early, [scan, dec], [])], [dec["decision_id"]])

    def test_not_executable_decisions_and_other_detectors_get_no_set(self):
        """Guards against: speculating on a name under Rp50 or on a benchmark rule's flag."""
        scan, dec = ledger_records(decision="NOT EXECUTABLE")
        now = datetime(2026, 10, 27, 23, 50, tzinfo=timezone.utc)
        self.assertEqual(sp.pending_decisions("US", now, [scan, dec], []), [])
        scan, dec = ledger_records()
        dec["detector"] = {**dec["detector"], "selected": "G5_IGNITION_D"}
        self.assertEqual(sp.pending_decisions("US", now, [scan, dec], []), [])
        scan, dec = ledger_records()
        sealed = [{"type": "SPECULATION_SET", "decision_id": dec["decision_id"]}]
        self.assertEqual(sp.pending_decisions("US", now, [scan, dec], sealed), [])

    def test_running_prior_uses_the_registers_own_resolutions_after_twenty(self):
        """Guards against: an invented prior for a statement no frozen record speaks to."""
        res = [{"type": "RESOLUTION", "market": "US", "set_id": f"S{i}", "window": "PATH20",
                "cone": [{"id": "RUN30_20", "outcome": i % 4 == 0}]} for i in range(19)]
        self.assertEqual(sp.running_prior("US", "RUN30_20", res), (0.5, 19))
        res.append({"type": "RESOLUTION", "market": "US", "set_id": "S19", "window": "PATH20", "cone": [{"id": "RUN30_20", "outcome": True}]})
        prior, n = sp.running_prior("US", "RUN30_20", res)
        self.assertEqual(n, 20)
        self.assertAlmostEqual(prior, 6 / 20)
        self.assertEqual(sp.running_prior("IDX", "RUN30_20", res), (0.5, 0))


class Resolution(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore")

    def make_set(self, m, twins=("U01", "U02"), session_index=10):
        return {"type": "SPECULATION_SET", "market": "US", "set_id": "SPEC-X", "ticker": "U00",
                "signal_session": str(m.dates[session_index]), "signal": {"close": float(m.close[0, session_index])},
                "entry": {"basis": "open"}, "twins": [{"ticker": t, "close": float(m.close[list(m.tickers).index(t), session_index])} for t in twins],
                "cone": [{"id": c["id"], "prior": 0.4, "resolves_with": c["resolves_with"]} for c in sp.protocol()[0]["cone"]],
                "protocol": {"id": "KOD-SPEC-REGISTER-v1", "sha256": "s"}}

    def test_resolve_set_pairs_the_candidate_with_its_twins_under_the_same_plan(self):
        """Guards against: twins scored under a different plan, or a paired difference without a traded twin."""
        m, a = us_market(n_sessions=30)
        d = 10
        set_closes(a, 0, d + 1, [26, 27, 28, 29, 30, 31], opens=[25, 27, 28, 29, 30, 31])
        set_closes(a, 1, d + 1, [24, 24, 24, 24, 24, 24], opens=[25, 24, 24, 24, 24, 24])
        set_closes(a, 2, d + 1, [25, 25, 25, 25, 25, 25])
        m = build(m.tickers, m.dates, a)
        r = sp.resolve_set(self.make_set(m), "BASE5", m, pd.DataFrame())
        self.assertEqual(r["status"], "RESOLVED")
        self.assertEqual(r["candidate"]["status"], "TRADED")
        self.assertEqual([t["status"] for t in r["twins"]], ["TRADED", "TRADED"])
        c = r["candidate"]["trade"]["net_return"]
        t1 = r["twins"][0]["trade"]["net_return"]
        t2 = r["twins"][1]["trade"]["net_return"]
        self.assertAlmostEqual(r["paired"]["diff"], c - (t1 + t2) / 2)
        self.assertGreater(c, 0)
        self.assertLess(t1, 0)
        self.assertEqual({x["id"] for x in r["cone"]}, {"RUN30_5", "FADE10_5", "GAIN0_5", "BEATS_TWINS_5"})
        self.assertIsNone(sp.resolve_set(self.make_set(m), "PATH20", m, pd.DataFrame()))  # 30 sessions do not cover s+20
        m, a = us_market(n_sessions=40)
        set_closes(a, 0, d + 1, [40] * 25)
        m = build(m.tickers, m.dates, a)
        p = sp.resolve_set(self.make_set(m), "PATH20", m, pd.DataFrame())
        self.assertEqual((p["status"], p["candidate"]["status"], p["paired"]), ("RESOLVED", "PATH", None))
        self.assertEqual({x["id"]: x["outcome"] for x in p["cone"]}, {"RUN30_20": True, "DOUBLE_20": False})
        self.assertEqual([t["status"] for t in p["twins"]], ["PATH", "PATH"])

    def test_a_recorded_close_that_does_not_reconcile_is_unresolvable_and_a_twin_is_dropped(self):
        """Guards against: scoring a rescaled history as if it were the price the set was sealed on."""
        m, a = us_market(n_sessions=30)
        m = build(m.tickers, m.dates, a)
        s = self.make_set(m)
        s["signal"]["close"] = 99.0
        r = sp.resolve_set(s, "BASE5", m, pd.DataFrame())
        self.assertEqual(r["status"], "UNRESOLVABLE")
        self.assertIn("reconcile", r["reason"])
        s = self.make_set(m)
        s["twins"][0]["close"] = 99.0
        r = sp.resolve_set(s, "BASE5", m, pd.DataFrame())
        self.assertEqual(r["twins"][0]["status"], "DROPPED")
        self.assertEqual(r["paired"]["twins_traded"], 1)

    def test_due_is_a_calendar_check_per_window(self):
        """Guards against: pulling bars for nothing, or forgetting a window that ended."""
        specs = [{"type": "SPECULATION_SET", "market": "US", "set_id": "S", "signal_session": "2026-10-27"},
                 {"type": "RESOLUTION", "market": "US", "set_id": "S", "window": "BASE5"}]
        self.assertEqual(sp.due("US", "2026-11-04", specs), [])  # 6 business days: only BASE5, already resolved
        self.assertEqual(sp.due("US", "2026-11-23", specs), [])  # 19 business days
        self.assertEqual(sp.due("US", "2026-11-24", specs), [("S", "PATH20")])
        self.assertEqual(sp.due("IDX", "2026-11-25", specs), [])


def fake_resolutions(market, diffs_by_session, net_shift=0.0, window="BASE5"):
    out = []
    for session, diffs in diffs_by_session.items():
        for i, dlt in enumerate(diffs):
            out.append({"type": "RESOLUTION", "market": market, "window": window, "status": "RESOLVED", "set_id": f"S-{session}-{i}",
                        "signal_session": session, "candidate": {"status": "TRADED", "trade": {"net_return": dlt + net_shift}},
                        "paired": {"candidate_net": dlt + net_shift, "twins_mean_net": net_shift, "diff": dlt, "twins_traded": 5},
                        "cone": [{"id": "RUN30_5", "prior": 0.15, "outcome": i % 7 == 0, "twins_rate": 0.2}]})
    return out


class Statistics(unittest.TestCase):
    def test_verdict_needs_the_look_t3_and_positive_net(self):
        """Guards against: a verdict before the pre-declared look, or a plan that beats its twins while losing money."""
        rng = np.random.default_rng(1)
        sessions = {f"2026-11-{d:02d}": list(rng.normal(0.08, 0.05, 4)) for d in range(1, 21)}  # 80 sets, 20 sessions
        strong = fake_resolutions("US", sessions, net_shift=0.01)
        sets = [{"type": "SPECULATION_SET", "market": "US", "set_id": r["set_id"], "signal_session": r["signal_session"],
                 "twins": [1] * 5} for r in strong]
        ledger = [{"type": "SCAN", "market": "US", "session": s} for s in sessions]
        st = sp.statistics(sets + strong, ledger)["markets"]["US"]
        a = st["plan"]
        self.assertEqual((a["n_paired"], a["n_sessions"], a["look"]["reached"]), (80, 20, 60))
        self.assertGreater(a["t"], 3.0)
        self.assertLess(a["p_holm"], 0.05)
        self.assertAlmostEqual(a["p_holm"], a["p_one_sided"])  # one plan: Holm is the raw p
        self.assertTrue(a["verdict"].startswith("ELIGIBLE FOR OWNER REVIEW"))
        losing = fake_resolutions("US", sessions, net_shift=-0.20)
        a = sp.statistics(sets + losing, ledger)["markets"]["US"]["plan"]
        self.assertLess(a["mean_net"], 0)
        self.assertTrue(a["verdict"].startswith("not eligible"))
        few = fake_resolutions("US", {k: v for k, v in list(sessions.items())[:10]})
        a = sp.statistics(sets + few, ledger)["markets"]["US"]["plan"]
        self.assertEqual(a["look"]["reached"], None)  # 40 sets, 10 sessions: no look yet
        self.assertEqual(a["verdict"], "accumulating (no look reached)")
        self.assertIsNotNone(a["projection"]["sessions_for_t3"])
        cone = sp.statistics(sets + strong, ledger)["markets"]["US"]["cone"]["RUN30_5"]
        self.assertEqual(cone["n"], 80)
        self.assertAlmostEqual(cone["mean_prior"], 0.15)
        self.assertAlmostEqual(cone["twins_rate"], 0.2)
        self.assertGreater(cone["brier_uninformed"], 0)
        self.assertEqual(sp.statistics(sets + strong, ledger)["markets"]["IDX"]["n_sets"], 0)

    def test_render_mentions_the_windows_and_the_protocol(self):
        text = sp.render(sp.statistics([], []), [])
        self.assertIn("BASE5", text)
        self.assertIn("PATH20", text)
        self.assertIn("KOD-SPEC-REGISTER-v1", text)


class Verify(unittest.TestCase):
    def test_chain_cutoff_and_ledger_binding_are_checked(self):
        """Guards against: a set sealed late, bound to a record that is not in the ledger, or a chain edited after
        the fact passing paper-verify."""
        scan, dec = ledger_records()
        now = datetime(2026, 10, 27, 23, 50, tzinfo=timezone.utc)
        s = sp.build_set(dec, scan, features_frame(), [scan, dec], [], now)
        real_lines = paper.ledger_lines

        def lines(path=paper.LEDGER):
            return [scan, dec] if path == paper.LEDGER else real_lines(path)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "speculations.jsonl"
            with mock.patch.object(sp, "SPEC_LEDGER", path), mock.patch.object(paper, "ledger_lines", lines):
                paper.append([s], path=path)
                self.assertEqual(sp.verify(), [])
                late = {**s, "sealed_at": "2026-10-28T13:31:00Z"}
                paper.append([late], path=path)
                problems = sp.verify()
                self.assertTrue(any("after its cutoff" in p for p in problems))
                self.assertTrue(any("sealed twice" in p for p in problems))
                text = path.read_text().splitlines()
                text[0] = text[0].replace('"PASS"', '"BUY ON TRIGGER"')
                path.write_text("\n".join(text) + "\n")
                self.assertTrue(any("record_hash" in p or "chain" in p for p in sp.verify()))


class Protocol(unittest.TestCase):
    def test_priors_in_the_protocol_match_the_frozen_validation_results(self):
        """Guards against: a prior drifting from the record it claims to come from."""
        proto = sp.protocol()[0]
        run30 = next(c for c in proto["cone"] if c["id"] == "RUN30_5")
        for mk, p in (("IDX", "research/E1/validation/result.json"), ("US", "research/E2/US/validation/result.json"),
                      ("CRYPTO", "research/E2/CRYPTO/validation/result.json")):
            res = json.loads((sp.PKG_ROOT / p).read_text(encoding="utf-8"))
            self.assertAlmostEqual(run30["prior"][mk], res["E30"]["precision"])
        self.assertEqual(tuple(proto["windows"]), sp.WINDOW_ORDER)
        self.assertEqual(proto["decision_rule"]["looks"], [60, 120, 240])
        for wid, n in proto["resolution"]["windows_after_signal"].items():
            self.assertEqual(sp.window_length(proto["windows"][wid]), n)
        self.assertEqual([w for w in proto["windows"].values() if w["kind"] == "plan"], [proto["windows"]["BASE5"]])

    def test_fade_and_gain_priors_match_the_validation_trades(self):
        """Guards against: a typed share that the run's trades do not reproduce."""
        proto = sp.protocol()[0]
        fade = next(c for c in proto["cone"] if c["id"] == "FADE10_5")["prior"]
        gain = next(c for c in proto["cone"] if c["id"] == "GAIN0_5")["prior"]
        for mk, (_, run) in sp.VALIDATION_SD.items():
            path = sp.PKG_ROOT / "results" / "runs" / run / "trades.csv.gz"
            if not path.exists():
                self.skipTest("validation run not present")
            t = pd.read_csv(path)
            nr = t[t["status"].isin(["EXITED", "EXIT_DATA_END"])]["net_return"].dropna()
            self.assertAlmostEqual(fade[mk], float((nr <= -0.10).mean()), places=3)
            self.assertAlmostEqual(gain[mk], float((nr > 0).mean()), places=3)
            self.assertAlmostEqual(sp.VALIDATION_SD[mk][0], float(nr.std()), places=3)


if __name__ == "__main__":
    unittest.main()


class NextSession(unittest.TestCase):
    """v1.1 (research/SPECULATION_REGISTER_v1/ADDENDUM_1.md): the NEXT1 window."""

    def setUp(self):
        warnings.simplefilter("ignore")

    def make_set(self, m, twins=("U01", "U02", "U03", "U04"), session_index=10):
        return {"type": "SPECULATION_SET", "market": "US", "set_id": "SPEC-N", "ticker": "U00",
                "signal_session": str(m.dates[session_index]), "signal": {"close": float(m.close[0, session_index])},
                "entry": {"basis": "open"}, "windows": ["BASE5", "PATH20", "NEXT1"],
                "twins": [{"ticker": t, "close": float(m.close[list(m.tickers).index(t), session_index])} for t in twins],
                "cone": [{"id": c["id"], "prior": 0.4, "resolves_with": c["resolves_with"]} for c in sp.protocol()[0]["cone"]],
                "protocol": {"id": "KOD-SPEC-REGISTER-v1.1", "sha256": "s"}}

    def test_next1_grades_the_next_close_against_the_twins(self):
        """Guards against: a next-session statement read on the wrong session, or the twins' median taken from the plan."""
        m, a = us_market(n_sessions=30)
        d = 10
        set_closes(a, 0, d + 1, [22.0])  # -12%
        set_closes(a, 1, d + 1, [26.0])  # +4%
        set_closes(a, 2, d + 1, [24.0])  # -4%
        set_closes(a, 3, d + 1, [25.0])  # 0
        set_closes(a, 4, d + 1, [25.0])  # 0
        m = build(m.tickers, m.dates, a)
        r = sp.resolve_set(self.make_set(m), "NEXT1", m, pd.DataFrame())
        self.assertEqual((r["status"], r["candidate"]["status"], r["paired"], r["resolver"]), ("RESOLVED", "PATH", None, "spec-resolve-v1.1"))
        got = {x["id"]: (x["outcome"], x["twins_rate"]) for x in r["cone"]}
        self.assertEqual(set(got), {"DOWN10_1", "UP10_1", "BEATS_TWINS_1"})
        self.assertEqual(got["DOWN10_1"], (True, 0.0))
        self.assertEqual(got["UP10_1"], (False, 0.0))
        self.assertEqual(got["BEATS_TWINS_1"][0], False)  # -12% is below the twins' median (0%)
        # each twin against the other three: +4% beats (-4%, 0, 0); -4% does not; 0 does not beat a median of 0
        self.assertAlmostEqual(got["BEATS_TWINS_1"][1], 1 / 4)
        self.assertEqual([t["status"] for t in r["twins"]], ["PATH"] * 4)
        self.assertIsNone(sp.resolve_set(self.make_set(m, session_index=29), "NEXT1", m, pd.DataFrame()))  # s+1 not covered

    def test_next1_is_ungraded_without_a_bar_and_needs_three_twins(self):
        """Guards against: grading a halted name, or a twins' median from one or two twins."""
        m, a = us_market(n_sessions=30)
        d = 10
        a["present"][0, d + 1] = False
        m = build(m.tickers, m.dates, a)
        r = sp.resolve_set(self.make_set(m), "NEXT1", m, pd.DataFrame())
        self.assertEqual({x["id"]: x["outcome"] for x in r["cone"]}, {"DOWN10_1": None, "UP10_1": None, "BEATS_TWINS_1": None})
        m, a = us_market(n_sessions=30)
        set_closes(a, 0, d + 1, [20.0])
        m = build(m.tickers, m.dates, a)
        r = sp.resolve_set(self.make_set(m, twins=("U01", "U02")), "NEXT1", m, pd.DataFrame())
        got = {x["id"]: x["outcome"] for x in r["cone"]}
        self.assertEqual((got["DOWN10_1"], got["BEATS_TWINS_1"]), (True, None))

    def test_v1_sets_never_open_next1_and_v1_1_sets_do(self):
        """Guards against: a third window opened on a set sealed under v1, or forgotten on a v1.1 set."""
        specs = [{"type": "SPECULATION_SET", "market": "US", "set_id": "OLD", "signal_session": "2026-10-27"},
                 {"type": "SPECULATION_SET", "market": "US", "set_id": "NEW", "signal_session": "2026-10-27",
                  "windows": ["BASE5", "PATH20", "NEXT1"]}]
        self.assertEqual(sp.due("US", "2026-10-28", specs), [("NEW", "NEXT1")])
        self.assertEqual(sp.due("US", "2026-10-27", specs), [])
        self.assertEqual([w for _, w in sp.due("US", "2026-11-24", specs)], ["BASE5", "PATH20", "BASE5", "PATH20", "NEXT1"])

    def test_v1_1_keeps_v1_windows_and_statements_byte_for_byte(self):
        """Guards against: a change to BASE5 or PATH20 or a v1 prior slipping in with the new window."""
        v11, _ = sp.protocol()
        v1 = json.loads(sp.PROTOCOL_VERSIONS["KOD-SPEC-REGISTER-v1"].read_text())
        self.assertEqual(v11["protocol_id"], "KOD-SPEC-REGISTER-v1.1")
        self.assertEqual({k: v11["windows"][k] for k in v1["windows"]}, v1["windows"])
        self.assertEqual(v11["cone"][:len(v1["cone"])], v1["cone"])
        self.assertEqual(v11["windows"]["NEXT1"], {"kind": "path", "what": "the next session's close of the candidate and its twins; no plan", "horizon": 1})
        self.assertEqual(sp.window_length(v11["windows"]["NEXT1"]), 1)
