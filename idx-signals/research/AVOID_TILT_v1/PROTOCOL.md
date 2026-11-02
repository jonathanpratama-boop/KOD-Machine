# AVOID_TILT_v1 — can KOD's loser-spotting skill make money long-only? (frozen 2026-11-02, before any outcome)

**Thesis.** KOD reliably spots losers (post-spike decay; dilution) but not winners. A long-only, monthly-rebalanced US
portfolio that holds the tradeable market and simply EXCLUDES KOD-flagged names should beat the same portfolio without
the exclusions, net of costs, with no shorting, leverage or intraday timing.

**Data.** `data/raw/yahoo_us_history/20261030T095328Z` (daily OHLCV + adjusted close, 2019-09..2026-10, ~5,700 tickers,
survivor-only: names delisted since are absent, which removes the worst of the excluded names and so UNDERSTATES the
benefit of excluding them). 8-K items from `research/US_8K_ITEMS/filings8k.csv.gz` (filed 2020-06..2023-09).

**Rebalance.** First trading day of each month, using only data up to the previous close. Hold to the next rebalance.
Monthly return from adjusted close. Equal weight.

**Universe (both arms).** Previous close >= $5; median daily dollar volume over the prior 20 sessions >= $1m; at least
60 sessions of history.

**Arms.** A = all eligible names. B = A minus (1) SPIKE: any daily adjusted-close return >= +30% in the prior 20
sessions; minus (2) DILUTION: an 8-K with Item 3.02 filed in the prior 90 calendar days (only where 8-K data exists,
2020-06..2023-09; elsewhere not flagged).

**Costs.** 0.20% per side on traded weight (turnover from weight changes at each rebalance), both arms.

**Periods.** Discovery: 2020-07..2023-12 (spike + dilution). Holdout (primary): 2024-01..2026-10 (spike only; no 8-K data).
These years were used by other KOD studies for other questions; this portfolio question has never been run on them.

**Pass (primary, holdout).** Mean monthly net return of B minus A > 0 with a one-sided 95% bootstrap lower bound > 0
(resampling months, 5,000 draws), AND B's annualised net return > 0. Otherwise FAIL. Reported beside it: annualised
return, volatility, Sharpe, max drawdown, per-year B-A, share of names excluded, and the excluded names' own next-month
return (the mechanism).
