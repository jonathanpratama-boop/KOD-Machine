#!/usr/bin/env python3
"""Download Binance public bulk data (data.binance.vision) with a hashed manifest.

Raw files are written OUTSIDE the repository (default /home/claude/data/binance) in line with
KOD-Machine's rule that raw data stays out of git; only the manifest (sha256 per file) is kept
alongside the research. The S3 listing is used so that DELISTED symbols are included: this is
what makes a point-in-time universe possible for cross-sectional tests.

Usage:
  fetch_binance_vision.py list  <market> <datatype> [interval]   # market: spot | um
  fetch_binance_vision.py fetch <market> <datatype> <symbols-file|ALL_USDT> [interval] [start YYYY-MM]
"""
import concurrent.futures as cf
import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

ROOT = os.environ.get("BINANCE_RAW", "/home/claude/data/binance")
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
DL = "https://data.binance.vision/"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"


def s3_list(prefix, delimiter="/"):
    """Return (common prefixes, keys) under prefix, following the 1000-item pagination."""
    prefixes, keys, marker = [], [], None
    while True:
        url = f"{S3}?delimiter={delimiter}&prefix={prefix}"
        if marker:
            url += f"&marker={marker}"
        with urllib.request.urlopen(urllib.parse.quote(url, safe=":/?&=-_."), timeout=60) as r:
            root = ET.fromstring(r.read())
        for p in root.iter(f"{NS}Prefix"):
            if p.text != prefix:
                prefixes.append(p.text)
        for k in root.iter(f"{NS}Key"):
            keys.append(k.text)
        trunc = root.find(f"{NS}IsTruncated")
        if trunc is not None and trunc.text == "true":
            nm = root.find(f"{NS}NextMarker")
            marker = nm.text if nm is not None else (keys[-1] if keys else prefixes[-1])
        else:
            break
    return prefixes, keys


def base_prefix(market, datatype, symbol=None, interval=None):
    m = "spot" if market == "spot" else "futures/um"
    p = f"data/{m}/monthly/{datatype}/"
    if symbol:
        p += f"{symbol}/"
        if interval and datatype == "klines":
            p += f"{interval}/"
    return p


def fetch_one(key, manifest_path):
    dest = os.path.join(ROOT, key)
    if os.path.exists(dest):
        return key, "exists"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(DL + urllib.parse.quote(key), timeout=120) as r:
                data = r.read()
            break
        except Exception as e:  # noqa
            if attempt == 3:
                return key, f"error {e}"
            time.sleep(2 * (attempt + 1))
    with open(dest, "wb") as f:
        f.write(data)
    rec = {"key": key, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
           "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with open(manifest_path, "a") as mf:
        mf.write(json.dumps(rec) + "\n")
    return key, "ok"


def main():
    cmd = sys.argv[1]
    market, datatype = sys.argv[2], sys.argv[3]
    if cmd == "list":
        interval = sys.argv[4] if len(sys.argv) > 4 else None
        prefixes, _ = s3_list(base_prefix(market, datatype))
        syms = [p.rstrip("/").split("/")[-1] for p in prefixes]
        print("\n".join(syms))
        return
    symbols_arg = sys.argv[4]
    interval = sys.argv[5] if len(sys.argv) > 5 and datatype == "klines" else None
    start = sys.argv[6] if len(sys.argv) > 6 else (sys.argv[5] if datatype != "klines" and len(sys.argv) > 5 else "2017-01")
    if symbols_arg == "ALL_USDT":
        prefixes, _ = s3_list(base_prefix(market, datatype))
        symbols = [p.rstrip("/").split("/")[-1] for p in prefixes]
        symbols = [s for s in symbols if s.isascii() and s.isalnum() and s.endswith("USDT") and not any(x in s for x in ("UP", "DOWN", "BULL", "BEAR")) or s in ("BTCUSDT",)]
    else:
        symbols = [l.strip() for l in open(symbols_arg) if l.strip()]
    os.makedirs(ROOT, exist_ok=True)
    tag = f"{market}_{datatype}_{interval or 'na'}"
    manifest_path = os.path.join(ROOT, f"manifest_{tag}.jsonl")
    keys = []
    def list_sym(s):
        _, ks = s3_list(base_prefix(market, datatype, s, interval))
        return [k for k in ks if k.endswith(".zip") and k.split("-")[-2] + "-" + k.split("-")[-1][:2] >= start]
    with cf.ThreadPoolExecutor(12) as ex:
        for ks in ex.map(list_sym, symbols):
            keys.extend(ks)
    print(f"{len(symbols)} symbols, {len(keys)} files to fetch -> {ROOT}", file=sys.stderr)
    counts = {}
    with cf.ThreadPoolExecutor(16) as ex:
        for i, (k, st) in enumerate(ex.map(lambda k: fetch_one(k, manifest_path), keys)):
            counts[st.split()[0]] = counts.get(st.split()[0], 0) + 1
            if i % 500 == 0:
                print(i, counts, file=sys.stderr)
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
