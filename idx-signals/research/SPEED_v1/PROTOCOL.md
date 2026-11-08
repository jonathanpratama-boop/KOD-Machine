# SPEED_v1: does entering 1 minute after a crypto ignition signal, instead of 5, 30 or 240 minutes, make it profitable?

Written 2026-11-08 by Claude at the owner's request ("Go"), before any minute-level outcome was computed. Paper research
only; changes no running experiment. Purpose: answer the cloud study's (R2) speed question from history in hours instead
of waiting for live events, so the owner can decide quickly whether crypto spike buying is worth continuing.

## Disclosure of what is already known
Hourly outcomes of these same alerts were seen in BREADTH_v1 (entry at the next-hour open, 24h hold, 0.6% cost: mean
-2.7% for 2020-2022 and -3.3% for 2023-2026). Nothing at minute resolution has been looked at.

## Events
Hermes's ignition alerts as reproduced in `../HERMES_NOV3_REPRO_v1` (status OK): 3h return >= +10%, 3h quote volume >= 5x
the 7-day hourly mean, prior 7-day run <= +30%, that mean >= $20,000, 72h cooldown per coin. Binance spot USDT pairs.
**Sample:** 1,000 drawn at random from 2020-2022 and 1,000 from 2023-01-01..2026-10, seed 20261108, drawn before any
minute data is downloaded. The sample list is written to `sample.json` and stamped with this protocol.

## Timing
Signal time S = the close of the trigger hour (the moment the hourly signal can first be known).
Arms: entry at S + 1, S + 5, S + 30 and S + 240 minutes, at the open of that one-minute bar. If that bar is missing (no
trades), the next bar within 5 minutes is used; otherwise the arm is unavailable for that event. Reference arm (reported
only): S + 0.
**Exit:** one common exit for all arms, the close of the last one-minute bar ending at or before S + 24h (searched back up to
30 minutes), as in R2. So later arms hold for less time.
Data: Binance public daily one-minute kline archives (data.binance.vision), which include delisted coins.

## Costs
Primary: R2's fixed 2.0 percentage points per round trip. Also reported: 0.6 (0.3% per side), which flatters the strategy.
Kline prices ignore the bid-ask spread, so all results here are somewhat better than live trading would get.

## Decision rules (fixed now)
Pooled over both periods, events with that arm available. 95% intervals by bootstrap over whole trigger days (UTC dates),
10,000 resamples, seed 20261108.
- **PROFITABLE:** the 1-minute arm's mean net return at 2.0 pts cost has its 95% lower bound above zero. Then speed is
  worth pursuing live.
- **FIRM NO:** the 1-minute arm's mean net return at 0.6 pts cost has its 95% upper bound below zero (it loses even with
  cheap costs and no spread).
- Otherwise: **NOT PROVEN** (no case for adding anything; let the live run finish unchanged).
- Speed effect (reported, same bootstrap): paired difference 1-min minus 30-min and 1-min minus 240-min.
- Also reported: medians; means without the top and bottom 1%; each period separately; the share of events where each arm
  was available; how much of the move had already happened by the 1-minute entry.

## Known weaknesses
Historical prices, not live quotes. No order-book depth or slippage. Events overlap in busy periods (handled by day-level
resampling). A 24h common exit gives the 240-min arm only 20h.
