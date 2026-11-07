# BREADTH_v1: does a jump in the number of trades, beyond the jump in dollar volume, predict better spike outcomes?

Written 2026-11-07 (WIB) by Claude at the owner's request ("Run it"), before any historical result was looked at.
Exploratory; paper only. It changes no running experiment. Idea source: one event, ONEUSDT at 2026-11-06 10:00Z (R2),
where trades over the trigger's 3 hours rose roughly 65x against about 30x for dollar volume, and the coin went on to
+50% in 24h. One event cannot support a rule; this test asks whether the pattern holds across history.

## Events
Hermes's ignition alerts exactly as reproduced and validated in `../HERMES_NOV3_REPRO_v1` (lib.detect, lib.events_and_controls,
status OK): 3h close return >= +10%, 3h quote volume >= 5x the mean hourly volume of hours t-170..t-3, prior 7-day run <= +30%,
that mean >= $20,000, 72h cooldown per coin. Two independent periods: **disc** (triggers 2020-2022, 5,267 alerts) and
**hold** (triggers 2023-01-01..2026-10, about 6,971 alerts). Binance spot USDT pairs, hourly.

## Breadth (uses only hours up to and including the trigger hour t)
N = Binance's hourly number of trades (column 9 of the public kline files).
- trade multiple = sum of N over hours t-2..t / (3 x mean hourly N over hours t-170..t-3), needing >= 150 of 168 hours.
- dollar multiple = the detector's own volume multiple (same windows, quote volume).
- **B = trade multiple / dollar multiple.** B > 1 means the average trade got smaller (more, smaller trades).
- **BROAD = B >= 2.0.** The threshold was stated in chat before this test (from ONE, B roughly 2) and is not tuned.

## Outcomes (entry = open of hour t+1, as Hermes; cost 0.3% per side)
- **Primary:** net 24h return = close of hour t+24 / open of hour t+1 - 1 - 0.006.
- Secondary (reported only): reached +30% within 24h (any hourly high t+1..t+24 >= 1.3 x entry); net 72h return.
Alerts without a valid B or without the needed prices are dropped and counted.

## Test (fixed now)
- Difference in mean net 24h return, BROAD minus the rest, per period.
- 95% interval by bootstrap resampling whole trigger days (UTC dates), 10,000 resamples, seed 20261107.
- **Pass = the lower end of the interval is above zero in disc AND in hold.** Anything else = not passed, and the idea
  is dropped.
- Reported only: medians; means with the top and bottom 1% of returns removed; the +30% hit rate; the difference within
  thirds of baseline liquidity (so a small-coin effect is not mistaken for breadth); B quintiles; ONE's own B from the
  live kline data.

## Known weaknesses
Bots that split orders look the same as many new buyers. Hourly trade counts are coarse. Overlapping events on busy days
are handled by day-level resampling, not removed. A pass would justify a live, pre-registered check, not a trading rule.
