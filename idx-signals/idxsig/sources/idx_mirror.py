"""IDX daily stock summary, via a public git mirror pinned to one commit.

idx.co.id publishes the daily stock summary (Previous, Open, High, Low, Close, Volume,
Value, Frequency, ...) but sits behind Cloudflare and its terms forbid scraping. The
mirror below republishes those summaries per ticker. Pinning the commit makes the
download exactly reproducible.

Coverage of the pinned commit: 2019-07-29 to 2025-02-21, 958 tickers. Prices are as
traded (not adjusted); `previous` is IDX's reference price, which IDX resets on split
dates, so close/previous - 1 is the exchange's own daily change. Names that delisted
after the mirror started (from 2021-01) keep their history (FINN, TURI, RMBA end early);
names delisted between 2019-07 and the mirror's first snapshot are absent.
"""

from __future__ import annotations

import csv
import os
import subprocess
from pathlib import Path

from ..provenance import RAW, rel, sha256_file, utc_stamp, write_manifest

REPO_URL = "https://github.com/wildangunawan/Dataset-Saham-IDX"
PINNED_COMMIT = "bc0ac7712ce5e46f1067349e13ab9f338883c6c4"
# The mirror's first ticker snapshot (upstream commit ca98f6539, 2021-01-22) held the names
# listed that day, each with history back to 2019-07-29. A name that delisted before it was
# never captured; from it on, delisted names keep their files. So the universe is
# survivorship-complete only from this date, and backtests start here by default.
FIRST_SNAPSHOT = "2021-01-22"
SOURCE = "idx_mirror"
LICENSE = (
    "Mirror: CC BY-NC 4.0 (wildangunawan/Dataset-Saham-IDX). Underlying data: PT Bursa Efek "
    "Indonesia; non-commercial use only, cite the source and the access date."
)
PATHS = ("Saham/Semua", "List Emiten", "info.json", "LICENSE.md", "Keterangan Nama Kolom.md", "README.md")


def _git(cwd: Path, *args: str) -> str:
    env = {**os.environ, "GIT_LFS_SKIP_SMUDGE": "1", "GIT_TERMINAL_PROMPT": "0"}
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {proc.stderr.strip()}")
    return proc.stdout


def _csv_summary(path: Path) -> dict:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    body = rows[1:]
    return {
        "rows": len(body),
        "first_date": body[0][0][:10] if body else None,
        "last_date": body[-1][0][:10] if body else None,
    }


def ticker_dir(commit: str = PINNED_COMMIT) -> Path:
    return RAW / "idx_mirror" / commit[:12] / "Saham" / "Semua"


def fetch(commit: str = PINNED_COMMIT, log=print) -> Path:
    started = utc_stamp()
    cache = RAW / "idx_mirror" / "_git"
    out = RAW / "idx_mirror" / commit[:12]
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"{rel(out)} already holds this commit; its manifest is in data/manifests")
    cache.mkdir(parents=True, exist_ok=True)
    if not (cache / ".git").exists():
        _git(cache, "init", "-q")
        _git(cache, "remote", "add", "origin", REPO_URL)
    log(f"fetching {REPO_URL} @ {commit}")
    _git(cache, "fetch", "-q", "--depth", "1", "origin", commit)
    out.mkdir(parents=True, exist_ok=True)
    _git(cache, f"--work-tree={out.resolve()}", "checkout", commit, "--", *PATHS)
    downloaded_at = utc_stamp()
    commit_date = _git(cache, "show", "-s", "--format=%cI", commit).strip()
    records = []
    for path in sorted(p for p in out.rglob("*") if p.is_file()):
        upstream_path = path.relative_to(out).as_posix()
        rec = {
            "path": rel(path),
            "source": SOURCE,
            "source_url": f"{REPO_URL}/blob/{commit}/{upstream_path}",
            "upstream_repo": REPO_URL,
            "upstream_commit": commit,
            "upstream_commit_date": commit_date,
            "upstream_path": upstream_path,
            "original_publisher": "PT Bursa Efek Indonesia daily stock summary (idx.co.id)",
            "downloaded_at": downloaded_at,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "license": LICENSE,
        }
        if upstream_path.startswith("Saham/Semua/") and path.suffix == ".csv":
            rec["ticker"] = path.stem
            rec.update(_csv_summary(path))
        records.append(rec)
    header = {
        "source": SOURCE,
        "description": "IDX daily stock summary per ticker, as traded (unadjusted), with IDX reference price",
        "upstream_repo": REPO_URL,
        "upstream_commit": commit,
        "upstream_commit_date": commit_date,
        "started_at": started,
        "downloaded_at": downloaded_at,
        "raw_dir": rel(out),
        "license": LICENSE,
    }
    return write_manifest(f"idx_mirror-{downloaded_at.replace('-', '').replace(':', '')}.jsonl", header, records)
