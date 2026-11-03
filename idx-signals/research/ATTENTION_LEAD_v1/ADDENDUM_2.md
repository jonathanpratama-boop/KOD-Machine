# ADDENDUM_2 (2026-11-03, before any page-view number was read or analysed)

The per-article API stayed throttled (49 of 300 sample articles in ~6 hours; HTTP 429, Retry-After ~35 s). Wikimedia
publishes the same counts as bulk monthly files, which this environment can download at ~5 MB/s without throttling.

Change of source: `dumps.wikimedia.org/other/pageview_complete/monthly/YYYY/YYYY-MM/pageviews-YYYYMM-user.bz2`,
2020-06 .. 2023-12. Lines `en.wikipedia <title> <page_id> <access> <total> <daily counts>`; the daily counts are summed over
the access methods (desktop, mobile-web, mobile-app) = the API's "all-access / user". Titles match the API's (spaces as
underscores, no redirect following). Fetcher: `fetch_dump.py`; it writes `pageviews.csv.gz` in the same columns.

Universe: back to the PROTOCOL's full article list (articles.csv, 1,962), since ADDENDUM_1's only reason (throttling) is gone.
The 300-ticker sample result is also reported, as a subset, so ADDENDUM_1's design is not discarded.

Validation gate (before run.py): for every article the API already returned (pv_raw.jsonl, status 200), compare dump and API
daily views. If fewer than 95% of article-days match exactly, stop and report; do not run.
Everything else in PROTOCOL.md is unchanged.
