# Addendum 4 — retain a finding when its supporting event disappears

Added 13 November 2026 following independent review of revision 3.

A readable event list can still omit the particular split that supported an earlier finding. With identical prices,
revision 3 lets an unrelated older event replace that finding with `UNITS_INCONSISTENT` and restores the artifact.

For reassessments of an `EVENT_BASED` standing finding with a stored split session:

- Check whether the response contains a readable event at that supporting effective session. The ratio may change.
- If that session is missing, retain the standing finding and append `NOT_ASSESSABLE` with
  `evidence_gap = SPLIT_EVENT_MISSING`.
- Allow a replacement when the classifier positively reconciles the previous close (`units = UNCHANGED`). This
  preserves a provider date correction accompanied by coherent price evidence, including the revision-3 reversal
  fixtures. A large move may still be `UNEXPLAINED_EXTREME_MOVE` after its old split explanation is disproved.
- Repeated identical gaps produce no duplicate reassessment. Restored evidence supersedes the gap record.

The absent/malformed-list handling in addendum 3 also applies. Old records without `evidence_gap` remain readable.
First assessments and the frozen classifier retain their existing interpretation. A withdrawal with no listed
replacement still needs further evidence before it can reverse an established finding.

The independently authored `tests/test_split_evidence_continuity.py` reproduces the omitted-event cases and covers
ratio correction, a post-split previous close, repeated gaps, restoration and legacy records. Existing revision-3
tests additionally cover corrected event dates with reconciled price evidence.
