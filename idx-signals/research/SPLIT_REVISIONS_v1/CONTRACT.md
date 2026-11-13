# SPLIT_REVISIONS_v1: contract for the code and its tests

Frozen with `PROTOCOL.md`. Part A is the classification rule. Part B is the interface of the two new modules.

## Part A. The rule `SPLIT_UNITS_V1`

The rule is check C01 of the KODCHECK specification (version 1.0, SHA-256 `7c237c91…0aca9`), steps 1 to 5, with its
addendum 1. The text below is copied from those two documents. Where it says "observation", read "sealed set"; `T` is
0.30; a corporate-action source counts as consulted whenever a provider payload was read. Rule CA-10 is not part of this
rule.


Applies when at least one included observation has `signal`. It is evaluated for each included observation that has
`signal`. Notation: `c = signal.close`, `p = signal.previous`, `r = c / p`, `S = signal.session`,
`T` = `study.eligibility.threshold` if `eligibility` is present, otherwise the parameter `ca_threshold`.

**Step 1, assessable.** If `c` or `p` is absent or not greater than zero, the class is `NOT_ASSESSABLE`. The
**reference bars** are the bars of `reference.bars` with a close greater than zero and a session `X` with
`S - ca_reference_lookback_days <= X < S`. If no corporate-action source was consulted and there is no reference bar,
the class is `NOT_ASSESSABLE`.

**Step 2, candidate events.** `E` is the set of events (when a source was consulted) with `type` `split`, numerator and
denominator greater than zero, `|ln k| > ln(ca_min_split_factor)`, and
`S - ca_lookback_days < effective_session <= S`.

**Step 3, the previous bar and its units.** `P` is the session of the bar that supplied `p`.

- Case A, `signal.previous_session` is present: `P` is that session. If a reference bar exists at `P` with close `q`:
  the units are `UNCHANGED` if `|ln(q / p)| <= ln(1 + ca_unchanged_tol)`; otherwise `PRE_SPLIT_CONFIRMED(e)` for the
  event `e` in `E` with the latest effective session that has `P < e.effective_session` and
  `|ln(q / (p * k_e))| <= ln(1 + ca_rebased_tol)`; otherwise `INCONSISTENT`. If no reference bar exists at `P`, the
  units are `UNKNOWN`.
- Case B, `signal.previous_session` is absent and at least one reference bar exists: let `Xu` be the latest reference
  session whose close `q` has `|ln(q / p)| <= ln(1 + ca_unchanged_tol)`. If `Xu` exists, `P = Xu` and the units are
  `UNCHANGED`. Otherwise take the events of `E` from the latest effective session to the earliest; for each, let `Xr`
  be the latest reference session before `e.effective_session` whose close `q` has
  `|ln(q / (p * k_e))| <= ln(1 + ca_rebased_tol)`; at the first event where `Xr` exists, `P = Xr` and the units are
  `PRE_SPLIT_CONFIRMED(e)`. If neither is found, `P` is unknown and the units are `INCONSISTENT`.
- Case C, `signal.previous_session` is absent and there is no reference bar: `P` is unknown and the units are
  `UNKNOWN`.

**Step 4, straddle.** For an event `e` in `E`: `YES` if `P` is known and `P < e.effective_session`; `NO` if `P` is
known and `P >= e.effective_session`; `UNKNOWN` if `P` is unknown.

**Step 5, class.** The first matching rule decides.

| Rule | Condition | Class | Severity |
|---|---|---|---|
| CA-1 | step 1 | `NOT_ASSESSABLE` | INSUFFICIENT |
| CA-2 | units are `INCONSISTENT` | `UNITS_INCONSISTENT` | INSUFFICIENT |
| CA-3 | units are `PRE_SPLIT_CONFIRMED(e)` and `r / k_e - 1 < T` | `ARTIFACT_CONFIRMED` | FAIL |
| CA-3 | units are `PRE_SPLIT_CONFIRMED(e)` and `r / k_e - 1 >= T` | `REAL_MOVE_UNITS_CONTAMINATED` | FAIL |
| CA-4 | an event in `E` with straddle not `NO` **explains** the move, and its straddle is `YES` or `r >= ca_extreme_ratio` | `ARTIFACT_PROBABLE` | FAIL |
| CA-4 | an event in `E` with straddle not `NO` explains the move, its straddle is `UNKNOWN` and `r < ca_extreme_ratio` | `SPLIT_IN_WINDOW_UNRESOLVED` | INSUFFICIENT |
| CA-5 | no event explains the move, but an event in `E` with straddle not `NO` has `|ln(r / k_e)| < |ln r|` | `REAL_MOVE_UNITS_UNVERIFIED` | INSUFFICIENT |
| CA-6 | `r >= ca_extreme_ratio` | `UNEXPLAINED_EXTREME_MOVE` | INSUFFICIENT |
| CA-7 | `P` is known and `S - P > ca_max_prev_gap_days` | `STALE_PREVIOUS` | INSUFFICIENT |
| CA-8 | `E` is not empty | `REAL_MOVE_AFTER_SPLIT` | none (pass) |
| CA-9 | otherwise | `NO_ACTION_FOUND` | none (pass) |

An event **explains** the move when `r / k_e - 1 < T` and `|ln(r / k_e)| < |ln r|`: dividing by the split factor leaves
a move below the threshold and closer to no move. When several events qualify in CA-4, the one with the latest
effective session is used.

What the classes mean:

- `ARTIFACT_CONFIRMED`: a later pull shows the previous close re-based by the split factor, so the recorded previous
  close was in pre-split units, and the adjusted move is below the threshold. The recorded event did not happen.
- `ARTIFACT_PROBABLE`: a split explains the move and either the previous bar is known to precede it or the recorded
  move is extreme. The units are not independently confirmed.
- `REAL_MOVE_UNITS_CONTAMINATED`: the units are confirmed wrong, yet the adjusted move still meets the threshold. The
  event qualifies; its recorded size, and anything computed from it, is wrong by the split factor.
- `SPLIT_IN_WINDOW_UNRESOLVED`: a split in the window would explain the move, but nothing shows whether the previous
  bar came before or after it, and the move is not extreme. It cannot be called either way.
- `REAL_MOVE_UNITS_UNVERIFIED`: a split may sit between the two bars and would change the size of the move without
  taking it below the threshold.
- `UNEXPLAINED_EXTREME_MOVE`: a move of `ca_extreme_ratio` times or more with no split to explain it. It needs a second
  source before it is used.
- `STALE_PREVIOUS`: the previous close is more than `ca_max_prev_gap_days` calendar days old, so the move is not a
  one-session move.
- `UNITS_INCONSISTENT`: the recorded previous close matches neither the later pull nor any re-based value.
- `REAL_MOVE_AFTER_SPLIT`: a split is in the window but does not sit between the two bars or does not explain the move.
- `NO_ACTION_FOUND`: a source was consulted, nothing was found, and none of the conditions above holds.

### Addendum 1 (re-basing by a later split)


Let `F` be the product of the factors of the split events, from a consulted source, with `effective_session > S` and,
when `reference.retrieved_at` is present, `effective_session <=` its UTC date. When `|ln F| > ln(ca_min_split_factor)`,
every comparison of step 3 that uses the recorded previous close `p` is tried first as written and then with `p * F`
in place of `p`:

- Case A, at session `P`: `UNCHANGED` if the reference close matches `p` or `p * F`; otherwise
  `PRE_SPLIT_CONFIRMED(e)` if it matches `p * k_e` or `p * k_e * F`; otherwise `INCONSISTENT`.
- Case B: `Xu` is the latest reference session matching `p`; if there is none, the latest matching `p * F`. If neither
  exists, each event of `E`, latest first, is tried with `p * k_e` and then with `p * k_e * F`. If nothing matches, the
  units are `INCONSISTENT`.

A match that needed `F` gives the same units result as one that did not, and the evidence records the factor as
`reference_rebased_by_later_splits`. Nothing else changes: a split after the signal session cannot alter the recorded
pair, because both of its bars precede it.

The behaviour is controlled by the parameter `ca_later_split_rebase`, default `true` from tool version 1.1.0. Setting it
to `false` reproduces version 1.0 of the specification exactly.

Parameters: `ca_lookback_days` 10, `ca_extreme_ratio` 4.0, `ca_max_prev_gap_days` 5, `ca_unchanged_tol` 0.01,
`ca_rebased_tol` 0.03, `ca_min_split_factor` 1.05, `ca_reference_lookback_days` 30.

## Part B. Interface

### B1. `idxsig/split_units.py` (pure functions, standard library only)

`RULE_ID = "SPLIT_UNITS_V1"`. `CLASSES` is the tuple of the eleven class names of step 5. `GROUP` maps each class to a
group:

| Group | Classes |
|---|---|
| `ARTIFACT` | `ARTIFACT_CONFIRMED`, `ARTIFACT_PROBABLE` |
| `CONTAMINATED` | `REAL_MOVE_UNITS_CONTAMINATED` |
| `REAL` | `REAL_MOVE_AFTER_SPLIT`, `NO_ACTION_FOUND` |
| `UNRESOLVED` | every other class |

`classify(close, previous, signal_session, events, bars, previous_session=None, retrieved_on=None) -> dict`

- `events`: every split event the pull lists, of any date; each a dict with `effective_session` (ISO date), `numerator`
  and `denominator`. An event whose numerator or denominator is missing or not greater than zero is ignored.
- `bars`: `(session, close)` pairs of the pull, of any date. A close that is `None` or not greater than zero is a session
  without a price.
- `previous_session`: the recorded session of the previous bar (Case A of step 3), or `None` (Case B or C).
- `retrieved_on`: the UTC date of the pull as an ISO date, or `None`. It bounds the later splits of addendum 1; `None`
  means every split after the signal session counts.
- Returns a dict with exactly these keys: `class`; `group`; `previous_session` (the `P` of step 3, or `None`);
  `previous_session_source` (`"recorded"` in Case A, `"matched"` when Case B found an unchanged match,
  `"rebased_match"` when Case B found a re-based match, otherwise `None`); `units` (`"UNCHANGED"`,
  `"PRE_SPLIT_CONFIRMED"`, `"INCONSISTENT"` or `"UNKNOWN"`); `event` (`None`, or the event used by CA-3 or CA-4 as a dict
  with `effective_session`, `numerator`, `denominator` and `k`); `adjusted_ret1` (`None`, or `r / k - 1` for that event
  rounded to 4 decimals); `later_factor` (`None`, or the factor `F` of addendum 1 when a match needed it).
- It never raises on bad input. A close, previous close or session that is missing or invalid gives `NOT_ASSESSABLE`.

`payload_bars(payload) -> list`: the `(session, close)` pairs of a provider chart payload, where the session is the New
York date of each entry of `chart.result[0].timestamp` and the close is the matching entry of
`chart.result[0].indicators.quote[0].close`. Anything missing or malformed gives `[]`.

### B2. `idxsig/split_assessments.py`

A second append-only ledger, `LEDGER = paper.PAPER / "split_assessments.jsonl"`, of records with
`type == "SPLIT_ASSESSMENT"` and `rule == "SPLIT_UNITS_V1"`. A set may have several records. The first is its original
assessment; each later one supersedes the one before it. The V11 ledger and its code are not changed.

A **sealed US set** is a speculation record with `market == "US"` and a `decision` key, as in `split_flags`.

`assessment_record(set_rec, payload, basis, assessed_at, *, prior=None, seal=None, pull_role="later", retrieved_on=None, sources=()) -> dict`

The record of one set before it is sealed into the ledger (no `prev_hash`, no `record_hash`). Its keys are exactly:
`type`, `rule`, `set_id`, `ticker`, `market`, `signal_session`, `recorded_ret1`, `assessment`, `group`, `split`,
`split_adjusted_ret1`, `previous_session`, `previous_session_source`, `units`, `later_factor`, `pull_role`, `supersedes`,
`basis`, `sources`, `assessed_at`.

- `recorded_ret1` is `signal.close / signal.previous - 1` rounded to 4 decimals, or `None` when either is missing or
  not greater than zero.
- `assessment` and `group` come from `split_units.classify` on the set's `signal.close`, `signal.previous` and
  `signal_session`, the payload's split events (`split_flags.provider_splits`) and bars (`split_units.payload_bars`).
  A `payload` of `None` gives `NOT_ASSESSABLE` with no previous session and units `UNKNOWN`.
- The recorded previous session passed to the classifier is `seal["previous_session"]` when `seal` is given, has
  `pull_role == "seal"` and a previous session; otherwise none is passed. `seal` is the set's own first record.
- `split` is `""`, or the effective session and ratio of the event used, in the form of the V11 ledger
  (`"2026-11-06 1:10"`; the provider's ratio string when it gave one).
- `split_adjusted_ret1`, `previous_session`, `previous_session_source`, `units`, `later_factor` are the classifier's
  values (`adjusted_ret1` for the first).
- `pull_role` is `"seal"` when the payload is the scan's own pull for the set's signal session, otherwise `"later"`.
- `supersedes` is `prior["record_hash"]` when `prior` is given, otherwise `None`.
- `sources` is stored as a list of the strings given.

`latest(records) -> dict`: set id to the set's last `SPLIT_ASSESSMENT` record, in ledger order.

`seal_assessments(records) -> dict`: set id to the set's first record, for sets whose first record has
`pull_role == "seal"`.

`pending(specs, records) -> list`: the sealed US sets with no `SPLIT_ASSESSMENT` record, in the order of `specs`.

`changed(new, old) -> bool`: true when `assessment`, `split`, `previous_session` or `units` differs.

`propose_assessments(specs, records, payloads, basis, assessed_at, *, seal_session=None, retrieved_on=None) -> list`

One unsealed record for every pending set. `payloads` maps ticker to payload; a missing ticker or a `None` payload gives
a `NOT_ASSESSABLE` record, never a skipped set. `pull_role` is `"seal"` for sets whose `signal_session` equals
`seal_session`, otherwise `"later"`.

`propose_reassessments(specs, records, payloads, basis, assessed_at, *, window_days=None, today=None, retrieved_on=None, sources=None) -> list`

For every sealed US set that already has a record: build a new record from the payload of its ticker, with
`pull_role="later"`, `prior` the set's latest record and `seal` its seal assessment. The record is returned only when
`changed(new, latest)` is true. A set whose ticker has no payload is skipped. When `window_days` and `today` (ISO date)
are given, only sets whose `signal_session` is at most `window_days` calendar days before `today` are considered.
`sources` maps set id to a list of strings for the records returned.

`removed_set_ids(view, records=None, v11_flags=None, cutoffs=None) -> set`

- `view == "corrected"`: the sets whose latest assessment has group `ARTIFACT`. A set with no assessment record is
  included when its V11 record has flag `ARTIFACT_V11`.
- `view == "at_the_time"`: `cutoffs` maps set id to the set's entry cutoff (ISO timestamp). For each set, take the
  records about it in both ledgers whose `assessed_at` is strictly earlier than its cutoff. The set is included when
  the latest of them by `assessed_at` is an artifact: a V11 record with flag `ARTIFACT_V11`, or an assessment with group
  `ARTIFACT`. When a V11 record and an assessment carry the same `assessed_at`, the assessment decides. A set with no
  cutoff, or no record before its cutoff, is not included.
- Any other view raises `ValueError`.
- `records` and `v11_flags` default to the two ledgers on disk.

`unresolved_set_ids(records=None) -> set`: the sets whose latest assessment has group `UNRESOLVED`.

`verify(records=None, specs=None) -> list`: a list of problems, empty when the ledger is sound. Each of these is a
problem: a record whose type is not `SPLIT_ASSESSMENT`; a rule other than `SPLIT_UNITS_V1`; an `assessment` that is not
one of the eleven classes; a `group` that is not the group of its assessment; a `pull_role` other than `"seal"` or
`"later"`; a set id that is not a sealed US set; a set's first record with a `supersedes` that is not `None`; a later
record whose `supersedes` is not the `record_hash` of the set's previous record; `pull_role == "seal"` on a record that
is not the set's first; a later record with no change from the one it supersedes (`changed` is false). Several records
for one set are legitimate. When `records` is `None` the ledger on disk is read and its hash chain is checked too.

### B3. The paper book report

`paper_book_report.views(rows, records, v11_flags, cutoffs) -> dict` returns three lists of book rows:
`"as_frozen"` (all rows), `"at_the_time"` (rows whose set is not in `removed_set_ids("at_the_time", ...)`) and
`"corrected"` (rows whose set is not in `removed_set_ids("corrected", ...)`). Rows keep their order.

`paper_book_report.secondary_view(rows)`: when no row's set has a `SPLIT_ASSESSMENT` record, the output is exactly what
it was before this change (the V11 section, or `""`). Otherwise it is a section headed
`## Secondary view: split-unit assessments (display only, the frozen verdict above is unchanged)` that states the counts
(confirmed, probable, unresolved, and earlier artifact tags that current evidence does not support), lists each affected
set with its tag at the time, whether that tag was recorded before the entry cutoff, and its current assessment, and
gives every book under the three views.

## Part C. Cases the independent tests must include

1. **A genuine move after a split.** A 1-for-2.8 split effective on session D; the previous bar is session D, already
   after the split; the signal session is the next one, with a recorded move of about +106%. The V11 rule tags it
   `ARTIFACT_V11`. `SPLIT_UNITS_V1` must give group `REAL`, from the scan's own pull and from a later pull alike.
2. **A split reported late.** The scan's own pull lists no split and the recorded move is extreme: the seal assessment is
   `UNEXPLAINED_EXTREME_MOVE`. A later pull lists a split on the signal session and shows the previous close re-based:
   the reassessment is `ARTIFACT_CONFIRMED`, it supersedes the seal assessment, `verify` accepts both records, the
   corrected view removes the set, and the at-the-time view does not.
3. **Unresolved evidence stays unresolved.** A set whose later pull matches nothing stays in every view, is listed by
   `unresolved_set_ids`, and is not reassessed into an artifact or a real move without new evidence.
4. **An earlier artifact tag that current evidence does not support.** A set tagged `ARTIFACT_V11` before its entry
   cutoff and assessed `REAL` afterwards is in the corrected view's books and out of the at-the-time view's books.
5. **Validation.** Two assessments for one set with a correct `supersedes` are sound. A wrong `supersedes`, a second
   `"seal"` record, an unchanged reassessment, an unknown class, a wrong group, and an unknown set are problems.
