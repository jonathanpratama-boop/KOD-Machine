# RESEARCH_CORRECTIONS_20261104: report

**Both original verdicts are CONFIRMED under the reading rule fixed in `README.md` before the runs.** Removing the
look-ahead (rows dropped because their future return was missing) changed the information comparisons only in the
fourth decimal. Neighbours, the "next stop" and taker-buy pressure still add no information over a coin's own data, and
no pick method is profitable after the owner's assumed 2% round trip.

Runs: one each, 2026-11-04 16:09-16:11 UTC, no crash, no rerun, no code change (`RUN_NOTES.txt`). Evaluator
`CAUSAL-DAILY-RESEARCH-v1` (sha256 `05edabda…3703f`). Inputs as hashed in `README.md`. Machine-readable comparison:
`comparison.json` (built by `compare.py` from the frozen original `RESULT.json` files and the corrected ones).

## Verdicts (3-day horizon, daily rank-IC difference, 20-day block bootstrap)

| Study | Comparison | Original mean (95% range) | Corrected mean (95% range) | Rule | Verdict |
|---|---|---|---|---|---|
| NEIGHBOURS_v1 | B - A (neighbours over own data) | -0.0052 (-0.0099 .. -0.0006) | -0.0053 (-0.0101 .. -0.0008) | `lo95 <= 0` | **CONFIRMED** |
| NEIGHBOURS_v1 | C - B (next stop over neighbours) | -0.0001 (-0.0036 .. +0.0034) | -0.0002 (-0.0039 .. +0.0034) | `lo95 <= 0` | **CONFIRMED** |
| PRESSURE_v1 | P - A (taker pressure over own data) | -0.0043 (-0.0059 .. -0.0026) | -0.0043 (-0.0060 .. -0.0026) | `lo95 <= 0` | **CONFIRMED** |

All three corrected intervals have 2,100 known days and 0 unknown days. Diagnostic horizons (not part of the verdict):
B - A is -0.0052 at 1 day and -0.0043 at 5 days; C - B is -0.0010 and +0.0006; none has an interval entirely above zero.

## Information coefficients (corrected, observed-only)

| Model | 1 day | 3 days | 5 days | 3 days, original |
|---|---:|---:|---:|---:|
| A (own data) | 0.0590 | 0.0548 | 0.0523 | 0.0539 |
| B (+ neighbours) | 0.0538 | 0.0496 | 0.0480 | 0.0487 |
| C (+ next stop) | 0.0528 | 0.0494 | 0.0485 | 0.0486 |
| P (+ taker pressure) | 0.0556 | 0.0505 | 0.0474 | 0.0496 |

## Denominators

| Item | Value |
|---|---|
| Evaluated coin-days | 469,938 corrected vs 469,339 original: the 599 rows the original dropped for a missing future return are now kept |
| 3-day outcome rows known / unknown | 469,574 / 364 |
| Rebalances | 700 (every third day) |
| Top-5 picks per model | 3,500 selected; unknown outcomes: A 7, B 4, C 0, P 6, random 1 |
| Unknown picks | kept in the denominator and never replaced; full-selection means are therefore reported as unknown where any pick is unknown |

## Top-5 picks, mean 3-day return per observed pick

| Picks | Gross | Net at 0.4% | Net at 2% (owner) | Original gross |
|---|---:|---:|---:|---:|
| A | +0.44% | +0.04% | -1.56% | +0.41% |
| B | +0.33% | -0.07% | -1.67% | +0.33% |
| C | +0.38% | -0.02% | -1.62% | +0.36% |
| P | +0.35% | -0.05% | -1.65% | +0.34% |
| Random five | +0.21% | -0.19% | -1.79% | +0.28% |
| Strong group | +1.08% per pick; +0.69% per rebalance | +0.68% | -0.92% | +0.69% per rebalance |

The original runners averaged one mean per rebalance; the evaluator averages per observed pick. They agree for the
five-coin methods. For `all` and `strong_group` (variable pick counts) they differ, and `per_rebalance.py` (written after
the results were read, changes no verdict) shows the corrected per-rebalance means match the originals: `all` +0.27% vs
+0.28%, `strong_group` +0.69% vs +0.69%. Second protocol condition: B beat A in 2 of 6 test years, C beat B in 3, P
beat A in 2, as in the originals (C over B was 2 originally).

## Plain reading
The earlier defect was real but small: the original studies looked at the future only through 599 dropped rows out of
about 470,000, and correcting it moves nothing that matters. What a coin's neighbours do, where the money "goes next",
and how hard buyers are pushing do not help pick coins beyond the coin's own recent behaviour. Every pick method loses
after a 2% round trip.

## Limits
Not a fresh holdout (2023-26 prices were seen before). Observed-only means can be biased if outcomes are missing for a
reason. Daily bars, one ridge setting and these feature groups only. Large outputs (`predictions.csv`,
`scored_selections.csv`) are not committed; each is pinned by sha256 in its run's `manifest.json`.
