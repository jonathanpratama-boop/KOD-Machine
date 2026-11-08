# SPEED_v1 results: FIRM NO

Run 2026-11-08 after the protocol, code and 2,000-event sample were stamped (freetsa and sectigo, 10:48Z, commit c70c374fb).
1,995 of 2,000 events had minute data for every arm (5 missing archive days).

Mean net 24h return (common exit at signal + 24h), 95% interval by bootstrap over trigger days:

| Entry after signal | Cost 2.0 pts (R2's) | Cost 0.6 pts | Median (2.0 pts) | Share of trades that won (2.0 pts) |
|---|---|---|---|---|
| 1 min | -3.9% (-4.8 to -2.9) | -2.5% (-3.4 to -1.5) | -7.0% | 23% |
| 5 min | -3.8% | -2.4% | -6.8% | 24% |
| 30 min | -3.2% | -1.8% | -6.0% | 25% |
| 240 min (20h hold) | -2.0% | -0.6% (-1.5 to +0.4) | -4.4% | 28% |

- **Verdict: FIRM NO.** The 1-minute entry loses money even at the cheap 0.6-point cost with no spread (upper bound -1.5%).
- **Speed hurts rather than helps.** 1-min minus 30-min: -0.75 pts (-1.0 to -0.5); 1-min minus 240-min: -1.9 pts (-2.3 to -1.5).
  Entering fast buys at the top of the burst; waiting lets part of the fade happen first. Part of the 240-min arm's
  smaller loss also comes from its shorter 20h hold.
- Both periods agree: every arm loses at 2.0 pts in 2020-2022 and in 2023-2026.
- By the 1-minute entry the coin had already risen a median 13.7% from three hours before the signal.
- Cross-check: the 0-minute arm (-2.5% at 0.6 pts) matches the hourly result in BREADTH_v1 (-2.7% / -3.3%).

Conclusion: buying crypto ignition spikes loses money at every entry speed tested, and reacting faster makes it worse.
The cloud study's speed question is answered from history; its live run cannot reasonably overturn 2,000 events.
