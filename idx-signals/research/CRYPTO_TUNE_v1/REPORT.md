# CRYPTO_TUNE_v1: result (one confirm, 2026-10-30)

814 model scenarios fitted on 2020-2022 crypto spikes (Binance pairs closing 30%+ higher), ranked on 2023, the two
pre-chosen candidates refit on 2020-2023 and scored once on 1,131 spikes over 587 days of 2024-01..2026-10, a period
no dump study had read. Every number is in `results/CONFIRM.json`, every prediction in `results/confirm_predictions.csv.gz`.

| Model | AUC | z vs chance | top 10% own-dump rate | vs benchmark |
|---|---:|---:|---:|---|
| BEST (LightGBM, picked on 2023: 0.699) | 0.631 | 6.6 | 55.8% | +0.020, p 0.12: **not shown** |
| TOP10 average | 0.623 | 6.2 | 57.5% | +0.012, p 0.21: **not shown** |
| Benchmark (5-feature logistic) | 0.612 | 5.7 | 57.5% | |

Base rate of the next-day own dump: 39.0%.

**Verdict.** The tuned models BEAT CHANCE on unseen crypto (z 6.6), but do NOT reliably beat the simple benchmark:
the 1,470-scenario-style search bought about +0.02 AUC, inside the noise. The 2023 ranking (0.699) overstated the
tuned model by 0.07, which is what picking the best of 814 on one year does. Crypto next-day dumps are predictable from
price features alone, and a five-feature model already captures most of it.
