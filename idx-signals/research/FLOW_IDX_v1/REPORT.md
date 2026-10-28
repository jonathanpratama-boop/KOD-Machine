# FLOW_IDX_v1 report (counted test 30)

Recorded 2026-10-26: Stage 1 (discovery 2021-01-22 .. 2022-12-30), commit `abbec93` (pins and rehearsal) plus the
code it names. Verified by `verify_v2.py`: the eight flow features recomputed per ticker with separate code and
equal to the runner's arrays; 200 sampled event rows per family; every lift, lower bound, gate and the verdict
(0 mismatches, `stage1/VERIFY.json`). Rehearsal (random names in place of the up episodes): 0 passing cells in both
windows. 2023 and the holdout were not read; Stage 2 was not run because no cell was frozen.

## Verdict: NO_FLOW_LEAD

0 of 256 gated cells pass. By gate, cells passing: G1 (lift >= 2) 20, G2 (significant) 42, G3 (direction) 10,
G4 (both years) 31, G5 (volume) 232, G6 (beats the placebo) 13. Four cells are movement-only.

## What the accumulation story looked like in the data

Lift = how much more often a name about to start a +30% rise sits in the feature's tail than similar names (1.0 =
chance). Void rule applied; leads 0 to 20 sessions before the rise starts.

| Idea | Feature, tail | Fast rises (unconditional) | Slow rises | Same, hot names, slow rises |
|---|---|---|---|---|
| Foreign net buying | fnet5 top | 0.9 - 1.1 | 1.0 - 1.1 | 1.0 - 1.4 |
| Foreign net buying, 20 days | fnet20 top | 0.9 - 1.1 | 0.9 - 1.3 | 1.1 - 1.7 |
| Heavy closing bid queue | bidq5 top | 1.2 - 1.3 | 1.1 - 1.4 | 1.1 - 1.5 |
| Block (negotiated) trading | blk20 top | 1.1 - 1.2 | 0.9 - 1.1 | 1.1 - 1.5 |

Accumulation by these three measures does not lead large rises on the IDX: lifts sit between 0.8 and 1.5 at every
lead, and the 20-day foreign net buying even runs below 1 before falls.

## The only large lifts are the absence of block trading, and they are movement

The cells with lift above 2 are all "block share in the bottom tail" (blk5, blk20; fast rises, leads 3 to 20): 2.1 to
4.0 times chance, with the matching falls at 1.8 to 2.8. Names with no negotiated-market trading are mostly
small, thin stocks, which move more in both directions: the same movement-not-direction result as tests 28 and 29.
The block-share and participation cells that passed G1 and G2 failed direction (G3), the placebo (G6) or volume (G5).

## The closest thing to a directional hint (not a result)

In hot names (top-fifth volatility), high foreign participation (fpart20 top: foreign buying plus selling as a share of
volume over 20 sessions) before slow rises: lift 1.87 at lead 5 (lower bound 1.11) and 1.85 at lead 3, against 1.02 and
1.13 before slow falls, stable across 2021 and 2022, and 2.1 times its placebo. It fails the size bar G1 (2.0) and
sits among 256 cells. By the pre-registered rule it is nothing. Chosen after seeing the data, it could only be
tested as a new counted test on fresh data (2023, one cell); on 170 events and an expected 23 it is thin.

## Consequence (the reading rule)

NO_FLOW_LEAD: foreign flow, the closing bid and offer queues and negotiated-market trading, as read from the exchange's
daily summaries, do not lead large moves on the IDX. This line stops. What remains untried in Indonesia is the broker
summary (which broker accumulates), which the daily summaries do not contain and which needs the owner's own exports.

## Limits

Daily snapshots only: the closing queue is one moment and foreign flow is reported after the day. Survivor-complete from
2021-01-22. Fees and fills of Stockbit are not modelled. Separation, not profit.
