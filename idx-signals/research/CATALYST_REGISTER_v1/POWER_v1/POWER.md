# POWER_v1: how long until a family can answer

`pairs_needed = (t_min x sd / edge)^2`, `years = pairs_needed / events_per_year`. sd is the spread of one set's paired excess, measured below; edge is the true mean excess, which nobody knows and which the table therefore scans. t_min is 3.0, the lab's standing floor.

## Spread, measured (test 26's scored events; a design read, not a new effect read)

| Hold | Subset | n | mean excess | sd of excess |
|---|---|---|---|---|
| 20 | all events | 2,964 | +1.01% | 0.156 |
| 20 | winsorised 5% | 2,964 | +0.54% | 0.107 |
| 20 | top-executive buyers | 834 | +1.41% | 0.171 |
| 20 | price band 0 | 75 | +1.36% | 0.457 |
| 20 | price band 1 | 407 | +1.99% | 0.223 |
| 20 | price band 2 | 986 | +0.54% | 0.150 |
| 20 | price band 3 | 1,496 | +1.05% | 0.098 |
| 60 | all events | 2,964 | +1.80% | 0.308 |
| 60 | winsorised 5% | 2,964 | +0.72% | 0.190 |
| 60 | top-executive buyers | 834 | +3.36% | 0.412 |
| 60 | price band 0 | 75 | +8.49% | 1.234 |
| 60 | price band 1 | 407 | +2.31% | 0.349 |
| 60 | price band 2 | 986 | +1.78% | 0.269 |
| 60 | price band 3 | 1,496 | +1.33% | 0.178 |

Hit rate at hold 20 in test 26: 46.5% beside a mean excess of +1.0%. The edge is a minority of large winners.

## Pairs needed at t >= 3.0

| Edge | sd 0.156 (hold 20, all) | sd 0.098 (hold 20, above USD 20) | sd 0.308 (hold 60, all) |
|---|---|---|---|
| 0.5% | 8,785 | 3,447 | 34,106 |
| 1.0% | 2,197 | 862 | 8,527 |
| 1.5% | 977 | 383 | 3,790 |
| 2.0% | 550 | 216 | 2,132 |
| 3.0% | 245 | 96 | 948 |

At the conventional one-sided 0.01 (t 2.33) the same rows need 60% of these pairs; the t >= 3.0 floor is kept, so the difference is a stated cost.

## Years to an answer at t >= 3.0 (hold 20, sd 0.156, except the above-20 row at sd 0.098)

| Family | Events a year | edge 0.5% | edge 1.0% | edge 1.5% | edge 2.0% | edge 3.0% |
|---|---|---|---|---|---|---|
| SEC13D (FIRE) | 125 | 70.3 | 17.6 | 7.8 | 4.4 | 2.0 |
| DILUTION_8K | 779 | 11.3 | 2.8 | 1.3 | 0.7 | 0.3 |
| FORM4 | 1,482 | 5.9 | 1.5 | 0.7 | 0.4 | 0.2 |
| FORM4 above USD 20 | 748 | 4.6 | 1.2 | 0.5 | 0.3 | 0.1 |
| DOCUMENT_CLASS (pooled) | 2,386 | 3.7 | 0.9 | 0.4 | 0.2 | 0.1 |

Sources of the rates:
- SEC13D (FIRE): 302 FIRE events over 2020-07..2022-11 in KILL_TEST_2020_2022 (2.42 years)
- DILUTION_8K: 1,558 Item 3.02 events over 2021-2022 in US_8K_ITEMS (test 27)
- FORM4: 2,964 scored purchase events over 2021-2022 in US_INSIDER_BUY (test 26)
- FORM4 above USD 20: 1,496 of test 26's events in price band 3
- DOCUMENT_CLASS (pooled): the three parents together

## Reading it

- The published activist-filing drift is one to three percent per event. SEC13D alone cannot answer in under a decade at any edge in that range; the kill test is what can retire it quickly.
- FORM4 answers in about a year if its edge is near the 1% test 26 found, and in months only if the edge is larger than that.
- Pooling (DOCUMENT_CLASS) is the only free lever on the rate; price is the cheapest lever on the spread.
- The per-session statistic the registers use clusters sets by signal session, so with many events a day the number of sessions, not the number of sets, bounds the t; min_sessions in the looks covers that.

Pinned inputs: `research/US_INSIDER_BUY/results_stage1/events_hold20.csv` 7daf3c3997ba, `research/US_INSIDER_BUY/results_stage1/events_hold60.csv` 93b9e1de0e1e.
