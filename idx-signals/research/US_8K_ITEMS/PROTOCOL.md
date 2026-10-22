# US_8K_ITEMS: do the item types of US 8-K filings predict returns after the filing date? (protocol)

Written 2026-10-22 and committed before any 8-K list is fetched, any event counted or any return read. Historical research only; no orders; the frozen paper cycle is untouched; the sealed
US holdout (2024 onward) is never loaded (the panel stops at 2023-12-29). The Blueprint's third idea ("8-K filings that arrive before the price moves"), run as a screen with the machinery of
SLOW_10K and US_INSIDER_BUY (same panel, harness, controls, cost tiers, entry rule).

## Question
After an 8-K of a given item type is filed, does the stock earn more than matched random stocks over the next 5, 20 or 60 sessions, when bought at the first obtainable entry (the open of the first
session strictly after the filing date)? Fast news is priced quickly and most of this family is expected to show nothing; the study asks whether any item is the exception, with the multiple
testing counted.

## Data
- Filing lists: EDGAR submissions JSON (`data.sec.gov/submissions/CIK##########.json` and its older chunk files) for the issuers in SLOW_10K's committed `filings.csv.gz` (10-K filers in the US
  repair panel with a CIK; one ticker per CIK). Form exactly "8-K" (not 8-K/A), filing date 2020-06-01 .. 2023-09-29, with the `items` field. Only the list is kept (`filings8k.csv.gz`); each response's
  URL, size and sha256 go into `data/manifests/sec_8k_filings-<stamp>.json`. Contact from `KOD_SEC_CONTACT`, never written to a file. The filing date is the public date (acceptance times are unreliable,
  SLOW_10K ADDENDUM_1); entry is the open of the first session strictly after it, so same-day reactions are not captured, by design.
- Prices: US repair panel `panel_us_repair-20261008T114805Z` (sha256 `8d3b7ce4be56d40b375ebac78b45be13910cbea492c29e456a417a6ae000cb4b`), survivor-only, to 2023-12-29.

## Items and events (fixed)
Nine item types: **1.01** material agreement, **1.02** agreement terminated, **2.02** results of operations, **2.03** direct financial obligation, **3.02** unregistered equity sales, **5.02**
officer/director change, **5.07** shareholder vote, **7.01** Regulation FD, **8.01** other events. A filing lists several items; it is a candidate event for each listed item of the nine. Per issuer and
item, filings are chained in date order from 2020-07-01: a filing is an event unless the same issuer already has an event of that item less than 30 days earlier. Stage 1 = filing dates
2021-01-04 .. 2022-12-30; Stage 2 = 2023-01-03 .. 2023-09-29. Earlier filings only seed the chain.

## Trade, controls, statistics (as US_INSIDER_BUY/PROTOCOL.md, unchanged)
Harness, US profile, USD 5,000, cost tiers, fill model B, entry at the next open, 200 matched controls per event (seed 20261007), excess = net return minus control mean, week-cluster bootstrap (10,000
resamples, seed 20261204). **Primary hold 20**; holds 5 and 60 are reported and used in G4. An event whose name cannot be bought is skipped and counted. The same company may be an event for several
items on the same filing; items are analysed separately.

## Gates, Stage 1 (per item; an item PASSES only if all four hold; hold 20)
- **G1** mean excess > 0 with bootstrap t >= 3.6 (the project hurdle for a family of 9 items x 3 holds = 27 variants; counted test 27).
- **G2** mean excess >= 1.0% and winsorised (1st/99th percentile) mean excess >= 0.5%.
- **G3** mean excess > 0 in each of 2021 and 2022 (entry year, at least 100 scored events each).
- **G4** mean excess > 0 at holds 5 and 60 too.
**GO rule (counts only):** an item with fewer than 500 scored Stage 1 events at hold 20 is not testable and is reported as such; if no item reaches 500 the run is not made. The study verdict is PASS if any
item passes; the passing items are named.

## Stage 2 (only for items that passed Stage 1; hold 20)
t >= 1.65 with mean excess > 0 and >= 0.5%. Counted as test 28 when run.

## Reported whatever the verdict (descriptive; counted in the 27 variants)
All items x holds 5, 20, 60: scored events, mean excess, t, winsorised mean, hit rate; by year. Items with t <= -3.6 are listed as negative (a small account can only use that as a reason to avoid).

## Reading (fixed now)
PASS item(s): a fast-news effect large enough to matter in survivor-only data (a lead, never a confirmation; Stage 2 decides persistence). No item passes: no 8-K item type is a usable signal at
this entry; the idea is closed. No rerun; changes are new experiments.

## Limits
Survivor-only prices (events that led to failure are missing, biasing positives up); filing-date entry misses same-day and, for pre-market filings, the whole reaction; items overlap in a filing
(2.02 usually comes with 9.01 exhibits and 7.01); 8-K list limited to 10-K filers in today's listing; 27 variants make a chance t of 3 likely somewhere, hence the 3.6 hurdle.
