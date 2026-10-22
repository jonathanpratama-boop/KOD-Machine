# US_INSIDER_BUY: do open-market purchases by US company insiders, reported on SEC Form 4, predict returns after the filing? (protocol)

Written 2026-10-22 and committed before any Form 3/4/5 record is fetched, any event counted or any return of these events read. Historical research only: never prospective
performance; no orders; the frozen paper cycle is untouched. The sealed US holdout (2024 onward) is never loaded: the price panel stops at 2023-12-29. This is the next step of
`handoff/BLUEPRINT.md` ("Open decisions and the next step"), applied on the owner's instruction of 2026-10-22 (`handoff/decisions/2026-10-22_close_US_plus30_line_and_take_the_blueprint_next_step.md`).

## Why this test, and what it can and cannot say
Every earlier test in this lab was fast information (price spikes, announcements, news) and died at stage 2: by the time anyone can act, the move is priced. An insider purchase is
different in two ways: the filing is public within two business days of the trade (an SEC rule, not something tested here), and published studies report abnormal returns after
insider purchases that build over months, larger for small firms (Lakonishok and Lee 2001; Jeng, Metrick and Zeckhauser 2003; sizes not re-checked here, and recent samples are
said to show less). The Blueprint rates it "a weaker fit to an early moonshot warning".

**This protocol is a screen for a large effect.** SLOW_10K measured the spread of this harness's 60-session excess returns on a comparable universe: standard deviation 25% per
event, week-cluster standard errors between 1.0 and 1.9 times the naive ones (1.25 on average over its five buckets). With about 2,500 scored events the standard error of the mean
excess is therefore about 0.65%, so the project hurdle t >= 3.0 needs a mean excess of about 2%. A literature-size premium of about 1% would not pass, by design. The question is whether insider buying is a big enough signal to be
worth anything to a small account, not whether a small premium exists.

## The question, in three stages
1. Will the stock move? Not scored. 2. Can we capture it? The filing is public on its filing date; the first obtainable entry is the open of the next session; after costs and
capacity, is there return that matched random entries did not earn? 3. Can the account carry it? Not tested (USD 5,000 per trade, the US profile).

## Data
- **Insider records.** The SEC "Insider Transactions Data Sets" (Forms 3, 4 and 5 as tab-separated tables in one zip per quarter, `https://www.sec.gov/files/structureddata/data/form-345/<year>q<n>_form345.zip`),
  the 14 quarters 2020q3 .. 2023q4. Tables used: SUBMISSION (filing date, document type, issuer CIK, the 10b5-1 flag where the table has it), REPORTINGOWNER (relationship and title)
  and NONDERIV_TRANS (the transaction lines). Each zip is downloaded once and read in memory; the rows the rules below keep are written to `form4_purchases.csv.gz` (committed), and each zip's URL,
  size and sha256 go into `data/manifests/sec_form345-<stamp>.json`. The SEC contact is read from `KOD_SEC_CONTACT` and never written to a file.
- **Prices.** The US repair panel `panel_us_repair-20261008T114805Z` (sha256 `8d3b7ce4be56d40b375ebac78b45be13910cbea492c29e456a417a6ae000cb4b`): Yahoo daily bars of the Nasdaq Trader listing
  of 2026-10-08, split-adjusted with as-traded unit factors, 2020-01-02 .. 2023-12-29, **survivor-only** (names delisted earlier are absent).
- **Identity.** The filing's issuer CIK, linked to the panel ticker by SLOW_10K's committed `filings.csv.gz` (one ticker per CIK: the one with most panel rows). An issuer with no 10-K
  in 2019-01-01 .. 2023-09-29, no entry in the SEC ticker map of 2026-10 or no panel ticker is not an event (counted, not hidden).

## What counts as a purchase (fixed)
A **purchase line** is a NONDERIV_TRANS row of a Form 4 (DOCUMENT_TYPE exactly "4"; "4/A" is not used) with TRANS_CODE "P" (open-market or private purchase) and
TRANS_ACQUIRED_DISP_CD "A", whose SECURITY_TITLE names common equity (a whole word of `common`, `ordinary`, `class <letter>`, `capital stock`, `share(s)` or `stock`, and none of
`preferred`, `warrant(s)`, `option(s)`, `note(s)`, `debenture(s)`, `convertible`, `bond(s)`, `depositary`, `unit(s)`, `right(s)`, case-insensitive), with TRANS_SHARES > 0 and
TRANS_PRICEPERSHARE > 0; its value is shares x price. A **purchase filing** is a Form 4 with at least one purchase line, at least one reporting owner whose RPTOWNER_RELATIONSHIP names
Director or Officer (a filing whose owners are only 10% holders or "Other" is dropped), no 10b5-1 flag (AFF10B5ONE = 1, where the table has the column), and purchase lines
totalling at least **USD 50,000**.

## Events (fixed)
Purchase filings whose issuer maps to a panel ticker, taken in filing-date order from 2020-07-01 and **chained per issuer**: a purchase filing is an event unless the same issuer
already has an event with a filing date less than 90 days earlier (so events of one issuer are at least 90 days apart and a 60-session hold never overlaps the next). The public date
is the FILING_DATE (the data sets carry no acceptance time, and EDGAR's acceptance clock was found unreliable in E9 and SLOW_10K ADDENDUM_1); the entry is the open of the first session strictly after
that date, so the reaction on the filing day itself is not captured, by design. **Stage 1** = filing dates 2021-01-04 .. 2022-12-30; **Stage 2** = 2023-01-03 .. 2023-09-29 (the last date
for which a 60-session hold can end before the panel does). Filings from 2020-07-01 to 2021-01-03 only seed the chain.

## Trade (the harness, unchanged: `idxsig.execution` through `idxsig.event_study`)
Entry at the open of the first session after the filing date; exit at the close of the 60th session after entry (primary hold 60; 20 and 120 reported). The US profile: USD 5,000 per trade,
fees 0 buy and 0.00278% sell plus the profile's per-side cost tiers by price (1.5% below USD 1, 0.5% to USD 5, 0.15% to USD 20, 0.05% above), `ca_mode="adjusted"`, `units="as_traded"`,
fill model B (shares at most 10% of the median as-traded volume of the 20 sessions up to the signal session), `data_end_exit="last_close"`. A name that cannot be bought is skipped and
counted; an event whose exit would fall after 2023-12-29 is INCOMPLETE and not scored.

## Controls
For each event, 200 replacement draws of names that could have been bought at the same signal session in the same buckets (price band, liquidity, volatility, momentum, drawdown, listing age;
`controls.py` v2, relaxed from the last feature when fewer than 10 match; the market-cap bucket is constant for the US panel), each executed with the same plan. The control of an event is the mean
net return of its scored draws; excess = the event's net return minus its control. Seed 20261007. Controls are not matched on earnings timing or on size beyond what price and liquidity carry.

## Statistics
Cluster = the ISO week of the entry session (filings bunch on deadlines and after earnings). 10,000 bootstrap resamples of weeks (seed 20261203). **Mean excess**; t = mean over its bootstrap standard
error. Winsorised mean excess = the mean after clipping the scored excess at its 1st and 99th percentiles.

## Gates, Stage 1 (PASS only if all four hold; hold 60)
- **G1** mean excess > 0 with bootstrap t >= 3.0 (the project hurdle for a new test; counted test 26 in the register).
- **G2** mean excess >= 2.0% and winsorised mean excess >= 1.0% (big enough to matter, and not carried by a few outliers).
- **G3** mean excess > 0 in each of 2021 and 2022 (year of the entry session; at least 300 scored events in each).
- **G4** mean excess > 0 at hold 20 and at hold 120 as well (an effect that flips sign between neighbouring holds is not an effect).

**GO rules (counts only, before the run):** at least 1,500 scored (EXITED with at least one scored control draw) Stage 1 events at hold 60, and at least 300 in each of 2021 and 2022; else the
run is not made and the shortfall is reported. A threshold changed after seeing counts (never returns) is a dated addendum.

## Gates, Stage 2 (PASS only if both hold; hold 60)
Run **only if Stage 1 passes.** **G1'** mean excess > 0 with t >= 1.65 (one-sided 5%: the replication of one pre-specified effect); **G2'** mean excess >= 1.0%. Counted as test 27.

## Reported whatever the verdict (descriptive; 8 variants counted in the register)
Holds 20, 60 and 120 (3). At hold 60: officers with a top-executive title (CEO, CFO, chief executive or financial officer, President) against all other filers (2), and purchase size
USD 50-100k, 100-500k, 500k+ (3). Also status counts, results by year and by price band, the lag between the last trade date and the filing, and the funnel from lines to events.

## How the result will be read (fixed now)
- **Stage 1 PASS**: a large insider-purchase effect exists in 2021-2022 in survivor-only data; Stage 2 decides whether it persisted. **Stage 1 and 2 PASS**: a large, persistent effect in
  survivor-only data, which can fail a test but cannot confirm one; next steps are a survivorship-complete check (prices of delisted names from a source the owner approves) and a forward,
  read-only watch of new filings; nothing real.
- **G1 holds but another gate fails**: a real but small or unstable effect; no Stage 2.
- **Mean excess > 0 with 1.5 <= t < 3.0**: a lean without the size to matter; no Stage 2.
- **Otherwise**: no insider-purchase effect that matters to a small account in these data; the question is closed at this size.
No rerun after the result: any change is a new experiment with its own protocol.

## Limits (stated before the result)
- Survivor-only prices: insiders who bought firms that later failed and delisted are missing from events and controls alike, but the events are the more failure-prone group, so the bias pushes the
  measured excess up (for a positive finding it is a lead, never a confirmation; for a null it is conservative).
- Entry at the next open after the filing date loses the filing day's reaction; the trade itself happened up to two business days earlier.
- Two years of discovery, one boom and one bear regime; an excess below about 2% cannot be detected, by design.
- Matched controls do not remove post-earnings timing (insiders buy when the trading window reopens) or size effects beyond price and liquidity.
- The bulk tables are filer-reported; rows with a missing or non-positive price or share count are dropped, and the title rule can misclassify a rare security.
- The issuer must have a 10-K in 2019-2023 and appear in today's SEC ticker map and Nasdaq Trader listing; delisted issuers are absent.
