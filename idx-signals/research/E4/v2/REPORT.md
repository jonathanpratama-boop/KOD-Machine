# E4 v2 results (protocol KOD-GLOBAL-E4-v2): the regime-conditioned fade passed discovery and failed validation

Historical research on Binance USDT pairs. Discovery 2020-07-01 .. 2022-12-31 selected a pair;
the single validation test on 2023 failed it. The holdout was not loaded.

## Discovery (`CRYPTO/discovery/`)

288 runs: the four v1 detectors and their `_BEAR` variants (BTC below its 50-session mean at
the signal close), 36 plans each, liquidation at +100% on the session high, redenomination-sized
jumps excluded as non-trades. **Admissible: 31 of 288, every one a `_BEAR` variant.** Without the
regime condition nothing was admissible, as in v1; with it, G2_RET30 and G7_MOMENTUM5_30 shorts
were positive in 2020, 2021 and 2022 alike.

Selected (the highest average net return): **G2_RET30_BEAR, entered at the first open above the
signal close within three sessions, covered at the first up close, else at the close of the second
session after entry** — 407 trades, hit rate 70.3%, +5.82% per trade against 0.00% for matched
random shorts under the same plan (p = 0.005), median +6%, 5th percentile -29%, 2.0% liquidated,
+5.2% in 2021 (197 trades) and +6.1% in 2022 (200).

## Validation (`CRYPTO/validation/`, run `MOONSHOT_E4_D1` on 2023)

| | discovery 2020-22 | validation 2023 |
|---|---:|---:|
| signals / scored | 407 | 57 / 34 |
| hit rate | 70.3% | **67.6%** |
| median net return | +6% | **+9.3%** |
| average net return | +5.82% | **-1.50%** |
| matched random shorts | 0.00% | -0.22% |
| one-sided p vs matched | 0.005 | 0.78 |
| liquidated | 2.0% | **8.8%** (3 of 34) |
| 5th percentile | -29% | -100% |

**Failed** on four of six criteria: scored 34 < 100, average net return < 0, p = 0.78, the tail.
The hit rate and the median replicated; the average did not, because three of 34 shorts were
liquidated (the position doubled against them within the hold) and those three cost more than
the 23 winners made. 2023 had few bear-regime sessions (BTC rose most of the year), so the sample
is small; the protocol said in advance that a small sample fails for the right reason.

## Reading

- The pattern is the same one v1 showed, now with a realistic short model: **the win rate is real
  and the losing rate is low; the losses are not.** Two trades in three win 6-9%; one in eleven,
  in 2023, lost the whole position. Selling the squeeze is selling insurance.
- The regime condition carried discovery (2021 and 2022 both positive) and was close to absent in
  2023. A plan that works only in bear regimes is a plan that mostly waits; when it does fire in
  a rising market, the squeezes are the ones that run.
- 31 admissible of 288 after a second design pass on discovery is the kind of count that a single
  validation test exists to discipline. It did.

## Status

`moonshot_e4.SELECTED` stays frozen as the record of what was tested; no paper policy change;
MOONSHOT_E4_D1 is not a decision detector anywhere. The short-side plan family, with and without
the regime condition, is exhausted for these detectors on crypto. US was not run. The holdout
stays sealed. A further attempt would be a new protocol with a new idea, not a re-tune: for
example a position cap that makes the liquidation loss small relative to equity by construction
(sizing is a portfolio question the harness does not answer), or a different regime definition
chosen before looking again, each tested once on the untouched holdout only after prospective
evidence.
