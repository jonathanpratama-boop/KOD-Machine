# Hermes research, 3–4 Nov 2026 (exploratory crypto studies, clue ledger, judgment policy)

All studies here are **exploratory** on Binance spot data that earlier KOD studies had already seen. None is a
validated strategy. Claude independently rebuilt them in `idx-signals/research/HERMES_NOV3_REPRO_v1/` on branch
`claude/hopeful-hypatia-ktzpog` (36 of 45 claims reproduced, 7 partly, 2 not — including "dead by day 3", now corrected).

| Folder | What it tested | Result in one line |
|---|---|---|
| `entry_timing_v1/` | Same alerts, same exit, different entries (limit, hold, reclaim, day-1 high, earlier 1h alarm) | Entries move results 2–5 pts; none profitable after 2021 |
| `psych_v1/` | Crowd mood (Fear & Greed) and perp funding vs how alerts behave | Mood sets the clock; crowded shorts hold most squeeze losses |
| `paths_v1/` | Every alert followed hour by hour for 30 days, no exit rule | Gains appear early and are mostly given back; losers rarely recover |
| `spike_default_v1/` | Test A: treat every alert as a spike (18 quick-exit variants) | FAIL: negative every year; alerts trail random coins |
| `bear_v1/` | Bear-market strategies, spot proxy and real perp funding | Cash wins; every short loses with real funding |
| `live_v0/` | One live snapshot (3 Nov 06:47 UTC) and comparison with 2018–26 | No action; today resembles ~6 past alt-bleed episodes |
| `clue_mechanisms_v1/` | Plan + script only | **Never run** |

Large intermediate CSVs are gzip-compressed. Raw Binance archives and the 21,860 funding zips are not included
(re-downloadable; `bear_v1/raw_funding_manifest.json` lists them). Control-method note: the earlier ±72h future-based
control exclusion flattered alerts by ~0.9 pt (see the ledger correction); no conclusion here depends on it.

`CLUE_LEDGER.md` (append-only, 31 entries) and `JUDGMENT_POLICY_v0.md` (with correction C1, 2026-11-04) are the current
local versions.
