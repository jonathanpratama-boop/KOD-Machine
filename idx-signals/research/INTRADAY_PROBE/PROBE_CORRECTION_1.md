# Probe correction 1 (2026-10-18, before any Alpaca data for the sample is fetched)

Code review of `probe.py` (b89c51a) found four implementation faults. `probe.py` is frozen and was never run
with `--alpaca`; `probe_v2.py` replaces that mode. `sample.csv`, the checks and the GO thresholds in
PROBE_SPEC.md are unchanged. The halt result in `out/halts.csv` / `out/SUMMARY.json` (b89c51a) stands and is
referenced, not rewritten.

1. **Window boundaries.** The API returns the bar stamped at the window's end (a 13th first-hour bar).
   v2 keeps only bars with 09:30 <= start < 10:30 (first hour, expect 12) and 09:30 <= start < 16:00
   (session, expect 78); early closes are recorded, not counted as missing.
2. **Historical identity.** v1 recorded only today's asset metadata (today's FB is an ETF). v2 requests
   every series with `asof=<date>` (the provider's symbol mapping on that date) and records, per pair:
   - for panel names: whether the last regular-session SIP bar's close matches the panel's as-traded close
     for that date within 2% (same security) - a level check on already-used discovery data, not a return;
   - for the identity set (not in the panel, so no reference): `UNVERIFIED` unless a dated source exists;
     no data before a known listing is `NOT YET LISTED` only if a dated listing source says so, else
     `UNKNOWN`. Today's asset record is kept as context only.
3. **Coverage denominator.** Expected activity comes from the panel (the name has a bar that date), fixed
   before fetching. Completeness = pairs with all 12 first-hour bars / pairs expected to trade, so a name
   with no data at all counts as a failure. Identity-set pairs, which have no independent expectation,
   are reported separately as DATA / NO DATA / UNKNOWN.
4. **Per-endpoint status, no overwrite.** Each endpoint's HTTP status, page count and completeness (every
   page fetched without error) is kept per pair; no `max()` collapse. Each execution writes a new
   `out/run-<UTC stamp>/` directory; nothing earlier is rewritten.

Status language: feasibility is INCOMPLETE until the Alpaca checks run and the 2022-06-03 halt gap is
resolved (11 of 12 dates do not meet the all-dates requirement; "archive gap" is an inference). Archive
backup is PENDING until a durable copy outside this container is verified against the manifest.
