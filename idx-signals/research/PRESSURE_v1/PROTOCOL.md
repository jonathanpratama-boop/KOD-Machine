# PRESSURE_v1: does urgent buying (taker-buy pressure) improve KOD's 3-day ranking beyond its own price information?

Written 2026-11-03, before any taker-buy number is downloaded. The one layer of Ace's map left untested by NEIGHBOURS_v1:
trading pressure relative to liquidity (cf. Cont, Kukanov and Stoikov on order-flow imbalance).

## Data
- NEIGHBOURS_v1's rows (same universe, dates, features, forward returns, eligibility), unchanged.
- Binance public archive, spot daily klines (data.binance.vision, monthly files, `<TICKER>USDT`, 1d), fields quote volume and
  taker-buy quote volume, 2020-01 .. 2026-10, for every ticker in those rows. Missing files are counted, not filled.

## New features (day t, known at the close of t)
- tb1: taker-buy share of quote volume on day t, minus 0.5.
- tb5: taker-buy share over days t-4..t.
- tbz: (taker-buy minus taker-sell quote volume over t-2..t) divided by the 20-day median daily quote volume (pressure relative to
  liquidity).
All rank-normalised across eligible coins each day; a coin with no taker data that day gets 0 (neutral).

## Model
**P = model A + tb1, tb5, tbz.** Same target, ridge alpha 10, walk-forward yearly refits, test years 2021-2026, same decision
rule (top 5 every 3rd day, held 3 days, costs 0.4% and 2%).

## Reading (fixed now)
- **Pressure adds information**: P-A daily rank correlation > 0 with the 95% block-bootstrap interval above zero (3-day horizon),
  and P's top 5 beats A's at 0.4% costs in at least 4 of 6 years.
- Otherwise: no incremental value. Profit after eToro costs reported separately.
One counted exploratory test; 2023-2026 already inspected (disclosed).
