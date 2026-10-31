"""SCORE_VALUE_v1: how the frozen pre-move scores translate into trade value, and whether the daily top-five admission
order picks the wrong alerts (research/SCORE_VALUE_v1/protocol.json). Attribution only: no model, stop, target or
ranking is changed; any rule the curves suggest would need a fresh period.

    python3 research/SCORE_VALUE_v1/score_value.py --counts --panel <panel.csv.gz>   # candidate counts, no outcome
    python3 research/SCORE_VALUE_v1/score_value.py --freeze --panel <panel.csv.gz>
    python3 research/SCORE_VALUE_v1/score_value.py --panel <panel.csv.gz>

Inputs: the 2023 early-population candidates of PREMOVE_SEQUENCE_v1 (every eligible coin-day, not just the top five),
scored with the frozen summary, sequence and shuffled-control coefficients exactly as CRYPTO_REPLAY_v1/rankings.py
did (the top five per day must reproduce the pinned shortlists); every candidate whose predicted upside probability
under any arm reaches FLOOR is traded on its own with CRYPTO_REPLAY_v1's frozen BASE rules; the BASE account's
decisions label the shortlisted ones.

Analyses, fixed before the run:
  A  calibration: realized hit rate by predicted-probability bin on all early candidates, per arm; the shortlist's
     mean predicted probability against its realized hit rate
  B  global threshold curve: candidates with p >= t (any day, no budget): count, days, hit rate, mean and median
     isolated net return, and the same on first alerts of consecutive-day runs
  C  admission timing: isolated outcomes of all five alerts on days the account could admit versus days it could not
  D  rank anatomy: predicted p, repeat share, volatility, hit rate and isolated net by rank 1..5
  E  value accounting: EV per alert = P(hit) x net(hit) + P(non-hit) x net(non-hit); the EV the predicted
     probabilities implied; the hit rate needed for 1% net per trade at the observed payoffs
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from idxsig import crypto_replay as cr
from idxsig import premove, premove_shadow
from idxsig.premove_core import build_examples, prepare_panel
from idxsig.provenance import sha256_file, utc_stamp

REPLAY = ROOT / "research/CRYPTO_REPLAY_v1"
PROTO, RESULTS = HERE / "protocol.json", HERE / "results"
PANEL_SHA256 = "f1dfd57d26a7a98781bd5fcbf18db3203778d24c51c46b4d4f92963dc9b75766"
FIRST, LAST = date(2023, 1, 1), date(2023, 12, 31)
ARMS = ("summary", "sequence", "shuffled")
MODEL_ARMS = ("summary", "sequence")
POLICY = cr.Policy()
NOTIONAL = POLICY.risk * POLICY.start_cash / POLICY.loss_fraction
FLOOR = 0.05  # candidates traded in isolation: predicted upside probability >= 5% under any arm
BINS = [0, 0.01, 0.02, 0.03, 0.05, 0.075, 0.10, 0.15, 0.20, 0.30, 1.0]
THRESHOLDS = [0.05, 0.075, 0.10, 0.15, 0.20, 0.30]
BOOT = {"draws": 2000, "seed": 20261031, "unit": "signal day"}
PINS = (
    "idxsig/crypto_replay.py",
    "idxsig/premove.py",
    "idxsig/premove_core.py",
    "idxsig/premove_shadow.py",
    "research/SCORE_VALUE_v1/score_value.py",
    "research/CRYPTO_REPLAY_v1/protocol.json",
    "research/CRYPTO_REPLAY_v1/rankings/shortlists_2023.csv.gz",
    "research/CRYPTO_REPLAY_v1/run/trades_BASE_summary.csv.gz",
    "research/CRYPTO_REPLAY_v1/run/trades_BASE_sequence.csv.gz",
    "research/CRYPTO_REPLAY_v1/run/trades_BASE_shuffled.csv.gz",
    "research/PREMOVE_SEQUENCE_v1/runs/20261030T024900Z/models.json",
    "research/PREMOVE_SEQUENCE_v1/runs/20261030T024900Z/summary.json",
    "research/PREMOVE_SHADOW_v1/control_model.json",
)


# ------------------------------------------------------------------------------------------- candidates
def candidates(panel: Path) -> pd.DataFrame:
    """Every eligible 2023 early-population coin-day with the three arms' calibrated upside probabilities, the
    model's own label, and its volatility; the top five per day must equal the pinned shortlists."""
    protocol = json.loads((ROOT / "research/PREMOVE_SEQUENCE_v1/protocol.json").read_text())
    examples = build_examples(prepare_panel(pd.read_csv(panel), market="CRYPTO"))
    test = premove.period(examples.frame, *protocol["periods"]["test"])
    arms, temps = premove_shadow.load_arms(), premove_shadow.temperatures()
    shuffled = premove_shadow.shuffle_windows(test)
    for arm, model in arms.items():
        p = premove.probabilities(
            model.predict(shuffled if arm == "shuffled" else test), temps[arm]
        )
        test[f"{arm}_up"] = p[:, 0]
    early = test.loc[(test.ret1 < 0.10) & (test.ret5 < 0.20)].copy()
    early["date"] = early["date"].dt.strftime("%Y-%m-%d")
    early["barrier"] = early["barrier_up_fraction"]
    cols = [
        "date",
        "ticker",
        "summary_up",
        "sequence_up",
        "shuffled_up",
        "label_known",
        "up_first",
        "ret1",
        "ret5",
        "vol20",
        "barrier",
        "median_value20",
    ]
    early = early[cols].reset_index(drop=True)
    pinned = pd.read_csv(REPLAY / "rankings/shortlists_2023.csv.gz")
    pinned = pinned[pinned.population == "early"]
    for arm in ARMS:
        top = (
            early.sort_values(
                ["date", f"{arm}_up", "ticker"], ascending=[True, False, True], kind="stable"
            )
            .groupby("date", sort=True)
            .head(5)
        )
        want = pinned[pinned.method == arm].sort_values(["date", "rank"])[["date", "ticker"]]
        if not top[["date", "ticker"]].reset_index(drop=True).equals(want.reset_index(drop=True)):
            sys.exit(f"error: the rebuilt {arm} top five does not reproduce the pinned shortlists")
    return early


def counts(panel: Path) -> int:
    early = candidates(panel)
    print(f"early candidates 2023: {len(early):,} coin-days, {early.date.nunique()} days")
    for arm in ARMS:
        binned = pd.cut(early[f"{arm}_up"], BINS, right=False)
        print(arm, binned.value_counts(sort=False).to_dict())
    union = early[(early[[f"{a}_up" for a in ARMS]] >= FLOOR).any(axis=1)]
    print(f"to simulate (p >= {FLOOR:.0%} under any arm): {len(union):,} coin-days")
    return 0


def freeze(panel: Path) -> int:
    if PROTO.exists():
        sys.exit("error: protocol.json exists")
    if sha256_file(panel) != PANEL_SHA256:
        sys.exit("error: wrong panel")
    proto = {
        "study_id": "SCORE_VALUE_v1",
        "frozen_at": utc_stamp(),
        "asked_by": (
            "Ace, 2026-10-31: the next research problem is how scores translate into trade value and admission "
            "priority; execute until the issue is narrower or resolved; no strategy changes"
        ),
        "status": (
            "attribution study on 2023 (already-studied data), simulation only; not investable, not a strategy, "
            "no permission to buy; 2024 data never read; any threshold or priority rule the curves suggest is a "
            "hypothesis for a fresh period, not a result"
        ),
        "candidates": (
            "every eligible 2023 early-population coin-day scored with the frozen coefficients and temperatures "
            "(no fitting); the top five per day must reproduce CRYPTO_REPLAY_v1's pinned shortlists"
        ),
        "isolated_trade": {
            "who": f"every candidate with predicted upside probability >= {FLOOR:.0%} under any arm, plus every "
            "shortlisted alert",
            "engine": "idxsig.crypto_replay.run, one alert, CRYPTO_REPLAY_v1 BASE policy, equity 10,000",
            "policy": POLICY.record(),
            "notional_usd": NOTIONAL,
        },
        "bins": BINS,
        "thresholds": THRESHOLDS,
        "analyses": __doc__.split("Analyses, fixed before the run:")[1].strip(),
        "verdict_rules": {
            "calibration": (
                "OVERCONFIDENT AT THE TOP if, in every bin that holds shortlisted alerts, the realized hit rate "
                "is below half the bin's mean predicted probability, in both model arms"
            ),
            "threshold": (
                "reported for every threshold; a level is called PROMISING only if its mean isolated net return "
                "is >= 1.0% with >= 100 candidates in the year, in both model arms; promising means test it on "
                "a fresh period, nothing more"
            ),
            "timing": (
                "ENTERS AT BAD TIMES if, in both model arms, the five alerts on days the account admitted "
                "something average a lower isolated net return than on days it admitted nothing, with the "
                "signal-day bootstrap interval of the difference below zero"
            ),
        },
        "bootstrap": BOOT,
        "pins": {p: sha256_file(ROOT / p) for p in PINS},
    }
    PROTO.write_text(json.dumps(proto, indent=1) + "\n")
    print(
        json.dumps(
            {k: proto[k] for k in ("study_id", "frozen_at", "isolated_trade", "verdict_rules")},
            indent=1,
        )
    )
    return 0


# ---------------------------------------------------------------------------------------- isolated trades
def isolated(bars, ticker: str, signal_day: date) -> dict:
    sl = pd.DataFrame([{"date": signal_day.isoformat(), "ticker": ticker, "rank": 1}])
    last = min(signal_day + timedelta(days=15), LAST)
    acct = cr.run(sl, bars, signal_day, last, POLICY)
    if last < LAST and any(e["type"] == "UNRESOLVED" for e in acct.events):
        acct = cr.run(sl, bars, signal_day, LAST, POLICY)
    ev = {e["type"]: e for e in acct.events}
    if "UNFILLED" in ev:
        return {"iso_status": "UNFILLED_AFTER_DATA", "iso_exit": None, "iso_net": np.nan}
    en = ev["ENTRY"]
    if en["status"] != "FILLED":
        return {"iso_status": en["status"], "iso_exit": None, "iso_net": np.nan}
    if "EXIT" in ev:
        ex = ev["EXIT"]
        return {"iso_status": "CLOSED", "iso_exit": ex["reason"], "iso_net": ex["net_return"]}
    return {
        "iso_status": "UNRESOLVED",
        "iso_exit": None,
        "iso_net": ev["UNRESOLVED"]["unrealized"] / NOTIONAL,
    }


def boot_diff(a: pd.DataFrame, b: pd.DataFrame) -> dict:
    days = sorted(set(a["date"]) | set(b["date"]))
    ga = {d: x["iso_net"].to_numpy() for d, x in a.groupby("date")}
    gb = {d: x["iso_net"].to_numpy() for d, x in b.groupby("date")}
    rng = np.random.default_rng(BOOT["seed"])
    draws = []
    for _ in range(BOOT["draws"]):
        pick = rng.choice(days, len(days))
        xa = np.concatenate([ga.get(d, np.empty(0)) for d in pick])
        xb = np.concatenate([gb.get(d, np.empty(0)) for d in pick])
        if len(xa) and len(xb):
            draws.append(xa.mean() - xb.mean())
    lo, hi = np.quantile(draws, [0.025, 0.975])
    return {
        "diff": float(a.iso_net.mean() - b.iso_net.mean()),
        "lower95": float(lo),
        "upper95": float(hi),
    }


def hit_rate(x: pd.DataFrame) -> float:
    return (
        float((x.label_known.astype(bool) & (x.up_first == 1)).mean()) if len(x) else float("nan")
    )


def closed(x: pd.DataFrame) -> pd.DataFrame:
    return x[x.iso_status == "CLOSED"]


def net_stats(x: pd.DataFrame) -> dict:
    c = closed(x)
    return {
        "n": len(x),
        "closed": len(c),
        "hit_rate": hit_rate(x),
        "mean_net": float(c.iso_net.mean()) if len(c) else None,
        "median_net": float(c.iso_net.median()) if len(c) else None,
        "win_rate": float((c.iso_net > 0).mean()) if len(c) else None,
    }


def first_of_run(frame: pd.DataFrame) -> pd.Series:
    f = frame.sort_values(["ticker", "date"])
    prev = f.groupby("ticker")["date"].shift(1)
    gap = (pd.to_datetime(f["date"]) - pd.to_datetime(prev)).dt.days
    return (gap.isna() | (gap > 1)).reindex(frame.index)


# ------------------------------------------------------------------------------------------- analyses
def analyse(early: pd.DataFrame, alerts: pd.DataFrame, arm: str) -> dict:
    p = f"{arm}_up"
    a = alerts[alerts.method == arm].copy()
    out = {}
    # A calibration
    early = early.copy()
    early["bin"] = pd.cut(early[p], BINS, right=False)
    rows = {}
    for b, g in early.groupby("bin", observed=True):
        gi = g[g.iso_status.notna()]
        rows[str(b)] = {
            "n": len(g),
            "mean_predicted": float(g[p].mean()),
            "hit_rate": hit_rate(g),
            "shortlisted": int(g.shortlisted.sum()),
            "closed_isolated": len(closed(gi)),
            "mean_net": float(closed(gi).iso_net.mean()) if len(closed(gi)) else None,
        }
    out["A"] = {
        "by_bin": rows,
        "shortlist_mean_predicted": float(a[p].mean()),
        "shortlist_hit_rate": hit_rate(a),
        "shortlist_hit_rate_known": float((a.up_first == 1)[a.label_known.astype(bool)].mean()),
        "all_candidates_mean_predicted": float(early[p].mean()),
        "all_candidates_hit_rate": hit_rate(early),
    }
    # B global thresholds
    thr = {}
    for t in THRESHOLDS:
        g = early[early[p] >= t].copy()
        g["first"] = first_of_run(g) if len(g) else pd.Series(dtype=bool)
        thr[f"{t:.3f}"] = {
            **net_stats(g),
            "days_with_candidates": int(g.date.nunique()),
            "max_per_day": int(g.groupby("date").size().max()) if len(g) else 0,
            "first_of_run": net_stats(g[g["first"]]) if len(g) else None,
            "promising": bool(
                len(g) >= 100 and (closed(g).iso_net.mean() if len(closed(g)) else -1) >= 0.01
            ),
        }
    out["B"] = thr
    # C admission timing
    cap_days = set(a.loc[a.account == "ORDER", "date"])
    on, off = a[a.date.isin(cap_days)], a[~a.date.isin(cap_days)]
    out["C"] = {
        "days_with_admission": len(cap_days),
        "days_without": int(a.date.nunique() - len(cap_days)),
        "alerts_on_admission_days": net_stats(on),
        "alerts_on_other_days": net_stats(off),
        "on_minus_off": boot_diff(closed(on), closed(off)),
        "admitted_on_admission_days": net_stats(on[on.account == "ORDER"]),
        "skipped_on_admission_days": net_stats(on[on.account != "ORDER"]),
    }
    # D rank anatomy
    a["first"] = first_of_run(a)
    out["D"] = {
        int(r): {
            **net_stats(g),
            "mean_predicted": float(g[p].mean()),
            "repeat_share": float(1 - g["first"].mean()),
            "median_vol20": float(g.vol20.median()),
            "median_value20": float(g.median_value20.median()),
            "admitted_share": float((g.account == "ORDER").mean()),
        }
        for r, g in a.groupby("rank")
    }
    # E value accounting
    c = closed(a)
    hit = c.label_known.astype(bool) & (c.up_first == 1)
    non = c.label_known.astype(bool) & (c.up_first != 1)
    ph, net_h, net_n = (
        float(hit.mean()),
        float(c.loc[hit, "iso_net"].mean()),
        float(c.loc[non, "iso_net"].mean()),
    )
    out["E"] = {
        "p_hit": ph,
        "net_given_hit": net_h,
        "net_given_non_hit": net_n,
        "ev_per_alert": float(c.iso_net.mean()),
        "ev_decomposed": ph * net_h + (1 - ph) * net_n,
        "ev_implied_by_predicted_p": float(a[p].mean()) * net_h + (1 - float(a[p].mean())) * net_n,
        "hit_rate_needed_for_1pct": (0.01 - net_n) / (net_h - net_n) if net_h > net_n else None,
        "usd_per_year_at_account_size": float(c.iso_net.mean()) * NOTIONAL * len(c),
    }
    return out


def verdicts(res: dict) -> list[str]:
    A = {arm: res["arms"][arm]["A"] for arm in MODEL_ARMS}
    over = []
    for arm in MODEL_ARMS:
        bins = [b for b in A[arm]["by_bin"].values() if b["shortlisted"] > 0]
        if bins and all(b["hit_rate"] < 0.5 * b["mean_predicted"] for b in bins):
            over.append(arm)
    cal = (
        (
            "Calibration: OVERCONFIDENT AT THE TOP in both model arms."
            if len(over) == 2
            else f"Calibration: overconfident at the top in {', '.join(over) or 'neither arm'}."
        )
        + " "
        + "; ".join(
            f"{arm}: shortlist predicted {A[arm]['shortlist_mean_predicted']:.1%} vs realized "
            f"{A[arm]['shortlist_hit_rate']:.1%}"
            for arm in MODEL_ARMS
        )
        + "."
    )
    B = {arm: res["arms"][arm]["B"] for arm in MODEL_ARMS}
    promising = [
        t for t in B["summary"] if B["summary"][t]["promising"] and B["sequence"][t]["promising"]
    ]
    thr = "Threshold curve: " + (
        f"PROMISING levels (both arms, >= 1% mean net, >= 100 candidates): {', '.join(promising)}; a hypothesis "
        "for a fresh period."
        if promising
        else "no threshold level reaches 1% mean net with 100 candidates in both arms."
    )
    C = {arm: res["arms"][arm]["C"]["on_minus_off"] for arm in MODEL_ARMS}
    bad = [arm for arm in MODEL_ARMS if C[arm]["upper95"] < 0]
    tim = (
        (
            "Timing: ENTERS AT BAD TIMES in both model arms."
            if len(bad) == 2
            else f"Timing: no consistent bad-timing effect ({', '.join(bad) or 'neither arm'} below zero)."
        )
        + " "
        + "; ".join(
            f"{arm}: admission days minus other days {C[arm]['diff'] * 100:+.2f} pts "
            f"(95% {C[arm]['lower95'] * 100:+.2f} to {C[arm]['upper95'] * 100:+.2f})"
            for arm in MODEL_ARMS
        )
        + "."
    )
    E = {arm: res["arms"][arm]["E"] for arm in MODEL_ARMS}
    val = (
        "Value: "
        + "; ".join(
            f"{arm}: EV {E[arm]['ev_per_alert'] * 100:+.2f}% per alert = hit rate {E[arm]['p_hit']:.1%} x "
            f"{E[arm]['net_given_hit'] * 100:+.1f}% + non-hits {E[arm]['net_given_non_hit'] * 100:+.2f}%; the "
            f"predicted probabilities implied {E[arm]['ev_implied_by_predicted_p'] * 100:+.2f}%; 1% per trade needs a "
            f"hit rate of {E[arm]['hit_rate_needed_for_1pct']:.1%}"
            for arm in MODEL_ARMS
        )
        + "."
    )
    return [cal, thr, tim, val]


def pc(x, d=2):
    return "-" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:+.{d}f}%"


def rt(x):
    return "-" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.1%}"


def render(res: dict) -> str:
    L = [
        "# SCORE_VALUE_v1: what a score is worth, and whether the top-five order picks the wrong alerts",
        "",
        f"Ran {res['ran_at']} at commit `{res['commit']}`. {res['status']}",
        "",
        (
            f"{res['n_candidates']:,} early-population coin-days in 2023; {res['n_simulated']:,} traded in isolation "
            f"(predicted probability >= {FLOOR:.0%} under any arm, or shortlisted) with the frozen BASE rules."
        ),
        "",
        "## Verdicts (fixed rules, from the numbers)",
        "",
        *[f"- {v}" for v in res["verdicts"]],
    ]
    for arm in ARMS:
        r = res["arms"][arm]
        A, B, C, D, E = r["A"], r["B"], r["C"], r["D"], r["E"]
        L += [
            "",
            f"## {arm}",
            "",
            "**A. Calibration on all candidates**",
            "",
            "| Predicted p bin | Candidates | Mean predicted | Realized hit rate | Of which shortlisted | Isolated trades | Mean net |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for b, s in A["by_bin"].items():
            L.append(
                f"| {b} | {s['n']} | {s['mean_predicted']:.1%} | {rt(s['hit_rate'])} | {s['shortlisted']} | "
                f"{s['closed_isolated']} | {pc(s['mean_net'])} |"
            )
        L += [
            "",
            (
                f"Shortlist: predicted {A['shortlist_mean_predicted']:.1%}, realized {A['shortlist_hit_rate']:.2%} "
                f"({A['shortlist_hit_rate_known']:.2%} of known). All candidates: predicted "
                f"{A['all_candidates_mean_predicted']:.2%}, realized {A['all_candidates_hit_rate']:.2%}."
            ),
            "",
            "**B. Global threshold curve (no daily budget)**",
            "",
            "| p >= | Candidates | Days | Max/day | Hit rate | Closed | Mean net | Median net | Win rate | First-of-run n | First-of-run mean net |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for t, s in B.items():
            f = s["first_of_run"] or {}
            L.append(
                f"| {float(t):.1%} | {s['n']} | {s['days_with_candidates']} | {s['max_per_day']} | {rt(s['hit_rate'])} | "
                f"{s['closed']} | {pc(s['mean_net'])} | {pc(s['median_net'])} | {rt(s['win_rate'])} | "
                f"{f.get('n', '-')} | {pc(f.get('mean_net'))} |"
            )
        on, off, d = C["alerts_on_admission_days"], C["alerts_on_other_days"], C["on_minus_off"]
        L += [
            "",
            "**C. Admission timing**",
            "",
            (
                f"Days the account admitted something: {C['days_with_admission']}; days it admitted nothing: "
                f"{C['days_without']}. All five alerts on admission days: mean net {pc(on['mean_net'])} (n {on['n']}); "
                f"on other days {pc(off['mean_net'])} (n {off['n']}); difference {pc(d['diff'])} "
                f"(95% {pc(d['lower95'])} to {pc(d['upper95'])}). On admission days, admitted "
                f"{pc(C['admitted_on_admission_days']['mean_net'])} vs skipped "
                f"{pc(C['skipped_on_admission_days']['mean_net'])}."
            ),
            "",
            "**D. Rank anatomy**",
            "",
            "| Rank | Mean predicted | Repeat share | Median vol20 | Median 20-day value | Admitted share | Hit rate | Mean net |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for k, s in D.items():
            L.append(
                f"| {k} | {s['mean_predicted']:.1%} | {s['repeat_share']:.0%} | {s['median_vol20']:.1%} | "
                f"{s['median_value20']:,.0f} | {s['admitted_share']:.0%} | {rt(s['hit_rate'])} | {pc(s['mean_net'])} |"
            )
        L += [
            "",
            "**E. Value accounting**",
            "",
            (
                f"EV per alert {pc(E['ev_per_alert'])} = {E['p_hit']:.1%} x {pc(E['net_given_hit'], 1)} + "
                f"{1 - E['p_hit']:.1%} x {pc(E['net_given_non_hit'])}. The predicted probabilities implied "
                f"{pc(E['ev_implied_by_predicted_p'])}. A 1% net per trade needs a hit rate of "
                f"{rt(E['hit_rate_needed_for_1pct'])}. At the account's size and this many alerts: "
                f"{E['usd_per_year_at_account_size']:,.0f} USDT a year."
            ),
        ]
    L += [
        "",
        "## Limits",
        "",
        "- 2023 only, already studied; descriptive; the threshold curve is in-sample and selects nothing.",
        "- Isolated trades overlap and ignore cash; their sums are not portfolio results.",
        "- Daily bars and modelled costs.",
        "",
    ]
    return "\n".join(L)


def run(panel: Path) -> int:
    proto = json.loads(PROTO.read_text())
    if RESULTS.exists():
        sys.exit("error: results exist; the study runs once")
    for path, want in proto["pins"].items():
        if sha256_file(ROOT / path) != want:
            sys.exit(f"error: {path} changed since the freeze")
    if sha256_file(panel) != PANEL_SHA256:
        sys.exit("error: wrong panel")
    early = candidates(panel)
    raw = pd.read_csv(panel)
    bars = cr.bars_from_panel(
        raw[(raw["date"] >= FIRST.isoformat()) & (raw["date"] <= LAST.isoformat())], FIRST, LAST
    )
    pinned = pd.read_csv(REPLAY / "rankings/shortlists_2023.csv.gz")
    pinned = pinned[pinned.population == "early"][["date", "ticker", "method", "rank"]]
    keys = set(zip(pinned.date, pinned.ticker))
    early["shortlisted"] = [(d, t) in keys for d, t in zip(early.date, early.ticker)]
    todo = early[early.shortlisted | (early[[f"{a}_up" for a in ARMS]] >= FLOOR).any(axis=1)]
    print(f"simulating {len(todo):,} isolated trades", flush=True)
    iso = pd.DataFrame(
        [isolated(bars, t, date.fromisoformat(d)) for t, d in zip(todo.ticker, todo.date)],
        index=todo.index,
    )
    early = early.join(iso)
    alerts = pinned.merge(early.drop(columns=["shortlisted"]), on=["date", "ticker"], how="left")
    for arm in ARMS:
        ledger = pd.read_csv(REPLAY / f"run/trades_BASE_{arm}.csv.gz")[
            ["signal_day", "ticker", "decision"]
        ]
        ledger = ledger.rename(columns={"signal_day": "date", "decision": "account"})
        ledger["method"] = arm
        alerts = (
            alerts.merge(ledger, on=["date", "ticker", "method"], how="left")
            if arm == ARMS[0]
            else alerts.merge(
                ledger, on=["date", "ticker", "method"], how="left", suffixes=("", "_dup")
            )
        )
        if "account_dup" in alerts:
            alerts["account"] = alerts["account"].fillna(alerts.pop("account_dup"))
    if alerts.account.isna().any() or alerts.iso_status.isna().any():
        sys.exit("error: an alert lacks its account decision or its isolated trade")
    res = {
        "study": "SCORE_VALUE_v1",
        "ran_at": utc_stamp(),
        "status": proto["status"],
        "n_candidates": len(early),
        "n_simulated": int(early.iso_status.notna().sum()),
        "arms": {arm: analyse(early, alerts, arm) for arm in ARMS},
    }
    res["verdicts"] = verdicts(res)
    res["commit"] = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    RESULTS.mkdir()
    early.to_csv(RESULTS / "candidates_2023_early.csv.gz", index=False)
    alerts.to_csv(RESULTS / "alerts.csv.gz", index=False)
    (RESULTS / "RESULT.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    (HERE / "REPORT.md").write_text(render(res), encoding="utf-8")
    print("\n".join(res["verdicts"]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True, type=Path)
    ap.add_argument("--counts", action="store_true")
    ap.add_argument("--freeze", action="store_true")
    args = ap.parse_args()
    if args.counts:
        return counts(args.panel)
    return freeze(args.panel) if args.freeze else run(args.panel)


if __name__ == "__main__":
    sys.exit(main())
