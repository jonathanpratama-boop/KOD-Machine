# FRESH_SHORT_v1, correction 1 (2026-10-30): the replay ran with the split-unit defect; the short test is not run

The replay (`results/`) completed before the defect described in `research/RECENT_REPLAY_v1/CORRECTION_1.md` was
confirmed: 389 of the period's 1,080 events have a split after the signal session. Its v2.4 AUC as recorded: 0.655
(0.662 on the 691 events no later split touches, 0.595 on the 389 it does). The frozen paper short (`short.py`) is NOT
run on these forecasts: it reads the certified calls, whose bar depends on the defective features. The short test and
the replay are re-run once on as-traded features in `research/REPLAY_UNITS_v2`, under the same frozen rules
(`short_rules.json`, copied unchanged).
