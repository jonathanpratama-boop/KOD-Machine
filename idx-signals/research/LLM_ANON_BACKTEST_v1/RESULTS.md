# LLM_ANON_BACKTEST_v1: results

Scored 2026-11-07 (WIB) with `python3 abt.py score`, after the calls were stamped (freetsa and sectigo, 2026-11-06 17:48 UTC;
the protocol, code, anonymised features, key and benchmarks were stamped at 17:45 UTC, before any judging).
264 anonymised events (150 IDX, 114 crypto), judged by 24 separate Claude instances of 11 events each, numbers only.
259 events were scorable; 5 were not (a missing or gapped bar five sessions later).

**Pass test: not passed.**

| Statement (pooled, n = 259) | Brier: judge | base rate | logistic | judge minus base (95% interval) |
|---|---:|---:|---:|---|
| RUN30_5 | 0.1683 | 0.1661 | 0.1690 | +0.0022 (+0.0008 to +0.0035), judge slightly worse |
| FADE10_5 | 0.2224 | 0.2246 | 0.2242 | -0.0022 (-0.0056 to +0.0005), not different from zero |
| GAIN0_5 (reported only) | 0.2271 | 0.2265 | 0.2301 | +0.0006 (-0.0015 to +0.0025), not different from zero |

Against the logistic model the judge is also within noise on all three (differences of -0.003 to +0.001, every interval
spanning zero). Lower Brier is better.

**Calls:** 161 AVOID, 103 ABSTAIN, 0 BACK. The BACK-versus-AVOID comparison was not evaluable (needs 20 BACK calls).

## What it says

- The judge was no better than the base rate, and no better than a numeric model fitted on 5,500 older events.
- The logistic model was itself no better than the base rate. So the seven numbers describing a spike day carry almost no
  information about the next five days in these markets. The LLM had little to read.
- This does not test the live `LLM_ARM_v1` question. That test gives the LLM news and filings, which this one withheld.
- Weaknesses (see PROTOCOL.md): one regime of about three months, overlapping events, a flat cost and IDX limit-up fills that
  flatter any buying rule, and a judge that was told to stay near base rates when unsure.
