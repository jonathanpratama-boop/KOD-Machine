"""The single recorded run of PROTOCOL.md. Writes results/{RESULT.json, monthly.csv, betas.csv}; refuses a second run.
Usage (from idx-signals/): python3 research/QUANT_ENGINE_2005_2019/run.py
"""
import hashlib
import importlib.util
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from idxsig import quant  # noqa: E402

_spec = importlib.util.spec_from_file_location("lowvol_run", ROOT / "research" / "US_LOWVOL_MOM_2005_2019" / "run.py")
lowvol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lowvol)

FEATURES = ["mom", "rev", "lowvol", "high52", "logdv", "maxret", "voltrend"]
LAM, EMBARGO, MIN_TRAIN, FIRST_SCORE = 100.0, 1, 24, "2008-01-01"
MIN_DV, MIN_HIST, CLIP = 2e6, 252, (-0.9, 2.0)
AUMS = [1e4, 1e5, 1e6, 1e7, 1e8]
GATE_AUM, T_BAR, YEARS_BAR, LARGE_T_BAR = 1e5, 3.0, 9, 2.0
FACTOR_COLS = ["Mkt-RF", "SMB", "HML", "MOM"]
FACTORS = ROOT / "data" / "raw" / "french" / "factors_daily.csv.gz"


def build_panels(adj: pd.DataFrame, cl: pd.DataFrame, vol: pd.DataFrame) -> dict:
    """Month-end feature, forward-return and cost-input panels (months x stocks). Features use data up to the formation
    close only; the forward return runs from the next session's close to the next month-end close."""
    dates = adj.index
    A, C, V = adj.to_numpy(float), cl.to_numpy(float), vol.to_numpy(float)
    lr = np.diff(np.log(A), axis=0, prepend=np.nan)
    dv = C * V
    month_end = [i for i in range(len(dates) - 1) if dates[i].month != dates[i + 1].month]
    keys = FEATURES + ["fwd", "sd60", "dv60"]
    P = {k: [] for k in keys}
    meta = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for k, t in enumerate(month_end[:-1]):
            if t < MIN_HIST or dates[t] < pd.Timestamp("2005-01-01"):
                continue
            t_next, e = month_end[k + 1], t + 1
            sd = np.nanstd(lr[t - 59:t + 1], axis=0)
            med60 = np.nanmedian(dv[t - 59:t + 1], axis=0)
            hist = np.isfinite(A[t - 252:t + 1]).sum(axis=0)
            f = {"mom": A[t - 21] / A[t - 252] - 1, "rev": A[t] / A[t - 21] - 1, "lowvol": -sd,
                 "high52": A[t] / np.nanmax(A[t - 251:t + 1], axis=0), "logdv": np.log(med60),
                 "maxret": np.nanmax(lr[t - 20:t + 1], axis=0),
                 "voltrend": np.log(np.nanmedian(dv[t - 19:t + 1], axis=0) / np.nanmedian(dv[t - 119:t + 1], axis=0))}
            ok = (np.isfinite(sd) & (sd > 0) & (med60 >= MIN_DV) & (hist >= MIN_HIST) & np.isfinite(A[t]))
            for name in FEATURES:
                P[name].append(np.where(ok, f[name], np.nan))
            P["fwd"].append(np.clip(A[t_next] / A[e] - 1, *CLIP))
            P["sd60"].append(np.where(ok, sd, np.nan))
            P["dv60"].append(np.where(ok, med60, np.nan))
            meta.append({"formed": dates[t], "entry": e, "exit": t_next})
    out = {k: np.array(v) for k, v in P.items()}
    out["meta"] = meta
    out["dates"] = dates
    return out


def holding_factors(meta: list[dict], dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Daily factor returns compounded over each holding window (sessions entry+1 .. exit)."""
    fac = pd.read_csv(FACTORS, index_col=0, parse_dates=True)
    rows = []
    for m in meta:
        w = fac.reindex(dates[m["entry"] + 1:m["exit"] + 1])
        rows.append(((1 + w).prod() - 1).to_dict() | {"n_days": int(w.notna().all(axis=1).sum())})
    return pd.DataFrame(rows)


def evaluate(P: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    feats = [P[n] for n in FEATURES]
    fwd = P["fwd"]
    first = next(i for i, m in enumerate(P["meta"]) if m["formed"] >= pd.Timestamp(FIRST_SCORE))
    scores, betas = quant.walk_forward_scores(feats, fwd, first, LAM, EMBARGO, MIN_TRAIN)
    rows, prev_long, prev_short = [], None, None
    for t in range(first, len(fwd)):
        s = scores[t]
        if not np.isfinite(s).any():
            continue
        qm = quant.quintile_means(s, fwd[t])
        mem = quant.quintile_members(np.where(np.isfinite(fwd[t]), s, np.nan))
        short, long = set(mem[0].tolist()), set(mem[4].tolist())
        row = {"formed": P["meta"][t]["formed"].strftime("%Y-%m-%d"), "ic": quant.rank_ic(s, fwd[t]),
               "universe": float(np.nanmean(fwd[t][np.isfinite(s)])), "n_leg": len(long),
               "tau_long": 1.0 if prev_long is None else len(long - prev_long) / len(long),
               "tau_short": 1.0 if prev_short is None else len(short - prev_short) / len(short),
               "adv_long": float(np.nanmedian(P["dv60"][t][list(long)])), "adv_short": float(np.nanmedian(P["dv60"][t][list(short)])),
               "vol_long": float(np.nanmedian(P["sd60"][t][list(long)])), "vol_short": float(np.nanmedian(P["sd60"][t][list(short)]))}
        large = np.isfinite(s) & (P["dv60"][t] >= np.nanmedian(P["dv60"][t][np.isfinite(s)]))
        row["ic_large"] = quant.rank_ic(np.where(large, s, np.nan), fwd[t])
        for i, name in enumerate(FEATURES):
            row[f"ic_{name}"] = quant.rank_ic(feats[i][t], fwd[t])
        for i in range(5):
            row[f"q{i + 1}"] = float(qm[i])
        row["spread"] = float(qm[4] - qm[0])
        rows.append(row)
        prev_long, prev_short = long, short
    m = pd.DataFrame(rows)
    fac = holding_factors(P["meta"], P["dates"])
    idx = {mm["formed"].strftime("%Y-%m-%d"): i for i, mm in enumerate(P["meta"])}
    fac = fac.iloc[[idx[f] for f in m.formed]].reset_index(drop=True)
    m = pd.concat([m, fac[FACTOR_COLS + ["RF"]].rename(columns=str.lower).add_prefix("f_")], axis=1)
    b = pd.DataFrame(betas[first:], columns=FEATURES, index=[P["meta"][t]["formed"].strftime("%Y-%m-%d") for t in range(first, len(fwd))])
    return m, b.dropna()


def results(m: pd.DataFrame, b: pd.DataFrame) -> dict:
    ic = quant.series_stats(m.ic.to_numpy())
    year = m.formed.str[:4]
    ic_years = m.groupby(year).ic.mean()
    ic["years_positive"], ic["years"] = int((ic_years > 0).sum()), int(len(ic_years))
    large = quant.series_stats(m.ic_large.to_numpy())
    nets = {}
    for aum in AUMS:
        nets[aum] = quant.net_spread_at_aum(m.spread.to_numpy(), m.tau_long.to_numpy(), m.tau_short.to_numpy(), m.adv_long.to_numpy(),
                                            m.adv_short.to_numpy(), m.vol_long.to_numpy(), m.vol_short.to_numpy(), m.n_leg.to_numpy(), aum)
    net_mean = {a: float(v.mean()) for a, v in nets.items()}
    X = m[["f_mkt-rf", "f_smb", "f_hml", "f_mom"]].to_numpy()
    alpha = quant.ols_hac(m.spread.to_numpy(), X, lags=6)
    pos = GATE_AUM / (2 * m.n_leg.to_numpy())
    long_cost = 2 * m.tau_long.to_numpy() * quant.impact_cost_per_side(pos, m.adv_long.to_numpy(), m.vol_long.to_numpy())
    gates = {"G1_ic_t_ge_3_and_9_of_12_years": bool(ic["mean"] > 0 and ic["t_nw"] >= T_BAR and ic["years_positive"] >= YEARS_BAR),
             "G2_net_spread_positive_at_100k": bool(net_mean[GATE_AUM] > 0),
             "G3_factor_alpha_t_ge_3": bool(alpha["alpha"] > 0 and alpha["alpha_t"] >= T_BAR),
             "G4_large_cap_ic_t_ge_2": bool(large["mean"] > 0 and large["t_nw"] >= LARGE_T_BAR)}
    return {"months": int(len(m)), "first": m.formed.iloc[0], "last": m.formed.iloc[-1], "ic_combined": ic, "ic_large_half": large,
            "ic_by_feature": {n: quant.series_stats(m[f"ic_{n}"].to_numpy()) for n in FEATURES},
            "mean_ridge_weights": b.mean().round(4).to_dict(),
            "quintile_means_monthly": [float(m[f"q{i}"].mean()) for i in range(1, 6)], "universe_mean_monthly": float(m.universe.mean()),
            "spread_gross": quant.series_stats(m.spread.to_numpy()),
            "mean_turnover": {"long": float(m.tau_long.mean()), "short": float(m.tau_short.mean())},
            "net_spread_mean_monthly_by_aum": {f"{int(a)}": v for a, v in net_mean.items()},
            "breakeven_aum": quant.breakeven_aum(net_mean),
            "factor_alpha_of_spread": alpha,
            "long_only_top_quintile_minus_universe_net_at_100k_monthly": float((m.q5 - m.universe - long_cost).mean()),
            "gates": gates, "all_pass": all(gates.values())}


def main() -> int:
    out = HERE / "results"
    if (out / "RESULT.json").exists():
        sys.exit("refused: the recorded run already exists")
    man = json.loads(sorted((ROOT / "data" / "manifests").glob("french_factors-*.json"))[-1].read_text())
    if hashlib.sha256(FACTORS.read_bytes()).hexdigest() != man["parsed"]["sha256"]:
        sys.exit("refused: factor file does not match its manifest")
    adj, cl, vol = lowvol.load()
    P = build_panels(adj, cl, vol)
    m, b = evaluate(P)
    res = results(m, b)
    res |= {"experiment": "US quant engine 2005-2019 (PROTOCOL.md), run once", "tickers_with_data": int(adj.shape[1]),
            "label": "NON-EVIDENCE: survivor-only universe; machinery demonstration (PROTOCOL.md)",
            "factor_manifest_sha256": man["parsed"]["sha256"]}
    out.mkdir(exist_ok=True)
    m.to_csv(out / "monthly.csv", index=False)
    b.to_csv(out / "betas.csv")
    (out / "RESULT.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    print(json.dumps(res, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
