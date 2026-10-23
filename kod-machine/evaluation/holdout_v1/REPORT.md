# Held-out release reader measurement (holdout_v1): report of 23 October 2026

## What was measured

The release reader on six US issuers it had never seen. For each issuer the set has two releases: the latest results release and the one before it.
The questions asked of each pair:

- the reported quarter;
- revenue, net income and diluted EPS;
- the year-ago revenue and its growth;
- for the two companies that gave one, the earlier outlook compared with the result;
- for the four that did not, that no outlook comparison is invented.

The set was chosen and its expected answers were written before any reader change, by a separate agent that never ran KOD on these documents (see
[PROTOCOL.md](PROTOCOL.md)). It was sealed and pushed in commit `3a2751d`. The reader work that followed (commits `92c97a1` and `9327047`) used a
disjoint set of development releases, the other half of the same ticker partition, and never opened this set.

The measurement was run once, with this command:

    python3 evaluation/run_eval.py --tasks evaluation/holdout_v1/tasks.json --runs 2 --no-baseline

The same task file (SHA-256 `7085c3a7…`) and runner were used for both columns. Both runs of each column were identical.

## Result

| | Before the reader work (`c2eb2e4`) | After it (`9327047`) |
|---|---|---|
| Tasks fully answered | 0 of 6 | 2 of 6 |
| Expected answers: correct / withheld / wrong | 15 / 20 / 2 (of 37) | 28 / 10 / 0 (of 38) |
| All checks, including the currency of each figure found: correct / missed / material errors | 18 / 20 / 2 | 39 / 10 / 0 |

The number of checks differs between the columns because some checks exist only when an answer is given (the currency of a figure, the growth beside a
year-ago figure).

**Before:** the two wrong answers were one company's revenue, shown both in thousands and unscaled (18,048 thousand and 18,048). That is now one
figure in thousands.

**After:** every remaining miss is a withheld answer. No wrong figure, period, sign or outlook is shown.

| Task | After | Withheld |
|---|---|---|
| HO-DRMA | 6 of 6 | — |
| HO-SPIR | 10 of 10 | — |
| HO-CHGG | 9 of 10 | the revenue outlook (a range for the quarter in the earlier release) is not read |
| HO-CBUS | 8 of 9 | diluted EPS |
| HO-NATL | 6 of 8 | net income and diluted EPS |
| HO-TDC | 0 of 6 | the release is refused: no table KOD recognises, so nothing is read |

## What this shows, and what it does not

- **No wrong answers.** On releases it had not seen, the reader answered 28 of 38 questions correctly and withheld the other 10. It gave no wrong
  answer.
- **A small sample.** Six companies, all reporting the calendar quarter ended 30 June 2026. No fiscal-year company or currency other than US dollars is
  in this set.
- **Before the review fixes.** Eight wrong-answer cases that an adversarial review constructed against the first version of the reader were fixed
  before this measurement. They are tests in `tests/test_earnings_reader_v2.py`.
- **Now used.** This set has been measured. A change made because of its misses would no longer be measured independently by it. The misses above
  are the starting point for the next development round, and a new held-out set should be prepared before that work is measured.
