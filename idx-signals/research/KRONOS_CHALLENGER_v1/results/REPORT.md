# Kronos + KOD: frozen pilot result

**Decision: do not promote this configuration into trading decisions.** The filter avoided most trades in a losing
historical cohort, but lost against cash. Its four accepted trades all lost after costs. Keep the optional adapter
as research evidence; this result does not justify a larger integration or a threshold search on the same history.

| Same 128 historical opportunities | Mean net return per opportunity |
|---|---:|
| Unfiltered legacy KOD ignition signals | -4.94% |
| KOD + frozen Kronos accept/cash filter | -0.34% |
| Hold cash | 0.00% |

These are equally weighted event-opportunity returns, **not account or portfolio returns**. Rejected events earn
zero. Positions may overlap. Entry is one full hour after the completed trigger candle becomes available; exit is
24 hours after entry. Every trade subtracts the frozen 2% round-trip assumption. Binance prices are execution proxies.

## What the model selected

- Submitted/evaluable: 128/128; 114 distinct UTC decision dates; no missing outcomes.
- Accepted: 4; rejected to cash: 123; invalid forecast fell back to the original baseline: 1.
- Accepted trades' mean net return: -9.37%; profitable: 0/4.
- Rejected trades' counterfactual mean net return: -4.78%.
- Failed-forecast fallback net return: -6.26%; its loss remains in both arms.
- Paired improvement versus unfiltered signals: 4.60 percentage points;
  descriptive 95% date-cluster bootstrap interval: 2.57 to 6.67 points.
  This measures avoided losses versus an already losing baseline; it does not establish superiority to cash.
- Forecast return MAE: 11.63 percentage points versus 11.11
  for predicting zero return. Kronos was worse on this diagnostic.
- The JSON field `largest_selected_winner_removed` removes the best selected trade even when it lost; here
  all four lost, so it removes the least bad loss. This sensitivity does not alter the primary comparison.
- Frozen evaluator verdict: `INSUFFICIENT_EVIDENCE`. Only four accepted events, below the predeclared minimum of ten.

| Accepted event | Forecast return | Actual net 24-hour return |
|---|---:|---:|
| LUNAUSDT · 2025-02-05T15:00:00+00:00 | 4.24% | -10.16% |
| INITUSDT · 2025-10-11T00:00:00+00:00 | 48.50% | -10.12% |
| NEIROUSDT · 2026-05-05T09:00:00+00:00 | 2.24% | -4.53% |
| SPELLUSDT · 2026-07-07T15:00:00+00:00 | 3.43% | -12.66% |

## Reliability and resources

24 focused tests passed, including separately authored contract tests and a captured real archive sample.
The existing KOD look-ahead tool passed truncation and scramble checks on actual input selection. Its scope is
recorded in `LOOKAHEAD_CHECK.json`; it does not remove the source cohort's future-availability selection.
An exact first-forecast replay passed. BTTC produced a negative predicted price: the failure was retained, and a
separate reproduced diagnostic is in `failure_diagnostics/`. No parameters, model weights, threshold or units were
changed after the failure or after scoring.

CPU inference took 21.73 minutes for the 128 events, median
9.57 seconds per event, maximum 25.11 seconds;
process peak resident memory 482.8 MiB. These measurements come from this isolated workspace,
not the paid collection server or a shared-load capacity test.

## Limits and preserved evidence

The sample was drawn by frozen hash from 4,413 already-exposed event identifiers after June 2024, not from new
prospective observations. The source event inclusion required future 72-hour price availability. The model's full
training membership was not independently audited. There is no capital allocation, spread/depth, broker-fill,
market-risk adjustment or trading authorization. This result concerns this one pretrained configuration and filter,
not every possible use of Kronos. It does not change the separate 30-day cloud study.

- `RESULT.json`: complete metrics and limitations.
- `records.jsonl`: every prediction/failure joined to its outcome; no event was removed.
- `predictions.jsonl`: frozen forecasts before the outcome join.
- `inputs.tar.gz`: exact causal inputs, separate outcomes, archive checksum manifest and preparation coverage.
- `forecasts.tar.gz`: all 127 generated paths with a valid positive terminal close; original invalid forecast has its failure record and
  an explicitly reproduced raw diagnostic, not an invented original path.
- `run_manifest.json`: code, cohort, input, model and prediction hashes, versions and resource measurements.

**CLOSE this pilot configuration.** A different use of Kronos would require a new question and protocol; this
negative readout will not be rescued by searching thresholds on the same outcomes.
