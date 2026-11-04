# KILL_TEST_2020_2023, addendum 1: the collection and its cross-check (written before the run)

Collection 2026-10-29 06:17:11Z to 06:45:18Z: 7,822 requests, 241 non-200, all of them 404s on the XBRL share-count
concept (such issuers become MV_UNKNOWN and abstain, as in 2020-2022, where 164 of 1,632 concept reads were 404).
Every header parsed; every submissions file read. 4,857 original SC 13D filings (3,597 to 2022-12-31, the same count as
the frozen file; 1,260 in 2023), 1,475 operating subjects kept at the collection stage.

## The cross-check against the frozen 2020-2022 file

`COLLECT.json` records `cross_check_2020_2022`. Read correctly, it passes. Two notes on reading it:

**A comparison artefact.** The function compares the frozen file (read as text) with the in-memory frame, whose
`subject_cik` and `header_status` are integers, so it reports all 3,597 rows as differing on those two columns.
Compared as text, after the data were written, every column that a rule reads agrees on every shared filing:
acceptance time 0 differences, subject CIK 0, subject name 0, tickers 0, header status 0. `collect.py` is pinned and
committed, so the artefact is recorded here rather than patched.

**The columns that differ, and why.**

| Column | Rows differing | Reason |
|---|---|---|
| `dilution`, `opforms` | 1,133 and 1,930 | the new file stores evidence through 2023-12-31, the frozen one through 2022-12-31; a rule reads only evidence up to the filing's acceptance date, so no 2020-2022 classification changes |
| `repeat_of`, `drop_reason` | 2 | the calendar-day repeat rule, below |
| `submissions_status`, `concept_status` | 5 | five filings dated before 2020-07-01 (SKIP_SEED_ONLY, never scored) whose subjects also filed in 2023 and so had their evidence read this time; the frozen file left those cells empty |

**The two repeat-rule rows.** The frozen 2020-2022 file was collected with the v1 library, whose repeat rule counted
seconds (90 x 86,400); its `run_v2.py` recomputed the rule in calendar days at run time, so the run was right but the
collection-stage flag in the file was stale. This collection applies the calendar-day rule at both stages.

- Arcus Biosciences, `0001564590-20-046531` (filed 2020-10-15, 90 calendar days after `0001104659-20-084444`):
  now SKIP_REPEAT_90D at collection, as the 2020-2022 run already treated it.
- TMC the metals company, `0001213900-21-068176`: accepted 2021-12-30 17:32:58, after 5:30 pm, so EDGAR dates it
  2022-01-03, 91 calendar days after `0001013762-21-000069` (2021-10-04). Not a repeat under the calendar rule (the
  seconds rule, at 87 days, had called it one). Its evidence is read this time; in the 2020-2022 run the stale
  collection flag had left its evidence empty, so that run could not classify it.

One filing in 3,597 is affected in each direction. Nothing in the frozen file or its result is changed.

## Pins

`freeze.py` wrote `PINS.json` over the collected files at 06:46Z. The run happens only after this addendum, the data
and the pins are committed.
