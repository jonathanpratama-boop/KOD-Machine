# BEAR_v1 — how to trade crypto when the tide is out (written 2026-11-03, before running)

**Status: EXPLORATORY.** All crypto years 2018–2026 have been seen by earlier studies for other questions. E4 v2
(short +30% movers only in a BTC bear regime) already FAILED on 2023 and FRESH_EYES T4 (buy extreme hourly drops)
and LIQ_REBOUND failed; those are re-measured here only as reference arms. Anything that looks good goes to a frozen
forward paper test.

**Regime (decided from the previous day's close only).** BEAR = BTC close below its 200-day SMA. Secondary:
ALT_BEAR = fewer than 35% of eligible coins above their own 50-day SMA. Outside the regime every arm holds cash.

**Universe.** Binance spot USDT pairs (union of the two universes already on disk; stable/leveraged excluded; delisted
coins included where archived). Eligible: 20-day median quote volume ≥ $1m (known the day before), ≥200 days of
history. Shorts, in the realistic mode, only on coins that had a USDT-M perpetual at the time, with actual funding.

**Clues used (from the side-by-side table).** Avoid clue (recent +30% spikers decay, worst without an uptrend and when
the spike fails to hold); trend clue (SMA50/SMA200 stack, near 200-day high = relative strength); tide clue (BTC
SMA200, breadth); sentiment clue (Fear & Greed).

**Weekly baskets (Sunday close decision, 7-day hold, equal weight, 0.3% per side on turnover).**
L_BTC, L_ALTS, S_ALTS, S_WEAK (below SMA50 < SMA200, ≥40% under the 200-day high, falling 20 days),
L_LEADERS (uptrend state), L_RS (top 10% 30-day return vs BTC and above SMA50), LS_LEADERS_WEAK (half long
leaders, half short weak), S_SPIKERS (short coins with a +30% day in the last 20 days that were not in an uptrend).
Shorts: proxy mode uses spot prices and a flat 0.03%/day carry; perp mode uses only perp-listed coins and actual
funding (when the funding download is complete).

**Event arms (only when BEAR at the event).** F_FAILED_SPIKE: short after a +30% day by a non-uptrend coin whose next
day closes below the spike close; enter next open, cover after 10 days or at the next open after a close ≥30% above
entry. F_ALL_SPIKES: same without the failed-hold filter (E4-v2-like reference). B_FEAR_BTC: long BTC when the prior
day's Fear & Greed ≤ 15; hold 10 and 20 days; 10-day cooldown. B_LEADER_DIP: long a leader coin after a ≥20% 3-day drop;
hold 10 days. B_CAPITULATION: long the equal-weight alt basket when breadth ≤ 10%; hold 20 days.

**Reporting.** Each arm by era of bear weeks/events (2018–20, 2021–23, 2024–26) and overall: weeks/trades, mean,
median, % positive, worst week/trade, compounded return, max drawdown, versus CASH (0) and L_BTC in the same weeks.
All arms reported, including failures.
