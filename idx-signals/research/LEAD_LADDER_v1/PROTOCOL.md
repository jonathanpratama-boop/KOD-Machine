# LEAD_LADDER_v1: how many sessions before a large move does any daily-bar feature separate it?

Written 2026-10-26, before any statistic of this test is computed. Counted test 28 in the register
(`research/QUANT_GRADE/trials/`). The US_8K_ITEMS protocol reserved "test 28" for its Stage 2, which runs only if
Stage 1 passes; Stage 1 failed (counted test 27), so that reservation lapsed and the number is used here.

## Why

Every detector so far was scored from the flag forwards: did a +30% move follow the flag? A flag inside the
move passes that test, so the detectors were validated for detection and failed when traded (E1, E2, E3, E9).
On the session a move began, the flags caught 0 of 4,100 US moves, 1 of 730 crypto moves and 4 of 569 IDX moves.
This test turns the scoring around: it anchors on the move and asks, at each lead k sessions before the move
starts, whether any of the pre-event features that E1 and E2 already compute separates the names about to move
from similar names that are not. A flag on a session that is already moving is void. It is paper research only;
nothing here is an order or a trading rule.

## Data (pinned; no new data)

| Market | Panel manifest | Discovery window | Survivorship | Can confirm? |
|---|---|---|---|---|
| IDX | `panel-20261007T225823Z.json` (E1's) | 2021-01-22 .. 2022-12-30 | complete (TIER_1, delisted names included) | yes |
| CRYPTO | `panel_crypto-20261008T003354Z.json` (E2's) | 2020-07-01 .. 2022-12-31 | Binance USDT pairs incl. delisted | yes |
| US | `panel_us-20261008T004105Z.json` (E2's) | 2020-07-01 .. 2022-12-31 | survivor-only (today's listings) | no: it can fail the test, not confirm it |

The panels are restored from `origin/data-archive` and must match their manifest SHA-256. The study market is
built by `idxsig.e1.Study` with each market's own protocol (E1, E2), which cuts everything after the last
validation session. Only discovery sessions are used. Validation (2023) and the holdouts (IDX 2024-01-02 ..
2025-02-21; US and crypto 2024-01-01 ..) are not read by any statistic.

## Targets (four episode kinds)

Levels are E1's reference chain (cumulative close/previous), so a corporate-action reset is not a move.

- **FAST_UP**: session t where the highest close in t+1..t+5 is at least 1.30 x close t (E1's E30).
- **FAST_DOWN**: the lowest close in t+1..t+5 is at most close t / 1.30 (the log-symmetric fall, -23.1%).
- **SLOW_UP**: the highest close in t+1..t+20 is at least 1.30 x close t, and no single session in t+1..t+20
  closes more than +15% above the previous one (a grind, not a spike).
- **SLOW_DOWN**: the lowest close in t+1..t+20 is at most close t / 1.30, and no single session in t+1..t+20
  falls more than 1/1.15 - 1 = -13.0%.

An episode of a kind starts at t when t qualifies, no session of the same kind qualifies in t-20..t-1, t is
eligible as in E1 (traded, reference > 0, at least 20 earlier sessions present), and t-20 .. t+H (H = 5 or 20)
lie inside the discovery window. The same episodes are used at every lead, so the curve across leads compares
like with like.

## Leads and the void rule

Leads k = 0, 1, 2, 3, 5, 10, 20 sessions. At lead k the features are read at session u = t - k (data through the
close of u only). The event at that lead needs u eligible as above.

**Void rule (primary analysis).** A name is *extended* at u when its level at u is more than 1.10 x the median of
its levels in u-20..u-1 (at least 10 of them present). An extended event at u is void at that lead, and extended
names are not eligible controls. The analysis without the void rule is reported beside it, descriptive only.

## Features

The weak-signal lists of each market's own protocol, unchanged: IDX (E1): continuous ret1, rel1, ret5, ret20,
volr, valr, freqr, rngr, cpos, vol20, dd60, turn, up5, zero20, age, logval20, logmcap; binary ara, brk60, ign.
US and crypto (E2): continuous ret1, rel1, ret5, ret20, volr, valr, rngr, cpos, vol20, dd60, up5, zero20, age,
logval20, gap; binary brk60, ign. Definitions are in `idxsig/e1.py` and each protocol.

## Comparison: matched pools at the lead session

For an event (name n, start t) at lead k, the pool is every other name c at u = t - k that is eligible at u, not
extended at u (primary analysis), has no same-kind qualifying session in u..t, and shares n's buckets at u:
price band, liquidity quintile, market-cap quintile (E1's matching, E1's relaxation order when fewer than 5 names
match). An event with fewer than 5 pool names with a finite feature value is not scored for that feature.

**Tail lift.** For a continuous feature and the top tail: the event counts 1 if its value is strictly above the
pool's 90th percentile; its expectation is the share of the pool strictly above that percentile. Bottom tail:
strictly below the pool's 10th percentile. A binary feature has one tail: the event counts 1 if the feature is 1;
its expectation is the pool's share of 1. Lift = sum of event counts / sum of expectations over the scored events.
The mean within-pool AUC (E1's statistic) is reported beside it.

**Uncertainty.** 2,000 bootstrap resamples of calendar weeks (ISO week of t), the same resample for numerator and
denominator; the standard error of log lift from the bootstrap; one-sided lower bound = exp(log lift - z x se).
Seed 20261026.

## Tests counted, gates and reading rules

Gated cells: leads 3, 5, 10, 20; up kinds (FAST_UP, SLOW_UP); every feature and tail; three markets.
N = 2 kinds x 4 leads x [IDX (17 x 2 + 3) + US (15 x 2 + 2) + CRYPTO (15 x 2 + 2)] = 8 x 101 = 808.
Bonferroni level 0.05 / 808 one-sided: z = 3.84.

A cell (market, up kind, feature, tail, lead) **passes** when all hold, in the primary (void) analysis:

- G1 size: lift >= 2.0.
- G2 significance: lower bound at z = 3.84 above 1.0.
- G3 direction: lift >= 1.5 x the lift of the same feature, tail and lead for the matching down kind
  (FAST_DOWN for FAST_UP, SLOW_DOWN for SLOW_UP). A cell that passes G1, G2, G4 and G5 but fails G3 is recorded as
  **MOVEMENT_ONLY**: it predicts a large move, not its direction.
- G4 stability: lift >= 1.5 in each calendar year of the window that has at least 30 scored events.
- G5 volume: at least 100 scored events and a summed expectation of at least 10.

The **horizon** of a (market, kind, feature, tail) is the largest gated lead at which its cell passes.

Reading rules, fixed now:

- **LEAD_FOUND**: at least one cell passes in IDX or CRYPTO. Consequence: the passing cell with the largest
  horizon (ties: highest lift) is written as one frozen detector, validated on 2023 as counted test 29 under its
  own protocol, with the void rule and a money test against matched entries. Nothing enters the paper ledger before
  that passes.
- **LEAD_US_ONLY**: cells pass only in US. Recorded as a lead on survivor-only data; it needs survivorship-free US
  prices before any validation.
- **NO_DAYS_AHEAD_LEAD**: no cell passes. Consequence: no further daily-bar early-detection detector is built in
  this repository; the next inputs to try are filings and intraday data.

The verdict is the primary analysis's. The unvoided analysis, leads 0 to 2, the down kinds and AUC are descriptive.

## Rehearsal before the run

A placebo: the same machinery with each market's FAST_UP and SLOW_UP events replaced by random eligible
(name, session) pairs, same count and same sessions, seed 20261026. Expected: lifts near 1 and no passing cell. The
rehearsal runs, and the independent verifier must agree with the runner on it, before the real run.

## Run, verification and record

`run.py` computes everything once and writes `results/` (exclusive-create). `verify.py`, written separately,
recomputes every event's pool and tail counts for a fixed random sample of 300 (market, kind, feature, lead, event)
cells from the panels and must match the runner exactly, and recomputes every gated lift from the runner's
per-event table. `PINS.json` records the SHA-256 of this protocol, `protocol.json`, the code and the panels
before the run. The result is entered in the register as a new trial file, whatever it is.

## Catalyst anatomy (descriptive, not gated)

For US FAST_UP and SLOW_UP episodes whose issuer is in the SEC submissions archived for E9
(`data/raw/sec/20261016T185931Z`, issuers with a G2_RET30 signal 2020-07..2023), and for one matched control per
episode drawn from the same covered issuers: the share with any filing dated in the 30 calendar days up to the
lead-3 session, the share whose first filing in the window is on t or t+1, and the share with none. The
difference between episodes and controls is the only number read. Coverage is a selected, volatile population;
the result is a pointer to inputs, not a test.

## What this cannot show

That a feature which separates moves makes money: separation at a 1-2% base rate leaves most flags false. That a
US pass is real: the US panel is survivor-only. That intraday, order-flow, options or news inputs lead: they are
not in the data.
