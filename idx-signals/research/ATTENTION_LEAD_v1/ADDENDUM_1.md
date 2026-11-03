# ADDENDUM_1 (2026-11-03, before any page-view number was read or analysed)

Wikimedia's API rate-limits this environment's generic client to roughly one article every few minutes (HTTP 429 with
Retry-After about 20 s; the parallel fetch.py was killed before writing anything). All 1,962 articles would take days.

Change: the universe becomes a fixed random sample of 300 tickers (`sample_300.csv`, numpy default_rng(20261103), choice
without replacement over the rows of articles.csv, kept in article order), plus any article already fetched by fetch_slow.py
when it stopped. Everything else in PROTOCOL.md is unchanged. The sample was drawn from the article list only; no price or
page view was used to draw it. Expect wider uncertainty; the controls are drawn from the same sampled universe.
