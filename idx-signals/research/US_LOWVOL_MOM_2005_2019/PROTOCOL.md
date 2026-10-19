# US low-volatility and momentum, 2005-2019 (independent period)

Written 2026-10-18 and committed before any 2005-2019 data is downloaded and before any return from it is
computed. Historical research only: never prospective performance; no order is placed.

## Why this test
An exploratory pass over 2020-2022 US data (23 monthly rebalances, already-used data, nothing frozen) saw
(a) the calmest 20% of liquid stocks beat the wildest 20% by about 2.2%/month (t = 1.4) and (b) 12-1 month momentum
flip sign between 2021 and 2022. Two years is one boom and one bust, so neither can be judged. 2005-2019 daily data
has never been used by this project, is separate from the sealed 2024+ period, and spans the 2008-09 crash and
the long bull market. This is the first independent test of those two ideas; 2020-2022 is already seen and
cannot confirm anything.

## Hypotheses (fixed now)
Each month-end t: rank the eligible stocks on a signal into quintiles (Q1 lowest ... Q5 highest signal), hold each
quintile equal-weighted to the next month-end.
- **H1 low volatility.** Signal = minus the standard deviation of daily log returns over the 60 sessions to t
  (Q5 = calmest). PASS if mean(Q5 - Q1) > 0.
- **H2 momentum.** Signal = total return from t-252 to t-21 sessions (12-1 months; Q5 = strongest). PASS if
  mean(Q5 - Q1) > 0.
- **H3 avoid the wildest.** Q1 of the H1 ranking (wildest 20%) mean return is below the eligible-universe mean:
  PASS if mean(universe - Q1) > 0.

Gate for each hypothesis (all must hold): the mean monthly difference is > 0; its t-statistic (mean / (sd / sqrt(months)))
is at least 2.4 (a Bonferroni-style bar for three two-sided tests); and the difference is positive in at least
10 of the 15 calendar years 2005-2019. A hypothesis that misses any condition FAILS. No hypothesis is changed after
the result.

## Data and rules (fixed now)
- Source: Yahoo Finance daily chart API, 2004-01-01 to 2019-12-31, for the tickers requested in the 2026-10-08 US
  pull (today's Nasdaq Trader listing). Response bytes are hashed in a manifest; the raw responses are stored
  gzipped under data/raw/yahoo_us_2005/.
- Returns use adjusted close (splits and dividends). Dollar volume = close x volume (invariant to splits).
- Eligible at t: at least 252 sessions of history, finite signals, and median 60-session dollar volume >= USD 2 million.
  No price floor (as-traded prices are not reconstructed for this period), so low-priced stocks can be present and
  fall into the wild quintile.
- Formation: the last session of each calendar month from 2005-01 to 2019-11. Entry at the close of the next session,
  exit at the close of the next month-end (so the formation signal is one full session old at entry).
- Each stock's holding-period return is clipped to [-90%, +200%]. Months with fewer than 300 eligible stocks are
  skipped and counted.
- Costs: the statistical gates use gross returns. A long-only reading is reported separately: Q5 minus the universe
  mean minus 0.30%/month (0.15% per side on a full monthly turnover).

## Known biases (stated before the result)
- **Survivor-only universe.** Only stocks listed in October 2026 are present; stocks that went bust or were bought out
  before then are missing. This flatters every quintile, most in the volatile and recent-loser groups, which
  tends to shrink H1 and H2 spreads, so a pass is not an artifact of it in that direction but the true effect cannot be
  recovered from this data.
- No as-traded price or listing-date information: a stock appears only once Yahoo has bars for it.
- 2005-2019 includes unusually low interest rates; this is one era.

## Reading the result (fixed now)
- All pass: worth a pre-registered forward paper test and a closer look at implementation. Still a few percent a year
  at best; not a route to quick large gains.
- H3 passes, H1 and H2 fail: the useful finding is "avoid the wildest stocks", a filter, not a strategy.
- None pass: these textbook effects are not distinguishable from noise in this survivor-only data; close the angle.
