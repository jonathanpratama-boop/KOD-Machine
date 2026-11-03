# Causal evaluation correction — 2026-11-04

Status: corrected implementation supplied; original-data corrected evaluation NOT RUN.
Original protocol, run.py, REPORT.md and RESULT.json are preserved byte-for-byte.

The original runner removes rows with any missing fwd1/fwd3/fwd5 before computing
cross-sectional feature ranks, fitting models, and selecting top-five picks. Future
outcome availability therefore changes the historical decision universe. A disappearing
or gappy coin can be removed before it would have been known to disappear. This is a
research-validity defect, not evidence that a corrected study will become profitable.

`idxsig/research_evaluation.py` and `run_corrected.py` now:

- Determine membership from as-of peers_ok and rank features over that complete universe.
- Fit only labels whose conservative five-day maturity is strictly before each annual refit.
- Freeze an outcome-free prediction table and selections before attaching outcome data.
- Keep a selected unknown outcome in the denominator; never replace it with another coin.
- Report selected/known/unknown counts and observed-only means explicitly. Full-selection
  returns remain unknown when any selected outcome is unavailable. Censored counts remain
  zero because these source rows do not identify why a label is absent; no cause is invented.
- Preserve alpha=10, annual fitting, three-day target, 1/5-day diagnostics, five picks every
  third day, original feature families, and assumed 0.4%/2% round-trip cost sensitivities.
- Use deterministic ticker tie breaks and date-block uncertainty. Missing IC dates stay
  in their original positions rather than being compressed out of the bootstrap timeline.
- Write only into a new run directory, with input/output hashes and promotion disabled.

Arithmetic returns are means per observed pick. They are not a capital-constrained account,
compounded returns, executable fill proof, or a live signal. Peer data does not establish
causation. Prior 2023–26 data exposure remains disclosed; this correction creates no fresh
holdout. No parameters were tuned and no original-data result was recomputed for this repair.

The original report says 482,598 coin-days while RESULT.json records 469,339 evaluated rows
and 2,100 days. The latter is the published machine denominator; the former is unresolved.
The corrected writer derives all output denominators from its own frozen prediction table.

Invocation (only when intentionally performing the recorded correction):

```sh
python idx-signals/research/NEIGHBOURS_v1/run_corrected.py --rows /path/to/rows.csv.gz --output /new/corrected-run
```

Do not silently replace the old result or promote the strategy from this implementation.
