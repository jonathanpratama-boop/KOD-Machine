"""MSCI_DELETION_OPT_v1 on fixtures: neighbour smoothing, the walk-forward's information set, cash, purge, sizing, gates."""

import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1] / "research/MSCI_DELETION_OPT_v1"
spec = importlib.util.spec_from_file_location("msci_opt", HERE / "opt.py")
opt = importlib.util.module_from_spec(spec)
sys.modules["msci_opt"] = opt
spec.loader.exec_module(opt)

REVIEWS = ("R1", "R2", "R3", "R4", "R5", "R6")


def frame(nets: dict, hold: int = 1) -> pd.DataFrame:
    """nets: {review: [net returns]}; every trade EXITED."""
    rows = []
    for r, xs in nets.items():
        for i, x in enumerate(xs):
            rows.append(
                {
                    "review": r,
                    "ticker": f"{r}{i}",
                    "status": "EXITED",
                    "net_return": x,
                    "control_mean": 0.0,
                    "excess": x,
                    "hold": hold,
                    "market_net": 0.0,
                    "mkt_adj": x,
                    "entry_date": "",
                    "exit_date": "",
                }
            )
    return pd.DataFrame(rows)


class Selection(unittest.TestCase):
    def test_smoothing_averages_grid_neighbours(self):
        sm = opt.smooth({1: 0.3, 2: 0.0, 3: -0.3, 5: 0.6})
        self.assertAlmostEqual(sm[1], 0.15)
        self.assertAlmostEqual(sm[2], 0.0)
        self.assertAlmostEqual(sm[3], 0.1)
        self.assertAlmostEqual(sm[5], 0.15)

    def test_ties_go_to_the_shorter_hold_and_nothing_positive_is_cash(self):
        self.assertEqual(opt.choose({1: 0.1, 2: 0.1, 3: 0.05}), 1)
        self.assertEqual(opt.choose({1: 0.0, 2: -0.1}), None)

    def test_the_outer_review_never_informs_its_own_choice(self):
        good = {r: [0.02, 0.01] for r in REVIEWS}
        base = {1: frame(good, 1), 2: frame({r: [-0.01] for r in REVIEWS}, 2)}
        picks = opt.walk_forward(base, order=REVIEWS, min_train=2)
        self.assertEqual([p["review"] for p in picks], ["R3", "R4", "R5", "R6"])
        self.assertEqual([p["train_reviews"] for p in picks], [2, 3, 4, 5])
        # R5 becomes a disaster at hold 1: R5's own pick is unchanged, R6's moves away from hold 1
        bad = dict(good, R5=[-0.9, -0.9])
        base2 = {1: frame(bad, 1), 2: base[2]}
        picks2 = opt.walk_forward(base2, order=REVIEWS, min_train=2)
        self.assertEqual(picks[2]["chosen"], picks2[2]["chosen"])
        self.assertNotEqual(picks2[3]["chosen"], 1)

    def test_cash_reviews_contribute_no_trades(self):
        frames = {1: frame({"R3": [0.1], "R4": [0.2]}, 1)}
        picks = [{"review": "R3", "chosen": None}, {"review": "R4", "chosen": 1}]
        out = opt.assemble(frames, picks)
        self.assertEqual(out.review.tolist(), ["R4"])
        empty = opt.assemble(frames, [{"review": "R3", "chosen": None}])
        self.assertEqual(len(empty), 0)
        self.assertIn("net_return", empty.columns)

    def test_most_selected_breaks_ties_to_the_shorter_hold_and_cash_wins_ties(self):
        self.assertEqual(
            opt.most_selected(
                [{"chosen": 5}, {"chosen": 2}, {"chosen": 5}, {"chosen": 2}]
            ),
            2,
        )
        self.assertIsNone(opt.most_selected([{"chosen": None}, {"chosen": 3}]))


class MostSelected(unittest.TestCase):
    def test_reviews_without_deletions_are_not_counted(self):
        picks = [
            {"chosen": 5, "has_deletions": False},
            {"chosen": 5, "has_deletions": False},
            {"chosen": 2, "has_deletions": True},
            {"chosen": 5, "has_deletions": True},
            {"chosen": 2, "has_deletions": True},
        ]
        self.assertEqual(opt.most_selected(picks), 2)
        self.assertIsNone(opt.most_selected([{"chosen": 1, "has_deletions": False}]))

    def test_walk_forward_flags_reviews_without_deletions(self):
        base = {1: frame({"R1": [0.01], "R2": [0.01], "R4": [0.02]}, 1)}
        picks = opt.walk_forward(base, order=("R1", "R2", "R3", "R4"), min_train=2)
        self.assertEqual([p["has_deletions"] for p in picks], [False, True])


class Purge(unittest.TestCase):
    def test_the_chain_skips_reviews_without_entries(self):
        f = frame({"R1": [0.1], "R3": [0.1]}, 20)
        f["entry_date"] = ["2020-01-02", "2020-03-02"]
        f["exit_date"] = [
            "2020-03-05",
            "2020-03-30",
        ]  # R1 still held at R3's entry; R2 has no deletion
        with self.assertRaises(RuntimeError):
            opt.check_purge({20: f}, order=("R1", "R2", "R3"))

    def test_a_review_still_held_at_the_next_entry_raises(self):
        f = frame({"R1": [0.1], "R2": [0.1]}, 20)
        f["entry_date"] = ["2020-01-02", "2020-03-02"]
        f["exit_date"] = ["2020-01-30", "2020-03-30"]
        opt.check_purge({20: f}, order=("R1", "R2"))
        f.loc[0, "exit_date"] = "2020-03-02"
        with self.assertRaises(RuntimeError):
            opt.check_purge({20: f}, order=("R1", "R2"))


class Sizing(unittest.TestCase):
    def test_economics_uses_the_accounts_own_weights(self):
        f = frame({"R1": [0.10, -0.05], "R2": [0.02]}, 1)
        acc = opt.account(f, ("R1", "R2"))
        w = dict(opt._weights(f, acc))
        self.assertAlmostEqual(w["R1"], 0.25)  # min(25%, 1/2, 40m/160m)
        eq1 = opt.v1.START_CASH * (1 + 0.25 * 0.05)
        self.assertAlmostEqual(w["R2"], min(0.25, 1.0, opt.v1.NOTIONAL / eq1))
        self.assertAlmostEqual(acc["end_equity"], eq1 * (1 + w["R2"] * 0.02))
        e = opt.economics(
            f, acc, sessions_in_period=100, years=1.0, cfg_fees=opt.v1.config().fees
        )
        self.assertAlmostEqual(e["avg_win"], 0.06)
        self.assertAlmostEqual(e["avg_loss"], -0.05)
        self.assertAlmostEqual(e["exposure_nominal_hold"], (0.25 * 2 + w["R2"]) / 100)
        self.assertAlmostEqual(e["turnover_per_year"], 2 * (0.25 * 2 + w["R2"]))

    def test_plans(self):
        self.assertEqual(opt.plan_config(3, "S1_entry_next_session").entry_lag, 2)
        self.assertTrue(opt.plan_config(3, "S2_tick_cost").tick_cost)
        f = opt.plan_config(3, "S3_double_fees").fees
        self.assertEqual((f.buy, f.sell), (0.003, 0.005))
        self.assertEqual(opt.plan_config(3, "base").holding_days, 3)
        with self.assertRaises(ValueError):
            opt.plan_config(3, "other")


def result(**kw):
    p = {
        "scored_with_controls": 40,
        "by_review": {str(i): {} for i in range(12)},
        "mean_net": 0.02,
        "boot_net": {"lower_one_sided_95": 0.001},
        "mean_mkt_adj": 0.01,
        "account": {"start": 160.0, "end_equity": 180.0, "pnl_without_top3": 5.0},
    }
    p.update(kw.pop("p", {}))
    r = {
        "walk_forward": {
            "base": p,
            "base_blocks": {"dev_outer": {"mean_net": 0.01}, "oot": {"mean_net": 0.01}},
            "S1_entry_next_session": {"mean_net": 0.01},
            "S2_tick_cost": {"mean_net": 0.01},
            "S3_double_fees": {"mean_net": 0.01},
        },
        "w3_accounts": {
            "walk_forward": {"end_equity": 175.0},
            "baseline": {"end_equity": 150.0},
        },
        "selection": {"most_selected": 2},
        "outer_sample": {"trades": 80, "reviews": 15},
        "fixed_outer": {str(h): {"mean_net": 0.01} for h in opt.HOLDS},
    }
    for k, v in kw.items():
        r[k] = v
    return r


class Gates(unittest.TestCase):
    def test_all_pass_is_an_exploratory_candidate(self):
        self.assertEqual(opt.gates(result())["verdict"], "EXPLORATORY_CANDIDATE")

    def test_each_failure(self):
        self.assertEqual(
            opt.gates(result(outer_sample={"trades": 20, "reviews": 15}))["verdict"],
            "INCONCLUSIVE",
        )
        self.assertEqual(
            opt.gates(result(outer_sample={"trades": 80, "reviews": 9}))["verdict"],
            "INCONCLUSIVE",
        )
        # an all-cash walk-forward is a reject, not inconclusive (W0 does not depend on the selector)
        cash = result(
            p={
                "scored_with_controls": 0,
                "by_review": {},
                "mean_net": None,
                "boot_net": {},
                "mean_mkt_adj": None,
                "account": {
                    "start": 160.0,
                    "end_equity": 160.0,
                    "pnl_without_top3": 0.0,
                },
            },
            selection={"most_selected": None},
        )
        self.assertEqual(opt.gates(cash)["verdict"], "EXPLORATORY_REJECT")
        self.assertEqual(
            opt.gates(result(p={"boot_net": {"lower_one_sided_95": -0.001}}))[
                "verdict"
            ],
            "EXPLORATORY_REJECT",
        )
        r = result()
        r["w3_accounts"]["baseline"]["end_equity"] = 190.0
        self.assertEqual(opt.gates(r)["gates"]["W3_vs_baseline"], "FAIL")
        r = result()
        r["walk_forward"]["base_blocks"]["oot"]["mean_net"] = -0.01
        self.assertEqual(opt.gates(r)["gates"]["W4_blocks"], "FAIL")
        r = result()
        r["walk_forward"]["S3_double_fees"]["mean_net"] = -0.001
        self.assertEqual(opt.gates(r)["gates"]["W6_stress"], "FAIL")
        self.assertEqual(
            opt.gates(result(p={"mean_mkt_adj": -0.01}))["gates"]["W7_incremental"],
            "FAIL",
        )

    def test_brittleness(self):
        r = result()
        r["fixed_outer"]["1"]["mean_net"] = r["fixed_outer"]["3"]["mean_net"] = -0.01
        self.assertEqual(opt.gates(r)["gates"]["W8_not_brittle"], "FAIL")
        r = result(selection={"most_selected": None})
        self.assertEqual(opt.gates(r)["gates"]["W8_not_brittle"], "FAIL")
        r = result(selection={"most_selected": 1})
        r["fixed_outer"]["2"]["mean_net"] = -0.01
        self.assertEqual(opt.gates(r)["gates"]["W8_not_brittle"], "FAIL")


def synthetic_grid(seed=7):
    """Fake trades for every (plan, hold) on the 24 reviews: no market data, only the analysis code paths."""
    rng = np.random.default_rng(seed)
    dev = pd.bdate_range("2019-10-01", "2023-12-29").to_numpy().astype("datetime64[D]")
    oo = pd.bdate_range("2025-02-24", "2026-10-06").to_numpy().astype("datetime64[D]")
    with_deletions = [
        r for i, r in enumerate(opt.ORDER) if i % 4 != 1
    ]  # some reviews have none, as in the data
    entries, k = {}, {"dev": 40, "oot": 3}
    for r in with_deletions:
        w = "oot" if r in opt.BLOCKS["oot"] else "dev"
        d = oo if w == "oot" else dev
        entries[r] = (w, str(d[k[w]]))
        k[w] += 62 if w == "dev" else 58
    windows = {
        w: (d, {r: e for r, (ww, e) in entries.items() if ww == w})
        for w, d in (("dev", dev), ("oot", oo))
    }
    grid = {}
    for plan in opt.PLANS:
        for h in opt.HOLDS:
            rows = []
            for r, (w, e) in entries.items():
                d = oo if w == "oot" else dev
                i = int(np.searchsorted(d, np.datetime64(e)))
                for j in range(3):
                    x = float(rng.normal(0.01, 0.05))
                    m = float(rng.normal(0.0, 0.02))
                    rows.append(
                        {
                            "review": r,
                            "ticker": f"{r}{j}",
                            "kind": "SC_EXIT",
                            "status": "EXITED",
                            "net_return": x,
                            "control_mean": m,
                            "excess": x - m,
                            "match_level": 0,
                            "hold": h,
                            "plan": plan,
                            "study_segment": w,
                            "market_net": m,
                            "mkt_adj": x - m,
                            "entry_date": e,
                            "exit_date": str(d[min(i + h, len(d) - 1)]),
                        }
                    )
            grid[(plan, h)] = pd.DataFrame(rows)
    return grid, windows


class EndToEnd(unittest.TestCase):
    def test_analysis_trial_log_gates_and_report_on_fake_trades(self):
        import tempfile

        grid, windows = synthetic_grid()
        part, picks, wf = opt.analyse(grid, windows)
        self.assertEqual(len(picks), len(opt.OUTER))
        res = {
            "ran_at": "x",
            "commit": "c",
            "protocol_sha256": "0" * 64,
            "reproduces_frozen_studies": {"a": True},
            **part,
            "benchmarks": {
                "cash": {"net_return": 0.0},
                "liquid_market_buy_and_hold": {
                    b: {"from_entry": "d0", "to": "d1", "net_return": 0.01}
                    for b in ("dev_outer", "oot")
                },
            },
        }
        res.update(opt.gates(res))
        self.assertIn(
            res["verdict"],
            ("EXPLORATORY_CANDIDATE", "EXPLORATORY_REJECT", "INCONCLUSIVE"),
        )
        trials = opt.trial_rows(grid, picks, wf, windows)
        self.assertEqual(
            len(trials), len(opt.PLANS) * len(opt.HOLDS) * 4 + len(opt.PLANS) * 3
        )
        # the walk-forward under the base plan equals, review by review, the chosen fixed hold's trades
        for p in picks:
            got = wf["base"][wf["base"].review == p["review"]]
            if p["chosen"] is None:
                self.assertEqual(len(got), 0)
            else:
                want = grid[("base", p["chosen"])]
                self.assertEqual(
                    got.net_return.tolist(),
                    want[want.review == p["review"]].net_return.tolist(),
                )
        spec2 = importlib.util.spec_from_file_location(
            "msci_opt_report", HERE / "report.py"
        )
        rep = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(rep)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "run").mkdir()
            import json

            (Path(tmp) / "run/RESULT.json").write_text(json.dumps(res, default=str))
            trials.to_csv(Path(tmp) / "run/TRIALS.csv", index=False)
            rep.HERE = Path(tmp)
            self.assertEqual(rep.main(), 0)
            text = (Path(tmp) / "REPORT.md").read_text()
            self.assertIn(res["verdict"], text)
            self.assertIn("fixed_hold", trials.trial.iloc[0])


class FakePrep:
    """A market of 3 names x 30 sessions for the liquid-market helpers (execute is replaced)."""

    def __init__(self):
        class M:
            dates = (
                pd.bdate_range("2021-01-04", periods=30)
                .to_numpy()
                .astype("datetime64[D]")
            )

        self.m = M()
        self.evaluable = np.ones((3, 30), dtype=bool)
        self.evaluable[2, :] = (
            False  # name 2 is never in the market (e.g. changed by MSCI)
        )
        self.feats = {"liquidity": np.full((3, 30), opt.LIQ_BUCKET)}
        self.feats["liquidity"][1, :] = 0  # name 1 is illiquid


class LiquidMarket(unittest.TestCase):
    def setUp(self):
        self.calls = []

        def fake_execute(m, names, sigs, cfg):
            self.calls.append(
                (list(names), int(sigs[0]), cfg.holding_days, cfg.fees.buy)
            )
            n = len(names)
            return {
                "status": np.zeros(n, dtype=int),
                "net_return": np.full(n, 0.01),
                "gross_return": np.full(n, 0.02),
            }

        self._orig = opt.execute
        opt.execute = fake_execute

    def tearDown(self):
        opt.execute = self._orig

    def test_market_net_uses_liquid_evaluable_names_at_the_signal_session(self):
        prep = FakePrep()
        res = pd.DataFrame(
            {
                "signal_date": [
                    str(prep.m.dates[3]),
                    str(prep.m.dates[3]),
                    str(prep.m.dates[7]),
                ]
            }
        )
        out = opt.market_net(prep, res, opt.plan_config(2, "base"))
        self.assertEqual(out.tolist(), [0.01, 0.01, 0.01])
        self.assertEqual(
            [c[0] for c in self.calls], [[0], [0]]
        )  # only name 0; one call per signal session
        self.assertEqual(sorted(c[1] for c in self.calls), [3, 7])

    def test_buy_and_hold_chains_blocks_to_the_window_end_with_costs_once(self):
        prep = FakePrep()
        out = opt.market_buy_and_hold(prep, str(prep.m.dates[5]), step=10)
        # entry at session 5 (signal 4); blocks of 10, 10 and the remaining 4 sessions to session 29
        self.assertEqual([c[1] for c in self.calls], [4, 14, 24])
        self.assertEqual([c[2] for c in self.calls], [10, 10, 4])
        self.assertTrue(
            all(c[3] == 0.0 for c in self.calls)
        )  # gross inside, costs once at the ends
        fees = opt.v1.config().fees
        self.assertAlmostEqual(
            out["net_return"], 1.02**3 * (1 - fees.sell) / (1 + fees.buy) - 1
        )
        self.assertEqual(out["blocks"], 3)

    def test_buy_and_hold_can_stop_before_the_window_end(self):
        prep = FakePrep()
        out = opt.market_buy_and_hold(
            prep, str(prep.m.dates[5]), step=10, last=str(prep.m.dates[20])
        )
        self.assertEqual([c[2] for c in self.calls], [10, 5])  # sessions 5..15, 15..20
        self.assertEqual(out["to"], str(prep.m.dates[20]))


class DataEnd(unittest.TestCase):
    def test_any_censored_or_incomplete_studied_trade_aborts(self):
        ok = frame({"Aug23": [0.1]}, 5)
        opt.check_data_end({("base", 5): ok})
        for status in ("EXIT_DATA_END", "INCOMPLETE"):
            bad = ok.assign(
                status=status, exit_date="2023-12-15"
            )  # as the harness writes it: before the window end
            with self.assertRaises(RuntimeError):
                opt.check_data_end({("S1_entry_next_session", 10): bad})
        nov23 = frame({"Nov23": [0.1]}, 20).assign(
            status="INCOMPLETE"
        )  # excluded review: kept only for reproduction
        opt.check_data_end({("base", 20): nov23})


class OuterSample(unittest.TestCase):
    def test_counts_trades_scored_at_every_hold_on_outer_reviews(self):
        a = frame({"Nov20": [0.1, 0.2], "Feb21": [0.1], "Nov19": [0.3]}, 1)
        b = frame({"Nov20": [0.1], "Feb21": [0.1], "Nov19": [0.3]}, 20)
        self.assertEqual(opt.outer_sample({1: a, 20: b}), {"trades": 2, "reviews": 2})


class Constants(unittest.TestCase):
    def test_windows_exclude_the_sealed_reviews(self):
        self.assertEqual(len(opt.ORDER), 23)
        self.assertFalse(any(r.endswith("24") for r in opt.ORDER))
        self.assertNotIn(
            "Nov23", opt.ORDER
        )  # its 20-session baseline reaches the sealed window
        self.assertEqual(opt.OUTER[0], "Nov20")
        self.assertEqual(opt.W3_REVIEWS, opt.OUTER)
        self.assertEqual(len(opt.OUTER), 19)
        self.assertEqual(opt.BLOCKS["dev_outer"][-1], "Aug23")
        self.assertEqual(opt.BLOCKS["oot"][0], "Feb25")
        self.assertEqual(opt.HOLDS[-1], opt.BASELINE)
        self.assertTrue(np.all(np.diff(opt.HOLDS) > 0))


if __name__ == "__main__":
    unittest.main()
