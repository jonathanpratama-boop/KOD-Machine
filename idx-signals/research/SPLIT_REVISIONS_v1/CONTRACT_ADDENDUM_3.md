# SPLIT_REVISIONS_v1, contract addendum 3

Written 2026-11-13 (UTC), AFTER an independent review of revision 2 (commit `ac0f24d3a`) found the fault below, and
disclosed as such. `CONTRACT.md`, `CONTRACT_ADDENDUM_1.md` and `CONTRACT_ADDENDUM_2.md` are unchanged. No ledger had
been written: `paper/split_assessments.jsonl` does not exist yet, so no record changes.

It is the fault addendum 2 corrected, in a third place: something that could not be evaluated was allowed to count as
a finding.

## The fault

Addendum 2 point 2 keeps a finding when a later response has **no** priced bar (`NOT_ASSESSABLE`). It does not cover a
later response that **has** priced bars but no readable split events. Example (the reviewer's): recorded previous close
1, close 24, the provider's previous-session close 24, a 1-for-24 split listed: `ARTIFACT_CONFIRMED`. A later response
with the same prices and the split-event block removed is classified `UNITS_INCONSISTENT` (the closes disagree and no
split explains them). That record is not `NOT_ASSESSABLE`, so `standing` takes it, the set leaves the corrected view's
removed sets, and the false spike is back in the corrected figures. `verify` reports nothing, because nothing in the
ledger is malformed. A malformed split-event block has the same effect, because `split_flags.provider_splits` returns
no event at all when one entry cannot be read.

Missing evidence is not contrary evidence. Every class in which a split was used rests on the response listing that
split; a response that lists no readable split can neither confirm nor contradict it.

## Correction

**Split-event coverage.** `split_assessments.split_event_coverage(payload) -> str` describes the split-event block of a
provider chart payload (`chart.result[0].events.splits`):

- `"LISTED"`: the block is a non-empty dict and `split_flags.provider_splits(payload)` returns one event per entry.
- `"MALFORMED"`: `events` is present but not a dict; or `splits` is present but not a dict; or `splits` is a non-empty
  dict and `provider_splits` returns fewer events than it has entries (an entry it could not read).
- `"ABSENT"`: anything else: no `chart.result[0]`, no `events`, `events` without `splits`, `splits` is `None` or an
  empty dict.

It never raises.

**Event-based findings.** `EVENT_BASED` is the classes whose finding rests on a split the response listed (addendum 2,
point 1): `ARTIFACT_CONFIRMED`, `ARTIFACT_PROBABLE`, `REAL_MOVE_UNITS_CONTAMINATED`, `SPLIT_IN_WINDOW_UNRESOLVED`,
`REAL_MOVE_UNITS_UNVERIFIED`, `REAL_MOVE_AFTER_SPLIT`.

**The incomplete refresh.** `assessment_record` takes a new keyword argument `finding=None`: the set's standing
assessment (addendum 2, point 2). When the payload holds a priced bar, `finding` is given, `finding["assessment"]` is
in `EVENT_BASED`, and the payload's coverage is not `"LISTED"`, the record is `NOT_ASSESSABLE` with the fields
addendum 1 gives (no previous session, units `UNKNOWN`, `split` `""`), and its new key `evidence_gap` is
`"SPLIT_EVENTS_MALFORMED"` when the coverage is `"MALFORMED"`, otherwise `"SPLIT_EVENTS_ABSENT"`. In every other case
the record is as before and `evidence_gap` is `None`. A payload with no priced bar stays as addendum 1 gives it, with
`evidence_gap` `None`. First assessments are unchanged: `propose_assessments` passes no finding.

**Reassessment.** `propose_reassessments` passes each set's standing assessment as `finding`. Because the incomplete
refresh is `NOT_ASSESSABLE`, addendum 2's `standing` already keeps the finding: the set stays in, or out of, the views
exactly as before. The night is still recorded, superseding the set's last record, so the ledger shows that the
evidence went missing.

**An evidence-backed reversal is still possible.** A response whose coverage is `"LISTED"` is classified by the rule as
before, whatever the finding. SMX 2026-11-10 is that case: the response lists the split, and the closes show both are
post-split, so the rule finds a real move.

**Records.** Every record has the key `evidence_gap` (after `later_factor`): `None`, or one of
`"SPLIT_EVENTS_ABSENT"`, `"SPLIT_EVENTS_MALFORMED"`. `CHANGE_FIELDS` gains `evidence_gap`, so a night that changes only
the kind of gap is recorded and a repeated identical gap is not. `verify` adds one check: a non-`None` `evidence_gap`
must be one of those two values and the record's `assessment` must be `NOT_ASSESSABLE`.

## Consequences

- On the 168 sets at `134f58f`: none. The dry run makes first assessments only, and the protection applies to
  reassessments of event-based findings. Every figure in `results/` is unchanged.
- The nightly simulation (`results/SIMULATION.md`): unchanged. Night 3 (no bars for GOVX) is addendum 1's case.
- A limit, stated now: a provider that withdraws a split it listed in error, and lists no split at all afterwards,
  does not reverse an artifact finding under this rule. Reversal needs a response that lists a readable split.

## Tests

To be added by the independent test author from this text, including an absent and a malformed split-event block.
