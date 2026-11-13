# SPLIT_REVISIONS_v1, contract addendum 2

Written 2026-11-12 (UTC; 2026-11-13 in Jakarta), AFTER the dry run under addendum 1 and after the independent test author's questions on the
contract (`CONTRACT_QUESTIONS.md`, questions 14, 19 and 20), and disclosed as such. `CONTRACT.md` and
`CONTRACT_ADDENDUM_1.md` are unchanged. The outputs of the run under addendum 1 are kept in `results/second-run/`.

Both points below are the same fault addendum 1 corrected in one place: something that could not be evaluated was
allowed to count as a finding. The test author found that it survived in two other places.

## Point 1. "No corporate action found" needs a response that reaches back before the signal session

Addendum 1 made a response with no priced bar `NOT_ASSESSABLE`. A response that holds a priced bar on the signal
session only is no better for one class: the previous close cannot be found in it, and it does not show that the
provider's history reaches back over the days in which a split would matter. Under addendum 1 such a set still falls
through to `NO_ACTION_FOUND`, group `REAL`, with units `UNKNOWN` and no previous session.

This is not hypothetical. For one sealed set, ADIL 2026-10-28 (recorded move +36.12%), the provider's response of
2026-11-12 holds exactly one bar, on 2026-10-28, and no events. It was reported as "no corporate action found" by the
KODCHECK run of 2026-11-12 and by both earlier dry runs of this protocol.

**Correction.** In `split_assessments.assessment_record`, when the rule's class is `NO_ACTION_FOUND` and the response
holds no reference bar (no pair of `split_units.payload_bars(payload)` with a close greater than zero and a session
`X` with `S - 30 days <= X < S`, `S` being the set's `signal_session`), the assessment is `NOT_ASSESSABLE`, with the
fields addendum 1 gives. Every other class is kept as the rule returns it, also when there is no reference bar:
`ARTIFACT_PROBABLE`, `SPLIT_IN_WINDOW_UNRESOLVED`, `REAL_MOVE_UNITS_UNVERIFIED` and `REAL_MOVE_AFTER_SPLIT` rest on a
split the response does list, and `UNEXPLAINED_EXTREME_MOVE` rests on the size of the move. Only `NO_ACTION_FOUND`
rests on an absence, and an absence in a response that does not reach back shows nothing. `split_units.classify` is
unchanged.

A first wording of this point made every response without a priced bar before the signal session `NOT_ASSESSABLE`.
It was withdrawn on the day it was written, before this file was timestamped: run against the independent tests that
already existed, it threw away split events the response does list, so that a probable artifact became "not
assessable". The test author received both wordings.

## Point 2. A `NOT_ASSESSABLE` record never displaces a finding

Under `CONTRACT.md` every reader uses a set's last assessment. With addendum 1 that has two consequences nobody
intended:

- A set assessed `ARTIFACT_CONFIRMED` is reassessed `NOT_ASSESSABLE` on a night when the provider returns no bars.
  The record is right to exist. But the set then leaves the corrected view's removed sets, and the artifact is back
  in the corrected figures until the provider answers again.
- A set correctly tagged `ARTIFACT_V11` whose first assessment finds an empty response returns to the corrected view
  for the same reason.

**Correction.** A new reader, `split_assessments.standing(records) -> dict[str, dict]`, maps each set id to the set's
*standing assessment*: its last record, in ledger order, whose `assessment` is not `NOT_ASSESSABLE`; for a set whose
records are all `NOT_ASSESSABLE`, its last record. Then:

- `removed_set_ids("corrected", ...)` is the sets whose standing assessment has group `ARTIFACT`, together with the
  sets tagged `ARTIFACT_V11` that have no assessment record or whose standing assessment is `NOT_ASSESSABLE`.
- `removed_set_ids("at_the_time", ...)` ignores records whose `assessment` is `NOT_ASSESSABLE`. Otherwise unchanged.
- `unresolved_set_ids(records)` is the sets whose standing assessment has group `UNRESOLVED`.
- `paper_book_report` uses the standing assessment wherever it used the last one, and counts as unresolved only sets
  that the corrected view does not remove.

`latest`, `changed`, `propose_reassessments`, the `supersedes` chain and `verify` are unchanged: the ledger still
records the night the evidence went missing, each new record still supersedes the set's last record whatever its
class, and a later pull with data is still compared with the last record. Only what the readers conclude changes.

## Consequences on the 168 sets at commit `134f58f`

- ADIL 2026-10-28 becomes `NOT_ASSESSABLE`: five sets are now not assessable (GNTA, HUBC, RCT, SGRX and ADIL) and
  145 are `NO_ACTION_FOUND`, each of those 145 with its previous session identified in the provider's bars.
- None of the five carries an `ARTIFACT_V11` tag, so no set enters or leaves a view and the effect table's figures do
  not change. Point 2 changes no figure today; it is prevention.

## Tests

To be added by the independent test author from this text.
