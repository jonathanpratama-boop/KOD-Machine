"""Build hourly panel from Binance spot 1h monthly zips (discovery window 2020-2022 only).
Writes out/panel_1h.parquet (or .pkl) and out/build_log.json with per-file hashes and failures."""
import zipfile, io, json, hashlib, glob, os, sys
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "raw", "k1h")
OUT = os.path.join(ROOT, "out")
cols = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_vol",
        "trades", "taker_base", "taker_quote", "ignore"]
frames, log = [], {"files": {}, "failures": []}
for fp in sorted(glob.glob(os.path.join(RAW, "*.zip"))):
    name = os.path.basename(fp)
    sym = name.split("-1h-")[0]
    try:
        b = open(fp, "rb").read()
        log["files"][name] = hashlib.sha256(b).hexdigest()
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            raw = z.read(z.namelist()[0])
        df = pd.read_csv(io.BytesIO(raw), header=None, names=cols)
        if not str(df.iloc[0, 0]).isdigit():  # header row present in some files
            df = df.iloc[1:]
        df = df[["open_time", "open", "high", "low", "close", "quote_vol", "trades"]].astype(float)
        df["sym"] = sym
        frames.append(df)
    except Exception as e:
        log["failures"].append({"file": name, "error": repr(e)})
p = pd.concat(frames, ignore_index=True)
p["open_time"] = p["open_time"].astype("int64")
# guard: microsecond timestamps (Binance changed format in 2025) -> should not appear here
assert p["open_time"].max() < 2e12, "unexpected microsecond timestamps"
p["ts"] = pd.to_datetime(p["open_time"], unit="ms", utc=True)
p = p.drop_duplicates(["sym", "open_time"]).sort_values(["sym", "open_time"]).reset_index(drop=True)
assert p["ts"].max() < pd.Timestamp("2023-01-01", tz="UTC"), "data beyond discovery window"
p.to_pickle(os.path.join(OUT, "panel_1h.pkl"))
log.update(rows=len(p), symbols=int(p["sym"].nunique()), ts_min=str(p["ts"].min()), ts_max=str(p["ts"].max()),
           n_files=len(log["files"]), n_failures=len(log["failures"]))
json.dump(log, open(os.path.join(OUT, "build_log.json"), "w"), indent=1)
print({k: v for k, v in log.items() if k not in ("files",)})
