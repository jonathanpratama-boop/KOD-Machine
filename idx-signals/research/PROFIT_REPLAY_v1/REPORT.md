# PROFIT_REPLAY_v1: result (one run, 2026-10-30)

Rules frozen in `protocol.json` before any return was computed. 182 certified dump calls from RECENT_REPLAY_v1
(2026-04-01..2026-10-28), shorted at the next open. Every trade is in `results/trades.csv.gz`, every number in
`results/RESULT.json`.

**Verdict: FAILS the go/no-go.** Under typical costs the one-day short (H1) earns +0.07% per trade, with a 95% lower
bound of -3.7%: not reliably profitable.

| Certified calls, short at next open | Gross per trade | Net, cheap | Net, typical | Net, brutal | Win rate (typical) |
|---|---:|---:|---:|---:|---:|
| Cover same day (H1, primary) | +1.2% | +0.9% | +0.1% (lb -3.7%) | -2.3% | 50% |
| Cover after 5 days (H5, descriptive) | +9.5% | +8.8% (lb +3.0%) | +6.4% (lb +0.6%) | -2.0% | 68% |

Shorting every spike instead loses money at every cost level on H1.

## Why

- **The dump happens before you can short.** The calls open on average 8.8% below the signal close (median 11.7%):
  most of the next-day fall is in the overnight gap, before the first possible entry at the open.
- **Squeezes dominate.** The worst one-day shorts lost 170%, 142% and 111% of the entry (WOK, WETO, IPST). Without the
  three worst, the gross H1 mean is +3.6%. An unhedged, unstopped, full-size short book is wiped out by single days.
- **The 5-day hold looks better but is descriptive.** It was not the pre-registered trade; it clears typical costs
  only narrowly and fails under brutal borrow costs (2% a day), which is common for these names.

## Use

KOD's forecasts rank the dumps (RECENT_REPLAY_v1), but this trade does not monetise them. A next design would need
an entry before the gap (not possible for a forecast made after the close without after-hours access), position
limits and stops against squeezes, and real borrow data. Any such design is a new protocol, tested forward, not tuned
on this run. Nothing in v2.4, the ledgers or the routines changes.
