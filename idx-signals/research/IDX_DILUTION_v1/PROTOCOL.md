# IDX_DILUTION_v1: do IDX stocks lag matched stocks after their listed-share count jumps?

Written 2026-10-27 after exploring 2019-10 .. 2022-12 and before any 2023 number was computed.

## Events (dl_lib.py)
A session where IDX's listed_shares rises by at least 5% over the prior session (splits excluded: a rise >= 30% whose raw close ratio matches
1/(1+rise) within 15% log). Acted on at the next session's close (posted 16:00 WIB). One event per name per 20 sessions.
Panel panel-20261007T225823Z with registry ca_registry-20261007T230210Z; plan as IDX_INSIDER_NEWS (10M IDR, fees 0.15%/0.25%).

## Exploration, stated openly (2019-10-01 .. 2022-12-30, 100 control draws)
All rises >= 1%: hold 60 mean excess -6.5% (t -2.2, n 99). By size at hold 60: 1-5% +0.4% (n 44); 5-20% -11.0% (t -2.8, n 41);
20-100% -16.5% (t -2.9, n 11). The 5% threshold was chosen after seeing this.

## The one test: events dated 2023-01-03 .. 2023-09-29, holds 20 and 60 (primary), 200 matched draws, week-cluster bootstrap
- **G1** hold-60 mean excess <= -2.0%.
- **G2** hold-60 bootstrap t <= -1.65 (one-sided 5%).
PASS needs both. Run once. The sealed holdout 2024-01-02 .. 2025-02-21 is not touched.

## Reading
PASS: a share-count jump of 5% or more is a sell-or-avoid flag for IDX holdings (retail cannot short IDX). FAIL: closed.
Power is low (about 25 scored events expected); a FAIL does not prove there is no effect.
