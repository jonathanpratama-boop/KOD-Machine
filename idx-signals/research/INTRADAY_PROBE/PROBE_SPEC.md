# Intraday data probe (feasibility only)

Written 2026-10-18, before any intraday data for these names and dates is fetched. Owner instruction: a
bounded probe of access, historical identities, coverage, quote freshness, halts and costs. **No strategy
return is computed**, no reserved outcome is opened (2024 onward stays sealed), and no gap-and-go, post-halt or
multi-week guidance experiment is started. The published opening-range rule (opening range + unusual opening
volume) is a starting specification for a later study, not validated performance for our implementation.

## Fixed sample (`sample.py`, seed 20261018)
- 12 regular sessions drawn from 2020-07-01..2022-12-30 (the already-used discovery era).
- Per date: 30 names drawn from the US repair panel names that traded that day, stratified 10/10/10 by
  20-session median traded value tercile (as-traded close >= USD 1). The panel is today's listings only, so:
- plus a fixed identity set chosen now for known identity problems, probed on every date:
  FB (Meta, ticker reused later), TWTR (delisted 2022-11), BBBY (delisted 2023), ATVI (acquired 2023),
  SIVB (failed 2023), FRC (failed 2023), DWAC (renamed DJT 2024), SQ (renamed XYZ 2025), SNDL, MRAM.

## Checks per (name, date)
1. Consolidated (SIP) 5-minute bars: count of the 12 first-hour bars and the 78 regular-session bars returned.
2. IEX 5-minute bars and IEX trades in the first hour: trade count, longest gap between trades.
3. IEX quotes in the first hour: update count, longest time a quote stood unchanged (freshness).
4. Official halts: Nasdaq halt history for the date (symbol, reason, halt and resume times). A missing or
   zero-volume bar is never read as a halt; an unexplained gap is recorded as UNKNOWN.
5. Identity: the provider's asset record today (status, name, class) next to the panel's or SEC's name for
   that date; a mismatch (e.g. FB now an ETF) is recorded, not resolved by guess.

## Separately recorded, never mixed
- Historical consolidated availability (the research data);
- live availability (free live feed is IEX only; consolidated is delayed >= 15 minutes);
- executable broker quotes (eToro): not measurable here; requires the owner's account facts (legal entity,
  commission shown in the trade ticket, API eligibility). Blocks any execution claim, not this probe.

## GO for designing one delayed intraday study if all hold
- SIP first-hour bars present for >= 95% of sampled (name, date) pairs that traded that day;
- the identity set resolves to the right historical security in every case, or each failure is explainable
  and can be handled by a point-in-time identity source;
- official halt records exist for every sampled date;
- a written plan for quote freshness: either IEX quotes are fresh enough in the liquid terciles, or the
  study restricts itself to what a delayed consolidated feed allows.
Otherwise NO-GO, with the missing requirement named.
