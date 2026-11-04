# CRYPTO_PUMP_HISTORY_v1: result (one look, 2026-10-29)

Protocol `protocol.json`, run once by `run.py`; every number is in `results/RESULT.json`. Counted trial
`CRYPTO_PUMP_HISTORY_v1_result.json`, the result of the PENDING registration.

**Question.** At each organised pump on a Binance BTC pair (1,381 events kept, 32 dropped because the pumped pair had no
bars in the 24 hours before), rank every BTC pair trading then (median 178 candidates in 2020, 266 in 2021-22). Does a model
on size, the pair's earlier pumps and its recent tape put the true target higher than ranking by 30-day volume alone?
Fit 2018-19, score 2020; fit 2018-20, score 2021-22.

| Cut-off | Metric | Volume only | Full model | Chance | Gain [95%] | Verdict |
|---|---|---|---|---|---|---|
| End of the previous day | pumped coin in the top 5 | 3.5% | **10.8%** | about 2.2% | +7.2 pts [+5.1, +9.3] | **BEATS VOLUME** (Holm p 0.002) |
| End of the previous day | mean reciprocal rank | 0.045 | 0.079 | | +0.034 [+0.025, +0.045] | **BEATS VOLUME** |
| One hour before the pump hour | top 5 | 3.7% | **12.6%** | about 2.2% | +8.9 pts [+6.5, +11.4] | DOES NOT BEAT VOLUME (Brier tie) |
| One hour before the pump hour | mean reciprocal rank | 0.046 | 0.091 | | +0.045 [+0.032, +0.058] | DOES NOT BEAT VOLUME (Brier tie) |

The hourly ranking gain is larger than the daily one and its bootstrap is just as clear, but the frozen rule also requires
a lower Brier score, and at six decimals the hourly FULL and BENCH Brier scores are equal (0.004155): with one pumped pair
among about 200, the Brier score barely moves. The rule decides; the hourly cut-off is recorded as not beating volume.

## What the model learned (same signs in both folds and both cut-offs)

- **Small and young:** lower 30-day volume and a more recent listing make a pair a likelier target.
- **Pumped before, recently:** more earlier pumps and fewer days since the last one (groups return to the same coins).
- **A volume pickup in the last hour** (hourly cut-off: the 1-hour volume against the day's average, +0.20 to +0.26): someone
  buys before the announcement, as Xu and Livshits (2019) found for insider accumulation.

## What it means

- **The target can be ranked, but not named.** The pumped coin lands in the model's top 5 about one time in nine: five times
  chance and three times the volume-only ranking, far from a call. The order-book study of Bolz et al. (2024) reached 56% in
  the top 5 twenty seconds before the pump, with data KOD does not have.
- **It is a ranking skill, the kind the IDX index-review sets need**, measured here for the first time on labelled history.
- **Not live-ready.** These pumps ran on Binance BTC pairs until early 2022; the groups have moved to other venues. A daily
  watch on Binance today would see few such events.

## What it does not show

- **Live skill.** History.
- **A tradable edge.** Ranking is not entry: the pump lasts minutes and taking part is market manipulation. Paper study only.
- **Every pump.** The lists cover the groups those researchers watched.

## Use

Per the protocol, the daily cut-off is a candidate for a live crypto family riding the existing 00:23 UTC routine. Given
that the pumps it learned from have left Binance, the recommendation is not to open that family now, and to carry the
ranking method to the IDX index-review sets instead.
