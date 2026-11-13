# SPLIT_REVISIONS_v1: contract questions recorded by the independent test author

Written with `test_split_assessments.py`, from `CONTRACT.md`, `CONTRACT_ADDENDUM_1.md`, `CONTRACT_ADDENDUM_2.md` and
`PROTOCOL.md`, without seeing the implementation. Questions 1 to 24 were written before addendum 2; the notes
"Addendum 2" under questions 14, 15, 19 and 20 say what that addendum settled, and questions 25 to 32 are the ones it
raises. Each entry gives what the text says or leaves open, the reading the tests use, and the tests
that depend on that reading. Where a reading is not certain, a failing test named here is a question about the
contract first and about the code second.

The existing files `split_flags.py`, `test_split_flags.py`, `paper_book.py` and `paper_book_report.py` were used for
the payload shape, the V11 record, the book rows and the legacy report text. The module `paper` was not available;
what the tests assume about it is in question 16.

Test names are written `Class.test_name`.

## Summary of the readings a test depends on

| Question | Reading | Certainty | Tests that fail if the reading is wrong |
|---|---|---|---|
| 1 | `k` is denominator divided by numerator | High | Most of the classifier tests |
| 2 | `classify` always treats its source as consulted | High (the addendum states it) | `ClassifyShape.test_empty_pull_counts_as_a_consulted_source`, `ResponseWithoutAPricedBar.test_classify_is_unchanged` |
| 3 | `event` is `None` for `REAL_MOVE_UNITS_UNVERIFIED` | Medium | `ElevenClasses.test_real_move_units_unverified` |
| 4 | Tolerances are on the logarithm of the ratio | High | `PreviousBar.test_unchanged_tolerance_...`, `PreviousBar.test_rebased_tolerance_...` |
| 8 | "Never raises" covers arguments of the wrong type | Medium | `ClassifyShape.test_never_raises_on_bad_input` |
| 11 | `split` is empty unless CA-3 or CA-4 used an event | Medium | `AssessmentRecord.test_split_is_empty_when_no_event_is_used` |
| 12 | A `None` payload is "no payload" for `propose_reassessments` | Medium | `Propose.test_reassessments_skip_a_set_whose_payload_is_none` |
| 14 | A finding of any class replaces the V11 tag in the corrected view; `NOT_ASSESSABLE` does not (addendum 2) | High (letter) | `RemovedSets.test_corrected_uses_the_v11_flag_for_a_set_without_a_finding`, `AddendumTwo.test_corrected_v11_artifact_with_a_finding_of_another_class_is_not_removed` |
| 15 | A V11 record later than an assessment decides at the time | High (letter of B2) | `RemovedSets.test_at_the_time_latest_record_before_the_cutoff_decides` (last assertion) |
| 16 | A changed line breaks the hash chain check | Medium (depends on `paper`) | `Verify.test_tampered_line_fails_the_chain_check_of_the_ledger_on_disk` |
| 17 | "A section headed" means the heading is the first line | Medium | `SecondaryView.test_an_assessed_row_gives_the_new_section` |
| 19 | One priced bar anywhere makes a response evidence for every class except `NO_ACTION_FOUND` (addendum 2) | High (letter) | `ResponseWithoutAPricedBar.test_one_priced_bar_is_evidence` (second half), `AddendumTwo.test_listed_split_keeps_its_class_without_a_reference_bar` |
| 20 | A lost history is proposed whatever the latest group | High (letter of the addenda) | `ResponseWithoutAPricedBar.test_reassessment_of_an_artifact_whose_history_is_lost`, `AddendumTwo.test_ledger_through_a_night_without_bars` |
| 21 | `previous_session_source` is `None` when there is no previous session | Medium | Every test of `ResponseWithoutAPricedBar` and `AddendumTwo` that calls `assert_not_assessable`, `AssessmentRecord.test_no_payload_is_not_assessable` |
| 26 | `REAL_MOVE_AFTER_SPLIT` is kept without a reference bar | High (named in addendum 2) | `AddendumTwo.test_listed_split_keeps_its_class_without_a_reference_bar` (last case) |
| 28 | Every class except `NOT_ASSESSABLE` is a finding for `standing` | High (letter) | `AddendumTwo.test_standing_keeps_a_finding_over_a_later_not_assessable`, `AddendumTwo.test_unresolved_set_ids_uses_the_standing_assessment` |
| 30 | A `NOT_ASSESSABLE` record is ignored at the time even in a tie with a V11 record | High (letter) | `AddendumTwo.test_at_the_time_ignores_not_assessable_records` |

## Part A and part B1: the classifier

### 1. The factor `k` is never defined

Part A uses `k`, `k_e` and "the split factor", and B1 returns an event with a key `k`, but no sentence says how `k`
is computed from numerator and denominator.

Reading: `k = denominator / numerator`, as in `split_flags.classify`. It is the only reading under which `p * k_e` is
the re-based previous close of a reverse split written "1:10" (numerator 1, denominator 10), and it agrees with part C
case 1 ("1-for-2.8") and with the example `"2026-11-06 1:10"`. A forward split 2-for-1 then has `k = 0.5`.

Tests: nearly all classifier tests. `CandidateEvents.test_forward_split_is_a_candidate_event` and
`CandidateEvents.test_forward_split_artifact` would change class under the inverse definition.

### 2. When a source counts as consulted inside `classify`

Step 1 gives `NOT_ASSESSABLE` when "no corporate-action source was consulted and there is no reference bar". Part A
adds that "a corporate-action source counts as consulted whenever a provider payload was read". `classify` has no
argument that says whether a source was consulted.

Reading: `classify` receives the events of a pull, so a source was consulted on every call, including a call with
`events == []` and `bars == []`. Such a call is Case C and ends in `NO_ACTION_FOUND`, or `UNEXPLAINED_EXTREME_MOVE`
when the ratio is 4 or more. `CONTRACT_ADDENDUM_1.md` confirms this reading ("the set falls through to
`NO_ACTION_FOUND`") and states that `classify` is unchanged.

Tests: `ClassifyShape.test_empty_pull_counts_as_a_consulted_source`,
`ResponseWithoutAPricedBar.test_classify_is_unchanged`. Wherever another test needs "no reference bar and no event in
E" without leaning on this reading, it passes an old split of 2026-06-12 in the event list, so that the source is
visibly consulted. `events=None` is not tested for a class; it is only required not to raise.

### 3. CA-5: which events "explain", and what `event` is returned

Two points.

(a) CA-5 reads "no event explains the move, but an event in `E` with straddle not `NO` has ...". It is not stated
whether "no event" means no event of `E` at all, or no event with a straddle that is not `NO`. The two differ when an
event with straddle `NO` would explain the move while another event with straddle `YES` only brings it closer.
Not tested.

(b) B1 defines `event` as "`None`, or the event used by CA-3 or CA-4". By that sentence the event that triggers CA-5 is
not returned.

Reading for (b): `event` and `adjusted_ret1` are `None` for `REAL_MOVE_UNITS_UNVERIFIED`, and for every class other
than the four of CA-3 and CA-4. An implementation that reports the CA-5 event would fail
`ElevenClasses.test_real_move_units_unverified`.

### 4. The tolerances are on the logarithm of the ratio

Step 3 writes the tolerances as `|ln(q / p)| <= ln(1 + tol)`. The band is therefore `[p / 1.01, p * 1.01]`, not
`p * (1 +/- 0.01)`: a close of 0.99 against 1.00 is outside the unchanged tolerance (`|ln 0.99| = 0.010050`, the
bound is `0.009950`), and 9.70 against 10.00 is outside the re-based tolerance. An implementation that compares the
relative difference would differ on those values.

Tests: `PreviousBar.test_unchanged_tolerance_is_one_percent_of_the_log_ratio`,
`PreviousBar.test_rebased_tolerance_is_three_percent_of_the_log_ratio`. Values exactly on a bound are not tested: the
bounds are logarithms of numbers that are not exact in binary floating point, and the result would depend on how the
implementation writes the comparison. The bounds that are tested exactly are the ones that are exact: the dates of
the three windows, the gap of 5 days, the ratio 4.0 (as 2.00 / 0.50), and the smallest split factor (the same float
1.05 on both sides of a strict comparison). The threshold is tested at `r / k = 13 / 10`, where the mathematical value
0.30 and the floating-point value 0.30000000000000004 both satisfy `>= T`.

### 5. Addendum 1 of part A (re-basing by a later split)

- Order of the attempts when both an event of `E` and the factor `F` are in play: the text for Case B says "each event
  of `E`, latest first, is tried with `p * k_e` and then with `p * k_e * F`"; for Case A it gives no order. The tests
  use at most one event of `E` together with `F`, so they do not depend on the order.
- Tolerance of a comparison that uses `p * F`: the text says the comparison "is tried first as written and then with
  `p * F` in place of `p`". Reading: the tolerance is that of the comparison (1% for unchanged, 3% for re-based).
  Test: `LaterSplits.test_rebased_comparison_keeps_the_tolerance_of_the_comparison`.
- `F` is the product of all later splits and the threshold `ln(1.05)` applies to the product, not to each factor.
  Tests: `LaterSplits.test_later_factor_is_the_product_of_the_later_splits`,
  `LaterSplits.test_later_factor_too_close_to_one_is_not_tried`. A later event with a bad numerator or denominator is
  assumed to be ignored like any other event; not tested.
- Rounding of `later_factor` is not specified. The tests compare it with `assertAlmostEqual`.
- The parameter `ca_later_split_rebase` cannot be set through `classify`. Reading: it is always `true`. The value
  `false` is not tested.

### 6. Case A with an unusual previous session

Nothing is said about a recorded previous session that is not a valid date, that is on or after the signal session, or
that lies outside the reference window.

Reading: a previous session outside the reference window has no reference bar, so the units are `UNKNOWN` while `P`
is still known (`PreviousBar.test_case_a_previous_session_outside_the_reference_window`). The other two situations
are only required not to raise.

### 7. The other fields of a `NOT_ASSESSABLE` result

B1 does not give `units`, `previous_session` and `previous_session_source` for a result that stops at step 1. The
tests of `classify` assert only the class, the group, the key set, that `units` is one of the four values, and that
`event`, `adjusted_ret1` and `later_factor` are `None`. For the record, see question 21.

### 8. How far "never raises on bad input" goes

The sentence is unconditional. The tests take it to cover arguments of the wrong type as well as wrong values:
`events` or `bars` that are `None`, a string or a number; list entries that are not dicts or pairs; sessions that are
not ISO dates; a number where a date is expected (`ClassifyShape.test_never_raises_on_bad_input`). They assert only
that a well-formed dict comes back.

For close, previous close and signal session the contract names the class. The tests treat `None`, zero, a negative
number, NaN, a non-numeric string, an empty string and an impossible date as "missing or invalid"
(`ElevenClasses.test_not_assessable`). Infinity, booleans and numeric strings such as `"9.84"` are not tested.

### 9. `payload_bars`

- Whether an entry whose close is `None` is kept as `(session, None)` or dropped is not stated. The tests accept both.
- The type of a pair (tuple or list) and of a session (assumed an ISO date string) are not stated. The tests convert
  pairs to tuples and compare sessions as ISO strings.
- The order of the list is assumed to be the order of the payload. The test payloads are chronological, so a sorted
  result is equal.
- A payload whose timestamp and close lists differ in length is arguably "malformed" but is not tested.
- A payload with one unusable timestamp entry is expected to give `[]` (`PayloadBars.test_malformed_payloads`), under
  "anything missing or malformed gives `[]`".

### 10. Keys of the returned `event`

B1 says the event is "a dict with `effective_session`, `numerator`, `denominator` and `k`". The tests require those
four keys and allow others, since the record needs the provider's ratio string from somewhere.

## Part B2: the assessment ledger

### 11. `assessment_record`

- `pull_role` is an argument, and the contract also says it "is `"seal"` when the payload is the scan's own pull".
  Reading: the function stores the argument; the sentence describes how callers choose it.
- `split` when the provider gave no ratio string: the contract says "in the form of the V11 ledger". The V11 code
  writes `numerator:denominator` with `:g` formatting. The tests cover only the case where that gives `1:10`. A
  numerator and denominator that are not in lowest terms, without a provider string, are not tested.
- `split` for a class that has a split in the window but no event "used": the contract says `split` is "`""`, or the
  effective session and ratio of the event used", and B1 ties "used" to CA-3 and CA-4. Reading: `split` is `""` and
  `split_adjusted_ret1` is `None` for `REAL_MOVE_AFTER_SPLIT`, `REAL_MOVE_UNITS_UNVERIFIED` and the other classes.
  This matters because `changed` compares `split`. Test: `AssessmentRecord.test_split_is_empty_when_no_event_is_used`.
- `recorded_ret1` is computed from the set alone and is present when the payload is `None` or empty.
- `seal` is read only for `pull_role` and `previous_session`. A seal record without a previous session, and a first
  record whose role is `"later"`, pass nothing to the classifier
  (`AssessmentRecord.test_seal_is_used_only_when_it_is_a_seal_record_with_a_previous_session`).

### 12. `propose_reassessments` and a payload that is `None`

For `propose_assessments` the contract separates "a missing ticker or a `None` payload". For `propose_reassessments`
it says only "a set whose ticker has no payload is skipped", and the addendum repeats that wording next to "a set whose
payload holds no bar is not skipped".

Reading: a ticker that maps to `None` has no payload and is skipped, exactly like a ticker that is absent. A response
that was received but holds no bar is a payload and is not skipped (question 20). The other reading (only an absent
ticker is skipped, `None` becomes a `NOT_ASSESSABLE` reassessment) is defensible; it would mean that one failed
download downgrades a real assessment.

Test: `Propose.test_reassessments_skip_a_set_whose_payload_is_none`, kept separate from the test of an absent ticker
so that the two readings can be told apart.

### 13. Order and window of the proposals

- The order of the lists returned by `propose_assessments` and `propose_reassessments` is not stated. The tests
  compare by set id, or use a single set.
- The window is "at most `window_days` calendar days before `today`". Reading: a set whose signal session is exactly
  `window_days` days before `today` is considered (`Propose.test_reassessments_window`).
- The behaviour when only one of `window_days` and `today` is given is not stated and not tested.

### 14. Corrected view: any assessment replaces the V11 tag

B2 says the corrected view removes "the sets whose latest assessment has group `ARTIFACT`", and that the V11 tag
counts only for "a set with no assessment record". A set tagged `ARTIFACT_V11` whose only assessment is unresolved
is therefore not removed. That includes `NOT_ASSESSABLE` because the ticker was missing from one pull, or because the
provider returned no bar.

The tests follow the letter (`RemovedSets.test_corrected_uses_the_v11_flag_only_for_a_set_without_an_assessment`).
The consequence deserves a decision by the owner of the contract: an artifact that the V11 rule identified correctly
returns to the corrected view as soon as one unresolved assessment is appended for it. The addendum's statement that
"no set is added to or taken out of the corrected view" is true of the four sets it names, which carried no V11
artifact tag; it is not true in general.

Addendum 2: settled for `NOT_ASSESSABLE`. A set tagged `ARTIFACT_V11` whose standing assessment is `NOT_ASSESSABLE`
stays removed. The test named above expected the opposite and was changed (question 27). A finding of any other
class, including the other unresolved classes, still replaces the tag; see question 29.

### 15. At-the-time view

- Timestamps are compared as given. The tests use one format (`YYYY-MM-DDTHH:MM:SSZ`) for `assessed_at` and for the
  cutoffs. Mixed formats or offsets are not tested.
- "The latest of them by `assessed_at`" is applied across both ledgers. A V11 record that is later than an assessment,
  both before the cutoff, decides (last assertion of
  `RemovedSets.test_at_the_time_latest_record_before_the_cutoff_decides`). With the nightly order (V11 hook, then the
  assessment) this should not occur, but the letter is clear.
- Two assessments of one set with the same `assessed_at` are not covered by the tie rule, which speaks of a V11 record
  and an assessment. Not tested.
- `cutoffs=None`, the default, is read as "no set has a cutoff": the result is empty
  (`RemovedSets.test_at_the_time_needs_a_cutoff`).

Addendum 2: records whose assessment is `NOT_ASSESSABLE` are now ignored in this view; see question 30.

### 16. `verify`, and what the tests assume about `paper`

- The wording and the number of the problems are not specified. The tests assert an empty list or a non-empty list.
- `specs=None` presumably reads the speculation register, as `split_flags.verify` does. Not tested; every call passes
  `specs`.
- A ledger file that does not exist is read as an empty, sound ledger (`Verify.test_missing_ledger_is_sound`,
  `RemovedSets.test_missing_ledgers_remove_nothing`). The existing V11 tests show that `paper.ledger_lines` tolerates
  a missing file for the V11 ledger.
- "A set id that is not a sealed US set" is tested with an unknown id, with a sealed set of another market, and with a
  US record that has no `decision` key.
- The chain check is tested by rewriting one field of a sealed line in place
  (`Verify.test_tampered_line_fails_the_chain_check_of_the_ledger_on_disk`). This assumes that `paper.verify_chain`
  recomputes each record's hash from its content, and that reading a ledger with a broken hash does not raise.
- Assumptions about `paper.append`, taken from `test_split_flags.py`: it accepts any dicts and a `path`, needs no
  timestamper, adds `prev_hash` and `record_hash`, and collapses identical payloads. The tests never append two
  identical records and never assume that the same record receives the same hash in two ledgers.

## Part B3: the paper book report

### 17. `secondary_view`

- The contract does not say where `secondary_view(rows)` takes the entry cutoffs from. The rows do not carry them.
  Expectation: from the `BOOK_PLAN` records of the paper book ledger (`paper_book.lines()`, field `entry_cutoff`),
  which is the only per-set cutoff in the files given. The tests write such plan records to a temporary
  `paper_book.LEDGER` and assert nothing that depends on a cutoff. If the implementation reads the cutoffs elsewhere
  (the forecast ledger, the speculation register), it reads the repository's own files during these four tests and
  must tolerate rows that have no cutoff there.
- "It is a section headed ..." is read as: the heading is the first non-blank line of the output
  (`SecondaryView.test_an_assessed_row_gives_the_new_section`). Whether the output begins with two newlines, as the
  legacy section does, is not asserted.
- "Affected set" is not defined. The test uses a row whose current assessment is `ARTIFACT_CONFIRMED` and requires
  only that its ticker or set id appears, and that every book name appears. The counts, the tag at the time, the
  "recorded before the entry cutoff" statement and the figures under the three views are not asserted, because their
  wording and layout are not specified.
- "Exactly what it was before this change" is tested against a copy of the legacy text taken from
  `reference/paper_book_report.py` (`legacy_section` in the test module). The condition "no row's set has a
  `SPLIT_ASSESSMENT` record" is evaluated on the ledger on disk; assessments of sets that are not rows of the book
  leave the legacy output in place
  (`SecondaryView.test_assessments_of_sets_outside_the_book_change_nothing`).
- `paper_book_report.render` is not tested: the contract does not mention it, and it needs `paper_input_health`, which
  is outside the imports given for this module.

### 18. `views`

"Returns three lists" is read as: the dict has exactly the keys `as_frozen`, `at_the_time` and `corrected`. Rows are
compared by equality, not identity.

## `CONTRACT_ADDENDUM_1.md`

### 19. The criterion is "no bar with a price", not "no reference bar"

The addendum makes a response non-evidence when `payload_bars(payload)` "contains no pair whose close is a number
greater than zero". A response with a single priced bar on the signal session, or only bars after it, still counts as
evidence. It has no reference bar, so a set without a split event in the window still falls through to
`NO_ACTION_FOUND`, group `REAL`, with units `UNKNOWN` and no previous session: nothing about the previous close was
checked, which is the fault the addendum describes. With a split event in such a response the events are used
(`ResponseWithoutAPricedBar.test_one_priced_bar_is_evidence`, second half, and the second night of
`Propose.test_reassessment_supersedes_the_latest_record_of_a_chain`).

The tests follow the letter. Whether the criterion should be "no reference bar" is a question for the owner of the
contract; `PROTOCOL.md` counts sets by group, and these sets are counted as real.

Addendum 2: settled by point 1 in its final wording. `NO_ACTION_FOUND` without a reference bar becomes
`NOT_ASSESSABLE`; every other class is kept, so a listed split in a response with one priced bar is still used. The
tests named above agree with that wording and were not changed. Questions 25 and 26 are what remains.

### 20. `propose_reassessments` when a history is lost

- "It is proposed as `NOT_ASSESSABLE` when that differs from its latest assessment" is read through `changed`, as the
  rest of `propose_reassessments` is: a set that is already `NOT_ASSESSABLE` with no previous session is not proposed
  again (`ResponseWithoutAPricedBar.test_reassessment_proposes_not_assessable_when_the_history_is_lost`).
- The addendum says "after a real assessment". Reading: after any assessment, whatever its group. The tests include a
  set whose latest assessment is `ARTIFACT_CONFIRMED` and whose response is an error body
  (`ResponseWithoutAPricedBar.test_reassessment_of_an_artifact_whose_history_is_lost`). The proposed record supersedes
  the confirmed artifact, and by question 14 the set then returns to the corrected view. The addendum calls the
  reassessment deliberate; it does not mention this effect on the corrected view. The test asserts the proposal, not
  the effect.
- A `None` payload: see question 12.

Addendum 2: settled by point 2. The proposal is still made and still supersedes the confirmed artifact, and the
readers use the standing assessment, so the set stays removed
(`AddendumTwo.test_ledger_through_a_night_without_bars`). Question 12 is still open.

### 21. Fields the addendum does not name

The addendum lists the assessment, the group, "no previous session", units `UNKNOWN`, an empty `split`, and `None`
for `split_adjusted_ret1` and `later_factor`. It does not name `previous_session_source`.

Reading: with no previous session the source is `None` (B1: "otherwise `None`"). "No previous session" holds even
when a seal assessment with a recorded previous session is passed
(`ResponseWithoutAPricedBar.test_seal_previous_session_is_not_carried_into_the_record`). `recorded_ret1`,
`supersedes`, `pull_role`, `sources`, `basis` and `assessed_at` are filled as in any other record.

### 22. "A number greater than zero"

The tests use `None` and `0.0` as closes that are not prices
(`ResponseWithoutAPricedBar.test_bars_whose_closes_are_all_none`). NaN, negative closes and numeric strings are not
tested.

### 23. Relation to `CONTRACT.md`, and the test that was changed

`CONTRACT.md` says "a corporate-action source counts as consulted whenever a provider payload was read" and leaves
`NOT_ASSESSABLE` in `assessment_record` to a payload of `None`. The addendum keeps `CONTRACT.md` unchanged and
overrides it for the record: a payload that was read but holds no priced bar is not evidence. The two texts now
disagree on purpose for `assessment_record` and agree for `classify`.

One test written before the addendum contradicted it and was removed:
`AssessmentRecord.test_payload_without_events_or_bars_was_still_consulted` expected `NO_ACTION_FOUND` from the payload
`{"chart": {"result": [{}]}}`. The same payload is now expected to give `NOT_ASSESSABLE` in
`ResponseWithoutAPricedBar.test_error_body_or_no_data`.

## `CONTRACT_ADDENDUM_2.md`

Point 1 was received in two wordings. The tests are written from the final one only: `NO_ACTION_FOUND` becomes
`NOT_ASSESSABLE` when the response holds no reference bar, and every other class is kept.

### 25. Point 1 asks for a reference bar, not for the previous bar

The condition is that the response "holds no reference bar". A reference bar anywhere in the 30 days is enough to
keep `NO_ACTION_FOUND`. One path still gives `NO_ACTION_FOUND` with units `UNKNOWN`: Case A, where the seal
assessment recorded a previous session, the later response has no priced bar on that session, and it has a priced
bar on some other session of the window. The previous close is then not found, yet the class is kept. The same
response without a recorded previous session is Case B and ends in `UNITS_INCONSISTENT` or `STALE_PREVIOUS` or a
match, so the path is narrow. Not tested.

### 26. `REAL_MOVE_AFTER_SPLIT` is kept without a reference bar

The addendum names it among the classes that "rest on a split the response does list". With no reference bar the
previous session is unknown, so nothing shows on which side of the split the recorded previous close lies. The rule
only establishes that the split does not explain the move; the group is `REAL` all the same. Example in the tests:
recorded ratio 1.5 with a 1-for-10 listed on the signal session and only the signal-session bar. The tests follow the
letter (`AddendumTwo.test_listed_split_keeps_its_class_without_a_reference_bar`, last case). Whether such a set should
count as real is a question for the owner of the contract.

### 27. Existing tests and the two addenda

Changed for point 2, both because they expected a `NOT_ASSESSABLE` record to displace a finding or a tag:

- `RemovedSets.test_corrected_uses_the_v11_flag_only_for_a_set_without_an_assessment` is now
  `RemovedSets.test_corrected_uses_the_v11_flag_for_a_set_without_a_finding`. It expected a set tagged `ARTIFACT_V11`
  with one `NOT_ASSESSABLE` assessment not to be removed; it now expects it removed.
- `ResponseWithoutAPricedBar.test_reassessment_proposes_not_assessable_when_the_history_is_lost`: one assertion.
  After `REAL_MOVE_AFTER_SPLIT` then `NOT_ASSESSABLE`, SMX was expected among the unresolved sets; it is no longer.

Not changed: three tests contradicted the withdrawn first wording of point 1 and agree with the final one
(`ResponseWithoutAPricedBar.test_one_priced_bar_is_evidence`, `Propose.test_reassessments_sources`,
`Propose.test_reassessment_supersedes_the_latest_record_of_a_chain`). All three rest on a split the response lists.

The two addenda now treat a listed split differently by one bar: with no priced bar at all the events are not used
(addendum 1); with one priced bar, even on the signal session only, they are (addendum 2). Both sides are tested.

### 28. What counts as a finding for `standing`

- The standing assessment passes over `NOT_ASSESSABLE` only. A record of any other class stands, including the other
  unresolved classes: `UNITS_INCONSISTENT` followed by `NOT_ASSESSABLE` stands as `UNITS_INCONSISTENT`
  (`AddendumTwo.test_standing_keeps_a_finding_over_a_later_not_assessable`).
- `NOT_ASSESSABLE` also arises when the set's own closes are missing or invalid (step 1). The addendum does not
  separate that case from a missing response; `standing` treats both alike.
- For a set with several records that are all `NOT_ASSESSABLE` the last one is returned. A sound ledger cannot hold
  two such records in a row, because `changed` would be false, but the reader is defined on any list
  (`AddendumTwo.test_standing_of_a_set_with_only_not_assessable_records`).
- Whether `standing` skips records of another type, as `latest` does, is not stated. Assumed; not tested.

### 29. The V11 tag and a finding of another unresolved class

The corrected view keeps a V11 artifact tag in force only for "no assessment record" and for a standing
`NOT_ASSESSABLE`. A set tagged `ARTIFACT_V11` whose standing assessment is `UNITS_INCONSISTENT`,
`SPLIT_IN_WINDOW_UNRESOLVED` or another unresolved class is not removed, as before. This is the part of question 14
that addendum 2 leaves in place; the task description for these tests confirms it. Tested in
`AddendumTwo.test_corrected_v11_artifact_with_a_finding_of_another_class_is_not_removed`.

### 30. At the time: `NOT_ASSESSABLE` and the tie rule

"Ignores records whose `assessment` is `NOT_ASSESSABLE`. Otherwise unchanged." Reading: such a record is left out
before anything else is applied. A V11 artifact tag and a `NOT_ASSESSABLE` assessment with the same `assessed_at` are
therefore decided by the tag, although the tie rule of `CONTRACT.md` gives a tie to the assessment; and a set whose
only record before its cutoff is `NOT_ASSESSABLE` has "no record before its cutoff". Tested in
`AddendumTwo.test_at_the_time_ignores_not_assessable_records`.

### 31. `unresolved_set_ids` and the report's count of unresolved sets

`unresolved_set_ids(records)` is "the sets whose standing assessment has group `UNRESOLVED`" and has no argument for
the V11 ledger. A set tagged `ARTIFACT_V11` whose only assessments are `NOT_ASSESSABLE` is returned by it and is also
removed by the corrected view. The addendum says the report "counts as unresolved only sets that the corrected view
does not remove", so the report has to subtract. The function is tested by its definition
(`AddendumTwo.test_unresolved_set_ids_uses_the_standing_assessment`); the report's count is not tested, for the
reason in question 17. Also not tested: a row whose only record is `NOT_ASSESSABLE` "has a `SPLIT_ASSESSMENT`
record", so `secondary_view` should give the new section for it and not the legacy one.

### 32. The ledger after a night without bars

Because a later pull "is still compared with the last record", a set goes finding, `NOT_ASSESSABLE`, and then the
same finding again when the data returns. The third record repeats the first one in the four fields that `changed`
compares; `verify` accepts it because it is compared with the record it supersedes. The seal assessment still
supplies the previous session. Tested end to end, with real hashes, in
`AddendumTwo.test_ledger_through_a_night_without_bars`.

## Part C

### 24. Choices made in the five cases

- Entry cutoffs are taken as 14:30 UTC on the session after the signal (09:30 in New York in November). The scan's
  V11 record and the seal assessment are stamped on the evening of the signal session, the later pull on a later day.
  The contract fixes none of these times; only their order matters to the tests.
- Case 1: when the seal assessment exists and is `REAL`, the at-the-time view does not remove the set either, because
  the assessment is later than the V11 tag and both precede the cutoff. The test does not assert this; it asserts the
  corrected view. Case 4 is the same set with the assessment made after the cutoff.
- Case 3, "is not reassessed into an artifact or a real move without new evidence": tested as `propose_reassessments`
  returning nothing for the same pull and for a newer pull that only adds sessions after the signal, and as `changed`
  being false for a record built from that newer pull.
- Case 5 builds the two sound records with the module's own functions and then introduces one defect at a time into a
  fresh ledger. A sound rebuild is checked last, so that a failure is the defect and not the rebuild.

## Not covered, and why

- `ca_later_split_rebase = false`: no way to set it through the interface (question 5).
- `verify(specs=None)`: it would read the repository's speculation register.
- The content of the new secondary section beyond its heading, the presence of the affected set and the book names
  (question 17).
- `paper_book_report.render`, the nightly hook, the one-off command and its dry run (`PROTOCOL.md`, "Ledger writes" and
  item 5 of "Added"): the contract gives no interface for them.
- Values exactly on a tolerance bound (question 4); mixed straddles in CA-5 (question 3); the order of attempts with
  several events and a later factor (question 5).
- The 83 corporate-action challenge cases of the KODCHECK audit, which `PROTOCOL.md` mentions as a second check of the
  classifier, were not available and are not part of this module.

## How the expected values were checked

The test author could not run the tests: the new modules were not available. The module compiles
(`python3 -m py_compile`). Six throwaway scripts in `tools/` were used; none reads anything outside this directory or
any repository code. The coordinator reported that the 129 tests written before addendum 2 pass against the
implementation after one repair on its side; the 18 tests of `AddendumTwo` and the two changed tests have not been
run.

- `arith.py`: ratios, logarithms, tolerances, weekdays and New York dates behind the comments in the tests.
- `derive.py`: applies steps 1 to 5 of part A and its addendum on later splits, as written in `CONTRACT.md`, to the
  128 inputs that the tests give to `classify` (directly or through a payload), and compares the result with the
  value each test expects. No difference. It is a check of the hand derivations, written by the test author from the
  contract; it shares the readings above and cannot detect a misreading.
- `derive_addendum2.py`: the same for the 23 record-level inputs of the addendum 2 tests, with the conditions of
  addendum 1 and of point 1 of addendum 2 applied on top of the rule. No difference.
- `helpers_check.py`: the fixture builders of the test module (payload shape, timestamps to New York dates, the keys
  of the hand-written records).
- `static_check.py`: undefined names, duplicate method names, tests per class.
- `harness_smoke.py`: imports the test module with inert placeholders in place of `idxsig` and with every assertion
  switched off, to find errors in the test module's own code (wrong argument counts, wrong attribute names). It found
  none after one such error had been corrected by reading. It exercises no implementation and says nothing about one.

`derive.py` and `harness_smoke.py` go beyond "small arithmetic scripts". They are disclosed here so that the reviewer
can decide whether that matters.
