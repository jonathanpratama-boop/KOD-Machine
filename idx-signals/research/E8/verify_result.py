"""Independent check of research/E8/discovery: recompute 25 random events from the raw archive files (not via
idxsig.e8.window) and the week-bootstrap p from the saved rows. Usage (from idx-signals/): python3 -I research/E8/verify_result.py $PWD"""
import io, json, zipfile, sys
import numpy as np, pandas as pd
ROOT = sys.argv[1]
ev = pd.read_csv(f"{ROOT}/research/E8/discovery/events.csv.gz")
s = json.load(open(f"{ROOT}/research/E8/discovery/summary.json"))
man = [json.loads(x) for x in open(f"{ROOT}/data/manifests/binance_1h-20261015T182940Z.jsonl")][1:]
files = {}
for r in man:
    files.setdefault(r["symbol"], {})[r["month"]] = r["file"]
def bars(sym, t0, t1):
    out = []
    for m in pd.period_range(t0.tz_convert(None).to_period("M"), t1.tz_convert(None).to_period("M"), freq="M"):
        fn = files[sym].get(str(m))
        if not fn: continue
        with zipfile.ZipFile(f"{ROOT}/data/raw/{fn}") as z:
            df = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), header=None)
        if not str(df.iloc[0, 0]).isdigit(): df = df.iloc[1:].astype(float)
        out.append(df)
    df = pd.concat(out); df["t"] = pd.to_datetime(df[0].astype("int64"), unit="ms", utc=True)
    df = df.drop_duplicates("t")
    return df[(df.t >= t0) & (df.t <= t1)].set_index("t")
rng = np.random.default_rng(1)
pick = rng.choice(len(ev), 25, replace=False)
bad = 0
for j in pick:
    e = ev.iloc[j]; t = pd.Timestamp(e["time"])
    b = bars(e["peer"], t + pd.Timedelta(hours=1), t + pd.Timedelta(hours=72))
    ent = b.iloc[0][1]; assert b.index[0] == t + pd.Timedelta(hours=1)
    R = b.iloc[-1][4] / ent - 1
    U20 = b[2].max() >= 1.2 * ent
    tp, sl, px, why = 1.2 * ent, 0.9 * ent, None, None
    for _, x in b.iterrows():
        if x[1] <= sl: px, why = x[1], "STOP_GAP"; break
        if x[3] <= sl: px, why = sl, "STOP"; break
        if x[2] >= tp: px, why = tp, "TAKE_PROFIT"; break
    if px is None: px, why = b.iloc[-1][4], "TIMEOUT"
    sl_ = 0.001 if e["liq"] >= 1e7 else 0.002
    net = px * (1 - 0.001 - sl_) / (ent * (1 + 0.001 + sl_)) - 1
    ok = abs(R - e["R72"]) < 1e-9 and U20 == e["U20"] and abs(net - e["net"]) < 1e-9 and why == e["reason"]
    bad += not ok
    if not ok: print("MISMATCH", e["peer"], e["time"], R, e["R72"], net, e["net"], why, e["reason"])
print("independent raw-file recomputation:", len(pick) - bad, "of", len(pick), "match")
# bootstrap statistic from saved rows
ev["excess"] = ev["R72"] - ev["ctrl_R72"]
iso = pd.DatetimeIndex(pd.to_datetime(ev["time"]).dt.tz_convert(None)).isocalendar()
wk = (iso["year"].astype(int) * 100 + iso["week"].astype(int)).to_numpy()
assert (wk == ev["week"].to_numpy()).all()
weeks = np.unique(wk); idx = np.searchsorted(weeks, wk)
S = np.bincount(idx, ev["excess"]); C = np.bincount(idx)
g = np.random.default_rng(20261015).integers(0, len(weeks), (10000, len(weeks)))
stat = S[g].sum(1) / C[g].sum(1)
print("mean excess", ev["excess"].mean(), "saved", s["report"]["information"]["mean_excess"])
print("p", (1 + (stat <= 0).sum()) / 10001, "saved", s["report"]["information"]["vs_controls"]["p_one_sided"])
print("win rate", (ev["net"] > 0).mean(), "U20", ev["U20"].mean(), "ctrl U20", ev["ctrl_U20"].mean())
