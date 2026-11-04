# CRYPTO_PUMP_HISTORY_v1: can the machine tell which coin an organised pump will pick?

Frozen 2026-10-29 after a counts-only feasibility check and before any price was read. `protocol.json` is normative.

**Why.** An organised pump announces its *time* and hides its *coin*: a scheduled catalyst with an unknown target, the mirror
image of every event family KOD has run. Three public research lists record 1,413 Binance BTC-pair pumps (2018 to February
2022); the Binance archive still has hourly bars for every pair, removed ones included.

**Question.** At each pump, rank every BTC pair trading then. Does a model on size, the pair's earlier pumps and its recent
tape put the true target higher than ranking by 30-day volume alone? Twice: with what was known at the end of the
previous day, and one hour before the pump hour.

**Out of time.** Fit 2018-2019, score 2020; fit 2018-2020, score 2021-22. Top-5 hit rate and mean reciprocal rank,
bootstrap over pump days, Holm over four tests, Brier beside it. One run (`run.py`), counted.
