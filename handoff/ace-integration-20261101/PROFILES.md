# Three execution profiles: shared accounting code, separate contracts

All three profiles run the same reviewed core:
- `paper_candidate.py`, sha256 `dbda12d461cb601693d6fa77737b8e0f955c9b0f2b7732841a2d9488f6c834c3`;
- the same cash accounting, `paper_cash_accounting.py`, sha256
  `29688797f6738e4aa02ca87403a5a90d60dec0bca54cffab36a4a4a7e266f8a6`.

The bytes are listed per profile in `hash_verification/shared_core_per_profile.txt`. Two profiles add a documented profile
seam (`CORE_PROFILE_DIFF.patch`).

**Shared accounting does not make the three execution profiles interchangeable.** The integration keeps them in separate directories with
separate journals, pins and clearances. It merges none of their outputs and runs none of them against another's inputs.

| | 1. Synthetic paper v2 | 2. Coinbase USD reference | 3. Historical daily replay |
|---|---|---|---|
| Directory | `paper_v2/.../trend_core_paper_v2_candidate_20261101/` | `reference_profile/coinbase_reference_adapter_20261101/` | `historical/historical_shared_account_replay_20261101/` |
| Core | `paper_candidate.py` (original) | `paper_reference_core.py` = original + profile diff | `daily_core.py` = original + profile diff |
| Evidence accepted | `synthetic` only; refuses anything else | public Coinbase Exchange GETs only (metadata, 40-day candles, level-1 books) | pinned Binance Vision daily archives (220 files, not bundled) |
| Instruments, currency | synthetic BTCUSDT/ETHUSDT, synthetic USDT | BTC-USD, ETH-USD, USD | BTCUSDT, ETHUSDT, USDT |
| Initial cash | configurable; fixtures 1,000 and 10,000 | 1,000 USD reference account | 10,000 USDT per case |
| Costs (named assumptions) | scenario fee and slippage, versioned per scenario | 1% fee per side, 0.1% slippage, 10% liquidity fraction, tick-rounded adverse price | 0.1% fee + 0.05% slippage per side, 0.1% of known volume cap |
| Timing | fills only on observations after the decision | fills only on post-intent book observations; stale marks (> 5 s) make NAV unknown | decision on prior-day closes, executed at the next day's opening reference (a full-session delay) |
| State | runnable offline; fixture demo only | OFF by default; the one authorised capture failed (`URLError`, 2026-11-01T11:07Z); capture authorisation is not renewed, so no retry | completed once; 8 frozen journals verified |
| What it does not show | not market performance | not Binance/USDT or eToro execution | not live-quote parity or untouched validation |

**Common contract (unchanged in every profile).**
- **Signal:** SMA 10/40 and 20-return volatility targets.
- **Sizing:** targets normalised down when they sum above 1, within shared cash.
- **Rebalancing:** against actual holdings, sells before buys.
- **Risk:** initial-equity peak; persistent kill at 25% drawdown or negative 90-day Sharpe; liquidation only on later
  observations.

**Not the same as the earlier backtest.** None of the three is the FRESH_EYES_v1 per-asset 0/1 backtest, and that
backtest does not validate them.
