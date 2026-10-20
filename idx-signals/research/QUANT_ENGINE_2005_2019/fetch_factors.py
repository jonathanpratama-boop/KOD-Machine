"""Fetch Kenneth French's daily factor files (market, size, value, momentum, risk-free) and write data/raw/french/factors_daily.csv.gz
plus a hash manifest (data/manifests/french_factors-<stamp>.json). Reference data only; no strategy return is read.
Usage (from idx-signals/): python3 research/QUANT_ENGINE_2005_2019/fetch_factors.py
"""
import gzip
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
BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
FILES = {"ff3": "F-F_Research_Data_Factors_daily_CSV.zip", "mom": "F-F_Momentum_Factor_daily_CSV.zip"}
UA = {"User-Agent": "Mozilla/5.0 (KOD-Machine research)"}


def parse(raw_zip: bytes, names: list[str]) -> pd.DataFrame:
    z = zipfile.ZipFile(io.BytesIO(raw_zip))
    text = z.read(z.namelist()[0]).decode("latin-1")
    rows = [re.split(r"\s*,\s*", ln.strip()) for ln in text.splitlines() if re.match(r"^\s*\d{8}\s*,", ln)]
    df = pd.DataFrame(rows, columns=["date"] + names)
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    return df.set_index("date").astype(float)


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raws, parts = {}, []
    for key, name in FILES.items():
        with urllib.request.urlopen(urllib.request.Request(BASE + name, headers=UA), timeout=60) as r:
            raws[key] = r.read()
    ff3 = parse(raws["ff3"], ["Mkt-RF", "SMB", "HML", "RF"])
    mom = parse(raws["mom"], ["MOM"])
    df = ff3.join(mom, how="inner") / 100.0                    # percent -> fraction
    out = ROOT / "data" / "raw" / "french" / "factors_daily.csv.gz"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out)
    man = {"fetched_at": stamp, "source": BASE, "units": "daily returns as fractions",
           "zips": {k: {"file": FILES[k], "bytes": len(v), "sha256": hashlib.sha256(v).hexdigest()} for k, v in raws.items()},
           "parsed": {"path": "data/raw/french/factors_daily.csv.gz", "rows": int(len(df)), "first": str(df.index[0].date()),
                      "last": str(df.index[-1].date()), "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}}
    path = ROOT / "data" / "manifests" / f"french_factors-{stamp}.json"
    path.write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps(man["parsed"], indent=1), path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
