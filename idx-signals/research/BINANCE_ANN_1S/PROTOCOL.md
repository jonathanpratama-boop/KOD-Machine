# Binance futures-launch announcements in seconds (BINANCE_ANN_1S)

Written 2026-10-21 and committed before any trade-level data for these events is fetched or read. Historical research only:
never prospective performance; no orders; the frozen paper cycle is untouched.

## Why this test, and what it is not
`research/BINANCE_ANN_1M` (registered, counted test 21) found that a token's first USDT-perpetual launch announcement moves
its spot price by about +3.3% **inside the one-minute bar that contains the published time** and by nothing reliable afterwards
(+3.8% at 60 minutes, +4.2% at 24 hours; entering at the close of that bar and holding an hour: +0.5% excess, t 0.91; with a
5-minute delay: -0.2%). Daily and minute bars cannot say whether that jump takes 200 milliseconds or 50 seconds. A trader
who polls Binance's announcement list and sends an order has a reaction time of roughly one to a few seconds at best. This test
measures the reaction in seconds from every trade Binance published, and asks whether any part of the move is left at such a
latency. **It is a follow-up chosen after seeing the minute-level result, on the same events: not an independent sample.** It is
counted as test 22 in the register, with the same hurdle.

## Events (fixed; nothing is re-selected)
The 112 events of `research/BINANCE_ANN_1M/results/events.csv` (valid events of the registered run; their pair, token and
announcement time in ms come from `research/BINANCE_ANN_1M/feasibility/events.csv`). An event is **usable** if its pair has at
least 3 trades in the 60 seconds before T (so the reference price is fresh). Unusable events are counted and dropped.

## Data
Binance's public daily aggregate-trade archives (data.binance.vision, spot/daily/aggTrades, one file per pair and UTC day;
columns: id, price, quantity, first id, last id, time in ms, is-buyer-maker, is-best-match). Every file's URL, size and sha256 is
recorded in `ticks/MANIFEST.json`. For each event and each placebo, the trades in [T-120 s, T+3900 s] are kept. **Placebo**: the
same pair at T minus 24 hours (the same clock time the day before), which carries no announcement.
`is-buyer-maker = true` means the seller was the aggressor (a trade at the bid); `false` means a buyer lifted the ask.

## Definitions
- T = the announcement's release time (ms). **P0** = the price of the last trade strictly before T.
- **Reaction** R(s) = (price of the last trade at or before T + s) / P0 - 1, for s in {-60, -30, -10, -5, -2, -1, 0, 0.25, 0.5, 1,
  2, 3, 5, 10, 20, 30, 60, 120, 300} seconds.
- **Latency L**: the time an order reaches the exchange after T (the feed poll, the decision and the network included).
- **Entry** = the price of the first buyer-initiated trade (a trade at the ask) at or after T + L, within 60 s of it; none = the
  event is unfillable at L and is counted and dropped for that cell. **Exit** = the price of the first seller-initiated trade (a
  trade at the bid) at or after entry time + H, within 120 s of it. Gross return = exit / entry - 1. Because the entry is taken at
  the ask and the exit at the bid, the spread is inside the prices; the fee is added on top.
- **Net** = gross - 0.20% (Binance's 0.10% taker fee per side). Conservative net = gross - 0.40% (0.20% per side). Both are reported.
- Grid: L in {0.5, 1, 2, 5, 10, 30} s x H in {60, 300, 3600} s = 18 cells (counted as 18 variants in the register).

## Statistics
Cluster = the UTC day of T. 10,000 bootstrap resamples of days, seed 20261023 plus the cell's position (0-17) in the grid, L-major
then H; t = mean over the bootstrap standard error. The placebo uses the same clusters and seeds. Winsorised means clip at the 1st
and 99th percentiles.

## Gates (PASS only if all four hold)
- **G1** L = 2 s, H = 300 s: mean net > 0 with bootstrap t >= 3.0 (the project hurdle, counted test 22).
- **G2** L = 5 s, H = 300 s: mean net > 0.
- **G3** L = 2 s, H = 300 s: the winsorised mean net > 0.
- **G4** (method check) the placebo's mean net at L = 2 s, H = 300 s is not significantly positive (bootstrap t < 2.5): the way
  entries and exits are read from trades does not by itself create return where there is no announcement.

## Reported whatever the verdict (descriptive, not gates)
- The mean and median reaction curve for the events (the mean with a day-cluster bootstrap interval, seed 20261123) and for the placebo.
- Speed of the move: among events with R(60) >= 1%, the time from T until the price first reaches half of its own R(60); the
  share of those events at half by T, by 1 s, 2 s, 5 s, 10 s and 30 s.
- The spread before and after T: the last buyer-initiated price minus the last seller-initiated price, relative to the mid, in the
  minute before T and in the first 2 seconds after.
- The clock check: the part of the move that happens before T. **Pre** = P0 / (price of the last trade at or before T - 60 s) - 1;
  **Total** = (price of the last trade at or before T + 60 s) / (price of the last trade at or before T - 60 s) - 1; both averaged
  over the events that have a trade in [T-120 s, T-60 s]. The mean reaction at -60, -30, -10, -5, -2 and -1 s is in the curve.
- The full 18-cell grid for events and placebo, gross, net and conservative net, with counts of unfillable events.

## How the result will be read (fixed now)
- **PASS**: a window of seconds exists that survives fees. Next step: a forward watch of Binance's live announcement list that
  records the actual lag between its timestamp and its appearance, plus the order book at that moment (the microstructure
  side-car pattern); nothing real.
- **FAIL, with Total > 1% and Pre at least a quarter of Total** (a quarter of the move is done before the published time): the
  clock is early or the news leaked; a bot polling the list cannot be first. Recorded as such.
- **FAIL, with R(60) > 1% and R(1 s) at least 80% of R(60)**: about four fifths of the move is done within one second of the
  published time; that is below any retail loop's reaction time. The stage-2 bottleneck is then measured in seconds.
- **FAIL, with R(60) > 1% and R(1 s) below 50% of R(60)**: a window of seconds exists but the net capture is not significant; the
  next measurement is the real cost and the real feed lag.
- **FAIL otherwise** (R(1 s) between 50% and 80% of R(60), or R(60) <= 1%).
If more than one reading applies, the clock reading comes first. No rerun after the result: any change is a new experiment with
its own protocol.

## Limits (stated before the result)
- Trade prices are not quotes: the first buyer-initiated trade is an approximation of what a small marketable buy would have paid;
  a large order, or a thin moment, would pay more. Orders are assumed small and always filled at the first such trade.
- The announcement list's time is when the record says it was published; when the page or the API actually showed it to a poller
  is unknown, so L above is measured from the record, not from visibility.
- The same 112 events, chosen after the minute-level result (see above); one venue and one event type; 2020-2023; nothing here
  addresses whether the owner can trade on Binance at all.
- Competing automated traders exist; this test measures the market's reaction, not whether a retail setup can beat them.
