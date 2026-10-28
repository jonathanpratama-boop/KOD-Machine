# MOVERS_NOW_v1: what came before 30%+ rises in the current market, and does it hold up?

Written 2026-10-27. Goal (owner): catch 30%+ rises early. Paper only.

## Exploration (done, stated openly), learn window 2025-01-02 .. 2026-03-31
For every tradable name-day (IDX: 20-day median value >= IDR 1bn; US and crypto: eToro-listed, >= USD 1m/day, US price >= $1), the label is whether
the close rose 30%+ at any point in the next 20 sessions, and whether it fell 23%+ (the matching fall). About 20 single signs and combinations were
looked at (study.py tables). US: every sign that raised the odds of a rise raised the odds of a fall as much or more. Crypto: no sign separated
up from down; market-wide mood dominated. IDX: two candidates tilted up:
- **R1 momentum**: close >= 99% of its 60-session high AND 20-session return >= +15%. Learn, through the IDX harness (hold 20, buy next close,
  fees 0.15%/0.25%): 936 trades, mean net +5.0%, median -1.6%; vs same price band and liquidity on the same day (baseline B) +2.7% (week-cluster
  t 2.39), median -3.4%; vs similar-momentum controls (baseline A) -0.1%. The top 10 trades carry two-thirds of the excess.
- **R2 dilution news before the move**: an EmitenNews headline naming the stock with a rights-issue or private-placement phrase
  (idxsig.sensors.dilution_kinds) dated 1-7 calendar days before t, AND |20-session return| < 10% AND close < 95% of the 60-session high.
  Learn (rows, not harness): 263 name-days, 85 name-months; up30 19.8%, dn30 11.8%, against 8.5% / 6.0% for all not-yet-moved names.

## The one check: signals dated 2026-04-01 .. 2026-09-08, run once through harness_idx.py (same plan, same baselines)
Signals: first qualifying session, then at most one per name per 20 sessions.
- A rule **holds up** if its mean excess over baseline B is > 0 with week-cluster bootstrap t >= 1.65.
- Also reported: mean and median net, share of trades +30% gross at exit, share -20% net, excess over baseline A, by month.

## Reading
Holds up: a lead for a forward paper watch, never a confirmation (one short window, survivor-only Yahoo-era prices, weak corporate-action coverage
after 2025-02-21). Does not hold up: say so; no rerun with changed thresholds. R2 will have few signals; a fail there is weak evidence either way.
Seen before writing this: the market-wide monthly 30% rise/fall rates through 2026-09 (study tables), not either rule's results in the check window.
