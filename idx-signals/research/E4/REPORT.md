# E4 results, v1 (protocol KOD-GLOBAL-E4-v1): the fade on crypto, no plan admitted

Historical research on Binance USDT pairs, discovery 2020-07-01 .. 2022-12-31 only. Validation
(2023) was not run and the holdout was not loaded. US was not run under v1 (its repair panel was
not yet rebuilt; the archived inputs have since been fetched and verified).

## Result

144 harness runs: G2_RET30, G1_RET20_CLOSEHIGH, G10_RET15_CLOSEHIGH and G7_MOMENTUM5_30 on the
short side, each under the 36 pre-registered plans (3 entries x 3 exits x hold 1/2/3/5), fill
model A, 0.1% fee + 0.1% slippage per side, funding 0.05% per day against the short, 200 matched
and 200 same-session random shorts per run (`CRYPTO/discovery/plans.csv`, `summary.json`). The
precondition reproduced the recorded E2 crypto run exactly (`CRYPTO/reproduce/result.json`).

**Admissible pairs: 0 of 144.** `moonshot_e4.SELECTED` stays None and no paper policy changes.

| | count of 144 |
|---|---:|
| hit rate >= 50% | **102** |
| average net return > 0 | 21 |
| average net return > 0 in 2022 (the bear market) | **143** |
| average net return > 0 in 2021 (the bull market) | **0** |
| average net return > 0 in 2020 (July on) | 21 |
| 1st percentile of trade returns >= -50% | **0** |

Best by average net return (none admissible):

| Pair (short) | Scored | Hit | Avg net | Median | Worst | 2020 | 2021 | 2022 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| G2_RET30, next open, hold 1 | 1,397 | 64.9% | +1.36% | +6.9% | -240% | +1.5% | -0.8% | +5.5% |
| G2_RET30, next open, stop at the signal high, hold 2 | 1,394 | 63.3% | +1.24% | +7.1% | -240% | +1.5% | -1.2% | +6.0% |
| G2_RET30, into a bounce within 3, hold 1 | 916 | 64.7% | +1.16% | +6.2% | -200% | +0.9% | -1.2% | +6.4% |
| G2_RET30, next open, hold 5 (reference: D1's plan mirrored) | 1,241 | 58.2% | -103% | +8.6% | -126,245% | | | |

The reference plan's average is one trade: COCOS, shorted at 0.000714 on 2021-01-16 and "bought
back" at 0.9003 a week later, Binance's 1000:1 COCOS redenomination, not a move. Without it the
plan's worst trades are real: GMT +424% in five sessions (March 2022), WRX, DOGE, NKN, CHR, STMX
(+200-380%, spring 2021). With losses capped at -100% (what an isolated-margin perpetual short can
lose) the reference plan averages +1.2%; 30 of its 1,241 trades (2.4%) lose more than the whole
position and 95 (7.7%) more than half of it.

## Reading

- The fade wins often: about two trades in three, with a median gain of 6-9% per trade. That is
  the high hit rate the question asked for, and it is exactly what selling volatility looks like.
- It is not a low losing rate. The losses are rare and enormous: one trade in forty or fifty
  loses more than the position, and no exit rule in the family prevents it, because the squeeze
  arrives as a gap the daily close cannot stop. Hit rate and risk are not the same thing.
- It is a regime. Every plan lost money in 2021 and nearly every plan made money in 2022. Short
  the spikes in a bear market and you win; in a bull market the spikes continue. The protocol's
  per-year condition exists for this and did its job.
- Redenominations (COCOS) are in the data as thousandfold jumps. A short model needs to treat
  them as non-trades; v1 did not, as frozen, and that is on record.

## What follows

A v2 protocol (`v2/`), designed on this discovery table and tested once on validation if anything
is admissible: the same family under a realistic short model (isolated-margin liquidation at
+100%, redenomination-sized jumps excluded as non-trades) and one pre-specified regime condition
(BTC below its 50-session average at the signal close, known at the decision). Its tail criterion
is stated in v2, because v1's 1st-percentile rule is unsatisfiable under liquidation by
construction. Validation stays untouched until then; the holdout stays sealed.
