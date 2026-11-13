# SPLIT_REVISIONS_v1: handoff to the architect

Written 2026-11-12 (UTC). Times in this file are UTC.

Terms used here. **V11** is the existing tagging rule `SPLIT_ARTIFACT_V11` (`idxsig/split_flags.py`, ledger
`paper/split_flags.jsonl`). **SPLIT_UNITS_V1** is the rule this branch adds (`idxsig/split_units.py`). A **set** is a
sealed US speculation set. The **KODCHECK audit** is the audit of 2026-11-12, kept outside this repository. An
**artifact** is a recorded one-day move of +30% or more that did not happen: a reverse split left the previous close in
pre-split units.

## 1. State of the branch

- Branch `fable/kod-split-revisions-20261112`, based on commit `134f58f`. It has not been pushed. It is delivered as a
  git bundle; pushing and merging are the owner's and the architect's decisions.
- The default branch has moved to `9573c48` since. The 448 files changed there are data and reports; none is under
  `idxsig/`, `tests/`, `tools/` or `handoff/`. Section 9 reports a trial merge onto `9573c48`.
- No ledger was written on this branch. `paper/split_assessments.jsonl` does not exist until the first run after the
  merge.

## 2. What changes

| File | Change |
|---|---|
| `idxsig/split_units.py` (new) | The rule SPLIT_UNITS_V1: check C01 of the KODCHECK specification, steps 1 to 5, with its addendum. It asks which session supplied the previous close. |
| `idxsig/split_assessments.py` (new) | A second append-only ledger, `paper/split_assessments.jsonl`. A set can be assessed more than once; each later record names the record it supersedes. Readers for three views, and a validator. |
| `idxsig/paper_book_report.py` | The secondary section shows the books three ways once a planned spike has an assessment: as frozen, as known at the time, corrected. Without any assessment the section is the V11 one, unchanged. |
| `idxsig/cli.py` | `split-assess` (one-off command, with `--dry-run`); `paper-verify` also validates the new ledger; the nightly hook assesses the sets just sealed and reassesses the sets of the last 14 days from the same pull. |
| `tools/check_append_only.py` | The new ledger is append-only. |
| `tests/test_split_assessments.py`, `tests/test_split_units_fixture.py`, `tests/fixtures/split_units_cases.json` | Tests (section 4). |
| `research/SPLIT_REVISIONS_v1/` | Protocol, contract, two contract addenda, the test author's questions, scripts and results. |

Untouched: the V11 rule, its ledger, its 23 tests, every detector, cone, plan, decision, cutoff and frozen record.

## 3. The four required outcomes

**3.1 The named cases.** On the 168 sets at `134f58f`, from the provider responses recorded on 2026-11-12
(`results/DRY_RUN.md`):

- SMX 2026-11-10 is `REAL_MOVE_AFTER_SPLIT`. Its recorded previous close is found unchanged in the pull on
  2026-11-09, the split's own effective session, so both closes are in post-split units. The issuer's filing says
  adjusted trading began on 2026-11-09
  (https://www.sec.gov/Archives/edgar/data/0001940674/000149315226049929/ex99-1.htm). The V11 tag `ARTIFACT_V11` on
  this set is not supported.
- GOVX and SLXN 2026-11-11 are `ARTIFACT_CONFIRMED`. The pull lists a 1-for-24 split on the signal session and shows
  the previous session's close multiplied by 24. Recorded moves +1,829% and +2,863%; adjusted -19.64% and +23.47%.
  Their V11 tags are `INDETERMINATE`, assigned at 2026-11-11 23:00 from a pull that did not list the split yet.
- The corrected view leaves out 11 sets: ATYR, MASK, WHLR (2026-10-30), XXII (2026-11-05), GOVX, SLXN (2026-11-11)
  confirmed; PARA, SCAG, ENLV (2026-10-28), OMEX (2026-10-30), TOPS (2026-11-09) probable. SMX is back in it.

**3.2 Revisions.** `split_assessments.verify` accepts any number of assessments of one set, provided each later one
supersedes the set's previous record, and rejects a second first assessment, a broken chain and an edited line. The
paper book report is the only reader of split tags in the code base (checked by search); it now reads the standing
assessment. The other consumers of the sets (speculation register, learners, decision ledger, catalyst tags, language
model calls, paper account) read no tag at all, before or after this branch. Their published figures include the
artifact sets. `results/EFFECT.md` shows each of them with and without those sets. Making them exclude a set would
change frozen protocols and is not done here.

**3.3 Two histories.** Three views, side by side in the report:

- *As frozen*: every planned spike. All verdicts and looks stay on this.
- *Known at the time*: leaves out only the sets whose artifact tag or assessment was recorded before the set's entry
  cutoff. At `134f58f` that is one set, SMX 2026-11-10, tagged 52 minutes before its cutoff, wrongly. No correct
  artifact tag had been recorded before an entry cutoff.
- *Corrected*: leaves out the sets that current evidence classes as artifacts. The report states that this uses later
  evidence and is not a filter that was available before the trade.

**3.4 Prevention.** `results/SIMULATION.md` runs the function the nightly job calls four times on a temporary ledger:

| Night | What the pull holds | Result |
|---|---|---|
| 1 | The scan's own pull; the split of GOVX and SLXN is not listed yet (a reconstruction, checked against the sealed previous closes) | 168 first assessments; GOVX and SLXN `UNEXPLAINED_EXTREME_MOVE`, unresolved, not passed; SMX real |
| 2 | The split is listed and the closes are re-based | 2 reassessments: GOVX and SLXN become `ARTIFACT_CONFIRMED`, each naming the record it supersedes |
| 3 | No bars for GOVX | 1 record, `NOT_ASSESSABLE`; GOVX stays out of the corrected view |
| 4 | GOVX answered again | 1 record, `ARTIFACT_CONFIRMED` |

Every night: validator problems 0, and running the same night twice adds 0 records. The three cases asked for are
covered: a genuine move after a split (SMX), a split reported late (GOVX, SLXN), and unresolved evidence (five
responses that could not be assessed, and the night without bars). The scheduled job itself has not run this code;
section 5 says what to check when it does.

One set sealed after the rule was frozen gives a live case. ARAI 2026-11-12 (set
`SPEC-SCAN-US-2026-11-12-G2_RET30-ARAI`, on the default branch at `9573c48`) records +3,392%: close 2.06 against a
previous close of 0.059. Its V11 tag is `INDETERMINATE`. The provider's response of 2026-11-13 00:04, about an hour
after sealing, lists no split and shows 0.059 on 2026-11-11. SPLIT_UNITS_V1 gives `UNEXPLAINED_EXTREME_MOVE`:
unresolved, neither passed as real nor called an artifact. Its entry cutoff is 2026-11-13 13:30. This is the state
GOVX and SLXN were in on their sealing night.

## 4. Evidence for the merge note's six questions

1. **Tests by a different agent.** Yes for the two new modules and the report's readers.
   `tests/test_split_assessments.py` (147 tests) was written by a separate agent from `CONTRACT.md` and the two
   addenda, without access to the implementation; its 32 questions on the contract are in `CONTRACT_QUESTIONS.md`.
   `tests/fixtures/split_units_cases.json` holds 178 observations with expected classes taken from the KODCHECK
   challenge cases, written on 2026-11-12 by another separate agent. The implementer ran the tests; the test author
   never did. No for the nightly hook and the `split-assess` command: the contract gave no interface for them, so
   they have no independent tests and are exercised only by the simulation and the dry run.
2. **Real-sample test for the parser of outside data.** No committed sample. `split_units.payload_bars` parses the
   provider's chart response, and raw provider responses are kept out of this repository. It was run on the 151
   responses recorded on 2026-11-12; `results/dry_run.json` lists the SHA-256 of each. The existing parser
   `split_flags.provider_splits` is reused unchanged.
3. **Look-ahead check.** Not applicable: no study is added or changed. The effect table recomputes only statistics
   each consumer's own report already prints, with that consumer's code, and takes no scheduled look.
4. **Architect's approval.** The architect's to give.
5. **Tradeable, and could it change what the owner does.** Not applicable: descriptive. It changes no plan or
   decision. It changes which paper-book figures are shown beside the frozen ones.
6. **Alert when it breaks.** The hook prints its tally in the nightly log and never blocks sealing; a failure prints
   `split assessments skipped (...)`. `paper-verify` fails on a broken ledger. There is no separate alert. A set
   classed real although its previous close was not found in the pull is printed with the mark
   `[classed real, previous close not found in the pull]`.

Checks run on the branch: `python3 -m unittest discover -s tests` runs 2,094 tests, with 9 failures or errors in
`test_lookahead_check` (1), `test_guidance_revision` (6) and `test_premove_evaluation` (2). The same nine fail on the
unmodified commit `134f58f` in this environment, which has pandas 3.0.5 where the repository pins a version below 3.
`idxsig rules`, `idxsig verify-runs`, `idxsig paper-verify` and `tools/check_append_only.py --all` pass.

## 5. After the merge

On the machine that holds the nightly pull's raw responses (the command refuses to write where it cannot read them):

```
cd idx-signals
python3 -m idxsig split-assess --dry-run
python3 -m idxsig split-assess \
  --source SPEC-SCAN-US-2026-11-10-G2_RET30-SMX=https://www.sec.gov/Archives/edgar/data/0001940674/000149315226049929/ex99-1.htm \
  --commit
```

The dry run should list the 11 artifact sets of section 3.1 and no line for SMX 2026-11-10 other than
`REAL_MOVE_AFTER_SPLIT`; the sets sealed since `134f58f` will appear as well. If the command is not run, the first
nightly run after the merge assesses every pending set by itself, without the source text on SMX's record.

On the next scheduled run, check:

- the log has a line `split assessments: ...`, and sealing completed;
- `paper/split_assessments.jsonl` gained one record for each US set sealed that night, with `pull_role` `seal`;
- `python3 -m idxsig paper-verify` passes;
- the paper book report ends with the section "Secondary view: split-unit assessments" and its three views;
- on later nights a line marked `[reassessment]` appears only when a set's assessment changed;
- ARAI 2026-11-12: on the first run whose pull lists a split for it, its assessment should be `ARTIFACT_CONFIRMED`
  (as a first assessment, or as a reassessment that supersedes an earlier unresolved one), and the corrected view
  should leave the set out from then on. If no split is ever listed, it stays unresolved, as VCIG has.

## 6. Effect on published results

`results/EFFECT.md`, descriptive, at `134f58f`. Left: every record. Right: without the 11 artifact sets.

| Result | As published | Without the artifact sets |
|---|---|---|
| Paper book KOD | 94 positions, 2 closed, 1 win, -$80, average -4.02% | 91 positions; the rest unchanged |
| Paper book ALL | 106 positions, 11 closed, 4 wins, -$1,140, average -10.37% | 98, 7, 2, -$1,087, average -15.52% |
| Paper book AVOIDED | 12 positions, 9 closed, 3 wins, -$1,060, average -11.78% | 7, 5, 1, -$1,006, average -20.13% |
| Speculation register US, plan BASE5 | 57 resolved, mean -12.50%, twins -1.82%, difference -10.68%, t -2.24 | 50, -10.27%, -0.94%, -9.33%, t -2.30 |
| LEARNER v2.4, NEXT_DUMP10_1 | 88 pairs, AUC 0.654, benchmark 0.630 | 82, 0.639, 0.608 |
| LEARNER v2.4, DUMP10_5 | 20 pairs, AUC 0.643, benchmark 0.583 | 16, 0.683, 0.817 |
| LEARNER v2.2, US statements | 52 per statement, Brier raw about equal to anchor | 45, the same |

No verdict changes and no scheduled look was reached either way. The figures were identical in all three dry runs.

## 7. Known limits

- **Eight sets stay unresolved** and remain in every view. Five could not be assessed: for GNTA 2026-11-02, HUBC
  2026-11-03, RCT 2026-11-06 and SGRX 2026-10-30 the provider returned no bars, and for ADIL 2026-10-28 only the
  signal session's bar. NUWE 2026-10-27 is `UNITS_INCONSISTENT`. VCIG 2026-11-02 and OMH 2026-11-04 are
  `UNEXPLAINED_EXTREME_MOVE`: the provider lists no split. For VCIG the issuer's filing shows a 1-for-18 share
  consolidation effective 2026-11-02
  (https://www.sec.gov/Archives/edgar/data/0001930510/000121390026113645/ea0309953-6k_vciglobal.htm), which makes the
  recorded +4,728% about +168%. The rule reads the provider only; a class set from a second source is not built.
- **Two narrow paths still class a set as real without finding its previous close** (the test author's questions 25
  and 26): `NO_ACTION_FOUND` when a set's recorded previous session has no bar in a later pull although other bars
  exist, and `REAL_MOVE_AFTER_SPLIT` when the pull lists a split that does not explain the move and holds no bar
  before the signal session. None of the 168 sets is on either path. Such a set is marked in the log (section 4,
  question 6); its class is not changed.
- **The contract was corrected twice after results were seen**, both times disclosed and timestamped: addendum 1 after
  the first dry run, addendum 2 after the test author's questions. The earlier outputs are kept in
  `results/first-run/` and `results/second-run/`. The same five sets are among the 150 sets the KODCHECK audit of
  2026-11-12 reported as "no corporate action found"; that count should read 145.
- **Night 1 of the simulation is a reconstruction.** No pull of a sealing night was available to this branch.
- A reassessment covers sets whose signal session is at most 14 days old. A split the provider lists later than that
  is caught only by running `split-assess` without `--window-days`.

## 8. Reproduction

From `idx-signals/`, with `EVIDENCE` the folder of provider responses recorded on 2026-11-12 (kept outside the
repository) and `KODCHECK_RESULT` the audit's result file:

```
python3 -m unittest tests.test_split_assessments tests.test_split_units_fixture tests.test_split_flags
python3 research/SPLIT_REVISIONS_v1/dry_run_and_effect.py EVIDENCE KODCHECK_RESULT
python3 research/SPLIT_REVISIONS_v1/render_results.py
python3 research/SPLIT_REVISIONS_v1/simulate_nightly.py EVIDENCE
```

## 9. Trial merge onto the current default branch

On 2026-11-13 00:10 the branch was merged, in a throwaway copy that was then deleted, onto `9573c48` (183 US sets).
The merge had no conflict. On the result: the split tests and the paper book tests pass (179 tests:
`test_split_assessments` 147, `test_split_units_fixture` 2, `test_split_flags` 23, `test_paper_book` 7);
`idxsig paper-verify` passes; `tools/check_append_only.py` passes for `--all` and for the range of the merge. The
merge-note check was not run: it needs the repository's full history, and the note is the architect's to write.
