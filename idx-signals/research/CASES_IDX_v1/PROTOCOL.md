# CASES_IDX_v1: what was visible three sessions before twenty IDX moonshots?

Written 2026-10-27 (WIB night of 2026-10-26), before any case is opened. Descriptive case study, not a counted test: no
gate, no p-value, no trading rule. Owner's instruction: "You do it." It answers one question before any new detector is
built: of the IDX +30% moves, what share had something public and usable at least three sessions before the move?

## Selection (frozen)

The 1,113 FAST_UP episodes of LEAD_LADDER_v1 (IDX, discovery 2021-01-22 .. 2022-12-30: the highest close within five
sessions is at least 1.30 x close t, first in 20 sessions), as listed in `research/LEAD_LADDER_v1/results/events_IDX.csv.gz`
(unique ticker and t). Twenty are drawn uniformly at random, seed 20261027, by `select.py`. No case is replaced after
it is drawn; a case without enough data is reported as such.

## Definitions

- t: the episode's base session. J: the first session in t+1 .. t+5 whose close is at least 10% above the previous close on
  the reference chain; if none, t+1. J-3: three sessions before J. "Three sessions out" means public by J-3's close.
- Evidence pack per case (`packs/`): sessions t-15 .. t+5 from the archived exchange data: close, daily return, volume
  against its prior 20-session median, traded value, foreign net buying as a share of volume, closing bid-queue share,
  negotiated-market value, the upper-limit lock, and any corporate-action registry row in the window.
- News: a search of public sources (exchange announcements as quoted by news sites, Indonesian business press, company
  sites) for items about the company dated from 30 days before J to J. Each item is kept with its URL and publication
  date. An item with no verifiable date counts as undated and is not used for timing.

## Classes (applied in this order; the first that fits)

1. **CORPORATE_ACTION**: a registry row or a reference reset inside t-5 .. J explains the measured move (artefact).
2. **TELEGRAPHED**: a dated public item published by J-3 that plausibly explains the move (an announced deal, a scheduled
   event, an earlier report, a named rumour in the press).
3. **NEWS_SHOCK**: a dated item explaining the move first published after J-3 (J-2 .. J), with nothing related earlier.
4. **SECTOR_SYMPATHY**: no company item; at least three other names in the same sector (the mirror's 2025-02 sector lists)
   closed at least 15% above their t close on some session in J .. J+2.
5. **QUIET_BUILDUP**: none of the above, and by J-3 the 5-session mean volume was at least 2x its prior 20-session median,
   or the close was at least 10% above its 20-session median.
6. **UNEXPLAINED**: none of the above.

"Visible at three sessions out" = TELEGRAPHED or QUIET_BUILDUP. The study reports the count in each class and, for each
case, the one line that decided it. With 20 cases, a share is known to about plus or minus 20 points; it guides the next
idea, it does not prove anything.

## Limits

News search reaches what is still online and indexed; a missing item is not proof that none existed. Classification of
"plausibly explains" is judgement, recorded case by case so it can be checked.
