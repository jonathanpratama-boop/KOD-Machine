"""REVERSAL_1M: the single recorded run of PROTOCOL.md. Reads the hashed French files, drops every month from 2024-01,
computes the four gates and the reported extras, writes results/{RESULT.json, monthly.csv}. Refuses a second run.
Usage (from idx-signals/): python3 research/REVERSAL_1M/run.py
"""
import glob
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig.quant import ols_hac, series_stats  # noqa: E402

OUT = Path(__file__).resolve().parent / "results"
STREV = ROOT / "data" / "raw" / "french" / "strev_monthly.csv.gz"
FACTORS = ROOT / "data" / "raw" / "french" / "factors_daily.csv.gz"
FACTOR_MANIFEST = ROOT / "data" / "manifests" / "french_factors-20261020T182212Z.json"
FACTOR_COLS = ["Mkt-RF", "SMB", "HML", "MOM"]
SEALED_FROM = "2024-01"
HURDLE, COST, LAGS = 3.0, 4 * 0.0020, 6


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_hashes() -> str:
    strev_man = sorted(glob.glob(str(ROOT / "data" / "manifests" / "french_strev-*.json")))
    if len(strev_man) != 1:
        sys.exit(f"error: expected one french_strev manifest, found {len(strev_man)}")
    for man, path in ((Path(strev_man[0]), STREV), (FACTOR_MANIFEST, FACTORS)):
        want = json.loads(man.read_text())["parsed"]["sha256"]
        if sha(path) != want:
            sys.exit(f"error: {path.name} does not match {man.name}")
    return Path(strev_man[0]).name


def load() -> pd.DataFrame:
    """Monthly ST_Rev joined with the daily factors compounded to calendar months; months >= SEALED_FROM never kept."""
    s = pd.read_csv(STREV, dtype={"month": str}).set_index("month")
    s = s[s.index < SEALED_FROM]
    d = pd.read_csv(FACTORS, parse_dates=["date"]).set_index("date")
    d = d[d.index < pd.Timestamp(SEALED_FROM + "-01")]
    m = (1 + d[FACTOR_COLS]).groupby(d.index.to_period("M").astype(str)).prod() - 1
    return s.join(m, how="inner")


def window(df: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    return df[(df.index >= a) & (df.index <= b)]


def main() -> int:
    OUT.mkdir(exist_ok=True)
    if (OUT / "RESULT.json").exists():
        sys.exit("error: results/RESULT.json exists; this test runs once")
    strev_manifest = check_hashes()
    df = load()
    main_w, oos, early = window(df, "2005-01", "2019-12"), window(df, "2020-01", "2023-12"), window(df, "1963-07", "2004-12")
    if len(main_w) != 180 or len(oos) != 48:
        sys.exit(f"error: expected 180 and 48 months, got {len(main_w)} and {len(oos)}")
    s_main = series_stats(main_w["ST_Rev"].to_numpy(), LAGS)
    reg = ols_hac(main_w["ST_Rev"].to_numpy(), main_w[FACTOR_COLS].to_numpy(), LAGS)
    oos_mean = float(oos["ST_Rev"].mean())
    gates = {
        "G1_mean_t_nw_ge_3": bool(s_main["mean"] > 0 and s_main["t_nw"] >= HURDLE),
        "G2_alpha_t_nw_ge_3": bool(reg["alpha"] > 0 and reg["alpha_t"] >= HURDLE),
        "G3_mean_minus_0.80pct_gt_0": bool(s_main["mean"] - COST > 0),
        "G4_oos_2020_2023_mean_gt_0": bool(oos_mean > 0),
    }
    years = main_w.groupby(main_w.index.str[:4])["ST_Rev"].mean()
    res = {
        "experiment": "REVERSAL_1M", "protocol": "research/REVERSAL_1M/PROTOCOL.md",
        "label": "historical research only; never prospective performance",
        "inputs": {"strev_manifest": strev_manifest, "factor_manifest": FACTOR_MANIFEST.name, "sealed_from": SEALED_FROM},
        "main_2005_2019": s_main,
        "alpha_2005_2019": {"alpha": reg["alpha"], "alpha_t": reg["alpha_t"], "betas": dict(zip(FACTOR_COLS, reg["betas"])),
                            "beta_t": dict(zip(FACTOR_COLS, reg["beta_t"])), "r2": reg["r2"], "n": reg["n"]},
        "assumed_cost_per_month": COST, "net_mean_2005_2019": s_main["mean"] - COST,
        "breakeven_cost_per_side": s_main["mean"] / 4,
        "oos_2020_2023": {"n": int(len(oos)), "mean": oos_mean, "share_positive": float((oos["ST_Rev"] > 0).mean())},
        "published_era_1963_2004": series_stats(early["ST_Rev"].to_numpy(), LAGS),
        "years_2005_2019": {k: float(v) for k, v in years.items()},
        "years_positive_2005_2019": int((years > 0).sum()),
        "gates": gates, "verdict": "PASS" if all(gates.values()) else "FAIL",
    }
    df[df.index >= "1963-07"].to_csv(OUT / "monthly.csv")
    (OUT / "RESULT.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("main_2005_2019", "gates", "verdict")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
