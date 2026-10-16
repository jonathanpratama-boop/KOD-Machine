"""E9 step 4: the single recorded discovery test (research/E9/PROTOCOL.md; protocol.json is frozen first).

1. The harness itself (idxsig.backtest.run, E9's configuration from entries/entries_meta.json) gives every signal
   trade and its net return; its trades must equal the shared entry list (entries/signals.csv).
2. backtest.run()'s own steps are repeated from its cached signals to obtain the trade indices, the matched
   controls and the 20-session secondary; they must reproduce the harness's nets, entries/controls.csv.gz and
   the harness's random_matched pooled mean.
3. Each attempted signal carries its frozen class (feasibility_a3/classes.csv.gz). Samples, statistics,
   sensitivities and verdicts are exactly those in protocol.json.

Usage (from idx-signals/): python3 research/E9/run_test.py
Writes research/E9/results/{RESULT.json, trades.csv.gz}. Refuses a dirty tree, a changed input or an existing output.
"""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import backtest, global_panel  # noqa: E402

E9 = ROOT / "research" / "E9"
OUT = E9 / "results"
PANEL = ROOT / "data" / "manifests" / "panel_us_repair-20261008T114805Z.json"
SCORED = ("EXITED", "EXIT_DATA_END")
GROUPS = ("DOCUMENTED", "UNDOCUMENTED", "DILUTION")


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git(*a) -> str:
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def tier_cost(price, tiers) -> np.ndarray:
    """The harness's extra per-side cost (execution._tier_costs) at an as-traded price."""
    b, c = np.array([x for x, _ in tiers]), np.array([y for _, y in tiers])
    return c[np.searchsorted(b, np.asarray(price, float), side="right").clip(0, len(c) - 1)]


def net_return(gross, entry_at, exit_at, fees, tiers, extra=0.0, flat=None) -> np.ndarray:
    """The harness's net return, (1 + gross)(1 - fee_sell - tier_exit) / (1 + fee_buy + tier_entry) - 1, tiers at
    the as-traded entry and exit prices. `extra` adds a cost to each side; `flat` = (mask, cost) replaces both
    tiers of the masked trades."""
    ti, te = tier_cost(entry_at, tiers), tier_cost(exit_at, tiers)
    if flat is not None:
        mask, cost = flat
        ti, te = np.where(mask, cost, ti), np.where(mask, cost, te)
    g = np.asarray(gross, float)
    return (1 + g) * (1 - fees.sell - te - extra) / (1 + fees.buy + ti + extra) - 1


def overlap_skips(tr: dict, tick: np.ndarray, sidx: np.ndarray, entry_lag: int) -> np.ndarray:
    """backtest.run()'s overlap rule: a signal while the same name is still held (original exit) is skipped."""
    skipped = np.zeros(len(tick), dtype=bool)
    held = {}
    for i, (n, s) in enumerate(zip(tick, sidx)):
        if s + entry_lag <= held.get(n, -1):
            skipped[i] = True
            continue
        if tr["exit_idx"][i] >= 0:
            held[n] = tr["exit_idx"][i]
        elif tr["status"][i] == backtest.STATUS.index("INCOMPLETE"):
            held[n] = np.iinfo(np.int64).max
    return skipped


class Boot:
    """Calendar-week cluster bootstrap: one fixed set of resampled ISO weeks (of the entry session) serves every
    statistic, so a class mean and a difference between classes see the same weeks."""

    def __init__(self, weeks, resamples: int, seed: int):
        self.weeks = np.array(sorted(set(int(w) for w in weeks)))
        self.pick = np.random.default_rng(seed).integers(0, len(self.weeks), size=(resamples, len(self.weeks)))

    def _stat(self, v, w):
        w = np.asarray(w, dtype=np.int64)
        i = np.searchsorted(self.weeks, w)
        if len(w) and not (self.weeks[np.minimum(i, len(self.weeks) - 1)] == w).all():
            raise ValueError("a week outside the bootstrap's week set")
        n = len(self.weeks)
        S, C = np.bincount(i, np.asarray(v, float), minlength=n), np.bincount(i, minlength=n).astype(float)
        with np.errstate(invalid="ignore", divide="ignore"):
            return S[self.pick].sum(1) / C[self.pick].sum(1)

    def mean(self, v, w) -> dict | None:
        v = np.asarray(v, float)
        if not len(v):
            return None
        st = self._stat(v, w)
        st = st[np.isfinite(st)]
        return {"mean": float(v.mean()), "ci95": [float(np.percentile(st, 2.5)), float(np.percentile(st, 97.5))],
                "n": int(len(v)), "weeks": int(len(set(np.asarray(w).tolist()))), "resamples_finite": int(len(st))}

    def diff(self, v1, w1, v2, w2) -> dict | None:
        v1, v2 = np.asarray(v1, float), np.asarray(v2, float)
        if not len(v1) or not len(v2):
            return None
        st = self._stat(v1, w1) - self._stat(v2, w2)
        st = st[np.isfinite(st)]
        return {"diff": float(v1.mean() - v2.mean()), "ci95": [float(np.percentile(st, 2.5)), float(np.percentile(st, 97.5))],
                "n1": int(len(v1)), "n2": int(len(v2)), "resamples_finite": int(len(st))}


def wilson(k: int, n: int, z: float = 1.959964) -> list:
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    hw = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [float(c - hw), float(c + hw)]


def describe(x) -> dict:
    """Per-trade distribution: mean, median, win rate (net > 0) with its Wilson interval, average win and loss,
    the share of trades at +20% or more net, the extremes."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if not len(x):
        return {"n": 0}
    w, l = x[x > 0], x[x < 0]
    return {"n": int(len(x)), "mean": float(x.mean()), "median": float(np.median(x)),
            "win_rate": float((x > 0).mean()), "win_rate_wilson95": wilson(int((x > 0).sum()), len(x)),
            "avg_win": float(w.mean()) if len(w) else None, "avg_loss": float(l.mean()) if len(l) else None,
            "share_net_at_least_20pct": float((x >= 0.20).mean()), "worst_5": [float(v) for v in np.sort(x)[:5]],
            "p1": float(np.percentile(x, 1)), "p99": float(np.percentile(x, 99)), "best": float(x.max())}


def exposure(entry_i, exit_i, net, notional: float, capital: float) -> dict:
    """One position per trade at a fixed notional from its entry session to its exit session (inclusive), P&L
    realised at the exit close, no compounding, no capital limit (concurrency above capital/notional is reported)."""
    s, e, r = np.asarray(entry_i, int), np.asarray(exit_i, int), np.asarray(net, float)
    if not len(r):
        return None
    occ = np.zeros(int(e.max()) + 2)
    np.add.at(occ, s, 1)
    np.add.at(occ, e + 1, -1)
    occ = np.cumsum(occ)[:-1]
    order = np.argsort(e, kind="stable")
    pnl = np.cumsum(notional * r[order])
    peak = np.maximum.accumulate(np.concatenate([[0.0], pnl]))[1:]
    dd = min(float((pnl - peak).min()), 0.0)
    slots = int(capital // notional)
    return {"model": f"{notional:.0f} USD per trade; capital {capital:.0f} USD ({slots} slots); no compounding; P&L at exit",
            "trades": int(len(r)), "total_pnl_usd": float(pnl[-1]), "return_on_capital": float(pnl[-1] / capital),
            "max_drawdown_usd": dd, "max_drawdown_of_capital": dd / capital,
            "max_concurrent_positions": int(occ.max()), "mean_concurrent_positions_while_any": float(occ[occ > 0].mean()),
            "sessions_above_slots": int((occ > slots).sum()), "sessions_with_a_position": int((occ > 0).sum())}


def counts(s: pd.Series) -> dict:
    return {str(k): int(v) for k, v in s.value_counts().items()}


def same(a, b) -> bool:
    a, b = pd.Series(a).fillna("").astype(str).to_numpy(), pd.Series(b).fillna("").astype(str).to_numpy()
    return len(a) == len(b) and bool((a == b).all())


def check_inputs(proto: dict) -> None:
    if git("status", "--porcelain", "--", "idxsig", "tests", "research/E9"):
        sys.exit("error: commit idxsig/, tests/ and research/E9 first")
    if OUT.exists():
        sys.exit(f"error: {OUT} exists; the test runs once")
    for rel, want in proto["hashes"].items():
        if sha(ROOT / rel) != want:
            sys.exit(f"error: {rel} differs from the frozen hash")


def main() -> int:
    proto = json.loads((E9 / "protocol.json").read_text())
    check_inputs(proto)
    started = now()
    meta_e = json.loads((E9 / "entries" / "entries_meta.json").read_text())
    cfg = backtest.RunConfig(**meta_e["config"])
    panel_df, pmeta = global_panel.load(PANEL)

    # 1. the harness itself
    cache = {}
    result = backtest.run(cfg, panel_df, pmeta, signal_cache=cache)
    (sig, _), = cache.values()
    T = result["trades"].reset_index(drop=True)
    S = pd.read_csv(E9 / "entries" / "signals.csv", dtype={"ticker": str}, keep_default_na=False, na_values=[""])
    s_status = np.where(S.overlap_skipped.astype(bool), "SKIP_OVERLAP", S.status)
    if not (same(T.ticker, S.ticker) and same(T.signal_date, S.signal_date) and same(T.status, s_status)
            and same(T.entry_date, S.entry_date)):
        sys.exit("error: the harness run does not reproduce the shared signal entries")

    # 2. the harness's own steps, from its cached signals
    rule = backtest.rule_registry.get(cfg.rule_id)
    profile = backtest.PROFILES[cfg.market]
    plan = backtest.resolve_plan(cfg, rule)
    fees = backtest.Fees(cfg.fee_buy, cfg.fee_sell)

    def exec_cfg(holding):
        return backtest.ExecConfig(lot_size=profile.lot_size, entry_price=profile.entry, cost_tiers=profile.cost_tiers,
                                   holding_days=holding, entry_lag=cfg.entry_lag, notional=cfg.notional,
                                   max_participation=cfg.max_participation, fees=fees, data_end_exit=cfg.data_end_exit,
                                   ca_mode=cfg.ca_mode, units=cfg.units, fill_model=cfg.fill_model, **plan)

    full = backtest.Market.from_panel(panel_df, price_limits=profile.price_limits)
    full = full.with_units(backtest._dense(full, panel_df, "unit_factor", 1.0))
    lo, hi = full.bounds(cfg.start, cfg.end)
    m = full.slice(lo, hi)
    tick, sidx = np.nonzero(sig == 1)
    ec5, ec2 = exec_cfg(cfg.holding_days), exec_cfg(proto["secondary"]["holding_days"])
    tr = backtest.execute(m, tick, sidx, ec5)
    skipped = overlap_skips(tr, tick, sidx, cfg.entry_lag)
    if not ((skipped == S.overlap_skipped.astype(bool).to_numpy()).all()
            and np.array_equal(tr["net_return"], T.net_return.to_numpy(float), equal_nan=True)):
        sys.exit("error: repeating the harness steps does not reproduce its trades")
    att = ~skipped
    a_tick, a_sig = tick[att], sidx[att]
    feats = {k: v[:, lo:hi] for k, v in backtest.controls.features(full, cfg.controls_version, profile.band_edges,
                                                                   as_traded=cfg.units == "as_traded").items()}
    mt, _ = backtest.controls.matched_draws(np.isfinite(sig), feats, a_tick, a_sig, cfg.random_draws,
                                            np.random.default_rng(cfg.seed + 1), cfg.controls_version)
    r_sig = np.broadcast_to(a_sig, mt.shape).ravel()
    ct = backtest.execute(m, mt.ravel(), r_sig, ec5)
    C = pd.read_csv(E9 / "entries" / "controls.csv.gz", dtype={"ticker": str}, keep_default_na=False, na_values=[""],
                    usecols=["draw", "j", "ticker", "status", "entry_date"])
    if not (same(C.ticker, np.asarray(m.tickers)[mt.ravel()]) and same(C.status, np.asarray(backtest.STATUS)[ct["status"]])):
        sys.exit("error: the re-executed controls do not reproduce the shared control entries")
    pooled = result["summary"]["random_matched"]["pooled"]["avg_net_return"]
    c_ok = np.isin(ct["status"], backtest.SCORED)
    mine = float(ct["net_return"][c_ok].mean())
    if abs(pooled - mine) > 1e-12:
        sys.exit(f"error: control pooled mean {mine} differs from the harness baseline {pooled}")
    tr2 = backtest.execute(m, a_tick, a_sig, ec2)
    ct2 = backtest.execute(m, mt.ravel(), r_sig, ec2)

    # 3. per attempted signal: the harness's trade, costs, controls, class
    A = T[att].reset_index(drop=True)
    names = np.asarray(backtest.STATUS)
    D = pd.DataFrame({"j": np.arange(int(att.sum())), "ticker": A.ticker, "signal_date": A.signal_date,
                      "status": A.status, "entry_date": A.entry_date, "exit_date": A.exit_date,
                      "entry_i": tr["entry_idx"][att], "exit_i": tr["exit_idx"][att],
                      "entry_at": A.entry_price_as_traded.to_numpy(float), "exit_at": A.exit_price_as_traded.to_numpy(float),
                      "gross": A.gross_return.to_numpy(float), "net": A.net_return.to_numpy(float),
                      "status_2": names[tr2["status"]], "net_2": tr2["net_return"]})
    ok = D.status.isin(SCORED).to_numpy()
    if not np.allclose(net_return(D.gross, D.entry_at, D.exit_at, fees, profile.cost_tiers)[ok], D.net[ok],
                       rtol=1e-12, atol=1e-15):
        sys.exit("error: the cost formula does not reproduce the harness nets")
    costs = proto["costs"]
    unit = D.ticker.isin(set(pmeta["unit_quarantine"]["tickers"])).to_numpy()
    D["unit_uncertain"] = unit
    D["net_stress"] = net_return(D.gross, D.entry_at, D.exit_at, fees, profile.cost_tiers, extra=costs["stress_extra_per_side"])
    D["net_bound"] = net_return(D.gross, D.entry_at, D.exit_at, fees, profile.cost_tiers,
                                flat=(unit, costs["unit_uncertain_tier_per_side"]))
    c_ok2 = np.isin(ct2["status"], backtest.SCORED)
    cdf = pd.DataFrame({"j": np.tile(np.arange(mt.shape[1]), mt.shape[0]),
                        "net": np.where(c_ok, ct["net_return"], np.nan),
                        "net_stress": np.where(c_ok, net_return(ct["gross_return"], ct["entry_price_as_traded"],
                                                                ct["exit_price_as_traded"], fees, profile.cost_tiers,
                                                                extra=costs["stress_extra_per_side"]), np.nan),
                        "net_2": np.where(c_ok2, ct2["net_return"], np.nan)})
    cm = cdf.groupby("j").agg(ctrl_net=("net", "mean"), ctrl_net_stress=("net_stress", "mean"),
                              ctrl_net_2=("net_2", "mean"), ctrl_scored=("net", "count"))
    D = D.join(cm, on="j")
    D["excess"] = D.net - D.ctrl_net
    D["excess_stress"] = D.net_stress - D.ctrl_net_stress
    D["excess_2"] = D.net_2 - D.ctrl_net_2
    K = pd.read_csv(E9 / "feasibility_a3" / "classes.csv.gz", dtype={"ticker": str}, keep_default_na=False, na_values=[""])
    if not (same(K.j, D.j) and same(K.ticker, D.ticker) and same(K.signal_date, D.signal_date)):
        sys.exit("error: the frozen classes do not line up with the attempted signals")
    D["class"] = K["class"].to_numpy()
    for col, src in (("covered", "window_covered"), ("etoro", "etoro_listed_now"), ("later4d", "later_documented_4d")):
        D[col] = K[src].astype(str).eq("True").to_numpy()
    D["forms"], D["items_8k"] = K["forms"].to_numpy(), K["items_8k"].to_numpy()
    entry = pd.to_datetime(D.entry_date.where(D.entry_date.astype(str) != ""), errors="coerce")
    iso = entry.dt.isocalendar()
    D["week"] = iso.year.astype("Int64") * 100 + iso.week.astype("Int64")
    D["year"] = D.signal_date.astype(str).str[:4]

    base = D[D.status.isin(SCORED) & D["class"].isin(GROUPS)]
    sc = base[base.covered].copy()
    sc["week"] = sc.week.astype(int)
    w_lo, w_hi = np.percentile(sc.net, [1, 99])  # robustness only: pooled 1st / 99th percentiles of the sample
    sc["net_w"] = sc.net.clip(w_lo, w_hi)
    sc["win"] = (sc.net > 0).astype(float)
    st = proto["statistics"]
    boot = Boot(sc.week, st["resamples"], st["seed"])
    g = {c: sc[sc["class"] == c] for c in GROUPS}
    doc, und, dil = g["DOCUMENTED"], g["UNDOCUMENTED"], g["DILUTION"]

    def ci(df, col):
        v = df[col].notna()
        return boot.mean(df.loc[v, col], df.loc[v, "week"])

    def dci(a, b, col):
        va, vb = a[col].notna(), b[col].notna()
        return boot.diff(a.loc[va, col], a.loc[va, "week"], b.loc[vb, col], b.loc[vb, "week"])

    def block(df):
        e = df[df.etoro]
        return {"plan_5d": describe(df.net), "mean_net_ci": ci(df, "net"), "excess_vs_matched": ci(df, "excess"),
                "winsorized_1_99": ci(df, "net_w"),
                "stress": {**describe(df.net_stress), "ci": ci(df, "net_stress"),
                           "excess_vs_matched": ci(df, "excess_stress")},
                "unit_bound": {**describe(df.net_bound), "ci": ci(df, "net_bound")},
                "secondary_20d": {**describe(df.net_2), "ci": ci(df, "net_2"), "excess_vs_matched": ci(df, "excess_2")},
                "etoro_listed_now": {**describe(e.net), "ci": ci(e, "net")},
                "by_year": {y: describe(x.net) for y, x in df.groupby("year")},
                "unit_uncertain_trades": int(df.unit_uncertain.sum()), "distinct_tickers": int(df.ticker.nunique())}

    sep = {"primary_5d": dci(doc, und, "net"), "excess_vs_matched": dci(doc, und, "excess"),
           "winsorized_1_99": dci(doc, und, "net_w"), "win_rate": dci(doc, und, "win"),
           "median": float(doc.net.median() - und.net.median()) if len(doc) and len(und) else None,
           "stress": dci(doc, und, "net_stress"), "unit_bound": dci(doc, und, "net_bound"),
           "etoro_listed_now": dci(doc[doc.etoro], und[und.etoro], "net"),
           "secondary_20d": dci(doc, und, "net_2"),
           "by_year": {y: {"diff": float(doc[doc.year == y].net.mean() - und[und.year == y].net.mean()),
                           "n_doc": int((doc.year == y).sum()), "n_undoc": int((und.year == y).sum())}
                       for y in proto["acceptance"]["years"]}}
    unc = base[base["class"].isin(("DOCUMENTED", "UNDOCUMENTED"))]
    u_doc, u_und = unc[unc["class"] == "DOCUMENTED"], unc[unc["class"] == "UNDOCUMENTED"]
    incl = {"note": "sensitivity: also the rows whose issuer has no fetched filing on or before the prior session",
            "documented": describe(u_doc.net), "undocumented": describe(u_und.net),
            "diff": float(u_doc.net.mean() - u_und.net.mean()) if len(u_doc) and len(u_und) else None}
    capital = proto["exposure"]["capital_usd"]
    scored_all = D[D.status.isin(SCORED)]
    res = {"protocol_id": proto["protocol_id"], "started": started, "code_commit": git("rev-parse", "HEAD"),
           "reproduction": {"harness_trades_equal_shared_entries": True, "repeated_steps_equal_harness_nets": True,
                            "controls_equal_shared_entries": True, "control_pooled_mean_vs_harness": [mine, pooled],
                            "cost_formula_reproduces_harness": True},
           "attempted": int(len(D)), "attempted_by_class": counts(D["class"]),
           "scored_by_class_before_coverage_rule": counts(base["class"]),
           "excluded_window_not_covered": counts(base[~base.covered]["class"]),
           "scored_by_class": counts(sc["class"]),
           "all_scored_signals": {**describe(scored_all.net), "excess_vs_matched_mean": float(scored_all.excess.mean())},
           "winsorization_bounds": [float(w_lo), float(w_hi)],
           "classes": {c: block(df) if len(df) else None for c, df in g.items()},
           "separation_doc_minus_undoc": sep,
           "dilution_minus_undoc": dci(dil, und, "net") if len(dil) else None,
           "undocumented_by_later_filing_4d": {"later_documented": describe(und[und.later4d].net),
                                               "not_documented_within_4d": describe(und[~und.later4d].net)},
           "uncovered_included": incl,
           "exposure_documented": exposure(doc.entry_i, doc.exit_i, doc.net, cfg.notional, capital),
           "exposure_all_classified": exposure(sc.entry_i, sc.exit_i, sc.net, cfg.notional, capital)}
    d5, dm = sep["primary_5d"], res["classes"]["DOCUMENTED"]
    yrs = proto["acceptance"]["years"]
    crit = {"C1_at_least_150_scored_DOCUMENTED_and_150_UNDOCUMENTED": len(doc) >= 150 and len(und) >= 150,
            "C2_DOCUMENTED_mean_net_positive_in_each_year": bool(dm) and all(
                dm["by_year"].get(y, {}).get("n", 0) > 0 and dm["by_year"][y]["mean"] > 0 for y in yrs),
            "C3_DOCUMENTED_mean_net_lower95_above_zero": bool(dm) and dm["mean_net_ci"]["ci95"][0] > 0,
            "C4_DOCUMENTED_minus_UNDOCUMENTED_lower95_above_zero": bool(d5) and d5["ci95"][0] > 0,
            "C5_DOCUMENTED_mean_excess_over_matched_controls_positive": bool(dm) and dm["excess_vs_matched"]["mean"] > 0,
            "C6_DOCUMENTED_mean_net_positive_under_stress": bool(dm) and dm["stress"]["mean"] > 0}
    rp = all(crit.values())
    q1 = ("SEPARATES" if d5 and d5["ci95"][0] > 0 else
          "DOES_NOT_SEPARATE" if d5 and d5["diff"] <= 0 else "INCONCLUSIVE")
    q2 = ("PROFITABLE_IN_THIS_HISTORICAL_TEST" if rp else
          "UNPROFITABLE" if dm and dm["plan_5d"]["mean"] <= 0 else "INCONCLUSIVE")
    res.update({"acceptance": crit, "research_positive": rp,
                "verdict": {"Q1_filing_known_at_entry_separates_continuation": q1,
                            "Q2_buying_documented_movers_on_the_E2_plan": q2,
                            "overall": "RESEARCH-POSITIVE" if rp else
                                       ("NEGATIVE" if q2 == "UNPROFITABLE" or q1 == "DOES_NOT_SEPARATE" else "INCONCLUSIVE")},
                "finished": now()})
    OUT.mkdir(parents=True)
    D.to_csv(OUT / "trades.csv.gz", index=False, float_format="%.12g", compression={"method": "gzip", "mtime": 0})
    (OUT / "RESULT.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: res[k] for k in ("scored_by_class", "excluded_window_not_covered", "verdict", "acceptance")},
                     indent=1, default=str))
    print(json.dumps({"doc_minus_undoc": d5, "documented": dm["plan_5d"] if dm else None,
                      "undocumented": res["classes"]["UNDOCUMENTED"]["plan_5d"] if res["classes"]["UNDOCUMENTED"] else None},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
