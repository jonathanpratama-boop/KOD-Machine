# LIQ_REBOUND_v1: independent verification of the one run (2026-10-31)

Two independent auditors with fresh context checked the run in `run/` after it completed. Neither modified a repo
file, and neither read any row dated 2024-01-01 or later. Their scratch work stays outside the repo
(`/tmp/verify_rederive/`, `/tmp/verify_accounting/`). **Verdict of both: CONFIRMED, no discrepancy.**

## 1. Reconstruction from raw data (own code, rebound.py not imported or copied)
- All 90 spot kline zips and all 1,978 open-interest zips match their manifest sha256.
- Signals rebuilt from the protocol text: 212 BTC and 48 ETH discovery signal hours; usable hours 18,087 / 7,275;
  debounced signals 16 BTC + 7 ETH = 23; 18 episodes. These equal FEASIBILITY.json and RESULT.json. The 5% OI
  percentile matches pandas exactly (max abs difference 0.0); sigma within 3.2e-15.
- Trades: the same 23 trades as `run/discovery/trades_A2.csv`, with every field identical (max abs difference 0.0 in
  entry/exit time, price, exit type, notional, units, net, pnl). 20 time exits, 3 stops at the bar low.
- Equity: final 7,552.406224631312, identical to `equity_A2.csv.gz` and RESULT.json. All 20,449 hourly rows match
  (equity, invested, cash). Labelling note: `t` is the bar open; the value is marked at that bar's close.
- Six trades were checked against raw kline rows, including both stops and a month boundary. Each entry is the raw
  open of the bar 1h after the signal; each time exit is the raw open exactly 72h later; each stop is the low of the
  first bar at or below 80% of entry, with every earlier low above that level.
- Look-ahead: 53 signal points were recomputed with all data after the signal time removed. Features and signals
  were identical.
- Open details do not matter: the std convention, the handling of repeated OI timestamps, the filter order and the
  within-hour ordering all leave the 23 trades and the end equity unchanged.

## 2. Accounting audit of the run outputs
- Per-trade cost identities hold in all 10 trade files (A1, A2, A3, S1, S2; discovery and 2023); largest differences:
  net 5.3e-16, pnl 2.0e-12 USDT.
- Cash identity (start + sum of pnl = final cash = final equity), no negative cash, no leverage, no overlapping
  same-coin positions, at most 2 concurrent positions, notional <= 50% of decision equity: all hold.
- Every number RESULT.json reports was recomputed from the CSVs (end equity, returns, drawdown on hourly marks,
  exposure, win rate, trade statistics, CVaR, P&L without the top 3, by coin, by year, episodes, mechanism means,
  placebo quantiles) and matches.
- Gates G0-G6 recomputed under the frozen GATES text: G0 PASS, G1-G6 FAIL. Verdict FAIL confirmed.
- Timing fields: entry = signal + 1h; TIME exits 72h after entry, stops earlier; every signal time is inside its
  declared window.
