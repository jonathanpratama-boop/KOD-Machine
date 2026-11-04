# Gate simulations (2026-10-29), run before the protocol was frozen

The real v2.2 gate code (`idxsig/learner2.py`), run on a simulated learner. All three files are design reads; none of
them reads market data.

- `gate_power.py`: weeks until the weekly gate opens, by skill (AUC) and forecasts a week. AUC 0.57 opens in a median
  of 67/44/30 weeks at 20/50/150 forecasts a week; AUC 0.61 in 38/30/30; AUC 0.66 or better at the 30-week minimum.
  Its zero-skill row is trivial: there, the learner does not move its forecasts at all.
- `betting_gate2.py`: an exact betting e-process, with each week's range known before the outcomes. It is slower, not
  faster: 42 to 132 weeks to open, against 30. It has a fair null, in which the learner moves its forecasts on noise:
  neither gate opened in 200 runs.
- `daily_gate.py`: next-session statements scored in daily blocks through v2.2's own confidence sequence. At 30
  forecasts a day, AUC 0.66 opens at the 30-session minimum, about 6 weeks. Under the fair null, 0 to 0.5% of 200 runs
  opened in two years.
