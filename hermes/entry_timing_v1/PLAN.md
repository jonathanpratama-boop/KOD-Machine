# ENTRY_TIMING_v1 — can a different entry make the clues pay? (written 2026-11-03, before running)

**Status: EXPLORATORY.** 2020–22 is development data; 2023–26 was used once by COMBO_HOLDOUT_v1 (the
detector and clues), never for entry rules. No entry rule will be called validated from this run. A rule that
looks good here goes to a frozen forward paper test.

**Question.** On the same candidate moves, does *how and when we enter* change the outcome, holding the exit fixed?

**Candidates.** (a) every hourly ignition from scan_v0 / COMBO_HOLDOUT (+10% in 3h, volume ≥5×, ≤30% prior-week
rise, ≥$20k hourly liquidity, 72h cooldown); (b) the subset with combo clue score ≥ 4; (c) the subset in a daily
uptrend on the previous completed day (close > SMA50 and > SMA200, within 15% of the 200-day high).
Plus a separate EARLIER detector: +5% in ONE hour on ≥5× hourly volume (same other filters).

**Fixed exit (all variants).** Take profit at +50% from the fill price, otherwise sell at the close 336 hours after the
fill. 0.3% cost per side. No stop loss. Fills: market entries at an hourly open; limit entries at the limit (or the
open if it gaps through), take-profit checked from the following hour (conservative).

**Entry variants (decided using data up to the decision hour only).**
- V0 NEXT_OPEN — buy the next hour's open (current method).
- V1 LIMIT_5 / LIMIT_10 / LIMIT_15 — resting buy 5/10/15% below the trigger close, valid 72h; unfilled = no trade.
- V2 HOLD_6H / HOLD_24H — buy only if the close 6h / 24h later is still at or above the trigger close.
- V3 DIP_RECLAIM — within 72h, price closes ≥5% below the trigger close, then closes back above it: buy next open.
- V4 BREAK_DAY1_HIGH — after the first 24h, buy when an hourly close exceeds the high of those 24h (within 72h more).
- V5 EARLY_1H — the earlier detector, buy next open.

**Reported for every variant × subset × period (2020–21, 2022, 2023–26):** candidates, trades, fill rate,
mean / median net, % profitable, take-profit hit rate, and **missed winners** (candidates where V0 reached +50% but the
variant never traded). Descriptive anatomy: how far price had moved at trigger and entry, how deep the first-72h dip
was, and how often the earlier detector fired before the full ignition. All results reported, including bad ones.
