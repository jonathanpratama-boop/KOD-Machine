# E3 addendum 2: the precondition deviation, explained (written while discovery ran)

Addendum 1 left the cause of the matched-baseline deviation open. It is now pinned down; no
E3 statistic was read in the process.

**Not the libraries.** The recorded E1 run (`20261008T000401Z`, fill model A) re-run on E3's
panel and registry under Python 3.12 with the recorded pandas 2.2.3 / numpy 2.3.5 gives the
same matched-random mean as under Python 3.15 / pandas 3.0.6 / numpy 2.5.4: -0.5342%, against
-0.5332% recorded. Signals, scored count, status counts and the rule's average net return are
identical in every environment.

**Not the data.** The pinned mirror commit yields the same 975 files (every SHA-256 equal), and
the panel builder takes mirror rows for every session up to 2025-02-21; the Yahoo segment
(2025-02-24 on) differs, but the recorded run's window is 2023. The registry differs by one
reset dated 2026-06-17 (BNBR), outside every E3 period.

**The control-matching code.** `idxsig/controls.py` changed after the recorded run's commit
(`a78ce92`): commit `bcb89f0` ("a listed day without trades counts as zero volume") and its
neighbours altered the liquidity feature used to bucket control candidates. A per-draw
comparison against the recorded `random_draws.csv` shows the same relaxation levels but
different draws: 41 of 200 matched draws identical, a net 7 of 75,371 matched-control trades
moving from EXITED to SKIP_LIQUIDITY (117,102 to 117,109), while the same-session random
baseline, which does not use the buckets, is identical in every scored count. So the recorded
baseline was computed with the matching code of its day; every E3 number is computed with
today's, and the within-E3 comparisons (plan against plan, rule against its own baseline) share
one code version, one panel and one registry.

**Consequence.** Discovery proceeds with `--accept-deviation` as addendum 1 said. A future
reproduction of the recorded 2026-10-08 runs should check out their code commit, or compare only
the rule side, which this precondition already does exactly.
