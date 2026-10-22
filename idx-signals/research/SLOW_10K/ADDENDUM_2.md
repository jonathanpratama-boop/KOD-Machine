# SLOW_10K: addendum 2 (a correction to a factual claim in PROTOCOL.md; no design change)

Written 2026-10-22 and committed before any filing's similarity is computed.

`PROTOCOL.md` says the published size of the "lazy prices" long-short spread is "about 1-2% a quarter, mostly on the short side" and builds on it the remark that a literature-size premium would
fail the 3% gate "by design". That figure was written from memory and is probably too low. As I remember the paper's abstract (Cohen, Malloy and Nguyen, 2020), the best long-short specification
earns up to 188 basis points a month in abnormal returns (over 22% a year), with smaller figures for other weightings and after factor adjustments. I could not check the paper from this environment,
so the number is not reliable in either direction.

**Nothing in the design depends on it.** The gates are a statement about economic relevance (a spread of at least 3% over 60 sessions, and t >= 3.0), chosen before the published size was looked at; the
sample and the measure are unchanged; the run is what it was. The consequence for reading the result is only this: if the effect is anywhere near the best published figure, this sample (about 1,000 or
more scored events per bucket) has high power to see it; if it is the small end of the published range, a miss is expected and says nothing against the paper. A pass or a miss is reported against
the gates as written, not against a literature number.
