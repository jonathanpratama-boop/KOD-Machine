"""Fetch Kenneth French's monthly short-term reversal factor and write data/raw/french/strev_monthly.csv.gz plus a hash
manifest (data/manifests/french_strev-<stamp>.json). Prints counts and dates only, never a value.
Usage (from idx-signals/): python3 research/REVERSAL_1M/fetch.py
"""
import hashlib
import io
import json
import re
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_ST_Reversal_Factor_CSV.zip"
UA = {"User-Agent": "Mozilla/5.0 (KOD-Machine research)"}


def parse(raw_zip: bytes) -> pd.DataFrame:
    """The monthly section only: rows keyed YYYYMM, up to the first blank line or the annual section."""
    z = zipfile.ZipFile(io.BytesIO(raw_zip))
    rows = []
    for ln in z.read(z.namelist()[0]).decode("latin-1").splitlines():
        if re.match(r"^\s*\d{6}\s*,", ln):
            rows.append(re.split(r"\s*,\s*", ln.strip()))
        elif rows and not ln.strip():
            break
    df = pd.DataFrame(rows, columns=["month", "ST_Rev"])
    df["month"] = pd.PeriodIndex(df["month"], freq="M").astype(str)
    return df.set_index("month").astype(float) / 100.0                  # percent -> fraction


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=60) as r:
        raw = r.read()
    df = parse(raw)
    out = ROOT / "data" / "raw" / "french" / "strev_monthly.csv.gz"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out)
    man = {"fetched_at": stamp, "source": URL, "units": "monthly returns as fractions",
           "zip": {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()},
           "parsed": {"path": "data/raw/french/strev_monthly.csv.gz", "rows": int(len(df)), "first": df.index[0],
                      "last": df.index[-1], "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}}
    path = ROOT / "data" / "manifests" / f"french_strev-{stamp}.json"
    path.write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps(man["parsed"], indent=1), path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
