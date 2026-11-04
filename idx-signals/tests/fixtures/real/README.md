# Real captured samples

Each file here is the exact output of an outside source, captured by a KOD process and
copied byte for byte. Nothing is edited, reformatted or invented. A new capture is a new
file; an existing file is never changed. Tests that need a malformed variant derive it in
the test from these bytes and say which edit they made.

## `chronyc_tracking_20261104T123000Z.txt`

| | |
|---|---|
| Source | `chronyc -c tracking` (chrony's CSV tracking report), real output |
| Host role | The production paper-observation server, during its one real-data commissioning capture on deployment commit `dbb27ea5c` (excluded from the 30-slot timing cohort) |
| Captured at | `2026-11-04T12:30:00.034011Z` (UTC, the `observed_at` the observer retained) |
| Retained as | The `stdout` field of clock evidence `clock_44499b11c6b067fc2239684750462ec5b9140169be0e71a34c4b56c6fda019c0` under `/var/lib/kod/commissioning/real-capture/timing/clocks/` (byte-identical in its restored backup), return code 0, empty stderr |
| Bytes | 141 bytes, one line ending in LF; SHA-256 `853d8cd5a2867a5d790f36f432257ac868c0493dba841bc3aab14989bad9d692` |

The 14 fields are chrony's: reference ID, reference name or address (the public time source
chrony followed, not the KOD server), stratum, reference time, system time offset, last
offset, RMS offset, frequency, residual frequency, skew, root delay, root dispersion, update
interval and leap status. Field index 4 is the system time offset, `0.002434953` seconds.
Field index 3 is the reference time, `1793795343.592268319`; the unversioned parser stored
that value as the offset (defect `OFFSET_FIELD_DEFECT_V1`).

`tests/test_chrony_tracking.py` rebuilds the production evidence object from these bytes and
checks that its hash is the evidence identity the production journal recorded, so the file
cannot drift from the original without that test failing.
