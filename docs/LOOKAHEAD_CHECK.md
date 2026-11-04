# Look-ahead check for study scripts

Every look-ahead defect found in KOD so far was in study code, not in the shared library:
rows dropped because a future return was missing (NEIGHBOURS, PRESSURE), random controls
that excluded coins triggering in the next 72 hours, and outcome-dependent bucketing
(`handoff/KOD_FIX_PLAN.md`, Fix 2). `idxsig.lookahead` and `tools/check_no_lookahead.py`
let a study author test their own decision code for that class of defect before a run.

The question it answers: **does any decision dated at or before a cutoff T change when
information after T is removed or replaced?** If it does, that decision used information
from after its own date.

## The three checks

| Check | What changes before `decide` is rerun | Use it when |
| --- | --- | --- |
| `truncation_check` | Rows dated after T are removed; a declared lagged value not yet known at T is set missing | The study can run on a shorter table (the default choice) |
| `scramble_check` | Every row is kept; the same values are replaced with seeded noise | The study needs its full calendar or row count, or deciding is separate from scoring |
| `compare_decisions` | Nothing is run; two decision tables the study already wrote are compared | The study writes dated decision files and cannot be imported |

Each check compares decisions by their key columns, at every cutoff, against the run on
the full data. Rows and columns may come back in any order. Decisions after the cutoff are
counted but not compared. Before any cutoff run, `decide` runs twice on the full data; if
the two runs differ, the check stops, because randomness would look like look-ahead.

Truncation catches leaks through the presence of later rows (a dropped row, a centred
window edge); scramble keeps every row and cannot. Scramble floats include missing values
(one in four by default) so that dependence on later missingness can still show; this is
randomised, so a second seed adds confidence. Run both where the study allows.

## How a study author uses it

1. Put the deciding step in one function, `decide(data) -> DataFrame`, that takes the
   study's input table and returns one row per decision with a decision-time column and
   key columns that identify each decision once. It must not read files or the clock.
2. Declare every column whose value on a row is only known later: forward returns,
   labels, "triggered within the next 72 hours" flags. Give each its lag, conservatively
   the horizon plus any maturity embargo. An undeclared label is invisible to the check
   (`test_a_label_on_its_signal_row_is_caught_once_its_lag_is_declared` shows exactly that).
   A lagged column must be able to hold a missing value: a numpy float column or a pandas
   nullable one (`Int64`, `Float64`, `boolean`). Store a flag as `astype("boolean")`.
3. Choose three to five cutoffs across the decision period, each after the first decision
   and before the last input time. Put at least one inside a refit or rebalance period,
   after its refit date: a refit that peeks ahead changes only the decisions made after it.
4. Add a unit test next to the study (preferred), or run the command line tool.

```python
from datetime import timedelta

from idxsig.lookahead import scramble_check, truncation_check

settings = dict(
    data_time_column="date",
    time_column="date",
    key_columns=("date", "ticker"),
    cutoffs=("2024-01-02T00:00:00Z", "2025-01-02T00:00:00Z", "2025-07-01T00:00:00Z"),
    value_lags={"fwd3": timedelta(days=5)},
)
for check in (truncation_check, scramble_check):
    report = check(decide, rows, **settings)
    assert report.verdict == "PASS", report.to_dict()["first_leak"]
```

From the repository root, with the idx-signals requirements installed:

```
python3 tools/check_no_lookahead.py module study.py rows.csv.gz \
    --data-time-column date --time-column date --key-columns date ticker \
    --cutoff 2024-01-02T00:00:00Z 2025-01-02T00:00:00Z --lag fwd3=5D

python3 tools/check_no_lookahead.py compare decisions_full.csv decisions_cut.csv \
    --time-column date --key-columns date ticker --cutoff 2025-01-02T00:00:00Z
```

Module mode executes the given study file and reads the data with `pandas.read_csv`
defaults. A study whose own loader parses differently should call the library from its own
test. Compare mode reads every cell as the text written, so both files must come from the
same code; only an empty cell counts as missing. Scramble options are `--seed` (default 0),
`--scramble-columns` and `--missing-share` (default 0.25). By default scramble reaches
every numpy or pandas nullable numeric or bool column except the time column, so the
canonical panel's `Int64` prices are scrambled; a column holding numbers in any other
dtype (pyarrow, sparse, complex) is refused rather than skipped. The report lists
`scrambled_columns` and `unscrambled_columns`, which together name every data column.
The tool prints one JSON verdict and exits 0 for PASS, 1 for LEAK and 2 when the check
could not run.

## Reading a verdict

`first_leak` names the earliest cutoff with a difference and its first differing decision
(by decision time, then key). Every cutoff also reports what it compared: rows removed or
values hidden (truncation), values replaced (scramble), decisions in scope on each side,
decisions compared and decisions differing.

| Kind | Meaning | Typical cause |
| --- | --- | --- |
| `ONLY_IN_REFERENCE` | The full data made a decision that the cut data did not | Rows dropped because a future value is missing; a centred window's edge |
| `ONLY_IN_CANDIDATE` | The cut data made a decision that the full data did not | A filter that excludes on later events, such as next-72-hour triggers |
| `VALUE_DIFFERS` | Same decision, different value, or its decision time moved | Full-sample means or ranks, centred windows, refits on unmatured labels |

## What a PASS does and does not show

A PASS shows that, on this data and at these cutoffs, no decision dated at or before T
depended on rows or declared values after T. It does **not** show:

- that the input data was available at its stated time (publication lags, revisions,
  backfilled vendor history, survivorship of the universe);
- that labels nobody declared with a lag are harmless;
- that other data, other cutoffs or code paths this data never reaches are clean;
- that the scoring of frozen decisions, the cost model or the statistics are right.

## Inputs that are refused rather than guessed

Each refusal raises `LookaheadCheckError` (exit 2 in the tool); a check that cannot run
never reports PASS. An exception raised by the study itself propagates unchanged from the
library; the tool turns it into an ERROR verdict and prints the traceback.

| Input | Behaviour |
| --- | --- |
| Times without a UTC offset | Refused unless `assume_utc=True` / `--assume-utc` states they are UTC; the report records the choice |
| Times in other offsets, such as `+07:00` | Converted to UTC; cutoffs are reported in UTC |
| Epoch numbers, unparseable or missing times | Refused: an epoch's unit (s, ms, us) is ambiguous |
| Unsorted input rows | Cut by a time mask, never by position |
| Empty data, a study with no decisions | Refused |
| Duplicate or missing decision keys, keys only in the index | Refused, naming the first offending key or row |
| A study that gives different decisions on identical input | Refused as not deterministic |
| A cutoff before the first decision, or one that removes or replaces nothing | Refused: it would compare or change nothing |
| Numbers in a dtype scramble cannot reach (pyarrow, sparse, complex) | Refused by the default scramble selection; name `columns` to leave them out explicitly |
| A lag on a column that cannot hold a missing value (numpy int or bool) | Refused; store it as float or a pandas nullable dtype |
| A study that edits its input in place | Harmless: each run receives its own copy |

## Validation and scope

From `idx-signals`:

```
python3 -m unittest tests.test_lookahead_check tests.test_check_no_lookahead -v
```

The tests run synthetic, seeded toys only. A centred rolling mean, a full-sample mean and
rows dropped when the future close is missing must each FAIL truncation and scramble; the
trailing-window twin must PASS both; a forward label stored on its signal row must FAIL once
its lag is declared. The centred window must also FAIL scramble on rows read through
`idxsig.panel.load`, whose prices are pandas `Int64`. No historical study was run and no
frozen research file was edited.
Adding "passes check_no_lookahead" to every new protocol and marking old studies in the
experiment catalog (Fix 2, items 4 to 6) are separate changes.
