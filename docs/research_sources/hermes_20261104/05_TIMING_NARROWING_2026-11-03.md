# Timing, narrowed (2026-11-03)

No new test was run. This note re-reads one existing, frozen, minute-resolution result and applies the owner's real costs.

## Source
`idx-signals/research/BINANCE_ANN_1M` on the main branch: 112 Binance futures-launch announcements, 2020-2023, tokens already
trading on Binance spot, 1-minute bars, 10 random liquid coins per event at the same minute. Verdict FAIL, reading
"priced inside the announcement minute". Its own costs were 0.20% per side.

## The stopwatch (mean excess return over the controls, from the close of the minute before the announcement)

| Minutes after the announcement | 0 (the announcement minute) | 1 | 4 | 15 | 60 | 1440 |
|---|---:|---:|---:|---:|---:|---:|
| Excess so far | +3.28% | +3.53% | +3.92% | +4.06% | +3.79% | +4.17% |

The hour before the announcement: -0.35% (no leak). About 80% of the whole move happens inside the announcement minute.

## What a buyer keeps (entry delay d minutes, hold h minutes; mean gross return)

| Entry | Hold 15 min | Hold 1 h | Hold 1 day | Net at Binance-like 0.4% round trip (1 h) | Net at eToro ~2% round trip (1 h) |
|---|---:|---:|---:|---:|---:|
| Within the minute (bot) | +0.69% | +0.38% | +0.30% | -0.02% | about -1.6% |
| After 1 minute | +0.30% | +0.04% | +0.14% | -0.36% | about -2.0% |
| After 5 minutes | +0.07% | -0.27% | -0.31% | -0.67% | about -2.3% |
| After 15 minutes (fast human) | -0.17% | -0.45% | -0.31% | -0.85% | about -2.5% |

eToro charges 1% on each crypto buy and sell plus the spread (etoro.com/trading/fees), so the eToro column subtracts 2.0%.

## Reading
For a public, exactly-timed attention event, the tradable window after the timestamp is under one minute, and even a bot
inside that minute barely breaks even after realistic costs. A human reacting by phone (15 minutes or more) on eToro loses
about 2.5% per trade on average. Faster clocks do not fix this for a manual trader. Timing after the public moment is closed
for this event type; the only timing question left is whether attention can be anticipated before the public moment.
This is one event type (futures launches); Upbit listings were not tested because Upbit's API is behind a bot check from
this environment; the owner's Mac holds Hermes's copy.
