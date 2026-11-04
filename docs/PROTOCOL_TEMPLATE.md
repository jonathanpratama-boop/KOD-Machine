# Protocol template

Copy this file to `idx-signals/research/<STUDY_ID>/PROTOCOL.md` and fill every section **before** any outcome data is
downloaded or read. Commit and push it first; the run happens once, afterwards. A crash before any outcome may be fixed
with a note in `RUN_NOTES.txt`; any change after an outcome is a new version.

## 0. Feasibility gate (answer first; any "no" or "nothing" means NO-GO, recorded and not run)

| Question | Answer |
|---|---|
| **Executable?** Venue the owner can use (eToro, Stockbit, or a named proxy), round-trip cost used (eToro crypto ~2% owner estimate; state the source), speed the rule needs vs speed available (manual, hourly, daily) | |
| **Known answer?** Two or three prior results on this question: published sources and/or earlier KOD studies (paths), and what they found | |
| **Decision value?** Which money decision changes, and which result would change it | |
| **New information?** Does it use information KOD has never tested? (`handoff/timing/IDEA_PARKING_LOT.md` gate) | |

Gate result: **GO / NO-GO**, with one line why.

## 1. Question
One falsifiable question, in one sentence.

## 2. Data
Sources, exact universe, membership as of each decision time, time range, and which periods were already examined by
earlier studies (exposure). Outside-data parsers used, each with a real-sample test (`handoff/claude/REAL_SAMPLE_INVENTORY.md`).

## 3. Timing (no look-ahead)
When each input becomes known, when a decision is made, and when the first executable price exists. The study must pass
`tools/check_no_lookahead.py` (`docs/LOOKAHEAD_CHECK.md`) before its outcome run.

## 4. Rule, controls and outcomes
Entry, exit, costs (named cost profile), controls chosen from information available at decision time only (past-only
exclusions), outcome definitions, and the primary endpoint. Secondary endpoints cannot rescue a failed primary endpoint.

## 5. Statistics
Estimator, uncertainty method (block or cluster bootstrap with its unit), seed, number of tests counted.

## 6. Reading (fixed now)
The exact pass, fail and inconclusive conditions, and what each one leads to (for example: pass -> prospective paper log;
fail -> close and record in the clue ledger).

## 7. Reviews
Tests written by a different agent than the code; the architect's approval before the result merges into the default
branch (`handoff/merges/TEMPLATE.md`).
