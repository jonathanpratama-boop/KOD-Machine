"""CASES_IDX_v1 evidence packs (PROTOCOL.md): sessions t-15 .. t+5 per case from the archived exchange data."""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from idxsig import e1, panel  # noqa: E402
from idxsig.provenance import MANIFESTS  # noqa: E402

sel = json.loads((HERE / "selection.json").read_text())["cases"]
df, meta, _ = panel.load(MANIFESTS / "panel-20261007T225823Z.json")
st = e1.Study(df, meta)
m, L, dates = st.m, st.level, st.dates
tick = [str(x) for x in m.tickers]
names = pd.read_csv(ROOT / "data/raw/idx_mirror/bc0ac7712ce5/List Emiten/all.csv").set_index("code")["name"].to_dict()
sector_of = {}
for f in glob.glob(str(ROOT / "data/raw/idx_mirror/bc0ac7712ce5/List Emiten/Sectors/*.csv")):
    for c in pd.read_csv(f)["code"]:
        sector_of[c] = Path(f).stem
reg = pd.read_csv(ROOT / "data/corporate_actions/ca_registry-20261007T230210Z.csv", dtype=str)
raw_dir = ROOT / "data/raw/idx_mirror/bc0ac7712ce5/Saham/Semua"
out_dir = HERE / "packs"
out_dir.mkdir(exist_ok=False)
summary = []
for c in sel:
    n, t = tick.index(c["ticker"]), int(c["t"])
    lv = L[n]
    J = next((j for j in range(t + 1, t + 6) if np.isfinite(lv[j]) and np.isfinite(lv[j - 1]) and lv[j] / lv[j - 1] >= 1.10), t + 1)
    raw = pd.read_csv(raw_dir / f"{c['ticker']}.csv")
    raw["date"] = pd.to_datetime(raw["date"].str[:10])
    raw = raw.set_index("date")
    rows = []
    for s in range(max(0, t - 15), min(len(dates), t + 6)):
        d = pd.Timestamp(dates[s])
        r = raw.loc[d] if d in raw.index else None
        prior = [raw.loc[pd.Timestamp(dates[k]), "volume"] for k in range(max(0, s - 20), s) if pd.Timestamp(dates[k]) in raw.index]
        med = float(np.median([p for p in prior if p > 0])) if any(p > 0 for p in prior) else np.nan
        rows.append({"session": s - J, "date": str(d.date()), "close": float(m.close[n, s]),
                     "ret_pct": round(100 * (lv[s] / lv[s - 1] - 1), 1) if s > 0 and np.isfinite(lv[s - 1]) else None,
                     "vol_x_med20": round(float(r["volume"]) / med, 2) if r is not None and med and np.isfinite(med) else None,
                     "value_bn": round(float(r["value"]) / 1e9, 2) if r is not None else None,
                     "foreign_net_pct_vol": round(100 * (r["foreign_buy"] - r["foreign_sell"]) / r["volume"], 1) if r is not None and r["volume"] > 0 else None,
                     "bid_queue_share": round(r["bid_volume"] / (r["bid_volume"] + r["offer_volume"]), 2) if r is not None and (r["bid_volume"] + r["offer_volume"]) > 0 else None,
                     "block_value_bn": round(float(r["non_regular_value"]) / 1e9, 2) if r is not None else None,
                     "upper_lock": bool(m.lock_up[n, s])})
    pk = pd.DataFrame(rows)
    j3 = J - 3
    vol = np.where(m.tradeable[n], m.volume[n], np.nan)
    v5 = np.nanmean(vol[j3 - 4: j3 + 1])
    v20 = np.nanmedian(vol[j3 - 24: j3 - 4])
    c20 = np.nanmedian(lv[j3 - 20: j3])
    quiet = bool((v20 > 0 and v5 >= 2 * v20) or lv[j3] >= 1.10 * c20)
    sec = sector_of.get(c["ticker"])
    peers = [i for i, x in enumerate(tick) if sector_of.get(x) == sec and i != n] if sec else []
    sym = [tick[i] for i in peers if np.isfinite(L[i, t]) and np.nanmax(L[i, J: J + 3] / L[i, t]) >= 1.15]
    ca = reg[(reg["ticker"] == c["ticker"]) & (reg["effective_date"] >= str(dates[max(0, t - 5)])) & (reg["effective_date"] <= str(dates[J]))]
    info = {**c, "name": names.get(c["ticker"], ""), "sector_2025": sec, "J_date": str(dates[J]), "J3_date": str(dates[j3]),
            "move_t_to_peak_pct": round(100 * (np.nanmax(lv[t + 1: t + 6]) / lv[t] - 1), 1),
            "J3_vol5_over_med20": round(float(v5 / v20), 2) if v20 > 0 else None,
            "J3_close_over_med20": round(float(lv[j3] / c20), 3), "quiet_buildup_rule": quiet,
            "sector_peers_up15_J_to_J2": sym, "sympathy_rule": len(sym) >= 3,
            "corporate_action_rows": ca[["effective_date", "action_type", "verification_status"]].to_dict("records")}
    summary.append(info)
    (out_dir / f"{c['ticker']}_{c['t_date']}.md").write_text(
        f"# {c['ticker']} {info['name']} (base {c['t_date']}, J {info['J_date']})\n\n```json\n{json.dumps(info, indent=1)}\n```\n\n"
        + pk.to_csv(index=False) + "\n", encoding="utf-8")
with (out_dir / "summary.json").open("x", encoding="utf-8") as fh:
    fh.write(json.dumps(summary, indent=1, default=str) + "\n")
for s in summary:
    print(s["ticker"], s["name"][:28], s["J_date"], s["move_t_to_peak_pct"], "quiet", s["quiet_buildup_rule"], s["J3_vol5_over_med20"],
          s["J3_close_over_med20"], "sym", len(s["sector_peers_up15_J_to_J2"]), "ca", len(s["corporate_action_rows"]))
