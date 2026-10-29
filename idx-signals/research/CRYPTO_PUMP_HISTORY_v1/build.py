"""CRYPTO_PUMP_HISTORY_v1 build: hourly klines of every Binance BTC pair, months 2017-07..2022-02, from the public archive.
Each monthly zip is checked against its .CHECKSUM, parsed, and folded into data/raw/binance_pumps/<PAIR>.npz (git-ignored;
zips are not kept). Resumable per pair. `--manifest` hashes the pair files into results/PRICE_MANIFEST.json. Also fetches
the two unlicensed event lists into data/raw/pumps/ and checks them against SOURCES.json. Reads no outcome."""
from __future__ import annotations

import concurrent.futures as cf
import csv
import hashlib
import io
import json
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "data" / "raw" / "binance_pumps"
CACHE = ROOT / "data" / "raw" / "pumps"
BASE = "https://data.binance.vision/data/spot/monthly/klines"
FIRST, LAST = "2017-07", "2022-02"


def get(url: str) -> bytes | None:
    for k in range(6):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(3 * (k + 1))
        except Exception:
            time.sleep(3 * (k + 1))
    raise RuntimeError(f"giving up on {url}")


def month(pair: str, ym: str) -> np.ndarray | None:
    name = f"{pair}-1h-{ym}.zip"
    blob = get(f"{BASE}/{pair}/1h/{name}")
    if blob is None:
        return None
    chk = get(f"{BASE}/{pair}/1h/{name}.CHECKSUM")
    if chk is not None and chk.split()[0].decode() != hashlib.sha256(blob).hexdigest():
        raise RuntimeError(f"{name}: checksum mismatch")
    rows = []
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for line in csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), "utf-8")):
            if not line or not line[0].isdigit():
                continue
            t = int(line[0])
            t = t // 1000 if t > 10 ** 14 else t  # microsecond files (2025 on) never occur here; guard anyway
            rows.append((t // 3_600_000, float(line[2]), float(line[3]), float(line[4]), float(line[7]), float(line[8])))
    return np.array(rows, dtype=float) if rows else None


def pair_file(pair: str, months: list[str]) -> str:
    path = OUT / f"{pair}.npz"
    if path.exists():
        return f"{pair} cached"
    parts = [m for m in (month(pair, ym) for ym in months if FIRST <= ym <= LAST) if m is not None]
    if not parts:
        a = np.zeros((0, 6))
    else:
        a = np.concatenate(parts)
        a = a[np.unique(a[:, 0], return_index=True)[1]]
    tmp = path.with_suffix(".tmp.npz")
    np.savez_compressed(tmp, hour=a[:, 0].astype(np.int64), high=a[:, 1], low=a[:, 2], close=a[:, 3], qvol=a[:, 4],
                        trades=a[:, 5])
    tmp.rename(path)
    return f"{pair} {len(a)} bars"


def lists() -> None:
    src = json.loads((HERE / "SOURCES.json").read_text())
    CACHE.mkdir(parents=True, exist_ok=True)
    for name, fname in (("ardia", "ardia.csv"), ("bayi_hu", "bayi.txt")):
        p = CACHE / fname
        if not p.exists():
            p.write_bytes(get(src[name]["url"]))
        if hashlib.sha256(p.read_bytes()).hexdigest() != src[name]["sha256"]:
            raise RuntimeError(f"{fname} differs from SOURCES.json")


def manifest() -> int:
    avail = json.loads((HERE / "results" / "archive_months.json").read_text())
    files = {}
    for pair in sorted(avail):
        p = OUT / f"{pair}.npz"
        if not p.exists():
            sys.exit(f"error: {pair} not built yet")
        files[pair] = hashlib.sha256(p.read_bytes()).hexdigest()
    (HERE / "results" / "PRICE_MANIFEST.json").write_text(json.dumps({"source": BASE, "interval": "1h", "months": [FIRST, LAST],
                                                                      "pairs": files}, indent=0) + "\n")
    print(f"manifest: {len(files)} pairs")
    return 0


def main() -> int:
    if "--manifest" in sys.argv:
        return manifest()
    lists()
    OUT.mkdir(parents=True, exist_ok=True)
    avail = json.loads((HERE / "results" / "archive_months.json").read_text())
    with cf.ThreadPoolExecutor(6) as ex:
        for msg in ex.map(lambda kv: pair_file(*kv), sorted(avail.items())):
            print(msg, flush=True)
    print("BUILD DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
