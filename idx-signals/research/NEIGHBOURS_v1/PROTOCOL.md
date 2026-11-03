# NEIGHBOURS_v1: do an asset's neighbours improve KOD's picks beyond its own price? (Ace's three-model comparison)

Written 2026-11-03, before any model is fitted or any forward return is computed. Owner + Ace: "neighbours may reveal
opportunity or danger before the asset's own price becomes an obvious mover". SEESAW_v1 (monthly) only rejected that
monthly specification; this tests the short horizon.

## Data and universe
panel_crypto-20261008T003354Z (Binance USDT spot, daily UTC bars, delisted pairs kept), 2020-01-01 .. 2026-10-07.
A coin is eligible on day t if it is not stable/fiat/leveraged (idxsig.global_panel.STABLE, LEVERAGED), has 20-day median quote
volume >= USD 1m and at least 120 days of history. BTC and ETH are eligible. Disclosure: 2023-2026 crypto prices were already
inspected by earlier KOD studies; this is not a clean holdout. Survivorship: pairs Binance removed entirely are missing.

## Timing (no look-ahead)
Features use bars up to the close of day t. Entry at the open of t+1, exit at the close of t+3 (3 days; primary). Sensitivity:
exit at the close of t+1 (1 day) and t+5 (5 days).

## Groups (fixed before the signal)
- Peers (behavioural): each day, the 20 eligible coins whose residual daily returns (return minus BTC's) over t-120..t-1 correlate
  most with the coin's, excluding the coin itself (at least 100 shared days).
- Stations for "next stop" (fixed, reproducible): S1 BTC, S2 ETH, S3 the next 20 coins by 60-day median quote volume, S4 the next
  40, S5 the rest. Membership is set from data up to t-1.

## The three models (nested; same rows, same target)
- **A baseline** (KOD's own information): own return 1, 3, 7, 20 days; volume 5-day / 20-day; distance from 60-day high; 20-day
  volatility; BTC 7-day return; breadth (share of eligible coins above their 50-day SMA).
- **B group context** = A + peer median return 1, 3, 7 days (self excluded); peer participation (share of peers up 3%+ on day t);
  own 7-day return minus peer median 7-day return.
- **C next stop** = B + each station's 1- and 3-day median return, separately for each own-station (station-specific
  coefficients: 5 own stations x 5 stations x 2 horizons).
Features are rank-normalised across coins each day; the target is the coin's 3-day return minus that day's cross-sectional
mean, clipped at the day's 1st/99th percentiles. Ridge regression, alpha = 10, fixed. Walk-forward: refit on 1 January each year
on all earlier days, predict that year. Test years 2021-2026.

## Measures
- Information: daily rank correlation (IC) between each model's prediction and the realised 3-day return; differences B-A and C-B,
  95% interval from a moving-block bootstrap of 20-day blocks.
- Decisions: every 3rd day, buy the top 5 by each model (equal weight), hold 3 days; mean net return per pick at 0.4% round trip
  (Binance-like) and at 2.0% (eToro), beside: random 5 eligible coins, all eligible coins, and "already-strong group" (the 5 coins
  of the station with the best 7-day median return that have the highest own 7-day return).
- Independence: results by year; with the best month removed; the number of distinct months that carry half of any gain.

## Reading (fixed now)
- **Neighbours add information**: B-A IC > 0 with the 95% interval above zero over 2021-2026, and B's top-5 beats A's top-5 at 0.4%
  costs in at least 4 of the 6 test years.
- **Next stop adds information**: the same, for C-B.
- Otherwise: no incremental value at this horizon. Profit after eToro costs is reported separately and is not implied by either.
One counted exploratory test. No rerun with changed settings.
