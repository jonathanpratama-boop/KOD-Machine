# ETH_TREND_REPRO_v1: one reproduction pass of the frozen ETH 10/40 rule

Written 2026-11-13 (UTC). Paper research only: spot ETH and cash, no leverage, no order. Nothing live was changed.

## What was run

- **Rule (frozen in FRESH_EYES_v1, T1c):** at each daily close, hold ETH from the next open when the 10-day simple
  average of the close is above the 40-day one; otherwise hold cash. Code: `handoff/fresh-eyes-2026-11-01/backtests/`
  `lib.py` (engine) and `run_t1_t5.py` (`sma_cross_positions`), imported unchanged by `repro_eth.py`.
- **Costs, both original assumptions:** Binance 0.10% fee + 0.05% slippage per side (0.15%); eToro-style 1.00% per side.
- **Inputs:** the 110 ETHUSDT spot 1d monthly archives listed in
  `handoff/fresh-eyes-2026-11-01/backtests/manifests/manifest_spot_klines_1d.jsonl`, fetched again from
  data.binance.vision by `fetch_pinned.py`; every file matched its pinned sha256 (110 of 110). Data end 2026-09-30, as
  in the original. The update adds the October 2026 archive, published after the pin (`manifest_extension.jsonl`).
- **Benchmark added here:** hold the rule's own average ETH exposure (52.1% from 2023 to 2026-09) all the time,
  rebalanced at every open, each rebalancing trade paying the same cost. A second version buys that share once and never
  trades. Buy-and-hold of 100% ETH is shown for reference.

## Reproduction

All 80 published ETH T1 figures (4 rules x 2 cost assumptions x 2 periods x CAGR, volatility, Sharpe, max drawdown,
total) are reproduced exactly: largest absolute difference 0.0 (`results/repro_eth.json`, `reproduction`).

## The rule against its own average exposure, 2023-01-01 to 2026-09-29

The rule changes position about 11 times a year (5 to 6 round trips) and holds ETH 52% of the days.

| | CAGR | Volatility | Sharpe | Max drawdown | Total |
|---|---:|---:|---:|---:|---:|
| **Rule, Binance costs** | **+50.2%** | 43.7% | **1.15** | **-36.8%** | +359% |
| 52% ETH held constantly, Binance costs | +17.1% | 32.9% | 0.64 | -42.0% | +81% |
| 52% ETH bought once, never traded, Binance costs | +14.2% | 43.8% | 0.52 | -55.0% | +64% |
| **Rule, eToro costs** | **+36.9%** | 43.7% | **0.93** | **-42.3%** | +224% |
| 52% ETH held constantly, eToro costs | +14.9% | 32.9% | 0.59 | -42.9% | +68% |
| 52% ETH bought once, never traded, eToro costs | +14.0% | 43.7% | 0.52 | -54.9% | +63% |
| 100% ETH buy-and-hold (no costs) | +24.0% | 63.1% | 0.65 | -67.5% | +124% |

Rule minus constant exposure (circular block bootstrap, 20-day blocks, 10,000 resamples; one-sided p is the share of
resamples in which the rule is not ahead):

| Costs | Extra return a year | 90% interval | p | Sharpe difference | 90% interval | p |
|---|---:|---|---:|---:|---|---:|
| Binance | +28.9 points | +5.0 to +53.2 | 0.021 | +0.50 | -0.12 to +1.09 | 0.091 |
| eToro | +21.4 points | -3.3 to +46.9 | 0.078 | +0.35 | -0.29 to +0.95 | 0.19 |

With 5-day and 60-day blocks the p for the extra return is 0.033 and 0.012 (Binance), 0.090 and 0.058 (eToro).

By calendar year (rule / constant exposure). Binance costs: 2023 +41% / +43%; 2024 +36% / +28%; 2025 +80% / +0%;
2026 to September +33% / -2%. eToro costs: 2023 +29% / +41%; 2024 +19% / +26%; 2025 +68% / -2%; 2026 +25% / -3%.
The advantage comes from 2025 and 2026, when ETH fell or went sideways; in 2023 and, at eToro costs, in 2024,
simply holding half in ETH did as well or better.

Update through October 2026 (one month after the original data end; ETH fell about 16%): the rule lost about 7% and
the constant exposure about 9%. From 2023 the rule's CAGR becomes +46.1% (Binance) and +33.1% (eToro); the extra
return a year is +28.8 points (90% interval +5.5 to +52.2) and +21.4 points (-2.9 to +45.6).

## The whole pinned history, 2017-08-17 to 2026-09-29

| | CAGR | Sharpe | Max drawdown |
|---|---:|---:|---:|
| Rule, Binance costs | +71.8% | 1.18 | -66.3% |
| 50% ETH held constantly, Binance costs | +23.5% | 0.71 | -72.3% |
| Rule, eToro costs | +57.8% | 1.05 | -69.1% |
| 50% ETH held constantly, eToro costs | +20.5% | 0.65 | -73.1% |
| 100% ETH buy-and-hold (no costs) | +27.0% | 0.71 | -94.0% |

Extra return a year: +42.7 points (90% interval +19.6 to +65.5) at Binance costs, +36.6 (+13.0 to +60.0) at eToro
costs. Sharpe difference +0.48 (+0.07 to +0.89) and +0.40 (-0.02 to +0.81). Note the rule's own worst fall: -66%.

## How choosing this rule after seeing four variants affects the evidence

FRESH_EYES_v1 pre-registered four trend rules per coin (Donchian 20/10, 28-day momentum, SMA 10/40, close above SMA200)
for BTC and ETH, taken from published studies, and twelve variants in all. The 10/40 rule on ETH was chosen for the
paper log after all of them had been read, in both periods. So the 2023 onward figures are not out of sample for the
choice: they are part of what the choice was based on.

A test that allows for the choice (White's Reality Check): the four ETH rules' daily excess over their own
exposure-matched benchmark, the same blocks of days resampled for all four so their correlation is kept, 20-day
blocks, 10,000 resamples. It asks how often the best of four rules with no true advantage would look as good.

| Window | Costs | 10/40 extra return a year | p if 10/40 had been the only rule | p allowing for the choice among four |
|---|---|---:|---:|---:|
| 2023 to 2026-09 | Binance | +28.9 points | 0.023 | **0.091** |
| 2023 to 2026-09 | eToro | +21.4 points | 0.080 | **0.235** |
| 2017-08 to 2022 | Binance | +52.8 points | 0.006 | 0.026 |
| 2017-08 to 2022 | eToro | +47.8 points | 0.014 | 0.048 |
| Whole history | Binance | +42.7 points | 0.001 | 0.007 |
| Whole history | eToro | +36.6 points | 0.005 | 0.024 |

- **Since 2023 alone, the choice removes the significance.** About 1 time in 11 (Binance costs) or 1 in 4 (eToro
  costs), the best of four rules with no advantage would have looked this good.
- **10/40 cannot be told apart from 28-day momentum.** Since 2023 at Binance costs the best of the four is 28-day
  momentum (+29.5 points), then 10/40 (+28.9), close above SMA200 (+12.5) and Donchian (-17.0). In 2017 to 2022 all
  four were ahead of their own exposure (+17 to +53 points).
- **The whole history still stands after the correction**, but its first five years are the years the published
  studies behind these rules were written about, so they are not independent of the choice of rule family.
- **Not corrected for:** BTC's four rules were read at the same time, and 10/40 on BTC did not beat holding from
  2023 on Sharpe (1.12 against 1.16 in the original results). A random-timing placebo (2,000 long/flat paths with the
  rule's average spell lengths, each against its own exposure) puts the 2023 onward result at p = 0.038 for one rule
  chosen in advance, in line with the table.
- **What is clean.** Only October 2026 (rule -7%, constant exposure -9%) and the paper log
  (`handoff/fresh-eyes-2026-11-01/paper/ledger.jsonl`, in cash on every day from 2026-10-31 to 2026-11-11) came after
  the choice. That is too short to confirm or reject anything.

Reading: a trend effect on ETH is more likely than not (three of four rules since 2023, four of four before, and the
whole history after the correction). That the 10/40 rule in particular beats holding half in ETH is not established
on the data since 2023.

## Limits

One asset; the advantage since 2023 comes from two years; the rule itself has lost two thirds of its value once
(2018); no taxes, withdrawal limits or exchange risk; eToro's real spread may differ from 1% a side; the
constant-exposure benchmark rebalances daily, which a real account would do less often (the buy-once row brackets it).
Neighbouring averages (for example 5/20 or 20/60) were deliberately not tried here: that would add looks at the same data.

## Files and commands

- `fetch_pinned.py`: fetch and verify the pinned archives. `repro_eth.py`: everything above.
- `results/repro_eth.json`: every figure, with the sha256 of the original code and manifest and the library versions;
  `results/daily_*.csv`: daily net returns of the rule and of the constant-exposure benchmark.

```
python3 idx-signals/research/ETH_TREND_REPRO_v1/fetch_pinned.py \
    handoff/fresh-eyes-2026-11-01/backtests/manifests/manifest_spot_klines_1d.jsonl RAW manifest_extension.jsonl
# RAW_PINNED = RAW without ETHUSDT-1d-2026-10.zip (the 110 pinned files); RAW_EXT = RAW (all 111 files), then:
BINANCE_RAW=RAW_PINNED python3 idx-signals/research/ETH_TREND_REPRO_v1/repro_eth.py --ext-raw RAW_EXT --out OUT
```
