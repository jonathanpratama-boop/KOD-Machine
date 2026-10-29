# CALL_CERT_v1: result (one look, 2026-10-29)

Protocol `protocol.json`, run once by `run.py`; every number is in `results/RESULT.json`. Counted trial
`CALL_CERT_v1_result.json`, the result of the PENDING registration `CALL_CERT_v1.json`.

**Question.** Can LEARNER v2.4's model (its 33 features, fitted out of time) make calls whose losing rate Learn then Test
certifies on 2022, and does the certificate hold on 2023?

| Call | Certified level (alpha) | 2022: certified? | 2023 calls | 2023 losing rate | Verdict |
|---|---|---|---|---|---|
| DUMP, next session (the stock closes 10% lower tomorrow, on its own) | wrong at most 50% | yes, at the strictest setting: 12 calls, 2 wrong (p 0.019) | 44 (3.1% of 1,402 events) | **29.5%** (31 right, 13 wrong) | **HOLDS** |
| SAFE, next session (it will not) | wrong at most 17.0% (half the base rate) | no: the safest 1% still dumped 3 of 12 | none | - | CANNOT CERTIFY |
| DUMP, 5 sessions | wrong at most 50% | no: 4 of 11 wrong at the strictest setting (p 0.27) | none | - | CANNOT CERTIFY |
| SAFE, 5 sessions | wrong at most 21.2% | no | none | - | CANNOT CERTIFY |

## What it means in plain words

- **One call can be certified, and the certificate held.** When the model puts a stock among its most likely next-day
  dumps, it was right 70.5% of the time on a year it had never seen (2023), against a base rate of 35.0% for any spiking
  stock. It speaks rarely: 44 times in 2023, under once a week.
- **The machine cannot certify a "safe" call.** Even the stocks it rates least likely to dump still dumped about a quarter
  of the time; nothing in its features marks a spike as safe to hold.
- **The 5-session statement cannot be certified at all** at the strictest setting tried; its base rate is already 42-44%.
- **The bound is conservative, as designed.** Without it, the naive threshold (empirical 2022 losing rate under 50%) made
  92 calls in 2023 with a 34.8% losing rate: more calls, still right more often than wrong. The certificate gave up half the
  calls for a guarantee.

## What it does not show

- **Live skill.** History, one calibration year, one test year.
- **Independence.** The binomial bound treats spikes as independent; they cluster in time, so the certificate is optimistic.
  2023 is the honest check, and it passed.
- **Survivor-free prices.** US prices are survivor-only.
- **Threshold stability.** The 2022 threshold made 1% of 2022's calls but 3.1% of 2023's: the refitted model's scores moved.
  A live version must recalibrate as outcomes resolve.

## Use

Per the protocol, the DUMP call on the next-session statement is a candidate for a **shadow report** on LEARNER v2.4's live
ledger (`paper/CALL_CERT.md`), recalibrated as v2.4's outcomes resolve; v2.4's frozen calls are not changed. The SAFE calls
and the 5-session statement are not carried forward.
