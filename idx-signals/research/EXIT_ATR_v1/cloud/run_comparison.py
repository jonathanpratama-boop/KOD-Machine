"""EXIT-ATR-v1 (cloud) step 3: the single recorded comparison (protocol.json, frozen before this runs).

Arm A = E2's original exit (5 sessions, sell at the close; E2 harness commit 21345b1).
Arm B = the ATR trailing stop (idxsig/exit_atr.py) over the same window; unstopped trades leave as in arm A.
Same shared entries, same eligibility, same costs per side in both arms.

Refuses a dirty tree, an existing output, or any input whose hash differs from the frozen protocol.
Usage (from idx-signals/ of branch claude/exit-atr-trail-v1):
  KOD_CODE_ROOT=<21345b1 worktree>/idx-signals python3 research/EXIT_ATR_v1/cloud/run_comparison.py
Writes research/EXIT_ATR_v1/cloud/results/{RESULT.json, RESULT.md, trades.csv.gz, controls.csv.gz}.
"""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[3]          # idx-signals/ of this branch
CLOUD = HERE / "research" / "EXIT_ATR_v1" / "cloud"
OUT = CLOUD / "results"
PROTO = json.loads((CLOUD / "protocol.json").read_text())


def _load(name, path):  # this branch's pure modules, loaded by path so E2's idxsig package can be imported too
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses with postponed annotations look their module up here
    spec.loader.exec_module(mod)
    return mod


X = _load("exit_atr_v1", HERE / "idxsig" / "exit_atr.py")
E6 = _load("e6_hourly", HERE / "idxsig" / "e6.py")
E2_ROOT = Path(os.environ["KOD_CODE_ROOT"]).resolve()
sys.path.insert(0, str(E2_ROOT))
from idxsig import backtest, global_panel  # noqa: E402  (E2 harness, commit 21345b1)

COSTS = PROTO["costs"]["per_side"]               # {"original": .002, "primary": .003, "stress": .004}
SEED, RESAMPLES = PROTO["statistics"]["seed"], PROTO["statistics"]["resamples"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git(*a, cwd=HERE):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True).stdout.strip()


# --------------------------------------------------------------------------------------------- inputs
def check_inputs():
    if git("status", "--porcelain", "--", "idxsig", "tests", "research/EXIT_ATR_v1"):
        sys.exit("error: commit idxsig/, tests/ and research/EXIT_ATR_v1 first")
    if OUT.exists():
        sys.exit(f"error: {OUT} exists; the comparison runs once")
    h = PROTO["hashes"]
    for rel, want in h["files"].items():
        got = sha(HERE / rel)
        if got != want:
            sys.exit(f"error: {rel} sha256 {got} differs from the frozen {want}")
    if git("rev-parse", "HEAD", cwd=E2_ROOT) != h["e2_harness_commit"]:
        sys.exit("error: KOD_CODE_ROOT is not at the frozen E2 harness commit")


def harness_baseline():
    """Re-run E2's harness exactly as make_entries.py does and return its per-trade exit price and net return
    at the ORIGINAL costs, for signals (raw order) and controls (ravel order)."""
    cfg = json.loads((CLOUD / "entries" / "entries_meta.json").read_text())["config"]
    rc = backtest.RunConfig(**cfg)
    manifest = HERE / PROTO["data"]["panel_manifest"]
    panel_df, meta = global_panel.load(manifest)
    rule = backtest.rule_registry.get(rc.rule_id)
    prof = backtest.PROFILES[rc.market]
    ec = backtest.ExecConfig(lot_size=prof.lot_size, entry_price=prof.entry, cost_tiers=prof.cost_tiers,
                             holding_days=rc.holding_days, entry_lag=rc.entry_lag, notional=rc.notional,
                             max_participation=rc.max_participation, fees=backtest.Fees(rc.fee_buy, rc.fee_sell),
                             data_end_exit=rc.data_end_exit, ca_mode=rc.ca_mode)
    full = backtest.Market.from_panel(panel_df, price_limits=prof.price_limits)
    lo, hi = full.bounds(rc.start, rc.end)
    m = full.slice(lo, hi)
    sig, _ = backtest.signals(rule, m, rc.lookahead_cuts)
    tick, sidx = np.nonzero(sig == 1)
    tr = backtest.execute(m, tick, sidx, ec)
    skipped = np.zeros(len(tick), dtype=bool)
    held = {}
    for i, (n, s) in enumerate(zip(tick, sidx)):
        if s + rc.entry_lag <= held.get(n, -1):
            skipped[i] = True
            continue
        if tr["exit_idx"][i] >= 0:
            held[n] = tr["exit_idx"][i]
        elif tr["status"][i] == backtest.STATUS.index("INCOMPLETE"):
            held[n] = np.iinfo(np.int64).max
    att = ~skipped
    feats = {k: v[:, lo:hi] for k, v in backtest.controls.features(full, rc.controls_version, prof.band_edges).items()}
    mt, _ = backtest.controls.matched_draws(np.isfinite(sig), feats, tick[att], sidx[att], rc.random_draws,
                                            np.random.default_rng(rc.seed + 1), rc.controls_version)
    ct = backtest.execute(m, mt.ravel(), np.broadcast_to(sidx[att], mt.shape).ravel(), ec)
    tk = np.asarray(m.tickers)
    return (pd.DataFrame({"ticker": tk[tick], "entry_price_h": tr["entry_price"], "exit_price_A": tr["exit_price"],
                          "net_A_harness": tr["net_return"]}),
            pd.DataFrame({"ticker": tk[mt.ravel()], "entry_price_h": ct["entry_price"], "exit_price_A": ct["exit_price"],
                          "net_A_harness": ct["net_return"]}))


# ---------------------------------------------------------------------------------------- simulation
def simulate(E, h):
    """Arm B for every eligible row of E (signals and controls); identical (ticker, signal date) windows are
    simulated once."""
    idx = {s: i for i, s in enumerate(h.symbols)}
    cache = {}
    cols = {k: [] for k in ("reason", "exit_price_B", "exit_bar", "held_bars", "initial_stop", "final_stop", "raises",
                            "reason_cons", "exit_price_B_cons", "highest")}
    for r in E.itertuples(index=False):
        key = (r.ticker, r.signal_date)
        if key not in cache:
            i, a, b = idx[r.symbol], int(r.h0), int(r.h1)
            sl = slice(a, b + 1)
            args = (h.open[i, sl], h.high[i, sl], h.low[i, sl], h.present[i, sl], float(r.entry_price), float(r.atr),
                    float(r.exit_price_A))
            p, c = X.trailing_exit(*args), X.trailing_exit(*args, conservative_gaps=True)
            cache[key] = (p["reason"], p["exit_price"], p["exit_bar"], p["held_bars"], p["initial_stop"],
                          p["final_stop"], p["raises"], c["reason"], c["exit_price"], p["highest"])
        for k, v in zip(cols, cache[key]):
            cols[k].append(v)
    for k, v in cols.items():
        E[k] = v
    return E


# ---------------------------------------------------------------------------------------- statistics
class Boot:
    """Calendar-week (ISO week of the entry date) bootstrap: one fixed set of resampled weeks for every metric."""

    def __init__(self, weeks):
        self.weeks = np.array(sorted(set(weeks)))
        rng = np.random.default_rng(SEED)
        self.pick = rng.integers(0, len(self.weeks), size=(RESAMPLES, len(self.weeks)))

    def __call__(self, values, weeks):
        v = np.asarray(values, dtype=float)
        w = np.searchsorted(self.weeks, np.asarray(weeks))
        S = np.bincount(w, v, minlength=len(self.weeks))
        C = np.bincount(w, minlength=len(self.weeks)).astype(float)
        with np.errstate(invalid="ignore", divide="ignore"):
            stat = S[self.pick].sum(1) / C[self.pick].sum(1)
        stat = stat[np.isfinite(stat)]
        return {"mean": float(v.mean()), "ci95": [float(np.percentile(stat, 2.5)), float(np.percentile(stat, 97.5))],
                "n": int(len(v)), "weeks": int(len(set(np.asarray(weeks)))), "resamples": int(len(stat))}


def wilson(k, n, z=1.959964):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    hw = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [float(c - hw), float(c + hw)]


def describe(net, hours):
    net = np.asarray(net, dtype=float)
    w, l = net[net > 0], net[net < 0]
    return {"n": int(len(net)), "mean": float(net.mean()), "median": float(np.median(net)),
            "win_rate": float((net > 0).mean()), "win_rate_wilson95": wilson(int((net > 0).sum()), len(net)),
            "avg_win": float(w.mean()) if len(w) else None, "avg_loss": float(l.mean()) if len(l) else None,
            "worst_1pct": float(np.percentile(net, 1)), "worst_5": [float(x) for x in np.sort(net)[:5]],
            "best": float(net.max()), "holding_hours_mean": float(np.mean(hours)),
            "holding_hours_median": float(np.median(hours))}


def exposure(h0, hours, net, notional):
    start, end = np.asarray(h0), np.asarray(h0) + np.asarray(hours)        # occupied hours [start, end)
    ev = np.concatenate([np.stack([start, np.ones(len(start))], 1), np.stack([end, -np.ones(len(end))], 1)])
    ev = ev[np.lexsort((ev[:, 1], ev[:, 0]))]
    conc = np.cumsum(ev[:, 1])
    order = np.argsort(end, kind="stable")
    pnl = np.cumsum(notional * np.asarray(net)[order])
    dd = pnl - np.maximum.accumulate(np.concatenate([[0.0], pnl]))[1:]
    span = end.max() - start.min()
    occ = np.zeros(int(span), dtype=np.int32)
    for s, e in zip(start - start.min(), end - start.min()):
        occ[s:e] += 1
    return {"max_concurrent_positions": int(conc.max()), "mean_concurrent_positions": float(occ.mean()),
            "share_of_hours_with_a_position": float((occ > 0).mean()),
            "max_capital_deployed_usdt": float(conc.max() * notional),
            "portfolio": {"model": f"each trade {notional:.0f} USDT, unlimited capital, no compounding, P&L booked at exit",
                          "total_pnl_usdt": float(pnl[-1]), "max_drawdown_usdt": float(dd.min()),
                          "max_drawdown_in_trade_notionals": float(dd.min() / notional)}}


# ------------------------------------------------------------------------------------------------ run
def main():
    check_inputs()
    started = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    E = pd.read_csv(CLOUD / "eligibility" / "eligibility.csv.gz", dtype={"ticker": str}, keep_default_na=False,
                    na_values=[""])
    hs, hc = harness_baseline()
    sig_raw = pd.read_csv(CLOUD / "entries" / "signals.csv", dtype={"ticker": str}, keep_default_na=False, na_values=[""])
    hs = pd.concat([sig_raw[["j", "ticker", "entry_price"]].rename(columns={"ticker": "t2"}), hs], axis=1)
    hs = hs[hs.j >= 0]
    if not ((hs.t2 == hs.ticker).all() and np.allclose(hs.entry_price.fillna(0), hs.entry_price_h.fillna(0), rtol=1e-9, atol=0)):
        sys.exit("error: harness re-run does not reproduce the saved signal entries")  # saved prices carry 10 digits
    ctl_raw = pd.read_csv(CLOUD / "entries" / "controls.csv.gz", dtype={"ticker": str}, keep_default_na=False,
                          na_values=[""])
    if not ((ctl_raw.ticker.to_numpy() == hc.ticker.to_numpy()).all()
            and np.allclose(ctl_raw.entry_price.fillna(0).to_numpy(), hc.entry_price_h.fillna(0).to_numpy(), rtol=1e-9, atol=0)):
        sys.exit("error: harness re-run does not reproduce the saved control entries")
    hc = pd.concat([ctl_raw[["j", "draw"]], hc], axis=1)
    keep = ["arm", "j", "draw", "entry_price_h", "exit_price_A", "net_A_harness"]
    base = pd.concat([hs.assign(arm="signal", draw=-1)[keep], hc.assign(arm="control")[keep]], ignore_index=True)
    E = E.merge(base, on=["arm", "j", "draw"], how="left", validate="one_to_one")
    E["entry_price"] = E.entry_price_h            # the harness's exact entry price (the CSV keeps 10 digits)

    S = E[E.scored_A]
    net_mine = X.net_return(S.entry_price, S.exit_price_A, COSTS["original"])
    repro = float(np.nanmax(np.abs(net_mine - S.net_A_harness)))
    if not repro < 1e-12:
        sys.exit(f"error: arm A at original costs does not reproduce E2's harness (max diff {repro})")

    El = E[E.eligible].copy()
    h, hmeta = E6.load_manifest(HERE / PROTO["data"]["hourly_manifest"],
                                last_hour=pd.Timestamp(PROTO["data"]["last_hour_read"], tz="UTC"))
    El = simulate(El, h)
    El["entry_dt"] = pd.to_datetime(El.entry_date)
    iso = pd.DatetimeIndex(El.entry_dt).isocalendar()
    El["week"] = (iso["year"].astype(int) * 100 + iso["week"].astype(int)).to_numpy()
    El["year"] = El.entry_dt.dt.year
    El["hold_A"] = El.h1 - El.h0 + 1
    El["data_end"] = (El.status == "EXIT_DATA_END") | (El.coverage == "TRUNCATED")
    for tag, c in COSTS.items():
        El[f"net_A_{tag}"] = X.net_return(El.entry_price, El.exit_price_A, c)
        El[f"net_B_{tag}"] = X.net_return(El.entry_price, El.exit_price_B, c)
    El["net_Bc_primary"] = X.net_return(El.entry_price, El.exit_price_B_cons, COSTS["primary"])
    stopped = El.reason != "NOT_STOPPED"
    El["net_A_dataend100"] = np.where(El.data_end, -1.0, El.net_A_primary)
    El["net_B_dataend100"] = np.where(El.data_end & ~stopped, -1.0, El.net_B_primary)

    sg = El[El.arm == "signal"].copy()
    ct = El[El.arm == "control"].copy()
    boot = Boot(sg.week)
    sg["paired"] = sg.net_B_primary - sg.net_A_primary
    cm = ct.groupby("j")[["net_A_primary", "net_B_primary", "net_B_stress", "net_A_stress"]].mean()
    sg = sg.join(cm, on="j", rsuffix="_ctrl")
    sg["excess_B"] = sg.net_B_primary - sg.net_B_primary_ctrl
    sg["excess_A"] = sg.net_A_primary - sg.net_A_primary_ctrl

    def arm_block(col_net, col_hours):
        return describe(sg[col_net], sg[col_hours])

    res = {"protocol_id": PROTO["protocol_id"], "label": PROTO["label"], "started": started,
           "code_commit": git("rev-parse", "HEAD"), "e2_harness_commit": git("rev-parse", "HEAD", cwd=E2_ROOT),
           "hourly_symbols_loaded": hmeta["symbols_loaded"],
           "baseline_reproduction": {"scored_trades_checked": int(len(S)), "max_abs_diff_vs_e2_harness": repro,
                                     "arm_A_all_scored_signals_original_costs": describe(
                                         X.net_return(S[S.arm == "signal"].entry_price, S[S.arm == "signal"].exit_price_A,
                                                      COSTS["original"]), np.ones((S.arm == "signal").sum())),
                                     "note": "holding hours not meaningful in this row (set to 1)"},
           "eligibility": json.loads((CLOUD / "eligibility" / "ELIGIBILITY.json").read_text()),
           "common_scored_trades": int(len(sg)), "distinct_coins": int(sg.ticker.nunique()),
           "arm_A": {t: describe(sg[f"net_A_{t}"], sg.hold_A) for t in COSTS},
           "arm_B": {t: describe(sg[f"net_B_{t}"], sg.held_bars) for t in COSTS},
           "arm_B_exit_reasons": sg.reason.value_counts().to_dict(),
           "arm_B_stop_raises": {"mean": float(sg.raises.mean()), "share_with_any_raise": float((sg.raises > 0).mean())},
           "initial_stop_distance": {q: float(np.percentile(1 - sg.initial_stop / sg.entry_price, p))
                                     for q, p in (("p10", 10), ("median", 50), ("p90", 90))},
           "paired_improvement_primary": {**boot(sg.paired, sg.week),
                                          "median": float(sg.paired.median()),
                                          "improved": int((sg.paired > 1e-15).sum()), "worse": int((sg.paired < -1e-15).sum()),
                                          "identical": int((sg.paired.abs() <= 1e-15).sum())},
           "abs_mean_net_B_primary": boot(sg.net_B_primary, sg.week),
           "abs_mean_net_A_primary": boot(sg.net_A_primary, sg.week),
           "matched_control_excess": {"B_trailing_exit": boot(sg.excess_B, sg.week), "A_original_exit": boot(sg.excess_A, sg.week),
                                      "controls_scored": int(len(ct)), "controls_per_signal_min": int(ct.groupby("j").size().min()),
                                      "control_arm_A_primary": describe(ct.net_A_primary, ct.hold_A),
                                      "control_arm_B_primary": describe(ct.net_B_primary, ct.held_bars),
                                      "control_arm_B_exit_reasons": ct.reason.value_counts().to_dict()},
           "by_year": {str(y): {"n": int(len(g)), "mean_net_A": float(g.net_A_primary.mean()),
                                "mean_net_B": float(g.net_B_primary.mean()), "paired_mean": float(g.paired.mean()),
                                "win_rate_B": float((g.net_B_primary > 0).mean())} for y, g in sg.groupby("year")},
           "sensitivities": {
               "stress_costs_0.4pct_per_side": {"mean_net_A": boot(sg.net_A_stress, sg.week), "mean_net_B": boot(sg.net_B_stress, sg.week),
                                                "paired": boot(sg.net_B_stress - sg.net_A_stress, sg.week)},
               "original_costs_0.2pct_per_side": {"mean_net_A": float(sg.net_A_original.mean()), "mean_net_B": float(sg.net_B_original.mean())},
               "conservative_gap_fills": {"mean_net_B": boot(sg.net_Bc_primary, sg.week),
                                          "paired": boot(sg.net_Bc_primary - sg.net_A_primary, sg.week),
                                          "trades_changed": int((sg.net_Bc_primary != sg.net_B_primary).sum())},
               "data_end_minus_100pct": {"trades_affected": int(sg.data_end.sum()),
                                         "mean_net_A": float(sg.net_A_dataend100.mean()), "mean_net_B": float(sg.net_B_dataend100.mean()),
                                         "paired": boot(sg.net_B_dataend100 - sg.net_A_dataend100, sg.week)},
               "unresolved_unfi_excluded": {"trades_dropped": int(sg.unresolved_unfi.sum()),
                                            "mean_net_B": float(sg[~sg.unresolved_unfi].net_B_primary.mean()),
                                            "paired": boot(sg[~sg.unresolved_unfi].paired, sg[~sg.unresolved_unfi].week)}},
           "exposure": {"arm_A": exposure(sg.h0, sg.hold_A, sg.net_A_primary, PROTO["sizing"]["notional_usdt"]),
                        "arm_B": exposure(sg.h0, sg.held_bars, sg.net_B_primary, PROTO["sizing"]["notional_usdt"])}}

    # acceptance (protocol.json "acceptance"; nothing here may be changed after the run)
    pi, ab = res["paired_improvement_primary"], res["abs_mean_net_B_primary"]
    crit = {"C1_at_least_200_common_scored_trades": res["common_scored_trades"] >= 200,
            "C2_mean_net_B_positive_each_discovery_year": all(res["by_year"].get(y, {}).get("mean_net_B", -1) > 0
                                                              for y in PROTO["acceptance"]["years"]),
            "C3_lower95_mean_net_B_above_zero": ab["ci95"][0] > 0,
            "C4_lower95_paired_improvement_above_zero": pi["ci95"][0] > 0,
            "C5_positive_excess_over_matched_controls_same_exit": res["matched_control_excess"]["B_trailing_exit"]["mean"] > 0,
            "C6_mean_net_B_positive_under_stress": res["sensitivities"]["stress_costs_0.4pct_per_side"]["mean_net_B"]["mean"] > 0}
    research_positive = all(crit.values())
    q1 = "IMPROVES" if pi["ci95"][0] > 0 else ("DOES_NOT_IMPROVE" if pi["mean"] <= 0 else "INCONCLUSIVE")
    q2 = ("PROFITABLE_IN_THIS_HISTORICAL_TEST" if research_positive else
          "UNPROFITABLE" if ab["mean"] <= 0 else "INCONCLUSIVE")
    res.update({"acceptance": crit, "research_positive": research_positive,
                "verdict": {"Q1_trailing_exit_vs_original_exit": q1, "Q2_resulting_strategy_profitability": q2,
                            "overall": "RESEARCH-POSITIVE" if research_positive else
                                       ("NEGATIVE" if q2 == "UNPROFITABLE" else "INCONCLUSIVE")},
                "finished": datetime.now(timezone.utc).replace(microsecond=0).isoformat()})

    OUT.mkdir(parents=True)
    keep = ["ticker", "signal_date", "entry_date", "exit_date_original", "status", "coverage", "entry_price", "atr",
            "initial_stop", "final_stop", "raises", "highest", "reason", "exit_bar", "held_bars", "exit_price_A",
            "exit_price_B", "reason_cons", "exit_price_B_cons", "hold_A", "data_end", "unresolved_unfi", "week", "year"]
    nets = [c for c in sg.columns if c.startswith("net_") or c in ("paired", "excess_A", "excess_B")]
    sg[["j"] + keep + nets].sort_values("j").to_csv(OUT / "trades.csv.gz", index=False, float_format="%.12g",
                                                   compression={"method": "gzip", "mtime": 0})
    ct[["j", "draw", "ticker", "signal_date", "entry_price", "atr", "reason", "exit_price_A", "exit_price_B",
        "net_A_primary", "net_B_primary", "net_A_stress", "net_B_stress"]].sort_values(["j", "draw"]).to_csv(
        OUT / "controls.csv.gz", index=False, float_format="%.12g", compression={"method": "gzip", "mtime": 0})
    (OUT / "RESULT.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: res[k] for k in ("common_scored_trades", "verdict", "acceptance", "paired_improvement_primary",
                                          "abs_mean_net_B_primary")}, indent=1, default=str))


if __name__ == "__main__":
    main()
