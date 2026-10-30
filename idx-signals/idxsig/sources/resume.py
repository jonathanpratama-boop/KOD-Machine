"""Request identity and immutable raw objects for resumable provider downloads.

Callers hold a directory-level download lock while binding, fetching and publishing
progress. Resume reuses the original absolute window and observed source snapshot.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..provenance import PKG_ROOT, publish_bytes, sha256_bytes, sha256_file


class ResumeMismatch(ValueError):
    pass


class CacheIntegrityError(ValueError):
    pass


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def publish(path: Path, raw: bytes) -> None:
    """Publish complete immutable bytes without replacing an existing object."""
    try:
        publish_bytes(path, raw)
    except FileExistsError:
        if path.read_bytes() != raw:
            raise CacheIntegrityError(f"immutable cache object differs: {path}; use a fresh output directory")



def bind_request(out_dir: Path, request: dict, window: dict, started_at: str) -> dict:
    path = out_dir / "_request.json"
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        payload = {k: v for k, v in saved.items() if k != "sha256"}
        if saved.get("sha256") != sha256_bytes(canonical(payload)):
            raise CacheIntegrityError("download request descriptor hash mismatch; use a fresh output directory")
        if saved.get("request") != request:
            raise ResumeMismatch("download request differs from this cache (range, universe, provider or filters); "
                                 "resume the original request or use a fresh output directory")
        return saved
    if any(p for p in out_dir.iterdir() if not p.name.endswith(".lock")):
        raise ResumeMismatch("existing download has no pinned request descriptor; its compatibility is unverified. "
                             "Preserve it and use a fresh output directory")
    saved = {"format": "provider-request-v1", "request": request, "window": window, "started_at": started_at}
    saved["sha256"] = sha256_bytes(canonical(saved))
    publish(path, canonical(saved) + b"\n")
    return saved


def save_raw(path: Path, raw: bytes) -> Path:
    """Responses, including failed attempts, get immutable content-addressed names."""
    target = path.with_name(path.stem + "." + sha256_bytes(raw) + path.suffix)
    publish(target, raw)
    return target


def verify_cached(rec: dict, out_dir: Path) -> None:
    path = (PKG_ROOT / rec["path"]).resolve()
    if not path.is_relative_to(out_dir.resolve()):
        raise CacheIntegrityError(f"cached path is outside the bound download directory: {rec['path']}")
    if not path.is_file() or sha256_file(path) != rec.get("sha256"):
        raise CacheIntegrityError(f"cached response is missing or modified: {rec['path']}; "
                                  "preserve the cache and use a fresh output directory")
