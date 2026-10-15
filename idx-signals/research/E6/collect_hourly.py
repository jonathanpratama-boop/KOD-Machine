"""E6 data: Binance spot 1h klines (with taker-buy volume) from data.binance.vision, 2020-04 .. 2023-12.

Survivorship: the universe is every USDT symbol directory in the public archive, delisted ones
included, minus stablecoins, fiat and leveraged tokens (idxsig.global_panel.STABLE / LEVERAGED).
Holdout: no month after 2023-12 is listed, downloaded or read (crypto holdout = 2024 onward).
Each zip is verified against the archive's own .CHECKSUM file; files go to data/raw/binance_1h/
(gitignored) and a manifest with the sha256 of every file goes to data/manifests/.
Usage: python3 research/E6/collect_hourly.py   (network; resumable)
"""
import concurrent.futures as cf, hashlib, json, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig.global_panel import LEVERAGED, STABLE  # noqa: E402

BASE = "https://data.binance.vision/"
LIST = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?delimiter=/&prefix="
FIRST, LAST = "2020-04", "2023-12"  # 3 months of warm-up before 2020-07; nothing from the holdout
OUT = ROOT / "data" / "raw" / "binance_1h"


def get(url, tries=4):
    for k in range(tries):
        try:
            return urllib.request.urlopen(urllib.parse.quote(url, safe=":/?&=.-_~%"), timeout=60).read()
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(2 ** k)


def listing(prefix, tag):
    out, marker = [], ""
    while True:
        x = get(LIST + prefix + (f"&marker={marker}" if marker else "")).decode()
        out += re.findall(rf"<{tag}>{re.escape(prefix)}([^<]+)</{tag}>", x)
        m = re.search(r"<NextMarker>(.*?)</NextMarker>", x)
        if not m:
            return out
        marker = m.group(1)


def months_of(sym):
    keys = listing(f"data/spot/monthly/klines/{sym}/1h/", "Key")
    ms = sorted({k[len(sym) + 4:len(sym) + 11] for k in keys if k.endswith(".zip")})
    return [m for m in ms if FIRST <= m <= LAST]


def fetch(sym, month):
    name = f"{sym}-1h-{month}.zip"
    dest = OUT / sym / name
    url = f"{BASE}data/spot/monthly/klines/{sym}/1h/{name}"
    want = get(url + ".CHECKSUM").decode().split()[0]
    if not (dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == want):
        data = get(url)
        got = hashlib.sha256(data).hexdigest()
        if got != want:
            raise RuntimeError(f"{name}: checksum {got} != archive {want}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    return {"symbol": sym, "month": month, "file": f"binance_1h/{sym}/{name}", "sha256": want, "url": url}


def main():
    started = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dirs = [d.rstrip("/") for d in listing("data/spot/monthly/klines/", "Prefix")]
    usdt = sorted(s for s in dirs if s.endswith("USDT"))
    excluded = [s for s in usdt if s[:-4] in STABLE or LEVERAGED.search(s[:-4])]
    universe = [s for s in usdt if s not in excluded]
    with cf.ThreadPoolExecutor(16) as ex:
        months = dict(zip(universe, ex.map(months_of, universe)))
    jobs = [(s, m) for s in universe for m in months[s]]
    print(f"{len(usdt)} USDT symbols, {len(excluded)} excluded, {len(universe)} kept, "
          f"{sum(1 for s in universe if months[s])} with months in {FIRST}..{LAST}, {len(jobs)} files", flush=True)
    records, failures = [], []
    with cf.ThreadPoolExecutor(16) as ex:
        futs = {ex.submit(fetch, s, m): (s, m) for s, m in jobs}
        for i, f in enumerate(cf.as_completed(futs), 1):
            try:
                records.append(f.result())
            except Exception as e:
                failures.append({"symbol": futs[f][0], "month": futs[f][1], "error": str(e)[:200]})
            if i % 1000 == 0:
                print(f"{i}/{len(jobs)}", flush=True)
    records.sort(key=lambda r: (r["symbol"], r["month"]))
    man = ROOT / "data" / "manifests" / f"binance_1h-{started}.jsonl"
    with man.open("w") as fh:
        fh.write(json.dumps({"type": "header", "source": "data.binance.vision spot monthly 1h klines",
                             "started": started, "months": [FIRST, LAST], "usdt_symbols": len(usdt),
                             "excluded": excluded, "universe": len(universe), "files": len(records),
                             "failures": failures, "holdout": "nothing after 2023-12 listed or fetched"}) + "\n")
        for r in records:
            fh.write(json.dumps(r) + "\n")
    print(f"manifest {man.name}: {len(records)} files, {len(failures)} failures")


if __name__ == "__main__":
    main()
