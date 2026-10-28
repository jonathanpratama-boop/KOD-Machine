"""US_BREAKOUT_v1 runner. Implements PROTOCOL.md / protocol.json exactly; changes no parameter.

    python3 research/US_BREAKOUT_v1/run_experiment.py validation       # the result, run once
    python3 research/US_BREAKOUT_v1/run_experiment.py pipeline_check   # code check only, informs nothing

Refuses to run from a dirty tree (tracked files) and writes into a new directory next to this file
(exclusive create: it cannot overwrite a recorded run)."""

import gzip
import hashlib
import io
import json
import multiprocessing as mp
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import breakout as B  # noqa: E402
from idxsig import contract, global_panel  # noqa: E402
from idxsig.backtest import _dense  # noqa: E402
from idxsig.execution import Market  # noqa: E402
from idxsig.provenance import sha256_file  # noqa: E402

HERE = Path(__file__).parent
PROTOCOL = json.loads((HERE / "protocol.json").read_text())
PANEL = ROOT / PROTOCOL["panel_manifest"]
SEED = PROTOCOL["baseline"]["seed"]
N_CONTROLS = PROTOCOL["baseline"]["controls_per_signal"]
WINDOWS = {"validation": PROTOCOL["windows"]["validation"], "pipeline_check": PROTOCOL["windows"]["pipeline_check_only"]}
SPECS = {"primary": contract.SPEC, "S2": contract.ContractSpec(stop_slippage=PROTOCOL["sensitivity"]["S2"]["stop_slippage"])}
assert SPECS["primary"].sha256() == PROTOCOL["execution"]["spec_sha256"]
assert SPECS["S2"].sha256() == PROTOCOL["sensitivity"]["S2"]["spec_sha256"]

M = None  # the market, inherited by forked workers


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def code_state():
    dirty = [ln for ln in git("status", "--porcelain", "--untracked-files=no").splitlines()]
    return {"commit": git("rev-parse", "HEAD"), "dirty": bool(dirty), "dirty_files": dirty}


def work(task):
    kind, n, s, inv, label = task
    r = B.run_trade(M, n, s, inv, SPECS[label])
    out = {"outcome": r["outcome"]}
    for k in ("exit_reason", "net_return", "net_pnl_usd", "shares_filled", "entry_price", "reason"):
        if k in r:
            out[k] = r[k]
    if "plan" in r and r["plan"]:
        out["plan_outcome"] = r["plan"].get("outcome")
    return out


def build(window: str):
    """Signals, controls and tasks from the panel. Everything from bars through each signal session."""
    global M
    frame, meta = global_panel.load(PANEL)
    full = Market.from_panel(frame, price_limits=False)
    M = full.with_units(_dense(full, frame, "unit_factor", 1.0))
    level, raw, history = B.levels_and_signals(M)
    cool = B.cooldown_mask(raw)
    adv = B.adv_usd(M)
    uf = M.unit_factor
    close_t = np.where(np.isfinite(M.close), M.close * uf, np.nan)
    cell = B.cells(np.nan_to_num(close_t), np.nan_to_num(adv))
    traded = M.present & (np.nan_to_num(M.volume) > 0)
    d0, d1 = (np.datetime64(x) for x in WINDOWS[window])
    in_win = (M.dates >= d0) & (M.dates <= d1)
    sig = raw & ~cool & (cell >= 0) & in_win[None, :]
    pool_ok = (cell >= 0) & history & traded & ~raw
    rng = np.random.default_rng(SEED)
    quarantined = set(meta["unit_quarantine"]["tickers"])
    sigs, ctrls, unmatched = [], [], 0
    ns, ss = np.nonzero(sig)
    order = np.lexsort((ns, ss))
    for n, s in zip(ns[order], ss[order]):
        sid = len(sigs)
        ratio = float(level[n, s] / M.close[n, s])
        inv = float(level[n, s] * uf[n, s])
        sigs.append({"sid": sid, "n": int(n), "s": int(s), "ticker": str(M.tickers[n]), "session": str(M.dates[s]),
                     "cell": int(cell[n, s]), "adv": float(adv[n, s]), "close": float(close_t[n, s]), "inv": inv,
                     "ratio": ratio, "quarantined": str(M.tickers[n]) in quarantined})
        cand = np.flatnonzero(pool_ok[:, s] & (cell[:, s] == cell[n, s]))
        if len(cand) == 0:
            unmatched += 1
            continue
        pick = rng.choice(cand, size=min(N_CONTROLS, len(cand)), replace=False)
        for c in pick:
            ctrls.append({"sid": sid, "n": int(c), "s": int(s), "ticker": str(M.tickers[c]), "session": str(M.dates[s]),
                          "cell": int(cell[c, s]), "adv": float(adv[c, s]), "close": float(close_t[c, s]),
                          "inv": float(close_t[c, s] * ratio), "quarantined": str(M.tickers[c]) in quarantined})
    counts = {"raw_signals_in_window": int((raw & in_win[None, :]).sum()),
              "cooldown_skipped": int((cool & in_win[None, :]).sum()),
              "ineligible_price_or_liquidity": int((raw & ~cool & (cell < 0) & in_win[None, :]).sum()),
              "eligible_signals": len(sigs), "unmatched_signals": unmatched, "controls_drawn": len(ctrls)}
    return M, meta, sigs, ctrls, counts


def run_all(sigs, ctrls, label, procs=4):
    tasks = [("signal", t["n"], t["s"], t["inv"], label) for t in sigs] + \
            [("control", t["n"], t["s"], t["inv"], label) for t in ctrls]
    t0 = time.time()
    with mp.get_context("fork").Pool(procs) as pool:
        res = pool.map(work, tasks, chunksize=200)
    print(f"  {label}: {len(tasks):,} trades in {time.time() - t0:,.0f}s", flush=True)
    a, b = res[: len(sigs)], res[len(sigs):]
    return pd.DataFrame(a), pd.DataFrame(b)


def frame(rows, res, arm):
    df = pd.DataFrame(rows)
    df = pd.concat([df, res.add_prefix("r_")], axis=1)
    df["arm"] = arm
    df["filled"] = df["r_net_return"].notna()
    return df


def compare(sig_df, ctl_df, seed=SEED, resamples=2000):
    """D, bootstrap over signal sessions. Cells without a filled control drop their signal trades."""
    s = sig_df[sig_df.filled]
    c = ctl_df[ctl_df.filled]
    ok_cells = sorted(set(s.cell) & set(c.cell))
    s, c = s[s.cell.isin(ok_cells)], c[c.cell.isin(ok_cells)]
    out = {"filled_signal_trades": int(len(s)), "filled_control_trades": int(len(c)),
           "dropped_signal_trades_no_control_in_cell": int(sig_df.filled.sum() - len(s))}
    if len(s) == 0 or len(c) == 0:
        return {**out, "D": None}
    sessions = sorted(set(s.session) | set(c.session))
    sidx = {x: i for i, x in enumerate(sessions)}
    cidx = {x: i for i, x in enumerate(ok_cells)}
    S, C = len(sessions), len(ok_cells)
    ss, sn, cs, cn = (np.zeros((S, C)) for _ in range(4))
    for r in s.itertuples():
        ss[sidx[r.session], cidx[r.cell]] += r.r_net_return
        sn[sidx[r.session], cidx[r.cell]] += 1
    for r in c.itertuples():
        cs[sidx[r.session], cidx[r.cell]] += r.r_net_return
        cn[sidx[r.session], cidx[r.cell]] += 1

    def stat(w):
        sum_s, n_s, sum_c, n_c = w @ ss, w @ sn, w @ cs, w @ cn
        keep = (n_c > 0) & (n_s > 0)
        if not keep.any() or n_s[keep].sum() == 0:
            return np.nan, np.nan, np.nan
        sig_mean = sum_s[keep].sum() / n_s[keep].sum()
        ctl_mean = ((n_s[keep] / n_s[keep].sum()) * (sum_c[keep] / n_c[keep])).sum()
        return sig_mean, ctl_mean, sig_mean - ctl_mean

    point = stat(np.ones(S))
    rng = np.random.default_rng(seed)
    boots = np.array([stat(np.bincount(rng.integers(0, S, S), minlength=S).astype(float))[2] for _ in range(resamples)])
    boots = boots[np.isfinite(boots)]
    sig_boots = np.array([stat(w)[0] for w in (np.bincount(rng.integers(0, S, S), minlength=S).astype(float)
                                              for _ in range(resamples))])
    return {**out, "signal_mean_net": point[0], "control_weighted_mean_net": point[1], "D": point[2],
            "signal_median_net": float(s.r_net_return.median()), "control_median_net": float(c.r_net_return.median()),
            "signal_hit_rate": float((s.r_net_return > 0).mean()), "control_hit_rate": float((c.r_net_return > 0).mean()),
            "D_ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
            "signal_mean_ci95": [float(np.nanpercentile(sig_boots, 2.5)), float(np.nanpercentile(sig_boots, 97.5))],
            "bootstrap_p_one_sided_D_le_0": float((1 + (boots <= 0).sum()) / (1 + len(boots))),
            "sessions": S, "cells": C}


def outcome_table(df):
    return df.r_outcome.value_counts().to_dict()


def account_run(sigs, window):
    sig_by = {}
    for t in sigs:
        sig_by.setdefault(t["s"], []).append((t["n"], t["inv"]))
    lo = int(np.searchsorted(M.dates, np.datetime64(WINDOWS[window][0])))
    hi = int(np.searchsorted(M.dates, np.datetime64(WINDOWS[window][1]), side="right")) - 1
    acc = contract.replay(M, sig_by, lo, hi, permitted=tuple(WINDOWS[window]))
    st = acc.state
    ex = [c for c in st["closed"] if "exit_session" in c]
    return {"sessions": hi - lo + 1, "starting_cash_usd": st["contract"]["starting_cash_usd"],
            "end_cash_usd": st["cash_usd"], "open_positions": len(st["positions"]), "working_orders": len(st["orders"]),
            "equity_at_end_usd": acc.equity(contract._Data(M, hi)), "exited_trades": len(ex),
            "net_pnl_usd_exited": float(sum(c["net_pnl_usd"] for c in ex)),
            "outcomes": pd.Series([c["outcome"] for c in st["closed"]]).value_counts().to_dict(),
            "note": "descriptive: one shared $10,000 account, priority by liquidity; not part of the decision rule"}


def main(window: str) -> int:
    state = code_state()
    if state["dirty"]:
        print("error: commit first so the result names the code that produced it:", state["dirty_files"], file=sys.stderr)
        return 2
    out_dir = HERE / ("validation" if window == "validation" else "pipeline_check")
    out_dir.mkdir(exist_ok=False)
    print(f"{window}: building signals and controls ...", flush=True)
    m, meta, sigs, ctrls, counts = build(window)
    print(" ", counts, flush=True)
    results, tables = {}, {}
    for label in ("primary", "S2"):
        a, b = run_all(sigs, ctrls, label)
        sd, cd = frame(sigs, a, "signal"), frame(ctrls, b, "control")
        tables[label] = (sd, cd)
    sd, cd = tables["primary"]
    primary = compare(sd, cd)
    s1 = compare(sd[~sd.quarantined], cd[~cd.quarantined])
    s2 = compare(*tables["S2"])
    s3 = compare(sd[sd.adv >= 5e6], cd[cd.adv >= 5e6])
    halves = {}
    for name, lo, hi in (("H1", "01-01", "06-30"), ("H2", "07-01", "12-31")):
        y = WINDOWS[window][0][:4]
        sel = lambda d: d[(d.session >= f"{y}-{lo}") & (d.session <= f"{y}-{hi}")]  # noqa: E731
        halves[name] = compare(sel(sd), sel(cd))
    stat_keys = ("filled_signal_trades", "signal_mean_net", "control_weighted_mean_net", "D", "bootstrap_p_one_sided_D_le_0")
    rule = {
        "1_at_least_200_matched_filled_signal_trades": primary["filled_signal_trades"] >= 200,
        "2_mean_net_positive": bool(primary.get("signal_mean_net") is not None and primary["signal_mean_net"] > 0),
        "3_D_positive_and_p_below_0.05": bool(primary.get("D") is not None and primary["D"] > 0
                                              and primary["bootstrap_p_one_sided_D_le_0"] < 0.05),
        "4_D_positive_in_S1_and_S2": bool(s1.get("D") is not None and s1["D"] > 0 and s2.get("D") is not None and s2["D"] > 0)}
    verdict = "PASS (forward paper scoring only)" if all(rule.values()) else "NO EDGE ESTABLISHED"
    if window != "validation":
        verdict = "PIPELINE CHECK ONLY: not a result"
    summary = {"experiment": "US_BREAKOUT_v1", "window": window, "dates": WINDOWS[window], "code": state,
               "protocol_sha256": sha256_file(HERE / "protocol.json"), "panel_sha256": meta["sha256"],
               "panel_manifest_sha256": sha256_file(PANEL), "counts": counts,
               "signal_outcomes": outcome_table(sd), "control_outcomes": outcome_table(cd),
               "signal_exit_reasons": sd[sd.filled].r_exit_reason.value_counts().to_dict(),
               "control_exit_reasons": cd[cd.filled].r_exit_reason.value_counts().to_dict(),
               "primary": primary, "S1_verified_units_only": s1, "S2_stop_slippage_1pct": s2, "S3_adv_5m": s3,
               "by_half": halves, "decision_rule": rule, "verdict": verdict,
               "account_level_run": account_run(sigs, window)}
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        gz.write(pd.concat([sd, cd]).drop(columns=["n", "s"]).to_csv(index=False, float_format="%.10g").encode())
    (out_dir / "trades.csv.gz").write_bytes(buf.getvalue())
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=float) + "\n")
    print(json.dumps({k: summary[k] for k in ("counts", "signal_outcomes", "decision_rule", "verdict")}, indent=1, default=float))
    print(json.dumps({k: primary.get(k) for k in stat_keys}, indent=1, default=float))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in WINDOWS:
        sys.exit("usage: run_experiment.py validation|pipeline_check")
    sys.exit(main(sys.argv[1]))
