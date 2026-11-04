# Catalyst-side warm start with the 13D pool fixed

Open item since `../ADDENDUM_3.md`: the v2.2 warm start's 90-day counts (earlier events on the same ticker) drew 13D filings
only from the 1,188 the kill test went on to score, a set that depends on prices after each filing. `build.py` recounts from
the full collection (2,750 filings with a ticker, of 4,857 collected) and changes nothing else.

**Result: 170 of 5,587 rows (3.0%) change** (92 13D, 56 Form 4, 22 8-K Item 3.02). The mean 90-day repeat count rises from
0.059 to 0.086 and the corroboration count from 0.040 to 0.056: the leak hid earlier 13D filings, it did not invent them.

**Use.** LEARNER v2.2 is frozen and monitoring only; it is not refitted. This corrected file (`events.csv.gz`, hashed in
`BUILD.json`) is the warm start for the next catalyst-side learner version when one is opened. One live challenger at a time
(LEARNER v2.4, on the US spike question) stays the rule, so no new catalyst learner is opened now.
