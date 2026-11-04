"""Read-only attempt inspection, with price plots gated by original evidence.

The timing projection supplies the chronology. Price data is loaded only through
the runtime's raw-evidence verifier. A missing runtime package or missing source
bytes leaves a useful chronology and an explicit unavailable price panel.
"""

from __future__ import annotations

from decimal import Decimal
import hashlib
import hmac
import json
from pathlib import PurePosixPath
import re

from .operations import (
    MAX_BYTES,
    OperationsArchive,
    OperationsUnavailable,
    TimingArchive,
    _timing_time,
    canonical,
    timing_timeline,
)

HEX = re.compile(r"[0-9a-f]{64}")
MAX_POINTS = 500


def _retained_path(root, relative):
    """Accept a bounded original file within the selected runtime only."""
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise OperationsUnavailable("Invalid retained evidence path.")
    parts = PurePosixPath(relative)
    if parts.is_absolute() or ".." in parts.parts:
        raise OperationsUnavailable("Evidence path escapes the runtime.")
    path = root
    for part in parts.parts:
        path = path / part
        if path.is_symlink():
            raise OperationsUnavailable("Linked evidence uses a symlink.")
    if not path.resolve().is_relative_to(root.resolve()):
        raise OperationsUnavailable("Evidence path escapes the runtime.")
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise OperationsUnavailable("Linked evidence is missing or exceeds the display limit.")
    return path


def _capture(root, owner):
    """Verify the attempt-to-capture join and every retained source receipt."""
    links = owner["links"]
    path = _retained_path(root, links["capture_path"])
    expected = links.get("capture_sha256")
    if (
        not isinstance(expected, str)
        or not HEX.fullmatch(expected)
        or path.parent != root / "timing" / "captures"
        or path.name != owner["id"] + ".json"
    ):
        raise OperationsUnavailable("Capture identity does not match its owning attempt.")
    raw = path.read_bytes()
    if not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected):
        raise OperationsUnavailable("Linked capture bytes changed.")
    declaration = json.loads(raw)
    _retained_path(root, "evidence/" + declaration["membership_path"])
    for evidence in declaration["evidence"]:
        _retained_path(root, "evidence/" + evidence["path"])
        _retained_path(
            root, "evidence/receipts/" + evidence["evidence_id"].removeprefix("ev_") + ".json"
        )
    # Optional import keeps the existing standalone workstation usable.
    from idxsig.runtime.intraday import load_intraday

    value = load_intraday(path, root / "evidence")
    if value["membership_snapshot_id"] != links.get("capture_membership_id"):
        raise OperationsUnavailable("Capture membership differs from the attempt.")
    expected_kind = "synthetic" if owner["evidence_kind"] == "synthetic" else "public_market"
    if value["evidence_kind"] != expected_kind:
        raise OperationsUnavailable("Capture and attempt evidence cohorts disagree.")
    if _timing_time(value["completed_at"], "completion") > _timing_time(
        owner["recorded_at"], "recorded"
    ):
        raise OperationsUnavailable("Capture completed after the attempt was recorded.")
    if owner.get("scheduled_at") != value["scheduled_at"]:
        raise OperationsUnavailable("Capture and attempt scheduled slots disagree.")
    return value


def _plot(bars, attempt):
    """Plot exact retained closes; gaps break the line and markers have no price."""
    if not bars:
        return None
    times = [_timing_time(row["bar_end_at"], "bar end").timestamp() for row in bars]
    prices = [Decimal(row["close"]) for row in bars]
    if any(not value.is_finite() or value <= 0 for value in prices):
        raise OperationsUnavailable("Price plot requires finite positive closes.")
    first, last = min(times), max(times)
    minimum, maximum = min(prices), max(prices)
    span = maximum - minimum
    segments, segment, points = [], [], []
    for index, (row, stamp, price) in enumerate(zip(bars, times, prices)):
        x = 60 + (stamp - first) / (last - first or 1) * 800
        y = 150 if not span else 250 - float((price - minimum) / span) * 200
        point = {**row, "x": round(x, 2), "y": round(y, 2)}
        if index and bars[index - 1]["bar_end_at"] != row["open_time"]:
            segments.append(" ".join(segment))
            segment = []
        segment.append(f"{x:.2f},{y:.2f}")
        points.append(point)
    if segment:
        segments.append(" ".join(segment))
    markers = []
    for key, label in (
        ("received_at", "Receipt"),
        ("detected_at", "Signal"),
        ("decision_at", "Decision"),
        ("executable_at", "Quote observation"),
        ("fill_at", "Simulated fill processing"),
    ):
        if attempt.get(key) is None:
            continue
        stamp = _timing_time(attempt[key], key).timestamp()
        if first <= stamp <= last:
            markers.append(
                {
                    "label": label,
                    "at": attempt[key],
                    "x": round(60 + (stamp - first) / (last - first or 1) * 800, 2),
                }
            )
    return {
        "segments": segments,
        "points": points,
        "markers": markers,
        "minimum": str(minimum),
        "maximum": str(maximum),
        "start": bars[0]["bar_end_at"],
        "end": bars[-1]["bar_end_at"],
    }


def _paper_fill(root, attempt):
    """Match an optional displayed fill by its retained timing-sidecar digest."""
    links = attempt["links"]
    if not links.get("fill_id"):
        return None
    account = OperationsArchive(root).snapshot()["payload"]["account"]
    if account.get("simulation_only") is not True:
        raise OperationsUnavailable("Linked account does not identify simulated execution.")
    fills = [row for row in account.get("fills", []) if row.get("id") == links["fill_id"]]
    if len(fills) != 1:
        raise OperationsUnavailable("The linked simulated fill is unavailable in the account view.")
    fill = fills[0]
    if (
        hashlib.sha256(canonical(fill)).hexdigest() != links.get("fill_record_sha256")
        or fill.get("intent_id") != links.get("intent_id")
        or fill.get("symbol") != links.get("intent_symbol")
        or fill.get("simulation_only") is not True
    ):
        raise OperationsUnavailable(
            "The simulated fill differs from its retained timing reference."
        )
    return fill


def _bind_journal(root, payload, attempt, detail):
    """Bind displayed chronology to immutable records, not a rehashable projection."""
    journal = root / "timing" / "attempts.jsonl"
    if not journal.exists():
        return False
    _retained_path(root, "timing/attempts.jsonl")
    try:
        from idxsig.timing_capture import read_attempts, summarize
    except ImportError:
        return False
    try:
        originals = read_attempts(root, as_of=payload["as_of"])
        indexed = {row["id"]: row for row in originals}
        owners = {row["id"]: row for row in payload["attempts"]}
        selected = [attempt["id"]]
        parent = attempt["links"].get("parent_attempt_id")
        if parent:
            selected.append(parent)
        for identity in selected:
            if identity not in indexed or canonical(indexed[identity]) != canonical(
                owners.get(identity)
            ):
                raise ValueError("attempt differs from retained timing journal")
        summary = summarize(originals, as_of=payload["as_of"])
        expected = next(row for row in summary["records"] if row["id"] == attempt["id"])
        if canonical(expected) != canonical(detail):
            raise ValueError("attempt summary differs from retained timing journal")
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        raise OperationsUnavailable("Chronology verification failed: " + str(exc)) from exc
    return True


def clock_assessment(root, attempt):
    """Assess the original clock independently of historical producer labels."""
    try:
        from idxsig.runtime.timing_evidence import assess_retained_clock

        return assess_retained_clock(root, attempt)
    except (ImportError, OSError, ValueError, KeyError, TypeError) as exc:
        return {
            "status": "UNKNOWN",
            "original_claim_valid": False,
            "reason": "Retained clock evidence is unavailable or invalid: " + str(exc),
        }


class DecisionInspector:
    """Present one retained attempt; GET requests never run collectors or writers."""

    def __init__(self, root=None):
        self.archive = TimingArchive(root)
        self.root = self.archive.root

    def attempt(self, attempt_id, *, symbol=None):
        snapshot = self.archive.snapshot()
        payload = snapshot["payload"]
        rows = {row["id"]: row for row in payload["attempts"]}
        if attempt_id not in rows:
            raise KeyError(attempt_id)
        attempt = rows[attempt_id]
        detail = next(row for row in payload["summary"]["records"] if row["id"] == attempt_id)
        bound = _bind_journal(self.root, payload, attempt, detail)
        view = {
            "chronology_status": "JOURNAL_VERIFIED" if bound else "DECLARED_REPORT_ONLY",
            "attempt": attempt,
            "snapshot_sha256": snapshot["sha256"],
            "report_cutoff": payload["as_of"],
            "timeline": timing_timeline(attempt),
            "details": detail,
            "price_status": "UNKNOWN",
            "price_reason": "This attempt has no linked intraday capture. No price path is inferred.",
            "capture": None,
            "symbols": [],
            "symbol": None,
            "plot": None,
            "bars": [],
            "quotes": [],
            "fill": None,
            "fill_error": None,
        }
        view["clock_assessment"] = clock_assessment(self.root, attempt)
        parent = attempt["links"].get("parent_attempt_id")
        owner = rows.get(parent) if parent else attempt
        if bound and owner is not None and owner["links"].get("capture_path"):
            try:
                capture = _capture(self.root, owner)
                request_symbol = None
                if parent:
                    prefix = parent + ":request:"
                    suffix = attempt_id.removeprefix(prefix)
                    if not attempt_id.startswith(prefix) or not suffix.isdigit():
                        raise OperationsUnavailable("Request identity does not match its capture.")
                    index = int(suffix)
                    if index >= len(capture["requests"]):
                        raise OperationsUnavailable("Request index is outside its capture.")
                    request = capture["requests"][index]
                    if (
                        attempt["evidence_kind"] != owner["evidence_kind"]
                        or attempt["evidence_id"] != (request.get("evidence_id") or attempt_id)
                        or attempt.get("received_at") != request.get("received_at")
                        or attempt.get("started_at") != request.get("request_started_at")
                    ):
                        raise OperationsUnavailable("Request chronology differs from its capture.")
                    request_symbol = request.get("symbol")
                symbols = capture["symbols_requested"]
                selected = (
                    symbol or request_symbol or attempt["links"].get("intent_symbol") or symbols[0]
                )
                if selected not in symbols:
                    raise OperationsUnavailable(
                        "Selected instrument is outside retained membership."
                    )
                bars = [row for row in capture["bars"] if row["symbol"] == selected]
                retained = len(bars)
                # Keep the last bounded window, with a truthful denominator.
                bars = bars[-MAX_POINTS:]
                view.update(
                    capture={
                        key: capture[key]
                        for key in (
                            "interval",
                            "status",
                            "coverage",
                            "symbol_status",
                            "failures",
                            "window_start_at",
                            "window_end_at",
                            "capture_sha256",
                            "clock_integrity",
                        )
                    },
                    capture_owner=owner["id"],
                    symbols=symbols,
                    symbol=selected,
                    bars=bars,
                    retained_bars=retained,
                    plot=_plot(bars, attempt),
                    quotes=[row for row in capture["quotes"] if row["symbol"] == selected],
                    price_status="VERIFIED_RETAINED_BYTES",
                    price_reason="Original capture, source bytes and receipts reconcile. This does not verify provider truth or achievable fills.",
                )
            except (ImportError, OSError, ValueError, KeyError, TypeError, ArithmeticError) as exc:
                view["price_status"] = "UNAVAILABLE"
                view["price_reason"] = (
                    "Price evidence could not be verified: " + str(exc)
                    if not isinstance(exc, ImportError)
                    else "The runtime evidence verifier is not installed. Chronology remains available."
                )
        elif parent and owner is None:
            view["price_reason"] = "The parent attempt is absent from this retained report."
        if not bound:
            view["price_reason"] = (
                "Chronology is an unverified report declaration. Original journal verification is required before showing linked prices or execution."
            )
            view["fill_error"] = "Original journal unavailable; execution claims are withheld."
            return view
        try:
            view["fill"] = _paper_fill(self.root, attempt)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            view["fill_error"] = str(exc)
        return view
