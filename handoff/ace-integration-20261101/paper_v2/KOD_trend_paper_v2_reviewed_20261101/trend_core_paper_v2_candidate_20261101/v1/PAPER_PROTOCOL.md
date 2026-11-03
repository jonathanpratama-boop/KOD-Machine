# TREND_CORE_PAPER_v1: paper-trading protocol for the FRESH_EYES_v1 trend core (frozen 2026-11-01)

Paper only. No order is placed and no money moves during this protocol. The protocol is pinned by hash before the
first decision is logged; any change is a new, dated protocol.

## Instruments and venue
BTCUSDT and ETHUSDT spot on Binance. Costs assumed for paper fills: 0.10% fee + 0.05% slippage per side. Daily bars
from the Binance Vision archive (monthly files, extended by the daily files published the next UTC day).

## Rule (unchanged from `../backtests/PROTOCOL.md` T1c)
Signal at the close of UTC day t: long if SMA10(close) > SMA40(close), otherwise cash. Position applies from the open of
day t+1 and is held until the signal flips. No other entry or exit.

## Risk layer (outside the rule)
- Volatility targeting: position fraction in each coin = min(1.0, 0.015 / sigma20), where sigma20 is the standard
  deviation of daily log returns over the trailing 20 days, so that each coin's position targets 1.5% daily
  volatility; gross exposure across both coins capped at 1.0 of equity; no leverage.
- Kill criterion (pre-registered): the paper account is stopped and the protocol declared FAILED if equity drawdown
  from its peak reaches 25%, or if the trailing 90-day Sharpe (daily, rf 0) is below zero once 90 days exist.
- Abstention is a valid output: CASH is logged like any other decision.

## Logging
`ledger.jsonl`, append-only, one line per coin per UTC day: signal date, close, SMA10, SMA40, sigma20, target
position fraction, action, data source (monthly archive or daily file), and the sha256 of the previous line (hash
chain). A missed day is logged as MISSED, never back-filled with hindsight.

## Pass bar for considering real capital (fixed now)
After at least 90 consecutive logged days: paper Sharpe above 0.5, maximum drawdown below 25%, every logged action
reproducible from the archived data, and no protocol change. Meeting the bar permits a proposal for a small live
allocation under a new protocol; it does not itself authorise an order.

## What this is not
Not a forecast. Not a confirmation of the backtest. A 90-day paper record cannot confirm a Sharpe-1 strategy (the
standard error of a 90-day Sharpe is about 2); it can only catch gross implementation errors and show the rule runs
as frozen. The owner's decision to fund anything rests on the backtest, the audit and this record together.
