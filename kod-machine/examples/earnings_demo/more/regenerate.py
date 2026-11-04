"""Rebuild examples/earnings_demo/more/<ticker>/output/ from the frozen files (no network). Run from kod-machine/: python3 examples/earnings_demo/more/regenerate.py"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from kod import earnings  # noqa: E402

HERE = Path(__file__).resolve().parent
NAMES = {
    "amd": ("Advanced Micro Devices, Inc.", "AMD", "XNAS", "2024-10-29T22:00:00Z"),
    "aapl": ("Apple Inc.", "AAPL", "XNAS", "2024-10-31T22:00:00Z"),
    "msft": ("Microsoft Corporation", "MSFT", "XNAS", "2024-10-30T22:00:00Z"),
}
for t, (name, ticker, venue, as_of) in NAMES.items():
    d = HERE / t
    src = json.loads((d / "SOURCES.json").read_text())
    url = {s["role"]: s["url"] for s in src if s["kind"] == "release"}
    ret = {s["role"]: s["retrieved_at_utc_file_mtime"] for s in src if s["kind"] == "release"}
    argv = [
        "--company",
        name,
        "--ticker",
        ticker,
        "--venue",
        venue,
        "--document",
        str(d / "cur.htm"),
        "--source-url",
        url["cur"],
        "--sec-headers",
        str(d / "cur_headers.html"),
        "--retrieved-at",
        ret["cur"],
        "--comparison-document",
        str(d / "pri.htm"),
        "--comparison-source-url",
        url["pri"],
        "--comparison-sec-headers",
        str(d / "pri_headers.html"),
        "--comparison-retrieved-at",
        ret["pri"],
        "--as-of",
        as_of,
        "--mode",
        "public",
        "--out-dir",
        str(d / "output"),
    ]
    if earnings.main(argv):
        raise SystemExit(1)
