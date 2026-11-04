"""VIX_BASIS_v1 data: Cboe's own daily VIX futures (VX) records per monthly contract, and the VIX and SPX index histories.

Free public files from cdn.cboe.com (no log-in). Monthly VX contracts expiring Jan 2006 .. Feb 2024 (Jan and Feb 2024 are
needed only for their rows up to 2023-12-29, when they are the front contracts). Each file is stored under
data/raw/cboe/ and pinned in a manifest. This script reads no price: it checks only that each file is a CSV with the
expected header. The US/crypto holdout (2024-01-01 .. 2026-12-31) is sealed: some raw files contain rows dated in it,
and the study's loader drops every row dated 2024-01-01 or later at parse time, before any use (as MSCI_DELETION_v1 does
with the IDX panel).

    python3 research/VIX_BASIS_v1/collect.py        # from idx-signals/
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig.provenance import utc_stamp

OUT = ROOT / "data/raw/cboe"
MAN = ROOT / "data/manifests"
CODES = "FGHJKMNQUVXZ"
ARCHIVE = "https://cdn.cboe.com/resources/futures/archive/volume-and-price/CFE_{code}{yy}_VX.csv"
CURRENT = "https://cdn.cboe.com/data/us/futures/market_statistics/historical_data/VX/VX_{date}.csv"
INDEX = {
    "VIX": "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv",
    "SPX": "https://cdn.cboe.com/api/global/us_indices/daily_prices/SPX_History.csv",
}
FIRST, LAST = (2006, 1), (2024, 2)  # contract months (expiry month)
VX_HEADER = b"Trade Date,Futures,"


def get(url: str) -> bytes | None:
    """The body, or None for a 403/404 (Cboe answers 403 for a file that does not exist)."""
    for k in range(4):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "KOD-research/1.0"}
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return None
            if k == 3:
                raise
        except Exception:
            if k == 3:
                raise
        time.sleep(2**k)
    raise RuntimeError("unreachable")


def third_friday(year: int, month: int) -> dt.date:
    d = dt.date(year, month, 15)
    return d + dt.timedelta(days=(4 - d.weekday()) % 7)


def nominal_expiry(year: int, month: int) -> dt.date:
    """The Wednesday 30 days before the third Friday of the following month (holiday shifts not applied; the
    collector tries nearby dates when Cboe's current-format file name differs)."""
    ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
    return third_friday(ny, nm) - dt.timedelta(days=30)


def months():
    y, m = FIRST
    while (y, m) <= LAST:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def fetch_contract(y: int, m: int) -> tuple[str, bytes]:
    url = ARCHIVE.format(code=CODES[m - 1], yy=f"{y % 100:02d}")
    body = get(url)
    if body and body.startswith(VX_HEADER):
        return url, body
    base = nominal_expiry(y, m)
    for off in (0, -1, 1, -2, 2, -7, 7):
        url = CURRENT.format(date=(base + dt.timedelta(days=off)).isoformat())
        body = get(url)
        if body and body.startswith(VX_HEADER):
            return url, body
    raise RuntimeError(f"no VX file found for {y}-{m:02d}")


def main() -> int:
    started = utc_stamp().replace("-", "").replace(":", "")
    (OUT / "vx").mkdir(parents=True, exist_ok=True)
    recs = []
    for y, m in months():
        url, body = fetch_contract(y, m)
        dest = OUT / "vx" / f"VX_{y}-{m:02d}.csv"
        dest.write_bytes(body)
        recs.append(
            {
                "kind": "VX",
                "contract": f"{y}-{m:02d}",
                "url": url,
                "file": str(dest.relative_to(ROOT / "data/raw")),
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
            }
        )
        print(f"VX {y}-{m:02d} {len(body)} bytes {url.rsplit('/', 1)[1]}")
    for name, url in INDEX.items():
        body = get(url)
        if not body or not body.startswith(b"DATE,"):
            raise RuntimeError(f"{url}: unexpected content")
        dest = OUT / f"{name}_History.csv"
        dest.write_bytes(body)
        recs.append(
            {
                "kind": name,
                "url": url,
                "file": str(dest.relative_to(ROOT / "data/raw")),
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
            }
        )
        print(f"{name} {len(body)} bytes")
    MAN.mkdir(parents=True, exist_ok=True)
    out = MAN / f"cboe_vx-{started}.jsonl"
    head = {
        "type": "header",
        "study": "VIX_BASIS_v1",
        "started": started,
        "source": "Cboe public historical data (cdn.cboe.com): VX per contract, VIX and SPX daily",
        "files": len(recs),
        "sealed_rows": "rows dated 2024-01-01 or later exist in some files and are dropped at parse time",
    }
    out.write_text("\n".join(json.dumps(r) for r in [head, *recs]) + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
