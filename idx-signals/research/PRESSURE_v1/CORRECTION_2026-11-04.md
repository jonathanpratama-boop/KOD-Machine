# Causal evaluation correction — 2026-11-04

Status: corrected implementation supplied; original-data corrected evaluation NOT RUN.
Original files and results are preserved unchanged.

PRESSURE inherits NEIGHBOURS' future-completeness filtering before feature ranking and
top-five selection. The additive `run_corrected.py` uses the shared causal evaluator;
see `../NEIGHBOURS_v1/CORRECTION_2026-11-04.md` for the defect and output interpretation.

Pressure rolling windows now use explicit calendar days, so an archive gap cannot compress
five observations spanning a longer interval into a purported five-day feature. This is a
data-handling correction, not a new trading parameter. Missing pressure observations remain
NaN; the original model's neutral rank convention is kept with separate missingness flags.
An absent observation is never presented as measured neutral buying pressure. Negative
volumes and taker-buy volume above total volume are rejected.

Alpha, model features, horizons, yearly refits, selection frequency and cost sensitivities
are unchanged. Original failure counts and neutral-imputation limitations still apply.
The original negative finding is not repaired into a positive claim. No original-data
research was rerun, no live order was placed, and no strategy promotion is permitted.

```sh
python idx-signals/research/PRESSURE_v1/run_corrected.py --rows /path/to/rows.csv.gz --taker /path/to/taker.csv.gz --output /new/corrected-run
```
