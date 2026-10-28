# EXIT-ATR-v1: coverage and discrepancies (published 2026-10-17 WIB, BEFORE any strategy return)

No exit price, gross return or net return has been computed or read for any trade in this test.
Sources: `entries/` (shared entry list, E2 run code 21345b1); `COVERAGE.json`; `coverage.csv.gz` (one row
per entered trade); `RECONCILE_DAILY_NOTE.md`.

## 1. Daily input (E2's panel)
- Rebuilt from the 2026-10-13 Binance pull with E2's own code (a155cf0): `panel_crypto-20261016T170939Z`,
  sha256 3e693547d547d3d93262b530f160f9b62a8e50e138c3c0f13c84e21a4dead1e0.
- It reproduces E2's committed discovery exactly for G2_RET30 (1,394 flags; 245/148/56 hits; 221,468
  eligible coin-days; identical episode sets).
- Two untested rules differ by one count each (see the note).
- Not a byte copy: E2's pinned panel (3dc12749...) and its raw files are absent here.

## 2. Shared entry list (E2 harness, recorded config, window 2020-07-01..2022-12-31)

| | Signals | Matched controls (200 per attempted signal) |
|---|---|---|
| Raw G2_RET30 signals | 1,495 | |
| Skipped: same coin still held under the ORIGINAL exit | 238 | |
| Attempted | 1,257 (314 coins) | 251,400 (346 coins) |
| Not filled (SKIP_LOT / SKIP_LIQUIDITY / SKIP_NOT_TRADED) | 11 | 1,888 |
| Entered: EXITED / EXIT_DATA_END / INCOMPLETE | 1,241 / 3 / 2 | 248,675 / 468 / 369 |

- Look-ahead check: prefix-first over 914 sessions, 0 mismatches, source audit passed.
- Control matching was often relaxed, so many controls are only loosely matched:
  - all 7 features matched for 64 signals and 6 for 44;
  - 5 features for 278, 4 for 412 and 3 for 316;
  - price band only for 136; same session only for 7.

## 3. Hourly coverage of entered trades (window = entry day 00:00 to the original exit day 23:00)

| Class | Signals | Controls | Meaning |
|---|---|---|---|
| COMPLETE | 1,152 | 231,038 | every hour present |
| GAPS | 91 | 17,969 | some hours missing inside; data resumes before the deadline |
| TRUNCATED | 3 | 505 | hourly data ends before the deadline (delisting or halt) |
| NO_HOURLY_SYMBOL | 0 | 0 | every traded coin is in the hourly archive, delisted ones included |

- Missing entry-day 00:00 bar: 0.
- Gaps are mostly short (median 1 hour, 90th percentile 4 hours) and cluster in months with known exchange
  maintenance (Feb 2021: 42 of the 91 signal gaps).
- Three signal trades are truncated, all EXIT_DATA_END: ANC and MIR (entry 2022-12-26, hourly data ends
  after 27 of 48 hours) and FTT (entry 2022-11-11, data ends after 101 of 120 hours).
- The 2 signal INCOMPLETE trades (AKRO, REN, entry 2022-12-27) are trades whose 5-day hold crosses the
  research boundary 2022-12-31. The original harness does not score them. The same applies to 369 controls.

## 4. ATR warm-up (15 consecutive daily bars s-14..s, high >= low > 0, close > 0)
- Fails for 62 signal trades (56 coins) and 3,524 controls. Mostly newly listed coins: a +30% day soon after
  listing is common, so this exclusion removes a real and possibly distinctive slice of signals. It applies
  to both arms and is reported, not hidden.
- Entered, hourly COMPLETE and ATR-valid: 1,097 signals (304 coins) and 227,670 controls.
  - This is NOT the scored set: gap and truncated trades stay in under explicit rules (to be frozen).

## 5. Daily versus hourly agreement (70,535 coin-days inside trade windows)
- 69,610 coin-days have 24 hourly bars and a daily row.
- 925 have fewer than 24 bars. 17 have hourly bars but no daily row.
- Mismatches above 1e-9 relative:

| Field | Mismatches | Above 0.1% | Largest |
|---|---|---|---|
| Open | 1 | 1 | 0.2% |
| High | 1 | 1 | 0.3% |
| Low | 4 | 3 | 0.94% |
| Close | 9 | 8 | 0.87% |
| Volume | 388 | 209 | 21.8% |

- The close mismatches cluster on 2021-12-07, 12-12, 12-24 and 12-26 (BTS, AXS, BLZ, TLM, LINA, KMD, LRC,
  REN, ALICE). These are source revisions between Binance's REST API (daily) and the public archive
  (hourly). Prices agree on 99.98% or more of coin-days.

## 6. MATERIAL DEFECT FOUND: unadjusted crypto redenominations
- COCOS was halted from 2021-01-19 01:00 to 2021-01-23 02:00 UTC (97 hours) and resumed at a price exactly
  1,000 times higher: last close 0.000695, first open 0.695. Both the daily panel and the hourly archive show
  the jump. Binance klines are not rescaled for token swaps or redenominations.
  - The G2_RET30 signal on 2021-01-15 enters at 0.000714 on 2021-01-16. Its original exit rolls past the
    halt to 2021-01-23 (close 0.9003), so E2's harness would record a gross return of about +126,000% that
    is not real.
- Consequences beyond COCOS (not yet enumerated):
  - A redenomination day can create a false +30% signal.
  - An ATR warm-up window spanning a unit change mixes units.
  - Controls drawn on such coins inherit the same defect.
- E2's ERRATA says "Crypto is not affected (Binance klines are not rescaled)". That is correct about
  rescaling, but a non-rescaled history is exactly what carries the unit jump. E2's discovery detection
  statistics may include signals caused by unit changes. This finding is recorded, not corrected, here.

## Decisions needed before the protocol freeze (proposed; not yet frozen)
1. **Unit changes.**
   - Classify as UNIT_CHANGE any pair of consecutive available bars separated by a halt of 12 hours or
     more, where the price ratio is within 5% of an exact power of ten (10x or more either way).
   - Exclude from BOTH arms, and from controls, any trade whose window or ATR warm-up spans a UNIT_CHANGE.
   - List every case. Check each against a Binance announcement where available.
   - Report results with and without the exclusion.
   - A real crash across a halt does not land on an exact power of ten, so it stays in.
2. **Gaps:** hold through missing hours. At the first bar after a gap, an open below the stop exits at that
   open. The stop is not updated during missing hours.
3. **Truncated (data ends):** stops are checked through the last available hour. Otherwise exit at the
   original model's exit price (last close), the same in both arms. Report a -100% sensitivity for any
   position still open when its data ends.
4. **Boundary-crossing (INCOMPLETE):** not scored in either arm, as in the original harness; count reported.
5. **Terminal exit:** both arms exit at the original model's exit price (the daily close of the deadline
   session). A trade never stopped therefore has an identical return in both arms.
