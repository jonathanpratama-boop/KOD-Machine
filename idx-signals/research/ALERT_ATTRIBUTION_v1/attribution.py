"""ALERT_ATTRIBUTION_v1: every 2023 top-five early alert of CRYPTO_REPLAY_v1 evaluated as ONE isolated trade under the
same frozen BASE policy (entry next open, 0.1% fee + 0.1% slippage per side, 5% stop, 10% target, bar-5 close exit,
gaps at the open, stop-first ambiguity), with no portfolio admission limits, then labelled by what the BASE account
did with it (admitted, or skipped and why). An attribution study: not an investable account, not a new strategy.
Stops, targets, models and rankings are the frozen ones; nothing is tuned.

    python3 research/ALERT_ATTRIBUTION_v1/attribution.py --freeze --panel <panel.csv.gz>
    python3 research/ALERT_ATTRIBUTION_v1/attribution.py --panel <panel.csv.gz>

Three questions, answered by fixed analyses declared in protocol.json before the run:
  Q1  do higher model scores go with better net trade outcomes under our rules?
  Q2  are good alerts crowded out by positions the account already holds?
  Q3  does the model's predicted event (its close-to-close barrier) turn into our 10%-before-5% trade?
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
from idxsig.provenance import sha256_file, utc_stamp

REPLAY = ROOT / "research/CRYPTO_REPLAY_v1"
PROTO, RESULTS = HERE / "protocol.json", HERE / "results"
PANEL_SHA256 = "f1dfd57d26a7a98781bd5fcbf18db3203778d24c51c46b4d4f92963dc9b75766"
FIRST, LAST = date(2023, 1, 1), date(2023, 12, 31)
ARMS = ("summary", "sequence", "shuffled")
POLICY = cr.Policy()  # CRYPTO_REPLAY_v1's BASE scenario, unchanged
NOTIONAL = POLICY.risk * POLICY.start_cash / POLICY.loss_fraction  # the account's first-order size
BOOT = {"draws": 2000, "seed": 20261031, "unit": "signal day"}
PINS = (
    "idxsig/crypto_replay.py",
    "research/ALERT_ATTRIBUTION_v1/attribution.py",
    "research/CRYPTO_REPLAY_v1/protocol.json",
    "research/CRYPTO_REPLAY_v1/rankings/shortlists_2023.csv.gz",
    "research/CRYPTO_REPLAY_v1/run/trades_BASE_summary.csv.gz",
    "research/CRYPTO_REPLAY_v1/run/trades_BASE_sequence.csv.gz",
    "research/CRYPTO_REPLAY_v1/run/trades_BASE_shuffled.csv.gz",
)

ASKED_BY = (
    "Ace, 2026-10-31: evaluate every original top-five alert individually with the SAME frozen entry, exit and "
    "cost assumptions, without portfolio admission limits; label each 'admitted' or 'skipped'; do not change "
    "stops, targets, models or rankings"
)
STATUS = (
    "attribution study on 2023 (already-studied data), simulation only; not investable, not a strategy, no "
    "permission to buy; 2024 data never read"
)
ANALYSES = [
    (
        "A per arm: isolated outcomes of all alerts: fills, exit reasons, entry-day stops, mean and median net "
        "return, win rate, gross (pre-cost) vs net mean, cost per trade"
    ),
    (
        "B per arm: by frozen rank 1..5 and by within-arm score quintile: mean net return, win rate, model hit "
        "rate; Spearman rho between score and net return; top-minus-bottom quintile mean"
    ),
    (
        "C per arm: admitted vs skipped (and by skip reason): n, mean and median net return, win rate; "
        "skipped-minus-admitted mean with a signal-day bootstrap 95% interval; the same on the first alert of "
        "each consecutive-day run of one coin (overlapping alerts collapsed)"
    ),
    (
        "D per arm: cross-tab of the model's own label (hit = barrier up first on closes within 5 days; non-hit; "
        "censored) against the isolated trade outcome (TARGET, STOP, TIME_EXIT win/loss, other): "
        "P(target | hit), P(stop | hit), P(hit | target), entry-day stop rate"
    ),
    (
        "E per arm: entry-day stop rate and mean net return by vol20 tercile; share of alerts whose model barrier "
        "(max(10%, 3 vol20 sqrt5)) exceeds the 10% target; the stop in units of daily vol"
    ),
    "F reproduce Ace's figures from the account ledgers (hits admitted, entry-day stops, cost attribution)",
]
VERDICT_RULES = {
    "Q1": (
        "YES if, in both model arms, Spearman rho > 0 and the top score quintile's mean net return exceeds the "
        "bottom's; NO if neither; MIXED otherwise"
    ),
    "Q2": (
        "CROWDED OUT if skipped alerts' mean net return exceeds admitted alerts' with the bootstrap interval "
        "above zero in a model arm; NOT CROWDED OUT if the interval is below zero or includes zero"
    ),
    "Q3": (
        "the trade matches the forecast if P(target before stop | model hit) >= 0.5; otherwise the predicted "
        "event does not translate into this trade"
    ),
}


def freeze(panel: Path) -> int:
    if PROTO.exists():
        sys.exit("error: protocol.json exists")
    if sha256_file(panel) != PANEL_SHA256:
        sys.exit("error: wrong panel")
    proto = {
        "study_id": "ALERT_ATTRIBUTION_v1",
        "frozen_at": utc_stamp(),
        "asked_by": ASKED_BY,
        "status": STATUS,
        "inputs": {
            "alerts": (
                "CRYPTO_REPLAY_v1 rankings/shortlists_2023.csv.gz, population early, 1,825 per arm, arms "
                "summary, sequence, shuffled (control)"
            ),
            "account_labels": (
                "CRYPTO_REPLAY_v1 run/trades_BASE_<arm>.csv.gz: decision ORDER = admitted, SKIP_* = skipped "
                "with the reason"
            ),
            "panel_sha256": PANEL_SHA256,
            "volatility": (
                "vol20 = 20-day std of daily log close returns through the signal day (the model's own vol20 "
                "definition), from bars before the decision only"
            ),
        },
        "isolated_trade": {
            "engine": (
                "idxsig.crypto_replay.run with a one-alert shortlist and CRYPTO_REPLAY_v1's BASE Policy, equity "
                "10,000 at the decision; the same code path as the account"
            ),
            "notional_usd": NOTIONAL,
            "policy": POLICY.record(),
        },
        "analyses": ANALYSES,
        "verdict_rules": VERDICT_RULES,
        "honesty": [
            (
                "overlapping alerts: the same coin alerted on consecutive days is evaluated once per alert, so "
                "runs are over-weighted; analysis C also collapses them"
            ),
            "isolated trades ignore cash and risk limits by design; their sum is not a portfolio result",
            "daily bars, modelled costs, one already-studied year",
        ],
        "pins": {p: sha256_file(ROOT / p) for p in PINS},
    }
    PROTO.write_text(json.dumps(proto, indent=1) + "\n")
    print(PROTO.read_text())
    return 0


# ----------------------------------------------------------------------------------------- isolated trades
def isolated(bars, ticker: str, signal_day: date) -> dict:
    sl = pd.DataFrame([{"date": signal_day.isoformat(), "ticker": ticker, "rank": 1}])
    last = min(signal_day + timedelta(days=15), LAST)
    acct = cr.run(sl, bars, signal_day, last, POLICY)
    if last < LAST and any(e["type"] == "UNRESOLVED" for e in acct.events):
        acct = cr.run(sl, bars, signal_day, LAST, POLICY)
    ev = {e["type"]: e for e in acct.events}
    out = {
        "iso_status": None,
        "iso_exit": None,
        "iso_bar": None,
        "iso_gross": np.nan,
        "iso_net": np.nan,
        "iso_pnl": np.nan,
        "iso_cost": np.nan,
        "iso_ambiguous": False,
        "iso_entry_day": None,
    }
    if ev["DECISION"]["decision"] != "ORDER":
        out["iso_status"] = ev["DECISION"]["decision"]
        return out
    if "UNFILLED" in ev:
        out["iso_status"] = "UNFILLED_AFTER_DATA"
        return out
    en = ev["ENTRY"]
    out["iso_entry_day"] = en["day"]
    if en["status"] != "FILLED":
        out["iso_status"] = en["status"]
        return out
    if "EXIT" in ev:
        ex = ev["EXIT"]
        gross = ex["raw_price"] / en["raw_open"] - 1
        out.update(
            iso_status="CLOSED",
            iso_exit=ex["reason"],
            iso_bar=ex["bar_index"],
            iso_gross=gross,
            iso_net=ex["net_return"],
            iso_pnl=ex["pnl"],
            iso_cost=gross - ex["net_return"],
            iso_ambiguous=bool(ex.get("ambiguous", False)),
        )
    else:
        u = ev["UNRESOLVED"]
        out.update(iso_status="UNRESOLVED", iso_net=u["unrealized"] / NOTIONAL)
    return out


def vol20_table(panel: pd.DataFrame) -> pd.DataFrame:
    """The model's vol20 on a calendar index, for every (ticker, day) in 2023, from bars on or before that day."""
    cal = pd.date_range(pd.Timestamp("2022-10-01"), pd.Timestamp(LAST), freq="D")
    rows = []
    for ticker, g in panel.groupby("ticker", sort=True):
        c = g.set_index(pd.to_datetime(g["date"]))["close"].reindex(cal)
        prev = c.shift(1)
        lr = np.log(c.where(c > 0) / prev.where(prev > 0))
        v = lr.rolling(20, min_periods=20).std(ddof=1)
        v = v[v.index >= pd.Timestamp(FIRST)]
        rows.append(
            pd.DataFrame(
                {"ticker": ticker, "date": v.index.strftime("%Y-%m-%d"), "vol20": v.to_numpy()}
            )
        )
    return pd.concat(rows, ignore_index=True)


def run_label(frame: pd.DataFrame) -> pd.Series:
    """True on the first alert of each consecutive-day run of one coin (within an arm)."""
    f = frame.sort_values(["ticker", "date"])
    prev = f.groupby("ticker")["date"].shift(1)
    gap = (pd.to_datetime(f["date"]) - pd.to_datetime(prev)).dt.days
    first = gap.isna() | (gap > 1)
    return first.reindex(frame.index)


def boot_diff(a: pd.DataFrame, b: pd.DataFrame) -> dict:
    """mean(a.iso_net) - mean(b.iso_net), resampling signal days (both groups share the day draw)."""
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
        "diff": float(a["iso_net"].mean() - b["iso_net"].mean()),
        "lower95": float(lo),
        "upper95": float(hi),
        **BOOT,
    }


def stats(x: pd.DataFrame) -> dict:
    closed = x[x.iso_status == "CLOSED"]
    n = len(closed)
    return {
        "alerts": len(x),
        "closed": int(n),
        "mean_net": float(closed.iso_net.mean()) if n else None,
        "median_net": float(closed.iso_net.median()) if n else None,
        "win_rate": float((closed.iso_net > 0).mean()) if n else None,
        "mean_gross": float(closed.iso_gross.mean()) if n else None,
        "mean_cost": float(closed.iso_cost.mean()) if n else None,
        "model_hit_rate": float((x.label_known.astype(bool) & (x.up_first == 1)).mean()),
    }


def entry_day_stop_rate(closed: pd.DataFrame):
    return (
        float(((closed.iso_exit == "STOP") & (closed.iso_bar == 1)).mean()) if len(closed) else None
    )


def analyse(alerts: pd.DataFrame, arm: str) -> dict:
    a = alerts[alerts.method == arm].copy()
    closed = a[a.iso_status == "CLOSED"]
    hits = a.label_known.astype(bool) & (a.up_first == 1)
    out = {
        "A": {
            **stats(a),
            "statuses": a.iso_status.value_counts().to_dict(),
            "exit_reasons": closed.iso_exit.value_counts().to_dict(),
            "entry_day_stops": int(((closed.iso_exit == "STOP") & (closed.iso_bar == 1)).sum()),
            "ambiguous_bars": int(closed.iso_ambiguous.sum()),
            "mean_pnl_usd_at_account_size": float(closed.iso_pnl.mean()),
            "cost_usd_per_trade": float((closed.iso_cost * NOTIONAL).mean()),
        }
    }
    # B: score -> outcome
    a["quintile"] = pd.qcut(a.rank_score.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(
        int
    )
    by_rank = {int(r): stats(g) for r, g in a.groupby("rank")}
    by_q = {int(q): stats(g) for q, g in a.groupby("quintile")}
    rho = float(closed[["rank_score", "iso_net"]].corr(method="spearman").iloc[0, 1])
    top, bottom = by_q[5]["mean_net"], by_q[1]["mean_net"]
    out["B"] = {
        "by_rank": by_rank,
        "by_score_quintile": by_q,
        "spearman_score_vs_net": rho,
        "top_minus_bottom_quintile_mean_net": None
        if top is None or bottom is None
        else top - bottom,
    }
    # C: admitted vs skipped
    adm, skp = a[a.account == "ORDER"], a[a.account != "ORDER"]
    first = a[a.first_of_run]
    fa, fs = first[first.account == "ORDER"], first[first.account != "ORDER"]
    out["C"] = {
        "admitted": stats(adm),
        "skipped": stats(skp),
        "by_skip_reason": {r: stats(g) for r, g in skp.groupby("account")},
        "skipped_minus_admitted": boot_diff(
            skp[skp.iso_status == "CLOSED"], adm[adm.iso_status == "CLOSED"]
        ),
        "hits_admitted": int((hits & (a.account == "ORDER")).sum()),
        "hits_total": int(hits.sum()),
        "first_of_run": {
            "alerts": len(first),
            "admitted": stats(fa),
            "skipped": stats(fs),
            "skipped_minus_admitted": boot_diff(
                fs[fs.iso_status == "CLOSED"], fa[fa.iso_status == "CLOSED"]
            ),
        },
    }
    # D: model label x trade outcome
    label = np.where(
        ~a.label_known.astype(bool), "censored", np.where(a.up_first == 1, "hit", "non-hit")
    )
    is_time = a.iso_exit.str.startswith("TIME", na=False)
    outcome = np.select(
        [
            a.iso_exit.isin(["TARGET", "TARGET_GAP"]),
            a.iso_exit.isin(["STOP", "STOP_GAP"]),
            is_time & (a.iso_net > 0),
            is_time & (a.iso_net <= 0),
        ],
        ["TARGET", "STOP", "TIME_WIN", "TIME_LOSS"],
        default="OTHER",
    )
    tab = pd.crosstab(
        pd.Series(label, name="model_label"), pd.Series(outcome, name="trade_outcome")
    )
    h = tab.loc["hit"] if "hit" in tab.index else pd.Series(dtype=int)
    n_h = int(h.sum()) if len(h) else 0
    n_target = int(tab["TARGET"].sum()) if "TARGET" in tab else 0
    out["D"] = {
        "crosstab": {str(i): {str(c): int(v) for c, v in row.items()} for i, row in tab.iterrows()},
        "p_target_given_hit": float(h.get("TARGET", 0) / n_h) if n_h else None,
        "p_stop_given_hit": float(h.get("STOP", 0) / n_h) if n_h else None,
        "p_hit_given_target": float(h.get("TARGET", 0) / n_target) if n_target and n_h else None,
        "entry_day_stop_rate": entry_day_stop_rate(closed),
        "mean_net_hits": float(a.loc[hits & (a.iso_status == "CLOSED"), "iso_net"].mean())
        if n_h
        else None,
        "mean_net_non_hits": float(
            a.loc[(label == "non-hit") & (a.iso_status == "CLOSED"), "iso_net"].mean()
        ),
    }
    # E: volatility
    a["vol_tercile"] = pd.qcut(a.vol20.rank(method="first"), 3, labels=["low", "mid", "high"])
    by_v = {}
    for t, g in a.groupby("vol_tercile", observed=True):
        gc = g[g.iso_status == "CLOSED"]
        by_v[str(t)] = {
            **stats(g),
            "vol20_median": float(g.vol20.median()),
            "entry_day_stop_rate": entry_day_stop_rate(gc),
            "stop_rate": float(gc.iso_exit.isin(["STOP", "STOP_GAP"]).mean()) if len(gc) else None,
        }
    out["E"] = {
        "by_vol20_tercile": by_v,
        "share_barrier_above_10pct": float((a.barrier > 0.10 + 1e-12).mean()),
        "median_barrier": float(a.barrier.median()),
        "median_stop_in_daily_vols": float((POLICY.stop / a.vol20).median()),
    }
    return out


def verdicts(res: dict) -> list[str]:
    b = {arm: res["arms"][arm]["B"] for arm in ("summary", "sequence")}
    ok = [
        arm
        for arm in b
        if b[arm]["spearman_score_vs_net"] > 0
        and (b[arm]["top_minus_bottom_quintile_mean_net"] or 0) > 0
    ]
    q1 = "YES" if len(ok) == 2 else "NO" if not ok else "MIXED"
    c = {arm: res["arms"][arm]["C"]["skipped_minus_admitted"] for arm in ("summary", "sequence")}
    crowded = [arm for arm in c if c[arm]["lower95"] > 0]
    d = {arm: res["arms"][arm]["D"]["p_target_given_hit"] for arm in ("summary", "sequence")}
    q1_line = (
        f"Q1 score -> trade outcome: {q1}. Spearman rho summary "
        f"{b['summary']['spearman_score_vs_net']:+.3f}, sequence "
        f"{b['sequence']['spearman_score_vs_net']:+.3f}; top-minus-bottom quintile mean net return summary "
        f"{b['summary']['top_minus_bottom_quintile_mean_net'] * 100:+.2f} pts, sequence "
        f"{b['sequence']['top_minus_bottom_quintile_mean_net'] * 100:+.2f} pts."
    )
    q2_head = f"CROWDED OUT in {', '.join(crowded)}." if crowded else "NOT CROWDED OUT."
    q2_body = "; ".join(
        f"{arm}: skipped minus admitted {c[arm]['diff'] * 100:+.2f} pts "
        f"(95% {c[arm]['lower95'] * 100:+.2f} to {c[arm]['upper95'] * 100:+.2f})"
        for arm in c
    )
    q3_body = "; ".join(
        f"{arm}: P(10% target before 5% stop | model hit) = {d[arm]:.0%}" for arm in d
    )
    q3_tail = (
        "The trade matches the forecast."
        if all(v is not None and v >= 0.5 for v in d.values())
        else "The predicted event does not translate into this trade."
    )
    return [
        q1_line,
        f"Q2 crowding out: {q2_head} {q2_body}.",
        f"Q3 forecast -> trade: {q3_body}. {q3_tail}",
    ]


def pct(x, d=2):
    return "-" if x is None else f"{x * 100:+.{d}f}%"


def rate(x):
    return "-" if x is None else f"{x:.1%}"


def render(res: dict) -> str:
    p = res["policy"]
    L = [
        "# ALERT_ATTRIBUTION_v1: every 2023 alert as one isolated trade",
        "",
        f"Ran {res['ran_at']} at commit `{res['commit']}`. {res['status']}",
        "",
        (
            "Each of the 1,825 early-population top-five alerts per arm was traded on its own with "
            f"CRYPTO_REPLAY_v1's frozen BASE rules (entry next open, {p['fee']:.1%} fee + {p['slip']:.1%} "
            f"slippage per side, {p['stop']:.0%} stop, {p['target']:.0%} target, bar-{p['hold_bars']} close "
            "exit), no account limits, and labelled by what the BASE account did with it. Net returns are per "
            "trade; they do not add up to a portfolio."
        ),
        "",
        "## Verdicts (fixed rules, from the numbers)",
        "",
        *[f"- {v}" for v in res["verdicts"]],
        "",
        "## Ace's figures, reproduced from the account ledgers",
        "",
        (
            "| Arm | Model hits | Hits the account entered | Entry-day stops (account) | Closed P&L before "
            "costs | After costs |"
        ),
        "|---|---:|---:|---:|---:|---:|",
    ]
    for arm, f in res["F"].items():
        L.append(
            f"| {arm} | {f['hits']} | {f['hits_admitted']} | {f['entry_day_stops']} | {f['gross']:,.2f} | "
            f"{f['net']:,.2f} |"
        )
    for arm in ARMS:
        r = res["arms"][arm]
        A, B, C, D, E = r["A"], r["B"], r["C"], r["D"], r["E"]
        L += [
            "",
            f"## {arm}",
            "",
            (
                f"**A. All {A['alerts']} alerts in isolation:** {A['closed']} closed, statuses {A['statuses']}; "
                f"exits {A['exit_reasons']}; entry-day stops {A['entry_day_stops']}; ambiguous bars "
                f"{A['ambiguous_bars']}. Mean net return {pct(A['mean_net'])} (median {pct(A['median_net'])}), "
                f"win rate {rate(A['win_rate'])}; mean gross {pct(A['mean_gross'])} minus cost "
                f"{A['mean_cost'] * 100:.2f}% per trade ({A['cost_usd_per_trade']:.2f} USDT at the account's "
                "size)."
            ),
            "",
            "**B. Score versus outcome**",
            "",
            "| Rank | Alerts | Mean net | Win rate | Model hit rate |",
            "|---|---:|---:|---:|---:|",
        ]
        for k, s in B["by_rank"].items():
            L.append(
                f"| {k} | {s['alerts']} | {pct(s['mean_net'])} | {rate(s['win_rate'])} | "
                f"{rate(s['model_hit_rate'])} |"
            )
        L += [
            "",
            "| Score quintile (5 = highest) | Alerts | Mean net | Win rate | Model hit rate |",
            "|---|---:|---:|---:|---:|",
        ]
        for k, s in B["by_score_quintile"].items():
            L.append(
                f"| {k} | {s['alerts']} | {pct(s['mean_net'])} | {rate(s['win_rate'])} | "
                f"{rate(s['model_hit_rate'])} |"
            )
        L += [
            "",
            (
                f"Spearman rho(score, net return) {B['spearman_score_vs_net']:+.3f}; top minus bottom quintile "
                f"{pct(B['top_minus_bottom_quintile_mean_net'])}."
            ),
            "",
            "**C. Admitted versus skipped**",
            "",
            "| Group | Alerts | Closed | Mean net | Median net | Win rate | Model hit rate |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        rows = [("admitted", C["admitted"]), ("skipped (all)", C["skipped"])] + [
            (f"skipped: {k}", v) for k, v in C["by_skip_reason"].items()
        ]
        for name, s in rows:
            L.append(
                f"| {name} | {s['alerts']} | {s['closed']} | {pct(s['mean_net'])} | {pct(s['median_net'])} | "
                f"{rate(s['win_rate'])} | {rate(s['model_hit_rate'])} |"
            )
        sd, fr = C["skipped_minus_admitted"], C["first_of_run"]
        fd = fr["skipped_minus_admitted"]
        L += [
            "",
            (
                f"Skipped minus admitted: {pct(sd['diff'])} (95% {pct(sd['lower95'])} to {pct(sd['upper95'])}). "
                f"Model hits admitted: {C['hits_admitted']} of {C['hits_total']}. First alert of each run only "
                f"({fr['alerts']} runs): admitted mean net {pct(fr['admitted']['mean_net'])} "
                f"({fr['admitted']['alerts']}), skipped {pct(fr['skipped']['mean_net'])} "
                f"({fr['skipped']['alerts']}); difference {pct(fd['diff'])} (95% {pct(fd['lower95'])} to "
                f"{pct(fd['upper95'])})."
            ),
            "",
            "**D. The model's event versus our trade**",
            "",
        ]
        cols = list(next(iter(D["crosstab"].values())).keys())
        L += ["| Model label | " + " | ".join(cols) + " |", "|---|" + "---:|" * len(cols)]
        for lab, row in D["crosstab"].items():
            L.append(f"| {lab} | " + " | ".join(str(v) for v in row.values()) + " |")
        L += [
            "",
            (
                f"P(target before stop | model hit) {rate(D['p_target_given_hit'])}; P(stop | hit) "
                f"{rate(D['p_stop_given_hit'])}; P(model hit | target) {rate(D['p_hit_given_target'])}; "
                f"entry-day stop rate {rate(D['entry_day_stop_rate'])}; mean net on hits "
                f"{pct(D['mean_net_hits'])}, on non-hits {pct(D['mean_net_non_hits'])}."
            ),
            "",
            "**E. Volatility**",
            "",
            (
                "| vol20 tercile | Median daily vol | Alerts | Mean net | Stop rate | Entry-day stop rate | "
                "Model hit rate |"
            ),
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for t, s in E["by_vol20_tercile"].items():
            L.append(
                f"| {t} | {s['vol20_median']:.1%} | {s['alerts']} | {pct(s['mean_net'])} | "
                f"{rate(s['stop_rate'])} | {rate(s['entry_day_stop_rate'])} | {rate(s['model_hit_rate'])} |"
            )
        L.append(
            f"\nThe model's barrier exceeds our 10% target in {E['share_barrier_above_10pct']:.0%} of alerts "
            f"(median barrier {E['median_barrier']:.0%}); the 5% stop is a median "
            f"{E['median_stop_in_daily_vols']:.2f} daily standard deviations away."
        )
    L += [
        "",
        "## Limits",
        "",
        (
            "- The same coin alerted on consecutive days counts once per alert (runs over-weighted; section C "
            "also collapses runs)."
        ),
        "- Isolated trades ignore cash and risk limits by design.",
        "- Daily bars, modelled costs, one already-studied year; descriptive, no statistical certainty.",
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
    raw = pd.read_csv(panel)
    raw = raw[raw["date"] <= LAST.isoformat()]
    bars = cr.bars_from_panel(raw[raw["date"] >= FIRST.isoformat()], FIRST, LAST)
    vols = vol20_table(raw[raw["date"] >= "2022-10-01"])
    sl = pd.read_csv(REPLAY / "rankings/shortlists_2023.csv.gz")
    sl = sl[sl.population == "early"].copy()
    frames = []
    for arm in ARMS:
        a = sl[sl.method == arm].copy()
        ledger = pd.read_csv(REPLAY / f"run/trades_BASE_{arm}.csv.gz")[
            ["signal_day", "ticker", "decision"]
        ]
        ledger = ledger.rename(columns={"signal_day": "date", "decision": "account"})
        a = a.merge(ledger, on=["date", "ticker"], how="left")
        if a.account.isna().any():
            sys.exit(f"error: {arm}: an alert has no account decision")
        a = a.merge(vols, on=["ticker", "date"], how="left")
        a["barrier"] = np.expm1(np.maximum(np.log1p(0.10), 3.0 * a.vol20 * np.sqrt(5)))
        a["first_of_run"] = run_label(a)
        iso = [isolated(bars, t, date.fromisoformat(d)) for t, d in zip(a.ticker, a.date)]
        a = pd.concat([a.reset_index(drop=True), pd.DataFrame(iso)], axis=1)
        frames.append(a)
        print(f"{arm}: {len(a)} alerts evaluated", flush=True)
    alerts = pd.concat(frames, ignore_index=True)
    res = {
        "study": "ALERT_ATTRIBUTION_v1",
        "ran_at": utc_stamp(),
        "status": proto["status"],
        "policy": POLICY.record(),
        "notional_usd": NOTIONAL,
        "arms": {arm: analyse(alerts, arm) for arm in ARMS},
        "F": {},
    }
    for arm in ARMS:
        t = pd.read_csv(REPLAY / f"run/trades_BASE_{arm}.csv.gz")
        labels = sl[sl.method == arm][["date", "ticker", "label_known", "up_first"]]
        m = t.merge(labels, left_on=["signal_day", "ticker"], right_on=["date", "ticker"])
        hits = m[m.label_known.astype(bool) & (m.up_first == 1)]
        closed = m[m.exit_reason.notna()]
        res["F"][arm] = {
            "hits": len(hits),
            "hits_admitted": int((hits.decision == "ORDER").sum()),
            "entry_day_stops": int(
                ((closed.exit_reason == "STOP") & (closed.bar_index == 1)).sum()
            ),
            "gross": float((closed.units * (closed.exit_raw - closed.raw_open)).sum()),
            "net": float(closed.pnl.sum()),
        }
    res["verdicts"] = verdicts(res)
    res["commit"] = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    RESULTS.mkdir()
    alerts.to_csv(RESULTS / "alerts.csv.gz", index=False)
    (RESULTS / "RESULT.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    (HERE / "REPORT.md").write_text(render(res), encoding="utf-8")
    print("\n".join(res["verdicts"]))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True, type=Path)
    ap.add_argument("--freeze", action="store_true")
    args = ap.parse_args()
    return freeze(args.panel) if args.freeze else run(args.panel)


if __name__ == "__main__":
    sys.exit(main())
