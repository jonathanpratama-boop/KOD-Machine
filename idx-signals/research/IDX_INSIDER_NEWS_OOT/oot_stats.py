"""IDX_INSIDER_NEWS_OOT: the gates, the reading rules and the descriptive tables of PROTOCOL.md as pure functions (tested in
tests/test_idx_oot.py). Imported by run.py."""
import numpy as np
import pandas as pd

HURDLE_T = 1.65                    # one-sided 5%: a replication of one pre-specified effect
MIN_YEAR_EVENTS = 20
EXTRA_PER_SIDE = 0.005
G1, G2, G3, G4 = ("G1_excess_t_ge_1.65", "G2_net_and_winsorised_net_gt_0", "G3_excess_gt_0_in_each_year_with_20_events",
                  "G4_net_gt_0_with_extra_0.5pct_per_side")


def gates(f: pd.DataFrame, stats: dict) -> tuple[dict, dict]:
    yr = f.assign(year=f.posted_wib.str[:4]).groupby("year").excess.agg(["count", "mean"])
    big = yr[yr["count"] >= MIN_YEAR_EVENTS]
    g = {G1: bool(stats["mean_excess"] > 0 and stats["t_excess"] >= HURDLE_T),
         G2: bool(stats["mean_net"] > 0 and stats["winsorised_net"] > 0),
         G3: bool(len(big) > 0 and (big["mean"] > 0).all()),
         G4: bool(stats["mean_net_extra_cost"] > 0)}
    return g, {str(k): {"n": int(r["count"]), "mean_excess": float(r["mean"])} for k, r in yr.iterrows()}


def reading(g: dict, stats: dict) -> str:
    """The protocol's reading rules, in order."""
    if all(g.values()):
        return "PASS"
    if g[G1] and not g[G4]:
        return "G1_HOLDS_G4_FAILS_TOO_SMALL_AFTER_FRICTIONS"
    if g[G1]:
        return "G1_HOLDS_ANOTHER_GATE_FAILS"
    if stats["mean_excess"] > 0 and stats["t_excess"] >= 1.0:
        return "LEAN_WITHOUT_POWER"
    return "NO_SIGN_IT_PERSISTED"


def half_years(f: pd.DataFrame) -> dict:
    half = f.posted_wib.str[:4] + np.where(f.posted_wib.str[5:7].astype(int) <= 6, "H1", "H2")
    return {k: {"n": int(len(g)), "mean_net": float(g.net_return.mean()), "mean_excess": float(g.excess.mean())} for k, g in f.groupby(half)}


def tail(f: pd.DataFrame) -> dict:
    srt = f.sort_values("excess", ascending=False)
    tot = float(f.excess.sum())
    return {"top5_share_of_total_excess": float(srt.excess.iloc[:5].sum() / tot) if tot else None,
            "top20_share_of_total_excess": float(srt.excess.iloc[:20].sum() / tot) if tot else None,
            "mean_excess_without_top10": float(srt.excess.iloc[10:].mean()), "median_excess": float(f.excess.median()),
            "share_excess_positive": float((f.excess > 0).mean())}


def pooled(a: dict, b: dict) -> dict:
    """Inverse-variance pooled excess of two estimates, each {mean_excess, lo95_excess, hi95_excess}; the standard error is read from the
    bootstrap interval. Descriptive only."""
    se = lambda s: (s["hi95_excess"] - s["lo95_excess"]) / 3.92  # noqa: E731
    wa, wb = 1 / se(a) ** 2, 1 / se(b) ** 2
    mean = (a["mean_excess"] * wa + b["mean_excess"] * wb) / (wa + wb)
    s = (wa + wb) ** -0.5
    return {"mean_excess": float(mean), "se": float(s), "t": float(mean / s), "weights": {"discovery": float(wa / (wa + wb)), "out_of_time": float(wb / (wa + wb))}}
