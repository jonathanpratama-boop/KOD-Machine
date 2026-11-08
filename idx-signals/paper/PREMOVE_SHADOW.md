# PREMOVE_SHADOW_v1: prospective shadow trial (paper only)

Generated 2026-11-08T00:28:01Z from `paper/premove_shadow.jsonl`. Protocol `research/PREMOVE_SHADOW_v1/protocol.json`.

**What are we predicting?** Each day, which five crypto pairs (not already up 10% today or 20% this week) will close above a volatility-scaled barrier (at least +10%) before closing below the mirror barrier, within 5 days.

**What counts as success?** At the frozen end of the trial, the sequence arm beats the summary arm's early hit rate by at least 1% with a paired 95% interval above zero, and catches more distinct episodes. Order matters only if it also beats the shuffled control.

**What evidence so far?** 8 days sealed, 3 resolved. Status: accumulating. No decision is taken before the end.

Trial: decisions 2026-10-30 to 2027-10-29, final outcomes due 2027-11-05.

| Arm (early population) | Alerts | Upside hits | Censored | Hit rate | Distinct episodes |
|---|---:|---:|---:|---:|---:|
| summary | 15 | 0 | 0 | 0.00% | 0 |
| sequence | 15 | 0 | 0 | 0.00% | 0 |
| shuffled | 15 | 0 | 0 | 0.00% | 0 |

Latest sealed day 2026-11-07 (438 early candidates):

- summary: BTTCUSDT, KAVAUSDT, JSTUSDT, ASTERUSDT, RLUSDUSDT
- sequence: BTTCUSDT, KAVAUSDT, ASTERUSDT, JSTUSDT, RLUSDUSDT
- shuffled: BTTCUSDT, KAVAUSDT, JSTUSDT, RLUSDUSDT, ASTERUSDT
