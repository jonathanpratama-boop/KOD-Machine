# ATTENTION_LEAD_v1: does crowd attention show up before the price moves?

Written 2026-11-03, before any page-view number is fetched. Owner's question: timing. The minute-level result
(handoff/timing/TIMING_NARROWING_2026-11-03.md) closed the "react after public news" door; this tests the only door left:
can attention be seen *before* the price moves?

## Data
- Universe: US tickers in panel_us_repair-20261008T114805Z that Wikidata links (P414 exchange NASDAQ or NYSE, qualifier P249
  ticker) to an English Wikipedia article. One article per ticker (the first returned, sorted by article title).
- Attention: Wikimedia daily page views, en.wikipedia, all-access, user agents, 2020-06-01 .. 2023-12-31.
- Prices: the repair panel (daily, survivor-only, split-adjusted), 2020-07-01 .. 2023-12-29. The sealed US holdout (2024+) is
  never loaded.

## Timing (no look-ahead)
Page views for UTC day D are complete only after D ends, so an event dated D is acted on at the **close of the first session
strictly after D**. The price filters use the close of the latest session on or before D.

## Event: an attention surge before a price move
Views(D) >= 3 x median(views D-30..D-1), views(D) >= 500, that median >= 50; and the stock has not moved yet:
|5-session return to the latest session on or before D| < 10% and |that session's return| < 5%. One event per ticker per 20 sessions.

## Controls (same entry session)
Every other universe name that day with median views >= 50, the same "not moved" filter, and views(D) < 1.5 x its median.

## Outcomes (from the entry close)
up30: a close >= 1.30 x entry within 20 sessions; dn23: a close <= entry / 1.30 within 20 sessions; fwd20 return. Excess =
event fwd20 minus the mean control fwd20 that session. Week-clustered bootstrap, 10,000 draws, seed 20261103.

## Descriptive (reported whatever the result)
Around every one-day +30% price jump in the universe: the median abnormal views (views / median of days -30..-11) on days
-10 .. +5. Does attention rise before the jump day, or only on and after it?

## Reading (fixed now)
- **Attention leads, upward**: events' up30 >= 1.5 x controls' AND (up30 - dn23) above the controls' AND mean excess fwd20 > 0
  with t >= 2.0. Then: the "before" door is open in US stocks; next is a live attention log, prospective only.
- **Attention leads, both ways**: up30 and dn23 both rise, excess not positive. Attention predicts movement, not direction,
  like every other KOD sign.
- **No lead**: neither rate rises, and in the descriptive view attention arrives on or after the jump day.
One counted exploratory test on development years. No rerun with changed thresholds.
