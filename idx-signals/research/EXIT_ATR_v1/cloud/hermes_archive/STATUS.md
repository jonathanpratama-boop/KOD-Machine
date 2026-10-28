# EXIT-ATR-v1: status checkpoint (resumable)

Owner's brief: one ATR trailing exit (14 daily bars, 3x ATR, ATR frozen per trade, hourly ratchet active
from the next hour) against E2's original exit, on E2's frozen CRYPTO G2_RET30 long signal with its
next-UTC-day-open entry. E2 discovery period only. Holdout sealed. No other exit settings. No agents,
purchases, live trades or merges.

Work branch: `hermes/exit-atr-trail-v1` (local, not pushed), from `origin/claude/e6-pressure-response`
`fa142ff` (base as of 15 Oct plus E6's hourly collector and manifest).

## Step 2: data feasibility (IN PROGRESS; no strategy return computed yet)

### E2's original configuration (verified from committed files)
- Signal: `idxsig/rules/moonshot_g.py`, `SELECTED = (("CRYPTO", "G2_RET30"), ...)`, meaning a UTC day return of
  at least +30%.
- Recorded run config (results/runs/20261008T005732Z_MOONSHOT_E2_CRYPTO_D1_v1/summary.json):
  - entry_lag 1, so entry is the next UTC day's open; holding_days 5; exit at a close;
    data_end_exit last_close; overlap skip;
  - fee 0.1% plus slippage tier 0.1% per side; notional 5,000 USDT; max_participation 0.1;
  - random_draws 200, seed 20261007, controls_version v2, ca_mode adjusted.
- Periods (research/E2/protocol.json): discovery 2020-07-01..2022-12-31; validation 2023 (already
  examined); holdout 2024+ (sealed).
- The ONLY recorded harness (trading) run for E2 crypto is the 2023 validation run: 312 signals, 264
  scored, average net -1.90% against matched controls +1.42%. There is no recorded discovery-period
  trading run.
  - So arm A's discovery baseline will be newly computed under the original config.
  - Fidelity rests on (a) identical pinned inputs and code, and (b) E5 Stage 0, which reproduced the
    pinned 2023 run (origin/claude/e5-ceiling research/E5/CRYPTO/reproduce/result.json).
  - Reading 2023 again is out of scope.

### Daily inputs: OPEN ISSUE
- Pinned panel: `panel_crypto-20261008T003354Z`, sha256 `3dc12749...d963d7d`, 683 tickers (190 delisted or
  halted bases), 773,512 rows, last session 2026-10-07.
  - It was built from REST-API raw files `data/raw/binance/20261008T001212Z` (manifest
    binance-20261008T003333Z.jsonl).
  - Neither the panel nor those raw files is on this Mac. LFS archives only the US inputs.
- Local alternative: `~/Projects/kod-machine-gh/idx-signals/data/raw/binance/20261013T205223Z` (723 files),
  manifest binance-20261013T205223Z.jsonl, and panel_crypto-20261013T205803Z (sha256 1fec989b..., 683
  tickers, 775,979 rows, last session 2026-10-12).
- Planned check:
  1. Rebuild a panel from the 13 Oct raw files, cut at 2026-10-07, and compare its sha256 to `3dc12749...`.
  2. If it differs, compare the discovery-window rows and reproduce E2's committed discovery outputs
     (research/E2/CRYPTO/discovery/detector_selection.csv and episodes_E30.csv).
  3. If neither reconciles, this is the precise blocker: the pinned crypto panel or raw files must be
     supplied from the environment that ran E2 and E5.

### Hourly inputs: RESTORE RUNNING
- Source: E6's frozen manifest `data/manifests/binance_1h-20261015T182940Z.jsonl` (406 USDT symbols, 46
  delisted before 2023-12, months 2020-04..2023-12, per-file sha256).
- `research/EXIT_ATR_v1/fetch_hourly.py` restores 2020-07..2022-12 only. Each file must match both E6's
  hash and the archive CHECKSUM. Log: `data_check/fetch_hourly.log`; output: `data_check/hourly_restore.jsonl`.
- Still to reconcile:
  - Universe gap: the E2 panel draws on 683 exchangeInfo tickers, while the hourly archive is built from
    archive directories.
  - Per trade: daily open versus the 00:00 hourly open, daily close versus the 23:00 bar's close, and
    daily high/low versus the hourly extremes.

## Next steps (in order; nothing below has started)
1. Hourly restore finished: record counts.
2. Daily panel rebuild and hash check (see above).
3. Discovery signal list under the original config (overlap computed with the ORIGINAL exit, shared by both
   arms) plus matched controls. Reconcile the counts with E2's committed discovery outputs.
4. Write `data_check/COVERAGE.md`: trades with complete hourly bars, exclusions by reason, and daily-versus-
   hourly discrepancies. Publish it BEFORE any return.
5. Freeze `PROTOCOL.md` and `protocol.json`:
   - the ATR definition, warm-up and invalid-ATR rule;
   - hourly stop timing, gap and touch fills, missing bars, halts and delistings;
   - costs: original, +10 bps per side, stress +20 bps per side;
   - acceptance criteria;
   - bootstrap: 2,000 calendar-week resamples, seed 20261016.
   Record data and code hashes, then commit.
6. Implement `idxsig/exit_atr.py` as the smallest addition, with focused tests: ATR timing, ratchet,
   next-hour activation, gaps, costs, missing data, deadline, future-bar invariance and boundary refusal.
   Run the full suites, `verify-runs` and `check_append_only.py --all`.
7. One recorded comparison: trade ledger, RESULT.md, verdict. Stop.

## Progress log
- 2026-10-17 (WIB), daily inputs: an exact rebuild of the pinned panel is impossible here.
  - `build-global-panel` verifies every raw file against the 8 Oct manifest, and those raw bytes are absent.
  - Fallback in progress:
    - Copied the 13 Oct manifest `binance-20261013T205223Z.jsonl` from `~/Projects/kod-machine-gh`. Its
      sha256 is e7de2d9702c84d15..., matching the input hash recorded in panel_crypto-20261013T205803Z.
    - Copied its 723 raw files.
    - Building a panel with THIS branch's code (`data_check/build_panel.log`).
  - Environment: venv Python 3.15, numpy 2.5.4, pandas 3.0.6. E2's original environment is not recorded here.
  - `reconcile_daily.py` then reruns E2's own discovery code into `data_check/e2_discovery_repro/` and compares
    the output with E2's committed files: 221,468 eligible coin-days; G2_RET30 1,394 flags with 245/148/56
    E30/E50/E100 hits; 3,333 E30 episodes. Output: `data_check/RECONCILE_DAILY.json`.
  - If the result is NOT_EQUIVALENT, investigate the environment (pandas 3 versus 2) before calling it a
    data blocker.
- Hourly restore: 6,000 of 7,623 files at the last check.
- Panel built with this branch's code: `panel_crypto-20261016T170734Z` (775,979 rows, 683 tickers, 2,477
  sessions, sha256 3a12bf48...).
  - Its format is `panel-global-v2`, and E2's `e1.Study` refuses it ("needs a panel-global-v1 panel").
  - Cause: the builder was upgraded after E2 (US split commits). This is a CODE VERSION mismatch, not a
    data defect.
- Fix in progress:
  - Detached worktree `~/Projects/KOD-E2-code-a155cf0` at E2's discovery code commit `a155cf0` (FORMAT
    panel-global-v1). Its raw dir is a symlink to the same 13 Oct files.
  - Build the v1 panel there, then run `reconcile_daily.py` with `KOD_CODE_ROOT` pointing at that worktree.
  - Outputs still go to this branch's `data_check/`. Logs: `build_panel_v1_a155cf0.log`, `reconcile_daily.log`.
- Open design point for later: the ATR run must use E2's v1 panel semantics. Check whether this branch's
  harness accepts a v1 panel; if not, run both arms on the E2-era harness code plus the new exit module.
  Decide and record this in the protocol before any return is computed.
- 2026-10-17 00:10 WIB, daily reconciliation DONE (`data_check/RECONCILE_DAILY_NOTE.md`).
  - v1 panel `panel_crypto-20261016T170939Z` (E2 code a155cf0, sha256 3e693547..., 775,977 rows)
    reproduces E2's committed discovery EXACTLY for G2_RET30: 1,394 flags; 245/148/56 hits; 221,468
    eligible coin-days; identical E30/E50/E100 episode sets.
  - Residual: one-count differences in two untested rules (G6 flags 2,992 versus 2,991; G11 E100 hits
    203 versus 202), cause unknown. Disclosed.
  - Decision: use this panel as E2's daily input.
- Next: hourly restore finishing (7,000 of 7,623). Then step 3: the signal list with matched controls,
  hourly coverage and daily-versus-hourly reconciliation, published in `data_check/COVERAGE.md`.
- Hourly restore DONE: 7,623 of 7,623 files OK, each matching E6's manifest sha256 AND the archive CHECKSUM
  (`data_check/hourly_restore.jsonl`).
- Step 3a RUNNING: `make_entries.py` on E2's run code (detached worktree `~/Projects/KOD-E2-run-21345b1`,
  commit 21345b1) with the v1 panel copied in.
  - It mirrors `backtest.run()`: signals, execute, overlap skip under the ORIGINAL exit, and matched draws
    (controls v2, seed+1, 200 draws) with each control entry executed.
  - Outputs go to `entries/` (signals.csv, controls.csv.gz, entries_meta.json). They hold entry and timing
    fields ONLY; exit prices and returns are deliberately not saved.
  - Log: `data_check/make_entries.log`.
- Then step 3b: write the coverage script, which checks each signal and control window
  [entry day 00:00, original exit day 23:00] for complete hourly bars. It also checks ATR warm-up
  (15 daily bars s-14..s) and reconciles daily open/close/high/low with the hourly bars on those windows.
  Publish `COVERAGE.md`, then freeze the protocol.
- Step 3a DONE (`entries/entries_meta.json`; code 21345b1; panel 3e693547...):
  - 1,495 raw G2_RET30 signals; 238 overlap-skipped under the original exit; 1,257 attempted (314 coins).
  - Attempted by status: EXITED 1,241, SKIP_LOT 11, EXIT_DATA_END 3, INCOMPLETE 2.
  - 251,400 matched-control entries (346 coins). Match levels used: 412 at 4 features, 316 at 3, 278 at 5,
    136 at price band only, 64 at all 7, 44 at 6, 7 at same session only.
  - Look-ahead: prefix-first over 914 sessions, 0 mismatches, source audit passed.
- Step 3b RUNNING: `coverage.py` writes `data_check/COVERAGE.json` and `coverage.csv.gz`; log `coverage.log`.
  No returns are computed.
- Step 3b DONE: `data_check/COVERAGE.md` published before any return.
  - MATERIAL DEFECT: an unadjusted COCOS 1,000:1 redenomination (halt 2021-01-19 to 2021-01-23) would turn
    E2's trade into a fake +126,000% return. Other redenominations have not yet been enumerated.
  - Five treatment decisions are proposed in COVERAGE.md section "Decisions needed". Unit-change rule:
    a halt of 12 hours or more plus a price ratio within 5% of a power of ten; exclude from both arms.
- NEXT: enumerate UNIT_CHANGE cases with the proposed rule (list only, no returns). Check them against Binance
  announcements. Then freeze PROTOCOL.md, protocol.json and the hashes, and commit.

## Separate background job (not part of this test)
The PUMP-LAB comparison download (`~/.hermes/profiles/kod-machine/pump-game/fetch_controls.py`), approved
earlier, is still running. Nothing in it is being analysed. The owner's instruction for this test
excludes starting the pump idea search.
