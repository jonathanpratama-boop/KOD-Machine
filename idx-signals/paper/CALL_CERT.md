# Certified dump calls (shadow, beside LEARNER v2.4)

Generated 2026-10-29T17:47:34Z from paper/learner_v3.jsonl and the registers. Method and history check: `research/CALL_CERT_v1` (the certificate held on 2023: 44 calls, right 70.5%). This report changes nothing in v2.4.

## The three plain answers

- **What is predicted:** for a US stock that just closed +30% or more, that it closes at least 10% lower at the next session while most of its twins do not. A call is made only when the shadow score clears a bar certified by Learn then Test.
- **What counts as success:** the calls are wrong at most half the time (certified level 50%, confidence 95%); the realised losing rate stays at or under it.
- **Evidence so far:** 0 live forecasts, 0 calls, no resolved call yet.

## The bar

- From history alone (2022 and 2023 scores of models that never saw those years, 2599 events): threshold 0.555.
- Each live forecast uses the bar certified from history plus every live outcome resolved before it was made; the bar moves as outcomes resolve (the history check found the 2022 bar fired 3.1% of 2023's events, not 1%).
- 2023 on its own does not certify (strictest 1%: 15 calls, 4 wrong, p 0.059 against 0.05); pooled with 2022 it does, at about the top 5% of spikes. Expect few calls.

## Live forecasts

| Signal session | Ticker | Shadow score | Bar | Call | v2.4 raw | Outcome |
|---|---|---|---|---|---|---|
| - | - | - | - | - | - | no live forecast yet |

## Limits

- The bound treats events as independent; spikes cluster, so it is optimistic, and the realised rate is the check.
- History prices are survivor-only; the live record is the honest one.
- A shadow report: no order, no change to the frozen challenger.
