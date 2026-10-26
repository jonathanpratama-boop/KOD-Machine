# FLOW_IDX_v1: does foreign flow, the closing queue or block trading lead a large move on the IDX?

Written 2026-10-26, before any flow feature is related to a price move. Counted test 30 in the register
(`research/QUANT_GRADE/trials/`; 29 is LEAD_LADDER_INTL_v1). Paper research only; no order.

## Why

Every earlier test read only the price and volume of a day. LEAD_LADDER_v1 and _INTL_v1 found that volatile and
beaten-down stocks move more, in both directions, and that no price feature gives an early directional warning.
Indonesia is the one market whose archived exchange data (IDX daily summaries, mirrored; 2019-07-29 to 2025-02-21,
delisted names included from 2021-01-22) also records who traded: the daily foreign buy and sell volume, the closing
best-bid and best-offer queue volumes, and the negotiated-market ("non-regular", block) value. No test used them as
signals. The idea: quiet accumulation (foreign net buying, a heavy closing bid queue, block crossings) in a name that
is not yet moving could lead a large up-move, and, in a name that is already "hot" (volatile), could supply the
direction the price features lack. The owner trades Indonesian stocks through Stockbit
(`handoff/decisions/2026-10-26b_keep_IDX_tradable_via_stockbit.md`).

## Data (pinned)

- Prices, episodes, buckets, the void rule: LEAD_LADDER_v1's machinery on `idxsig.e1.Study` for panel
  `panel-20261007T225823Z` (sha256 `9d3a0718…`), exactly as in test 28.
- Flow fields: the raw mirror files of manifest `idx_mirror-20261007T180744Z.jsonl` (the panel's input; every file
  hash-checked), columns foreign_buy, foreign_sell, volume, value, bid_volume, offer_volume, non_regular_value.
  Rows dated after 2023-12-29 are never read. Units: shares (foreign_buy <= volume on every row; checked before this
  protocol, no returns involved). 958 of the panel's 983 tickers have flow data; the rest are Yahoo-era names and carry
  no flow feature.
- Windows: discovery 2021-01-22 .. 2022-12-30; validation 2023-01-02 .. 2023-12-29 (used once, for cells frozen by the
  discovery stage); the IDX holdout 2024-01-02 .. 2025-02-21 is not read.

## Flow features (8; each at session u uses sessions up to u's close only)

Sums and means run over the name's tradeable sessions in the window (NaN elsewhere), with the minimum count stated.

| Feature | Definition | Min sessions |
|---|---|---|
| fnet5 | (sum of foreign_buy - foreign_sell over 5) / (sum of volume over 5) | 4 |
| fnet20 | the same over 20 | 15 |
| fpart20 | (sum of foreign_buy + foreign_sell over 20) / (2 x sum of volume over 20) | 15 |
| bidq1 | bid_volume / (bid_volume + offer_volume) at u's close (NaN if both 0) | 1 |
| bidq5 | mean of bidq1 over 5 | 3 |
| bidx1 | log10((bid_volume at u + 1) / (median volume of the 20 sessions before u + 1)) | 10 |
| blk5 | (sum of non_regular_value over 5) / (sum of value + non_regular_value over 5) | 4 |
| blk20 | the same over 20 | 15 |

Tails as in test 28: top = strictly above the matched pool's 90th percentile at u, bottom = strictly below its 10th.
16 feature-tails.

## Two families

- **IDX** (unconditional): LEAD_LADDER_v1's episodes, void rule and matched pools (price band, liquidity, market cap),
  with the flow features in place of the price features.
- **IDX_HOT** (the two keys): the same, but an event and every pool name must be "hot" at the lead session u: vol20 (E1's
  20-session volatility) at or above the 80th percentile, across the names eligible and not extended at u. The hot
  mask is cross-sectional and causal.

## Episodes, leads, void rule

LEAD_LADDER_v1's four kinds (FAST_UP, FAST_DOWN, SLOW_UP, SLOW_DOWN, +/-30% as defined there), leads 0, 1, 2, 3, 5, 10,
20, the void rule (level more than 1.10 x its prior 20-session median is extended and void) in the primary analysis;
week-clustered bootstrap, 2,000 resamples, seed 20261026.

## Stage 1 (discovery) gates

Gated cells: 2 up kinds x leads 3, 5, 10, 20 x 16 feature-tails x 2 families = 256. Bonferroni, one-sided 0.05/256:
z = 3.55. A cell passes when all hold in the primary (void) analysis:

- G1 lift >= 2.0.
- G2 lower bound at z 3.55 above 1.0.
- G3 direction: lift >= 1.5 x the same family, feature, tail and lead lift for the matching down kind. (Passing G1, G2,
  G4, G5 but not G3 is MOVEMENT_ONLY.)
- G4 lift >= 1.5 in each year (2021, 2022) that has >= 30 scored events.
- G5 at least 100 scored events and a summed expectation of at least 10.
- G6 lift >= 1.5 x the lift of the same cell in the rehearsal (below), because the matched pools exclude names with a
  same-kind move in u..t, which lifts some nulls above 1 (LEAD_LADDER_v1/ERRATA_1.md).

Stage 1 verdict: **NO_FLOW_LEAD** if no cell passes (then foreign flow, closing queues and block trading in daily
summaries do not lead large moves on the IDX; stop this line; the remaining candidate is the broker summary, which
needs the owner's exports); **FLOW_CANDIDATES** otherwise. The passing cells are written to `stage1/frozen.json` and
committed before Stage 2 runs.

## Stage 2 (validation 2023, once, only frozen cells)

For the m frozen cells, on 2023 episodes (same machinery, window 2023-01-02 .. 2023-12-29): V1 lift >= 1.5; V2 lower
bound at z_b = inverse normal CDF of (1 - 0.05/m) above 1.0; V3 lift >= 1.5 x the matching down-kind lift in 2023; V4 at
least 60 scored events and expectation >= 6 (else the cell is NOT_TESTABLE); V5 lift >= 1.5 x the rehearsal lift of the
cell on 2023. Verdict **FLOW_LEAD_VALIDATED** if any frozen cell passes V1 to V5; **NOT_VALIDATED** if none does and at
least one is testable; **NOT_TESTABLE** otherwise.

Consequence of FLOW_LEAD_VALIDATED: the validated cell with the longest lead (ties: highest lift) is written as one
frozen IDX detector and goes to a money test (the harness's execution model for Indonesian stocks, `--void-extended 0.10`,
matched entries, fees at the harness's 0.15% buy and 0.25% sell, which are not Stockbit's verified schedule) as the next
counted test. Nothing enters the paper ledger before that passes.

## Rehearsal, verification, record

Rehearsal first: up episodes replaced by random eligible names on the same sessions (seed 20261026), both families and
both windows; expected: no Stage 1 pass. `verify.py` recomputes the flow features from the raw files with separate code
(per ticker, not the vectorised arrays), then a seeded sample of 200 event rows (episode, lead session, void, hot, pool,
tail counts) and every lift, lower bound, gate and verdict from the per-event tables. `PINS.json` before Stage 1. The
result enters the register whatever it is.

## What this cannot show

That flow predicts profit: separation at a 0.2-0.4% base rate leaves most flags false. That it persists beyond 2023.
That any broker's retail fees and fills match the harness's. Daily closing queues are one snapshot; foreign flow is
reported by the exchange after the day, not in real time.
