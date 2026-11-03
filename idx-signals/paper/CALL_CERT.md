# Certified dump calls (shadow, beside LEARNER v2.4)

Generated 2026-11-03T22:58:15Z from paper/learner_v3.jsonl and the registers. Method and history check: `research/CALL_CERT_v1` (the certificate held on 2023: 44 calls, right 70.5%). This report changes nothing in v2.4.

## The three plain answers

- **What is predicted:** for a US stock that just closed +30% or more, that it closes at least 10% lower at the next session while most of its twins do not. A call is made only when the shadow score clears a bar certified by Learn then Test.
- **What counts as success:** the calls are wrong at most half the time (certified level 50%, confidence 95%); the realised losing rate stays at or under it.
- **Evidence so far:** 21 live forecasts, 4 calls, 2 wrong of 4 (50.0%); p that the true rate exceeds 50%: 0.688.

## The bar

- From history alone (2022 and 2023 scores of models that never saw those years, 2599 events): threshold 0.555.
- Each live forecast uses the bar certified from history plus every live outcome resolved before it was made; the bar moves as outcomes resolve (the history check found the 2022 bar fired 3.1% of 2023's events, not 1%).
- 2023 on its own does not certify (strictest 1%: 15 calls, 4 wrong, p 0.059 against 0.05); pooled with 2022 it does, at about the top 5% of spikes. Expect few calls.

## Live forecasts

| Signal session | Ticker | Shadow score | Bar | Call | v2.4 raw | Outcome |
|---|---|---|---|---|---|---|
| 2026-10-30 | WHLR | 0.601 | 0.555 | **DUMP** | 0.623 | dumped |
| 2026-10-30 | SLGB | 0.378 | 0.555 | - | 0.519 | did not dump |
| 2026-10-30 | SGRX | 0.446 | 0.555 | - | 0.581 | did not dump |
| 2026-10-30 | ONEG | 0.516 | 0.555 | - | 0.609 | did not dump |
| 2026-10-30 | OMEX | 0.626 | 0.555 | **DUMP** | 0.700 | did not dump |
| 2026-10-30 | MASK | 0.521 | 0.555 | - | 0.631 | dumped |
| 2026-10-30 | GDYN | 0.333 | 0.555 | - | 0.466 | did not dump |
| 2026-10-30 | FMC | 0.255 | 0.555 | - | 0.382 | did not dump |
| 2026-10-30 | CHOW | 0.562 | 0.555 | **DUMP** | 0.681 | did not dump |
| 2026-10-30 | ATYR | 0.548 | 0.555 | - | 0.651 | did not dump |
| 2026-10-30 | ASUR | 0.301 | 0.555 | - | 0.430 | did not dump |
| 2026-10-29 | XCH | 0.336 | 0.555 | - | 0.507 | did not dump |
| 2026-10-29 | SGLY | 0.454 | 0.555 | - | 0.575 | pending |
| 2026-10-29 | PCLA | 0.479 | 0.555 | - | 0.599 | dumped |
| 2026-10-29 | NCPL | 0.303 | 0.555 | - | 0.423 | dumped |
| 2026-10-29 | KPLT | 0.336 | 0.555 | - | 0.498 | dumped |
| 2026-10-29 | JFIN | 0.342 | 0.555 | - | 0.499 | did not dump |
| 2026-10-29 | INLF | 0.740 | 0.555 | **DUMP** | 0.744 | dumped |
| 2026-10-29 | GKOS | 0.204 | 0.555 | - | 0.357 | did not dump |
| 2026-10-29 | BURU | 0.413 | 0.555 | - | 0.528 | dumped |
| 2026-10-29 | ADT | 0.177 | 0.555 | - | 0.384 | did not dump |

## Limits

- The bound treats events as independent; spikes cluster, so it is optimistic, and the realised rate is the check.
- History prices are survivor-only; the live record is the honest one.
- A shadow report: no order, no change to the frozen challenger.
