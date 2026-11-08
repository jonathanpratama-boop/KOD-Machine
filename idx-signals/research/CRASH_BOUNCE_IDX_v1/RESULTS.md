# CRASH_BOUNCE_IDX_v1 results: FIRM NO

Run 2026-11-08 after the protocol and code were stamped (freetsa and sectigo, 15:10:18Z, commit 7a7f6e928).
5,662 fresh crash days (close <= -7% and at the day's low, traded value >= IDR 100m); 5,574 scorable, 88 not.

Buy the close of the next session, sell 5 sessions later, 1.5% round-trip cost. Mean net return, 95% interval by bootstrap over dates:

| Period | Events | Mean net | 95% interval | Median | Won | Excess vs same-day stocks |
|---|---|---|---|---|---|---|
| 2019-2022 | 521 | -8.0% | -11.1 to -4.5 | -5.5% | 27% | -2.6 pts (-4.1 to -1.1) |
| 2023-2026 | 5,053 | -1.6% | -2.6 to -0.5 | -2.6% | 38% | -0.4 pts (-1.1 to +0.3) |
| Pooled | 5,574 | -2.2% | -3.3 to -1.1 | -2.9% | 37% | -0.6 pts (-1.2 to +0.1) |

- **Verdict: FIRM NO.** Pooled, even at 0.8% cost the upper bound is below zero (-1.5%, interval -2.5 to -0.4).
- Before costs, a crashed stock does about what an ordinary stock does (pooled 5-day gross -0.7% vs -0.1% for the same-day
  control). There is no bounce to harvest; costs then make it a loss. The 1-session bounce is -0.6% gross.
- Deeper crashes are no better: -7 to -10%: -2.1%; -10 to -15%: -2.3%; below -15%: -2.8% (net).
- By liquidity (reported only, not a decision rule): lowest tercile -0.04% net, middle -1.9%, highest -4.6%. Even the best
  tercile is not positive, and picking it after seeing this would be a new, untested rule.
- Caveats that flatter the result: limit-down exits ignored, close-to-close prices, possible survivorship in the panel.

Conclusion: buying Indonesian stocks the day after a crash does not pay. The last cheap price-pattern test is closed.
