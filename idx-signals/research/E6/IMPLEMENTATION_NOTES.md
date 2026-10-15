# E6 implementation notes: ambiguities resolved before any outcome was computed

`protocol.json` (frozen in `cacda7b`) is unchanged. Where it leaves a choice open, `idxsig/e6.py` makes the
choice below. Every choice was written here before the discovery run; none was made after seeing an outcome.

## Time and information

1. **Hour grid.** All bars sit on one UTC hourly grid. Day d is the 24 bars opening 00:00..23:00 of d. The
   decision for d is taken at 00:00 UTC of d+1, when bar 23:00 of d has closed.
2. **Features read only bars of day d and earlier.** The 168-hour recent window is the bars of d-6..d. The
   720-hour baseline is the bars of d-36..d-7. Tests prove it: perturbing every bar after day d leaves day d's
   features and flags identical.
3. **Outcome windows start strictly after the decision.** Entry is the open of bar 01:00 of d+1. The window
   is the 120 bars from 01:00 d+1 to 00:00 d+6, and R120 uses that last bar's close. The 00:00 bar of d+1 is
   skipped, as the frozen one-hour delay requires.
4. **Discovery reads nothing after 2022-12-31 23:00.** The loader drops later bars before anything is
   computed. The last decision day whose window ends inside discovery is therefore 2022-12-25. The first is
   2020-07-01.
5. **r_h** is ln(close_h / close_{h-1}) only when bar h-1 exists. An hour after a gap has no return and is not
   counted as a buy or sell hour.

## Features

6. **M_d cancels.** Every lambda in A is a ratio of a return sum to a flow sum scaled by the same M_d, so A
   does not depend on M_d. M_d only decides the sign of f_h, which is the sign of B_h - S_h. The code uses
   B_h - S_h directly. Results are identical to the frozen formula.
7. **Daily quantities.** Daily close is the close of the last bar of the day. Daily high is the highest
   hourly high. Daily quote volume is the sum over the day's bars, and zero when the day has none, so a coin
   that stops trading loses liquidity rather than vanishing.
8. **"Top 5%"** means A_d >= the 95th percentile, linear interpolation, of A among that day's eligible coins
   with A defined. The other P1 conditions apply after that cut. The placebo takes its own 95th percentile of
   placebo A the same way.
9. **close_{d-7}** missing means the 7-day return is undefined, so in_range and relative strength are false.
   The relative-strength median is taken over that day's eligible coins with a defined 7-day return.
10. **30-day high** for in_range and breakout is the maximum daily high over d-30..d-1, using the days that
    exist.
11. **Placebo signs** are drawn once per coin over the whole hour grid with numpy default_rng(20261015 + i).
    Here i is the coin's position in the alphabetically sorted list of the 406 symbols in the manifest.
12. **Debounce** is greedy in date order, per coin and arm. P2's look-back uses debounced P1 flags.

## Eligibility

13. **History** counts complete days, meaning 24 bars, strictly before d, within the fetched data, which
    starts 2020-04-01.
14. **Liquidity** is the median of daily quote volume over the 30 calendar days d-29..d, days without bars
    counting as zero. Day d is complete at decision time.
15. **Data sanity** excludes a coin-day when any hour in d-36..d has buyer-initiated value above total value,
    or a non-positive close. The count of such exclusions is reported.

## Outcomes and controls

16. **No entry bar.** A flag without a 01:00 bar on d+1 has no outcome. It is excluded and counted as
    NO_ENTRY. A window missing later bars ends at the last close available in the window and is counted as
    MISSING_END.
17. **Control pool.** The pool for a flag is that day's eligible coins with an entry bar, excluding the
    flagged coin. Liquidity and volatility quintiles are computed within that pool. Volatility is the
    standard deviation of hourly returns over d-29..d. Requiring an entry bar uses future availability, but
    it applies to flags and controls alike.
18. **Draws** are 200 with replacement. Each arm has its own generator, seeded 20261008, with flags in
    (date, symbol) order, so one arm's flag count cannot change another arm's draws.
19. **Bootstrap.** Weeks are ISO year-weeks of the decision day. Each resample draws weeks with replacement
    and takes the flag-weighted mean excess. p = (1 + count of resampled means <= 0) / (1 + 10,000).
    Differences between arms resample the union of their weeks with the same draw for both arms, so shared
    weeks stay paired.
20. **Stage 2** is written only if an arm passes Stage 1, and only from the frozen Stage-2 rules.

## Limitation of the frozen design, recorded before any outcome

**The gate does not require beating the plain breakout.** The pass criteria test against matched coins and
against the scrambled-flow placebo. "P1 minus B0" and "P2 minus B0" are reported but not gated. So:

- A pass shows the buy/sell split carries information beyond volume, because of the placebo. It does not by
  itself show added value over a plain breakout.
- P2 is a subset of B0, so "P2 minus B0" measures exactly what pressure adds to a breakout. It is the most
  direct answer to Astra's question, and it is reported with its interval.

The protocol is not changed. The report will state plainly whether any arm beats B0, and will not call a pass
"better than a breakout" unless that reported comparison supports it.
