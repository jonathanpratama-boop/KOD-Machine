"""MSCI_DELETION_OPT_v1: a bounded, exploratory holding-period study of the MSCI Indonesia deletion trade (spot, long only).

Diagnosis (PROTOCOL.md section 2, written before this code ran): the frozen 20-session rule lost out of time mostly
because it carried the falling IDX market for 20 sessions, while the forced-selling concession is documented to reverse
within days. The one lever studied is the holding period, with everything else fixed: the same events, the same
closing-auction entry on MSCI's implementation session, the same harness, costs, matched controls and account. The
original 20-session rule is the baseline.

Search: 6 holds {1, 2, 3, 5, 10, 20} sessions. Selection: an expanding walk-forward over 23 non-sealed scheduled reviews
(Nov 2019 .. Aug 2023, then Feb 2025 .. Aug 2026; Nov23 is excluded because its 20-session baseline hold reaches the
sealed window). Before each outer review the hold is chosen on the earlier
reviews only (account log-growth, averaged with the grid neighbours, ties to the shorter hold; cash if none is positive)
and applied to that review. Outer results never feed back. The sealed IDX holdout (2024 reviews) is never computed.

Every review here was inspected before (MSCI_DELETION_v1, MSCI_DELETION_OOT_v1: holds 5, 20, 60 and the next-session
entry), so any result is EXPLORATORY. A candidate licenses only a frozen, paper-only prospective protocol; whether to ask
the owner about the sealed reviews is a separate decision that this verdict does not justify. It is never evidence of
future profit and never a live promotion.

    python3 research/MSCI_DELETION_OPT_v1/opt.py --feasibility   # counts and reproduction flags only
    python3 research/MSCI_DELETION_OPT_v1/opt.py --freeze
    python3 research/MSCI_DELETION_OPT_v1/opt.py --run
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import itertools
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
# MSCI_DELETION_OOT_v1 loads MSCI_DELETION_v1 itself (as sys.modules["msci_deletion"]); both are frozen and used unchanged.
_spec = importlib.util.spec_from_file_location(
    "msci_deletion_oot", ROOT / "research/MSCI_DELETION_OOT_v1/oot.py"
)
oot = importlib.util.module_from_spec(_spec)
sys.modules["msci_deletion_oot"] = oot
_spec.loader.exec_module(oot)
v1 = oot.v1
from idxsig import idx_events
from idxsig.execution import STATUS, execute
from idxsig.market import Fees
from idxsig.provenance import sha256_file, utc_stamp

PROTO, RUN, FEAS = HERE / "protocol.json", HERE / "run", HERE / "FEASIBILITY.json"
EXITED = STATUS.index("EXITED")
HOLDS = (
    1,
    2,
    3,
    5,
    10,
    20,
)  # sessions after the implementation-close entry; 20 is the baseline (v1's rule)
BASELINE = 20
MIN_TRAIN = 4  # the first outer review has 4 earlier reviews to choose on
SEGMENTS = (
    ("discovery", v1.DISCOVERY),
    ("screen_2023", v1.SCREEN),
    ("oot", oot.REVIEWS),
)  # run exactly as the two frozen studies ran them (separate harness calls), so hold 20 reproduces their trades
# Nov23's 20-session baseline hold runs past 2023-12-29 into the sealed window (INCOMPLETE), so it would count as cash at
# hold 20 but as a real result at holds 1-10; it is dropped from selection and evaluation so every hold is compared on
# the same reviews (pre-freeze review finding S-1).
EXCLUDED = ("Nov23",)
ORDER = tuple(
    r for r in (*v1.DISCOVERY, *v1.SCREEN, *oot.REVIEWS) if r not in EXCLUDED
)  # chronological; the 2024 reviews (sealed) are absent
OUTER = ORDER[MIN_TRAIN:]
W3_REVIEWS = OUTER
WINDOWS = (
    ("dev", (*v1.DISCOVERY, *v1.SCREEN)),
    ("oot", tuple(oot.REVIEWS)),
)  # one prepared market each
BLOCKS = {
    "dev_outer": tuple(r for r in OUTER if r in (*v1.DISCOVERY, *v1.SCREEN)),
    "oot": tuple(oot.REVIEWS),
}
PLANS = ("base", "S1_entry_next_session", "S2_tick_cost", "S3_double_fees")
DOUBLE_FEES = Fees(0.0030, 0.0050)
LIQ_BUCKET = 4  # the liquid market: names in the top quintile of 20-session median traded value at the signal session
GATES = {
    "W0_sample": "a property of the sample, not of the selector: the outer reviews hold at least 30 deletion trades "
    "scored with matched controls at every hold 1..20 under the base plan, from at least 10 outer reviews; else "
    "INCONCLUSIVE",
    "W1_account": "the walk-forward account (v1 sizing: slots fixed before the auction, each at most 25% of equity and "
    "IDR 40m, cash otherwise; from IDR 160m) ends above its start",
    "W2_net": "walk-forward mean net trade return > 0 and its review-cluster bootstrap one-sided 95% lower bound > 0",
    "W3_vs_baseline": "the walk-forward account ends above the hold-20 baseline account on the same outer reviews",
    "W4_blocks": "walk-forward mean net trade return > 0 in both blocks: development outer reviews (Nov20..Aug23) and "
    "out-of-time reviews (Feb25..Aug26)",
    "W5_winners": "walk-forward account P&L without its 3 largest winning trades > 0",
    "W6_stress": "walk-forward mean net trade return > 0, with the holds selected under the base plan, under each of S1 "
    "(entry one session later), S2 (one tick per side) and S3 (fees doubled to 0.30%/0.50%)",
    "W7_incremental": "walk-forward mean of (net trade return minus the equal-weight liquid IDX market's net return under "
    "the same plan and window) > 0",
    "W8_not_brittle": "on the outer reviews with at least one deletion, the hold selected most often (ties: shorter; a "
    "tie with cash counts as cash) and at least one of its grid neighbours both have outer mean net trade return > 0 "
    "as fixed rules; fails if cash was selected most often",
    "verdict": "EXPLORATORY_CANDIDATE if W0-W8 all pass; INCONCLUSIVE if W0 fails; otherwise EXPLORATORY_REJECT. "
    "Exploratory because every review was inspected before; given that inspection a candidate is the expected outcome "
    "if a short hold is chosen and adds little new support. A candidate licenses only a frozen prospective paper "
    "protocol from MSCI's next review; never a live promotion and never evidence of future profit. A reject or an "
    "inconclusive result ends this family's search on history. One run; no other grid, plan, event set or window.",
}


# ------------------------------------------------------------------------------------------------------------ plans
def plan_config(hold: int, plan: str):
    if plan == "base":
        return v1.config(hold=hold)
    if plan == "S1_entry_next_session":
        return v1.config(hold=hold, entry_lag=2)
    if plan == "S2_tick_cost":
        return v1.config(hold=hold, tick_cost=True)
    if plan == "S3_double_fees":
        return dataclasses.replace(v1.config(hold=hold), fees=DOUBLE_FEES)
    raise ValueError(plan)


# ------------------------------------------------------------------------------------------------------------ inputs
def segment_inputs():
    """The two frozen studies' own inputs: development (rows <= 2023-12-29) and out-of-time (window 2025-02-24 ..
    2026-10-06, matching features trailing into the sealed window as in MSCI_DELETION_OOT_v1; no return inside it)."""
    df, reg, meta = v1.load_inputs()
    ev_all = pd.read_csv(v1.EVENTS)
    prep, sessions = v1.prepared(df, reg, ev_all)
    dev = {
        "discovery": v1.deletion_events(ev_all, sessions, v1.DISCOVERY),
        "screen_2023": v1.deletion_events(ev_all, sessions, v1.SCREEN),
    }
    del df
    df2, reg2, meta2 = oot.load_inputs()
    ev2 = pd.read_csv(oot.EVENTS)
    prep2, sessions2 = oot.prepared(df2, reg2, ev2)
    out = {
        "discovery": (prep, dev["discovery"]),
        "screen_2023": (prep, dev["screen_2023"]),
        "oot": (prep2, oot.oot_events(ev2, sessions2)),
    }
    if (
        meta["panel_sha256"] != meta2["panel_sha256"]
        or meta["registry_sha256"] != meta2["registry_sha256"]
    ):
        raise RuntimeError("the two segments read different panels or registries")
    return out, {
        "panel_sha256": meta["panel_sha256"],
        "registry_sha256": meta["registry_sha256"],
    }


# ------------------------------------------------------------------------------------------------------------ market
def market_net(prep, res: pd.DataFrame, cfg) -> pd.Series:
    """Per event: the equal-weight mean net return, under the same plan from the same signal session, of the liquid IDX
    market (evaluable names, so MSCI's changed names of the review are excluded, in liquidity bucket LIQ_BUCKET)."""
    m = prep.m
    out = pd.Series(np.nan, index=res.index)
    for day, idx in res.groupby("signal_date").groups.items():
        s = int(np.searchsorted(m.dates, np.datetime64(day, "D")))
        if s >= len(m.dates) or str(m.dates[s]) != day:
            raise RuntimeError(f"signal date {day} is not a session of the window")
        names = np.flatnonzero(
            prep.evaluable[:, s] & (prep.feats["liquidity"][:, s] == LIQ_BUCKET)
        )
        if not len(names):
            continue
        t = execute(m, names, np.full(len(names), s), cfg)
        ok = (t["status"] == EXITED) & np.isfinite(
            t["net_return"]
        )  # names censored at a data end are left out
        if ok.any():
            out.loc[idx] = float(t["net_return"][ok].mean())
    return out


def run_keys(inputs: dict, keys, draws: int = v1.DRAWS) -> dict:
    """{(plan, hold): frame of every mapped deletion of the 24 reviews (Nov23 kept for the reproduction check), with
    study_segment, hold, plan, market_net, mkt_adj. MSCI's own `segment` column (SC/ST) is kept."""
    grid = {}
    for plan, h in keys:
        cfg = plan_config(h, plan)
        frames = []
        for seg, _ in SEGMENTS:
            prep, ev = inputs[seg]
            r = idx_events.run_events(prep, ev, cfg, draws=draws, seed=v1.SEED)
            r = r.assign(study_segment=seg, hold=h, plan=plan)
            r["market_net"] = market_net(prep, r, cfg)
            r["mkt_adj"] = r["net_return"] - r["market_net"]
            frames.append(r)
        grid[(plan, h)] = pd.concat(frames, ignore_index=True)
    return grid


def run_grid(inputs: dict, plans=PLANS, draws: int = v1.DRAWS) -> dict:
    return run_keys(inputs, [(pl, h) for pl in plans for h in HOLDS], draws)


# ------------------------------------------------------------------------------------------------------------ selection
def criterion(frame: pd.DataFrame, reviews) -> float:
    """Training objective: log growth of v1's account over the given reviews."""
    a = v1.account(frame, tuple(reviews))
    return float(np.log(a["end_equity"] / a["start"]))


def smooth(crit: dict) -> dict:
    """Each hold's criterion averaged with its neighbours in the ordered grid (anti-brittleness)."""
    hs = sorted(crit)
    return {
        h: float(np.mean([crit[x] for x in hs[max(0, i - 1) : i + 2]]))
        for i, h in enumerate(hs)
    }


def choose(sm: dict) -> int | None:
    """The best smoothed hold (ties: the shorter); None (cash) if no hold's smoothed criterion is positive."""
    best = min(sm, key=lambda h: (-sm[h], h))
    return best if sm[best] > 0 else None


def check_purge(base: dict, order=ORDER) -> None:
    """Every training trade, at the longest hold, has exited before the next review's entry session."""
    f = base[max(HOLDS)]
    entries = f[f.entry_date.astype(str) != ""].groupby("review").entry_date.min()
    exits = f[f.exit_date.astype(str) != ""].groupby("review").exit_date.max()
    seq = [
        r for r in order if r in entries.index
    ]  # reviews without a deletion do not break the chain
    for a, b in itertools.pairwise(seq):
        if a in exits.index and str(exits[a]) >= str(entries[b]):
            raise RuntimeError(f"{a}'s trades are still held at {b}'s entry")


def walk_forward(base: dict, order=ORDER, min_train: int = MIN_TRAIN) -> list[dict]:
    """base: {hold: frame} under the base plan. One record per outer review: the hold chosen on the earlier reviews."""
    out = []
    with_deletions = set(base[min(base)].review)
    for k in range(min_train, len(order)):
        train = order[:k]
        crit = {h: criterion(base[h], train) for h in sorted(base)}
        sm = smooth(crit)
        out.append(
            {
                "review": order[k],
                "train_reviews": len(train),
                "criterion": crit,
                "smoothed": sm,
                "chosen": choose(sm),
                "has_deletions": order[k] in with_deletions,
            }
        )
    return out


def assemble(frames: dict, picks: list[dict]) -> pd.DataFrame:
    """The walk-forward trades: for each outer review, its trades under the chosen hold (none when cash)."""
    parts = [
        frames[p["chosen"]][frames[p["chosen"]].review == p["review"]]
        for p in picks
        if p["chosen"] is not None
    ]
    cols = next(iter(frames.values())).columns
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=cols)


# ------------------------------------------------------------------------------------------------------------ economics
def economics(
    f: pd.DataFrame, acc: dict, sessions_in_period: int, years: float, cfg_fees: Fees
) -> dict:
    """Trade and capital economics of a scored trade frame and its v1 account. Trade statistics use the trades with
    matched controls (as summarize does); exposure, turnover and fees use every trade the account held. Fees exclude
    the S2 tick; a zero return is neither a win nor a loss."""
    held_x = f[f.net_return.notna()]
    x = idx_events.filled(f)
    wins, losses = x.net_return[x.net_return > 0], x.net_return[x.net_return < 0]
    w = {r: wt for r, wt in _weights(held_x, acc)}
    held = sum(w.get(t.review, 0.0) * max(int(t.hold), 1) for t in held_x.itertuples())
    traded = sum(2 * w.get(t.review, 0.0) for t in held_x.itertuples())
    return {
        "trades": len(x),
        "trades_held_by_account": len(held_x),
        "zero_return_trades": int((x.net_return == 0).sum()),
        "win_rate": float((x.net_return > 0).mean()) if len(x) else None,
        "avg_win": float(wins.mean()) if len(wins) else None,
        "avg_loss": float(losses.mean()) if len(losses) else None,
        "payoff_ratio": float(wins.mean() / -losses.mean())
        if len(wins) and len(losses) and losses.mean() < 0
        else None,
        "expectancy_per_trade": float(x.net_return.mean()) if len(x) else None,
        "median_net": float(x.net_return.median()) if len(x) else None,
        "worst_net": float(x.net_return.min()) if len(x) else None,
        "best_net": float(x.net_return.max()) if len(x) else None,
        "mean_capital_per_review": acc["mean_capital_per_review"],
        "exposure_nominal_hold": float(held / sessions_in_period)
        if sessions_in_period
        else None,
        "turnover_per_year": float(traded / years) if years else None,
        "fees_per_year_pct_equity": float(
            traded / 2 * (cfg_fees.buy + cfg_fees.sell) / years
        )
        if years
        else None,
    }


def _weights(x: pd.DataFrame, acc: dict):
    """The per-review slot weight v1's account used (recomputed from its curve: equity before the review)."""
    curve = dict(acc["curve"])
    eq_before, prev = {}, acc["start"]
    for r, v in acc["curve"][1:]:
        eq_before[r], prev = prev, v
    for r, g in x.groupby("review"):
        if r not in curve:
            continue
        eq = eq_before[r]
        slots = int(acc["slots"][r])
        yield r, min(v1.MAX_WEIGHT, 1.0 / slots, v1.NOTIONAL / eq)


def account(f: pd.DataFrame, reviews, skip_review=None) -> dict:
    """v1's account, plus each review's slot count (for the economics)."""
    a = v1.account(f, tuple(reviews), skip_review=skip_review)
    a["slots"] = {
        r: int((~f[f.review == r].status.isin(v1.DECISION_SKIPS)).sum())
        for r in reviews
        if r != skip_review
    }
    return a


def summary(f: pd.DataFrame, reviews, windows: dict, fees: Fees) -> dict:
    """Trades, matched-control excess, market-adjusted return, account and economics on the given reviews."""
    g = f[f.review.isin(reviews)]
    s = v1.summarize(g)
    fl = idx_events.filled(g)
    s["mean_mkt_adj"] = float(fl.mkt_adj.mean()) if fl.mkt_adj.notna().any() else None
    s["mean_market_net"] = (
        float(fl.market_net.mean()) if fl.market_net.notna().any() else None
    )
    s["boot_mkt_adj"] = v1.cluster_bootstrap(
        fl.mkt_adj.dropna().to_numpy(), fl.review[fl.mkt_adj.notna()]
    )
    acc = account(g, reviews)
    sessions, years = period_length(reviews, windows)
    s["account"] = {k: v for k, v in acc.items() if k != "slots"}
    s["economics"] = economics(g, acc, sessions, years, fees)
    return s


def period_length(reviews, windows: dict) -> tuple[int, float]:
    """IDX sessions from the first given review's entry to the entry of the next review with a deletion after the last
    one (or the window's last session), summed over the two windows (development, out-of-time); years at 245
    sessions. Reviews without a deletion have no entry and are skipped."""
    total = 0
    for w, revs in WINDOWS:
        d, entry = windows[w]
        mine = [
            r for r in revs if r in reviews and r in entry
        ]  # reviews with a deletion
        if not mine:
            continue
        nxt = [entry[r] for r in revs if r in entry and entry[r] > entry[mine[-1]]]
        last = nxt[0] if nxt else str(d[-1])
        total += int(
            np.searchsorted(d, np.datetime64(last, "D"))
            - np.searchsorted(d, np.datetime64(entry[mine[0]], "D"))
        )
    return total, total / 245.0


def first_entry(windows: dict, w: str, reviews) -> str:
    """The entry session of the first of `reviews` that has a deletion in window `w`."""
    entry = windows[w][1]
    found = next((entry[r] for r in reviews if r in entry), None)
    if found is None:
        raise RuntimeError(f"no review of {reviews} has a deletion in window {w}")
    return found


def market_buy_and_hold(
    prep, first_entry: str, step: int = 20, last: str | None = None
) -> dict:
    """Descriptive benchmark: the equal-weight liquid IDX market held continuously from `first_entry` to `last` (default:
    the window's end), rebalanced every `step` sessions, costs charged once in and once out (favours the benchmark)."""
    m = prep.m
    s0 = (
        int(np.searchsorted(m.dates, np.datetime64(first_entry, "D"))) - 1
    )  # signal session: entry at first_entry
    end = (
        len(m.dates) - 1
        if last is None
        else int(np.searchsorted(m.dates, np.datetime64(last, "D")))
    )
    gross, s, blocks = 1.0, s0, 0
    zero = dataclasses.replace(v1.config(hold=step), fees=Fees(0.0, 0.0))
    while s + 1 < end:
        h = min(step, end - (s + 1))
        cfg = dataclasses.replace(zero, holding_days=h)
        names = np.flatnonzero(
            prep.evaluable[:, s] & (prep.feats["liquidity"][:, s] == LIQ_BUCKET)
        )
        t = execute(m, names, np.full(len(names), s), cfg)
        ok = (t["status"] == EXITED) & np.isfinite(t["gross_return"])
        gross *= 1 + float(t["gross_return"][ok].mean())
        s += h
        blocks += 1
    fees = v1.config().fees
    net = gross * (1 - fees.sell) / (1 + fees.buy) - 1
    return {
        "from_entry": first_entry,
        "to": str(m.dates[end]),
        "blocks": blocks,
        "net_return": float(net),
    }


# ------------------------------------------------------------------------------------------------------------ gates
def gates(r: dict) -> dict:
    wf, g = r["walk_forward"], {}
    p = wf["base"]
    smp = r["outer_sample"]
    g["W0_sample"] = "PASS" if smp["trades"] >= 30 and smp["reviews"] >= 10 else "FAIL"
    a = p["account"]
    g["W1_account"] = "PASS" if a["end_equity"] > a["start"] else "FAIL"
    bn = p.get("boot_net", {})
    g["W2_net"] = (
        "PASS"
        if (p.get("mean_net") or -1) > 0 and (bn.get("lower_one_sided_95") or -1) > 0
        else "FAIL"
    )
    w3 = r["w3_accounts"]
    g["W3_vs_baseline"] = (
        "PASS"
        if w3["walk_forward"]["end_equity"] > w3["baseline"]["end_equity"]
        else "FAIL"
    )
    blocks = wf["base_blocks"]
    g["W4_blocks"] = (
        "PASS" if all((blocks[b].get("mean_net") or -1) > 0 for b in BLOCKS) else "FAIL"
    )
    g["W5_winners"] = "PASS" if a["pnl_without_top3"] > 0 else "FAIL"
    g["W6_stress"] = (
        "PASS"
        if all((wf[pl].get("mean_net") or -1) > 0 for pl in PLANS if pl != "base")
        else "FAIL"
    )
    g["W7_incremental"] = "PASS" if (p.get("mean_mkt_adj") or -1) > 0 else "FAIL"
    mode = r["selection"]["most_selected"]
    if mode is None:
        g["W8_not_brittle"] = "FAIL"
    else:
        fixed = r["fixed_outer"]
        i = HOLDS.index(mode)
        nb = [HOLDS[j] for j in (i - 1, i + 1) if 0 <= j < len(HOLDS)]
        ok = (fixed[str(mode)].get("mean_net") or -1) > 0 and any(
            (fixed[str(h)].get("mean_net") or -1) > 0 for h in nb
        )
        g["W8_not_brittle"] = "PASS" if ok else "FAIL"
    if g["W0_sample"] == "FAIL":
        verdict = "INCONCLUSIVE"
    elif all(v == "PASS" for v in g.values()):
        verdict = "EXPLORATORY_CANDIDATE"
    else:
        verdict = "EXPLORATORY_REJECT"
    return {"gates": g, "verdict": verdict}


def most_selected(picks: list[dict]) -> int | None:
    c = pd.Series(
        [
            p["chosen"] if p["chosen"] is not None else -1
            for p in picks
            if p.get("has_deletions", True)
        ]
    ).value_counts()
    if c.empty:
        return None
    top = c[c == c.max()].index
    best = min(top)  # ties: shorter (cash, -1, wins a tie: conservative)
    return None if best == -1 else int(best)


# ------------------------------------------------------------------------------------------------------------ reproduction
COMMITTED = {
    "discovery": ROOT / "research/MSCI_DELETION_v1/run/discovery",
    "screen_2023": ROOT / "research/MSCI_DELETION_v1/run/screen_2023",
    "oot": ROOT / "research/MSCI_DELETION_OOT_v1/run",
}
REPRO = {
    ("base", 20): "primary",
    ("S1_entry_next_session", 20): "S1_entry_next_session",
    ("S2_tick_cost", 20): "S2_tick_cost",
    ("base", 5): "descriptive_hold_5",
}
REPRO_COLS = (
    "ticker",
    "review",
    "status",
    "entry_date",
    "exit_date",
    "net_return",
    "control_mean",
)


def reproduces(grid: dict) -> dict:
    """The frozen studies' committed trade files, recomputed here: hold 20 (primary, S1, S2) and hold 5 (descriptive).
    Returns True/False per file; no return is printed."""
    out = {}
    for key, name in REPRO.items():
        if key not in grid:
            continue
        for seg, folder in COMMITTED.items():
            want = pd.read_csv(
                folder / f"trades_{name}.csv", keep_default_na=False, na_values=[""]
            )
            got = grid[key][grid[key].study_segment == seg].reset_index(drop=True)
            ok = len(want) == len(got)
            for c in REPRO_COLS if ok else ():
                a, b = want[c], got[c]
                if c in ("net_return", "control_mean"):
                    a, b = (
                        pd.to_numeric(a, errors="coerce").to_numpy(),
                        b.astype(float).to_numpy(),
                    )
                    ok &= bool(np.allclose(a, b, rtol=0, atol=1e-12, equal_nan=True))
                else:
                    ok &= bool(
                        (
                            a.fillna("").astype(str).to_numpy()
                            == b.fillna("").astype(str).to_numpy()
                        ).all()
                    )
            out[f"{seg}/{name}"] = bool(ok)
    return out


# ------------------------------------------------------------------------------------------------------------ modes
def windows_of(inputs: dict) -> dict:
    """Per window: its sessions and each review's entry session."""
    dev = pd.concat([inputs["discovery"][1], inputs["screen_2023"][1]])
    return {
        "dev": (
            inputs["discovery"][0].m.dates,
            dict(zip(dev.review, dev.entry_session)),
        ),
        "oot": (
            inputs["oot"][0].m.dates,
            dict(zip(inputs["oot"][1].review, inputs["oot"][1].entry_session)),
        ),
    }


def feasibility() -> int:
    if PROTO.exists():
        sys.exit("error: protocol.json exists")
    inputs, meta = segment_inputs()
    grid = run_grid(inputs, plans=("base",), draws=5)
    counts = {str(h): idx_events.status_counts(grid[("base", h)]) for h in HOLDS}
    scored = {
        str(h): {
            seg: len(idx_events.filled(f[f.segment == seg])) for seg, _ in SEGMENTS
        }
        for h, f in ((h, grid[("base", h)]) for h in HOLDS)
    }
    out = {
        "study": "MSCI_DELETION_OPT_v1",
        "computed_at": utc_stamp(),
        "what": "status counts and scored-trade counts per hold (5 control draws) and reproduction flags; no return "
        "printed, saved or looked at",
        **meta,
        "reviews": {
            "order": list(ORDER),
            "outer": list(OUTER),
            "blocks": {k: list(v) for k, v in BLOCKS.items()},
        },
        "events": {seg: len(inputs[seg][1]) for seg, _ in SEGMENTS},
        "status_counts_by_hold": counts,
        "scored_with_controls_by_hold": scored,
        "outer_sample_at_5_draws": outer_sample({h: grid[("base", h)] for h in HOLDS}),
        "reproduces_frozen_studies": reproduces(
            run_keys(inputs, list(REPRO), draws=v1.DRAWS)
        ),
        "reproduction_note": "hold 20 (primary, S1, S2) and hold 5 recomputed at 200 draws against the two frozen "
        "studies' committed trade files (already published results); only True/False is shown",
    }
    FEAS.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return 0


PINS = (
    "research/MSCI_DELETION_OPT_v1/opt.py",
    "research/MSCI_DELETION_OPT_v1/report.py",
    "research/MSCI_DELETION_OPT_v1/PROTOCOL.md",
    "research/MSCI_DELETION_OPT_v1/FEASIBILITY.json",
    "research/MSCI_DELETION_OPT_v1/FEASIBILITY_pass1_repro_compare_bug.json",
    "tests/test_msci_deletion_opt.py",
    "research/MSCI_DELETION_OOT_v1/protocol.json",
    "research/MSCI_DELETION_v1/protocol.json",
    *(
        f"research/MSCI_DELETION_{d}/trades_{n}.csv"
        for d in ("v1/run/discovery", "v1/run/screen_2023", "OOT_v1/run")
        for n in (
            "primary",
            "S1_entry_next_session",
            "S2_tick_cost",
            "descriptive_hold_5",
        )
    ),
    *oot.PINS,
)


def frozen_fields() -> dict:
    return {
        "holds": list(HOLDS),
        "baseline": BASELINE,
        "min_train": MIN_TRAIN,
        "order": list(ORDER),
        "outer": list(OUTER),
        "excluded_reviews": list(EXCLUDED),
        "blocks": {k: list(v) for k, v in BLOCKS.items()},
        "plans": {
            p: {k: str(v) for k, v in plan_config(BASELINE, p).__dict__.items()}
            for p in PLANS
        },
        "liquid_bucket": LIQ_BUCKET,
        "draws": v1.DRAWS,
        "seed": v1.SEED,
        "bootstrap": v1.BOOT,
        "selection": "criterion = log(end/start) of v1's account on the training reviews; smoothed = mean over the hold "
        "and its grid neighbours; choose the max smoothed (ties: shorter); cash if max smoothed <= 0",
        "gates": GATES,
        "versions": v1.versions(),
    }


def freeze() -> int:
    if PROTO.exists():
        sys.exit("error: protocol.json exists")
    v1.git_clean([*PINS, "idxsig"])
    v1.inputs_reproduce()
    oot.inputs_reproduce()
    proto = {
        "study_id": "MSCI_DELETION_OPT_v1",
        "frozen_at": utc_stamp(),
        **frozen_fields(),
        "idxsig_tree": v1.idxsig_tree(),
        "code_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip(),
        "pins": {p: sha256_file(ROOT / p) for p in PINS},
    }
    PROTO.write_text(json.dumps(proto, indent=1) + "\n")
    print(
        json.dumps(
            {k: proto[k] for k in ("study_id", "frozen_at", "holds", "gates")}, indent=1
        )
    )
    return 0


def verify_frozen() -> dict:
    proto = json.loads(PROTO.read_text())
    v1.git_clean([*PINS, "research/MSCI_DELETION_OPT_v1/protocol.json", "idxsig"])
    if set(proto["pins"]) != set(PINS):
        sys.exit("error: protocol.json pins a different file set")
    for p, want in proto["pins"].items():
        if sha256_file(ROOT / p) != want:
            sys.exit(f"error: {p} changed since the freeze")
    for k, want in frozen_fields().items():
        if proto[k] != want:
            sys.exit(f"error: protocol.json '{k}' differs from this code")
    if proto["idxsig_tree"] != v1.idxsig_tree():
        sys.exit("error: the idxsig package changed since the freeze")
    v1.inputs_reproduce()
    oot.inputs_reproduce()
    return proto


def trial_rows(
    grid: dict, picks: list[dict], wf_frames: dict, ss: dict
) -> pd.DataFrame:
    """The trial log: every (plan, hold) as a fixed rule on all 23 reviews (Nov23 excluded), on the outer reviews and per block, and the
    walk-forward sequence under every plan."""
    rows = []
    for (plan, h), f in grid.items():
        fees = plan_config(h, plan).fees
        for scope, revs in (("all_23", ORDER), ("outer_19", OUTER), *BLOCKS.items()):
            s = summary(f, revs, ss, fees)
            rows.append(_row(f"fixed_hold_{h}", plan, scope, s))
    for plan, f in wf_frames.items():
        fees = plan_config(BASELINE, plan).fees
        for scope, revs in (("outer_19", OUTER), *BLOCKS.items()):
            s = summary(f, revs, ss, fees)
            rows.append(_row("walk_forward", plan, scope, s))
    return pd.DataFrame(rows)


def _row(trial: str, plan: str, scope: str, s: dict) -> dict:
    e, a = s.get("economics", {}), s.get("account", {})
    return {
        "trial": trial,
        "plan": plan,
        "scope": scope,
        "scored": s.get("scored_with_controls"),
        "mean_net": s.get("mean_net"),
        "median_net": s.get("median_net"),
        "win_rate": s.get("win_rate"),
        "avg_win": e.get("avg_win"),
        "avg_loss": e.get("avg_loss"),
        "payoff_ratio": e.get("payoff_ratio"),
        "mean_excess_vs_controls": s.get("mean_excess"),
        "mean_market_net": s.get("mean_market_net"),
        "mean_mkt_adj": s.get("mean_mkt_adj"),
        "boot_net_lower_one_sided_95": (s.get("boot_net") or {}).get(
            "lower_one_sided_95"
        ),
        "account_end_idr": a.get("end_equity"),
        "account_return": a.get("net_return"),
        "max_dd_at_review_exits": a.get("max_drawdown_at_review_exits"),
        "pnl_without_top3_idr": a.get("pnl_without_top3"),
        "mean_capital_per_review": e.get("mean_capital_per_review"),
        "exposure_nominal_hold": e.get("exposure_nominal_hold"),
        "turnover_per_year": e.get("turnover_per_year"),
        "fees_per_year_pct_equity": e.get("fees_per_year_pct_equity"),
    }


def outer_sample(base: dict) -> dict:
    """W0: deletion trades on the outer reviews scored with matched controls at every hold (independent of selection)."""
    keys = None
    for f in base.values():
        fl = idx_events.filled(f[f.review.isin(OUTER)])
        k = set(zip(fl.review, fl.ticker))
        keys = k if keys is None else keys & k
    keys = keys or set()
    return {"trades": len(keys), "reviews": len({r for r, _ in keys})}


def check_data_end(grid: dict, windows: dict | None = None) -> None:
    """No studied trade (a review in ORDER, any plan and hold) may be EXIT_DATA_END (scored at its last traded close
    because the name has no row at the window's end: it could have resumed later, inside the sealed window for
    development) or INCOMPLETE (its hold runs past the data: the Nov23-type asymmetry between holds). The feasibility
    counts show none in the base plan; any in the run aborts it."""
    for key, f in grid.items():
        bad = f[f.review.isin(ORDER) & f.status.isin(("EXIT_DATA_END", "INCOMPLETE"))]
        if len(bad):
            raise RuntimeError(
                f"{key}: trades censored at the data end: {bad[['review', 'ticker']].values.tolist()}"
            )


def analyse(grid: dict, ss: dict) -> tuple[dict, list[dict], dict]:
    """Everything after the harness runs: purge check, walk-forward, summaries. Pure (no I/O)."""
    base = {h: grid[("base", h)] for h in HOLDS}
    check_purge(base)
    picks = walk_forward(base)
    wf_frames = {pl: assemble({h: grid[(pl, h)] for h in HOLDS}, picks) for pl in PLANS}
    res = {
        "selection": {
            "picks": [
                {
                    "review": p["review"],
                    "train_reviews": p["train_reviews"],
                    "chosen": p["chosen"],
                    "has_deletions": p["has_deletions"],
                    "criterion": {str(k): v for k, v in p["criterion"].items()},
                    "smoothed": {str(k): v for k, v in p["smoothed"].items()},
                }
                for p in picks
            ],
            "most_selected": most_selected(picks),
            "counts_reviews_with_deletions": {
                str(k): int(v)
                for k, v in pd.Series(
                    [str(p["chosen"]) for p in picks if p["has_deletions"]]
                )
                .value_counts()
                .items()
            },
            # in-sample, for a prospective protocol only: the hold the same procedure picks on all reviews
            "final_choice_all_reviews": choose(
                smooth({h: criterion(base[h], ORDER) for h in sorted(base)})
            ),
        },
        "outer_sample": outer_sample(base),
        "walk_forward": {
            pl: summary(wf_frames[pl], OUTER, ss, plan_config(BASELINE, pl).fees)
            for pl in PLANS
        },
    }
    res["walk_forward"]["base_blocks"] = {
        b: summary(wf_frames["base"], revs, ss, plan_config(BASELINE, "base").fees)
        for b, revs in BLOCKS.items()
    }
    best = v1.best_review(wf_frames["base"])
    res["walk_forward"]["account_without_best_review"] = {
        "review": best,
        **{
            k: v
            for k, v in account(wf_frames["base"], OUTER, skip_review=best).items()
            if k != "slots"
        },
    }
    res["baseline_outer"] = summary(
        base[BASELINE], OUTER, ss, plan_config(BASELINE, "base").fees
    )
    res["w3_accounts"] = {
        name: {k: v for k, v in account(f, W3_REVIEWS).items() if k != "slots"}
        for name, f in (
            ("walk_forward", wf_frames["base"]),
            ("baseline", base[BASELINE]),
        )
    }
    res["fixed_outer"] = {
        str(h): summary(base[h], OUTER, ss, plan_config(h, "base").fees) for h in HOLDS
    }
    return res, picks, wf_frames


def run() -> int:
    if RUN.exists():
        sys.exit("error: run/ exists; MSCI_DELETION_OPT_v1 runs once")
    verify_frozen()
    inputs, meta = segment_inputs()
    feas = json.loads(FEAS.read_text())
    if (meta["panel_sha256"], meta["registry_sha256"]) != (
        feas["panel_sha256"],
        feas["registry_sha256"],
    ):
        sys.exit("error: panel or registry differs from the feasibility run")
    grid = run_grid(inputs)
    repro = reproduces(grid)
    if not all(repro.values()):
        sys.exit(
            f"error: the frozen studies' committed trades do not reproduce: {repro}"
        )
    ss = windows_of(inputs)
    check_data_end(grid, ss)
    part, picks, wf_frames = analyse(grid, ss)
    res = {
        "study": "MSCI_DELETION_OPT_v1",
        "ran_at": utc_stamp(),
        **meta,
        "protocol_sha256": sha256_file(PROTO),
        "versions": v1.versions(),
        "label": "EXPLORATORY: every review was inspected before",
        "reproduces_frozen_studies": repro,
        **part,
    }
    res["benchmarks"] = {
        "cash": {
            "net_return": 0.0,
            "note": "IDR cash at 0%; deposit interest not credited to either side",
        },
        "liquid_market_buy_and_hold": {
            "dev_outer": market_buy_and_hold(
                inputs["discovery"][0],
                first_entry(ss, "dev", BLOCKS["dev_outer"]),
                last=ss["dev"][1][
                    EXCLUDED[0]
                ],  # stop where the excluded Nov23 review starts
            ),
            "oot": market_buy_and_hold(
                inputs["oot"][0], first_entry(ss, "oot", BLOCKS["oot"])
            ),
        },
    }
    res.update(gates(res))
    res["commit"] = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    trials = trial_rows(grid, picks, wf_frames, ss)
    RUN.mkdir()
    trials.to_csv(RUN / "TRIALS.csv", index=False)
    for (pl, h), f in grid.items():
        f.to_csv(RUN / f"trades_{pl}_hold{h}.csv", index=False)
    for pl, f in wf_frames.items():
        f.to_csv(RUN / f"walk_forward_{pl}.csv", index=False)
    (RUN / "RESULT.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    print(res["verdict"], json.dumps(res["gates"], indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--feasibility", action="store_true")
    g.add_argument("--freeze", action="store_true")
    g.add_argument("--run", action="store_true")
    a = ap.parse_args()
    return feasibility() if a.feasibility else freeze() if a.freeze else run()


if __name__ == "__main__":
    sys.exit(main())
