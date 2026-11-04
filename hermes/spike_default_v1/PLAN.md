# SPIKE_DEFAULT_v1 — Test A of the combined Ace + Hermes model (written 2026-11-03, before running)

**Status: EXPLORATORY** (all 2020–26 prices seen before; the exit policy itself is new and never tested).

**Question.** If every alert is treated as a short-lived spike — take the early gain, cut losers, drop non-movers by day 3 —
and only Extreme Greed alerts are allowed to run, is the result positive after costs, and better than random coins
under the same policy?

**Candidates.** All hourly ignitions 2020–26 (same as ENTRY_TIMING / PATHS). Controls: random eligible coins at the
same hours from the earlier studies (up to 20,000 per period block, seed 20261103), same policy applied.
Entry: next hour open. Cost 0.3% per side. Mood = previous day's Fear & Greed.

**SPIKE mode (all moods except Extreme Greed, i.e. F&G ≤ 75).** Resting take-profit at +T%; resting stop at −L%;
if neither, exit at the close of hour 72. Fills at the level, or at the open if the hour gaps through it. If take-profit
and stop are both touched in the same hour, the stop is assumed first (conservative).
**HOLD mode (Extreme Greed, F&G > 75).** Stop −15%; once the gain has reached +20%, a trailing stop at half the best
gain (level updated from the previous hour's high); otherwise exit at hour 336.

**Variants (all reported).** T ∈ {10, 15, 20}, L ∈ {10, 15, none}; each with HOLD mode on, and with HOLD mode off
(SPIKE mode for every mood). **Primary: T = 15, L = 10, HOLD on.** References: old fixed exit (TP +50% / 14 days), and
hold-72h.

**Reported.** By period (2020–21, 2022, 2023–26) and by year inside 2023–26; all alerts, combo-score ≥ 4, daily uptrend;
event vs control; by mood. Mean, median, % profitable, n.
