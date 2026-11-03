"""PRESSURE_v1 fetch: Binance spot monthly 1d klines for every ticker in NEIGHBOURS_v1 rows, 2020-01..2026-10.
Keeps date, quote volume, taker-buy quote volume. Writes taker.csv.gz and fetch_manifest.json. Resumable via raw/ folder."""
import concurrent.futures as cf, csv, io, json, zipfile, urllib.request, hashlib
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent; NB = HERE.parent / "NEIGHBOURS_v1"
RAW = HERE / "raw"; RAW.mkdir(exist_ok=True)
ticks = sorted(pd.read_csv(NB / "rows.csv.gz", usecols=["ticker"]).ticker.unique())
months = [f"{y}-{m:02d}" for y in range(2020, 2027) for m in range(1, 13) if f"{y}-{m:02d}" <= "2026-10"]
jobs = [(t, mo) for t in ticks for mo in months]
def one(j):
    t, mo = j; f = RAW / f"{t}-{mo}.csv"
    if f.exists(): return j, "cached"
    u = f"https://data.binance.vision/data/spot/monthly/klines/{t}USDT/1d/{t}USDT-1d-{mo}.zip"
    for k in range(3):
        try:
            with urllib.request.urlopen(u, timeout=60) as r: b = r.read()
            z = zipfile.ZipFile(io.BytesIO(b)); rows = list(csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))))
            with f.open("w") as w:
                for x in rows:
                    if not x or not x[0].isdigit(): continue
                    ts = int(x[0]); ts = ts // 1000 if ts > 1e14 else ts
                    w.write(f"{ts},{x[7]},{x[10]}\n")
            return j, "ok"
        except urllib.error.HTTPError as e:
            if e.code == 404: f.write_text(""); return j, "404"
        except Exception: pass
    return j, "fail"
stat = {}
with cf.ThreadPoolExecutor(24) as ex:
    for k, (j, s) in enumerate(ex.map(one, jobs), 1):
        stat[s] = stat.get(s, 0) + 1
        if k % 5000 == 0: print(k, len(jobs), stat, flush=True)
out = []
for f in RAW.glob("*.csv"):
    t = f.name.rsplit("-", 2)[0]
    for line in f.read_text().splitlines():
        ts, qv, tbq = line.split(","); out.append((t, pd.Timestamp(int(ts), unit="ms").date().isoformat(), float(qv), float(tbq)))
d = pd.DataFrame(out, columns=["ticker", "date", "quote_vol", "taker_buy_quote"]).drop_duplicates(["ticker", "date"])
d.to_csv(HERE / "taker.csv.gz", index=False, compression="gzip")
(HERE / "fetch_manifest.json").write_text(json.dumps({"tickers": len(ticks), "jobs": len(jobs), "status": stat, "rows": len(d)}) + "\n")
print("done", len(d), stat)
