"""Provenance. Every data file gets one manifest line: what it is, where it came from, when.

Manifests are JSONL files under data/manifests/, one per download, never rewritten. The
first line is a header; each following line describes one file. The raw files themselves
are not committed (size and third-party terms); the manifest hashes make any rebuild
checkable against the files a run actually used.
"""

from __future__ import annotations

import hashlib
import json
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
