# FRESH_EYES_v1: pre-registered crypto edge tests (frozen before any return is computed)

Written 2026-11-01 (UTC) by the cloud session, on the owner's instruction of the same day to take a fresh, wider
look at the machine, to include Binance spot and USDT-margined perpetual futures, and to backtest the findings. The
owner authorised the session to proceed without approval on individual steps. Simulation only: no order is placed,
no credentials are used, no money moves.

## Why these tests and not another moonshot detector

Forty-odd counted KOD tests since 2026-10-07 have asked one class of question (can a +30% repricing be detected and
bought in time, spot-long, 1 to 5 sessions) and all have failed. The literature review filed alongside this protocol
(`../research/02_CRYPTO_EDGE_EVIDENCE.md`) says the crypto edges with credible, repeated, cost-aware evidence are a
different class: slow trend following on majors (drawdown avoidance), funding carry (now compressed), short-horizon
mean reversion after forced liquidation, and cross-sectional momentum on perpetuals. None of these has been tested
by the lab. These tests ask whether any of them survives Binance retail costs on Binance's own data, with every rule
and parameter taken from the literature and fixed here, before any return is read.

## Data (all from data.binance.vision bulk archive; sha256 manifests in `manifests/`)

- Spot 1d klines: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, DOGEUSDT, ADAUSDT, AVAXUSDT, LINKUSDT, LTCUSDT, from listing.
- USDT-margined perpetual (UM) 1d klines: every symbol ending USDT in the archive's listing, including delisted
  symbols, from 2019-09. Leveraged tokens (UP/DOWN/BULL/BEAR) excluded.
- UM funding rates: every USDT symbol, from 2019-09.
- UM 1h klines and spot 1h klines: the ten majors above, from 2019-09.

Point-in-time universe for cross-sectional tests: a symbol is eligible on a rebalance date only if it has at least
90 daily bars before that date and its median dollar volume over the prior 30 days is at least USD 5 million. Delisted
symbols stay in the panel until their last bar; a position in a symbol that stops trading is closed at its last close
(this understates the loss on delisting; it is disclosed).

## Periods

- Development: 2019-09-01 to 2022-12-31 (spot trend on BTC/ETH: from 2017-08-17).
- Validation: 2023-01-01 to 2026-10-31.

The lab's sealed crypto holdout (2024-01-01 onward) was recorded as largely spent by earlier experiments
(`handoff/decisions/2026-10-31_holdout_breach_by_research_agent.md`). These tests do not tune on any period: every
parameter below is fixed from the literature now. Both periods are reported for every variant; no variant is dropped
or altered after results. The validation period is therefore a genuine out-of-time check for these rules even though
the rows have been seen by the lab before.

## Costs

- Spot: 0.10% fee + 0.05% slippage per side (0.30% round trip).
- Perpetuals: 0.05% fee + 0.05% slippage per side (0.20% round trip), plus realised funding paid or received at
  each 8-hour funding timestamp while a position is open (long pays positive funding; short receives it).
- Sensitivity: eToro-style 1.00% per side on spot variants, reported alongside.
- Signals use data up to the close of bar t; execution at the open of bar t+1 (daily tests) or the open of the
  next hour (hourly test). No fill inside the signal bar.

## Tests and pass rules (fixed now)

### T1. Trend following, BTC and ETH spot, long-flat, daily
- T1a Donchian channel: enter long when close > highest high of the prior 20 days; exit to cash when close <
  lowest low of the prior 10 days (channel breakout, Hudson & Urquhart's best class; Quantpedia's MAX rule).
- T1b Time-series momentum: long when the trailing 28-day return > 0, otherwise cash; re-evaluated every 5 days
  (Han, Kang & Ryu lookback/hold, simplified to the sign of the lookback return).
- T1c Moving-average crossover: long when SMA10 > SMA40, otherwise cash (Rozario et al.).
- T1d Long-run filter: long when close > SMA200, otherwise cash.
- Benchmark: buy-and-hold on the same bars.
- Statistics: CAGR, annualised volatility, Sharpe (daily, rf = 0), maximum drawdown, trades per year, net return by
  calendar year, all net of Binance costs; eToro-cost sensitivity.
- PASS: net Sharpe above buy-and-hold Sharpe in both periods, and maximum drawdown lower than buy-and-hold in both.
- WEAK: passes in one period only. FAIL otherwise.

### T2. Funding carry and funding as a signal, BTC and ETH perpetuals
- Realised funding, annualised, by calendar year; share of 8-hour periods with negative funding.
- Carry (long spot, short perp, delta-neutral): annualised funding received minus one round trip on each leg per
  year (0.30% + 0.20%), by year. No basis P&L is modelled (perpetual basis has no expiry convergence; disclosed).
- Contrarian signal (report only, no pass rule because the sample is small): when the trailing 30-day mean funding
  is negative on a day and was non-negative the day before, the forward 90-day BTC return, listed event by event,
  against the unconditional 90-day return distribution.
- PASS for carry: annualised net carry above 8% in both periods (a bar set so that it beats a stablecoin lending
  rate with a margin for basis and liquidation risk). Otherwise FAIL.

### T3. Cross-sectional momentum, UM perpetuals, weekly
- Rebalance each Monday at the open on signals computed at Sunday's close. Signal: 14-day return (Han, Kang & Ryu).
- T3a long top decile, short bottom decile, equal weight, 7-day hold, gross exposure 100% each side.
- T3b long top decile only, 100% of capital, against the equal-weight eligible universe as benchmark.
- Costs: perpetual costs on every leg traded; funding accrued daily from the daily funding sum.
- PASS: net Sharpe above 1.0 in both periods and net return positive in at least 70% of calendar years.

### T4. Short-horizon mean reversion after extreme moves, UM perpetuals (ten majors), hourly
- z = (4-hour log return) / (standard deviation of 4-hour log returns over the trailing 30 days, computed on
  non-overlapping 4-hour windows ending at the signal hour). Signal at the close of hour t.
- T4a: if z <= -3, long at the open of hour t+1, hold 4 hours, exit at the open of hour t+5. If z >= +3, mirror short.
- T4b: the same at |z| >= 2.
- Taker costs both sides (0.20% round trip); funding if a timestamp falls inside the hold.
- Statistics: trades, mean net return per trade, t-statistic (trade returns treated as independent; overlapping
  signals in the same symbol are skipped while a position is open), win rate, by period and by side.
- PASS: mean net return per trade positive with t >= 3 in both periods, on the same side.

### T5. Exit logic on T1a (BTC and ETH spot)
Holding the T1a entry fixed, compare four exits: (i) the 10-day channel exit; (ii) a trailing stop at 2 x ATR(20)
below the highest close since entry; (iii) a fixed stop 5% below entry with the channel exit otherwise; (iv) a
10-day time exit. Report the same statistics as T1. No pass rule; this answers the owner's question about whether a
trailing stop is the best exit.

### T6. Growth arithmetic (no market data needed beyond T1 results)
Monte Carlo (20,000 paths, 252 trading days) of daily returns with annualised Sharpe in {0.5, 1.0, 1.5, 2.0} and
volatility 20% (unlevered), at leverage 1x to 5x, with daily rebalancing: probability of reaching 10x starting
capital within one year, probability of a 50% drawdown first, and median terminal wealth. Repeated with bootstrapped
daily returns of any T1 variant that PASSES (block bootstrap, 20-day blocks). This states what USD 1,000 to
USD 10,000 in a short period requires, in numbers.

## Multiplicity and what will not happen

Twelve strategy variants are tested (T1a-d x 2 coins, T3a-b, T4a-b) plus descriptive T2, T5, T6. Results are
reported for every variant. No parameter, window, cost, universe rule or pass rule changes after any return is read.
A follow-up test, if any, is a new protocol with a new date. A PASS here is evidence from a single frozen test on
historical data and is not a forecast; a paper-trading stage would be required before any real order.

Protocol sha256 (of this file, computed and committed before the run): see `PINS.json`.
