"""Bounded, checksum-verified local runtime archives. No network or scheduling."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zipfile

from .storage import canonical, locked

SCHEMA = "KOD_RUNTIME_BACKUP_V1"
MANIFEST = "BACKUP_MANIFEST.json"
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_FILES = 100000


def _name(name):
    path = PurePosixPath(name)
    if (
        not name
        or "\\" in name
        or "\x00" in name
        or path.is_absolute()
        or any(part in ("", ".", "..") for part in name.split("/"))
        or ":" in name
        or name == MANIFEST
    ):
        raise ValueError("unsafe or reserved archive path")
    return path


def _publish(source, destination):
    """Linux no-replace rename; runtime already requires POSIX flock."""
    library = ctypes.CDLL(None, use_errno=True)
    rename = getattr(library, "renameat2", None)
    if rename is None:
        raise RuntimeError("atomic no-replace publication requires Linux renameat2")
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(-100, os.fsencode(source), -100, os.fsencode(destination), 1):
        code = ctypes.get_errno()
        if code == errno.EEXIST:
            raise FileExistsError(destination)
        raise OSError(code, os.strerror(code))
    fd = os.open(Path(destination).parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def backup(root, destination):
    root, destination = Path(root).resolve(), Path(destination).absolute()
    if not root.is_dir():
        raise ValueError("runtime root does not exist")
    if destination.resolve().is_relative_to(root):
        raise ValueError("backup must be outside the runtime root")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".kod-backup-", dir=destination.parent)
    os.close(fd)
    files, total = {}, 0
    try:
        with (
            locked(root),
            zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive,
        ):
            for path in sorted(root.rglob("*")):
                if path.is_symlink():
                    raise ValueError("runtime backup refuses symbolic links")
                if path.is_dir():
                    continue
                if not path.is_file():
                    raise ValueError("runtime backup requires ordinary files")
                name = path.relative_to(root).as_posix()
                if path.name.endswith(".lock"):
                    continue
                _name(name)
                size = path.stat().st_size
                total += size
                if size > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES or len(files) >= MAX_FILES:
                    raise ValueError("runtime exceeds archive size limits")
                body = path.read_bytes()
                if len(body) != size:
                    raise ValueError("runtime changed during locked backup")
                files[name] = {"bytes": size, "sha256": hashlib.sha256(body).hexdigest()}
                archive.writestr(name, body)
            manifest = {"schema_version": SCHEMA, "files": files}
            archive.writestr(MANIFEST, canonical(manifest))
        with open(temporary, "rb") as stream:
            os.fsync(stream.fileno())
        _publish(temporary, destination)
        return {
            "ok": True,
            "archive": str(destination),
            "files": len(files),
            "bytes": total,
            "manifest_sha256": hashlib.sha256(canonical(manifest)).hexdigest(),
        }
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate manifest key")
        result[key] = value
    return result


def restore(archive, destination):
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    # Validate every byte before creating the destination or staging directory.
    with zipfile.ZipFile(archive, "r") as bundle:
        entries = bundle.infolist()
        names = [entry.filename for entry in entries]
        if (
            len(names) != len(set(names))
            or names.count(MANIFEST) != 1
            or len(names) > MAX_FILES + 1
        ):
            raise ValueError("duplicate, missing manifest or excessive archive entries")
        total = 0
        for entry in entries:
            if entry.filename != MANIFEST:
                _name(entry.filename)
            mode = (entry.external_attr >> 16) & 0xFFFF
            if (
                entry.is_dir()
                or (stat.S_IFMT(mode) not in (0, stat.S_IFREG))
                or entry.flag_bits & 1
            ):
                raise ValueError("only ordinary unencrypted files may be restored")
            total += entry.file_size
            if entry.file_size > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                raise ValueError("archive exceeds size limits")
        manifest = json.loads(bundle.read(MANIFEST), object_pairs_hook=_unique)
        files = manifest.get("files")
        if manifest.get("schema_version") != SCHEMA or not isinstance(files, dict):
            raise ValueError("unsupported backup manifest")
        if set(files) != set(names) - {MANIFEST}:
            raise ValueError("manifest/archive membership mismatch")
        for name, info in files.items():
            body = bundle.read(name)
            if (
                not isinstance(info, dict)
                or len(body) != info.get("bytes")
                or hashlib.sha256(body).hexdigest() != info.get("sha256")
            ):
                raise ValueError("backup content checksum mismatch")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".kod-restore-", dir=destination.parent))
        try:
            for name in files:
                path = temporary / name
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("xb") as stream:
                    body = bundle.read(name)
                    if (
                        len(body) != files[name]["bytes"]
                        or hashlib.sha256(body).hexdigest() != files[name]["sha256"]
                    ):
                        raise ValueError("archive changed during restore")
                    stream.write(body)
                    stream.flush()
                    os.fsync(stream.fileno())
            for directory in [
                *sorted(
                    (p for p in temporary.rglob("*") if p.is_dir()),
                    key=lambda p: len(p.parts),
                    reverse=True,
                ),
                temporary,
            ]:
                fd = os.open(directory, os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            _publish(temporary, destination)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
    return {
        "ok": True,
        "root": str(destination),
        "files": len(files),
        "manifest_sha256": hashlib.sha256(canonical(manifest)).hexdigest(),
        "next_action": "Run runtime verify before resuming paper cycles",
    }
