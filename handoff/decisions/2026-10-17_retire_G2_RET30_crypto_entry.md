# Decision 2026-10-17 (owner): retire "buy the day after a +30% day" as a crypto trading entry

Owner's words: "retire that shit. We don't chase green dildos unless it's really bullish."

Evidence: EXIT-ATR-v1 cloud run (handoff/exit-atr-cloud/RESULT.md). On 1,181 discovery trades the G2_RET30
entry underperformed matched random coins by about 3 points per 5-day trade under both the original exit
(-2.86, 95% -4.98 to -0.51) and the ATR trailing exit (-3.00, -4.54 to -1.37). E2's 2023 validation was also
negative (-1.90% vs +1.42% for matched coins). Exits cannot repair the entry.

Scope: no further exit, sizing or filter variants are run on this entry. The daily paper scans may keep
logging these days as detections (descriptive only); they were already PASS. No code or frozen result changed.
