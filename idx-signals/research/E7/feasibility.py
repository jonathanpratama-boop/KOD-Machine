"""E7 feasibility counts (FEASIBILITY_SPEC.md, commit 6a2ba8f). Discovery window only; no return conditional
on any signal is computed. Writes research/E7/FEASIBILITY.json.
Usage (from idx-signals/): python3 research/E7/feasibility.py data/manifests/binance_perp-<stamp>.jsonl \
                           data/manifests/binance_1h-20261015T182940Z.jsonl
"""
import io, json, sys, zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
D0, D1 = pd.Timestamp("2021-12-01", tz="UTC"), pd.Timestamp("2022-12-31 23:00", tz="UTC")  # nothing later is read
T_LAST = pd.Timestamp("2022-12-30 23:00", tz="UTC")  # the 24-bar spot window starting T+1h ends inside discovery
SPOT_COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote", "count", "tb_base", "tb_quote", "ignore"]


def zcsv(path, **kw):
    with zipfile.ZipFile(ROOT / "data" / "raw" / path) as z:
        return pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), **kw)


def load_perp(manifest):
    lines = [json.loads(l) for l in Path(manifest).read_text().splitlines()]
    head, recs = lines[0], lines[1:]
    fund, oi = {}, {}
    for r in recs:
        if r["kind"] == "fundingRate":
            df = zcsv(r["file"])
            if not str(df.columns[0]).startswith("calc_time"):
                df = zcsv(r["file"], header=None, names=["calc_time", "funding_interval_hours", "last_funding_rate"])
            fund.setdefault(r["symbol"], []).append(df)
        else:
            oi.setdefault(r["symbol"], []).append(zcsv(r["file"], usecols=["create_time", "sum_open_interest"]))
    F = {}
    for s, parts in fund.items():
        df = pd.concat(parts).drop_duplicates("calc_time")
        df["T"] = pd.to_datetime(df["calc_time"], unit="ms", utc=True).dt.floor("h")
        F[s] = df.sort_values("T").set_index("T")[["funding_interval_hours", "last_funding_rate"]]
        F[s] = F[s][F[s].index <= D1]
    O = {}
    for s, parts in oi.items():
        df = pd.concat(parts)
        df["t"] = pd.to_datetime(df["create_time"], utc=True)
        O[s] = df.drop_duplicates("t").sort_values("t").set_index("t")["sum_open_interest"].astype(float)
        O[s] = O[s][O[s].index <= D1]
    return head, F, O


def load_spot(manifest, syms):
    lines = [json.loads(l) for l in Path(manifest).read_text().splitlines()[1:]]
    S = {}
    for s in syms:
        files = sorted(r["file"] for r in lines if r["symbol"] == s and "2021-08" <= r["month"] <= "2022-12")
        if not files:
            continue
        df = pd.concat([zcsv(f, header=None, names=SPOT_COLS) for f in files])
        df["t"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        df = df.drop_duplicates("t").set_index("t").sort_index()
        S[s] = df[df.index <= D1][["open", "close", "quote"]]
    return S


def main(perp_manifest, spot_manifest):
    head, F, O = load_perp(perp_manifest)
    syms = sorted(set(F) & set(O))
    S = load_spot(spot_manifest, syms)
    out = {"spec_commit": "6a2ba8f", "perp_manifest": Path(perp_manifest).name, "spot_manifest": Path(spot_manifest).name,
           "window": [str(D0), str(T_LAST)], "download_failures": len(head["failures"])}
    # ---------------- coverage
    cov = {}
    for s in head["overlap_symbols"]:
        c = head["coverage"][s]
        o = O.get(s)
        in_win = o[(o.index >= D0)] if o is not None else None
        if in_win is not None and len(in_win):
            span = pd.date_range(max(D0, in_win.index[0].floor("D")), min(D1, in_win.index[-1]).floor("D") + pd.Timedelta("23:55:00"), freq="5min")
            completeness = len(in_win) / len(span)
        else:
            completeness = 0.0
        cov[s] = {**c, "metrics_snapshots_in_window": int(len(in_win)) if in_win is not None else 0,
                  "metrics_completeness": round(completeness, 4),
                  "funding_settlements_in_window": int(((F[s].index >= D0)).sum()) if s in F else 0,
                  "non_8h_intervals": int((F[s]["funding_interval_hours"] != 8).sum()) if s in F else None,
                  "spot_loaded": s in S}
    covered = [s for s, c in cov.items() if c["metrics_completeness"] >= 0.8 and c["funding_settlements_in_window"] > 0 and c["spot_loaded"]]
    out["coverage"] = {"overlap_perps": len(head["overlap_symbols"]), "with_funding_and_metrics_files": len(syms),
                       "covered_ge_80pct_metrics": len(covered),
                       "metrics_completeness_quartiles": [float(x) for x in np.percentile([c["metrics_completeness"] for c in cov.values()], [25, 50, 75])],
                       "delisted_before_2023_by_archive": sum(1 for c in cov.values() if c["funding_last"] and c["funding_last"] < "2023-01"),
                       "listed_after_window_start": sum(1 for c in cov.values() if c["metrics_first"] and c["metrics_first"] > "2021-12-01"),
                       "non_8h_funding_intervals": int(sum((c["non_8h_intervals"] or 0) for c in cov.values())),
                       "perps_with_2023_files_listed": sum(1 for c in cov.values() if c["metrics_files_2023_listed"] > 0),
                       "note": "listing/delisting dates are archive-derived; 2023 counts are from listings only"}
    # ---------------- observations
    rows, miss = [], {"no_spot_bar_at_T": 0, "no_oi_near_T": 0, "no_oi_near_T_minus_7d": 0, "fewer_than_3_settlements": 0,
                      "spot_ineligible": 0, "entry_bar_missing": 0, "window_short": 0}
    for s in covered:
        f, o, sp = F[s], O[s], S[s]
        daily_q = sp["quote"].resample("1D").sum()
        complete = sp["quote"].resample("1D").count() == 24
        med30 = daily_q.rolling(30, min_periods=30).median().shift(1)        # last 30 completed days before T's day
        hist = complete.astype(int).cumsum().shift(1)
        hourly_med24 = sp["quote"].rolling(24, min_periods=12).median()
        fr = f["last_funding_rate"].astype(float)
        for T, rate in fr[(fr.index >= D0) & (fr.index <= T_LAST)].items():
            i = f.index.get_loc(T)
            if i < 2:
                miss["fewer_than_3_settlements"] += 1; continue
            bar_end = T - pd.Timedelta("1h")                                   # spot bar ending at T opens at T-1h
            if bar_end not in sp.index:
                miss["no_spot_bar_at_T"] += 1; continue
            day = T.floor("D")
            if not (med30.get(day, np.nan) >= 200_000 and hist.get(day, 0) >= 60):
                miss["spot_ineligible"] += 1; continue
            a = o[(o.index <= T - pd.Timedelta("5min")) & (o.index >= T - pd.Timedelta("35min"))]
            b = o[(o.index <= T - pd.Timedelta("7D") - pd.Timedelta("5min")) & (o.index >= T - pd.Timedelta("7D") - pd.Timedelta("35min"))]
            if not len(a):
                miss["no_oi_near_T"] += 1; continue
            if not len(b):
                miss["no_oi_near_T_minus_7d"] += 1; continue
            r3 = fr.iloc[i - 2:i + 1]
            Fflag = bool((r3 < 0).all())
            c72 = sp["close"].get(bar_end - pd.Timedelta("72h"), np.nan)
            Sflag = Fflag and a.iloc[-1] / b.iloc[-1] >= 1.20 and sp.at[bar_end, "close"] >= c72
            # unconditional spot window for sample planning (not conditional on F or S)
            e0, e1 = T + pd.Timedelta("1h"), T + pd.Timedelta("24h")
            ent = sp["open"].get(e0, np.nan)
            win = sp.loc[e0:e1]
            if not np.isfinite(ent):
                miss["entry_bar_missing"] += 1; r24 = np.nan
            else:
                if len(win) < 24:
                    miss["window_short"] += 1
                r24 = win["close"].iloc[-1] / ent - 1 if len(win) else np.nan
            rows.append({"symbol": s, "T": T, "F": Fflag, "S": bool(Sflag), "r24": r24,
                         "capacity_usdt": 0.01 * hourly_med24.get(bar_end, np.nan)})
    obs = pd.DataFrame(rows)
    out["missingness"] = miss
    out["eligible_observations"] = int(len(obs))

    def debounce(df, col):
        keep = []
        for s, g in df[df[col]].groupby("symbol"):
            last = None
            for T in g["T"]:
                if last is None or T - last >= pd.Timedelta("72h"):
                    keep.append((s, T)); last = T
        return pd.DataFrame(keep, columns=["symbol", "T"])

    ev = {"S_primary": debounce(obs, "S"), "F_funding_only": debounce(obs, "F")}
    obs["month"] = obs["T"].dt.strftime("%Y-%m")
    out["eligible_by_month"] = obs.groupby("month").size().to_dict()
    out["distinct_eligible_contracts_per_settlement"] = {k: float(v) for k, v in
        obs.groupby("T")["symbol"].nunique().describe()[["min", "25%", "50%", "75%", "max"]].items()}
    for k, e in ev.items():
        e["month"] = e["T"].dt.strftime("%Y-%m")
        e["week"] = e["T"].dt.strftime("%G-%V")
        bycoin = e.groupby("symbol").size().sort_values(ascending=False)
        share = bycoin / bycoin.sum() if len(bycoin) else bycoin
        out[k] = {"events_after_debounce": int(len(e)), "raw_flags_before_debounce": int(obs[k[0]].sum()),
                  "distinct_coins": int(len(bycoin)), "months_with_events": int(e["month"].nunique()),
                  "by_month": e.groupby("month").size().to_dict(),
                  "top_coins": {s: int(n) for s, n in bycoin.head(10).items()},
                  "top1_share": float(share.iloc[0]) if len(share) else None,
                  "top5_share": float(share.head(5).sum()) if len(share) else None,
                  "effective_coins_1_over_hhi": float(1 / (share ** 2).sum()) if len(share) else None,
                  "distinct_days": int(e["T"].dt.floor("D").nunique()),
                  "events_per_week": {"mean": float(e.groupby("week").size().mean()) if len(e) else 0,
                                      "max": int(e.groupby("week").size().max()) if len(e) else 0, "weeks": int(e["week"].nunique())}}
        cap = obs.merge(e[["symbol", "T"]], on=["symbol", "T"])["capacity_usdt"]
        out[k]["capacity_usdt_quartiles_pre_entry"] = [float(x) for x in np.nanpercentile(cap, [25, 50, 75])] if len(cap) else None
    out["S_primary"]["also_F"] = "S is a subset of F by construction"
    # ---------------- unconditional sample-planning inputs
    u = obs.dropna(subset=["r24"]).copy()
    u["excess"] = u["r24"] - u.groupby("T")["r24"].transform("median")
    sigma = float(u["excess"].std())
    nonover = u[(u["T"].dt.hour == 0) & (u["T"].dt.dayofyear % 3 == 0)].copy()   # one 24h window per coin per 3 days
    nonover["week"] = nonover["T"].dt.strftime("%G-%V")
    g = nonover.groupby("week")["excess"]
    k_i, n_tot, a_ = g.size(), len(nonover), g.ngroups
    msb = (k_i * (g.mean() - nonover["excess"].mean()) ** 2).sum() / (a_ - 1)
    msw = ((nonover["excess"] - g.transform("mean")) ** 2).sum() / (n_tot - a_)
    k0 = (n_tot - (k_i ** 2).sum() / n_tot) / (a_ - 1)
    rho = float(max((msb - msw) / (msb + (k0 - 1) * msw), 0.0))
    out["planning_inputs_unconditional"] = {"sigma_24h_excess": sigma, "observations": int(len(u)),
                                           "rho_same_week_excess": rho, "rho_sample": int(len(nonover)),
                                           "note": "excess = coin 24h spot return minus the median over eligible coins at the same settlement; never conditional on F or S"}
    m = max(out["S_primary"]["events_per_week"]["mean"], 1.0)
    de_meas = 1 + (m - 1) * rho
    table = []
    for sig_mult in (1.0, 1.5):
        for de in (1.0, de_meas, 2.0, 3.0):
            for d in (0.0025, 0.005, 0.01, 0.02):
                n = ((1.96 + 0.84) * sigma * sig_mult / d) ** 2 * de
                table.append({"sigma": round(sigma * sig_mult, 4), "design_effect": round(de, 3), "delta": d, "events_needed": int(np.ceil(n))})
    out["sample_size_sensitivity"] = table
    out["design_effect_measured"] = {"events_per_week_S": m, "rho": rho, "DE": de_meas}
    need1 = int(np.ceil(((1.96 + 0.84) * sigma / 0.01) ** 2 * de_meas))
    need2 = int(np.ceil(((1.96 + 0.84) * sigma / 0.02) ** 2 * de_meas))
    nS = out["S_primary"]["events_after_debounce"]
    mde = (1.96 + 0.84) * sigma * np.sqrt(de_meas / nS) if nS else None
    crit = {"coverage_ge_100_perps": len(covered) >= 100, "events_cover_delta_1pct": nS >= need1,
            "events_cover_delta_2pct": nS >= need2, "months_ge_10_of_13": out["S_primary"]["months_with_events"] >= 10,
            "top5_le_40pct": (out["S_primary"]["top5_share"] or 1) <= 0.40}
    verdict = ("GO" if crit["coverage_ge_100_perps"] and crit["events_cover_delta_1pct"] and crit["months_ge_10_of_13"] and crit["top5_le_40pct"]
               else "GO-LIMITED" if crit["coverage_ge_100_perps"] and crit["events_cover_delta_2pct"] and crit["months_ge_10_of_13"] and crit["top5_le_40pct"]
               else "PAUSE")
    out["decision"] = {"criteria": crit, "events_needed_delta_1pct": need1, "events_needed_delta_2pct": need2,
                       "S_events": nS, "minimum_detectable_effect_24h": float(mde) if mde else None, "verdict": verdict}
    (Path(__file__).parent / "FEASIBILITY.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps({k: out[k] for k in ("coverage", "missingness", "eligible_observations", "decision", "planning_inputs_unconditional")}, indent=1, default=str))
    for k in ev:
        print(k, {x: out[k][x] for x in ("events_after_debounce", "raw_flags_before_debounce", "distinct_coins", "months_with_events", "top1_share", "top5_share", "effective_coins_1_over_hhi", "events_per_week")})


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
