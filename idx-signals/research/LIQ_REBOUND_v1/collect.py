"""LIQ_REBOUND_v1 data: Binance USDT-M 5-minute open-interest metrics for BTCUSDT and ETHUSDT, development window only.

Downloads every daily metrics file from the first archived day (BTCUSDT 2020-09-01, ETHUSDT 2021-12-01) to 2023-12-31,
verifies each against the archive's .CHECKSUM (research/E7/collect_perp.py `get`/`listing`, reused unchanged) and
stores it under data/raw/liq_rebound/metrics/ (a separate folder, so E7's pinned files are never overwritten). No file
dated 2024-01-01 or later is requested: the crypto holdout stays sealed for this question.

It also re-verifies the spot hourly klines already on disk (manifest binance_1h-20261015T182940Z.jsonl, BTCUSDT and
ETHUSDT 2020-04..2023-12) and compares the overlapping E7 metrics pins (binance_perp-20261015T191341Z.jsonl), because
the archive's metrics files were regenerated (LastModified 2026-03-18) and are therefore not point-in-time.

    python3 research/LIQ_REBOUND_v1/collect.py            # from idx-signals/
"""

from __future__ import annotations

import concurrent.futures as cf
import hashlib
import importlib.util
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig.provenance import sha256_file, utc_stamp

_spec = importlib.util.spec_from_file_location("e7collect", ROOT / "research/E7/collect_perp.py")
e7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e7)

OUT = ROOT / "data/raw/liq_rebound/metrics"
FIRST = {"BTCUSDT": date(2020, 9, 1), "ETHUSDT": date(2021, 12, 1)}
LAST = date(2023, 12, 31)
SPOT_MANIFEST = ROOT / "data/manifests/binance_1h-20261015T182940Z.jsonl"
E7_MANIFEST = ROOT / "data/manifests/binance_perp-20261015T191341Z.jsonl"
SYMBOLS = ("BTCUSDT", "ETHUSDT")


def days(sym: str) -> list[date]:
    d, out = FIRST[sym], []
    while d <= LAST:
        out.append(d)
        d += timedelta(days=1)
    return out


def fetch(sym: str, day: date) -> dict:
    if day > LAST:
        raise RuntimeError("refusing a file after the development window")
    name = f"{sym}-metrics-{day.isoformat()}.zip"
    path = f"data/futures/um/daily/metrics/{sym}/{name}"
    dest = OUT / sym / name
    try:
        want = e7.get(e7.BASE + path + ".CHECKSUM").decode().split()[0]
    except Exception as exc:  # a day missing from the archive is recorded, never filled
        return {"symbol": sym, "day": day.isoformat(), "status": "missing", "error": str(exc)[:120]}
    if not (dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == want):
        data = e7.get(e7.BASE + path)
        if hashlib.sha256(data).hexdigest() != want:
            raise RuntimeError(f"{name}: checksum mismatch")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    return {
        "symbol": sym,
        "day": day.isoformat(),
        "status": "ok",
        "file": str(dest.relative_to(ROOT / "data/raw")),
        "sha256": want,
    }


def main() -> int:
    started = utc_stamp().replace("-", "").replace(":", "")
    jobs = [(s, d) for s in SYMBOLS for d in days(s)]
    with cf.ThreadPoolExecutor(12) as ex:
        records = list(ex.map(lambda j: fetch(*j), jobs))
    records.sort(key=lambda r: (r["symbol"], r["day"]))

    spot = []
    for line in SPOT_MANIFEST.read_text().splitlines()[1:]:
        r = json.loads(line)
        if r.get("symbol") in SYMBOLS:
            p = ROOT / "data/raw" / r["file"]
            spot.append({**r, "verified": p.exists() and sha256_file(p) == r["sha256"]})
    if not all(r["verified"] for r in spot):
        raise RuntimeError("a pinned hourly kline file is missing or changed")

    e7_pins = {}
    for line in E7_MANIFEST.read_text().splitlines()[1:]:
        r = json.loads(line)
        if r.get("kind") == "metrics" and r["symbol"] in SYMBOLS:
            e7_pins[(r["symbol"], r["file"].rsplit("-metrics-", 1)[1][:10])] = r["sha256"]
    same = differ = 0
    for r in records:
        k = (r["symbol"], r["day"])
        if r["status"] == "ok" and k in e7_pins:
            same += e7_pins[k] == r["sha256"]
            differ += e7_pins[k] != r["sha256"]

    header = {
        "type": "header",
        "study": "LIQ_REBOUND_v1",
        "started": started,
        "finished": utc_stamp(),
        "source": "data.binance.vision futures/um/daily/metrics (5-minute open interest, coin units)",
        "window": {s: [FIRST[s].isoformat(), LAST.isoformat()] for s in SYMBOLS},
        "files_ok": sum(r["status"] == "ok" for r in records),
        "days_missing": [f"{r['symbol']} {r['day']}" for r in records if r["status"] == "missing"],
        "spot_hourly_manifest": SPOT_MANIFEST.name,
        "spot_hourly_files_verified": len(spot),
        "e7_overlap_same_sha256": int(same),
        "e7_overlap_different_sha256": int(differ),
        "point_in_time_note": "archive metrics files were regenerated (LastModified 2026-03-18); values may differ "
        "from what was published in real time",
    }
    man = ROOT / "data/manifests" / f"liq_rebound-{started}.jsonl"
    with man.open("x") as fh:
        fh.write(json.dumps(header) + "\n")
        for r in records:
            fh.write(json.dumps(r) + "\n")
    print(json.dumps(header, indent=1))
    print(man.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
