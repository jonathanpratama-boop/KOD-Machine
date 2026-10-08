# Run 20261008T115656Z_MOONSHOT_E2_US_D1_v1

Rule: **MOONSHOT_E2_US_D1 v1** (DETECTOR), holding 5 sessions
Rule SHA-256: `c21126d8ba9db77b06c186401220850b36c4e1b539d77d4f9da4dcc571e6753f`
Code: `5fe491bb0db02ea6cab116513f139253578f7ada`
Panel: `8d3b7ce4be56d40b375ebac78b45be13910cbea492c29e456a417a6ae000cb4b`
Window: 2023-01-03 .. 2023-12-29 (250 sessions, 4878 tickers, 0 stop trading inside the window)

> Experiment E2 detector: the single rule from FAMILY selected on the market's discovery period defined in research/E2/protocol.json, by the rule pre-registered there. Signal at the close of session d when that rule holds; hold 5 sessions. Market: US. Selected: G2_RET30.

## Result

| | Rule | Matched random (primary) | Same-session random |
|---|---:|---:|---:|
| Signals | 876 (rate 0.1% of evaluable ticker-sessions) | — | — |
| Attempted (after overlap skip) | 794 | 200 draws × 794 | 200 draws × 794 |
| Filled | 553 (69.6%) | 74.6% | 91.0% |
| Scored trades | 536 | 114192 | 139934 |
| Hit rate (net return > 0) | 42.5% | 42.6% (95% of draws 38.7% .. 46.4%) | 48.2% (95% of draws 44.2% .. 51.2%) |
| Average net return | -0.97% | -0.75% (95% of draws -1.96% .. +0.59%) | +0.08% (95% of draws -0.52% .. +0.90%) |
| Median net return | -4.27% | -1.70% | -0.19% |

Average return vs matched random: -0.22% (rule at percentile 38.0 of draws, one-sided p = 0.622).
Hit rate vs matched random: -0.02% (rule at percentile 52.0 of draws, one-sided p = 0.483).
Average return vs same-session random: -1.05% (rule at percentile 0.0 of draws, one-sided p = 1.000).
Hit rate vs same-session random: -5.65% (rule at percentile 0.5 of draws, one-sided p = 0.995).

Matched controls found at: price_band+liquidity+market_cap+volatility+momentum+drawdown+listing_age 619, price_band+liquidity+market_cap+volatility+momentum+drawdown 47, price_band+liquidity+market_cap+volatility+momentum 107, price_band+liquidity+market_cap+volatility 9, price_band 12

Status counts (rule): EXITED 536, INCOMPLETE 17, SKIP_NO_ENTRY_SESSION 4, SKIP_NOT_TRADED 27, SKIP_LIQUIDITY 210

Status counts (matched random, pooled): EXITED 114192, INCOMPLETE 4303, SKIP_NO_ENTRY_SESSION 800, SKIP_NOT_TRADED 1105, SKIP_LIQUIDITY 38400

## By signal year

| Year | Attempts | Scored | Hit rate | Avg net | Matched hit rate | Matched avg net | Same-session avg net |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2023 | 794 | 536 | 42.5% | -0.97% | 42.6% | -0.75% | +0.08% |

## Data quality

Sessions by tier: US_SURVIVOR 250 (panel format panel-global-v2-units)

- US_SURVIVOR 2020-01-02 .. 2023-12-29: yahoo, survivorship survivor-only: the universe is the Nasdaq Trader listing snapshot of 2026-10-08; names delisted earlier are absent, corporate actions from split-adjusted by the source; as-traded units via unit_factor

Known limitations:

- survivor-only: the universe is the Nasdaq Trader listing snapshot of 2026-10-08; names delisted earlier are absent
- prices are split-adjusted by the source, not dividend-adjusted; unit_factor restores as-traded levels from the provider's split records (convention checked against FMP and SEC: research/E2/repair)
- daily bars only: no intraday path, no halts (US LULD) or order-book depth
- costs are assumed per price tier (profiles.py), not measured spreads

## Matched controls

Controls v2; full match (every feature) for 78.0% of attempts; pool minimum 5.

| Priority | Feature | Known for signalled name | Matched on | Availability |
|---:|---|---:|---:|---|
| 1 | price_band: close in <$1 / $1-5 / $5-20 / >$20 | 100.0% | 100.0% | every tier |
| 2 | liquidity: quintile of 20-session median traded value | 98.0% | 98.5% | every tier |
| 3 | market_cap: quintile of close x IDX listed shares | 0.0% | 98.5% | TIER_1, TIER_2 (no share counts after the mirror ends) |
| 4 | volatility: tercile of 20-session std of daily log returns | 98.0% | 98.5% | every tier |
| 5 | momentum: tercile of 20-session cumulative log return | 98.0% | 97.4% | every tier |
| 6 | drawdown: tercile of close / 60-session high close - 1 | 96.1% | 83.9% | every tier |
| 7 | listing_age: sessions since first panel session: <60 / <250 / older or censored at the panel start | 100.0% | 78.0% | every tier |

Not matched on (no point-in-time data): sector: only a 2025-02 snapshot (List Emiten/Sectors); not point-in-time, so not used; board: listing board known only as of the 2025-02 snapshot; not point-in-time, so not used; free_float: IDX tradeble_shares equals listed_shares for most names; it is not free float, so not used

## Execution

- signal at close of s, entry at the open of s + entry_lag, exit at a close, entry lag 1
- 100-share lots, notional Rp 5,000 per trade, at most 10% of session volume
- Fees: buy 0.00%, sell 0.00%
- none (no daily price limits)
- Corporate actions: source prices are split-adjusted; no reference resets are expected or scaled
- Overlap: skip; names that stop trading exit at last_close
- Lookahead check: prefix-first-v1: causal by construction. Each signal is column d of a call given only sessions 0..d and the names listed by d (250 calls); source audit passed; file, network, process, frame and heap access blocked during compute; a full-window call matched every prefix-built signal

## Warnings

- US: survivor-only: the universe is the Nasdaq Trader listing snapshot of 2026-10-08; names delisted earlier are absent
- costs assumed: per side 1.5% under $1, 0.5% $1-5, 0.15% $5-20, 0.05% above, plus the SEC fee on sales
