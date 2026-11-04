# RESEARCH_CORRECTIONS_20261104: corrected runs of NEIGHBOURS_v1 and PRESSURE_v1 (pre-run record)

Written 2026-11-04 16:07 UTC, before either corrected runner has been started. This file states what will be
run, on which bytes, and how the result will be read. It is committed before the runs and is frozen from then on
(the append-only guard covers `idx-signals/research/`).

## What this is, and what it is not

- **Corrections of two existing studies.** NEIGHBOURS_v1 and PRESSURE_v1 were each run once on 2026-11-03 and
  reported no incremental value. Both original runners drop every row with a missing `fwd1`, `fwd3` or `fwd5`
  before ranking features, fitting and choosing picks, so the availability of future returns shaped the historical
  decision universe (look-ahead). The defect and the repair are described in
  `../NEIGHBOURS_v1/CORRECTION_2026-11-04.md` and `../PRESSURE_v1/CORRECTION_2026-11-04.md`. The repair is the
  existing shared evaluator `idx-signals/idxsig/research_evaluation.py`, called by the existing `run_corrected.py`
  in each study folder. That code runs as it stands at the base commit. The only change allowed is a crash fix
  under the run discipline below.
- **Not a new early-entry search.** Neither these runs nor the corrections add or change a hypothesis, feature,
  horizon, model, parameter or cost. The corrections change only how the existing specifications are evaluated, as
  the two CORRECTION files describe. This is item 5 of Fix 2 in `handoff/KOD_FIX_PLAN.md`: run the already-written
  corrected runners once into new folders and report whether "adds nothing" survives.
- **The originals stay as they are.** `PROTOCOL.md`, `ADDENDUM_1.md`, `run.py`, `REPORT.md` and `RESULT.json` of
  both studies are not touched. Outputs go only into new folders under this one.

## Code that will run (base commit d607c3250)

| File | sha256 |
|---|---|
| `idx-signals/idxsig/research_evaluation.py` (`VERSION = "CAUSAL-DAILY-RESEARCH-v1"`) | `05edabda14cf246446b6b4dd2775a2cf4a73ef70010e819850be7aaa3cc3703f` |
| `idx-signals/research/NEIGHBOURS_v1/run_corrected.py` | `b2fdae0a1024d057222a6e2ab47d92d758487ded0644e40ce8a62d8df00c347e` |
| `idx-signals/research/PRESSURE_v1/run_corrected.py` | `db003cdab03b2378bf4d1e2b69743176f2f7e7a9c8b42a2e53e0f83258ee0126` |

Interpreter: CPython 3.12.3 with numpy 2.3.5 and pandas 2.2.3, in a session virtual environment. Neither runner
downloads anything.

## Inputs, hashed before running

| Input | Bytes | sha256 | Where it lives |
|---|---:|---|---|
| `NEIGHBOURS_v1/rows.csv.gz` | 66,621,409 | `dd09e0c9f53b01d335b5594957c48635fb334dd020c2bc3ad8045d208a481c6e` | Gitignored, built by `NEIGHBOURS_v1/build.py`. Read from the main checkout. |
| `PRESSURE_v1/taker.csv.gz` | 13,321,491 | `286656c8872edd1354af69449ee1b2759d9c8a78df8cba738eb8e4849f461367` | Committed at `idx-signals/research/PRESSURE_v1/taker.csv.gz`. The main-checkout copy read here has the same sha256. |

PRESSURE_v1 is built on NEIGHBOURS_v1's rows (its protocol says so), so `rows.csv.gz` is an input to both runs.

Structural precheck, run before this file was written. It computed no outcome statistic.

- `rows.csv.gz`: 482,598 rows, 31 columns, dates 2020-05-10 to 2026-10-01, no duplicate date/ticker, `peers_ok`
  read as booleans (482,424 true), station values 1 to 5. 482,598 is also the number the original NEIGHBOURS_v1
  `REPORT.md` gives as coin-days.
- `taker.csv.gz`: 772,258 rows, no duplicate date/ticker, and no missing, negative or taker-buy-above-total volumes.

## Commands (each run exactly once, from the repository root)

```sh
/tmp/claude-0/-home-user-KOD-Machine/1c24db66-827c-592f-9e21-9f9bc0e9f7e9/scratchpad/kodvenv/bin/python \
  idx-signals/research/NEIGHBOURS_v1/run_corrected.py \
  --rows /home/user/KOD-Machine/idx-signals/research/NEIGHBOURS_v1/rows.csv.gz \
  --output idx-signals/research/RESEARCH_CORRECTIONS_20261104/NEIGHBOURS_v1

/tmp/claude-0/-home-user-KOD-Machine/1c24db66-827c-592f-9e21-9f9bc0e9f7e9/scratchpad/kodvenv/bin/python \
  idx-signals/research/PRESSURE_v1/run_corrected.py \
  --rows /home/user/KOD-Machine/idx-signals/research/NEIGHBOURS_v1/rows.csv.gz \
  --taker /home/user/KOD-Machine/idx-signals/research/PRESSURE_v1/taker.csv.gz \
  --output idx-signals/research/RESEARCH_CORRECTIONS_20261104/PRESSURE_v1
```

Run discipline:

- `write_corrected_run` refuses an existing output folder, so a repeated command fails instead of overwriting.
- The evaluator writes `predictions.csv` and `selections.csv` before it attaches any outcome. It then writes the
  outcome files `scored_selections.csv` and `RESULT.json`, and last `manifest.json` (the sha256 of each other file
  in the run folder).
- `RUN_NOTES.txt` in this folder records, for each run, the command, start and end time (UTC), exit status and
  console output.
- If a run crashes before an outcome file exists, its traceback goes into `RUN_NOTES.txt`. Only the cause of the
  crash is fixed, only if it lies outside frozen files, and in a commit of its own with a test. Any partial,
  outcome-free folder is deleted, its file list recorded in `RUN_NOTES.txt`, and the command is run again.
- Once an outcome file exists, the run is never repeated.

## Reading rule (fixed now, before the runs)

Original verdicts, copied from the frozen `RESULT.json` files:

| Study | Comparison | Original verdict | Original 3-day IC difference (95% range) |
|---|---|---|---|
| NEIGHBOURS_v1 | B minus A (neighbours over own information) | `neighbours_add_information: false` | -0.0052 (-0.0099 .. -0.0006) |
| NEIGHBOURS_v1 | C minus B (next stop over neighbours) | `next_stop_adds_information: false` | -0.0001 (-0.0036 .. +0.0034) |
| PRESSURE_v1 | P minus A (taker pressure over own information) | `"NO INCREMENTAL VALUE"` | -0.0043 (-0.0059 .. -0.0026) |

In the corrected `RESULT.json` of each run, the statistic is `ic_differences["fwd3_B-A"]`,
`ic_differences["fwd3_C-B"]` (NEIGHBOURS_v1) and `ic_differences["fwd3_P-A"]` (PRESSURE_v1). Each holds `mean`,
`lo95`, `hi95`, `known_days` and `unknown_days`. `lo95` and `hi95` are the 2.5th and 97.5th percentiles of a 20-day
moving-block bootstrap of the daily rank-IC difference (5,000 draws, seed 20261103). Days without an IC keep their
positions in the timeline instead of being compressed out.

- `lo95 <= 0`, so the interval does not lie entirely above zero: the original verdict is **CONFIRMED**.
- `lo95 > 0`, so the interval lies entirely above zero: the verdict is **CHANGED** and is reported as changed.
- `lo95` or `hi95` is null, so the evaluator produced no interval: the verdict is **NOT DETERMINED by this rule**.
  What the evaluator did produce (`mean`, `known_days`, `unknown_days`) is reported, and no substitute interval is
  computed.

Reported beside each verdict, but not part of it:

- The original protocols' second condition: in how many of the test years 2021 to 2026 the model's top 5 beat the
  baseline's top 5 (B over A, C over B, P over A). It is read from `decisions[<model>]["by_year"][<year>]["gross_observed_mean"]`. These are
  observed-only means, and a year with unknown picks is marked as such. A cost subtracted from both sides does not
  change this comparison.
- The 1-day and 5-day horizons, as diagnostics only.
- The selected, known and unknown denominators of every pick method and every horizon.
- Net means at the assumed 0.4% and 2% round trips. No verdict implies profit after eToro costs.

## Catalog handling (fixed now)

`configs/experiments.json` is changed only if `idx-signals/tests/test_experiment_catalog.py` passes and the edited
catalog loads through `idxsig.experiment_catalog.load_catalog`. If every comparison of a study is CONFIRMED, its
record moves from `RESEARCH_CORRECTION_PENDING` to `RESEARCH_CLOSED` with evidence level `REPORTED_RETROSPECTIVE`,
and the corrected `REPORT.md` and `RESULT.json` join its sources. If any comparison is CHANGED or NOT DETERMINED, the
record stays `RESEARCH_CORRECTION_PENDING` with its current evidence level, the corrected evidence joins its sources,
and its summary says that review is needed. `live_eligible` stays false either way.

## Output size

An output file of at most 10,000,000 bytes is committed as written. A larger output file is not committed. It is
listed in a `.gitignore` in this folder, and it is represented by its sha256 in that run's `manifest.json` and by a
summary in `REPORT.md`. Anyone holding `rows.csv.gz` can rerun into a new folder and compare against those hashes.

## What the corrected numbers will not show

- They are not a fresh holdout. 2023 to 2026 crypto prices were inspected by earlier studies, and the original
  results on the same data are known.
- A mean per observed pick is not a shared-account, compounded or executable return.
- Observed-only means and ICs can be biased when outcomes are missing for a reason, for example a delisted coin. The
  evaluator keeps unknown picks in the denominators and never fills them.
- A confirmed null covers these specifications only (daily bars, one ridge setting, these groups and features). It
  does not show that peers or buying pressure carry no information in any form.
- Nothing here permits promotion. The evaluator writes `"promotion": "DISABLED_PENDING_REVIEW"` into each
  `RESULT.json`.

## Files this folder will hold

- `README.md`: this pre-run record.
- `RUN_NOTES.txt`: the run log.
- `NEIGHBOURS_v1/` and `PRESSURE_v1/`: the evaluator's outputs, one folder per run.
- `REPORT.md`: original and corrected numbers side by side, denominators, and the verdicts.
- `.gitignore`: only if an output file exceeds the size limit.
