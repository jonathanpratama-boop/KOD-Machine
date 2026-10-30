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
import tempfile
import uuid
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
    publish_bytes(path, ("\n".join(lines) + "\n").encode("utf-8"))
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
    path = Path(path).resolve()
    lock_path = path.with_name(path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _sync_directory(directory: Path) -> None:
    """Durable directory entry publication on the POSIX local filesystems we support."""
    fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextlib.contextmanager
def atomic_writer(path: Path, *, replace: bool = False):
    """Stage/fsync bytes then atomically publish. Exclusive publication never clobbers.

    Mutable callers must hold their stable sibling lock across read and publication.
    A crash before publication leaves the previous file intact (possibly a staging
    orphan); after publication readers see the complete new file. Local POSIX only.
    """
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="." + path.name + ".stage-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            if replace and path.exists():
                os.fchmod(stream.fileno(), path.stat().st_mode & 0o777)
            else:
                os.fchmod(stream.fileno(), 0o644)
            yield stream
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            os.replace(temporary, path)
        else:
            # Hard-link creation is atomic and fails if the destination exists.
            # Staging in the same directory ensures it is on the same filesystem.
            os.link(temporary, path)
        _sync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def publish_bytes(path: Path, data: bytes, *, replace: bool = False) -> None:
    with atomic_writer(path, replace=replace) as stream:
        stream.write(data)


def build_stamp() -> str:
    """Sortable fine-grained publication time plus collision-resistant build identity."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex


def write_csv_gz_exclusive(path: Path, frame, **to_csv) -> None:
    """Stage deterministic gzip CSV and publish exclusively; no name/time header.

    Existing objects remain untouched even if serialization fails. New output bytes
    are deterministic across filenames; historical panel hashes are unchanged.
    """
    with atomic_writer(path) as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with io.TextIOWrapper(gz, encoding="utf-8", newline="") as text:
                frame.to_csv(text, **to_csv)


def latest_panel_manifest(prefix: str) -> Path:
    """Select complete published manifests by explicit build time, with legacy support.

    New publication IDs encode microsecond start time and a collision-resistant suffix.
    Legacy manifests retain their original built_at time and deterministic filename tie.
    A malformed published manifest is an error, not a silently skipped candidate.
    """
    found = list(MANIFESTS.glob(f"{prefix}-*.json"))
    if not found:
        raise FileNotFoundError(f"no {prefix} manifest in {MANIFESTS}")
    def key(path):
        meta = json.loads(path.read_text(encoding="utf-8"))
        if not meta.get("panel") or not meta.get("sha256"):
            raise ValueError(f"incomplete panel manifest: {path.name}")
        if meta.get("publication_id"):
            moment = datetime.strptime(meta["publication_id"].split("-", 1)[0], "%Y%m%dT%H%M%S%fZ").replace(tzinfo=timezone.utc)
        else:
            moment = datetime.fromisoformat(meta["built_at"].replace("Z", "+00:00"))
        return moment, path.name
    return max(found, key=key)
