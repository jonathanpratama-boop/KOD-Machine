# SLOW_10K: addendum 1 (timing uses the filing date, not the acceptance timestamp)

Written 2026-10-22 and committed before any filing is fetched. `PROTOCOL.md` governs everything not changed here.

## Why
`PROTOCOL.md` times an entry by the filing's acceptance timestamp. Test E9 found that the acceptance field of EDGAR's submissions JSON mixes UTC readings and New York readings converted to UTC twice
(`research/E9/FEASIBILITY_AMENDMENT_3.md`; the reliable source is each filing's own SGML header, one more request per filing). A wrong convention would let an entry precede the information.

## The change (timing only)
- **Entry** = the open of the **first session strictly after EDGAR's `filingDate`** (a calendar date; EDGAR dates a filing accepted up to 17:30 New York time with that day and a later one with the next
  business day). Whatever the timestamp convention, the filing is public before that open. This is slower than the protocol's rule for filings made before the open (they are bought one session
  later), which is irrelevant to a 60-session drift and keeps the first-day reaction out of the test.
- **Trailing set for the buckets** = filings with `filingDate` strictly earlier than this filing's `filingDate` and not more than 365 days before it (at least 200, else the filing is not classified).
- **Previous 10-K** = the issuer's earlier 10-K with `filingDate` 300 to 450 days before this one's (the closest to 365 days if several).
- **Stage windows** are by `filingDate`: Stage 1 2021-01-04 .. 2022-12-30, Stage 2 2023-01-03 .. 2023-09-29, and the filings considered start at 2019-01-01.

Everything else (the text measure, the buckets' percentiles, the harness and profile, the controls, the statistics, the gates, the GO rules, the reading rules, the sealed 2024+ holdout) is unchanged.
