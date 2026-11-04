"""Versioned chrony interpretation, separate from retained historical claims.

The Reference ID line supplies *two* CSV fields: ID and address. Consequently
field 3 is the reference epoch and field 4 is the system-time offset. The
chronyc manual documents the fields, CSV units and conditional accuracy bound:
https://chrony-project.org/doc/4.9/chronyc.html

This is local chrony evidence, not an independent proof of absolute time. No
function here changes the clock, makes a request or rewrites old observations.
"""

from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
import re

PARSER_VERSION = "CHRONY_TRACKING_CSV_14_V1"


def parse_tracking(stdout: str, returncode: int = 0) -> dict:
    """Parse the declared 14-field format or reject it; never guess columns."""
    if type(returncode) is not int or returncode != 0:
        raise ValueError("chronyc did not complete successfully")
    if not isinstance(stdout, str) or len(stdout) > 16384:
        raise ValueError("invalid chronyc output")
    try:
        rows = list(csv.reader(stdout.strip().splitlines(), strict=True))
    except csv.Error as exc:
        raise ValueError("invalid chronyc CSV") from exc
    if len(rows) != 1 or len(rows[0]) != 14:
        raise ValueError("unsupported chronyc tracking format; expected 14 CSV fields")
    fields = [field.strip() for field in rows[0]]
    if fields[13] != "Normal":
        raise ValueError("chrony does not report normal synchronization")
    if not re.fullmatch(r"[0-9A-Fa-f]{8}", fields[0]):
        raise ValueError("invalid chrony reference ID")
    if fields[0].upper() in {"00000000", "7F7F0101"}:
        raise ValueError("chrony has no external reference")
    if not fields[2].isdigit() or not 1 <= int(fields[2]) <= 15:
        raise ValueError("invalid synchronized chrony stratum")
    try:
        values = [Decimal(field) for field in fields[3:13]]
    except InvalidOperation as exc:
        raise ValueError("chrony measurement is not numeric") from exc
    if any(not value.is_finite() for value in values):
        raise ValueError("chrony measurement must be finite")
    reference, offset, last, rms, frequency, residual, skew, delay, dispersion, interval = values
    if reference <= 0 or any(value < 0 for value in (rms, skew, dispersion, interval)):
        raise ValueError("invalid chrony measurement range")
    # Absolute delay is conservative for historical chrony variants that can
    # report a negative path delay. The bound assumes a correct reference clock.
    try:
        bound = abs(offset) + dispersion + abs(delay) / 2
    except ArithmeticError as exc:
        raise ValueError("chrony measurement exceeds supported numeric range") from exc
    return {
        "parser_version": PARSER_VERSION,
        "reference_id": fields[0].upper(),
        "reference_address": fields[1],
        "stratum": int(fields[2]),
        "reference_epoch_seconds": str(reference),
        "system_time_offset_seconds": str(offset),
        "last_offset_seconds": str(last),
        "rms_offset_seconds": str(rms),
        "frequency_ppm": str(frequency),
        "residual_frequency_ppm": str(residual),
        "skew_ppm": str(skew),
        "root_delay_seconds": str(delay),
        "root_dispersion_seconds": str(dispersion),
        "update_interval_seconds": str(interval),
        "conditional_error_bound_seconds": str(bound),
        "bound_assumption": "reference clock is correct; local chrony report only",
    }


def assess_clock(raw: dict, claim: dict) -> dict:
    """Check the original claim and derive a separate, non-mutating assessment.

    Old evidence has no parser version. Its old offset is checked against the old
    column solely to verify correspondence; it never becomes a valid measurement.
    """
    version = raw.get("parser_version")
    if version not in (None, PARSER_VERSION):
        raise ValueError("unsupported retained clock parser version")
    measured = claim.get("status") == "MEASURED_EXTERNAL"
    if measured:
        try:
            original = Decimal(str(claim["offset_seconds"]))
            if not original.is_finite():
                raise ValueError("nonfinite original clock offset")
            if version is None:
                fields = raw["stdout"].strip().split(",")
                if (
                    raw.get("returncode") != 0
                    or len(fields) < 13
                    or fields[-1].strip() != "Normal"
                    or not Decimal(fields[3]).is_finite()
                    or Decimal(fields[3]) != original
                ):
                    raise ValueError("legacy clock claim differs from retained raw output")
        except (InvalidOperation, IndexError, KeyError, TypeError) as exc:
            raise ValueError("invalid original clock claim") from exc
    try:
        parsed = parse_tracking(raw.get("stdout"), raw.get("returncode"))
    except ValueError as exc:
        if version == PARSER_VERSION and measured:
            raise ValueError("clock measurement differs from retained raw output") from exc
        return {
            "status": "UNKNOWN",
            "parser_version": PARSER_VERSION,
            "original_offset_seconds": claim.get("offset_seconds"),
            "original_claim_valid": False,
            "system_time_offset_seconds": None,
            "conditional_error_bound_seconds": None,
            "reason": str(exc),
        }
    if version == PARSER_VERSION:
        if measured and original != Decimal(parsed["system_time_offset_seconds"]):
            raise ValueError("clock measurement differs from retained raw output")
        if not measured:
            raise ValueError("normal versioned clock output has an inconsistent failure claim")
        state, reason = "VERIFIED", "versioned measurement matches retained raw output"
    else:
        state = "DERIVED_FROM_RETAINED_RAW"
        reason = "legacy offset used the reference-time column; original claim is not a measurement"
    return {
        **parsed,
        "status": state,
        "original_offset_seconds": claim.get("offset_seconds"),
        "original_claim_valid": version == PARSER_VERSION and measured,
        "reason": reason,
    }
