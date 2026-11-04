# CLUE_MECHANISMS_v1 — why do KOD's working clues work, and do they combine? (written 2026-11-03, before running)

**Status: EXPLORATORY.** Every period used here has been looked at by earlier KOD or Hermes studies
(crypto 2020–2026, US 2020–2026 including the AVOID_TILT holdout). Nothing here is validation. Any
combination that looks good becomes a hypothesis for a frozen forward (paper) test, not a strategy.

## Clues under study
1. **Detection clue** — spike / early-mover detectors find future +30% movers 4–9× more often than chance.
   Hypothesis H1: mostly because they select *volatile* names (big moves both ways), not upward direction.
2. **Avoid clue** — names that just spiked +30% keep underperforming for weeks (AVOID_TILT US; crypto ignition
   buys lose). Hypothesis H2: the decay is concentrated in spikes *without* an established uptrend, in small /
   illiquid names, in larger spikes, and in spikes that fail to hold on day 2; it is weaker for spikes in trend.
3. **Trend clue** — early movers already in a strong uptrend (SMA stack, near 200-day high) did better.
   Hypothesis H3: the trend clue is ordinary momentum and works as a *selection* tilt for a whole basket too.
4. **Tide clue** — profit came only when the broad alt market was rallying (Greed; 2020–21).
   Hypothesis H4: a breadth gate known in advance (share of coins above SMA50) separates good and bad periods.

## Tests
- `crypto_mech.py` (Binance spot USDT daily, 2018-01..2026-10, union of discovery + holdout universes, delisted
  symbols included where archived): H1 on hourly ignitions (events/controls from scan_v0) and daily +30% days;
  H2 forward abnormal returns after daily +30% days (entry next-day open, vs equal-weight eligible coins over the same
  window) with splits; H3/H4 weekly long-only baskets: ALL → minus spikers → plus trend → plus breadth gate, vs
  BTC buy-and-hold. Cost 0.3% per side on turnover.
- `us_mech.py` (local Yahoo snapshot 2020-01..2026-10-07, survivor-only): H2 event study on +30% days (entry next
  open, vs equal-weight eligible universe) with splits incl. dilution 8-K 3.02; monthly baskets A (all), B (minus
  spikers = AVOID_TILT), C (B plus trend), D (C minus dilution). Cost 0.2% per side.

## Reporting rule
Report every split and basket, including the ones that do not help. No thresholds tuned after seeing results; if a
variant is added later it is labelled post hoc.
