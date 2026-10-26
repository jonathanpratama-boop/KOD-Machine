# LEAD_LADDER_INTL_v1 addendum 1 (2026-10-26, before any statistic)

The first feasibility attempt stopped before computing anything: `idxsig.execution.Market` evaluates the IDX
auto-rejection calendar for every panel and refuses dates before 2019-07-29, and the INTL panels start at
2019-01-01. `execution.py` is pinned by LEAD_LADDER_v1 and is not changed. Instead the INTL runner (run_v2.py; run.py stays as committed) drops panel rows
dated before 2019-07-29 when it loads a panel (the panel files and manifests are unchanged).

Effects: the warm-up before discovery (2020-07-01) is 11 months instead of 18; listing age is censored at 2019-07-29
instead of the first Yahoo bar, so a stock listed between January and July 2019 reads as old. P3 therefore asks
about listings since 2019-07-29. Nothing else changes.
