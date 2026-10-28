"""E6 data check: is the hourly buy/sell flow sound, and is the protocol feasible? Reads NO outcome.

Only same-hour quantities and backward-looking features are computed, on warm-up + discovery hours
(<= 2022-12-31); no return after a decision time is read. Writes research/E6/data_check/
{DATA_CHECK.json, flow_vs_return.png}.
Usage: python3 research/E6/data_check.py data/manifests/binance_1h-<stamp>.jsonl
"""
import io, json, sys, zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote", "count", "tb_base", "tb_quote", "ignore"]
END = pd.Timestamp("2022-12-31 23:00", tz="UTC")


def load(files):
    parts = []
    for f in files:
        with zipfile.ZipFile(ROOT / "data" / "raw" / f) as z:
            raw = z.read(z.namelist()[0])
        df = pd.read_csv(io.BytesIO(raw), header=None, names=COLS)
        if not str(df.iloc[0, 0]).isdigit():  # a header row
            df = pd.read_csv(io.BytesIO(raw), names=COLS, header=0)
        parts.append(df)
    df = pd.concat(parts, ignore_index=True)
    unit = "us" if df["open_time"].max() > 1e14 else "ms"
    df["t"] = pd.to_datetime(df["open_time"], unit=unit, utc=True)
    return df.drop_duplicates("t").sort_values("t").set_index("t"), unit


def main(manifest):
    lines = [json.loads(x) for x in Path(manifest).read_text().splitlines()]
    head, recs = lines[0], lines[1:]
    by = {}
    for r in recs:
        by.setdefault(r["symbol"], []).append(r)
    stats = {"manifest": Path(manifest).name, "symbols": len(by), "files": len(recs), "download_failures": len(head["failures"]),
             "excluded_stable_or_leveraged": len(head["excluded"]),
             "delisted_before_2023_12": sum(1 for s, rs in by.items() if max(r["month"] for r in rs) < "2023-12"),
             "units": {}, "bad_taker_gt_quote_hours": 0, "nonpositive_close_hours": 0, "hours": 0,
             "missing_hours_share_median": None}
    bins = np.linspace(-1, 1, 21)
    sum_r, cnt = np.zeros(20), np.zeros(20)
    per_coin_corr, missing, daily = [], [], []
    for sym, rs in sorted(by.items()):
        df, unit = load([r["file"] for r in rs])
        stats["units"][unit] = stats["units"].get(unit, 0) + 1
        df = df[df.index <= END]
        if len(df) < 24 * 60:
            continue
        span = int((df.index[-1] - df.index[0]) / pd.Timedelta("1h")) + 1
        missing.append(1 - len(df) / span)
        stats["hours"] += len(df)
        stats["bad_taker_gt_quote_hours"] += int((df["tb_quote"] > df["quote"] * (1 + 1e-9)).sum())
        stats["nonpositive_close_hours"] += int((df["close"] <= 0).sum())
        q, b = df["quote"].to_numpy(float), df["tb_quote"].to_numpy(float)
        s = q - b
        x = np.where(q > 0, (b - s) / q, np.nan)  # net flow fraction of the hour
        r = np.log(df["close"] / df["close"].shift(1)).to_numpy()
        ok = np.isfinite(x) & np.isfinite(r) & (q > 0)
        if ok.sum() > 500:
            per_coin_corr.append(np.corrcoef(x[ok], r[ok])[0, 1])
            idx = np.clip(np.digitize(x[ok], bins) - 1, 0, 19)
            np.add.at(sum_r, idx, r[ok]); np.add.at(cnt, idx, 1)
        d = df["quote"].resample("1D").agg(["sum", "count"])
        d["symbol"] = sym
        daily.append(d)
    stats["missing_hours_share_median"] = float(np.median(missing)) if missing else None
    pc = np.array(per_coin_corr)
    stats["same_hour_flow_return_corr"] = {"coins": int(len(pc)), "median": float(np.median(pc)), "share_positive": float((pc > 0).mean()),
                                           "p10": float(np.percentile(pc, 10)), "p90": float(np.percentile(pc, 90))}
    stats["mean_return_by_flow_bin"] = [{"flow_lo": float(bins[i]), "flow_hi": float(bins[i + 1]), "hours": int(cnt[i]),
                                         "mean_log_return": float(sum_r[i] / cnt[i]) if cnt[i] else None} for i in range(20)]
    dd = pd.concat(daily).reset_index()
    dd = dd[dd["count"] == 24]
    dd["med30"] = dd.groupby("symbol")["sum"].transform(lambda v: v.rolling(30, min_periods=30).median())
    elig = dd[(dd["t"] >= "2020-07-01") & (dd["med30"] >= 200_000)]
    per_day = elig.groupby("t")["symbol"].nunique()
    stats["eligible_coin_days_discovery_liquidity_only"] = int(len(elig))
    stats["eligible_coins_per_day"] = {"min": int(per_day.min()), "median": float(per_day.median()), "max": int(per_day.max())}
    stats["expected_P1_ceiling"] = ("top 5% of eligible coins per day before the participation, range, strength and debounce "
                                    f"filters: about {int(0.05 * len(elig))} coin-days; the filters cut this further")
    out = Path(__file__).parent / "data_check"
    out.mkdir(exist_ok=True)
    (out / "DATA_CHECK.json").write_text(json.dumps(stats, indent=2))
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    mid = (bins[:-1] + bins[1:]) / 2
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(mid, [sum_r[i] / cnt[i] * 100 if cnt[i] else 0 for i in range(20)], width=0.09, color="#4a6fa5")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel("net flow fraction of the hour: (buy-initiated - sell-initiated) / traded value")
    ax.set_ylabel("mean same-hour log return (%)")
    ax.set_title(f"Binance spot USDT, 2020-04..2022-12, {stats['hours']:,} hours, {len(pc)} coins")
    fig.tight_layout(); fig.savefig(out / "flow_vs_return.png", dpi=120)
    print(json.dumps({k: v for k, v in stats.items() if k not in ("mean_return_by_flow_bin", "units")}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
