"""E7 feasibility data: Binance USDT-M perpetual funding (monthly) and open-interest metrics (daily, 5-minute),
for perps whose spot pair is in the E6 spot universe. Discovery window plus look-back only:
funding 2021-11..2022-12, metrics 2021-11-24..2022-12-31. 2023 is LISTED (file counts per symbol), never
downloaded. Every file is verified against the archive's .CHECKSUM.
Usage (from idx-signals/): python3 research/E7/collect_perp.py data/manifests/binance_1h-20261015T182940Z.jsonl
"""
import concurrent.futures as cf, hashlib, json, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://data.binance.vision/"
LIST = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?delimiter=/&prefix="
OUT = ROOT / "data" / "raw" / "binance_perp"
F_FIRST, F_LAST = "2021-11", "2022-12"
M_FIRST, M_LAST = "2021-11-24", "2022-12-31"


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
        x = get(LIST + prefix + (f"&marker={urllib.parse.quote(marker)}" if marker else "")).decode()
        out += re.findall(rf"<{tag}>{re.escape(prefix)}([^<]+)</{tag}>", x)
        m = re.search(r"<NextMarker>(.*?)</NextMarker>", x)
        if not m:
            return out
        marker = m.group(1)


def fetch(kind, sym, name):
    path = f"data/futures/um/{'monthly' if kind == 'fundingRate' else 'daily'}/{kind}/{sym}/{name}"
    dest = OUT / kind / sym / name
    want = get(BASE + path + ".CHECKSUM").decode().split()[0]
    if not (dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == want):
        data = get(BASE + path)
        if hashlib.sha256(data).hexdigest() != want:
            raise RuntimeError(f"{name}: checksum mismatch")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    return {"kind": kind, "symbol": sym, "file": f"binance_perp/{kind}/{sym}/{name}", "sha256": want}


def main(spot_manifest):
    started = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    spot = {json.loads(l)["symbol"] for l in Path(spot_manifest).read_text().splitlines()[1:]}
    perps = {s.rstrip("/") for s in listing("data/futures/um/monthly/fundingRate/", "Prefix")}
    syms = sorted(spot & perps)

    def keys(sym):
        f = [k for k in listing(f"data/futures/um/monthly/fundingRate/{sym}/", "Key") if k.endswith(".zip")]
        m = [k for k in listing(f"data/futures/um/daily/metrics/{sym}/", "Key") if k.endswith(".zip")]
        return sym, f, m

    with cf.ThreadPoolExecutor(16) as ex:
        lists = list(ex.map(keys, syms))
    jobs, coverage = [], {}
    for sym, f, m in lists:
        fm = sorted(k[-11:-4] for k in f)                      # YYYY-MM
        md = sorted(k[-14:-4] for k in m)                      # YYYY-MM-DD
        coverage[sym] = {"funding_first": fm[0] if fm else None, "funding_last": fm[-1] if fm else None,
                         "metrics_first": md[0] if md else None, "metrics_last": md[-1] if md else None,
                         "funding_files_2023_listed": sum(1 for x in fm if x.startswith("2023")),
                         "metrics_files_2023_listed": sum(1 for x in md if x.startswith("2023"))}
        jobs += [("fundingRate", sym, f"{sym}-fundingRate-{x}.zip") for x in fm if F_FIRST <= x <= F_LAST]
        jobs += [("metrics", sym, f"{sym}-metrics-{x}.zip") for x in md if M_FIRST <= x <= M_LAST]
    print(f"{len(spot)} spot symbols, {len(perps)} perps, {len(syms)} overlap, {len(jobs)} files", flush=True)
    records, failures = [], []
    with cf.ThreadPoolExecutor(24) as ex:
        futs = {ex.submit(fetch, *j): j for j in jobs}
        for i, fu in enumerate(cf.as_completed(futs), 1):
            try:
                records.append(fu.result())
            except Exception as e:
                failures.append({"job": futs[fu], "error": str(e)[:200]})
            if i % 5000 == 0:
                print(f"{i}/{len(jobs)}", flush=True)
    records.sort(key=lambda r: (r["kind"], r["symbol"], r["file"]))
    man = ROOT / "data" / "manifests" / f"binance_perp-{started}.jsonl"
    with man.open("w") as fh:
        fh.write(json.dumps({"type": "header", "started": started, "funding_months": [F_FIRST, F_LAST],
                             "metrics_days": [M_FIRST, M_LAST], "spot_manifest": Path(spot_manifest).name,
                             "overlap_symbols": syms, "coverage": coverage, "files": len(records), "failures": failures,
                             "note": "2023 coverage is from archive listings only; no 2023 file was downloaded"}) + "\n")
        for r in records:
            fh.write(json.dumps(r) + "\n")
    print(f"manifest {man.name}: {len(records)} files, {len(failures)} failures")


if __name__ == "__main__":
    main(sys.argv[1])
