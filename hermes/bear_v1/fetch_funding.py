"""Fetch Binance USDT-M perpetual funding-rate monthly archives (data.binance.vision) for the bear-market study.
Raw zips kept as retrieved; a manifest records URL, HTTP status and size for every file (missing files are not silently ignored)."""
import os, re, subprocess, json, concurrent.futures as cf, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); RAW = os.path.join(HERE, "raw_funding"); os.makedirs(RAW, exist_ok=True)
BASE = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
def ls(prefix):
    out, marker = [], ""
    while True:
        x = subprocess.run(["curl", "-s", "--retry", "3", f"{BASE}?prefix={prefix}&delimiter=/&marker={marker}"], capture_output=True, text=True).stdout
        pre = re.findall(r"<Prefix>([^<]+)</Prefix>", x)[1:]; keys = re.findall(r"<Key>([^<]+)</Key>", x)
        out += pre + keys
        if "<IsTruncated>true</IsTruncated>" not in x: return out
        marker = (keys or pre)[-1]
syms = [p.rstrip("/").split("/")[-1] for p in ls("data/futures/um/monthly/fundingRate/")]
syms = [s for s in syms if s.endswith("USDT")]
print("symbols", len(syms), flush=True)
keys = []
with cf.ThreadPoolExecutor(32) as ex:
    for ks in ex.map(lambda s: [k for k in ls(f"data/futures/um/monthly/fundingRate/{s}/") if k.endswith(".zip")], syms): keys += ks
print("files", len(keys), flush=True)
def get(k):
    fp = os.path.join(RAW, os.path.basename(k))
    if os.path.exists(fp) and os.path.getsize(fp) > 0: return k, 200, os.path.getsize(fp)
    r = subprocess.run(["curl", "-s", "-f", "--retry", "3", "-o", fp, "-w", "%{http_code}", f"https://data.binance.vision/{k}"], capture_output=True, text=True)
    return k, int(r.stdout or 0), os.path.getsize(fp) if os.path.exists(fp) else 0
man = []
with cf.ThreadPoolExecutor(48) as ex:
    for m in ex.map(get, keys): man.append(m)
json.dump(dict(retrieved_utc=dt.datetime.utcnow().isoformat() + "Z", symbols=len(syms), files=len(keys),
               ok=sum(1 for m in man if m[1] == 200), failed=[m for m in man if m[1] != 200]), open(os.path.join(HERE, "raw_funding_manifest.json"), "w"), indent=1)
print("done ok", sum(1 for m in man if m[1] == 200), "failed", sum(1 for m in man if m[1] != 200), flush=True)
