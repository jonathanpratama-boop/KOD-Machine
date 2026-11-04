"""MSCI_DELETION_v1 data: MSCI's own dated review announcement lists (Global Standard and Global Small Cap), Nov 2019 to Nov 2023.

Downloads each review's public PDF from app2.msci.com (free, no log-in), stores it under data/raw/msci/ and pins it in a
manifest. These PDFs are the announcements themselves (point-in-time: published after the European close on the announcement
day, about 04:00-05:00 WIB the next morning). Nothing here reads a price.

    python3 research/MSCI_DELETION_v1/collect.py        # from idx-signals/
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig.provenance import utc_stamp

OUT = ROOT / "data/raw/msci"
REVIEWS = [f"{m}{y}" for y in ("19", "20", "21", "22", "23") for m in ("Feb", "May", "Aug", "Nov")]
REVIEWS = REVIEWS[
    REVIEWS.index("Nov19") :
]  # the IDX panel starts 2019-07-29: Nov 2019 is the first usable review
URL = {
    "ST": "https://app2.msci.com/eqb/gimi/stdindex/MSCI_{r}_STPublicList.pdf",
    "SC": "https://app2.msci.com/eqb/gimi/smallcap/MSCI_{r}_SCPublicList.pdf",
    "PR": "https://app2.msci.com/eqb/pressreleases/archive/MSCI_{r}_QIRPR.pdf",
}  # dates: announcement, implementation


def get(url: str) -> bytes:
    for k in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "KOD-research/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception:
            if k == 3:
                raise
            time.sleep(2**k)
    raise RuntimeError("unreachable")


def _committed(p: Path) -> bool:
    import subprocess

    return (
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(p)],
            cwd=ROOT,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def main() -> int:
    started = utc_stamp().replace("-", "").replace(":", "")
    OUT.mkdir(parents=True, exist_ok=True)
    recs = []
    for r in REVIEWS:
        for seg, pat in URL.items():
            url = pat.format(r=r)
            body = get(url)
            if not body.startswith(b"%PDF"):
                raise RuntimeError(f"{url}: not a PDF")
            dest = OUT / (f"MSCI_{r}_QIRPR.pdf" if seg == "PR" else f"MSCI_{r}_{seg}PublicList.pdf")
            dest.write_bytes(body)
            recs.append(
                {
                    "review": r,
                    "segment": seg,
                    "url": url,
                    "file": str(dest.relative_to(ROOT / "data/raw")),
                    "bytes": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(),
                }
            )
    man = ROOT / "data/manifests" / f"msci_lists-{started}.jsonl"
    old = sorted((ROOT / "data/manifests").glob("msci_lists-*.jsonl"))
    if old:  # one manifest only: a re-collection must match the pinned bytes exactly
        pinned = {
            json.loads(x)["file"]: json.loads(x)["sha256"]
            for x in old[0].read_text().splitlines()[1:]
        }
        changed = [
            x["file"] for x in recs if x["file"] in pinned and pinned[x["file"]] != x["sha256"]
        ]
        if changed:
            raise RuntimeError(f"MSCI files changed since {old[0].name}: {changed}")
        if {x["file"] for x in recs} <= set(pinned):
            print(old[0].name, "unchanged")
            return 0
        old[0].unlink() if old[0].stat().st_size and not _committed(old[0]) else None
    with man.open("x") as fh:
        fh.write(
            json.dumps(
                {
                    "type": "header",
                    "study": "MSCI_DELETION_v1",
                    "started": started,
                    "source": "MSCI public review lists (app2.msci.com/eqb/gimi)",
                    "files": len(recs),
                }
            )
            + "\n"
        )
        for x in recs:
            fh.write(json.dumps(x) + "\n")
    print(man.name, len(recs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
