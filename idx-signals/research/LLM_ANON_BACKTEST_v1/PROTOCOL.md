# LLM_ANON_BACKTEST_v1: can an LLM beat a simple numeric model on anonymised spike numbers?

Written 2026-11-07 (WIB) by Claude for the owner. Exploratory and separate from `LLM_ARM_v1`, which stays frozen and
untouched. Owner decision, 2026-11-07: no architect sign-off is required for this experiment. Paper only; nothing is traded.

## Question

Given only anonymised numbers about a one-day spike (no ticker, no date, no news), does an LLM's probability judgement
beat (a) the base rate and (b) a simple logistic model fitted on older events, when scored on spikes from July to
September 2026?

A positive result would only say the LLM reads price numbers well. It would not show the LLM adds information beyond
KOD's numbers, because it sees the same numbers. The live test (`LLM_ARM_v1`) is where news and filings come in.

## Data

Daily price panels already in the repository: `data/panel/panel-20261007T225823Z.csv.gz` (IDX) and
`data/panel/panel_crypto-20261008T003354Z.csv.gz` (crypto). US is left out: the live scanner's US rules are not
reproduced here, and a crude filter found too few events.

A "session" is a row for that ticker in the panel. This is an approximation: a day with no trade has no row.

## Events (fixed now, before any outcome is computed)

Signal day `s` is a row where:

- IDX: close / previous - 1 >= 0.20, close >= 0.999 x high, and traded value >= 100,000,000 IDR.
- Crypto: close / previous - 1 >= 0.30 and traded value >= 1,000,000 (quote currency).
- The ticker had no qualifying row in the 5 rows before it (a "fresh" event).
- At least 20 rows of history before `s`.

Test window: signal days 2026-07-01 to 2026-09-22 (so five-day outcomes fit before the panel ends on 2026-10-06).
Training window: signal days up to 2026-06-30, with a complete five-day outcome.
If a market has more than 150 test events, 150 are drawn at random with seed 20261107. Otherwise all are used.

## What the judge sees (computed from rows up to and including `s` only)

`market`, `ret1`, `ret5`, `ret20` (close-to-close returns to the signal close), `volr` (traded value / mean value of the
previous 20 rows), `cpos` ((close - low) / (high - low); 1 when high equals low), `dd60` (close / highest close of the last
60 rows, minus 1), and `adv20_log10` (log10 of the 20-row mean traded value). No ticker, date, name, price level or
news. Events carry random ids; the id-to-event key is kept in a separate file that judges never receive.

## Statements judged (the same three as the live test, simplified)

Entry is the close of the next session `s+1`. With `c0` the close on `s`:

- `RUN30_5`: the highest close over rows s+1..s+5 is >= 1.30 x `c0`.
- `FADE10_5`: `close[s+6] / close[s+1] - 1 - 0.015 <= -0.10` (a flat 1.5% round-trip cost, an assumption of this test).
- `GAIN0_5`: the same net return is > 0.

An event is unscorable if `s+6` is missing or more than 20 calendar days after `s` (a suspension or data gap).
Unscorable events are counted and reported, and left out of scoring. This can bias the results; it is disclosed, not fixed.
Locked-limit-up fills on IDX are ignored (the live frozen plan treats them as unfillable). That makes the IDX net returns here optimistic.

## Judge output

For each event: `call` (BACK, AVOID or ABSTAIN), and probabilities for the three statements, each between 0.02 and 0.98.
Judges are told the base rates measured on the training window for that market and are told not to use any outside
information about the event. Judges are separate Claude instances given 10 shuffled events at a time.

## Benchmarks (fitted on the training window only)

1. Base rate: the training frequency of each statement, per market.
2. Logistic: an L2-regularised (lambda 1.0) logistic regression per market and statement on standardised
   `ret1, ret5, ret20, log(volr), cpos, dd60, adv20_log10`, fitted by Newton's method in numpy.

## Scoring (fixed now)

- Brier score of the judge, the base rate and the logistic model on scorable test events, per market and pooled.
- Paired difference in Brier (judge minus benchmark) with a bootstrap 95% interval (10,000 resamples, seed 20261107).
- **Pass:** on both RUN30_5 and FADE10_5, pooled over both markets, the judge's Brier is lower than the base rate's and the
  logistic's, with the upper end of the one-sided 95% bound below zero for each comparison. `GAIN0_5` is reported only.
- BACK versus AVOID: the difference in mean net five-day return (BACK minus AVOID) with a bootstrap 95% interval.
  Evaluated only if there are at least 20 BACK calls; otherwise reported as "not evaluable".
- Results are reported whether positive or negative. Nothing here changes `LLM_ARM_v1`.

## Integrity

The outcomes already exist in the panel, so this test cannot be made tamper-proof by data embargo. It is controlled by
order and by timestamps. Before any judging, this protocol, the code, the test features file and the training summary are
hashed and stamped with RFC 3161 (freetsa and sectigo). The calls file is stamped before the outcomes file is generated.
The scoring script is the only place outcomes are read for test events, and it is run after the calls are stamped.

## Known weaknesses

Anonymised numbers give the LLM little to work with. A flat result is the most likely. Many events share days, so they
are not independent. The cost and limit-up simplifications flatter the strategy. The sample is about three months of one
market regime.
