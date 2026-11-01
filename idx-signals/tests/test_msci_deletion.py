"""MSCI_DELETION_v1 on fixtures: MSCI list parsing, review dates, event selection, timing, account and gates (no prices)."""

import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1] / "research/MSCI_DELETION_v1"


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


be = load("build_events")
md = load("msci_deletion")

DOC = """MSCI MALAYSIA INDEX
Additions                    Deletions
None                         AIRASIA GROUP


MSCI INDONESIA INDEX
Additions                    Deletions
ASTRA AGRO LESTARI           ADHI KARYA TBK
BANK TABUNGAN NEGARA         ALAM SUTERA REALTY
                             TIMAH


MSCI PHILIPPINES INDEX
Additions                    Deletions
PUREGOLD PRICE CLUB          SECURITY BANK CORP
"""

PR = """MSCI Equity Indexes November 2019 Index
Review
London - November 07, 2019 - MSCI Inc. (NYSE:MSCI), a leading provider ... All changes
will be implemented as of the close of November 26, 2019. These changes have been posted"""


class Parsing(unittest.TestCase):
    def test_the_indonesia_block_splits_at_the_deletions_column(self):
        adds, dels = be.indonesia_block(DOC)
        self.assertEqual(adds, ["ASTRA AGRO LESTARI", "BANK TABUNGAN NEGARA"])
        self.assertEqual(dels, ["ADHI KARYA TBK", "ALAM SUTERA REALTY", "TIMAH"])

    def test_no_indonesia_block_means_no_change(self):
        self.assertEqual(
            be.indonesia_block("MSCI MALAYSIA INDEX\nAdditions   Deletions\nNone   X\n"), ([], [])
        )

    def test_press_release_dates(self):
        self.assertEqual(be.pr_dates(PR), ("2019-11-07", "2019-11-26"))


SESS = np.array(
    ["2022-02-23", "2022-02-24", "2022-02-25", "2022-03-01", "2022-03-02"], dtype="datetime64[D]"
)


class Timing(unittest.TestCase):
    def test_an_idx_holiday_moves_the_entry_to_the_session_before(self):
        self.assertEqual(
            md.implementation_session(SESS, "2022-02-28"), "2022-02-25"
        )  # 28 Feb 2022: IDX closed
        self.assertEqual(md.implementation_session(SESS, "2022-03-01"), "2022-03-01")

    def test_only_deletions_are_events_and_they_buy_the_implementation_close(self):
        ev = pd.DataFrame(
            [
                {
                    "review": "Feb22",
                    "side": "DEL",
                    "kind": "SC_EXIT",
                    "ticker": "AAAA",
                    "implementation_close": "2022-02-28",
                },
                {
                    "review": "Feb22",
                    "side": "DEL",
                    "kind": "SC_TO_ST",
                    "ticker": "BBBB",
                    "implementation_close": "2022-02-28",
                },
                {
                    "review": "Feb22",
                    "side": "ADD",
                    "kind": "ADD",
                    "ticker": "CCCC",
                    "implementation_close": "2022-02-28",
                },
                {
                    "review": "May22",
                    "side": "DEL",
                    "kind": "ST_EXIT",
                    "ticker": "DDDD",
                    "implementation_close": "2022-03-02",
                },
            ]
        )
        d = md.deletion_events(ev, SESS, ("Feb22",))
        self.assertEqual(
            d.ticker.tolist(), ["AAAA"]
        )  # the upward migration and the addition are not deletions
        self.assertEqual(d.posted_wib.iloc[0], "2022-02-25 09:00:00")
        # the harness maps a 09:00 posting on a session day to a buy at that day's close
        s = md.idx_events.signal_session(SESS, pd.Timestamp(d.posted_wib.iloc[0]))
        self.assertEqual(str(SESS[s + 1]), "2022-02-25")


def trades(rows):
    return pd.DataFrame(
        [
            {
                "review": r,
                "ticker": tk,
                "net_return": x,
                "status": st or ("EXITED" if pd.notna(x) else "SKIP_NOT_TRADED"),
            }
            for r, tk, x, *rest in rows
            for st in [rest[0] if rest else None]
        ]
    )


class Account(unittest.TestCase):
    def test_slots_are_fixed_before_the_auction_capped_and_compounded(self):
        nan = float("nan")
        t = trades(
            [
                ("R1", "A", 0.10),
                ("R1", "S", nan, "SKIP_LIQUIDITY"),  # a decision-time skip: no slot
                ("R2", "B", 0.02),
                ("R2", "C", -0.02),
                ("R2", "U", nan),  # not traded at the auction: slot in cash
                *[("R3", f"X{i}", 0.01) for i in range(10)],
            ]
        )
        a = md.account(t, ("R1", "R2", "R3"))
        e1 = md.START_CASH * (
            1 + 0.25 * 0.10
        )  # one slot: at most 25% (= the checked notional at the start)
        w2 = min(0.25, 1 / 3, md.NOTIONAL / e1)  # three slots; also capped at the checked notional
        e2 = e1 * (1 + w2 * (0.02 - 0.02))
        e3 = e2 * (1 + 10 * min(0.1, md.NOTIONAL / e2) * 0.01)
        self.assertAlmostEqual(a["end_equity"], e3)
        self.assertEqual(a["trades"], 13)

    def test_no_position_exceeds_the_notional_the_harness_checked(self):
        t = trades([("R1", "A", 1.0), ("R2", "B", 0.10)])
        a = md.account(t, ("R1", "R2"))
        e1 = md.START_CASH * 1.25
        self.assertAlmostEqual(
            a["end_equity"], e1 + md.NOTIONAL * 0.10
        )  # R2 is capped at NOTIONAL, not 25% of e1
        self.assertEqual(md.config().notional, md.NOTIONAL)

    def test_pnl_without_the_three_largest_winners_and_without_the_best_review(self):
        t = trades(
            [("R1", c, r) for c, r in zip("ABCDE", (0.2, 0.1, 0.05, -0.01, -0.02))]
            + [("R2", "F", 0.01)]
        )
        a = md.account(t, ("R1", "R2"))
        w = 0.2 * md.START_CASH
        self.assertAlmostEqual(
            a["pnl_without_top3"],
            w * (-0.01 - 0.02) + md.NOTIONAL * 0.01,  # F (R2) is capped at the checked notional
        )
        self.assertEqual(md.best_review(t), "R1")
        b = md.account(t, ("R1", "R2"), skip_review="R1")
        self.assertAlmostEqual(b["end_equity"], md.START_CASH * (1 + 0.25 * 0.01))


class Controls(unittest.TestCase):
    def test_every_name_changed_in_a_review_leaves_the_control_pool_at_its_signal_session(self):
        class P:
            pass

        prep = P()
        prep.m = P()
        prep.m.dates, prep.m.tickers = SESS, np.array(["AAAA", "BBBB", "CCCC", "ZZZZ"])
        prep.evaluable = np.ones((4, len(SESS)), bool)
        ev = pd.DataFrame(
            [
                {
                    "review": "Feb22",
                    "side": "ADD",
                    "ticker": "AAAA",
                    "implementation_close": "2022-02-28",
                },
                {
                    "review": "Feb22",
                    "side": "DEL",
                    "ticker": "CCCC",
                    "implementation_close": "2022-02-28",
                },
            ]
        )
        md.exclude_review_names(prep, ev, SESS)
        s = md.idx_events.signal_session(SESS, pd.Timestamp("2022-02-25 09:00:00"))
        expect = np.ones((4, len(SESS)), bool)
        expect[[0, 2], s] = False
        self.assertTrue((prep.evaluable == expect).all())


class Freeze(unittest.TestCase):
    def test_the_frozen_fields_survive_the_json_round_trip(self):
        import json

        f = md.frozen_fields()
        self.assertEqual(json.loads(json.dumps(f)), f)

    def test_every_review_with_a_deletion_is_in_a_window(self):
        ev = pd.read_csv(HERE / "events_all.csv")
        self.assertTrue(set(ev[ev.side == "DEL"].review) <= set(md.DISCOVERY) | set(md.SCREEN))


class Gates(unittest.TestCase):
    def result(self):
        prim = {
            "scored_with_controls": 40,
            "by_review": {str(i): {} for i in range(7)},
            "boot_net": {"mean": 0.02, "lower_one_sided_95": 0.001},
            "boot_excess": {"mean": 0.015, "lower_one_sided_95": 0.002},
            "mean_net": 0.02,
        }
        return {
            "discovery": {
                "primary": prim,
                "account": {"end_equity": 2.0, "start": 1.0, "pnl_without_top3": 5.0},
                "S1_entry_next_session": {"mean_net": 0.01},
                "S2_tick_cost": {"mean_net": 0.01},
            },
            "screen_2023": {"primary": {"scored_with_controls": 6, "mean_net": 0.0}},
        }

    def test_verdicts(self):
        r = self.result()
        self.assertEqual(md.gates(r)["verdict"], "PROMISING")
        r["discovery"]["primary"]["boot_excess"]["lower_one_sided_95"] = -0.001
        self.assertEqual(md.gates(r)["verdict"], "FAIL")
        r = self.result()
        r["discovery"]["primary"]["by_review"] = {"1": {}, "2": {}}
        self.assertEqual(md.gates(r)["verdict"], "INCONCLUSIVE")
        r = self.result()
        r["screen_2023"]["primary"] = {"scored_with_controls": 3}
        self.assertEqual(md.gates(r)["verdict"], "PROMISING")
        r["screen_2023"]["primary"] = {"scored_with_controls": 6, "mean_net": -0.01}
        self.assertEqual(md.gates(r)["verdict"], "FAIL")

    def test_cluster_bootstrap_brackets_the_mean(self):
        b = md.cluster_bootstrap(np.array([0.01, 0.03, -0.02, 0.04]), ["a", "a", "b", "c"])
        self.assertTrue(b["lower95"] <= b["mean"] <= b["upper95"])
        self.assertEqual(b["clusters"], 3)


if __name__ == "__main__":
    unittest.main()
