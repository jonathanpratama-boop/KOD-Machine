# SEESAW_v1: does money flow tell us in advance when altcoin moonshots become common?

Written 2026-11-03, before any outcome is computed. Owner's idea: follow where the money flows (a seesaw between cash,
Bitcoin and altcoins). KOD's strongest clue is that the market tide decides profit (30% movers became a third as common after
2022), and its weakest point is seeing the tide turn in time.

## Data
- Stablecoin supply: DefiLlama `stablecoincharts/all`, total circulating USD-pegged supply, daily (saved here, sha256 in
  `stablecoins_all.sha256`).
- Prices: panel_crypto-20261008T003354Z (Binance USDT pairs, daily, delisted pairs included), 2020-01-01 .. 2026-10-07.
- Alt universe on a day: non-stable, non-leveraged pairs other than BTC, with 20-day median quote volume >= USD 1m.
Disclosure: crypto 2024+ was already largely spent by earlier KOD studies (owner-approved); 2023-2026 is a check on
already-seen prices, not a clean holdout. The flow signals themselves have never been used in KOD.

## Monthly blocks (no overlap)
Decision days: the first day of each calendar month, using only data up to the previous day.

**Signals (known at the decision day):**
- S1 stablecoin flow: % change in total stablecoin supply over the prior 30 days.
- S2 the seesaw: median 30-day return of the alt universe minus BTC's 30-day return.
- S3 breadth: share of the alt universe above its own 50-day SMA.

**Outcome (the tide, over the next 30 days):** share of the alt universe that closes >= 1.30 x the decision-day close at any
point within 30 days ("moonshot rate"); also the median alt 30-day return.

## Tests
- Development 2020-02 .. 2022-12; check 2023-01 .. 2026-09.
- For each signal: Spearman rank correlation with the next month's moonshot rate, in each period.
- The combined "tide on" rule, fixed now: S1 > 0 AND S2 > 0 (cash flowing in, and alts beating BTC). Compare the next month's
  moonshot rate and median alt return when ON vs OFF, in each period.

## Reading (fixed now)
- **Flow leads the tide**: in the check period, the "tide on" months have a higher moonshot rate than "off" months AND a
  higher median alt return, and S1 or S2 has a positive rank correlation in both periods. Then: a live monthly flow gauge for
  the analyst; prospective only.
- **Flow describes, does not lead**: correlations near zero or sign flips between periods.
Few months (about 80), so this is a direction-finding test, not proof. Counted as one exploratory test.
