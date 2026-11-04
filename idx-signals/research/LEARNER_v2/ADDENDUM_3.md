# LEARNER_v2, addendum 3: v2.3, the one live challenger

Written 2026-10-29, before any set it can forecast existed. `protocol_v2_3.json` (KOD-LEARNER-v2.3) is normative for
the challenger. It does not supersede `protocol_v2_2.json`: v2.2 keeps running untouched, as monitoring, and its 20
sealed forecasts keep verifying.

## Why

Two reviews on 2026-10-29 reached the same conclusion from different directions. The independent quantitative review
of 7c9013a: "simplify the active objective: one clearly defined prediction, one credible comparison, one prospective
result." The owner: "we need to speedrun this." `research/PATH_HISTORY_v1` then measured, on 14,561 past spikes, what
is learnable from free data and found the next-session own dump the best-discriminated and fastest-resolving dump
statement (US AUC 0.627 with EDGAR and FINRA data), while pumps barely rank. The headline was chosen there, before
any live outcome existed.

## The one question

For a US stock that just closed 30% or more higher: will it close at least 10% below the signal close at the next
session, when most of its twins do not? The companion is the same question over the 5-session plan, which v2.2 also
forecasts, so the two versions are compared on the same sets.

## What is new, and what the review asked for

| Review finding | v2.3 |
|---|---|
| "Market removed" is not what the PATH label establishes | the labels are twin-filtered paths, named so; the thesis says exactly what is graded |
| The warm-start 13D pool leaked eventual scorability | v2.3 does not use that warm start at all: its warm start is the history study's US spikes through the same feature code. The 13D pool fix belongs to the catalyst-side learner's next version (open item) |
| The confidence guarantee was stated too strongly | one gate, one 5% nominal budget, stated as asymptotic with a measured heuristic; the floor is 30 populated sessions |
| The AUC-to-weeks table had no artifact | `research/PATH_HISTORY_v1/sims/gate_power2.py` and `daily_gate.py`, with quantiles over all runs and a fair null |
| Brier gain can come from calibration alone | AUC is the claim statistic; Brier gains are reported beside it, never in its place |
| Establish how much the forecasts merely predict volatility; add the catalyst and the share supply | the pre-declared benchmark (volatility and market context only) is fitted beside the learner and recorded with every forecast; the catalyst (an 8-K that day), offerings, a shelf, a 424B5, a reverse split and turnover against shares outstanding are the E_US block |

## What it costs

A feature read from the scan's price pull or from EDGAR and FINRA is reproducible by `verify` only where those raw
inputs are still present (they are hashed in every forecast). Where they are absent, `verify` takes the recorded
features as recorded and reports the count. Training never depends on them: rows take their features from the
learner's own hash-chained forecasts.

## What does not change

Every v2.2 forecast, ledger line, protocol and gate. The registers. The holdouts. The sealing cutoffs. The rule that a
BACK call needs a 0.4 logit margin and 95% certainty. Nothing is traded.
