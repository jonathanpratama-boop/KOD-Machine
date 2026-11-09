# Consumer sweep: who reads the IDX lower-limit lock (Market.lock_down) or calls market.limits()

Independent consumer sweeper, 2026-11-09. Nothing was replayed. Every count below is recomputed from the committed files by
`sweep/scripts/counts_all.py` (output: `sweep/counts.json`); the rule comparison is `sweep/scripts/limits_grid.py`; the raw
keyword grep is `sweep/raw_grep_all.txt` (1,248 hit lines). I read every production hit, and confirmed the list with an AST
pass (Attribute accesses `.lock_down`, `.limits`, `.regime_index`, `.regime_labels`, `.REGIMES`, `.special_limits`, and every
`import ... market` / `import ... execution`). Line numbers are those of the repository files, which are byte-identical to
`code_B`/`code_C` except `idxsig/market.py` (for market.py I cite `code_C` lines; HEAD adds 6 lines of docstring).

Independence: I did not open `handoff/claude/idx_arb_oct2026_correction_20261109`, the tests of the correction, or any of the directories I
was told to avoid. I read `idx-signals/README.md` lines 196-240 (the correction's text) once, after the map was drafted, as a cross-check:
it agrees that the legacy scorer gives no outcome for a locked horizon close and that no recorded decision depends on the 2026-10-19
Rp11-14 limit; I checked the second statement against the rows (section 8, item 5) and did not rely on the README for anything else.

State of the repository during the sweep: HEAD moved twice while I worked (927efb8bf, 2faf02f85: market.py docstrings, tests,
handoff and README text only). `git diff 04927b3c4 HEAD -- idx-signals/paper idx-signals/data idx-signals/results idx-signals/research`
is empty, so every ledger and register I counted is the base-commit snapshot.

## 1. Headline

1. The lower-limit lock is READ (as a value) in exactly four places: `execution.py:819` (exit roll in `execute`), `execution.py:724`
   (short-side guard), `speculation.py:459` (`simulate`, which `catalysts.py` also calls) and `paper.py:1670` (the legacy IDX scorer).
   `market.limits()` is called in exactly two places: `execution.py:414` (`Market.build`) and `panel.py:265` (limit QA). The regime table
   (`REGIMES`, `regime_index`, `regime_labels`) is read by `panel.py` and `e5.py` only.
2. Three persisted families store values that came out of the lock test: `paper/ledger.jsonl` OUTCOME rows (IDX 93; 40 carry an exit,
   35 of those exit on or after 2026-10-19), `paper/speculations.jsonl` RESOLUTION rows of window BASE5 (2 of the 23 IDX resolutions;
   11 simulated exits, all on 2026-11-06) and `paper/catalysts.jsonl` RESOLUTION rows (all 14 IDX resolutions, window RUNUP;
   84 simulated exits, all on 2026-10-30).
3. Derived families: `paper/learner_v2.jsonl` (202 of 238 sealed forecasts were trained with the 14 catalyst RUNUP outcomes in the
   shared RELATIVE model, 78 also with SPEC_IDX BASE5 outcomes), three derived reports (SPECULATIONS.md, CATALYSTS.md, LEARNER_V2.md) and
   the LLM_ARM_v1 IDX calls (8, not yet scored). Pending IDX work that will be computed with whichever market.py is live:
   33 decisions, 24 BASE5 sets, 14 POST20 sets.
4. `data/manifests/panel-*.json` (3 IDX manifests) hold `qa_limit_violations` and `market_regimes` computed with `limits()`/`REGIMES`;
   they do not read the lock, and as persisted (last session 2026-10-06 / 2026-10-13) they cannot change.
5. Things the lock-only view misses (section 8): the legacy scorer gives NO outcome when the horizon close is locked (rows can vanish,
   they do not roll); paper.py hard-codes the old 15% ARB (97 IDX decisions carry it); three frozen MSCI protocols pin the sha256 of
   market.py (they match B, not C); the new warning fires for US and crypto too after 2026-12-31; no persisted row records which
   market.py scored it.

## 2. What the correction changes (verified, not taken from the spec)

I evaluated `limits()` of `code_B` and `code_C` on 2,772 dates (2019-07-29 .. 2027-02-28) x 707 reference prices (all integers
Rp1-300, a log grid to Rp100,000, and every tick-band edge +-1):

- ARA is identical everywhere. So `lock_up`, every entry rule, `SKIP_ARA_LOCK` and every scan flag are unchanged.
- ARB is identical on every date before 2026-10-19 (0 differing cells). From 2026-10-19 ARB_C >= ARB_B in every cell (never lower);
  98.2% of the cells dated 2026-10-19 .. 2026-12-31 differ. References Rp1-10 never differ; Rp11-13 differ on 2026-10-19 only (ARB = ref
  under C) and match B afterwards (ref-1 equals B's rounded 15% limit); every reference from Rp14 up differs on every date. At usual price
  levels the lower limit moves from 15% to 7% below the reference (ref 100: ARB 85 -> 93; ref 500: 426 -> 466).
- Therefore `lock_down_C` is a superset of `lock_down_B`: only False -> True flips; `sellable_C` is a subset of `sellable_B`; an exit
  can only move later or become unavailable, never earlier. Domain of change: IDX bars (price_limits True) dated >= 2026-10-19,
  tradeable, with a reference, `close < ref`, and ARB_B < close <= ARB_C (a fall of about 7% to 15% below the reference, tick rounding
  aside); from 2026-10-20 also references Rp11-14 closing at or below ref-1.
- 2026-10-19, references Rp11-14: the 7% formula gives ARB = reference, so nothing can lock (needs `close < ref`). That is the day BTEK
  and TAXI closed 25% lower. No persisted lock-reading row involves them (section 8, item 5).
- Dates >= 2027-01-01 also differ (B: ARB = ARA again; C: 7% carried forward). No bar exists for those dates yet.
- New surface in market.py: `REGIMES` grows from 8 to 10 entries (the first 7 and their labels are unchanged; B's 2027-01-01 entry is
  replaced by 2026-10-19, 2026-10-20 and an UNCONFIRMED 2027-01-01 entry), `Regime.arb_abs_max`, `RULES_CONFIRMED_THROUGH`,
  `RulesUnconfirmedWarning`, `unconfirmed()`. `limits()` (code_C:143-172) warns for any date > 2026-12-31 and `Market.build` calls
  `limits()` before it discards the result for `price_limits=False`, so US and crypto markets built from 2027 data warn too.

## 3. Every reader

### 3.1 Readers of the lock VALUE (Market.lock_down)

| # | file:line | reads | influences | persisted in | IDX rows now | changes under the correction |
|---|---|---|---|---|---|---|
| A1 | `idxsig/execution.py:819-842`, `:954` (`execute`) | `sellable = tradeable & ~lock_down`, `next_sellable`, `found` | exit session (`exit_idx`), exit price, gross/net return, status (EXITED / EXIT_DATA_END / INCOMPLETE), `rolled_sessions` (callers derive mfe/mae from the exit); in `idx_events.run_events` and `backtest.run` also the `held_until` overlap skip | callers: `backtest.py:544,261` -> `results/runs/*/trades.csv.gz` (+summary.json, random_draws.csv); `idx_events.py:121,151` -> frozen research outputs; `paper.py:1478` (`_score_plan`) -> ledger OUTCOME only for decisions carrying `plan.execution_plan` | runs: 5 IDX of 17 (3 PLACEBO + 2 E1, windows end 2025-02-21 / 2023-12-29); ledger: 0 IDX decisions carry an execution_plan | Yes in principle (bars >= 2026-10-19). No persisted row can change: all IDX runs and research end before 2026-10-19. Live only if an E3 plan is ever validated |
| A2 | `idxsig/execution.py:724` | `m.lock_up.any() or m.lock_down.any()` for `side == "short"` | raises ValueError (short side not modelled under limits) | none | none | No. Short side is US/crypto (both arrays all False); on an IDX market `lock_up.any()` is already True |
| A3 | `idxsig/speculation.py:457-459` (`sellable`), `:484-496` (`x = next(k ...)`), `:466` (entry, lock_up) | `tradeable & ~lock_down` for market IDX only (US/crypto use `present & close>0`) | exit session `x`, exit_reason ("rolled N"), gross/net return, mfe/mae, sessions_held, `paired` (candidate vs twins), cone outcomes FADE10_5 / GAIN0_5 / BEATS_TWINS_5 (and via the learner DUMP10_5 / PUMP_AND_DUMP_5); returns None (window stays open, no RESOLUTION) when no bar from the target on is sellable and the data-end rule does not apply; one None twin holds back the whole set | `paper/speculations.jsonl` RESOLUTION window BASE5; also called from `catalysts.py:1208,1222` | speculations.jsonl: 49 IDX rows (26 SET, 23 RESOLUTION); lock-dependent: 2 RESOLUTION (BASE5: YPAS, ALKA); 11 simulated trades, all exit 2026-11-06 (the last bar of the final pull) at their horizon; 24 BASE5 pairs pending | Yes. All 11 exits sit on 2026-11-06: any newly locked bar there makes `x` None and the RESOLUTION would not exist yet |
| A3b | `idxsig/catalysts.py:1177-1252` (`resolve_set`; `spec.simulate` at `:1208` candidate, `:1222` twins) | same lock test through `simulate`, for the IDX_INDEX family (market IDX) | RESOLUTION candidate/twin trades, `paired.diff`, cone WITH_FLOW_RUNUP (and POST20 statements later) | `paper/catalysts.jsonl` RESOLUTION | catalysts.jsonl: 43 IDX rows (1 BATCH, 14 SET, 14 TAG, 14 RESOLUTION); all 14 RESOLUTION are window RUNUP (family IDX_INDEX); 84 simulated trades (14 candidates + 70 twins), all exit 2026-10-30 at their horizon; 14 POST20 pairs pending | Yes. This is the reviewer's miss: all 14 resolutions are exposed |
| A4 | `idxsig/paper.py:1670-1677` (legacy IDX scorer in `score`) | `sellable = tradeable & ~lock_down` at every session k in [e+1, e+5] | invalidation exit (first sellable bar with close <= stop) or horizon exit (k == e+5 and sellable); if no exit, `return None` forever (the loop never rolls past e+5) | `paper/ledger.jsonl` OUTCOME (market IDX) | ledger.jsonl: 242 IDX rows (23 SCAN, 126 DECISION, 93 OUTCOME). OUTCOME: 40 carry `paper_trade` (the only ones that reach the lock), 35 of those exit on or after 2026-10-19 (18 invalidation, 17 horizon), 5 earlier; 53 OUTCOME without a trade never read the lock; 0 trades have a rolled exit; 33 IDX decisions still have no OUTCOME | Yes for the 35 exits >= 2026-10-19: the exit can move later, change reason/return, or the row can disappear (None). The 5 earlier exits cannot change |
| A5 | name lists and generic copies: `execution.py:302` (`Market.FIELDS`, copied by `slice`, `window`, `truncate`, `with_registry`, `with_units`); `rules/__init__.py:89,114,141` (`RULE_FIELDS`, `CausalSource`, `RuleView` copy the array); `breakout.py:70` (`submarket`, US); `backtest.py:901` writes the field NAMES into summary.json | the array, never its meaning | nothing: no shipped rule reads `view.lock_down` (E1/E3/E5 read `lock_up`; E4/G/placebo read neither) | `results/runs/*/summary.json` `rule_view_fields` (17 files, names only) and research summaries | n/a | No |

Readers of the by-products `sellable`, `next_sellable`, `rolled_sessions` and `INCOMPLETE`: `execution.py:819-842,954` (producer);
`backtest.py:729` (writes the `rolled_sessions` column of `trades.csv.gz`; 5 IDX runs hold 73 + 51 + 182 + 138 + 137 trades with a roll,
all dated before 2026-10-19); `paper.py:1481-1482,1488-1499` (`_score_plan`: INCOMPLETE returns None, the exit_reason text "(rolled N
session(s) while locked at ARB or untraded)"); `speculation.py:522` (exit_reason "(rolled N)"); `idx_events.py:124-132` and `backtest.py:547-558`
(`held_until` from `exit_idx`). `crypto_replay.py` and `exec_us.py` have their own roll logic for crypto and US and do not use the Market lock.

### 3.2 Readers of limits() and the regime table (inputs of the lock, or QA)

| # | file:line | reads | influences | persisted in | IDX rows now | changes under the correction |
|---|---|---|---|---|---|---|
| B1 | `idxsig/execution.py:414-426` (`Market.build`) | `market.limits(safe_ref, day_grid)` -> ARA, ARB; `special_limits` (10%, unchanged); builds `lock_up` (:420) and `lock_down` (:421-423); zeros both when `price_limits=False` (:424-426) | creates the arrays every A-reader consumes | none directly (in memory) | n/a | lock_down: yes (False -> True, bars >= 2026-10-19). lock_up: no |
| B2 | `idxsig/panel.py:265-281` (`_limit_qa`), `:393-394` | `limits()`, `regime_index`, `REGIMES[idx].label/.start`, `regime_labels()` | QA counts per regime: rows, above_ara, below_arb, violations_priced_below_rp50, violations_other, other_violation_dates; and the regime table itself | `data/manifests/panel-<stamp>.json` keys `qa_limit_violations`, `market_regimes`. Nothing in the code reads them back | 3 IDX panel manifests (20261007T182306Z, 20261007T225823Z, last session 2026-10-06; 20261013T194245Z, last session 2026-10-13), each with 8 regimes listed and 7 QA regime rows | As persisted: no (frozen by the append-only guard; no bar >= 2026-10-19). Any panel rebuilt after the correction lists 10 regimes and adds QA rows for 2026-10-19+ (below_arb counts rise, they test the new table) |
| B3 | `idxsig/e5.py:41`, `:853-857` (`by_regime`) | `REGIMES`, `regime_index` on the signal dates | per-regime precision and paired excess, keyed by regime label (IDX only) | `research/E5/IDX/discovery/stage1.json`, `research/E5/v1.1/IDX/discovery/stage1.json` (key `COVID ARB 7%` only) | 2 frozen files | No. Frozen; labels of the first 7 regimes are unchanged |
| B4 | `idxsig/market.py` itself (`limits`, `regime_index`, `regime_labels`, `special_limits`) | definitions | | | | the change |

### 3.3 Callers that build the Market (they hand the lock arrays to section 3.1)

| file:line | market | notes |
|---|---|---|
| `paper.py:544-550` (`_market`) | IDX: `Market.from_panel(df)` (price_limits True); others `price_limits=False` | used by `scan_frame:603` (decisions), `score_pending:2245` (OUTCOME), `speculation.resolve_pending:853`, `catalysts.resolve_pending:1263`, `learner3.py:157` (US), `paper_account.py:434` (US) |
| `backtest.py:468` | by profile (IDX True; US, crypto False) | `run`; E9 and EXIT_ATR_v1 are US configurations |
| `e1.py:183`, `e5.py:1556,2148` | by profile | research harness; lock_up only (e1) |
| `event_study.py:35,85,115` | US only (`US.price_limits`) | zeros |
| `idx_events.py:88,121,151` | IDX by default (`price_limits=True`) | `prepare` / `run_events`; used by frozen research only |
| `cli.py:826-830` | IDX (`Market.from_panel(df)`) | `corporate_actions.build`: reads only ca_ratio, prev, close, listed_shares: lock-independent. Output `data/corporate_actions/ca_registry-*` (2 IDX builds) |
| `breakout.py:71` | US | one-name submarket |
| research scripts (section 6) | various | frozen |

### 3.4 Readers of lock_up only (unchanged by the correction)

`execution.py:629,769`; `e1.py:222,303,337`; `rules/moonshot_e1.py:109`, `moonshot_e3.py:97`, `moonshot_e5.py:374`; `paper.py:72,1643` (`E1_ARGS`,
fillable); `speculation.py:466`; research: `CASES_IDX_v1/packs.py:51`, `PATH_HISTORY_v1/build.py:69,114`, `build2.py:69,117`,
`feasibility.py:31`, `E1/d1_v1_1/equivalence_check.py:13`. Scan features (`ara`) and the 23 IDX `paper/scans/*/features.csv` are lock_up-based.

### 3.5 Hard-coded copies of the OLD ARB (not read from market.py, so the correction does not touch them)

`paper.py:106` `Policy.max_stop_distance = 0.15  # invalidation no further than 15% below entry (IDX ARB)`, used at `:838` (stop clamp) and
`:853` (sizing stop for plans without a stop); literal text at `:1108`, `:1112`, `:1131` ("locked at ARB, 15% below the entry", "up to 15%
per session while locked at ARB"). Persisted in `paper/ledger.jsonl` DECISION rows: 126 IDX decisions (122 explicit + 4 legacy without
`market`); 97 carry the 15% text in `plan.gap_risk`; 88 were decided on or after 2026-10-19. The policy is frozen and hashed (a change is a
new POLICY_ID), so this is a separate decision, not part of the market.py correction.

## 4. Persisted record families

### 4.1 They depend on the lock (a stored value came out of `lock_down`)

| family | IDX rows now | which rows | exposure to the correction (counted from the rows, no replay) |
|---|---|---|---|
| `paper/ledger.jsonl` OUTCOME | 93 of 276 | the 40 with `execution.paper_trade` | 35 exits dated >= 2026-10-19 (18 invalidation, 17 horizon); 5 earlier (cannot change) |
| `paper/speculations.jsonl` RESOLUTION window BASE5 | 2 of 23 IDX (130 total) | SPEC-SCAN-2026-10-29-F1_ARA-YPAS (candidate TRADED, net -20.62%), ...-ALKA (candidate NOT_FILLABLE, 5 twins traded) | 11 simulated exits, all 2026-11-06 |
| `paper/catalysts.jsonl` RESOLUTION (IDX_INDEX, window RUNUP) | 14 of 14 IDX (14 total are IDX) | all | 84 simulated exits, all 2026-10-30 |
| pending, will be computed by the live code | ledger 33 IDX decisions without OUTCOME (31 windows still open; ARII and BIKE are complete but unscored, see section 8); speculations 24 BASE5 pairs; catalysts 14 POST20 pairs | | all of their exit bars are >= 2026-10-30 |

### 4.2 Derived from those rows (depend transitively, through persisted RESOLUTION cone outcomes)

- `paper/learner_v2.jsonl` (238 forecasts, 26 IDX = SPEC_IDX). `learner2.py:144-146` reads both registers, `:326-342` `outcomes`, `:374-394`
  `live_rows`, `:571` `train`, `:609` `forward_pairs`. 202 forecasts (all made at or after 2026-10-30T11:02:59Z, every market) carry
  `IDX_INDEX:WITH_FLOW_RUNUP` (14 lock-dependent outcomes) in `training.live_rows`; WITH_FLOW_RUNUP is a RELATIVE statement outside
  `NOT_SHARED`, so it feeds the shared RELATIVE "RIGHT" slope block. 78 forecasts (at or after 2026-11-06T10:43:14Z) also carry SPEC_IDX
  statements (BEATS_TWINS_5, FADE10_5, GAIN0_5, DUMP10_5, PUMP_AND_DUMP_5 depend on the BASE5 net; RUN30_5, PUMP30_5 are path-only).
  The sealed rows themselves are facts and `learner2.verify` rebuilds them from the hashed register prefix, not from prices.
- Derived reports (not hash chains, regenerated by commands): `paper/SPECULATIONS.md` (IDX BASE5 row: 2 resolved, 1 traded, mean net -20.62%,
  twins -5.15%, FADE10_5 n=1, GAIN0_5 n=1, BEATS_TWINS_5 n=1; built by `speculation.statistics` / `plan_statistics` :925-1108),
  `paper/CATALYSTS.md` (IDX_INDEX RUNUP: 14 paired, mean signed diff +1.16%, 64% with the flow; `catalysts.statistics` :1497-1560),
  `paper/LEARNER_V2.md` (SPEC_IDX rows of the statement table).
- LLM_ARM_v1: `research/LLM_ARM_v1/calls.jsonl` (3 IDX calls, sets of 2026-11-02) and `calls_IDX_20261104.jsonl` (5 IDX calls) are scored on the
  register's BASE5 statements RUN30_5 / FADE10_5 / BEATS_TWINS_5 and the candidate `net_return` (`idxsig/llm_arm/workbench.py:219-278`,
  `audit.py:141-200`, `tools/watch_llm_arm.py:90-100`, a daily GitHub Action that keeps only a 90-day artifact). None of the 8 IDX sets has a
  BASE5 RESOLUTION yet, so nothing is scored; FADE10_5 and BEATS_TWINS_5 will be lock-dependent. 71 US calls: not affected.

### 4.3 They use limits()/REGIMES but not the lock

`data/manifests/panel-*.json` IDX (3) and `research/E5/**/stage1.json` (2): section 3.2 (B2, B3).

### 4.4 They do NOT depend on the lock

| family | rows | reason |
|---|---|---|
| ledger SCAN (IDX 23, plus the 23 `paper/scans/SCAN-2026-*` feature files) | 23 | detection reads `lock_up` only (`ara`); no exit |
| ledger DECISION (IDX 126) | 126 | entry-time: `lock_up`, and the hard-coded 15% policy constant (section 3.5), never `lock_down` |
| ledger OUTCOME without a trade (IDX) | 53 | the exit search is skipped (not fillable or outside the chase band); the verdict uses `lock_up` and path levels |
| speculations SPECULATION_SET (IDX 26), catalysts CATALYST_SET (14), BATCH (1), TAG (14) | 55 | sealed before the entry; features, plan text, twins from the scan; no exit |
| speculations RESOLUTION windows NEXT1 (IDX 21) and PATH20 (0 yet) | 21 | `kind: path`: `statement_outcome` uses reference-chain levels (`next_return`, `path_statement`) and never calls `simulate` |
| catalysts mechanism RESOLUTIONs | 0 IDX | graded from EDGAR or register batches (US families) |
| `paper/learner.jsonl` (v1) | 2 | SEC13D forecasts sealed with `resolutions_before: 0` |
| `paper/learner_v3.jsonl` | 60 (all US) | `learner3.live_rows` (`:458`) trains only on the sets it forecast (SPEC_US); US markets have all-False lock arrays; only the discarded `limits()` call inside `Market.build` remains |
| `paper/CALL_CERT.md`, `paper_book.jsonl` (50), `paper_account.jsonl` (106) | | built from learner_v3 forecasts and `exec_us` (US spikes); no IDX row, no `Market.lock_down` read |
| `premove_shadow.jsonl` (13), `crypto_account.jsonl` (13), `paper/microstructure/` | | crypto; `premove_core` accepts CRYPTO/US only; no import of market |
| `paper/sensors/`, `paper/catalysts_form4/`, `paper/timestamps/` | | text alerts, EDGAR indexes, RFC 3161 tokens |
| `results/RUNS.jsonl` (17) and `results/runs/*` | 17 | 5 IDX runs end 2025-02-21 / 2023-12-29 (rolled exits exist but all before 2026-10-19); 12 US/crypto runs have `price_limits: False`. `verify-runs` re-hashes run files and pins `code_commit`, not file content of market.py |
| `data/corporate_actions/ca_registry-*` (2 IDX builds) | 2 | `corporate_actions.build` reads ca_ratio, prev, close, listed_shares |
| `kod-machine/**` | | no import of idxsig market/execution; `forecasts.py` re-reads sealed learner_v3 and register rows and recomputes nothing (US sets); the 155 `.execute(` hits are SQLite; `research_evidence/execution.json` lists the field NAMES lock_up/lock_down for a crypto run |
| `tools/**`, `ops/**` | | zero keyword hits; they check hashes, chains and CI scope (`check_append_only.py`, `check_history_integrity.py`, `ci_scope.py`) and read no price or lock data |

## 5. Indirect consumers checked one by one

| consumer | verdict |
|---|---|
| learner v1 / v2 / v3 | v2 yes (4.2); v1 no (zero resolutions at sealing); v3 no (US sets only) |
| call_cert | no. Reads learner_v3 and the US register; imports `research/TA_HISTORY_v1/run.py`, which builds a US Market (limits() computed, lock arrays discarded) |
| paper_account, paper_book | no. US (`exec_us.execute`, `paper._market(df, "US")`) |
| premove_shadow, crypto_account | no. Crypto |
| speculation / catalyst reports | yes, derived (4.2) |
| dashboards / status builders | `tools/watch_llm_arm.py` (reads BASE5 resolutions, counts readiness; yes later for IDX calls), `kod-machine/.../forecasts.py` and `web.py:801` (read-only replay of US forecasts; no), `ops/kod-watch` (timing server receipts; no) |
| CI (`.github/workflows/checks.yml`) | runs the idx-signals and kod-machine unit tests, `kod verify`, `idxsig rules`, `idxsig verify-runs`, `check_append_only --all`, style and release checks. None recomputes an IDX outcome. No `-W error` or `PYTHONWARNINGS` anywhere in the repository |
| rule sandbox | `rules/audit.py:24` allows a rule to import `idxsig.market`; `user_rule.py` is an empty stub, so no rule calls `limits()` |

## 6. Frozen research (append-only directory `idx-signals/research/`; list only, never to be edited)

All IDX research reads a pinned panel manifest (last session 2026-10-06 or 2026-10-13), so none holds a bar dated >= 2026-10-19; the
recent-pull replays (FRESH_SHORT_v1, REPLAY_UNITS_v2, RECENT_REPLAY_v1) are US.

- Read the lock VALUE for IDX (through `idx_events.run_events`, `backtest.execute` or `spec.simulate`): PATH_HISTORY_v1 (`build.py:146-147`,
  `build2.py:149-150`, `simulate(..., market)` for IDX/US/crypto), MSCI_DELETION_v1, MSCI_DELETION_OOT_v1, MSCI_DELETION_OPT_v1 (`opt.py:177,411`
  `execute`), IDX_DILUTION_v1, IDX_INSIDER_NEWS, IDX_INSIDER_NEWS_OOT, MOVERS_NOW_v1, IDX_CAUSAL_CAPACITY_v1 (backtest), and the CLI runs
  E1, E3 and E5 on IDX.
- Import `idxsig.market` directly (all `Fees` only, which the correction does not change): `E2/repair/reproduce_source_findings_v2.py:22`,
  `IDX_DILUTION_v1/common.py:10`, `IDX_INSIDER_NEWS/run.py:20`, `run_v2.py:21`, `MSCI_DELETION_OPT_v1/opt.py:52`,
  `MSCI_DELETION_v1/msci_deletion.py:34`.
- Pin the sha256 of `idxsig/market.py`: MSCI_DELETION_v1 / _OPT_v1 / _OOT_v1 `protocol.json` pin `e9e9328a...` = `code_B`: all 11 idxsig pins
  match under B and exactly one (market.py) mismatches under C (`code_C` ab263fb7...). All three have a `run/` directory (the scripts refuse
  to run twice) and already fail their `idxsig_tree` pin at the base commit, so this is a record mismatch, not a new failure. Seven more
  directories pin the pre-tidy hash `b956576f...` and already mismatch under B (SLOW_10K, US_INSIDER_BUY, US_8K_ITEMS, E9,
  IDX_INSIDER_NEWS_OOT, CATALYST_REGISTER_v1/KILL_TEST_2020_2022 and 2020_2023); `SLOW_10K/run.py:101-104` refuses to run on such a mismatch.
  The golden fixture `tests/fixtures/market_limits_golden_20261109.json` records `captured_from` sha256 `e9e9328a...` (B).
- Names only (field lists in summaries): E3, E4 (crypto), E5 IDX `runs/IDX/*.json`.
- US or crypto Markets (limits() computed, lock arrays all False): E2, E9, EXEC_US_v2 and v2_1, EXIT_ATR_v1, FRESH_SHORT_v1, LEARNER_v2 warm starts,
  RECENT_REPLAY_v1, REPLAY_UNITS_v2, TA_HISTORY_v1, US_BREAKOUT_v1, US_PIPELINE_v1; CALL_CERT_v1, ATTENTION_HISTORY_v1 and TUNE_SWEEP_v1 only import learner3 (US).
- Not IDX consumers although the words match: CATALYST_REGISTER_v1/KILL_TEST_*/run*.py (`execute(prep, ev)` is local, US), E10 (`simulate` is an
  account simulation), VIX_BASIS_v1, HERMES_NOV3_REPRO_v1, IDX_INSIDER_NEWS/audit_score.py.
- `research/CATALYST_REGISTER_v1/protocol.json:33` states that the exit "rolls while not sellable, as speculation.simulate": the frozen
  protocol itself ties the catalyst register to the lock.

## 7. Hits that are not consumers (so the grep is accounted for)

386 in `idx-signals/tests` (reference only; tests that exercise the lock: `test_market*.py`, `test_execution*.py`, `test_speculation.py`,
`test_catalysts.py`, `test_plans.py`, `test_markets.py`, `test_e5.py`, `test_backtest_paired.py`); 199 in
`handoff/claude/idx_arb_oct2026_correction_20261109` (the correction's own harness and reports; not read, and not a production consumer;
`harness/impact_replay_a.py` and `_b.py` import market, paper and speculation); 178 in other `handoff/*` (agent outputs, patches, old
scripts; two `.js` workflow files; `run_t6.py` x2 define a local `simulate`); 157 in `kod-machine` non-test (155 SQLite `.execute(`, 2 field
names); 56 in kod-machine tests (SQLite, one `..._limits`); 122 in research (section 6); 118 in `idxsig` (sections 3.1-3.4 plus the local
functions `exec_us.execute`, `moonshot_e5.score`, `e8.score`, `call_cert.score`, `premove_shadow.score`); 30 in `results/runs/*/summary.json`
(field names); `tools/` and `ops/`: 0. Excluded as instructed: `.git`, `.claude`, `handoff/*/old_repair`.

## 8. Unclear, or needing a decision

1. **The legacy scorer does not roll.** `paper.py:1663-1677` looks only at sessions e+1..e+5; a locked horizon bar gives `None` for ever (no
   OUTCOME row), unlike `execute` and `simulate`, which roll. Under C more horizon bars on or after 2026-10-19 lock, so the 35 exposed OUTCOME
   rows can disappear from a corrected replay instead of changing. Precedents already in the ledger: ARII (decision 2026-10-08) has no OUTCOME
   because its 2026-10-16 close of 400 equals ARB (ref 470, 15% rule; I checked `limits()`: 400 under B and C, so independent of the
   correction); BIKE (2026-10-14) has none because the name has had zero volume since 2026-10-20 (suspension, not a lock). The stored
   plan text of 100 IDX decisions says "a sale rolls while locked at ARB" (`plan.exit`), which the legacy scorer does not implement.
2. **`simulate` returns None, and one None withholds a whole set.** All 11 BASE5 exits (the candidate and the twins of both sets) are on
   2026-11-06, the last bar of the only surviving pull. A newly locked bar among the 11 has no later sellable bar to roll to, so
   `resolve_set` returns None and that set's RESOLUTION would not exist yet. The 14 RUNUP resolutions exit on 2026-10-30 with later bars
   available, so there a lock would roll the exit instead (the row survives with another exit session and return).
3. **No persisted row names the rules that scored it.** OUTCOME rows carry `scorer: paper-score-v3`, `scoring_version`, `preprocessing`,
   `data.manifest`; RESOLUTION rows carry `resolver`, `register`, `protocol`, `data`. No market.py hash or regime marker, and the ids do not
   change with the correction. A corrected value can only be told apart by `revises` / `revision_reason`. `paper.latest_resolutions`
   (`paper.py:345-390`) raises unless a revision names the preceding effective record, and a non-RESOLVED revision clears an earlier graded
   outcome. Rows appended between now and the merge are indistinguishable by code version.
   **Only OUTCOME rows have a rescore command** (`paper-score --rescore ID --reason`, `cli.py:301,1194,1239-1248`). The registers have none:
   `speculation.due` (`:644`) and `catalysts.due` (`:1106`) skip every (set, window) that already has a RESOLUTION, and nothing in
   `speculation.py` or `catalysts.py` writes `revises`. A corrected RESOLUTION needs new code; the existing 2 + 14 rows would stay as written.
4. **Future rows.** After the correction ships, the 33 + 24 + 14 pending IDX items are computed with C. Dates after 2026-12-31 are not expected in
   any pending row (the longest window, POST20, ends about 2026-11-27 unless a lock or suspension rolls it further).
5. **The Rp11-14 nominal-Rp1 rule cannot matter for persisted trades:** the lowest IDX entry price among the 40 ledger trades is Rp74, among
   the BASE5 and RUNUP trades Rp230 and Rp77. BTEK and TAXI appear in the ledger only as NOT EXECUTABLE decisions and no-trade outcomes.
6. **Special-board names.** A one-price bar is also tested against the 10% special limit (`special_limits`, unchanged), and the regular-board
   7% is applied to every name (market.py docstring): names on 10% boards are over-locked by 7% falls. No row identifies board membership.
7. **Hard-coded 15% (3.5)** is a policy decision outside market.py: 97 IDX decisions carry the text, the stop clamp and sizing use 0.15.
8. **Warnings.** After 2026-12-31 every `Market.build` warns, for US and crypto too (`price_limits=False` still calls `limits()`);
   no repo configuration escalates warnings. Separately, `regime_index` raises ValueError for any date before 2019-07-29 in every market (unchanged).
9. **The replay inputs.** `code_B` and `code_C` carry only `paper/ledger.jsonl` and `paper/speculations.jsonl`; replaying the catalyst register
   also needs `paper/catalysts.jsonl` (read from the repository), and the RUNUP rows were resolved on 2026-10-30 from a pull that no longer
   exists; a replay on the 2026-11-06 pull is a final-bar replay and must say so.

## 9. Reproduction

Files in `sweep/`: `map.md` (this file), `counts.json`, `grid_compare.txt`, `raw_grep_all.txt`, `scripts/`.
`python3 -I scripts/counts_all.py` rewrites `counts.json` from the repository (read-only). `python3 -I scripts/limits_grid.py B|C
grid_B.npz|grid_C.npz` evaluates `limits()` of one code dir on the date x reference grid, and `python3 -I scripts/compare_grid.py <dir>`
writes `grid_compare.txt` (the two 31 MB npz files were deleted after the comparison; the scripts regenerate them).
`scripts/count_ledger.py` and `scripts/count_registers.py` are earlier, narrower versions of `counts_all.py`. The raw grep is
`grep -rEn -e 'lock_down|lock_up|limits\(|regime_index|regime_labels|REGIMES|sellable|next_sellable|rolled_sessions|Market\.build|Market\.from_panel|execute\(|simulate\(|resolve_set|score\(' .`
from the repository root with `.git`, `.claude`, `__pycache__`, `.ruff_cache`, `old_repair` excluded. Nothing under `code_B`, `code_C`,
the repository, or any directory I was told not to open was written or opened.
