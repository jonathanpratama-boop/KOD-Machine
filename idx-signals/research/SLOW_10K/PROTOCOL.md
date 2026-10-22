# SLOW_10K: do year-over-year changes in a US 10-K's text predict returns? (protocol)

Written 2026-10-22 and committed before any 10-K is fetched, any similarity computed or any return of these events read. Historical research only: never prospective
performance; no orders; the frozen paper cycle is untouched. The sealed US holdout (2024 onward) is never loaded: the price panel stops at 2023-12-29.

## Why this test, and what it can and cannot say
Everything tested so far in this lab was fast information (news, announcements, price spikes) and died at stage 2: by the time anyone can act, the move is priced. Slow information
does not have that problem: a filing's text can change a firm's prospects in ways the market digests over weeks or months. The published anomaly closest to this is "lazy prices"
(Cohen, Malloy and Nguyen, 2020): firms whose 10-K text changed most from last year's underperform firms whose text did not. Its published size is small, about 1-2% a quarter for the
long-short spread, mostly on the short side. **A premium that small would not matter for a small account even if it replicates**, so this protocol is a screen for a *large* effect:
the gates include a minimum economic size (a 3% spread over 60 sessions). A literature-size premium would fail it by design. The question is whether text change is a big enough signal to be
worth anything, not whether a small premium exists.

## The question, in three stages
1. Will the stock move? Not scored. 2. Can we capture it? A filing is public at its acceptance time; the first obtainable entry is the next open; after costs and capacity, is there
return that matched random entries did not earn? 3. Can the account carry it? Not tested (USD 5,000 per trade, the US profile).

## Data
- **Filings.** SEC EDGAR, form "10-K" (not 10-K/A) filings of the issuers in the US panel (below) that SEC's ticker map links to a CIK, accepted 2019-01-01 .. 2023-09-29 (the last date for which a
  60-session hold can end before the panel does). The acceptance timestamp (UTC, from EDGAR's submissions record) is the time the filing became public. The main document is downloaded, never stored
  (the store would be tens of GB); each document's URL, size and sha256 are listed in a manifest, so any value can be recomputed from a fresh download.
- **Prices.** The US repair panel `panel_us_repair-20261008T114805Z` (sha256 `8d3b7ce4be56d40b375ebac78b45be13910cbea492c29e456a417a6ae000cb4b`): Yahoo daily bars of the Nasdaq Trader listing
  of 2026-10-08, split-adjusted with as-traded unit factors, 2020-01-02 .. 2023-12-29, **survivor-only** (names delisted earlier are absent). Used by tests E2/E9 with the same harness.

## The text feature (one measure, fixed)
For a filing, strip hidden inline-XBRL header blocks, scripts, styles and tags, unescape entities, lower-case, and keep the alphabetic tokens of three or more letters. TF = the count of each
token. **Similarity** = the cosine of the filing's TF vector with the TF vector of the same issuer's previous 10-K, where the previous 10-K is the issuer's most recent earlier 10-K accepted
300 to 450 days before. A filing without such a predecessor has no similarity and is not an event. No stop-word removal, no stemming, no weighting. (A second measure, section-level similarity of
Item 1A, is not computed in this study.)

## The signal (causal)
Each filing is placed in a bucket by comparing its similarity with the similarities of all filings *accepted in the 365 days before its own acceptance time* (strictly earlier; at least 200 of them,
else the filing is not classified): **Q1 ("changers")** = similarity at or below the 20th percentile of that set, **Q5 ("stable")** = at or above the 80th, Q2-Q4 in between. No later filing
informs an earlier filing's bucket.

## Trade (the harness, unchanged: `idxsig.execution`)
Entry at the open of the first session after the acceptance time (a filing accepted before 09:30 New York time on a session day is bought at that day's open; otherwise at the next session's open);
exit at the close of the 60th session after entry (primary hold 60; 20 and 120 reported). The US profile: USD 5,000 per trade, fees 0 buy and 0.00278% sell plus the profile's per-side cost tiers by price
(1.5% below USD 1, 0.5% to USD 5, 0.15% to USD 20, 0.05% above), `ca_mode="adjusted"`, `units="as_traded"`, fill model B (shares at most 10% of the median as-traded volume of the 20 sessions up to the
signal session), `data_end_exit="last_close"`. A name that cannot be bought is skipped and counted; a filing whose exit would fall after 2023-12-29 is INCOMPLETE and not scored.

## Controls
For each event, 200 replacement draws of names that could have been bought at the same signal session in the same buckets (price band, liquidity, volatility, momentum, drawdown, listing age;
`controls.py` v2, relaxed from the last feature when fewer than 10 match; the market-cap bucket is constant for the US panel), each executed with the same plan. The control of an event is the mean net
return of its scored draws; excess = the event's net return minus its control. Seed 20261007.

## Statistics
Cluster = the ISO week of the entry session (filings bunch on deadline days). 10,000 bootstrap resamples of weeks (seed 20261201), one fixed set of resampled weeks for every statistic so that a
difference between buckets sees the same weeks. **Spread** = mean excess of Q5 minus mean excess of Q1 (the published long-short measure); t = spread over its bootstrap standard error.

## Stages
- **Stage 1 (discovery):** filings accepted 2021-01-04 .. 2022-12-30 (signal sessions in 2021-2022). Needs 2019-2020 filings for similarities and for the trailing distribution.
- **Stage 2 (out of time):** filings accepted 2023-01-03 .. 2023-09-29. Run **only if Stage 1 passes**.

## Gates, Stage 1 (PASS only if all four hold; hold 60)
- **G1** spread > 0 with bootstrap t >= 3.0 (the project hurdle for a new test; counted test 26 in the register).
- **G2** spread >= 3.0% (a screen for an effect big enough to matter).
- **G3** spread > 0 in each of 2021 and 2022 (years of the entry session, at least 200 scored events per quintile in the year).
- **G4** (method check) 20 shuffles of the Q1/Q5 labels within each filing month give spreads with every |t| < 3.0.
**GO rules (counts only, before the run):** at least 1,000 scored (EXITED) events in each of Q1 and Q5 in Stage 1; else the run is not made and the shortfall is reported.

## Gates, Stage 2 (PASS only if both hold; hold 60)
**G1'** spread > 0 with t >= 1.65 (one-sided 5%: a replication of one pre-specified effect); **G2'** spread >= 1.5%. Counted as test 27.

## Reported whatever the verdict (descriptive; 3 variants counted in the register)
Holds 20, 60, 120: scored events, mean net, mean excess, t for Q1 to Q5 and the spread; status counts; results by year and by the filer's price band; the share of Q1 and Q5 events among
all filings; the mean similarity per bucket; the correlation between similarity and the filing's length ratio.

## How the result will be read (fixed now)
- **Stage 1 PASS**: a large text-change effect exists in 2021-2022; Stage 2 decides whether it persisted. **Stage 1 and 2 PASS**: a large, persistent effect in survivor-only data; next steps are a
  survivorship-complete check and a forward watch of new 10-K filings (read-only); nothing real. Note that the practical side is the short leg (Q1 underperforming), which a small account
  can use only by avoiding such names or through instruments the owner may not have.
- **Stage 1 FAIL with spread > 0 and t >= 1.5**: a lean without the size to matter; no Stage 2.
- **Otherwise**: no large text-change effect in these data; the question is closed for effects that matter to a small account.
No rerun after the result: any change is a new experiment with its own protocol.

## Limits (stated before the result)
- Survivor-only prices: changers that failed and delisted are missing, which pushes Q1's measured return up and the spread down (conservative for a positive finding, ambiguous for a null).
- Two years of discovery, one market regime (2021 boom, 2022 bear); the spread of a small effect is not detectable here, by design.
- A 10-K often coincides with an earnings release; matched controls do not remove earnings surprise. Similarity of the whole document is dominated by boilerplate and by format changes (inline XBRL
  since 2019-2021); the trailing-365-day bucketing removes common shifts but not firm-specific formatting changes.
- The filer must be in today's Nasdaq Trader listing and SEC's current ticker map; delisted issuers are absent.
