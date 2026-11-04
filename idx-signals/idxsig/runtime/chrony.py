"""Read chrony's ``chronyc -c tracking`` line under one explicit layout version.

CHRONY_TRACKING_CSV_V2 accepts exactly the 14 comma-separated fields chrony prints
with ``-c``, in this order: reference ID (eight hexadecimal digits), reference name
or address, stratum, reference time (epoch seconds), system time offset (seconds),
last offset, RMS offset, frequency, residual frequency, skew, root delay, root
dispersion, update interval and leap status. Field index 4 is the system time
offset. Any other shape, a nonzero exit status, or a leap status other than
``Normal`` is a measurement failure with a stated reason; no other layout is tried.

Clock evidence written before this version has no ``parser_version`` key. Its parser
stored field index 3, the reference time, as the offset. Such records are verified
as written and reported as OFFSET_FIELD_DEFECT_V1 beside the value this version reads
from the same retained bytes; no stored record is rewritten.

Not claimed: that the host clock is correct, that chrony's reference is accurate, or
that the offset holds at any moment other than chrony's last update. The offset is
stored with chrony's sign, as printed. Fields other than the offset are checked for
shape only; their values are not used.
"""

from __future__ import annotations

from decimal import Decimal
import re

CHRONY_COMMAND = "chronyc -c tracking"
CHRONY_TRACKING_CSV_V2 = "CHRONY_TRACKING_CSV_V2"
OFFSET_FIELD_DEFECT_V1 = "OFFSET_FIELD_DEFECT_V1"
TRACKING_FIELDS_V2 = (
    "reference_id",
    "reference_name",
    "stratum",
    "reference_time",
    "system_time_offset",
    "last_offset",
    "rms_offset",
    "frequency",
    "residual_frequency",
    "skew",
    "root_delay",
    "root_dispersion",
    "update_interval",
    "leap_status",
)
OFFSET_INDEX = 4
V1_OFFSET_INDEX = 3
_REFERENCE_ID = re.compile(r"[0-9A-Fa-f]{8}")
_STRATUM = re.compile(r"[0-9]+")
_NUMBER = re.compile(r"[+-]?[0-9]+(?:\.[0-9]+)?")


class TrackingLayoutError(ValueError):
    """Retained chronyc output is not a usable CHRONY_TRACKING_CSV_V2 measurement."""


def _system_offset(returncode: int, stdout: str) -> Decimal:
    if returncode != 0:
        raise TrackingLayoutError(f"chronyc exited with return code {returncode}")
    lines = stdout.splitlines()
    if len(lines) != 1:
        raise TrackingLayoutError(f"expected one CSV line, found {len(lines)}")
    fields = lines[0].split(",")
    if len(fields) != len(TRACKING_FIELDS_V2):
        raise TrackingLayoutError(
            f"expected {len(TRACKING_FIELDS_V2)} comma-separated fields, found {len(fields)}"
        )
    if not _REFERENCE_ID.fullmatch(fields[0]):
        raise TrackingLayoutError(f"reference_id is not eight hexadecimal digits: {fields[0]!r}")
    if not _STRATUM.fullmatch(fields[2]):
        raise TrackingLayoutError(f"stratum is not a non-negative integer: {fields[2]!r}")
    for index in range(3, 13):
        if not _NUMBER.fullmatch(fields[index]):
            raise TrackingLayoutError(
                f"{TRACKING_FIELDS_V2[index]} is not a finite decimal: {fields[index]!r}"
            )
    if fields[13] != "Normal":
        raise TrackingLayoutError(
            f"leap_status is {fields[13]!r}; only 'Normal' is a usable measurement"
        )
    return Decimal(fields[OFFSET_INDEX])


def read_tracking_v2(returncode: int, stdout: str) -> dict:
    """Interpret one retained chronyc result; a layout violation is a stated failure."""
    try:
        offset = _system_offset(returncode, stdout)
    except TrackingLayoutError as exc:
        return {"status": "MEASUREMENT_FAILED", "offset_seconds": None, "reason": str(exc)}
    return {"status": "MEASURED_EXTERNAL", "offset_seconds": str(offset), "reason": None}


def v1_offset_defect(returncode: int, stdout: str, recorded_offset: str) -> dict:
    """Describe an unversioned stored offset beside the version 2 reading of its bytes."""
    reading = read_tracking_v2(returncode, stdout)
    stored = "the unversioned parser stored field index 3 (reference_time) as the offset; "
    if reading["offset_seconds"] is None:
        reason = (
            stored
            + f"no corrected offset exists because {CHRONY_TRACKING_CSV_V2} rejects the "
            + "retained output: "
            + reading["reason"]
        )
    else:
        reason = (
            stored
            + f"{CHRONY_TRACKING_CSV_V2} reads field index 4 (system_time_offset) of the "
            + "same retained bytes"
        )
    return {
        "code": OFFSET_FIELD_DEFECT_V1,
        "recorded_offset_seconds": recorded_offset,
        "recorded_field": TRACKING_FIELDS_V2[V1_OFFSET_INDEX],
        "corrected_offset_seconds": reading["offset_seconds"],
        "corrected_by": CHRONY_TRACKING_CSV_V2,
        "reason": reason,
    }
