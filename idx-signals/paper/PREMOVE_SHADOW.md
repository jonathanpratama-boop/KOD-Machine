# PREMOVE_SHADOW_v1: prospective shadow trial (paper only)

Generated 2026-11-03T00:27:31Z from `paper/premove_shadow.jsonl`. Protocol `research/PREMOVE_SHADOW_v1/protocol.json`.

**What are we predicting?** Each day, which five crypto pairs (not already up 10% today or 20% this week) will close above a volatility-scaled barrier (at least +10%) before closing below the mirror barrier, within 5 days.

**What counts as success?** At the frozen end of the trial, the sequence arm beats the summary arm's early hit rate by at least 1% with a paired 95% interval above zero, and catches more distinct episodes. Order matters only if it also beats the shuffled control.

**What evidence so far?** 3 days sealed, 0 resolved. Status: accumulating. No decision is taken before the end.

Trial: decisions 2026-10-30 to 2027-10-29, final outcomes due 2027-11-05.

Latest sealed day 2026-11-02 (443 early candidates):

- summary: KAVAUSDT, BTTCUSDT, SPYBUSDT, JSTUSDT, ASTERUSDT
- sequence: BTTCUSDT, KAVAUSDT, MTLUSDT, POLYXUSDT, ASTERUSDT
- shuffled: KAVAUSDT, BTTCUSDT, STRAXUSDT, SPYBUSDT, ASTERUSDT
