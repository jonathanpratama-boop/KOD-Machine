"""Run-time guard while a rule computes: no files, network, processes, frames or heap walks.

A PEP 578 audit hook, installed once per process, is inert except inside `guarded()`. While
active it refuses (and records) any attempt to:

  - open or list a file outside the Python installation and the idxsig source tree (data
    files, the panel, the corporate-action registry), or write anything other than the
    import system's own bytecode cache;
  - reach the network, start a process, or load foreign code (socket, subprocess, os.system,
    urllib, ctypes, ...);
  - walk frames or the heap (sys._getframe, traceback/generator frames, gc.get_objects ...),
    which is how a rule could reach the caller's full, untruncated arrays.

The rule sees a PermissionError; even if it swallows it, the violation is recorded and the
run fails with LookaheadError, as it does if the sandbox's own state is changed during compute.

Limits: an in-process sandbox is not a security boundary. It stops accidental and naive
leaks, and the source audit refuses the obvious ways around it; a rule written to defeat
both can still do so, so rule source is reviewed before a run is trusted. Python's own imports read .py files under the installation
and the idxsig package, which stay allowed.
"""

from __future__ import annotations

import os
import sys
import sysconfig
from contextlib import contextmanager
from pathlib import Path

_STATE = {"active": False, "violations": [], "installed": False}
_PKG = str(Path(__file__).resolve().parents[1])  # idxsig/
_READ_ROOTS = tuple(sorted({
    os.path.realpath(p) for p in (
        sys.prefix, sys.base_prefix, sys.exec_prefix, *(sysconfig.get_paths().values()),
    ) if p
}))
_BLOCKED_PREFIXES = (
    "socket.", "subprocess.", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.fork", "os.forkpty",
    "os.kill", "os.startfile", "urllib.", "http.client.", "ftplib.", "smtplib.", "poplib.", "imaplib.",
    "telnetlib.", "webbrowser.", "ctypes.", "sqlite3.", "shutil.", "os.remove", "os.unlink", "os.rename",
    "os.mkdir", "os.rmdir", "os.chmod", "os.chown", "os.truncate", "os.symlink", "os.link", "os.putenv",
    "os.unsetenv", "sys._getframe", "sys._current_frames", "sys._current_exceptions", "sys.settrace",
    "sys.setprofile", "sys.addaudithook", "gc.get_objects", "gc.get_referrers", "gc.get_referents",
    "pickle.find_class", "mmap.", "builtins.input", "pdb.",
)
_FRAME_ATTRS = {"tb_frame", "gi_frame", "cr_frame", "ag_frame", "f_back", "gi_code"}
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC


class SandboxViolation(PermissionError):
    pass


def _under(real: str, root: str) -> bool:
    try:
        return os.path.commonpath([real, root]) == root
    except ValueError:
        return False


def _real(path) -> str | None:
    if isinstance(path, int):
        return None
    try:
        return os.path.realpath(os.fsdecode(path))
    except (TypeError, ValueError):
        return None


def _path_allowed(path) -> bool:
    real = _real(path)
    if real is None:
        return False
    if any(_under(real, root) for root in _READ_ROOTS):
        return True
    return _under(real, _PKG) and (os.path.isdir(real) or real.endswith((".py", ".pyc")))


def _bytecode_cache(path) -> bool:
    """The import system writing a .pyc into a __pycache__ directory of allowed code."""
    real = _real(path)
    if real is None:
        return False
    parts = real.split(os.sep)
    in_cache = "__pycache__" in parts[-2:]
    return in_cache and (any(_under(real, root) for root in _READ_ROOTS) or _under(real, _PKG))


def _on_sys_path(path) -> bool:
    try:
        real = os.path.realpath(os.fsdecode(path))
    except (TypeError, ValueError):
        return False
    return real in {os.path.realpath(p or ".") for p in sys.path if isinstance(p, str)}


def _hook(event: str, args: tuple) -> None:
    if not _STATE["active"]:
        return
    reason = None
    if event == "marshal.load":  # reading marshalled data from a file object; marshal.loads (imports) is fine
        reason = event
    elif event == "open":
        path, mode, flags = (tuple(args) + (None, None, 0))[:3]
        if isinstance(path, int):  # wrapping a descriptor that an allowed open already produced
            return
        writing = (mode is not None and any(c in str(mode) for c in "wax+")) or (
            mode is None and isinstance(flags, int) and flags & _WRITE_FLAGS)
        if writing and not _bytecode_cache(path):
            reason = f"open for writing {path!r}"
        elif not writing and not _path_allowed(path):
            reason = f"open {path!r}"
    elif event in ("os.listdir", "os.scandir", "glob.glob", "os.walk"):
        target = (args[0] if args and args[0] not in (None, "", b"") else ".")
        # The import system lists sys.path directories (names only) to find modules.
        listing_import_path = event in ("os.listdir", "os.scandir") and _on_sys_path(target)
        if not listing_import_path and not _path_allowed(target):
            reason = f"{event} {target!r}"
    elif event == "object.__getattr__":
        if len(args) > 1 and args[1] in _FRAME_ATTRS:
            reason = f"frame access .{args[1]}"
    elif event in ("os.mkdir", "os.rename") and all(_bytecode_cache(a) for a in args[:2] if isinstance(a, (str, bytes))):
        pass  # the import system caching bytecode
    elif event.startswith(_BLOCKED_PREFIXES):
        reason = event
        if event == "sys._getframe":
            reason += (" (pandas query/eval and DataFrame printing inspect the call stack; they are not "
                       "available inside compute)")
    if reason:
        _STATE["violations"].append(reason)
        raise SandboxViolation(f"not allowed while a rule computes: {reason}")


def install() -> None:
    if not _STATE["installed"]:
        sys.addaudithook(_hook)
        _STATE["installed"] = True


@contextmanager
def guarded():
    """Yields a list that collects violations made inside the block."""
    install()
    if _STATE["active"]:
        raise RuntimeError("guarded() does not nest")
    violations: list = []
    _STATE["violations"] = violations
    _STATE["active"] = True
    try:
        yield violations
    finally:
        if _STATE.get("active") is not True or _STATE.get("violations") is not violations:
            violations.append("the sandbox's state was changed while the rule computed")
        _STATE["active"] = False
