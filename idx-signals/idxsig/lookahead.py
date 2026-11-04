"""Truncation and scramble checks: do a study's past decisions depend on later information?

A study under test is a function ``decide(data) -> decisions``. ``data`` is the study's
input table with one time column. ``decisions`` is a table with a decision-time column
and key columns that identify each decision once. Both checks run ``decide`` twice on
the full data (the two runs must agree, or the check stops), then once per cutoff T on
perturbed data, and compare every decision dated at or before T:

* truncation removes the rows dated after T, and sets missing any lagged value not yet
  known at T (for example a forward return stored on its signal row);
* scramble keeps every row and replaces those same values with seeded noise, for
  studies that cannot run on a shortened table.

``compare_decisions`` compares two decision tables that a study already wrote, one
from the full data and one from data cut at T, without running anything.

A PASS shows only that, on this data and at these cutoffs, no decision dated at or
before T changed when information after T was removed or replaced. It does not show
that the input data was itself available at its stated time (publication lags,
revisions, survivorship), that other data or cutoffs are clean, that code paths this
data never reaches are clean, or that the scoring of decisions is correct. Scramble
noise is random: a different seed can expose a leak that one seed happened to hide.
A check that cannot run as specified raises ``LookaheadCheckError``; it never passes.
This module runs no study by itself, reads no files and makes no network calls.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from numbers import Real

import numpy as np
import pandas as pd

VERSION = "KOD-LOOKAHEAD-CHECK-v1"
TRUNCATION = "TRUNCATION"
SCRAMBLE = "SCRAMBLE"
COMPARE = "COMPARE"
ONLY_IN_REFERENCE = "ONLY_IN_REFERENCE"
ONLY_IN_CANDIDATE = "ONLY_IN_CANDIDATE"
VALUE_DIFFERS = "VALUE_DIFFERS"
SCRAMBLE_KINDS = "fiub"  # numpy float, signed and unsigned integer, bool
# pandas nullable dtypes: numbers and bools whose missing value is pd.NA. The canonical
# panel (idxsig.panel.load) holds its prices and volumes as Int64.
NULLABLE_DTYPES = (
    pd.Int8Dtype,
    pd.Int16Dtype,
    pd.Int32Dtype,
    pd.Int64Dtype,
    pd.UInt8Dtype,
    pd.UInt16Dtype,
    pd.UInt32Dtype,
    pd.UInt64Dtype,
    pd.Float32Dtype,
    pd.Float64Dtype,
    pd.BooleanDtype,
)

Decide = Callable[[pd.DataFrame], pd.DataFrame]


class LookaheadCheckError(ValueError):
    """The check could not run as specified; this is not a verdict on the study."""


@dataclass(frozen=True)
class Difference:
    """One decision that differs; ``reference`` and ``candidate`` are display text."""

    kind: str
    decision_time: str
    key: tuple[str, ...]
    column: str | None
    reference: str | None
    candidate: str | None


@dataclass(frozen=True)
class CutoffResult:
    """Decisions dated at or before one cutoff: reference run against candidate run.

    ``rows_removed`` and ``values_hidden`` apply to truncation, ``values_replaced`` to
    scramble; a field that does not apply to the check is None. ``first_difference`` is
    the earliest differing decision by decision time, then by key text.
    """

    cutoff: str
    rows_removed: int | None
    values_hidden: int | None
    values_replaced: int | None
    reference_rows: int
    candidate_rows: int
    reference_in_scope: int
    candidate_in_scope: int
    decisions_compared: int
    decisions_differing: int
    first_difference: Difference | None


@dataclass(frozen=True)
class LookaheadReport:
    """Everything one check compared, in cutoff order, with the settings it used.

    For scramble, ``scrambled_columns`` and ``unscrambled_columns`` together name every
    data column, so a column the noise never reached is stated, not implied; both are
    empty for the other checks.
    """

    check: str
    time_column: str
    key_columns: tuple[str, ...]
    value_columns: tuple[str, ...]
    assume_utc: bool
    input_rows: int | None
    scrambled_columns: tuple[str, ...]
    unscrambled_columns: tuple[str, ...]
    value_lags: tuple[tuple[str, str], ...]
    seed: int | None
    missing_share: float | None
    cutoffs: tuple[CutoffResult, ...]

    @property
    def verdict(self) -> str:
        return "LEAK" if self.first_leak is not None else "PASS"

    @property
    def first_leak(self) -> CutoffResult | None:
        """The earliest cutoff at which any compared decision differs."""
        return next((c for c in self.cutoffs if c.decisions_differing), None)

    def to_dict(self) -> dict:
        out = asdict(self)
        out["value_lags"] = dict(self.value_lags)
        leak = self.first_leak
        out["first_leak"] = (
            None if leak is None else {"cutoff": leak.cutoff, **asdict(leak.first_difference)}
        )
        return {"version": VERSION, "verdict": self.verdict, **out}


@dataclass(frozen=True)
class _Decisions:
    """A validated decision table: key -> (UTC decision time, values by column)."""

    columns: tuple[str, ...]
    rows: dict[tuple, tuple[pd.Timestamp, tuple]]


def _iso(stamp: pd.Timestamp) -> str:
    return stamp.isoformat().replace("+00:00", "Z")


def _first_label(index: pd.Index, mask: np.ndarray):
    """The first flagged index label, as a plain Python value for error messages."""
    label = index[mask][0]
    return label.item() if isinstance(label, np.generic) else label


def _text(value) -> str | None:
    if _missing(value):
        return None
    if isinstance(value, pd.Timestamp):
        return _iso(value) if value.tzinfo is not None else value.isoformat()
    if isinstance(value, float):
        return repr(value)
    return str(value)


def _missing(value) -> bool:
    if not pd.api.types.is_scalar(value):
        raise LookaheadCheckError(f"decision values must be scalars, not {type(value).__name__}")
    return bool(pd.isna(value))


def _naive(label: str, value) -> LookaheadCheckError:
    return LookaheadCheckError(
        f"{label} has a time without a UTC offset ({value!r}); write it with an offset, or "
        "pass assume_utc=True only if every naive time is UTC"
    )


def _timestamp(value, label: str, assume_utc: bool) -> pd.Timestamp:
    """One aware UTC timestamp; epoch numbers are refused because their unit is unknown."""
    if isinstance(value, bool) or not isinstance(value, (str, datetime, np.datetime64)):
        raise LookaheadCheckError(
            f"{label} must hold timestamps or ISO 8601 text, not {type(value).__name__} "
            f"({value!r}); epoch numbers are refused because their unit is ambiguous"
        )
    try:
        stamp = pd.Timestamp(value)
    except (TypeError, ValueError) as exc:
        raise LookaheadCheckError(f"{label} has an unparseable time {value!r}") from exc
    if pd.isna(stamp):
        raise LookaheadCheckError(f"{label} has a missing time {value!r}")
    if stamp.tzinfo is None:
        if not assume_utc:
            raise _naive(label, value)
        return stamp.tz_localize("UTC")
    return stamp.tz_convert("UTC")


def _utc_series(values: pd.Series, label: str, assume_utc: bool) -> pd.Series:
    """Parse a time column to aware UTC; a missing or naive time is never guessed."""
    missing = values.isna().to_numpy()
    if missing.any():
        raise LookaheadCheckError(
            f"{label} is missing at row {_first_label(values.index, missing)!r}"
        )
    if isinstance(values.dtype, pd.DatetimeTZDtype):
        return values.dt.tz_convert("UTC")
    if pd.api.types.is_datetime64_dtype(values.dtype):
        if not assume_utc:
            raise _naive(label, values.iloc[0] if len(values) else None)
        return values.dt.tz_localize("UTC")
    if len(values) == 0:
        return pd.Series([], index=values.index, dtype="datetime64[ns, UTC]")
    parsed = {value: _timestamp(value, label, assume_utc) for value in pd.unique(values)}
    return pd.Series(
        pd.DatetimeIndex([parsed[value] for value in values]), index=values.index
    ).astype("datetime64[ns, UTC]")


def _cutoffs(values: Sequence, assume_utc: bool) -> tuple[pd.Timestamp, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence) or not values:
        raise LookaheadCheckError("cutoffs must be a nonempty sequence of times")
    stamps = [_timestamp(value, "cutoff", assume_utc) for value in values]
    if len(set(stamps)) != len(stamps):
        raise LookaheadCheckError("cutoffs must be distinct")
    return tuple(sorted(stamps))


def _key_columns(key_columns: Sequence[str], time_column: str) -> tuple[str, ...]:
    if isinstance(key_columns, str) or not isinstance(key_columns, Sequence) or not key_columns:
        raise LookaheadCheckError("key_columns must be a nonempty sequence of column names")
    if not all(isinstance(column, str) and column for column in key_columns):
        raise LookaheadCheckError("key column names must be nonempty strings")
    if len(set(key_columns)) != len(key_columns):
        raise LookaheadCheckError("key columns must be distinct")
    if not isinstance(time_column, str) or not time_column:
        raise LookaheadCheckError("time_column must be a nonempty string")
    return tuple(key_columns)


def _decisions(
    table, label: str, time_column: str, key_columns: tuple[str, ...], assume_utc: bool
) -> _Decisions:
    """Validate one decision table; the index is ignored, keys must be columns."""
    if not isinstance(table, pd.DataFrame):
        raise LookaheadCheckError(f"{label} must be a pandas DataFrame, not {type(table).__name__}")
    if not table.columns.is_unique:
        raise LookaheadCheckError(f"{label} has duplicate column names")
    absent = [c for c in (time_column, *key_columns) if c not in table.columns]
    if absent:
        raise LookaheadCheckError(
            f"{label} lacks columns {absent}; keys held in the index need reset_index()"
        )
    for column in key_columns:
        missing = table[column].isna().to_numpy()
        if missing.any():
            raise LookaheadCheckError(
                f"{label} key column {column!r} is missing at row "
                f"{_first_label(table.index, missing)!r}"
            )
    times = _utc_series(table[time_column], f"{label} column {time_column!r}", assume_utc)
    columns = tuple(c for c in table.columns if c not in key_columns)
    data = {c: table[c].tolist() for c in table.columns}
    data[time_column] = times.tolist()
    rows: dict[tuple, tuple[pd.Timestamp, tuple]] = {}
    for position, stamp in enumerate(data[time_column]):
        key = tuple(data[c][position] for c in key_columns)
        if key in rows:
            text = tuple(_text(part) for part in key)
            raise LookaheadCheckError(
                f"{label} has duplicate key {text}; key columns must identify one decision"
            )
        rows[key] = (stamp, tuple(data[c][position] for c in columns))
    return _Decisions(columns, rows)


def _same_columns(reference: _Decisions, candidate: _Decisions, what: str) -> _Decisions:
    """Return ``candidate`` with its values in the reference column order."""
    if set(reference.columns) != set(candidate.columns):
        raise LookaheadCheckError(
            f"{what} have different columns: only in reference "
            f"{sorted(set(reference.columns) - set(candidate.columns))}, only in candidate "
            f"{sorted(set(candidate.columns) - set(reference.columns))}"
        )
    order = [candidate.columns.index(c) for c in reference.columns]
    rows = {k: (t, tuple(v[i] for i in order)) for k, (t, v) in candidate.rows.items()}
    return _Decisions(reference.columns, rows)


def _same(a, b) -> bool:
    """Two missing values are equal; otherwise values are compared with ``==``."""
    a_missing, b_missing = _missing(a), _missing(b)
    if a_missing or b_missing:
        return a_missing and b_missing
    try:
        equal = a == b
    except TypeError:
        return False
    if not isinstance(equal, (bool, np.bool_)):
        raise LookaheadCheckError(f"decision values {a!r} and {b!r} do not compare as scalars")
    return bool(equal)


def _differences(
    reference: _Decisions, candidate: _Decisions, cutoff: pd.Timestamp | None
) -> tuple[int, int, int, list[Difference]]:
    """Every in-scope key of either side, compared against the other side's whole table.

    A key in scope on one side and present out of scope on the other differs in its
    decision time, so it is a value difference, not a missing decision. Differences are
    ordered by decision time, then key text, then key repr (1 and "1" share their text).
    """

    def in_scope(table: _Decisions) -> set[tuple]:
        return {k for k, (t, _) in table.rows.items() if cutoff is None or t <= cutoff}

    ref_scope, cand_scope = in_scope(reference), in_scope(candidate)
    union = ref_scope | cand_scope
    found = []
    for key in union:
        ref, cand = reference.rows.get(key), candidate.rows.get(key)
        text = tuple(_text(part) for part in key)
        order = tuple(repr(part) for part in key)
        if cand is None or ref is None:
            kind = ONLY_IN_REFERENCE if cand is None else ONLY_IN_CANDIDATE
            stamp = (ref or cand)[0]
            difference = Difference(kind, _iso(stamp), text, None, None, None)
            found.append((stamp, text, order, difference))
            continue
        for column, a, b in zip(reference.columns, ref[1], cand[1]):
            if not _same(a, b):
                stamp = min(ref[0], cand[0])
                difference = Difference(
                    VALUE_DIFFERS, _iso(stamp), text, column, _text(a), _text(b)
                )
                found.append((stamp, text, order, difference))
                break
    found.sort(key=lambda item: item[:3])
    return len(ref_scope), len(cand_scope), len(union), [item[3] for item in found]


def _result(
    reference: _Decisions,
    candidate: _Decisions,
    cutoff: pd.Timestamp,
    *,
    rows_removed: int | None = None,
    values_hidden: int | None = None,
    values_replaced: int | None = None,
) -> CutoffResult:
    ref_n, cand_n, compared, found = _differences(reference, candidate, cutoff)
    return CutoffResult(
        cutoff=_iso(cutoff),
        rows_removed=rows_removed,
        values_hidden=values_hidden,
        values_replaced=values_replaced,
        reference_rows=len(reference.rows),
        candidate_rows=len(candidate.rows),
        reference_in_scope=ref_n,
        candidate_in_scope=cand_n,
        decisions_compared=compared,
        decisions_differing=len(found),
        first_difference=found[0] if found else None,
    )


def compare_decisions(
    reference: pd.DataFrame,
    candidate: pd.DataFrame,
    *,
    time_column: str,
    key_columns: Sequence[str],
    cutoff: str | datetime,
    assume_utc: bool = False,
) -> LookaheadReport:
    """Compare two decision tables on every decision dated at or before ``cutoff``.

    ``reference`` should come from the full data and ``candidate`` from the same study
    run on data cut at ``cutoff``; producing them that way is the caller's job. Rows
    and columns may be in any order. Decisions after the cutoff are counted, not compared.
    """
    keys = _key_columns(key_columns, time_column)
    stamp = _cutoffs([cutoff], assume_utc)[0]
    ref = _decisions(reference, "reference decisions", time_column, keys, assume_utc)
    cand = _decisions(candidate, "candidate decisions", time_column, keys, assume_utc)
    result = _result(ref, _same_columns(ref, cand, "decision tables"), stamp)
    if not result.decisions_compared:
        raise LookaheadCheckError(
            f"no decision in either table is dated at or before {_iso(stamp)}"
        )
    return LookaheadReport(
        check=COMPARE,
        time_column=time_column,
        key_columns=keys,
        value_columns=ref.columns,
        assume_utc=assume_utc,
        input_rows=None,
        scrambled_columns=(),
        unscrambled_columns=(),
        value_lags=(),
        seed=None,
        missing_share=None,
        cutoffs=(result,),
    )


def _input(data, time_column: str, assume_utc: bool) -> pd.Series:
    if not isinstance(data, pd.DataFrame):
        raise LookaheadCheckError(f"data must be a pandas DataFrame, not {type(data).__name__}")
    if data.empty:
        raise LookaheadCheckError("data is empty; there is nothing to cut at a cutoff")
    if not data.columns.is_unique:
        raise LookaheadCheckError("data has duplicate column names")
    if time_column not in data.columns:
        raise LookaheadCheckError(f"data lacks its time column {time_column!r}")
    return _utc_series(data[time_column], f"data column {time_column!r}", assume_utc)


def _scrambleable(dtype) -> bool:
    """A numpy float, integer or bool dtype, or a pandas nullable one."""
    if isinstance(dtype, np.dtype):
        return dtype.kind in SCRAMBLE_KINDS
    return isinstance(dtype, NULLABLE_DTYPES)


def _can_be_missing(dtype) -> bool:
    """A numpy float dtype (NaN) or a pandas nullable dtype (pd.NA)."""
    if isinstance(dtype, np.dtype):
        return dtype.kind == "f"
    return isinstance(dtype, NULLABLE_DTYPES)


def _lags(value_lags, data: pd.DataFrame, time_column: str) -> dict[str, pd.Timedelta]:
    """Columns whose value on a row dated t is first known at t + lag."""
    if value_lags is None:
        return {}
    if not isinstance(value_lags, Mapping):
        raise LookaheadCheckError("value_lags must map column names to positive timedeltas")
    lags = {}
    for column, lag in value_lags.items():
        if column not in data.columns or column == time_column:
            raise LookaheadCheckError(f"lagged column {column!r} is not a data value column")
        if not _can_be_missing(data[column].dtype):
            raise LookaheadCheckError(
                f"lagged column {column!r} has dtype {data[column].dtype}, which cannot hold a "
                "missing value; store it as a numpy float or pandas nullable column (a flag as "
                "astype('boolean')) so a value not yet known can be set missing"
            )
        if not isinstance(lag, timedelta) or pd.isna(lag) or lag <= timedelta(0):
            raise LookaheadCheckError(
                f"lag for {column!r} must be a positive timedelta, not {lag!r}"
            )
        lags[column] = pd.Timedelta(lag)
    return dict(sorted(lags.items()))


def _run(
    decide: Decide,
    data: pd.DataFrame,
    label: str,
    time_column: str,
    keys: tuple[str, ...],
    assume_utc: bool,
) -> _Decisions:
    """Each run gets its own copy, so a study that edits its input cannot affect the next."""
    return _decisions(decide(data.copy(deep=True)), label, time_column, keys, assume_utc)


def _reference(
    decide: Decide,
    data: pd.DataFrame,
    time_column: str,
    keys: tuple[str, ...],
    assume_utc: bool,
    cutoffs: tuple[pd.Timestamp, ...],
) -> _Decisions:
    """Two full runs must agree before a difference can be attributed to look-ahead."""
    if not callable(decide):
        raise LookaheadCheckError("decide must be callable as decide(data) -> DataFrame")
    first = _run(decide, data, "decisions on the full data", time_column, keys, assume_utc)
    second = _run(
        decide, data, "repeated decisions on the full data", time_column, keys, assume_utc
    )
    second = _same_columns(first, second, "two runs on the full data")
    _, _, _, found = _differences(first, second, None)
    if found:
        raise LookaheadCheckError(
            f"decide is not deterministic: two runs on the same full data differ first at "
            f"{asdict(found[0])}; fix its randomness before checking for look-ahead"
        )
    if not first.rows:
        raise LookaheadCheckError("decide made no decisions on the full data; nothing to check")
    earliest = min(t for t, _ in first.rows.values())
    for cutoff in cutoffs:
        if cutoff < earliest:
            raise LookaheadCheckError(
                f"cutoff {_iso(cutoff)} is before the first decision ({_iso(earliest)}); "
                "no full-data decision would be compared"
            )
    return first


def _vacuous(cutoff: pd.Timestamp, last: pd.Timestamp) -> LookaheadCheckError:
    return LookaheadCheckError(
        f"cutoff {_iso(cutoff)} changes no input value (the last input time is {_iso(last)}); "
        "every cutoff must precede some input information"
    )


def _report(
    check: str,
    time_column: str,
    keys: tuple[str, ...],
    reference: _Decisions,
    assume_utc: bool,
    data: pd.DataFrame,
    results: list[CutoffResult],
    lags: dict[str, pd.Timedelta],
    scrambled_columns: tuple[str, ...] = (),
    unscrambled_columns: tuple[str, ...] = (),
    seed: int | None = None,
    missing_share: float | None = None,
) -> LookaheadReport:
    return LookaheadReport(
        check=check,
        time_column=time_column,
        key_columns=keys,
        value_columns=reference.columns,
        assume_utc=assume_utc,
        input_rows=len(data),
        scrambled_columns=scrambled_columns,
        unscrambled_columns=unscrambled_columns,
        value_lags=tuple((c, lag.isoformat()) for c, lag in lags.items()),
        seed=seed,
        missing_share=missing_share,
        cutoffs=tuple(results),
    )


def truncation_check(
    decide: Decide,
    data: pd.DataFrame,
    *,
    data_time_column: str,
    time_column: str,
    key_columns: Sequence[str],
    cutoffs: Sequence,
    value_lags: Mapping[str, timedelta] | None = None,
    assume_utc: bool = False,
) -> LookaheadReport:
    """Rerun ``decide`` with input rows dated after each cutoff removed.

    Rows are kept by a time mask, never by position, so unsorted input is cut correctly.
    A lagged column's value on a kept row dated t is set missing when t + lag > cutoff.
    """
    keys = _key_columns(key_columns, time_column)
    stamps = _cutoffs(cutoffs, assume_utc)
    times = _input(data, data_time_column, assume_utc)
    lags = _lags(value_lags, data, data_time_column)
    plans = []
    for cutoff in stamps:
        keep = (times <= cutoff).to_numpy()
        hidden = {c: ((times + lag) > cutoff).to_numpy() & keep for c, lag in lags.items()}
        removed, blanked = int((~keep).sum()), sum(int(mask.sum()) for mask in hidden.values())
        if removed + blanked == 0:
            raise _vacuous(cutoff, times.max())
        plans.append((cutoff, keep, hidden, removed, blanked))
    reference = _reference(decide, data, time_column, keys, assume_utc, stamps)
    results = []
    for cutoff, keep, hidden, removed, blanked in plans:
        cut = data.copy(deep=True)
        for column, mask in hidden.items():
            cut[column] = cut[column].mask(mask)  # NaN or pd.NA; the dtype is kept
        cut = cut.iloc[np.flatnonzero(keep)]
        label = f"decisions on data cut at {_iso(cutoff)}"
        candidate = _same_columns(
            reference, _run(decide, cut, label, time_column, keys, assume_utc), label
        )
        results.append(
            _result(reference, candidate, cutoff, rows_removed=removed, values_hidden=blanked)
        )
    return _report(TRUNCATION, time_column, keys, reference, assume_utc, data, results, lags)


def _scrambled(
    data: pd.DataFrame, time_column: str, keys: tuple[str, ...], columns
) -> tuple[str, ...]:
    """The named columns, or by default every scrambleable column but the time and keys.

    Decision key columns that are also data columns identify rows (an integer asset id);
    noise in them would only produce duplicate keys after the cutoff. A default column
    that holds numbers in a dtype this module cannot scramble (pyarrow, sparse, complex)
    is refused: skipping it would let a leak through it pass unseen.
    """
    if columns is None:
        chosen = []
        for column in data.columns:
            if column == time_column or column in keys:
                continue
            dtype = data[column].dtype
            if _scrambleable(dtype):
                chosen.append(column)
            elif pd.api.types.is_numeric_dtype(dtype) or pd.api.types.is_bool_dtype(dtype):
                raise LookaheadCheckError(
                    f"column {column!r} holds numbers in dtype {dtype}, which cannot be "
                    "scrambled; convert it to a numpy or pandas nullable dtype, or name the "
                    "columns to scramble with columns=[...]"
                )
        if not chosen:
            raise LookaheadCheckError("data has no numeric or bool column to scramble")
        return tuple(chosen)
    if isinstance(columns, str) or not isinstance(columns, Sequence) or not columns:
        raise LookaheadCheckError("columns must be a nonempty sequence of column names")
    if len(set(columns)) != len(columns):
        raise LookaheadCheckError("scrambled columns must be distinct")
    for column in columns:
        if column not in data.columns or column == time_column:
            raise LookaheadCheckError(f"scrambled column {column!r} is not a data value column")
        if not _scrambleable(data[column].dtype):
            raise LookaheadCheckError(
                f"scrambled column {column!r} has dtype {data[column].dtype}; only numpy "
                "float, integer and bool columns and pandas nullable Int, UInt, Float and "
                "boolean columns can be scrambled"
            )
    return tuple(columns)


def _noise(values: pd.Series, count: int, rng: np.random.Generator, missing_share: float):
    """``count`` seeded values over the column's observed range, in the column's dtype.

    A column that can hold a missing value (numpy float, every pandas nullable dtype)
    also has each drawn value set missing with probability ``missing_share``.
    """
    dtype = values.dtype
    numpy_dtype = dtype if isinstance(dtype, np.dtype) else dtype.numpy_dtype
    observed = values.dropna().to_numpy(dtype=numpy_dtype)
    if numpy_dtype.kind == "b":
        noise = rng.integers(0, 2, size=count).astype(bool)
    elif numpy_dtype.kind in "iu":
        low, high = (int(observed.min()), int(observed.max())) if observed.size else (0, 1)
        noise = rng.integers(low, max(high, low + 1), size=count, endpoint=True, dtype=numpy_dtype)
    else:
        finite = observed[np.isfinite(observed)]
        low, high = (float(finite.min()), float(finite.max())) if finite.size else (0.0, 1.0)
        if low == high:
            low, high = low - 1.0, high + 1.0
        noise = rng.uniform(low, high, size=count).astype(numpy_dtype)
    if not _can_be_missing(dtype):
        return noise
    missing = rng.random(count) < missing_share
    if isinstance(dtype, np.dtype):
        noise[missing] = np.nan
        return noise
    noise = pd.array(noise, dtype=dtype)
    noise[missing] = pd.NA
    return noise


def scramble_check(
    decide: Decide,
    data: pd.DataFrame,
    *,
    data_time_column: str,
    time_column: str,
    key_columns: Sequence[str],
    cutoffs: Sequence,
    seed: int = 0,
    columns: Sequence[str] | None = None,
    value_lags: Mapping[str, timedelta] | None = None,
    missing_share: float = 0.25,
    assume_utc: bool = False,
) -> LookaheadReport:
    """Rerun ``decide`` with every value after each cutoff replaced by seeded noise.

    ``columns`` defaults to every numpy or pandas nullable numeric or bool column except
    the time column and any decision key column; a column holding numbers in any other
    dtype is refused, not skipped.
    Rows, the time column and every unscrambled column (such as text identifiers) are
    kept, so presence of later rows is unchanged; truncation is the check for that. The
    report names both sets. A value on a row dated t counts as after the cutoff when
    t + lag > cutoff (lag zero unless given). Numbers and bools get uniform draws over the
    column's observed range, in the column's own dtype; a column that can hold a missing
    value (numpy float, pandas nullable) also gets a ``missing_share`` chance of becoming
    missing. Noise for each (cutoff, column) pair is drawn from
    ``numpy.random.default_rng([seed, cutoff number, column position])``.
    """
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise LookaheadCheckError("seed must be a nonnegative integer")
    if (
        isinstance(missing_share, bool)
        or not isinstance(missing_share, Real)
        or not 0 <= missing_share < 1
    ):
        raise LookaheadCheckError("missing_share must be a number in [0, 1)")
    keys = _key_columns(key_columns, time_column)
    stamps = _cutoffs(cutoffs, assume_utc)
    times = _input(data, data_time_column, assume_utc)
    chosen = _scrambled(data, data_time_column, keys, columns)
    lags = _lags(value_lags, data, data_time_column)
    unscrambled = sorted(set(lags) - set(chosen))
    if unscrambled:
        raise LookaheadCheckError(f"lagged columns {unscrambled} must also be scrambled")
    plans = []
    for number, cutoff in enumerate(stamps):
        after = {c: ((times + lags.get(c, pd.Timedelta(0))) > cutoff).to_numpy() for c in chosen}
        replaced = sum(int(mask.sum()) for mask in after.values())
        if replaced == 0:
            raise _vacuous(cutoff, times.max())
        plans.append((number, cutoff, after, replaced))
    reference = _reference(decide, data, time_column, keys, assume_utc, stamps)
    results = []
    for number, cutoff, after, replaced in plans:
        noisy = data.copy(deep=True)
        for column, mask in after.items():
            values = noisy[column].array.copy()
            rng = np.random.default_rng([seed, number, data.columns.get_loc(column)])
            values[mask] = _noise(noisy[column], int(mask.sum()), rng, missing_share)
            noisy[column] = values
        label = f"decisions on data scrambled after {_iso(cutoff)}"
        candidate = _same_columns(
            reference, _run(decide, noisy, label, time_column, keys, assume_utc), label
        )
        results.append(_result(reference, candidate, cutoff, values_replaced=replaced))
    return _report(
        SCRAMBLE,
        time_column,
        keys,
        reference,
        assume_utc,
        data,
        results,
        lags,
        scrambled_columns=chosen,
        unscrambled_columns=tuple(c for c in data.columns if c not in chosen),
        seed=seed,
        missing_share=float(missing_share),
    )
