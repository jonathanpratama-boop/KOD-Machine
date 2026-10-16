# EXIT-ATR-v1 (cloud run): result — NEGATIVE

Exploratory historical test on previously examined E2 discovery data (Binance spot, 2020-07-01..2022-12-31).
Not prospective performance. 2023 and the 2024+ holdout were not read. Protocol frozen at `d1f11c4` before
any exit return existed; one run; nothing retuned. Machine-readable: `RESULT.json`; ledgers: `trades.csv.gz`
(every signal trade: entry, ATR, initial and final stop, stop raises, exit reason, prices, all nets) and
`controls.csv.gz`.

## The two answers

1. **Does the trailing exit improve on the original exit for identical entries? Does not improve.**
   Paired change −0.82 percentage points per trade (95% week-bootstrap interval −2.92 to +1.19).
2. **Does the resulting strategy have positive net returns? Unprofitable.**
   Mean net −1.11% per trade at 0.3% per side (95% interval −3.82% to +1.55%). The original exit was
   −0.29% on the same trades (−4.21% to +3.60%).

Overall: **NEGATIVE**. Five of six acceptance criteria fail.

| Criterion | Value | Pass |
|---|---|---|
| C1 at least 200 common scored trades | 1,181 | yes |
| C2 trailing-exit mean net > 0 in each year | 2020 −1.74%, 2021 +0.45%, 2022 −3.96% | no |
| C3 lower 95% bound of mean net > 0 | −3.82% | no |
| C4 lower 95% bound of paired improvement > 0 | −2.92 points | no |
| C5 excess over matched controls with the same exit > 0 | −3.00 points (−4.54 to −1.37) | no |
| C6 mean net > 0 at 0.4% per side | −1.31% | no |

## Trades

- Shared entries: 1,495 G2_RET30 signals, 238 skipped because the coin was still held under the original
  exit, 1,257 attempted, 1,244 scored by the original model.
- Excluded from both arms: 55 for ATR warm-up (62 fail it, 7 of them also touch a unit change), 8 for a
  source-confirmed unit or asset change, 11 unfilled, 2 crossing the research boundary.
- **Common scored set: 1,181 trades, 307 coins** (2020: 89, 2021: 718, 2022: 374); 1,095 with every hour,
  83 with short gaps, 3 truncated.

| Primary costs (0.3% per side) | Original exit (A) | ATR trailing exit (B) |
|---|---:|---:|
| Mean net | −0.29% | **−1.11%** |
| Median net | −9.72% | −8.65% |
| Win rate (Wilson 95%) | 33.2% (30.6–35.9) | 35.6% (32.9–38.3) |
| Average win / average loss | +35.6% / −18.1% | +26.9% / −16.6% |
| Worst trade / worst 1% | −65.4% / −46.5% | −65.4% / −40.5% |
| Best trade | +380% | +178% |
| Holding hours, mean / median | 144 / 144 | 90 / 111 |

- Arm B exits: 626 stops, 21 gaps through the stop, 534 never stopped (identical to arm A).
  359 trades improved and 288 got worse.
- The stop is wide: initial distance from entry median 37% (10th–90th percentile 26% to 78%), because the
  14-day ATR after a +30% day is large. 99.6% of trades had their stop raised at least once.
- By year the trailing exit cut losses in the 2022 decline (+4.05 points per trade) and cut winners in 2021
  (−3.39 points). The total effect is negative and its interval spans zero.

## Comparison with matched controls

Each signal trade was compared with up to 200 matched coins entered the same day (minimum 26 eligible):

- excess with the original exit −2.86 points (−4.98 to −0.51);
- excess with the trailing exit −3.00 points (−4.54 to −1.37).

The signal underperformed comparable random entries under **both** exits. The exit does not change that.

## Capital exposure

Fixed 5,000 USDT per trade, unlimited capital, P&L booked at exit:

| | Original exit | ATR trailing exit |
|---|---:|---:|
| Maximum concurrent positions | 79 (395,000 USDT) | 76 (380,000 USDT) |
| Mean concurrent positions | 7.8 | 4.8 |
| Total P&L | −17,105 USDT | −65,757 USDT |
| Maximum drawdown | −279,094 USDT (55.8 trade sizes) | −181,064 USDT (36.2 trade sizes) |

The trailing exit ties up less capital and has a shallower drawdown, but loses more in total.

## Sensitivities (predefined)

| | Mean net A | Mean net B | Paired B − A |
|---|---:|---:|---|
| Stress 0.4% per side | −0.49% | −1.31% | −0.82 points (−2.91 to +1.19) |
| Original 0.2% per side | −0.09% | −0.92% | — |
| Conservative gap fills | — | −1.11% | unchanged: no stop fired on the first bar after a gap |
| Data-end positions at −100% (3 trades) | −0.45% | −1.27% | −0.82 points |
| UNFI excluded (1 trade) | — | −1.14% | −0.81 points |

## Verification

- 16 focused tests cover ATR timing, true range, warm-up rejection, initial stop, next-bar ratchet, no
  downward move, no take-profit, gap fills, missing bars, conservative gaps, the deadline, truncated data,
  costs and future-bar invariance. The 249-test branch suite passes, and the append-only check passes.
- Arm A at E2's original costs reproduces E2's harness for all 250,387 scored signal and control trades
  (largest difference 2.3e−13).
- `verify_result.py` replays 60 random trades from the raw panel and raw Binance zip files with a separate
  implementation: ATR, exit reason, exit price and both nets match in 60 of 60. It also reproduces the
  bootstrap interval from the saved ledger.
- Inputs: E2's original panel (sha256 `3dc12749…`). The shared entry list reproduces Hermes's counts
  exactly. No file after 2022-12 was opened.

## Forensic note (not a result)

Scoring all 1,244 original-model trades at E2's costs, without the unit-change exclusion, gives a mean of
+100.6%. One trade causes it: COCOS's unadjusted 1,000:1 redenomination (a fake +125,489%). With the
documented exclusions the same arm averages −0.09%. Any E2-style crypto trading statistic over this
period needs the exclusion.

## What this cannot establish

- Any other ATR length, multiplier, take-profit or signal. None was tried, by design.
- Fill quality. Hourly bars do not show the order book, so stop fills at the stop price are optimistic in
  fast markets.
- Anything about 2023 onward, or live trading.
