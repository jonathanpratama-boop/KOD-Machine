"""Independent check of results/ (not via idxsig.exit_atr or idxsig.e6).

For 40 random signal trades and 20 random control trades it rebuilds, from the raw daily panel and the raw
monthly Binance zip files: the ATR, the hourly window, the trailing stop path (a separate implementation) and
the primary-cost net returns of both arms. It also reproduces the paired-improvement bootstrap from the saved
ledger and counts trades whose stop fired on the first bar after a missing hour (the conservative-gap case).
Usage (from idx-signals/): python3 -I research/EXIT_ATR_v1/cloud/verify_result.py <idx-signals path>
"""
import io, json, sys, zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(sys.argv[1])
C = ROOT / "research" / "EXIT_ATR_v1" / "cloud"
R = C / "results"
T = pd.read_csv(R / "trades.csv.gz", dtype={"ticker": str}, keep_default_na=False, na_values=[""])
K = pd.read_csv(R / "controls.csv.gz", dtype={"ticker": str}, keep_default_na=False, na_values=[""])
res = json.loads((R / "RESULT.json").read_text())
proto = json.loads((C / "protocol.json").read_text())
c = proto["costs"]["per_side"]["primary"]
P = pd.read_csv(ROOT / "data/panel/panel_crypto-20261008T003354Z.csv.gz", usecols=["date", "ticker", "high", "low", "close"],
                parse_dates=["date"], dtype={"ticker": str}, keep_default_na=False, na_values=[""])
man = [json.loads(x) for x in (ROOT / "data/manifests/binance_1h-20261015T182940Z.jsonl").read_text().splitlines()[1:]]
files = {}
for r in man:
    files.setdefault(r["symbol"], {})[r["month"]] = r["file"]


def hourly(sym, a, b):
    out = []
    for m in pd.period_range(a.to_period("M"), b.to_period("M"), freq="M"):
        f = files[sym].get(str(m))
        if f is None:
            continue
        if str(m) > "2022-12":
            raise SystemExit("would read beyond the research boundary")
        with zipfile.ZipFile(ROOT / "data/raw" / f) as z:
            df = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), header=None)
        if not str(df.iloc[0, 0]).isdigit():
            df = df.iloc[1:].astype(float)
        out.append(df)
    df = pd.concat(out)
    df["t"] = pd.to_datetime(df[0].astype("int64"), unit="ms")
    df = df.drop_duplicates("t").set_index("t").sort_index()
    return df[(df.index >= a) & (df.index <= b)]


def atr(t, s):
    g = P[(P.ticker == t) & (P.date >= s - pd.Timedelta(days=14)) & (P.date <= s)].sort_values("date")
    assert len(g) == 15
    pc = g.close.shift(1)
    tr = pd.concat([g.high - g.low, (g.high - pc).abs(), (g.low - pc).abs()], axis=1).max(axis=1).iloc[1:]
    return tr.mean()


def replay(ticker, entry_date, exit_date, entry, a, exit_A):
    e0 = pd.Timestamp(entry_date)
    b = hourly(ticker + "USDT", e0, pd.Timestamp(exit_date) + pd.Timedelta(hours=23))
    stop, hi, gap_first = entry - 3 * a, entry, False
    expect = e0
    for t, x in b.iterrows():
        after_gap = t > expect
        expect = t + pd.Timedelta(hours=1)
        o, h, l = x[1], x[2], x[3]
        if o <= stop:
            return o, "STOP_GAP", after_gap
        if l <= stop:
            return stop, "STOP", after_gap
        hi = max(hi, h)
        stop = max(stop, hi - 3 * a)
    return exit_A, "NOT_STOPPED", False


net = lambda e, x: x * (1 - c) / (e * (1 + c)) - 1
rng = np.random.default_rng(7)
bad, n = 0, 0
for df, k, label in ((T, 40, "signal"), (K, 20, "control")):
    for i in rng.choice(len(df), k, replace=False):
        r = df.iloc[i]
        a = atr(r.ticker, pd.Timestamp(r.signal_date))
        el = None
        if label == "control":
            el = pd.read_csv(C / "eligibility" / "eligibility.csv.gz", usecols=["arm", "j", "draw", "entry_date", "exit_date_original"])
            el = el[(el.arm == "control") & (el.j == r.j) & (el.draw == r.draw)].iloc[0]
            ed, xd = el.entry_date, el.exit_date_original
        else:
            ed, xd = r.entry_date, r.exit_date_original
        px, why, _ = replay(r.ticker, ed, xd, r.entry_price, a, r.exit_price_A)
        ok = (abs(a / r.atr - 1) < 1e-10 and why == r.reason and abs(px / r.exit_price_B - 1) < 1e-10  # ledger keeps 12 digits
              and abs(net(r.entry_price, px) - r.net_B_primary) < 1e-9
              and abs(net(r.entry_price, r.exit_price_A) - r.net_A_primary) < 1e-9)
        n += 1
        bad += not ok
        if not ok:
            print("MISMATCH", label, r.ticker, r.signal_date, why, r.reason, px, r.exit_price_B, a, r.atr)
print(f"independent replay: {n - bad} of {n} trades match (ATR, exit reason, exit price, both nets)")

# conservative-gap case: stopped trades whose stop bar came right after a missing hour (signals)
cnt = 0
for r in T[(T.reason != "NOT_STOPPED") & (T.coverage == "GAPS")].itertuples():
    _, _, ag = replay(r.ticker, r.entry_date, r.exit_date_original, r.entry_price, r.atr, r.exit_price_A)
    cnt += bool(ag)
print("signal trades stopped on the first bar after a gap:", cnt,
      "| stopped trades with gaps:", int(((T.reason != "NOT_STOPPED") & (T.coverage == "GAPS")).sum()))

# paired bootstrap from the saved ledger
d = T.net_B_primary - T.net_A_primary
weeks = np.array(sorted(T.week.unique()))
w = np.searchsorted(weeks, T.week)
S, N = np.bincount(w, d), np.bincount(w).astype(float)
pick = np.random.default_rng(proto["statistics"]["seed"]).integers(0, len(weeks), (proto["statistics"]["resamples"], len(weeks)))
st = S[pick].sum(1) / N[pick].sum(1)
got = [float(np.percentile(st, 2.5)), float(np.percentile(st, 97.5))]
print("paired mean", float(d.mean()), "ci", got, "| saved", res["paired_improvement_primary"]["mean"], res["paired_improvement_primary"]["ci95"])
print("ledger rows", len(T), "controls", len(K), "| NOT_STOPPED identical:", int((d.abs() < 1e-15).sum()),
      "==", int((T.reason == "NOT_STOPPED").sum()))
