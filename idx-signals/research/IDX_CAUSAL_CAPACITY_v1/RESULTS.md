# IDX_CAUSAL_CAPACITY_v1: results

**Conclusion: the ex-post capacity filter did not hide an edge.** Under the causal fill model
FILL-C-v1, MOONSHOT_E1_D1 still loses money and still does worse than matched random picks.
The difference from fill model A is not material by the threshold fixed in `PROTOCOL.md`
(commit `857807a`, pushed before the rerun). E1 D1 remains negative evidence, and nothing
else changes.

This is a historical rerun of the 2023 validation year. It is not prospective performance,
and it does not approve or reject anything beyond what the evidence run already showed.

## Steps

1. **Reproduction.** Fill model A was rerun in memory on the new code (`d57e4b8`). It gave a
   byte-identical trades file and identical summary statistics to the evidence run
   `20261008T000401Z` (`reproduce_a.json`).
2. **Rerun.** Fill model C was run with every other input unchanged: the same panel, registry,
   seed and 200 draws. It was appended as run `20261009T050040Z_MOONSHOT_E1_D1_v1.1`. The
   2024 onwards holdout was not read.
3. **Comparison.** `compare.py` compared the two recorded runs and wrote `comparison.json`.

## Rule against matched random

| | A (evidence run) | C (causal capacity) |
|---|---:|---:|
| Attempts (after the overlap skip) | 1,042 | 1,073 |
| Filled | 420 | 262 |
| Scored | 407 | 251 |
| Hit rate | 28.3% | 31.1% |
| Average net | −4.06% | −3.64% |
| Median net | −5.93% | −5.93% |
| Matched random, average net | −0.53% | −0.44% |
| Difference vs matched random | −3.53 pp | −3.20 pp |
| One-sided p | 1.000 | 1.000 |

- **APPROVAL-v2 test under C:** p < 0.05 no, positive average net no, above matched random
  no. It **fails** all three.
- **Materiality:** the average net moved 0.42 pp, under the 1 pp threshold, and p did not cross
  0.05. The difference is **not material**.

## What changed, trade by trade

- **Stricter, not looser.** The rule fires on names that hit the upper price limit (ARA). Those
  names trade very heavily on the entry session, so the final entry-day volume that A used is
  much larger than their 20-session median.
  - 159 trades scored under A are skipped for liquidity under C. Another 5 that A held into the
    end of the data (incomplete) are also skipped.
  - 2 are skipped because a reset the registry cannot verify fell inside the capacity window
    (`SKIP_CAPACITY_UNKNOWN`).
  - Only 4 attempts that A skipped for liquidity are filled under C. More attempts are made
    under C (1,073 against 1,042) because fewer fills free up the overlap rule.
- **The dropped trades were not the good ones.** The 163 trades scored only under A averaged
  −4.78% net. The 7 scored only under C averaged −5.69%. The 244 trades scored under both
  have identical returns in the two runs (−3.58% average). Only which trades are entered
  changes. Exits, costs and corporate actions do not.
- **Same for the baseline.** Matched random fills fall from 37.3% to 33.4%. The control
  population changes in the same direction as the rule's, because the baselines use the same
  execution.

## Limits

- A 20-session median ignores the signal day's own surge in volume, which is known at the
  decision. For limit-up names this makes C conservative: real capacity on the entry day was
  probably larger. A rule allowed to use the signal-day volume would be a different model. It
  was not specified in advance and was not run.
- Using registry-verified split factors assumes a split's ratio and date were public before
  the entry session. Every verified split in this window was corroborated by the exchange's
  reference prices and share counts.
- The entry still needs the entry session to have traded and not to close locked at ARA.
  Those are fill outcomes of the closing auction, as in A.
- Single year (2023) and a single rule. Nothing here estimates prospective performance.

## Recommendation

New IDX research runs should use `--fill-model C`. It uses only data available at the
decision, and it matches how IDX paper plans are sized (10% of 20-session median traded value).
The pinned evidence run and the paper policy are unchanged. Changing what is pinned would
need a new policy version.

## Reproduce

```sh
cd idx-signals
python3 research/IDX_CAUSAL_CAPACITY_v1/reproduce_a.py     # A in memory == evidence run
python3 -m idxsig run --rule MOONSHOT_E1_D1 --start 2023-01-02 --end 2023-12-29 \
  --panel data/manifests/panel-20261007T225823Z.json \
  --ca-registry data/manifests/ca_registry-20261007T230210Z.json --fill-model C
python3 research/IDX_CAUSAL_CAPACITY_v1/compare.py
python3 -m unittest tests.test_fill_c
```
