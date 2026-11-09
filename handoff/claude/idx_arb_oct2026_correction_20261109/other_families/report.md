# IDX lower-limit correction: effect on the Catalyst Register and the other persisted record families (addendum)

Paper trading only, no real money. Every count and statistic here comes from `harness.py`; statements about code paths and protocols come from reading the code (`code_callers.txt`) and are labelled as such. The harness replays the real functions of the shipped rules (B) and the corrected rules (C) on the only surviving raw pull (`yahoo_recent-20261106T101853Z.jsonl`, sha256 `3a27d3445b3d`, 920 tickers, last bar 2026-11-06). That makes every result a *final-bar replay*: a sale that rolls is resolved with the bars up to 2026-11-06, and a roll that runs past the last bar leaves the row pending. Nothing was edited: no ledger, no register, no code dir (hash snapshots of the two code dirs, the repository's paper/ and research/ and the frozen inputs, taken before and after the run, are identical).

## The numbers

- **Catalyst register: 14 IDX RESOLUTION rows** (`paper/catalysts.jsonl` lines 74 to 87), all `IDX_INDEX` window `RUNUP`: signal session 2026-10-28, buy the 2026-10-29 close, sell the 2026-10-30 close. 84 trades (14 candidates, 70 twins). Every sale falls on 2026-10-30, after both October rule changes; the rows were written at 2026-10-30T10:59:10Z.
- **Baseline gate passed.** B replayed on the final pull reproduces **14 of 14** recorded rows: 1596 leaves compared, every text, date, status, boolean and count identical, 704 of 868 numeric leaves bit-identical and the other 164 within 3.3e-16 (floating-point noise from a different window start, diagnosed below). The published `CATALYSTS.md` line is also reproduced by the register's own `statistics()` and `render()` from the recorded rows.
- **Under the corrected rules (C), 9 of 14 rows change** (CUAN, HEAL, ISAT, MIKA, PGEO, SCMA, SMGR, SMRA, TINS); 5 do not (AALI, ELSA, PTBA, TKIM, UNVR). **17 of 84 trades change their exit** (2 candidates, 15 twin slots, 15 distinct names; DMAS is a twin of 3 sets) and 16 change their return (SMDR sells the next day at an unchanged price). Each of them closed on 2026-10-30 between 6.3% and 10.0% below the previous close; 16 of the 17 closed exactly at the tick-rounded 7% limit price and 1 (LUCY) exactly at the 10% special-board limit. The old 15% limit let all of them sell on 2026-10-30; the 7% limit locks them, so each sale rolls to the next sellable session (14 trades roll 1 session, 1 trade rolls 2 sessions, 2 trades roll 3 sessions).
- **The data themselves show a binding 7% limit from 2026-10-19**, independent of the decree texts (which I did not read). Among traded names with a reference above Rp14 that closed down, closes exactly at the tick-rounded 7% limit price run at 16.4 per session in the 15%-limit sessions of 2026-09-28 to 2026-10-16 (13.0 over the 106 sessions before) and at 117.5 per session from 2026-10-19; closes below that price fall from 85 to 11 per session; the 15% limit price itself is hit 0 times from 2026-10-19, against 545 in the 15 sessions before.
- **The published line moves.** `paper/CATALYSTS.md` says *RUNUP: paired 14, mean signed diff +1.16%, share with the flow 64%*. Recomputed with the register's own code: recorded rows +1.16% and 64%; B replay +1.16% and 64% (identical); **C replay +1.35% and 71%** (10 of 14 sets with the flow, was 9 of 14). One graded statement flips: ISAT `WITH_FLOW_RUNUP` goes False to True, so the calibration row's realised rate goes from 0.64 to 0.71; its Brier terms stay 0.250 (prior 0.5 for every set). POST20 has no resolved row under either rule set.
- **One other family has IDX values that depend on the lock and was not covered: `learner_v2.jsonl`** (26 IDX rows), through its training labels only. Re-forecast with the learner's own code from each record's own ledger prefix, the single flipped label (ISAT) shifts the raw forecast probabilities of 202 of 238 records (24 of 26 IDX records; US and crypto records share the slope) by at most 0.0398 (0.0198 on IDX records); published probabilities and calls do not change. Separately, the ALKA BASE5 speculation row stays pending under C, which moves the published `RUN30_5` and `PUMP30_5` probability of 3 IDX forecasts by 0.0235.
- **Cross-check of the earlier work with the same machinery.** Speculation Register, 23 IDX rows: B reproduces 22; under C ALKA BASE5 is PENDING (a sale rolls past the last bar). Ledger, 93 IDX OUTCOME rows: B reproduces 90; C gives 11 of them a different exit session and leaves 3 pending. Details below.
- **No other family has IDX rows that depend on the lock** (table below): scans, decisions, sets, tags and batches, and the US, crypto, book and account ledgers are independent of `lock_down`.

## Catalyst register, row by row

Signed difference = (candidate net minus the twins' mean net) x direction; *with flow* = signed difference above zero (`WITH_FLOW_RUNUP`). Net returns are after the paper fees. `Line` is the line in `paper/catalysts.jsonl`; the hash is the row's `record_hash` (first 12 characters). Candidate and twin trades of every row, with exits and returns under both rule sets, are in the appendix and in `trades.csv`.

| Line | Set | Record hash | Dir | Cand. net B | Cand. net C | Cand. exit C | Signed diff B | Signed diff C | With flow B | With flow C | Trades whose exit changes in C |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 74 | AALI | `601abd15813c` | +1 | +1.18% | +1.18% | 2026-10-30 | +1.16% | +1.16% | yes | yes | 0 of 6 |
| 75 | CUAN | `fa1e6a590b0d` | -1 | -7.20% | -0.89% | 2026-11-02 | +6.25% | +0.69% | yes | yes | 2 of 6 (cand CUAN, IRSX) |
| 76 | ELSA | `fd088c2bb52b` | +1 | +0.40% | +0.40% | 2026-10-30 | +2.64% | +2.64% | yes | yes | 0 of 6 |
| 77 | HEAL | `85a4dcaf1e04` | -1 | -0.40% | -0.40% | 2026-10-30 | -2.73% | -1.62% | no | no | 2 of 6 (UNSP, MITI) |
| 78 | ISAT | `e70c71b8af89` | +1 | -7.20% | -2.44% | 2026-11-02 | -3.72% | +0.17% | no | yes | 3 of 6 (cand ISAT, ARCI, TEBE) |
| 79 | MIKA | `5eee604f53e3` | -1 | -4.76% | -4.76% | 2026-10-30 | +1.73% | +2.00% | yes | yes | 1 of 6 (ASPI) |
| 80 | PGEO | `187d9466759b` | -1 | -6.11% | -6.11% | 2026-10-30 | +4.42% | +3.31% | yes | yes | 1 of 6 (DMAS) |
| 81 | PTBA | `e8bd59308b14` | +1 | +5.46% | +5.46% | 2026-10-30 | +7.10% | +7.10% | yes | yes | 0 of 6 |
| 82 | SCMA | `784dd5c92879` | -1 | -0.40% | -0.40% | 2026-10-30 | -5.90% | -5.36% | no | no | 3 of 6 (MDIA, KOTA, LUCY) |
| 83 | SMGR | `0547782a29b3` | +1 | -2.59% | -2.59% | 2026-10-30 | +0.29% | +1.41% | yes | yes | 1 of 6 (DMAS) |
| 84 | SMRA | `392a6322a112` | -1 | +0.42% | +0.42% | 2026-10-30 | -3.47% | -4.59% | no | no | 2 of 6 (DMAS, SMDR) |
| 85 | TINS | `930ca03e7207` | +1 | +1.26% | +1.26% | 2026-10-30 | +6.77% | +10.31% | yes | yes | 2 of 6 (RATU, BUVA) |
| 86 | TKIM | `8fd7dd52d65b` | +1 | +0.82% | +0.82% | 2026-10-30 | +2.10% | +2.10% | yes | yes | 0 of 6 |
| 87 | UNVR | `3f062b1898ad` | -1 | -1.11% | -1.11% | 2026-10-30 | -0.34% | -0.34% | no | no | 0 of 6 |

The 17 trades whose exit changes. Target session 2026-10-30 for all; ARB = the lower-limit price; the move is close over the previous close.

| Set | Role | Name | Move | ARB B | ARB C | Close | Exit and net, B | Exit and net, C | Rolled |
|---|---|---|---|---|---|---|---|---|---|
| CUAN | candidate | CUAN | -6.83% | 350 | 382 | 382 | 2026-10-30, -7.20% | 2026-11-02, -0.89% | 1 |
| CUAN | twin | IRSX | -6.60% | 181 | 198 | 198 | 2026-10-30, -6.98% | 2026-11-02, -3.22% | 1 |
| HEAL | twin | UNSP | -6.98% | 220 | 240 | 240 | 2026-10-30, -7.35% | 2026-11-02, -3.49% | 1 |
| HEAL | twin | MITI | -6.67% | 204 | 224 | 224 | 2026-10-30, -7.04% | 2026-11-02, -5.38% | 1 |
| ISAT | candidate | ISAT | -6.83% | 1250 | 1365 | 1365 | 2026-10-30, -7.20% | 2026-11-02, -2.44% | 1 |
| ISAT | twin | ARCI | -6.99% | 795 | 865 | 865 | 2026-10-30, -7.36% | 2026-11-02, -6.29% | 1 |
| ISAT | twin | TEBE | -6.91% | 1420 | 1550 | 1550 | 2026-10-30, -7.28% | 2026-11-02, -3.99% | 1 |
| MIKA | twin | ASPI | -6.62% | 645 | 705 | 705 | 2026-10-30, -7.00% | 2026-11-04, -5.68% | 3 |
| PGEO | twin | DMAS | -6.63% | 167 | 183 | 183 | 2026-10-30, -7.01% | 2026-11-02, -12.60% | 1 |
| SCMA | twin | MDIA | -6.49% | 66 | 72 | 72 | 2026-10-30, -6.87% | 2026-11-02, -0.40% | 1 |
| SCMA | twin | KOTA | -6.33% | 68 | 74 | 74 | 2026-10-30, -6.70% | 2026-11-02, -7.96% | 1 |
| SCMA | twin | LUCY | -10.00% | 102 | 112 | 108 | 2026-10-30, -10.36% | 2026-11-02, -12.85% | 1 |
| SMGR | twin | DMAS | -6.63% | 167 | 183 | 183 | 2026-10-30, -7.01% | 2026-11-02, -12.60% | 1 |
| SMRA | twin | DMAS | -6.63% | 167 | 183 | 183 | 2026-10-30, -7.01% | 2026-11-02, -12.60% | 1 |
| SMRA | twin | SMDR | -6.84% | 324 | 354 | 354 | 2026-10-30, -7.21% | 2026-11-02, -7.21% | 1 |
| TINS | twin | RATU | -6.97% | 1770 | 1935 | 1935 | 2026-10-30, -7.34% | 2026-11-03, -11.41% | 2 |
| TINS | twin | BUVA | -6.55% | 286 | 314 | 314 | 2026-10-30, -6.92% | 2026-11-04, -20.56% | 3 |

## Why the rows change

`catalysts.resolve_set` runs `speculation.simulate` for the candidate and for each twin. `simulate` sells at the first session at or after the target where `tradeable and not lock_down`, and returns nothing (row pending) if there is none. `lock_down` is built in `Market.build`: the bar traded, the close is below the reference and at or below that day's lower limit (ARB). B keeps the 15% limit set on 2026-09-28; C applies 7% from 2026-10-19 and a nominal Rp1 limit for references Rp11 to 14 from 2026-10-20. The upper limit (ARA, and so `lock_up` and every entry) is identical in B and C (0 of 125,120 cells differ). The two rule sets differ only in lower-limit cells on or after 2026-10-19: 1,892 cells are locked under C and not under B, 0 the other way, 0 before 2026-10-19 (`lock_cells_changed.csv`); 4 of them have a reference of Rp14 or less. The lock formula was recomputed independently from the limit arrays and reproduces `Market.lock_down` and `lock_up` exactly under both rule sets, and the two limit prices were recomputed by hand (previous close x 0.85 and x 0.93, rounded up to the tick) for the target cell of each of the 84 catalyst trades: they match the code in 84 of 84. The rows were resolved on 2026-10-30 at about 10:59 UTC, when none of these sales was locked under B. Under C, 9 of the sets cannot resolve that day, because a sale rolls: they would have been written when the last rolled sale closed (2026-11-02, 2026-11-04).

## Baseline gate, and what the tiny differences are

The 14 rows were written on the 2026-10-30 pull (manifest sha256 `cc80bfb2b36a`; that manifest is kept in the frozen inputs and matches the hash recorded in the rows, but its raw payloads were not kept). The replay reads the 2026-11-06 pull, whose 200-day window starts later (2026-04-20 against 2026-04-13). The reference chain `level` is a cumulative sum of log returns from the first bar of the window, so `level[exit] / level[entry]` differs in the last bits. The numeric fields that are not bit-identical are exactly `/candidate/trade/gross_return`, `/candidate/trade/mae`, `/candidate/trade/mfe`, `/candidate/trade/net_return`, `/paired/candidate_net`, `/paired/diff`, `/paired/twins_mean_net`, `/paired/twins_median_net`, `/twins/#/trade/gross_return`, `/twins/#/trade/mae`, `/twins/#/trade/mfe`, `/twins/#/trade/net_return`, never by more than 3.3e-16. Entry prices, sessions, exit reasons, costs, statuses, units, cone outcomes and Brier terms are identical (0 non-numeric mismatches). The B-replayed rows and the recorded rows both render, with the register's own `render()`, to exactly the published IDX_INDEX lines (yes); the four hash chains read here verify (ledger.jsonl: intact, catalysts.jsonl: intact, speculations.jsonl: intact, learner_v2.jsonl: intact). A first-principles recomputation of every replayed plan trade (the 84 catalyst trades and the 11 traded legs of the two BASE5 speculation rows) from the saved price and lock arrays alone, without calling `simulate` (first sellable session at or after the target, reference-chain return, the recorded costs), agrees on exit session and net return for 95 of 95 trades under B and 90 of 90 under C.

## Other persisted record families

Counted from the committed snapshot (a ledger row without `market` is IDX). *Touching* = a session field (signal, entry, exit or scan session) on or after 2026-10-19. *Exposed* = a trade sold on or after that date, the only place the lock enters; for `learner_v2` it means the record was trained on the 14 `IDX_INDEX` labels. The depends / path / replay columns come from reading the code (`code_callers.txt`) and, where stated, from the replays here.

| File | Record family | IDX rows | Touching | Exposed | Depends on the lock | Code path | Replayable from the final pull | Replay result (rows replayed, rows changed under C, B reproduces) |
|---|---|---|---|---|---|---|---|---|
| `ledger.jsonl` | SCAN (market absent = IDX) | 23 | 15 |  | no | paper.scan_frame and the rules read lock_up, never lock_down (grep); ARA is identical in B and C | n/a (no lock dependence) |  |
| `ledger.jsonl` | DECISION (market absent = IDX) | 126 | 88 |  | no | paper._decide_v3 sizes on the hard-coded Policy.max_stop_distance 0.15 and prints '15% below the entry'; it never calls market.limits | n/a |  |
| `ledger.jsonl` | OUTCOME (IDX) | 93 | 65 | 35 | yes (direct) | paper.score_pending -> paper.score -> the legacy v3 loop (sellable = tradeable & ~lock_down; used by all 93 recorded rows) or _score_plan -> execution.execute (roll to next_sellable; E3-plan decisions, none recorded) | yes (replayed here as a cross-check of the earlier work) | 93 replayed, 14 changed, B reproduces 90 of 93; 11 exit changes, 3 pending |
| `speculations.jsonl` | SPECULATION_SET (IDX) | 26 | 26 |  | no | speculation.build_set: twins and signal from the scan's features | n/a |  |
| `speculations.jsonl` | RESOLUTION BASE5 (IDX) | 2 | 2 | 2 | yes (direct) | speculation.resolve_set -> simulate(): sellable(k) = tradeable & ~lock_down; x = first sellable session >= target, None (pending) if none | yes (replayed here as a cross-check of the earlier work) | 2 replayed, 1 changed, B reproduces 2 of 2; pending under C: ALKA |
| `speculations.jsonl` | RESOLUTION NEXT1 (IDX) | 21 | 21 |  | no | path window: next_return() uses closes only | yes (replayed here with the 23) | 21 replayed, 0 changed, B reproduces 20 of 21; pending under C: none |
| `catalysts.jsonl` | BATCH (IDX_INDEX) | 1 | 1 |  | no | catalysts.idx_index_batch: event list statuses | n/a |  |
| `catalysts.jsonl` | CATALYST_SET (IDX_INDEX) | 14 | 14 |  | no | catalysts.idx_index_batch: twins by draw_twins from the scan's features | n/a |  |
| `catalysts.jsonl` | TAG (IDX_INDEX) | 14 | 14 |  | no | catalysts.dilution_tags: EmitenNews headlines | n/a |  |
| `catalysts.jsonl` | RESOLUTION (IDX_INDEX) | 14 | 14 | 14 | yes (direct) | catalysts.resolve_set -> speculation.simulate for the candidate and each twin: sellable(k) = tradeable & ~lock_down; the sale rolls to the next sellable session | yes (the priority of this addendum) | 14 replayed, 9 changed, B reproduces 14 of 14; 17 of 84 trades change exit; 1 statement flips; published line moves |
| `catalysts.jsonl` | US families (BATCH/CATALYST_SET/TAG) | 0 | 0 |  | no | US markets are built with price_limits=False: lock_down is all False | n/a (IDX rows: 0) |  |
| `learner_v2.jsonl` | LEARNER2_FORECAST (SPEC_IDX) | 26 | 26 | 24 | yes (indirect: training labels) | learner2.train -> live_rows -> outcomes() reads RESOLUTION cone outcomes: IDX_INDEX WITH_FLOW_RUNUP (shared RELATIVE slope) and SPEC_IDX BASE5 statements (anchors) | yes (the learner's own _record() on each record's ledger prefix, with replayed labels) | 26 replayed, 24 changed, B reproduces 26 of 26; raw forecasts shift in 24, published in 3, calls in 0 |
| `learner_v2.jsonl` | LEARNER2_FORECAST (US/CRYPTO rows: not IDX) | 0 | 0 |  | indirect only (shared slope) | the same labels reach US/CRYPTO forecasts through the shared RELATIVE slope | yes (same replay) | 212 replayed, 178 changed, B reproduces 212 of 212; raw forecasts shift (shared slope); published and calls unchanged |
| `learner_v3.jsonl` | LEARNER3_FORECAST (SPEC_US) | 0 | 0 |  | no | US only; trains on SPEC_US rows and its own forecasts | n/a (IDX rows: 0) |  |
| `learner.jsonl` | LEARNER_FORECAST (SEC13D) | 0 | 0 |  | no | US SEC13D only | n/a (IDX rows: 0) |  |
| `paper_book.jsonl` | BOOK_PLAN | 0 | 0 |  | no | US spikes only | n/a (IDX rows: 0) |  |
| `paper_account.jsonl` | ACCT_* | 0 | 0 |  | no | exec_us on US bars only | n/a (IDX rows: 0) |  |
| `crypto_account.jsonl` | ACCT_* / CRYPTO_QUOTE | 0 | 0 |  | no | crypto | n/a (IDX rows: 0) |  |
| `premove_shadow.jsonl` | PREMOVE_SHADOW_* | 0 | 0 |  | no | crypto (Binance) only | n/a (IDX rows: 0) |  |
| `microstructure/crypto.jsonl` | TIMELINE/BOOK | 0 | 0 |  | no | crypto order books | n/a (IDX rows: 0) |  |
| `sensors/sensors.jsonl` | SENSOR_ALERT emitennews_dilution (IDX-related) | 4 | 4 |  | no | news headlines, no prices | n/a |  |
| `scans/` | scan directories (IDX = no market infix) | 23 | 15 |  | no | features.csv built by rules that read lock_up only | n/a |  |
| `catalysts_form4/` | EDGAR Form 4 dumps (US) | 0 | 0 |  | no | no price or lock input | n/a |  |
| `timestamps/` | RFC 3161 tokens | 0 | 0 |  | no | no price or lock input | n/a |  |
| `sensors/raw/` | raw feed pulls | 0 | 0 |  | no | no price or lock input | n/a |  |
| `microstructure/raw/` | crypto raw books | 0 | 0 |  | no | no price or lock input | n/a |  |

The derived reports (`CATALYSTS.md`, `SPECULATIONS.md`, `LEARNER_V2.md`, `LEARNER_V3.md`, `CALL_CERT.md`, the account and book reports, `README.md`) are rendered from the ledgers and hold no value of their own; of them only the IDX_INDEX section of `CATALYSTS.md` is changed by this addendum's rows.

## Second-order: learner_v2

`learner_v2.jsonl` trains on every graded statement that the two registers resolved before each forecast. The 14 `IDX_INDEX WITH_FLOW_RUNUP` labels enter the slope shared by all relative statements (`BEATS_TWINS_k` and the like, in every family and market); the `SPEC_IDX` BASE5 labels enter the Speculation Register anchors. Each forecast record carries the ledger state it was computed from, so the learner's own `_record()` can be re-run per record with changed labels (first order: each record's earlier learner records stay as recorded). All 238 recorded forecasts are reproduced from the recorded ledgers (first row) and from the B-replayed labels (second row) before any C row is read.

| Labels used | Records with raw forecasts changed (all / IDX) | Published changed (all / IDX) | Calls changed | Largest raw change | Largest published change |
|---|---|---|---|---|---|
| recorded ledgers (baseline) | 0 / 0 | 0 / 0 | 0 | 0.00000 | 0.00000 |
| B-replayed labels (baseline) | 0 / 0 | 0 / 0 | 0 | 0.00000 | 0.00000 |
| C labels at the recorded timestamps (the ISAT flip) | 202 / 24 | 0 / 0 | 0 | 0.03976 | 0.00000 |
| ALKA BASE5 row absent (pending under C) | 78 / 3 | 3 / 3 | 0 | 0.02395 | 0.02352 |
| both, recorded timestamps | 202 / 24 | 3 / 3 | 0 | 0.03976 | 0.02352 |
| both, each changed label available only after its roll completes | 202 / 24 | 3 / 3 | 0 | 0.03841 | 0.02352 |

*Changed* means beyond the learner's own verification tolerance (2e-06). Published probabilities stay at their anchors because the learner's gates are closed (alpha 0); the raw numbers are what the gate would pass through. The only published changes are the 3 IDX forecasts sealed at 2026-11-06T10:43:14Z (POLU, FLMC, AIMS): PUMP30_5, RUN30_5 move from 0.1170 to 0.1405, because the ALKA BASE5 row (recorded at 2026-11-06T10:28:09Z, 15 minutes before) would not exist yet under C and its `RUN30_5` label would be missing from the Speculation Register anchor.

## Cross-checks of the earlier work (not the focus of this addendum)

**Speculation Register, 23 IDX rows** (21 NEXT1, 2 BASE5) with `speculation.resolve_set`. B reproduces 22 of 23. TMPO NEXT1 (signal 2026-11-04) does not: recorded statements are ungraded (outcome null) but the final pull grades them: a bar the resolving pull lacked. Under C: ALKA BASE5 is PENDING (a sale rolls past the last bar). `SPEC-SCAN-2026-10-29-F1_ARA-ALKA`: KDTN closes 238 from 254 on 2026-11-06, the last bar, with ARB 216 under B and 238 under C; WBSA closes 344 from 368 on 2026-11-06, the last bar, with ARB 314 under B and 344 under C.

**Ledger, 93 IDX OUTCOME rows** (all use the legacy v3 plan loop in `paper.score`) with `paper.scoring_units` and `paper.score`, as `score_pending` does. B reproduces 90 of 93; the others: BTEK (signal 2026-10-20): knife-edge threshold: every number agrees within 1e-12 but a boolean flips (/discovery/E30); CARE (signal 2026-10-21): recorded outcome scored at 2026-10-29T08:21:17Z, before its exit session's bar was final (2026-10-29T09:30:00Z): the replay reads the settled close; SOHO (signal 2026-10-21): recorded outcome scored at 2026-10-29T08:21:17Z, before its exit session's bar was final (2026-10-29T09:30:00Z): the replay reads the settled close. Under C 14 rows change relative to B: 11 get a different exit session and return (0 verdict flips) and 3 stay pending (PNSE, PTSP, KONI). Mean net return over the 37 trades present under both: -9.62% under B, -11.17% under C. The earlier analysts' numbers were not read, so these are an independent count, not a comparison.

## Caveats and unresolved items

- **Final-bar replay, not a re-run of 2026-10-30.** Only the 2026-11-06 raw pull survives. Under C the 9 changed sets could not have been written on 2026-10-30; the register would have written them on 2026-11-02 and 2026-11-04. The values here are what the register holds once the last roll closes.
- **The rule schedule is the one in `market.py` (C), and I did not verify it.** I did not check the 7% limit from 2026-10-19 or the Rp1 limit against decree texts; the module itself says the decrees were not read and that the real limit on 2026-10-19 for references Rp11 to 14 is unknown (nothing here depends on that day). What the data say: closes bunch at the 7% limit price from 2026-10-19 (see the numbers above), 16 of the 17 changed sales closed exactly at C's tick-rounded limit price, and across the panel 1,751 of the 1,892 cells that C locks and B does not close exactly at C's limit while 141 close below it (a regular-board name cannot do that under a 7% limit; those are 10%-board names, or names whose reference was reset). That corroborates the 7% schedule as the rule in force on 2026-10-30; it does not test the Rp11-14 rule, which nothing in this register uses.
- **Board membership is not in the data.** `limits()` models the regular boards for every name; a name on a 10% board is over-locked by a fall between 7% and 10%. In this register the only close below the 7% limit is LUCY (-10.0%), which sits exactly at the 10% special-board limit and is locked on either reading.
- **The register is append-only and I changed no row.** A correction would be new RESOLUTION rows whose `revises` names the earlier hash. Because each learner forecast is verified against the ledger prefix it was made from, appended revisions would leave every existing forecast verifiable; only forecasts made after the revisions would train on the corrected labels. The learner results above are therefore what the forecasts would have been had the corrected labels existed at the time. Whether to append revisions, and a corrected `CATALYSTS.md` line, is the owner's decision.
- **Descriptive only.** The register labels IDX_INDEX 'never tested'. The shift in the mean signed difference is 0.19 percentage points against a standard error of 1.10 percentage points (14 sets, one index review, one signal session). The flipped ISAT statement lands at +0.17% signed difference (was -3.72%), so it is fragile.
- **The learner replay is first-order.** Each forecast is recomputed from its own recorded ledger prefix and the recorded earlier learner records; compounding through later forecasts' gates is not followed. The C-world timing (a changed label becomes available to the first learner batch on the calendar day of its last rolled sale, minus one second) is my assumption.
- **Baseline differences in the cross-checks are data, not the lock.** Speculation Register: TMPO NEXT1. Ledger: BTEK: knife-edge threshold: every number agrees within 1e-12 but a boolean flips (/discovery/E30); CARE: recorded outcome scored at 2026-10-29T08:21:17Z, before its exit session's bar was final (2026-10-29T09:30:00Z): the replay reads the settled close; SOHO: recorded outcome scored at 2026-10-29T08:21:17Z, before its exit session's bar was final (2026-10-29T09:30:00Z): the replay reads the settled close. The raw 2026-11-05 payload did not survive, so the 'missing bar' reading of the Speculation Register row is an inference. 2 ledger outcomes (CARE, SOHO) were scored before their exit bar was final, a separate data-quality point outside this question.
- **Decision text and sizing are stale after 2026-10-19 but do not read `market.py`.** DECISION rows size against the hard-coded `Policy.max_stop_distance` 0.15 and say 'locked at ARB, 15% below the entry'. The market.py correction cannot change them; PAPER-POLICY-v4 would need a new version.
- **POST20 windows of the same 14 sets are not resolvable yet** (signal 2026-10-28 plus 22 sessions, 2026-11-27 at the earliest), so they will be the first rows written under whichever rules are then in force.
- **Outside `paper/`:** `research/LLM_ARM_v1/calls*.jsonl` (5 IDX calls) hold forecasts only and persist no outcome; `llm_arm.workbench.resolve` imports BASE5 outcomes from the Speculation Register when it scores, so it inherits that register's numbers. `research/GUIDANCE_REVISION_v1/paper/ledger.jsonl` is US. The backtest runs under `results/` use 2023 windows and cannot touch sessions on or after 2026-10-19. These were read, not replayed.
- **The code dirs, the repository and the frozen inputs were not touched.** The harness only hashes them and runs byte-identical overlay copies with bytecode writing off; snapshots of both code dirs, the repository's `paper/` and `research/` and the frozen inputs taken before and after the run are identical. Any `__pycache__` folders that already existed in the code dirs when the run started are listed in `run_meta.json` and were left as they were.
- **Environment.** python 3.13.17, numpy 2.5.3, pandas 3.0.5. The harness is deterministic; the Reproduction section says whether this run matched the previous one.

## Reproduction

This run was compared with the previous run in this folder: 8 of 8 deterministic outputs are byte-identical (results.csv, trades.csv, baseline_gate.csv, family_census.csv, lock_cells_changed.csv, learner_changes.csv, code_callers.txt, summary.json). `run_meta.json` has the sha256 of each output.

## Appendix: all 84 catalyst trades under B and C

Exit session and net return after fees. *Same* means the exit and the return are unchanged in C.

| Set | Role | Name | Exit B | Net B | Exit C | Net C | |
|---|---|---|---|---|---|---|---|
| AALI | candidate | AALI | 2026-10-30 | +1.18% | 2026-10-30 | +1.18% | same |
| AALI | twin | BSSR | 2026-10-30 | +1.08% | 2026-10-30 | +1.08% | same |
| AALI | twin | AADI | 2026-10-30 | +2.73% | 2026-10-30 | +2.73% | same |
| AALI | twin | INTP | 2026-10-30 | +0.96% | 2026-10-30 | +0.96% | same |
| AALI | twin | ITMG | 2026-10-30 | +0.82% | 2026-10-30 | +0.82% | same |
| AALI | twin | PKPK | 2026-10-30 | -5.51% | 2026-10-30 | -5.51% | same |
| CUAN | candidate | CUAN | 2026-10-30 | -7.20% | 2026-11-02 | -0.89% | **rolled** |
| CUAN | twin | IRSX | 2026-10-30 | -6.98% | 2026-11-02 | -3.22% | **rolled** |
| CUAN | twin | NICL | 2026-10-30 | +2.27% | 2026-10-30 | +2.27% | same |
| CUAN | twin | ARTO | 2026-10-30 | -5.05% | 2026-10-30 | -5.05% | same |
| CUAN | twin | EXCL | 2026-10-30 | +5.42% | 2026-10-30 | +5.42% | same |
| CUAN | twin | JARR | 2026-10-30 | -0.40% | 2026-10-30 | -0.40% | same |
| ELSA | candidate | ELSA | 2026-10-30 | +0.40% | 2026-10-30 | +0.40% | same |
| ELSA | twin | ULTJ | 2026-10-30 | +0.07% | 2026-10-30 | +0.07% | same |
| ELSA | twin | ACES | 2026-10-30 | +0.85% | 2026-10-30 | +0.85% | same |
| ELSA | twin | GULA | 2026-10-30 | -6.50% | 2026-10-30 | -6.50% | same |
| ELSA | twin | AYAM | 2026-10-30 | +0.02% | 2026-10-30 | +0.02% | same |
| ELSA | twin | CLEO | 2026-10-30 | -5.61% | 2026-10-30 | -5.61% | same |
| HEAL | candidate | HEAL | 2026-10-30 | -0.40% | 2026-10-30 | -0.40% | same |
| HEAL | twin | UNSP | 2026-10-30 | -7.35% | 2026-11-02 | -3.49% | **rolled** |
| HEAL | twin | MSTI | 2026-10-30 | -2.48% | 2026-10-30 | -2.48% | same |
| HEAL | twin | MOLI | 2026-10-30 | -0.40% | 2026-10-30 | -0.40% | same |
| HEAL | twin | AVIA | 2026-10-30 | +1.65% | 2026-10-30 | +1.65% | same |
| HEAL | twin | MITI | 2026-10-30 | -7.04% | 2026-11-02 | -5.38% | **rolled** |
| ISAT | candidate | ISAT | 2026-10-30 | -7.20% | 2026-11-02 | -2.44% | **rolled** |
| ISAT | twin | EXCL | 2026-10-30 | +5.42% | 2026-10-30 | +5.42% | same |
| ISAT | twin | EMTK | 2026-10-30 | -3.02% | 2026-10-30 | -3.02% | same |
| ISAT | twin | SSIA | 2026-10-30 | -5.16% | 2026-10-30 | -5.16% | same |
| ISAT | twin | ARCI | 2026-10-30 | -7.36% | 2026-11-02 | -6.29% | **rolled** |
| ISAT | twin | TEBE | 2026-10-30 | -7.28% | 2026-11-02 | -3.99% | **rolled** |
| MIKA | candidate | MIKA | 2026-10-30 | -4.76% | 2026-10-30 | -4.76% | same |
| MIKA | twin | FORE | 2026-10-30 | -3.93% | 2026-10-30 | -3.93% | same |
| MIKA | twin | ASPI | 2026-10-30 | -7.00% | 2026-11-04 | -5.68% | **rolled** |
| MIKA | twin | DGWG | 2026-10-30 | -1.93% | 2026-10-30 | -1.93% | same |
| MIKA | twin | HBAT | 2026-10-30 | +0.99% | 2026-10-30 | +0.99% | same |
| MIKA | twin | NRCA | 2026-10-30 | -3.29% | 2026-10-30 | -3.29% | same |
| PGEO | candidate | PGEO | 2026-10-30 | -6.11% | 2026-10-30 | -6.11% | same |
| PGEO | twin | CMNT | 2026-10-30 | -1.73% | 2026-10-30 | -1.73% | same |
| PGEO | twin | CMRY | 2026-10-30 | -1.10% | 2026-10-30 | -1.10% | same |
| PGEO | twin | CTRA | 2026-10-30 | -1.27% | 2026-10-30 | -1.27% | same |
| PGEO | twin | HMSP | 2026-10-30 | +2.69% | 2026-10-30 | +2.69% | same |
| PGEO | twin | DMAS | 2026-10-30 | -7.01% | 2026-11-02 | -12.60% | **rolled** |
| PTBA | candidate | PTBA | 2026-10-30 | +5.46% | 2026-10-30 | +5.46% | same |
| PTBA | twin | MEDC | 2026-10-30 | +3.32% | 2026-10-30 | +3.32% | same |
| PTBA | twin | CMNT | 2026-10-30 | -1.73% | 2026-10-30 | -1.73% | same |
| PTBA | twin | CMRY | 2026-10-30 | -1.10% | 2026-10-30 | -1.10% | same |
| PTBA | twin | AKRA | 2026-10-30 | -2.18% | 2026-10-30 | -2.18% | same |
| PTBA | twin | GULA | 2026-10-30 | -6.50% | 2026-10-30 | -6.50% | same |
| SCMA | candidate | SCMA | 2026-10-30 | -0.40% | 2026-10-30 | -0.40% | same |
| SCMA | twin | MDIA | 2026-10-30 | -6.87% | 2026-11-02 | -0.40% | **rolled** |
| SCMA | twin | KOTA | 2026-10-30 | -6.70% | 2026-11-02 | -7.96% | **rolled** |
| SCMA | twin | LUCY | 2026-10-30 | -10.36% | 2026-11-02 | -12.85% | **rolled** |
| SCMA | twin | MNCN | 2026-10-30 | -2.77% | 2026-10-30 | -2.77% | same |
| SCMA | twin | KIJA | 2026-10-30 | -4.81% | 2026-10-30 | -4.81% | same |
| SMGR | candidate | SMGR | 2026-10-30 | -2.59% | 2026-10-30 | -2.59% | same |
| SMGR | twin | DEWI | 2026-10-30 | -3.93% | 2026-10-30 | -3.93% | same |
| SMGR | twin | PRDA | 2026-10-30 | -1.49% | 2026-10-30 | -1.49% | same |
| SMGR | twin | AUTO | 2026-10-30 | -0.70% | 2026-10-30 | -0.70% | same |
| SMGR | twin | DMAS | 2026-10-30 | -7.01% | 2026-11-02 | -12.60% | **rolled** |
| SMGR | twin | CTRA | 2026-10-30 | -1.27% | 2026-10-30 | -1.27% | same |
| SMRA | candidate | SMRA | 2026-10-30 | +0.42% | 2026-10-30 | +0.42% | same |
| SMRA | twin | PRDA | 2026-10-30 | -1.49% | 2026-10-30 | -1.49% | same |
| SMRA | twin | ACES | 2026-10-30 | +0.85% | 2026-10-30 | +0.85% | same |
| SMRA | twin | DMAS | 2026-10-30 | -7.01% | 2026-11-02 | -12.60% | **rolled** |
| SMRA | twin | TOWR | 2026-10-30 | -0.40% | 2026-10-30 | -0.40% | same |
| SMRA | twin | SMDR | 2026-10-30 | -7.21% | 2026-11-02 | -7.21% | rolled, same return |
| TINS | candidate | TINS | 2026-10-30 | +1.26% | 2026-10-30 | +1.26% | same |
| TINS | twin | AMRT | 2026-10-30 | -4.57% | 2026-10-30 | -4.57% | same |
| TINS | twin | RATU | 2026-10-30 | -7.34% | 2026-11-03 | -11.41% | **rolled** |
| TINS | twin | EMTK | 2026-10-30 | -3.02% | 2026-10-30 | -3.02% | same |
| TINS | twin | BUVA | 2026-10-30 | -6.92% | 2026-11-04 | -20.56% | **rolled** |
| TINS | twin | HRTA | 2026-10-30 | -5.68% | 2026-10-30 | -5.68% | same |
| TKIM | candidate | TKIM | 2026-10-30 | +0.82% | 2026-10-30 | +0.82% | same |
| TKIM | twin | PKPK | 2026-10-30 | -5.51% | 2026-10-30 | -5.51% | same |
| TKIM | twin | AADI | 2026-10-30 | +2.73% | 2026-10-30 | +2.73% | same |
| TKIM | twin | UNTR | 2026-10-30 | -1.82% | 2026-10-30 | -1.82% | same |
| TKIM | twin | ICBP | 2026-10-30 | -2.19% | 2026-10-30 | -2.19% | same |
| TKIM | twin | INKP | 2026-10-30 | +0.36% | 2026-10-30 | +0.36% | same |
| UNVR | candidate | UNVR | 2026-10-30 | -1.11% | 2026-10-30 | -1.11% | same |
| UNVR | twin | ANTM | 2026-10-30 | -2.26% | 2026-10-30 | -2.26% | same |
| UNVR | twin | SSMS | 2026-10-30 | -0.40% | 2026-10-30 | -0.40% | same |
| UNVR | twin | AMMN | 2026-10-30 | -2.80% | 2026-10-30 | -2.80% | same |
| UNVR | twin | ESSA | 2026-10-30 | -1.39% | 2026-10-30 | -1.39% | same |
| UNVR | twin | HRUM | 2026-10-30 | -0.40% | 2026-10-30 | -0.40% | same |

## Files

`harness.py` (one command), `results.csv` (one row per replayed record: 14 catalyst, 23 speculation, 93 ledger, 238 learner, with source line, record id and record hash), `trades.csv` (one row per replayed trade), `baseline_gate.csv` (field-by-field gate per record), `family_census.csv`, `lock_cells_changed.csv`, `learner_changes.csv`, `code_callers.txt`, `summary.json`, `run_meta.json`.
