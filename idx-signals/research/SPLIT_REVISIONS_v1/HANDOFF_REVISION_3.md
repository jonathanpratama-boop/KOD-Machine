# SPLIT_REVISIONS_v1, revision 3: an incomplete refresh no longer undoes a split finding

Written 2026-11-13 (UTC). Revision 3 sits on revision 2 (`ac0f24d3a`). It answers finding P2 of the independent
review of 13 November 2026. `HANDOFF.md` is not edited (it is a frozen record); this file adds to it.

## The fault (review P2)

`standing` protected a finding only from a later `NOT_ASSESSABLE` record. A later response with the same prices but no
split-event block (or a block that cannot be read) was classified `UNITS_INCONSISTENT`, which displaced
`ARTIFACT_CONFIRMED`: the false spike came back into the corrected view, and `verify` reported nothing.

Reproduced before the fix through the submitted functions (`assessment_record`, `propose_reassessments`, `standing`,
`removed_set_ids`): previous close 1, close 24, provider previous-session close 24, a 1-for-24 split listed. With the
events removed, the set stopped being excluded. Same result for a malformed entry and for a block that is a list.

## The correction (`CONTRACT_ADDENDUM_3.md`, RFC 3161 stamped by freetsa and sectigo before the tests were written)

- `split_event_coverage(payload)` says whether a response lists readable splits (`LISTED`), lists none (`ABSENT`) or
  holds a block that cannot be read in full (`MALFORMED`).
- When a set's standing finding rests on a listed split (`EVENT_BASED`: `ARTIFACT_CONFIRMED`, `ARTIFACT_PROBABLE`,
  `REAL_MOVE_UNITS_CONTAMINATED`, `SPLIT_IN_WINDOW_UNRESOLVED`, `REAL_MOVE_UNITS_UNVERIFIED`, `REAL_MOVE_AFTER_SPLIT`)
  and a later response lists no readable split, the night is recorded as an incomplete refresh: `NOT_ASSESSABLE`
  with a new field `evidence_gap` (`SPLIT_EVENTS_ABSENT` or `SPLIT_EVENTS_MALFORMED`). Addendum 2's `standing` keeps the
  finding, so the set stays in, or out of, every view.
- A response that lists a readable split is classified by the rule as before, so an evidence-backed reversal (the
  SMX kind) still displaces a finding.
- Every record carries `evidence_gap` (`None` normally). It is in `CHANGE_FIELDS`, and `verify` rejects an unknown
  value or a gap on a record that is not `NOT_ASSESSABLE`.
- First assessments are unchanged. No ledger exists yet, so no record changes; every figure in `results/` is unchanged.
- A limit, stated in the addendum: a split withdrawn by the provider with no split listed afterwards does not reverse
  an artifact finding. Reversal needs a response that lists a readable split.

## Files

| File | Change |
|---|---|
| `idxsig/split_assessments.py` | `split_event_coverage`, `EVENT_BASED`, `EVIDENCE_GAPS`; `assessment_record(finding=...)`; `propose_reassessments` passes the standing finding; `evidence_gap` field, change field and `verify` check |
| `tests/test_split_assessments.py` | `RECORD_KEYS` gains `evidence_gap` (one line; the record contract changed) |
| `tests/test_split_addendum3.py` (new) | 30 tests, 262 subtests, written by a separate agent from the addendum text without reading the implementation |
| `research/SPLIT_REVISIONS_v1/CONTRACT_ADDENDUM_3.md` (+ two `.tsr`) | The correction, stamped |

## Checks run

- After the fix the reproduction keeps the set excluded for an absent block, a malformed entry and a block that is a
  list. Each night is recorded as a `NOT_ASSESSABLE` gap record superseding the previous record, and `verify` reports
  no problem. When the split is listed again, the finding is `ARTIFACT_CONFIRMED` once more.
- Targeted: 172 existing split tests plus the 30 new ones pass. Pinned ruff 0.14.3: no findings in the changed module.
- Full `idx-signals/tests`: 2,118 passed, 9 failed. All 9 fail for environment reasons that also fail without this
  change: 6 need `exchange_calendars` (not installed here) and 3 are pandas date-type tests (`test_lookahead_check`,
  `test_premove_evaluation`).
- `results/SIMULATION.md` was not re-run: it needs the provider responses of 2026-11-12, which are outside this
  repository. Its night 3 is addendum 1's case, which this change does not touch.

## Found while checking, not fixed here

`tools/check_append_only.py --all` reports three violations on this branch, all from revision 2's handoff commits
`0fe3c1616`, `083b5e396` and `ac0f24d3a`: each modifies `research/SPLIT_REVISIONS_v1/HANDOFF.md`, and every file under
`idx-signals/research/` is frozen once committed. Revision 3 adds no further violation. Fixing the three would mean rewriting this branch's history (for
example squashing the handoff edits into the commit that adds the file), which is the architect's or owner's call at
merge time.
