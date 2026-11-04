"""MSCI_DELETION_v1: build events.csv from the pinned MSCI PDFs (no price is read).

For each review Nov 2019 .. Nov 2023 and each segment (ST = MSCI Indonesia Standard index, SC = MSCI Indonesia Small Cap index),
parse the "MSCI INDONESIA INDEX" additions/deletions block of the public list, and from the review's press release the
announcement date and the implementation close ("All changes will be implemented as of the close of <date>").

A DELETION event is a name leaving a segment. Classification per review:
  - ST_EXIT: deleted from Standard and not added to Small Cap in the same review
  - ST_TO_SC: deleted from Standard and added to Small Cap (a downward migration; Standard trackers sell, Small Cap trackers,
    a much smaller pool, buy)
  - SC_EXIT: deleted from Small Cap and not added to Standard (leaves the investable index or moves to Micro Cap)
  - SC_TO_ST: deleted from Small Cap because it was added to Standard: an UPWARD migration, net buying - not a deletion here.
Names come from MSCI (no tickers); research/MSCI_DELETION_v1/ticker_map.csv maps each MSCI name to its IDX code by hand,
with a note for every uncertain case.

    python3 research/MSCI_DELETION_v1/build_events.py      # from idx-signals/
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MANIFEST = ROOT / "data/manifests/msci_lists-20261031T235555Z.jsonl"


def text(path: Path) -> str:
    return subprocess.run(
        ["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, check=True
    ).stdout


def indonesia_block(doc: str) -> tuple[list[str], list[str]]:
    """(additions, deletions) of the 'MSCI INDONESIA INDEX' block, split at the 'Deletions' column."""
    lines = doc.splitlines()
    k = next((i for i, x in enumerate(lines) if x.strip() == "MSCI INDONESIA INDEX"), None)
    if k is None:
        return [], []
    head = lines[k + 1]
    if "Additions" not in head or "Deletions" not in head:
        raise ValueError("unexpected Indonesia block header")
    col = head.index("Deletions")
    adds, dels = [], []
    for x in lines[k + 2 :]:
        if not x.strip():
            break
        a, d = x[:col].strip(), x[col:].strip()
        if a and a != "None":
            adds.append(a)
        if d and d != "None":
            dels.append(d)
    return adds, dels


def indonesia_summary(doc: str) -> tuple[int, int] | None:
    """MSCI's own per-country summary row ('INDONESIA <added> <deleted>'), or None when Indonesia has no change."""
    m = re.search(r"^\s*INDONESIA\s+(\d+)\s+(\d+)\s*$", doc, re.MULTILINE)
    return (int(m.group(1)), int(m.group(2))) if m else None


def pr_dates(doc: str) -> tuple[str, str]:
    flat = re.sub(r"\s+", " ", doc)
    impl = re.search(r"implemented as of the close of ([A-Z][a-z]+ \d{1,2}, \d{4})", flat)
    ann = re.search(
        r"(?:NEW YORK|GENEVA|LONDON)\s*[-,\u2013]\s*([A-Z][a-z]+ \d{1,2}, \d{4})",
        flat,
        re.IGNORECASE,
    )
    if not impl or not ann:
        raise ValueError("press release dates not found")
    f = lambda s: datetime.strptime(s, "%B %d, %Y").date().isoformat()  # noqa: DTZ007  (a calendar date, no time)
    return f(ann.group(1)), f(impl.group(1))


def main() -> int:
    recs = [json.loads(x) for x in MANIFEST.read_text().splitlines()[1:]]
    tmap = pd.read_csv(HERE / "ticker_map.csv")
    name2tick = dict(zip(tmap.msci_name, tmap.ticker))
    bad = [t for t in name2tick.values() if not re.fullmatch(r"[A-Z]{4}", str(t))]
    if bad:
        sys.exit(f"error: ticker_map.csv holds codes that are not IDX codes: {bad}")
    rows, unmapped = [], set()
    for review in dict.fromkeys(r["review"] for r in recs):
        files = {r["segment"]: ROOT / "data/raw" / r["file"] for r in recs if r["review"] == review}
        ann, impl = pr_dates(text(files["PR"]))
        blocks = {}
        for seg in ("ST", "SC"):
            doc = text(files[seg])
            adds, dels = indonesia_block(doc)
            if (indonesia_summary(doc) or (0, 0)) != (len(adds), len(dels)):
                sys.exit(
                    f"error: {review} {seg}: parsed Indonesia changes differ from MSCI's summary row"
                )
            blocks[seg] = (adds, dels)
        (st_add, st_del), (sc_add, sc_del) = blocks["ST"], blocks["SC"]
        for seg, adds, dels, other_adds in (
            ("ST", st_add, st_del, sc_add),
            ("SC", sc_add, sc_del, st_add),
        ):
            for side, names in (("ADD", adds), ("DEL", dels)):
                for n in names:
                    if n not in name2tick:
                        unmapped.add(n)
                    if (
                        side == "DEL"
                    ):  # migrations are matched on the IDX code, not on MSCI's spelling
                        moved = name2tick.get(n) in {name2tick.get(x) for x in other_adds}
                        kind = (
                            ("ST_TO_SC" if moved else "ST_EXIT")
                            if seg == "ST"
                            else ("SC_TO_ST" if moved else "SC_EXIT")
                        )
                    else:
                        kind = "ADD"
                    rows.append(
                        {
                            "review": review,
                            "segment": seg,
                            "side": side,
                            "kind": kind,
                            "msci_name": n,
                            "ticker": name2tick.get(n, ""),
                            "announce_date": ann,
                            "implementation_close": impl,
                        }
                    )
    if unmapped:
        sys.exit(f"error: MSCI names without a ticker in ticker_map.csv: {sorted(unmapped)}")
    ev = pd.DataFrame(rows)
    if (
        len(sys.argv) > 1 and sys.argv[1] == "--check"
    ):  # used by msci_deletion.freeze(): must reproduce the pinned file
        return 0 if ev.to_csv(index=False) == (HERE / "events_all.csv").read_text() else 1
    ev.to_csv(HERE / "events_all.csv", index=False)
    print(ev.groupby(["review", "segment", "side"]).size().unstack(fill_value=0).to_string())
    print(ev[ev.side == "DEL"].kind.value_counts().to_dict())
    return 0


if __name__ == "__main__":
    sys.exit(main())
