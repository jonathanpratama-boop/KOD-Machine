# E8 feasibility check: declared selection rule (committed before the check runs)

The check counts signals and data defects. It computes **no forward return, no high or low after a
decision, and no outcome of any kind**. The only use of bars after a decision hour is a presence
count (is the bar there), for missing-data accounting. Variance for the minimum-detectable-effect
calculation comes from trailing volatility only.

## Data and period

- Manifest `data/manifests/binance_1h-20261015T182940Z.jsonl` (Binance spot 1h klines, USDT pairs,
  delisted symbols included, stablecoins and leveraged tokens excluded at collection).
- Months 2020-04 to 2022-12 only; 2023 and later are never opened. Decision hours run from
  2020-07-01 00:00 UTC to the last hour whose 72-hour holding window ends by 2022-12-31 23:00 UTC.

## Definitions (bar t = the hour opening at t; everything below uses bars up to and including t)

- **Hourly residual return**: log(close_t / close_{t-1}) minus the median of that quantity over
  eligible coins with a valid return in bar t.
- **R24(t)** = close_t / close_{t-24} - 1; **residual R24** = R24 minus its median over eligible coins.
- **Eligible coin at t**: at least 60 complete UTC days before t's day; median daily quote volume of
  the 30 complete days before t's day at least $1,000,000; all 24 bars t-23..t present; no bar with
  taker volume above total volume or a non-positive close in the 37 days before t; no gap longer than
  7 days in the 60 days before t (a relisting guard: a symbol that disappears and returns may be a
  different asset).
- **Leader trigger** for coin L at t: L eligible; R24_L(t) >= +25%; residual R24_L(t) >= +20 points;
  quote volume of bars t-23..t at least 3 x L's 30-day median daily quote volume; and no trigger
  for L in t-72..t-1.
- **Candidate peers**: eligible coins other than L, without a leader trigger in t-72..t, with
  residual R24 <= +5 points (not yet moved).
- **Link**: Pearson correlation of hourly residual returns between L and the candidate over the
  720 bars t-743..t-24 (the 30 days ending where L's 24-hour move window begins), using bars where
  both are valid; at least 600 such bars required.
- **Peers of L at t**: the 3 candidates with the highest link, each with link >= 0.20.
- **Peer event**: (peer P, hour t). If several leaders name P in the same hour it is one event.
  A coin cannot start a new peer event within 72 hours of its previous one.
- **Planned entry**: open of bar t+1. **Holding window**: bars t+1..t+72.

## What the check reports

1. Timestamp checks: open-time unit, hour alignment, duplicate and non-monotonic bars.
2. Identity checks: symbols ending in USDT, none in the stablecoin/leveraged lists, gaps longer than
   7 days (count, symbols), and symbols whose history restarts after such a gap.
3. Missing data: share of missing hours; peer events whose entry bar or any holding bar is absent.
4. Counts: eligible coins per hour, leader triggers, peer events, distinct peer coins, distinct
   ISO weeks, events per calendar year, link distribution of selected peers, leaders per event.
5. Minimum detectable effect: 72-hour sigma from trailing 30-day hourly volatility x sqrt(72),
   effective sample from a week-cluster design effect computed on event counts per week, for 80%
   power at one-sided alpha 0.025.

## GO / NO-GO (fixed now)

**GO** if all hold: at least 600 peer events with an entry bar; at least 80 distinct weeks; at least
100 distinct peer coins; median eligible coins per decision hour at least 80; timestamp and identity
defects affect under 1% of eligible coin-hours; under 5% of peer events miss any holding bar.
Otherwise **NO-GO**, with the failing condition named. A NO-GO stops E8 at feasibility; the rule
is not loosened afterwards.

Every threshold above (25%, 20 points, 3x, 5 points, 0.20, top 3, 72 hours, $1M) is fixed here on
economic grounds before the check, and the eventual protocol uses the same values.
