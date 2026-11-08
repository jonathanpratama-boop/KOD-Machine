# CRASH_BOUNCE_IDX_v1: do Indonesian stocks bounce after a crash day?

Written 2026-11-08 (WIB) by Claude at the owner's request ("run the indonesian crash bounce test"), before any return was computed.
Paper research only; changes no running experiment. Mirror image of KOD's spike tests: spikes fade, so do crashes bounce?
Long only (no short selling is assumed). Earlier KOD tests of this idea covered Bitcoin/Ether only (LIQ_REBOUND_v1, failed).

## Disclosure
Only event counts by threshold and year were looked at to choose the definition (about 10,000 events). No return, bounce or
outcome of any kind was computed before this protocol was stamped.

## Events (daily panel `data/panel/panel-20261007T225823Z.csv.gz`, IDX, 2019-07-29 to 2026-10-06)
Signal day s is a row where:
- close / previous - 1 <= -0.07, and
- close <= 1.001 x low (it closed at the day's low), and
- traded value >= 100,000,000 IDR (same liquidity floor as KOD's IDX spike tests), and
- the ticker had no qualifying row in the 5 rows before it (a "fresh" event), and at least 20 rows of history.
The -7% floor is chosen because the exchange's lower limit was 7% in 2021-22 (no -10% days exist then); the same rule is used
in all years. A "session" is a row for that ticker; a day with no trade has no row.

## Trade (decided now)
Entry: close of session s+1 (the panel has no open price; this approximates buying the day after the crash).
Exit (primary): close of session s+6, a 5-session hold. Secondary, reported only: exit at s+2 (1 session).
Cost: 1.5% round trip (the assumption used in KOD's other IDX tests); also reported at 0.8%.
Unscorable (counted, left out): s+6 missing, or more than 20 calendar days after s (suspension / gap).
Locked limit-down on the exit day is ignored, so results are optimistic.

## Control (same dates, no selection)
For each signal date, the equal-weighted mean net return of every other IDX stock that day with traded value >= 100,000,000 IDR,
a scorable window, and no crash-event row in sessions s-5..s (needs at least 20 such stocks), over the identical entry and exit
sessions. Excess = event net return minus that day's control mean.

## Periods
Period A: signal days 2019-2022. Period B: 2023-2026 (the lower-limit rules changed in 2023). Pooled is reported as well.

## Decision rules (fixed now)
95% intervals by bootstrap over whole signal dates, 10,000 resamples, seed 20261108.
- **PASS:** in BOTH periods, the lower bound of the mean primary net return (1.5% cost) is above zero AND the lower bound of
  the mean excess versus control is above zero.
- **FIRM NO:** pooled, the upper bound of the mean primary net return (0.8% cost) is below zero.
- Otherwise **NOT PROVEN.**
Also reported: medians; means without the top and bottom 1%; win rate; the 1-session bounce; results by crash depth
(-7 to -10%, -10 to -15%, below -15%) and by liquidity tercile.

## Known weaknesses
Close-to-close prices (no open, no spread, no depth). Limit-down exits are ignored, so the true result is worse. The panel may
omit delisted stocks (survivorship), which flatters a buy-the-crash test. Many events share days (handled by date resampling).
The 2023+ period holds most events. A pass would justify a live paper test, not trading.
