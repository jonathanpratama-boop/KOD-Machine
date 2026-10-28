# Daily-data reconciliation: interpretation (written 2026-10-17 WIB, before any return is computed)

`RECONCILE_DAILY.json` (verdict NOT_EQUIVALENT) is kept unchanged. This note explains it.

## What was compared
- Panel: rebuilt with E2's own code (commit a155cf0, panel-global-v1, detached worktree
  `~/Projects/KOD-E2-code-a155cf0`) from the 2026-10-13 Binance pull.
  - `panel_crypto-20261016T170939Z`, sha256 3e693547...: 775,977 rows, 683 tickers, 2,477 sessions.
  - The pinned E2 panel (sha256 3dc12749..., 773,512 rows, last session 2026-10-07) is not on this machine.
    The extra rows are sessions after 2026-10-07.
- Discovery outputs: produced by E2's own discovery code and compared with E2's committed discovery files.
- Environment: Python 3.15, numpy 2.5.4, pandas 3.0.6. E2's original environment is not recorded.

## Results

| Check | E2 committed | Rebuilt | Equal |
|---|---|---|---|
| Eligible coin-days, discovery | 221,468 | 221,468 | yes |
| **G2_RET30 flags (signal under test)** | **1,394** | **1,394** | **yes** |
| G2_RET30 E30 / E50 / E100 hits | 245 / 148 / 56 | 245 / 148 / 56 | yes |
| E30 episodes (ticker, date) | 3,333 | 3,333 | yes, same keys; all 33 columns equal within 1e-9 relative |
| E50 episodes | 1,322 | 1,322 | yes, identical text |
| E100 episodes | 284 | 284 | yes, identical text |
| Other rules (9 of 11) | | | yes, all counts |
| G6_BREAKOUT60_VOL3 flags | 2,992 | 2,991 | **no (one flag)** |
| G11_HIGHVOL_ACTIVE E100 hits | 203 | 202 | **no (one hit)** |

- The script's E30 "identical_rows false" is a text-formatting artefact. Its string comparison is stricter
  than intended: the keys are identical and every value agrees within a relative 1e-9. This is a known
  limitation of that check, disclosed here; the JSON is not rewritten.
- The two one-count differences are in rules NOT under test. Their cause is not established. Candidates:
  - a floating-point boundary case (volume exactly 3x its median; a price ratio exactly 2.0);
  - a single historical bar revised between Binance's 8 Oct and 13 Oct responses.
  They are disclosed as a residual discrepancy.

## Decision for EXIT-ATR-v1
- The E2 discovery signal set and its daily outcome labels are reproduced exactly for G2_RET30.
- The rebuilt panel `panel_crypto-20261016T170939Z` (E2 code a155cf0) is therefore used as E2's daily
  input for this test. Its sha256 is to be recorded in the protocol.
- This is a reconciliation, not a byte reproduction of the pinned panel. The residual G6/G11 differences
  stay disclosed in the result.
