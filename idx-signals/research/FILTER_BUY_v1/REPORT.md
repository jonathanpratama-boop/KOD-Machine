# FILTER_BUY_v1: result (one run, 2026-10-30)

Rules frozen in `protocol.json` before any return was computed. US +30% spikes bought at the next open, equal weight;
the third KOD v2.4 expects to dump most (by raw probability) is flagged, the rest kept. Both as-traded replay periods
(`research/REPLAY_UNITS_v2`): A 2026-04..10 (1,718 spikes), B 2025-11..2026-03 (1,080). `results/RESULT.json`,
`results/trades.csv.gz`.

**Registered verdict: FILTER NOT SHOWN.** The primary test (sell the same day, typical cost, kept minus all, lower
bound above zero in both periods) fails: A -0.25% (lower bound -0.90%), B +0.66% (lower bound -0.19%).

| Buy at next open, TYPICAL cost | All spikes | Kept | Flagged | Kept minus all (95% lower bound) |
|---|---:|---:|---:|---|
| A, sell same day (registered) | +0.73% | +0.48% | +1.22% | -0.25% (-0.90%) |
| B, sell same day (registered) | -0.83% | -0.17% | -2.15% | +0.66% (-0.19%) |
| A, hold 5 days (descriptive) | -3.08% | -0.82% | -7.55% | +2.26% (+0.89%) |
| B, hold 5 days (descriptive) | -1.41% | +1.04% | -6.31% | +2.45% (+0.73%) |

## What it shows

- **Same-day, the filter does not help.** The dump KOD predicts mostly happens overnight, before the next open: the
  flagged spikes already opened lower, and buying them there did not lose more that day (in A they gained more).
- **Over five days the filter clearly helps, in both periods.** The flagged third lost 6-8% on average; skipping it
  lifts the average buy by about 2.3-2.5 points, with a positive lower bound in both. This hold was reported beside the
  registered test and was not the pass criterion, so it is a lead, not a result.
- **Buying spikes loses on average at five days** in both periods at every cost level except the kept group in B.

## What it does not show

- It does not show a profitable buying strategy: the kept group's five-day return is -0.8% in A and +1.0% in B.
- Survivorship (names delisted since are absent) flatters buying; open prints are not fills.
- Both periods' forecasts had been read once for AUC, not for returns.

## Use

Registered answer: no. The five-day pattern is worth a clean test: a frozen five-day filter on a new period, which is
what the live US record (tonight onward) will provide. Nothing in v2.4, the ledgers or the routines changes.
