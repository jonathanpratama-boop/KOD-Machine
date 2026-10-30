"""Provenance. Every data file gets one manifest line: what it is, where it came from, when.

Manifests are JSONL files under data/manifests/, one per download, never rewritten. The
first line is a header; each following line describes one file. The raw files themselves
are not committed (size and third-party terms); the manifest hashes make any rebuild
checkable against the files a run actually used.
"""

from __future__ import annotations

import contextlib
import fcntl
import gzip
import hashlib
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[1]
DATA = PKG_ROOT / "data"
RAW = DATA / "raw"
PANEL_DIR = DATA / "panel"
MANIFESTS = DATA / "manifests"


def utc_stamp(moment: datetime | None = None) -> str:
    moment = moment or datetime.now(timezone.utc)
    return moment.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    return Path(path).resolve().relative_to(PKG_ROOT).as_posix()


def write_manifest(name: str, header: dict, records: list[dict]) -> Path:
    """Write a new manifest. Refuses to overwrite: a re-download is a new manifest."""
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    path = MANIFESTS / name
    if path.exists():
        raise FileExistsError(f"{rel(path)} exists; manifests are never rewritten")
    lines = [json.dumps({"manifest": name, **header, "n_files": len(records)}, sort_keys=True)]
    lines += [json.dumps(r, sort_keys=True) for r in sorted(records, key=lambda r: r["path"])]
    with path.open("x", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


def read_manifest(path: Path) -> tuple[dict, list[dict]]:
    lines = [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    return lines[0], lines[1:]


def latest_manifest(prefix: str, suffix: str = ".jsonl") -> Path:
    found = sorted(MANIFESTS.glob(f"{prefix}-*{suffix}"))
    if not found:
        raise FileNotFoundError(f"no {prefix} manifest in {rel(MANIFESTS)}; fetch first")
    return found[-1]


def check_files(manifest: Path) -> list[str]:
    """Return problems: files missing or not matching their recorded hash."""
    _, records = read_manifest(manifest)
    problems = []
    for r in records:
        if not r.get("sha256"):
            continue
        path = PKG_ROOT / r["path"]
        if not path.exists():
            problems.append(f"missing {r['path']}")
        elif sha256_file(path) != r["sha256"]:
            problems.append(f"hash mismatch {r['path']}")
    return problems


@contextlib.contextmanager
def exclusive_lock(path: Path):
    """One writer at a time for an append-only file: an advisory lock on `<name>.lock` beside it, held across read-tail,
    chain and write, so two appenders cannot read the same previous hash and append conflicting successors. The lock
    file is empty and git-ignored (*.lock); the chain check still catches damage, the lock prevents it."""
    path = Path(path)
    lock_path = path.with_name(path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def write_csv_gz_exclusive(path: Path, frame, **to_csv) -> None:
    """Publish a DataFrame as gzip CSV at a path that must not exist yet (O_EXCL): two builds that pick the same name
    in the same second cannot overwrite each other, the second fails before touching anything. The bytes are the ones
    frame.to_csv(path, compression={"method": "gzip", "mtime": 0}, **to_csv) writes (same gzip header: the basename,
    mtime 0, level 9), so a panel's recorded sha256 does not depend on which writer produced it."""
    path = Path(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb") as raw, gzip.GzipFile(filename=path.name, mode="wb", fileobj=raw, mtime=0) as gz, \
            io.TextIOWrapper(gz, encoding="utf-8", newline="") as text:
        frame.to_csv(text, **to_csv)
