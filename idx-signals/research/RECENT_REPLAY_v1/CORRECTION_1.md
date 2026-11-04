# RECENT_REPLAY_v1, correction 1 (2026-10-30): split units in two features

Found by the adversarial preflight review of TUNE_SWEEP_v1 (not by reading outcomes). The replay's price pull is
Yahoo's split-adjusted series as of 2026-10-30. Two of v2.4's 33 features were therefore computed on prices adjusted
for splits that happened after the signal session: `log_price` (from the signal close) and `log_turnover` (volume over
shares outstanding). The warm start and the live forecasts use as-traded prices, so for a name that later split the
replay fed v2.4 a different number than it would have had that evening. 344 of the 1,718 events (20%) have a split
after the signal session; 343 of those are reverse splits. The twins' price bands use the same adjusted close.

Diagnostic (v2.4's replayed raw forecasts, no refit, no new choice):

| events | n | AUC |
|---|---:|---:|
| all (the reported result) | 1,718 | 0.623 |
| no split after the signal session | 1,374 | 0.639 |
| a split after the signal session | 344 | 0.522 |

The defect did not create the reported skill: on the events it cannot touch, the AUC is higher. The reported number
stands as recorded and is superseded by `research/REPLAY_UNITS_v2`, which rebuilds the features in as-traded units
(the close times the product of later split ratios, volume divided by it) and replays v2.4 once more under the same
frozen statistic. Nothing in RESULT.json or REPORT.md is edited.
