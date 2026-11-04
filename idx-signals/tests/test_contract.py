"""EXEC-US-v2 (idxsig/contract.py, research/EXEC_US_v2/CONTRACT.md). Synthetic markets only:
these check mechanics, not profitability.

Each test names the failure it guards against."""

import json
import unittest

import numpy as np

from idxsig import contract as C
from idxsig.exec_us import cost_rate
from idxsig.execution import ExecConfig, Market, STATUS, execute
from tests.support import flat_market

SPEC = C.SPEC


def market(n_tickers=3, n_sessions=30, price=100.0, volume=1_000_000.0, edit=None, uf=None):
    """Flat US-style bars (open = close = price, high/low +-1%). `edit(a)` mutates the arrays first."""
    t, d, a = flat_market(n_tickers, n_sessions, price=price, volume=volume)
    a["open"] = a["close"].copy()
    if edit:
        edit(a)
    a["value"] = np.nan_to_num(a["close"]) * np.nan_to_num(a["volume"])
    m = Market.build(
        t,
        d,
        a["close"],
        a["prev"],
        a["high"],
        a["low"],
        a["volume"],
        a["value"],
        a["present"],
        opens=a["open"],
        price_limits=False,
    )
    return m.with_units(np.ones(m.shape) if uf is None else uf)


def run(m, signals, k0=0, k1=None, spec=SPEC):
    return C.replay(m, signals, k0, m.shape[1] - 1 if k1 is None else k1, spec)


def closed(acc, ticker="T000"):
    return [c for c in acc.state["closed"] if c["ticker"] == ticker]


def events(acc, kind):
    return [e for e in acc.state["events"] if e["event"] == kind]


class ValidTrade(unittest.TestCase):
    def test_entry_at_next_open_time_exit_and_balance(self):
        """Guards against: a fill at the already-observed signal close, a wrong holding period, and a
        balance that does not add up from the fills and costs."""

        def edit(a):
            a["open"][0, 21] = 99.0  # entry open, inside the band (stop 95, limit 100)
            a["close"][0, 25] = 104.0  # session 5 counting the entry session: time exit here
            a["high"][0, 25] = 105.0

        m = market(edit=edit)
        acc = run(m, {20: [(0, 95.0)]})
        [t] = closed(acc)
        self.assertEqual(
            (t["outcome"], t["entry_session"], t["entry_price"]), ("FILLED", str(m.dates[21]), 99.0)
        )
        self.assertEqual(
            (t["exit_reason"], t["exit_session"], t["sessions_held"]),
            ("TIME_EXIT_AT_CLOSE", str(m.dates[25]), 5),
        )
        # Size: risk 1% of $10,000 at the permitted entry 100 (stop 95; exit cost at the stop's tier).
        rps = 100 * (1 + cost_rate(100, "buy")) - 95 * (1 - cost_rate(95, "sell"))
        self.assertAlmostEqual(C.risk_per_share(100.0, 95.0), rps)
        self.assertEqual(t["shares_filled"], int(min(100 / rps, 2000 / 100)))
        debit = t["shares_filled"] * 99 * (1 + cost_rate(99, "buy"))
        proceeds = t["shares_filled"] * 104 * (1 - cost_rate(104, "sell"))
        self.assertAlmostEqual(acc.state["cash_usd"], 10_000 - debit + proceeds, places=9)
        self.assertAlmostEqual(t["net_pnl_usd"], proceeds - debit, places=9)


class EntryRejections(unittest.TestCase):
    def test_excessive_entry_gap_is_not_filled_and_cash_is_released(self):
        """Guards against: chasing a gap. Signal $100, stop $95, open $110: the stop would be 13.6% away."""
        m = market(edit=lambda a: a["open"].__setitem__((0, 21), 110.0))
        acc = run(m, {20: [(0, 95.0)]})
        [t] = closed(acc)
        self.assertEqual(t["outcome"], "UNFILLED_OPEN_ABOVE_LIMIT")
        self.assertIn("13.64%", t["reason"])
        self.assertEqual(acc.state["cash_usd"], 10_000.0)
        self.assertEqual(acc.state["positions"], [])

    def test_risk_distance_is_measured_at_the_permitted_entry_and_the_stop_never_moves(self):
        """Guards against: measuring the 5% from the signal close, or widening/raising the stop to make
        an entry fit. Close 100, stop 80: the only permitted entries are at or below 84.21."""
        plan = C.plan_order(100.0, 80.0, 1e9, 10_000.0)
        self.assertEqual((plan["invalidation"], plan["entry_limit"]), (80.0, 84.21))
        self.assertLessEqual(plan["stop_distance_at_limit"], 0.05)
        self.assertAlmostEqual(plan["stop_distance_from_signal_close"], 0.20)
        m = market(edit=lambda a: a["open"].__setitem__((0, 21), 99.0))
        [t] = closed(run(m, {20: [(0, 80.0)]}))
        self.assertEqual(t["outcome"], "UNFILLED_OPEN_ABOVE_LIMIT")
        self.assertEqual(t["stop_at_entry_units"], 80.0)
        self.assertEqual(C.plan_order(100.0, 0.0, 1e9, 10_000.0)["outcome"], "REJECTED_NO_PLAN")

    def test_open_at_or_below_the_stop_fills_and_stops_out_at_that_open(self):
        """Guards against: assuming an order can be cancelled on information inside the auction. The
        limit-on-open fills; its attached stop sells at once (assumed at the open): costs are lost."""
        m = market(edit=lambda a: a["open"].__setitem__((0, 21), 94.0))
        [t] = closed(run(m, {20: [(0, 95.0)]}))
        self.assertEqual(
            (t["outcome"], t["exit_reason"], t["exit_session"]),
            ("FILLED", "STOP_AT_OPEN_ON_ENTRY", t["entry_session"]),
        )
        self.assertLess(t["net_pnl_usd"], 0)
        # The loss is the round-trip cost, which the plan at this fill already counts: nothing beyond it.
        self.assertAlmostEqual(t["realized_loss_beyond_planned_risk_usd"], 0.0, places=9)


class Capital(unittest.TestCase):
    def test_simultaneous_signals_share_cash_by_priority_without_leverage(self):
        """Guards against: spending the same cash twice, or an order order that depends on input order.
        The more liquid name goes first; the second is cut to the cash left; the third gets none."""
        spec = C.ContractSpec(
            starting_cash_usd=3_000.0, max_position_fraction=0.6, risk_fraction=1.0
        )
        m = market(edit=lambda a: a["volume"].__setitem__((1, slice(None)), 2_000_000.0))
        acc = run(m, {20: [(0, 95.0), (1, 95.0), (2, 95.0)]}, spec=spec)
        placed = {e["ticker"]: e for e in events(acc, "ORDER_PLACED")}
        rejected = {e["ticker"]: e for e in events(acc, "ORDER_REJECTED")}
        self.assertEqual(placed["T001"]["priority"], 1)  # double the traded value
        self.assertFalse(placed["T001"]["cash_limited"])
        self.assertTrue(placed["T000"]["cash_limited"])
        self.assertEqual(rejected["T002"]["outcome"], "REJECTED_INSUFFICIENT_CASH")
        self.assertTrue(all(e["cash_usd"] >= 0 for e in acc.state["events"]))

    def test_insufficient_capital_for_one_share(self):
        """Guards against: an order the account cannot pay for. The first position takes almost all
        the cash; equity is unchanged, so the second plan sizes normally but cannot be paid for."""
        spec = C.ContractSpec(max_position_fraction=0.999, risk_fraction=1.0)
        acc = run(market(), {20: [(0, 95.0)], 21: [(1, 95.0)]}, spec=spec, k1=22)
        [t] = closed(acc, "T001")
        self.assertEqual(t["outcome"], "REJECTED_INSUFFICIENT_CASH")
        self.assertGreaterEqual(t["plan"]["shares"], 1)


class Liquidity(unittest.TestCase):
    def test_thin_history_gives_no_plan(self):
        """Guards against: planning a position the name's traded value cannot carry."""
        m = market(volume=1.0)  # $100 a day
        [t] = closed(run(m, {20: [(0, 95.0)]}))
        self.assertEqual(
            (t["outcome"], t["plan"]["binding_limit"]), ("REJECTED_SIZE_ZERO", "liquidity")
        )

    def test_entry_session_volume_bounds_the_fill(self):
        """Guards against (Hermes): 10,000 shares scored as filled when the whole entry session
        traded 1,000. The planned order and the fill are separate; the fill is at most 10% of the
        session (an upper bound, labelled), and the rest is cancelled."""
        spec = C.ContractSpec(starting_cash_usd=10_000_000.0)

        def edit(a):
            a["volume"][0, 21] = 1_000.0

        acc = run(market(edit=edit), {20: [(0, 95.0)]}, spec=spec)
        [t] = closed(acc)
        self.assertGreaterEqual(t["shares_ordered"], 10_000)
        self.assertEqual((t["outcome"], t["shares_filled"]), ("PARTIAL", 100))
        self.assertIn("upper bound", t["fill_evidence"])

    def test_legacy_fill_c_still_reproduces_hermes_case(self):
        """Documents, does not fix: FILL-C-v1 (kept for reproduction) sizes from the 20 sessions before
        the entry and never checks the entry session, so 10,000 shares can EXIT on a 1,000-share day."""
        from tests.test_corporate_actions import registry

        t, d, a = flat_market(volume=1_000_000.0)
        a["volume"][0, 5] = 1_000.0
        from tests.support import rebuild

        m = rebuild(t, d, a)
        m = m.with_registry(registry(m))
        out = execute(
            m,
            np.array([0]),
            np.array([4]),
            ExecConfig(holding_days=4, notional=10_000_000.0, ca_mode="registry", fill_model="C"),
        )
        self.assertEqual((STATUS[out["status"][0]], out["shares"][0]), ("EXITED", 10_000))

    def test_no_trade_on_the_entry_session(self):
        """Guards against: filling on a session with no opening print."""

        def edit(a):
            a["volume"][0, 21] = 0.0
            a["open"][0, 21] = np.nan

        [t] = closed(run(market(edit=edit), {20: [(0, 95.0)]}))
        self.assertEqual(t["outcome"], "UNFILLED_NOT_TRADED")


class Units(unittest.TestCase):
    def test_split_between_decision_and_execution(self):
        """Guards against: a 1:2 split at the entry open filling at the old limit or for the old share
        count. Limit, stop and shares are converted; the dollars are the same."""
        uf = np.ones((3, 30))
        uf[0, :21] = (
            2.0  # adjusted panel: as traded = adjusted x F; the split takes effect at session 21
        )

        def edit(a):
            a["open"][0, :] = a["close"][0, :] = 50.0
            a["high"][0, :], a["low"][0, :] = 50.5, 49.5
            a["value"] = None

        m = market(edit=edit, uf=uf)  # as traded: $100 through session 20, $50 from session 21
        acc = run(m, {20: [(0, 95.0)]})
        [t] = closed(acc)
        self.assertEqual(t["plan"]["entry_limit"], 100.0)
        self.assertEqual((t["limit_at_entry_units"], t["stop_at_entry_units"]), (50.0, 47.5))
        self.assertEqual(t["planned_shares_at_entry_units"], 2 * t["shares_ordered"])
        self.assertEqual(t["entry_price"], 50.0)
        self.assertEqual(t["outcome"], "FILLED")


class Scans(unittest.TestCase):
    def test_no_signal_and_failed_scan_are_different_records(self):
        """Guards against: a scan that could not run being read as 'nothing to buy'."""
        m = market()
        acc = C.Account()
        self.assertEqual(acc.step(m, 20, [])["status"], "NO_SIGNAL")
        self.assertEqual(acc.step(m, 21, C.ScanFailed("INPUT_HASH_MISMATCH"))["status"], "FAILED")
        kinds = [e["event"] for e in acc.state["events"] if e["event"].startswith("SCAN_")]
        self.assertEqual(kinds, ["SCAN_NO_SIGNAL", "SCAN_FAILED"])

    def test_stale_data_fails_the_scan_and_touches_nothing(self):
        """Guards against: trading yesterday's bars as if they were today's."""
        m = market()
        state, _ = C.forward_step(None, m.truncate(20), [(0, 95.0)], str(m.dates[20]))
        before = json.dumps(
            {k: state[k] for k in ("cash_usd", "orders", "positions")}, sort_keys=True
        )
        state2, scan = C.forward_step(state, m.truncate(20), [], str(m.dates[21]))
        self.assertEqual(scan["status"], "FAILED")
        self.assertIn("STALE_DATA", scan["reason"])
        self.assertEqual(
            json.dumps({k: state2[k] for k in ("cash_usd", "orders", "positions")}, sort_keys=True),
            before,
        )

    def test_a_failed_scan_still_lets_held_positions_exit(self):
        """Guards against: a failed scan freezing stops that the broker would have executed."""

        def edit(a):
            a["low"][0, 23] = 90.0

        m = market(edit=edit)
        acc = run(m, {20: [(0, 95.0)]}, k1=22)
        acc.step(m, 23, C.ScanFailed("MISSING_DATA"))
        [t] = closed(acc)
        self.assertEqual(t["exit_reason"], "STOP")


class Risk(unittest.TestCase):
    def test_planned_risk_account_risk_and_gap_loss_are_separate(self):
        """Guards against: reporting a gap loss as if the 5% stop had capped it."""

        def edit(a):
            a["open"][0, 23] = 80.0  # gap through the 95 stop
            a["low"][0, 23] = 79.0

        [t] = closed(run(market(edit=edit), {20: [(0, 95.0)]}))
        self.assertEqual((t["exit_reason"], t["exit_price"]), ("STOP_GAP_AT_OPEN", 80.0))
        self.assertLessEqual(t["planned_account_risk"], 0.01 + 1e-12)
        self.assertGreater(t["realized_loss_beyond_planned_risk_usd"], 0)
        self.assertAlmostEqual(
            -t["net_pnl_usd"],
            t["planned_risk_at_fill_usd"] + t["realized_loss_beyond_planned_risk_usd"],
            places=9,
        )


class SameContractBothWays(unittest.TestCase):
    def test_forward_scoring_equals_replay_on_identical_inputs(self):
        """Guards against: forward paper scoring and replay drifting apart. Forward sees only the data
        through each day and keeps its state as JSON between days; the trace must be identical."""

        def edit(a):
            a["open"][0, 21] = 99.0
            a["open"][1, 22] = 120.0  # gap above the limit
            a["low"][2, 24] = 90.0  # stop
            a["volume"][2, 22] = 100.0  # partial fill: at most 10 shares

        m = market(edit=edit)
        sig = {20: [(0, 95.0)], 21: [(1, 95.0), (2, 95.0)], 22: [(0, 95.0)]}
        rep = run(m, sig, 15, 29)
        state = None
        for k in range(15, 30):
            state, _ = C.forward_step(state, m.truncate(k), sig.get(k, []), str(m.dates[k]))
        self.assertEqual(
            json.dumps(json.loads(json.dumps(rep.state, default=float)), sort_keys=True),
            json.dumps(state, sort_keys=True),
        )
        outcomes = sorted(c["outcome"] for c in state["closed"])
        self.assertEqual(
            outcomes,
            sorted(["FILLED", "UNFILLED_OPEN_ABOVE_LIMIT", "PARTIAL", "REJECTED_ALREADY_HELD"]),
        )

    def test_research_window_is_enforced(self):
        """Guards against: evidence drawn from sessions outside the permitted research dates."""
        m = market()
        with self.assertRaises(ValueError):
            C.replay(m, {}, 0, 29, permitted=(str(m.dates[5]), str(m.dates[29])))
        C.replay(m, {}, 5, 29, permitted=(str(m.dates[5]), str(m.dates[29])))

    def test_contract_version_is_bound_to_the_state(self):
        """Guards against: continuing a saved account under changed rules."""
        state, _ = C.forward_step(None, market().truncate(20), [], str(market().dates[20]))
        with self.assertRaises(ValueError):
            C.Account(C.ContractSpec(max_stop_distance=0.08), state)


if __name__ == "__main__":
    unittest.main()


# -- Ace's review of 21eb6aa: each test reproduces a reported failure -------------------------------------


def permuted(m, order):
    """The same market with its rows in another order (a later download sorted differently)."""
    arrays = {f: getattr(m, f)[order] for f in Market.FIELDS}
    return Market(m.tickers[order], m.dates, **arrays, unit_factor=m.unit_factor[order])


def readjusted_for_split(m, at, ratio=2.0):
    """A later download after a ratio:1 split effective at session `at`: as-traded prices from `at` on
    are divided by `ratio`, and the provider re-adjusts the whole history to the new basis."""
    t, d = m.tickers, m.dates
    arrays = {f: getattr(m, f).copy() for f in Market.FIELDS}
    for f in ("close", "prev", "high", "low", "open"):
        arrays[f][0] = arrays[f][0] / ratio  # every session, adjusted to the post-split basis
    arrays["volume"][0] = arrays["volume"][0] * ratio
    uf = m.unit_factor.copy()
    uf[0, :at] = uf[0, :at] * ratio  # as traded = adjusted x F: unchanged before the split
    return Market(t, d, **arrays, unit_factor=uf)


class AceReview(unittest.TestCase):
    def test_saved_orders_follow_the_ticker_not_the_row(self):
        """P1 (Ace): state kept row numbers, so a download with another row order filled the $100
        stock's order at the other stock's $50 prices."""

        def edit(a):
            for k in ("close", "prev", "open"):
                a[k][1] = 50.0
            a["high"][1], a["low"][1] = 50.5, 49.5

        m = market(n_tickers=2, edit=edit)
        state, _ = C.forward_step(None, m.truncate(20), [(0, 95.0)], str(m.dates[20]))
        m2 = permuted(m, np.array([1, 0]))
        state, _ = C.forward_step(state, m2.truncate(21), [], str(m.dates[21]))
        [p] = state["positions"]
        self.assertEqual((p["ticker"], p["entry_price"]), ("T000", 100.0))

    def test_a_rolling_window_download_is_not_already_processed(self):
        """P1 (Ace): a download whose window starts later shifts every index; the next session was
        reported as already processed."""
        m = market()
        state, _ = C.forward_step(None, m.truncate(20), [(0, 95.0)], str(m.dates[20]))
        state, scan = C.forward_step(state, m.slice(5, 22), [], str(m.dates[21]))
        self.assertEqual(scan["status"], "NO_SIGNAL")
        self.assertEqual(len(state["positions"]), 1)

    def test_a_split_readjusted_download_keeps_the_holding(self):
        """P1 (Ace): after a 2-for-1 split the provider re-adjusts history. The holding must double
        and the stop halve; no false stop, no artificial loss."""
        m = market()
        state = None
        for k in range(20, 23):
            state, _ = C.forward_step(
                state, m.truncate(k), [(0, 95.0)] if k == 20 else [], str(m.dates[k])
            )
        [p] = state["positions"]
        filled = p["shares_filled"]
        m2 = readjusted_for_split(m, at=23)
        for k in range(23, 26):
            state, _ = C.forward_step(state, m2.truncate(k), [], str(m.dates[k]))
        t = [c for c in state["closed"] if c["ticker"] == "T000" and "exit_reason" in c][0]
        self.assertEqual(
            (t["exit_reason"], t["exit_session"]), ("TIME_EXIT_AT_CLOSE", str(m.dates[25]))
        )
        self.assertEqual((t["shares_at_exit"], t["exit_price"]), (2 * filled, 50.0))
        round_trip = filled * 100 * (cost_rate(100, "buy")) + 2 * filled * 50 * cost_rate(
            50, "sell"
        )
        self.assertAlmostEqual(-t["net_pnl_usd"], round_trip, places=6)

    def test_planned_risk_covers_the_exit_cost_tier_at_the_stop(self):
        """P2 (Ace): $5 entry, $4.75 stop. The exit cost was estimated at the entry price's tier, so
        an ordinary stop (no gap, no slippage) lost $106.08 against a $100 budget."""

        def edit(a):
            for k in ("close", "prev", "open"):
                a[k][0] = 5.0
            a["high"][0], a["low"][0] = 5.05, 4.95
            a["low"][0, 23] = 4.70

        acc = run(market(edit=edit), {20: [(0, 4.75)]})
        [t] = closed(acc)
        self.assertEqual(t["exit_reason"], "STOP")
        self.assertLessEqual(-t["net_pnl_usd"], t["planned_risk_usd"] + 1e-9)
        self.assertLessEqual(-t["net_pnl_usd"], 100.0 + 1e-9)

    def test_no_exit_on_a_session_without_trades(self):
        """P2 (Ace): a zero-volume session with stale prices filled the scheduled exit."""

        def edit(a):
            a["volume"][0, 25] = 0.0  # the planned exit session: listed, carried prices, no trades
            a["low"][0, 25] = 90.0  # a stale low below the stop must not trigger it either

        acc = run(market(edit=edit), {20: [(0, 95.0)]})
        [t] = closed(acc)
        self.assertEqual(
            (t["exit_reason"], t["exit_session"]), ("TIME_EXIT_ROLLED", str(acc_dates()[26]))
        )


def acc_dates():
    return market().dates


class DemoWindow(unittest.TestCase):
    def test_demo_window_ends_on_the_declared_session(self):
        """P2 (Ace): the demo sliced one session past its declared end (bounds() is already exclusive)."""
        import importlib.util
        from pathlib import Path

        spec = importlib.util.spec_from_file_location(
            "exec_us_v2_demo",
            Path(__file__).resolve().parents[1] / "research" / "EXEC_US_v2_1" / "demo.py",
        )
        demo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(demo)
        m = market(n_sessions=30)
        w = demo.window(m, str(m.dates[3]), str(m.dates[20]))
        self.assertEqual(
            (str(w.dates[0]), str(w.dates[-1]), w.shape[1]), (str(m.dates[3]), str(m.dates[20]), 18)
        )
