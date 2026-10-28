# LEAD_LADDER_v1 report (counted test 28)

Recorded run 2026-10-26, commit `63eeb95` (clean), protocol `2e7590b` pushed before any statistic. Verified by
`verify_v2.py`: 300 sampled event rows recomputed from the panels and all 808 gated cells recomputed from the
per-event tables, 0 mismatches (`results/VERIFY.json`). Discovery years only; 2023 and the holdouts unread.

## Verdict: LEAD_FOUND, by the pre-registered rule, and weak

6 of 808 gated cells pass all five gates. None is a timing signal: each feature's lift is nearly flat from lead 20
to lead 3, so it describes a standing condition of the name, not something building up before the move.

| Market | Kind | Feature, tail | Leads passing | Lift (lower bound) | Lift for the matching falls |
|---|---|---|---|---|---|
| IDX | SLOW_UP | youngest listings (age, bottom 10%) | 3, 5, 10 | 2.01-2.12 (1.44-1.50) | 1.31-1.42 |
| IDX | SLOW_UP | fewest up-days in the last 5 (up5, bottom) | 5 | 2.21 (1.40) | 1.34 |
| CRYPTO | FAST_UP | worst 20-session return (ret20, bottom) | 3 | 2.11 (1.63) | 1.21 |
| US | FAST_UP | worst 20-session return (ret20, bottom) | 3 | 3.17 (2.83) | 2.09 (survivor-only data) |

Lift is the rate at which upcoming episodes fall in the feature's tail, divided by the rate for matched names on the
same session. Base rates of an episode start per eligible, non-extended ticker-day: IDX FAST_UP 0.37%, SLOW_UP 0.21%;
CRYPTO 1.08% and 0.84%; US 0.26% and 0.36%. At a lift near 2, more than 97 of 100 flagged name-days are followed by
no episode.

Lift by lead for the passing features (void analysis):

| Cell | 0 | 1 | 2 | 3 | 5 | 10 | 20 |
|---|---|---|---|---|---|---|---|
| IDX SLOW_UP age bottom, up | 1.93 | 2.01 | 1.95 | 2.01 | 2.12 | 2.10 | 1.83 |
| same, down | 1.46 | 1.37 | 1.34 | 1.31 | 1.42 | 1.33 | 1.45 |
| CRYPTO FAST_UP ret20 bottom, up | 2.48 | 2.37 | 2.14 | 2.11 | 1.86 | 1.69 | 1.49 |
| same, down | 1.13 | 1.15 | 1.24 | 1.21 | 1.30 | 1.57 | 1.73 |
| US FAST_UP ret20 bottom, up | 3.73 | 3.37 | 3.27 | 3.17 | 3.01 | 2.88 | 2.91 |
| same, down | 1.69 | 1.94 | 1.96 | 2.09 | 2.19 | 2.46 | 2.62 |

The crypto cell is the only one whose up-lift grows as the move approaches and stays clearly above its down-lift,
and only out to lead 3: coins far down over 20 sessions rebound more often than similar coins in the next few days.

## Movement, not direction

64 cells pass size, significance, stability and volume but fail direction (MOVEMENT_ONLY): high 20-session
volatility, deep drawdown from the 60-session high and closes near the day's low separate upcoming large moves at
every lead, US up to 3.8x and IDX up to 2.8x, but they separate upcoming large falls just as much or more. They
predict that a name will move a lot, not which way. The placebo produced two such cells for crypto listing age (tied,
censored ages), so crypto age cells are not read.

## Catalyst anatomy (descriptive)

US episodes from the 1,225 issuers with archived SEC submissions (E9's), against one matched control each from the
same issuers. A filing in the 30 days up to the lead-3 session: FAST_UP 82.6% of episodes vs 82.1% of controls
(difference +0.5 points, about -1.2 to +2.2); SLOW_UP 83.3% vs 84.1% (-0.9, about -2.7 to +1.0). Offering filings
(S-1, S-3, 424B): 14.4% vs 11.5% for FAST_UP, 12.2% vs 11.3% for SLOW_UP. Having filed something is not a tell: nearly
every issuer in this population files in any 30-day window. Which filing, and what it says, is not measured here.

## What it means

The ladder confirms the late-detection diagnosis. Daily-bar features carry almost no timing information before a
move: what separates movers is volatility and drawdown, and those predict size in both directions. The few
directional cells are states (a young listing, a deep fall) with lifts near 2 on base rates under 1.1%.

## Consequence (pre-registered)

LEAD_FOUND: the passing cell with the largest horizon in a confirming market is IDX SLOW_UP, youngest listings
(age in the bottom 10% of matched names) at lead 10. It is to be written as one frozen detector and validated on 2023
as counted test 29, with the void rule and a money test against matched entries; nothing enters the paper ledger
before that passes. Two facts for that decision: eToro lists no IDX stocks, and 2021-22 was an IDX listing wave, so
the effect may be era-specific. The crypto cell (ret20 bottom, lead 3), tradable on eToro at 1% a side, is not the
rule's pick.

## Limits

Separation is not profit. US data are survivor-only. Leads count from the earliest session from which the move
completes within its horizon, so the first up-session can be up to 4 (FAST) or 19 (SLOW) sessions after t: a lead of
k means at least k + 1 sessions before the move's first up-session. Intraday, order-flow, options and news inputs are
not in the data.
