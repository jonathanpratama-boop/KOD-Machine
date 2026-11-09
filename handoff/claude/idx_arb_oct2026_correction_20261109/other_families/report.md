# IDX lower-limit correction: effect on the Catalyst Register and the other record families (addendum)

Paper trading only, no real money. Everything below is a *final-bar replay*: the real functions of the shipped code (B) and the corrected code (C) run on the only surviving raw pull (`yahoo_recent-20261106T101853Z.jsonl`, sha256 `3a27d3445b3d`, 920 tickers, last bar 2026-11-06). Nothing was edited: no ledger, no register, no code dir.

## The numbers

- **Catalyst register: 14 IDX RESOLUTION rows**, all `IDX_INDEX` window `RUNUP` (signal 2026-10-28, buy the 2026-10-29 close, sell the 2026-10-30 close, one session). 84 trades (14 candidates, 70 twins), every sale on 2026-10-30, after both October rule changes.
- **Baseline gate passed.** The B replay reproduces 14 of 14 recorded rows. 1596 leaves compared per variant; every string, date, status, boolean and count identical; 704 of 868 numeric leaves bit-identical, the rest differ by at most 3.3e-16 (floating-point noise, diagnosed below).
- **Under the corrected rules (C), 9 of 14 rows change** (CUAN, HEAL, ISAT, MIKA, PGEO, SCMA, SMGR, SMRA, TINS); 5 do not (AALI, ELSA, PTBA, TKIM, UNVR). 17 of 84 trades change their exit (2 candidates, 15 twin slots; 15 distinct names), 16 of them change their return. Each one was closing 6.7% to 7.0% below the previous close on 2026-10-30, which the old 15% rule let sell and the 7% rule locks, so the sale rolls to the next sellable session (1 session: 14 trades, 2 sessions: 1 trades, 3 sessions: 2 trades).
- **The published line moves.** `paper/CATALYSTS.md` says: *RUNUP: paired 14, mean signed diff +1.16%, share with the flow 64%*. Recomputed with the register's own `statistics()`/`render()`: recorded rows +1.16% and 64%; B replay +1.16% and 64% (identical); **C replay +1.35% and 71%** (10 of 14, was 9 of 14). One graded statement flips: ISAT `WITH_FLOW_RUNUP` goes False to True, so the calibration row's realised rate moves from 0.64 to 0.71; the Brier terms stay 0.250 (prior 0.5).
- **Only one other family has IDX values that depend on the lock and was not covered: `learner_v2.jsonl`** (26 IDX rows), and only through its training labels. Replayed with the learner's own code, the flipped label shifts the raw forecast probabilities of 202 of 238 forecast records (all families, 24 of the 26 IDX records) by at most 0.0398; published probabilities and calls do not change. A separate effect: the ALKA BASE5 speculation row cannot be resolved under C on the last bar (two twins are locked on 2026-11-06), which moves 3 IDX forecasts' published `RUN30_5`/`PUMP30_5` probability by 0.0235.
- Every other family under `paper/` has no IDX row that depends on the lock (table below). Scans, decisions, sets, tags and the US, crypto and book/account ledgers are independent of `lock_down`.

## Catalyst register, row by row

Signed difference = (candidate net minus twins' mean net) x direction; `with flow` = signed difference above zero (`WITH_FLOW_RUNUP`). Source = line in `paper/catalysts.jsonl`, record hash prefix. Net returns after the paper fees.

| Line | Set (ticker) | Record hash | Dir | Candidate net B | Candidate net C | Candidate exit C | Signed diff B | Signed diff C | with flow B | with flow C | Trades changed in C |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 74 | AALI | `601abd15813c` | +1 | +1.18% | +1.18% | 2026-10-30 | +1.16% | +1.16% | yes | yes | 0 of 6 |
| 75 | CUAN | `fa1e6a590b0d` | -1 | -7.20% | -0.89% | 2026-11-02 | +6.25% | +0.69% | yes | yes | 2 of 6 (cand CUAN;IRSX) |
| 76 | ELSA | `fd088c2bb52b` | +1 | +0.40% | +0.40% | 2026-10-30 | +2.64% | +2.64% | yes | yes | 0 of 6 |
| 77 | HEAL | `85a4dcaf1e04` | -1 | -0.40% | -0.40% | 2026-10-30 | -2.73% | -1.62% | no | no | 2 of 6 (UNSP;MITI) |
| 78 | ISAT | `e70c71b8af89` | +1 | -7.20% | -2.44% | 2026-11-02 | -3.72% | +0.17% | no | yes | 3 of 6 (cand ISAT;ARCI;TEBE) |
| 79 | MIKA | `5eee604f53e3` | -1 | -4.76% | -4.76% | 2026-10-30 | +1.73% | +2.00% | yes | yes | 1 of 6 (ASPI) |
| 80 | PGEO | `187d9466759b` | -1 | -6.11% | -6.11% | 2026-10-30 | +4.42% | +3.31% | yes | yes | 1 of 6 (DMAS) |
| 81 | PTBA | `e8bd59308b14` | +1 | +5.46% | +5.46% | 2026-10-30 | +7.10% | +7.10% | yes | yes | 0 of 6 |
| 82 | SCMA | `784dd5c92879` | -1 | -0.40% | -0.40% | 2026-10-30 | -5.90% | -5.36% | no | no | 3 of 6 (MDIA;KOTA;LUCY) |
| 83 | SMGR | `0547782a29b3` | +1 | -2.59% | -2.59% | 2026-10-30 | +0.29% | +1.41% | yes | yes | 1 of 6 (DMAS) |
| 84 | SMRA | `392a6322a112` | -1 | +0.42% | +0.42% | 2026-10-30 | -3.47% | -4.59% | no | no | 2 of 6 (DMAS;SMDR) |
| 85 | TINS | `930ca03e7207` | +1 | +1.26% | +1.26% | 2026-10-30 | +6.77% | +10.31% | yes | yes | 2 of 6 (RATU;BUVA) |
| 86 | TKIM | `8fd7dd52d65b` | +1 | +0.82% | +0.82% | 2026-10-30 | +2.10% | +2.10% | yes | yes | 0 of 6 |
| 87 | UNVR | `3f062b1898ad` | -1 | -1.11% | -1.11% | 2026-10-30 | -0.34% | -0.34% | no | no | 0 of 6 |

Trades whose exit changes (all sold on 2026-10-30 under B; the target session is 2026-10-30 for every trade):

| Set | Role | Name | Move on 2026-10-30 | ARB B | ARB C | Close | Exit B / net B | Exit C / net C | Rolled |
|---|---|---|---|---|---|---|---|---|---|
| CUAN | candidate | CUAN | -6.83% | 350 | 382 | 382 | 2026-10-30 / -7.20% | 2026-11-02 / -0.89% | 1 |
| CUAN | twin | IRSX | -6.60% | 181 | 198 | 198 | 2026-10-30 / -6.98% | 2026-11-02 / -3.22% | 1 |
| HEAL | twin | UNSP | -6.98% | 220 | 240 | 240 | 2026-10-30 / -7.35% | 2026-11-02 / -3.49% | 1 |
| HEAL | twin | MITI | -6.67% | 204 | 224 | 224 | 2026-10-30 / -7.04% | 2026-11-02 / -5.38% | 1 |
| ISAT | candidate | ISAT | -6.83% | 1250 | 1365 | 1365 | 2026-10-30 / -7.20% | 2026-11-02 / -2.44% | 1 |
| ISAT | twin | ARCI | -6.99% | 795 | 865 | 865 | 2026-10-30 / -7.36% | 2026-11-02 / -6.29% | 1 |
| ISAT | twin | TEBE | -6.91% | 1420 | 1550 | 1550 | 2026-10-30 / -7.28% | 2026-11-02 / -3.99% | 1 |
| MIKA | twin | ASPI | -6.62% | 645 | 705 | 705 | 2026-10-30 / -7.00% | 2026-11-04 / -5.68% | 3 |
| PGEO | twin | DMAS | -6.63% | 167 | 183 | 183 | 2026-10-30 / -7.01% | 2026-11-02 / -12.60% | 1 |
| SCMA | twin | MDIA | -6.49% | 66 | 72 | 72 | 2026-10-30 / -6.87% | 2026-11-02 / -0.40% | 1 |
| SCMA | twin | KOTA | -6.33% | 68 | 74 | 74 | 2026-10-30 / -6.70% | 2026-11-02 / -7.96% | 1 |
| SCMA | twin | LUCY | -10.00% | 102 | 112 | 108 | 2026-10-30 / -10.36% | 2026-11-02 / -12.85% | 1 |
| SMGR | twin | DMAS | -6.63% | 167 | 183 | 183 | 2026-10-30 / -7.01% | 2026-11-02 / -12.60% | 1 |
| SMRA | twin | DMAS | -6.63% | 167 | 183 | 183 | 2026-10-30 / -7.01% | 2026-11-02 / -12.60% | 1 |
| SMRA | twin | SMDR | -6.84% | 324 | 354 | 354 | 2026-10-30 / -7.21% | 2026-11-02 / -7.21% | 1 |
| TINS | twin | RATU | -6.97% | 1770 | 1935 | 1935 | 2026-10-30 / -7.34% | 2026-11-03 / -11.41% | 2 |
| TINS | twin | BUVA | -6.55% | 286 | 314 | 314 | 2026-10-30 / -6.92% | 2026-11-04 / -20.56% | 3 |

## Mechanism

`catalysts.resolve_set` runs `speculation.simulate` for the candidate and each twin. `simulate` sells at the first session at or after the target where `tradeable and not lock_down`. `lock_down` (built in `Market.build`) is: the bar traded, the close is below the reference and at or below the day's ARB. B keeps the 15% ARB from 2026-09-28; C applies 7% from 2026-10-19 (and a nominal Rp1 ARB for references Rp11 to 14 from 2026-10-20). ARA (and so `lock_up`) is identical in B and C (0 cells differ), and the two markets differ only on lower-limit cells on or after 2026-10-19: 1892 cells of 125120 are locked under C but not B, 0 the other way, 0 before 2026-10-19; 4 of them have a reference at or below Rp14 (the Rp11-14 rule), the rest are the 7% rule. See `lock_cells_changed.csv`. The 14 rows were resolved on 2026-10-30 at 10:59 UTC, when the sale on that day was not locked under B; under C nine of the sets could not have resolved that day and would have waited for the roll.

## Baseline gate, diagnosis of the tiny differences

The 14 rows were written on the 2026-10-30 pull (manifest sha256 `cc80bfb2b36a`, which is the manifest file kept in the frozen inputs; its raw payloads were not kept). The replay uses the 2026-11-06 pull, whose 200-day window starts later (2026-04-20 against 2026-04-13). The reference chain `level` is a cumulative sum of log returns from the first bar of the window, so `level[exit]/level[entry]` differs in the last bits. The numeric leaves that are not bit-identical are exactly: `/candidate/trade/gross_return`, `/candidate/trade/mae`, `/candidate/trade/mfe`, `/candidate/trade/net_return`, `/paired/candidate_net`, `/paired/diff`, `/paired/twins_mean_net`, `/paired/twins_median_net`, `/twins/#/trade/gross_return`, `/twins/#/trade/mae`, `/twins/#/trade/mfe`, `/twins/#/trade/net_return`; the largest difference is 3.3e-16. Entry prices, sessions, exit reasons, costs, statuses, units, cone outcomes and Brier terms are identical.

## Other record families

Counted from the committed snapshot (`market` absent = IDX in the ledger). `touching` = a session field (signal, entry, exit, scan) on or after 2026-10-19; `exit on/after` = a trade sold on or after that date (the only place the lock can enter).

| File | Record family | IDX rows | Touching | Exit on/after | Depends on the lock | Path | Replayable |
|---|---|---|---|---|---|---|---|
| `ledger.jsonl` | SCAN (IDX; market absent = IDX) | 23 | 15 |  | no (none) | paper.scan_frame / rules read lock_up and never lock_down (grep); ARA is identical in B and C | n/a (scan features were computed on each day's own pull; no lock dependence) |
| `ledger.jsonl` | DECISION (IDX; market absent = IDX) | 126 | 88 |  | no (none) | paper._decide_v3 sizes on the hard-coded Policy.max_stop_distance 0.15 and prints '15% below the entry'; it never calls market.limits | n/a |
| `ledger.jsonl` | OUTCOME (IDX) | 93 | 65 | 35 | yes (direct) | paper.score_pending -> paper.score -> _score_plan -> execution.execute (sellable = tradeable & ~lock_down; roll to next_sellable) | legacy loop sellable | yes (covered by the earlier work) |
| `speculations.jsonl` | SPECULATION_SET (IDX) | 26 | 26 |  | no (none) | speculation.build_set: twins and signal from the scan's features | n/a |
| `speculations.jsonl` | RESOLUTION BASE5 (IDX) | 2 | 2 | 2 | yes (direct) | speculation.resolve_set -> simulate(): sellable(k) = tradeable & ~lock_down; x = first sellable session >= target, None (pending) if none | yes (cross-check here; covered by the earlier work) |
| `speculations.jsonl` | RESOLUTION NEXT1/PATH20 (IDX) | 21 | 21 |  | no (none) | path windows: next_return / path_statement use closes only | yes (reproduced here as part of the 23) |
| `catalysts.jsonl` | BATCH (IDX_INDEX) | 1 | 1 |  | no (none) | catalysts.idx_index_batch: event list statuses | n/a |
| `catalysts.jsonl` | CATALYST_SET (IDX_INDEX) | 14 | 14 |  | no (none) | catalysts.idx_index_batch: twins by draw_twins from the scan features | n/a |
| `catalysts.jsonl` | TAG (IDX_INDEX) | 14 | 14 |  | no (none) | catalysts.dilution_tags: EmitenNews headlines | n/a |
| `catalysts.jsonl` | RESOLUTION (IDX_INDEX) | 14 | 14 | 14 | yes (direct) | catalysts.resolve_set -> speculation.simulate (candidate and each twin): sellable(k) = tradeable & ~lock_down; the sale rolls to the next sellable session | yes (the priority of this addendum) |
| `catalysts.jsonl` | all US rows (BATCH/CATALYST_SET/TAG; no RESOLUTION yet) | 212 | 212 |  | no (none) | US markets are built with price_limits=False: lock_down is all False | n/a (IDX rows: 0) |
| `learner_v2.jsonl` | LEARNER2_FORECAST (SPEC_IDX) | 26 | 26 | 24 | yes (indirect (training labels)) | learner2.train -> live_rows -> outcomes() reads RESOLUTION cone outcomes: IDX_INDEX WITH_FLOW_RUNUP (shared RELATIVE slope) and SPEC_IDX BASE5 statements (anchors) | yes (the learner's own _record() on each record's ledger prefix, with replayed labels) |
| `learner_v2.jsonl` | LEARNER2_FORECAST (US and CRYPTO rows, for reference) | 212 | 212 | 178 | indirect only (indirect (shared slope)) | same labels reach US/CRYPTO forecasts through the shared RELATIVE slope | yes (same replay) |
| `learner_v3.jsonl` | LEARNER3_FORECAST (SPEC_US) | 0 | 0 |  | no (none) | US only; trains on SPEC_US rows and its own forecasts | n/a (IDX rows: 0) |
| `learner.jsonl` | LEARNER_FORECAST (SEC13D) | 0 | 0 |  | no (none) | US SEC13D only | n/a (IDX rows: 0) |
| `paper_book.jsonl` | BOOK_PLAN | 0 | 0 |  | no (none) | US spikes only | n/a (IDX rows: 0) |
| `paper_account.jsonl` | ACCT_* (US paper account) | 0 | 0 |  | no (none) | exec_us on US bars only | n/a (IDX rows: 0) |
| `crypto_account.jsonl` | ACCT_* / CRYPTO_QUOTE | 0 | 0 |  | no (none) | crypto | n/a (IDX rows: 0) |
| `premove_shadow.jsonl` | PREMOVE_SHADOW_* | 0 | 0 |  | no (none) | crypto (Binance) only | n/a (IDX rows: 0) |
| `microstructure/crypto.jsonl` | TIMELINE/BOOK | 0 | 0 |  | no (none) | crypto order books | n/a (IDX rows: 0) |
| `sensors/sensors.jsonl` | SENSOR_ALERT emitennews_dilution (IDX-related) | 4 | 4 |  | no (none) | news headlines, no prices | n/a |
| `scans/` | scan directories (IDX = names without a market infix) | 23 | 15 |  | no (none) | features.csv built by rules that read lock_up only | n/a |
| `catalysts_form4/` | EDGAR Form 4 dumps (US) | 0 | 0 |  | no (none) | no price or lock input | n/a |
| `timestamps/` | RFC 3161 tokens | 0 | 0 |  | no (none) | no price or lock input | n/a |
| `sensors/raw/` | raw feed pulls | 0 | 0 |  | no (none) | no price or lock input | n/a |
| `microstructure/raw/` | crypto raw books | 0 | 0 |  | no (none) | no price or lock input | n/a |

Derived reports (`CATALYSTS.md`, `SPECULATIONS.md`, `LEARNER_V2.md` and the other `.md` files) are rendered from the ledgers and carry the same numbers; only `CATALYSTS.md`'s IDX_INDEX section changes through this addendum's rows.

## Second-order: learner_v2

`learner_v2.jsonl` trains on every graded statement of the registers that resolved before each forecast. The `IDX_INDEX WITH_FLOW_RUNUP` labels (14 of them) feed the slope shared by all relative statements (`BEATS_TWINS_k` and so on, every family and market); the `SPEC_IDX` BASE5 labels feed the Speculation Register anchors. Each forecast record carries the ledger state it was computed from, so the learner's own `_record()` can be re-run per record with changed labels (first-order: each record's earlier learner records stay as recorded).

| World | Records changed in raw forecasts (all / IDX) | Published changed (all / IDX) | Calls changed | Max raw change | Max published change |
|---|---|---|---|---|---|
| recorded ledgers (baseline: must reproduce) | 0 / 0 | 0 / 0 | 0 | 0.00000 | 0.00000 |
| B-replayed labels (baseline: must reproduce) | 0 / 0 | 0 / 0 | 0 | 0.00000 | 0.00000 |
| C labels at the recorded timestamps | 202 / 24 | 0 / 0 | 0 | 0.03976 | 0.00000 |
| ALKA BASE5 row absent (pending under C) | 78 / 3 | 3 / 3 | 0 | 0.02395 | 0.02352 |
| both, recorded timestamps | 202 / 24 | 3 / 3 | 0 | 0.03976 | 0.02352 |
| both, labels available only after their roll completes | 202 / 24 | 3 / 3 | 0 | 0.03841 | 0.02352 |

Changed means beyond the learner's own verification tolerance (2e-06). The first two rows are the baseline gate for this family: every one of the 238 recorded forecasts is reproduced from the recorded ledgers and from the B-replayed labels.

## Cross-check of the earlier work: the 23 IDX speculation rows

Replayed with `speculation.resolve_set` (NEXT1 21, BASE5 2). B reproduces 22 of 23; SPEC-SCAN-2026-11-04-F1_ARA-TMPO NEXT1 differs in /cone/0/brier;/cone/0/outcome;/cone/1/brier;/cone/1/outcome;/cone/2/brier;/cone/. Under C: ALKA BASE5 is PENDING (a sale rolls past the last bar).
The pending row `SPEC-SCAN-2026-10-29-F1_ARA-ALKA`: KDTN closes 238 on 2026-11-06 from 254, ARB 216 under B and 238 under C; WBSA closes 344 on 2026-11-06 from 368, ARB 314 under B and 344 under C.

## Caveats and unresolved

- **Final-bar replay, not a re-run of 2026-10-30.** Only the 2026-11-06 raw pull survives; the rows were written on the 2026-10-30 pull. A rolled sale is resolved with the bars up to 2026-11-06. Under C the nine changed sets could not have been written on 2026-10-30 (their sales roll), so the register would have written them on 2026-11-02 or 2026-11-04; the learner results below treat that explicitly in the last world.
- **The rule schedule is the one in market.py (C), unverified by me.** I did not check the 7% from 2026-10-19 or the Rp1 ARB against decree texts; the module itself says the decrees were not read and that on 2026-10-19 the real limit for references Rp11-14 is unknown (nothing here depends on that day). The names that change here all closed 6.7% to 7.0% below the previous close, so the result depends on the 7% rule being right on 2026-10-30 and is sensitive to tick rounding of the limit price.
- **Board membership is not in the data.** `limits()` models the regular boards for every name; a name on a 10% board is over-locked by a 7% fall under C. I did not test which of the 15 names change because of that.
- **The register is append-only.** I changed no row. A correction would be new RESOLUTION rows whose `revises` names the earlier hash; whether to append them (and a corrected CATALYSTS.md line) is the owner's decision. The published line and calibration row would read as in the C column above.
- **Descriptive only.** The register labels IDX_INDEX 'never tested'; the shift in the mean signed difference is 0.19 percentage points against a standard error of 1.10, with 14 sets from one index review and one signal session.
- **Learner replay is first-order.** Each forecast is recomputed from its own recorded ledger prefix and the recorded earlier learner records; compounding through later forecasts' gates is not followed. The timing treatment for C-world availability (a changed row becomes available to the first learner batch on the calendar day of its last roll session, minus one second) is my assumption.
- **Learner 'changed' is measured against the learner's own verification tolerance (2e-6);** the raw-probability shifts are small but would make `paper-verify` fail for those records if the labels were corrected in place, because verify retrains from the registers.
- **The Speculation Register cross-check is not the earlier analyst's number.** B reproduces 22 of 23 rows; the 1 that differ (SPEC-SCAN-2026-11-04-F1_ARA-TMPO NEXT1) differ in data, not in the lock: the recorded row left statements ungraded that the final pull grades, consistent with a bar present in the final pull and missing on the 2026-11-05 pull (the raw 2026-11-05 payload did not survive, so I cannot confirm it).
- **Decision text and sizing are stale after 2026-10-19 but do not read market.py.** DECISION rows size against the hard-coded `Policy.max_stop_distance` 0.15 and say 'locked at ARB, 15% below the entry'. The correction cannot change them; PAPER-POLICY-v4 would need a new version.
- **POST20 windows of the same 14 sets are not resolvable yet** (signal 2026-10-28 plus 22 sessions, 2026-11-27 at the earliest), so they will be the first rows to be written under whichever rules are in force.
- **Outside `paper/`:** `research/LLM_ARM_v1/calls*.jsonl` (5 IDX calls) hold forecasts only and persist no outcome; `llm_arm.workbench.resolve` imports BASE5 outcomes from the Speculation Register at scoring time, so it inherits that register's numbers. `research/GUIDANCE_REVISION_v1/paper/ledger.jsonl` is US. Backtest results under `results/` use 2023 windows and cannot touch sessions on or after 2026-10-19. Not examined in depth.
- **The ledger OUTCOME rows were not replayed here** (the earlier work covers them); the census only counts how many touch sessions on or after 2026-10-19.
- **Environment:** python 3.13.17, numpy 2.5.3, pandas 3.0.5; the replay is deterministic and was run twice (see the end of this report's source run).

## Files

`harness.py` (one command), `results.csv` (one row per replayed record: 14 catalyst, 23 speculation, 238 learner), `trades.csv` (one row per replayed trade), `baseline_gate.csv`, `family_census.csv`, `lock_cells_changed.csv`, `learner_changes.csv`, `code_callers.txt`, `summary.json`.
