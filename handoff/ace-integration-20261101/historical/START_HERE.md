# KOD shared-account historical proof — 1 November 2026

## Verdict

**A functioning daily-account simulation, not demonstrated profitable edge or live-system validation.** All eight frozen cases completed and independently reconciled. The shared trend produced positive modeled returns, but validation growth was below both passive controls, with lower sampled drawdown. No claim of economic superiority is established. No policy was changed or rerun after outcomes.

Each case starts with **10,000 USDT research cash**. These are hypothetical results, not actual trades or a user balance. “Validation” names reused historical data, not an untouched holdout.

| Window / policy | Ending NAV (USDT) | Total growth | Annualized growth | Sampled max drawdown | Fees (USDT) |
|---|---:|---:|---:|---:|---:|
| Development / Shared trend | 20,592.77 | +105.93% | 14.70% | 15.42% | 88.69 |
| Development / Buy-once + same kills | 17,844.13 | +78.44% | 11.62% | 27.60% | 16.92 |
| Development / Buy-once, no kills | 24,500.54 | +145.01% | 18.54% | 71.69% | 23.59 |
| Development / Cash | 10,000.00 | +0.00% | 0.00% | 0.00% | 0.00 |
| Validation / Shared trend | 12,377.20 | +23.77% | 5.86% | 11.55% | 76.78 |
| Validation / Buy-once + same kills | 15,037.86 | +50.38% | 11.50% | 19.54% | 25.03 |
| Validation / Buy-once, no kills | 36,220.21 | +262.20% | 40.97% | 57.58% | 46.23 |
| Validation / Cash | 10,000.00 | +0.00% | 0.00% | 0.00% | 0.00 |

Development:2017-09-26→2023-01-01 opening; validation:2023-01-01→2026-09-30 opening. Separate accounts, no within-account restart. Development begins after40 strictly earlier closes because earlier warm-up data do not exist at the old August17 study boundary.

## Why the long windows are not years of active growth

- Development trend killed on **2018-03-15** (negative90-day Sharpe), liquidated at the March16 modeled open, and stayed cash. Only144 of1924 daily samples were invested.
- Validation trend killed on **2023-04-22** (negative90-day Sharpe), liquidated at the April23 modeled open, and stayed cash. Only89 of1369 daily samples were invested.
- All eight cases ended with no holdings/pending orders in this replay. This is an observed result of the declared capacity model, not forced liquidation or a guarantee of real execution.
- A25% drawdown trigger is not a guaranteed loss cap: the development risk-matched passive case reached27.60% sampled drawdown while waiting for a later modeled liquidation.

## Essential comparator limitation

Both development buy-once controls targeted5,000 USDT per coin, but the frozen synthetic volume cap bound their first entry. Actual cash debits were2,830.58 BTC-side and1,704.46 ETH-side; **5,464.96 USDT remained cash**, and gross exposure was only**45.31%** of NAV. Unfilled IOC remainders were canceled, not silently refilled. Thus these are intended50/50 buy-once controls under the cap—not fully invested ideal50/50 buy-and-hold. Validation entry was99.999798% invested with0.02016 USDT cash and nonbinding caps. See INITIAL_PASSIVE_EXPOSURE.json for exact values.

The no-kill control deliberately has a different risk policy; its larger return came with much larger drawdown. Do not select a winner or change the volume/risk policy retrospectively from this comparison.

## Fixed assumptions and limits

- Exact v2 SMA10/40,20-logreturn volatility targets and shared-cash down-normalization; this is not the earlier independent per-asset0/1 backtest.
- Prior-day closes assumed available at00:01; decisions execute only at the FOLLOWING day’s opening reference—a full-session delay. Historical first-publication/arrival timestamps are unknown. No BBO or executable-quote parity is claimed.
- Fee0.1% plus adverse slippage0.05% per side, zero tax/interest,8-decimal quantity precision and a synthetic0.1%-of-already-known-volume cap are research assumptions, not verified venue/user terms.
- Cash, holdings, fees, turnover, NAV, initial-equity peak, persistent kills and later-only liquidation are reconciled. Intraday drawdowns, actual depth/queueing/minimums/latency and live broker operations remain unsupported.
- No downloads, new market inputs, variants, fitting, real orders, scheduler, remote publication or deployment occurred. The separate Coinbase attempt remains blocked; this historical replay does not repair its connectivity.

## Inspectable proof

- **27 synthetic tests** (13 author+14 independent), normal Python and`-O`, passed before historical execution.
- All**220 original archive hashes** and3332 bars/asset validated before returns. Reviewer independently byte-hashed all220 files. No raw archive ZIP is bundled.
- One canonical run:2026-11-01T11:34:27.503333Z→11:38:47.897493Z, process exit0. All8 account chains passed deterministic core replay; independent eventwise cash/holdings/fees/NAV/timing/risk/metric checks also passed.
- Complete derived journals, modeled observations, summaries, source/protocol pins, test logs, pre-outcome clearance and postrun audit are included. Derived journals contain historical reference prices; they are not original archive files or untouched holdout evidence.

Key file: `historical_shared_account_results_20261101T1134/RESULTS.json` SHA256
`142c1074cf4c861e800304fee5752746cd510bbeb8ecb407d413ea83affd324f`.

## Verify locally without network or another market experiment

Run from this bundle’s root:
```sh
python historical-independent-audit/run_combined.py
python -O historical-independent-audit/run_combined.py
python historical-independent-audit/verify_results.py
python -O historical-independent-audit/verify_results.py
```

The last two commands independently verify the already-completed journals; they do not run a new strategy variant or fetch data. `CANONICAL_COMMAND.md` records the actual completed command; the source README explains reproduction. Original archive inputs are intentionally excluded; do not silently download or change parameters to rerun. `BUNDLE_MANIFEST.json` lists every delivered file’s SHA256.
