# KILL_TEST_2020_2023: the 13D kill test finished on one more year of entries (one shot, can fail, cannot confirm)

Frozen 2026-10-29, before any 2023 Schedule 13D filing, header or price was read for this test, and before any return
of the 13D question was read by anyone. Owner instruction: "Commit to it and do it. We need results."
(`handoff/decisions/2026-10-29_kill_test_2023.md`). Paper only, no orders.

## Why this exists, and why it is allowed

`KILL_TEST_2020_2022` ran once on 2026-10-28 and returned **INCONCLUSIVE**: 288 scored FIRE events against its GO rule
of 300. Because the GO rule failed on counts, `run_v2.py` never computed a return statistic and never wrote
`events_fire.csv`. **No return of this test has been read by anyone.** That record stands unchanged.

Extending the entry window before any outcome is visible is an enrollment extension, not a second look at a result: the
analyst cannot be steered by a number nobody has seen. What makes it safe is written into the code and checked by the
pins:

- The GO rule stays at **300** scored FIRE events. The bar is not lowered.
- The statistic, the plan (20-session hold, entry at the open of the first session whose 09:15 New York is after
  acceptance), the controls (v2, 200 draws, seed 20261007), the abstention rules (dilution in 20 sessions, a 15% move
  already, under USD 50M, unknown size) and the verdict rule are byte-identical to the frozen v2 code. `kt_lib.py`
  differs from `KILL_TEST_2020_2022/kt_lib_v2.py` in exactly three constants: the entry window end and the two
  evidence cut-offs.
- Only the entry window and the quarters collected change.

This overrides one line written by the session itself on 2026-10-28, in the outcome section of
`handoff/decisions/2026-10-28c_proof_program.md`: "must not be rerun with a lower bar or a wider window." The owner
overrode it explicitly. The bar is not lowered; the window is.

## What changes

| | 2020-2022 | 2020-2023 |
|---|---|---|
| Quarterly `form.idx` collected | 2020Q2..2022Q4 | 2020Q2..2023Q4 |
| Entry sessions scored | 2020-07-01..2022-11-30 | 2020-07-01..**2023-11-30** |
| Panel bars loaded | to 2022-12-30 | to **2023-12-29** |
| Evidence stored (submissions, share facts) | to 2022-12-31 | to 2023-12-31 |
| Everything else | | unchanged |

2023-11-30 is the last entry session whose 20-session hold ends inside the panel, which runs to 2023-12-29. **The
sealed US holdout (2024 onward) is never loaded.**

## What it still cannot do

- **Survivor-only prices.** The panel holds the names that still exist; delisted 13D subjects are missing, and they are
  the more failure-prone group. The bias pushes a long-event mean upward. So this test can **fail** the family and
  cannot **confirm** it. NOT_KILLED is not a green light.
- **2023 is not virgin data for the lab.** It is outside the sealed holdout but was the validation year of earlier
  experiments (E2, E5). It is unused by *this* test, whose 2020-2022 run loaded bars only to 2022-12-30. A NOT_KILLED
  on this window is therefore weaker still; a KILL remains informative.
- **One reading.** This is the first and only time a return is read for the 13D kill question. The 2020-2022 run
  consumed a trial slot but no inferential budget on returns.

## Collection

Every quarter is collected fresh, not spliced onto the 2020-2022 file, whose stored evidence is truncated at
2022-12-31 and would be wrong for a 2023 entry. `collect.py` writes `events.csv.gz` (one row per original SC 13D with
its header fields, SEC tickers, rule inputs and collection-stage drop reason) and `COLLECT.json` (every request as
url, HTTP status and sha256, plus the funnel counts). Responses are parsed in memory and never written to disk. The
declared SEC contact comes from `KOD_SEC_CONTACT`, inline on the command line, and is never written anywhere.

`COLLECT.json` also records a **cross-check**: the re-collected 2020-2022 rows compared against the frozen
`KILL_TEST_2020_2022/events.csv.gz`. A material disagreement there is a reason to stop and investigate, not to run.

## Rules, statistic and verdict

Unchanged from `KILL_TEST_2020_2022/PROTOCOL.md`, which remains the normative description of every rule in the funnel,
the abstention classes, the plan, the controls and the statistic. In brief: every original `SC 13D` in the quarterly
index; the subject and acceptance time from the filing's `-index-headers.html`; the subject's first SEC ticker present
in the pinned US repair panel; no other original 13D on the same subject in the 90 calendar days before (counted on
the filing date); an operating issuer; then FIRE unless an abstention rule binds.

- **GO rule (counts only, before any return)**: at least 300 scored FIRE events, else INCONCLUSIVE and no return is read.
- **Primary**: mean excess, t from 10,000 bootstrap resamples of the ISO weeks of the entry session (seed 20261203).
- **KILL** if the mean excess is at or below 0. **NOT_KILLED** if above 0, which is not a confirmation.
- **Descriptive only**: win rate and its Wilson interval, the median, the ABSTAIN class, each abstention rule's class.

## On KILL

The session advises the owner to stop the prospective SEC13D family, which today means both `SEC13D` and its child
`SEC13D_V2`. Nothing stops automatically and no record is rewritten: the sealed sets keep resolving on their own
schedule, and the decision is the owner's.

## Running it, once

```sh
cd idx-signals
KOD_SEC_CONTACT=<email> python3 research/CATALYST_REGISTER_v1/KILL_TEST_2020_2023/collect.py
python3 research/CATALYST_REGISTER_v1/KILL_TEST_2020_2023/freeze.py     # writes PINS.json; refuses over an existing one
python3 research/CATALYST_REGISTER_v1/KILL_TEST_2020_2023/run.py        # refuses if results/RESULT.json exists
```

## Forbidden

A second run; a lower GO bar; a wider window again; loading any bar after 2023-12-29; editing this directory or
`KILL_TEST_2020_2022`; reading the result before the pins are committed; any order.
