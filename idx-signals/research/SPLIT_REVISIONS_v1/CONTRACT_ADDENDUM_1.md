# SPLIT_REVISIONS_v1, contract addendum 1

Written 2026-11-12 (UTC), AFTER the first dry run, and disclosed as such. `CONTRACT.md` is unchanged. The outputs of the first
run are kept in `results/first-run/`.

## What the first dry run showed

For four sealed sets (GNTA 2026-11-02, HUBC 2026-11-03, RCT 2026-11-06, SGRX 2026-10-30) the provider's response of
2026-11-12 holds no bar at all: metadata, an empty quote and no events. A second request about thirteen hours later
(2026-11-12 23:30 UTC) returned the same. Under `CONTRACT.md` such a response counts as a consulted source that lists no split, there is no reference bar,
and the set falls through to `NO_ACTION_FOUND`, group `REAL`. Nothing was checked for those four sets, and they were
reported as checked. The same holds for a response that carries an error instead of data.

This is the fault the independent review of the KODCHECK audit described: a rule that could not be evaluated was
treated as a rule that found nothing. The KODCHECK run of 2026-11-12 has the same four sets among its 150 "no
corporate action found".

## The correction

A response that holds no bar with a price is not evidence. In `split_assessments.assessment_record`, when `payload` is
`None`, or `split_units.payload_bars(payload)` contains no pair whose close is a number greater than zero, the
assessment is `NOT_ASSESSABLE` (group `UNRESOLVED`), with no previous session, units `UNKNOWN`, an empty `split`, and
`split_adjusted_ret1` and `later_factor` of `None`. The provider's split events in such a response are not used.

`split_units.classify` is unchanged: it is a pure function of what it is given, and the 178 pinned observations of the
KODCHECK challenge cases still describe it. The correction sits where a provider response becomes evidence.

## Consequences

- The four sets become `NOT_ASSESSABLE`. They stay in every view, as every unresolved set does, and are counted as
  unresolved. No set is added to or taken out of the corrected view, so the effect table's figures do not change.
- `propose_reassessments` skips a set whose ticker has no payload; a set whose payload holds no bar is not skipped: it
  is proposed as `NOT_ASSESSABLE` when that differs from its latest assessment. A provider that loses a name's history
  after a real assessment therefore produces a visible reassessment, not silence. This is deliberate.

## Tests

To be added by the independent test author from this text.
