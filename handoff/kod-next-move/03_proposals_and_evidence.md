# Proposals, judge scores, refutations (Phase 1 state at checkpoint)

Full agent outputs are in `outputs/`. This file is the digest; where it disagrees with an output
file, the output file wins. Proposal indices are the workflow's (launch order).

## Judge aggregate (`outputs/ranking.json`; three judges, totals out of 60)

| Rank | # | Angle | Title (short) | Judge totals | Mean | Effort | Data now |
|---|---|---|---|---|---|---|---|
| 1 | 4 | skeptic | **E5-CEILING**: pre-registered T-0 predictability ceiling for the +30%/5-session event from daily bars; directional (up-minus-down) ranker as the kill test | 48, 47, 46 | 47.0 | 30 h | yes |
| 2 | 1 | new-family | **E5 PRE-SPIKE TAPE**: accumulation / re-base / contraction detectors that fire without a big up day (KOD VOLUME_CREEP_PRICE_QUIET as frozen reference member), IDX/US/crypto | 46, 44, 47 | 45.7 | 30 h | yes |
| 3 | 2 | structure | **E5-PATH**: delayed-entry long after the fade; entry-lag {1,2,3,6,11} × hold {5,10,20} grid on frozen G2_RET30, crypto primary, US secondary | 43, 39, 48 | 43.3 | 14 h | yes |
| 4 | 5 | regime | **E5 regime partition**: own-event spike-breadth HOT/COLD partition of F1_ARA / G2_RET30 under their recorded plans | 40, 37, 42 | 39.7 | 24 h | yes |
| 5 | 0 | information | **E5_US_INFO_v1**: 8-K acceptance-time join; documented vs undocumented +30% days; filing-type detectors I1..I8 | 37, 35, 36 | 36.0 | 44 h | **no** (needs ~6,000 EDGAR submissions JSONs) |
| 6 | 3 | kod-feed | **KPF-v1**: daily tape-fed prospective KOD pipeline (VOLUME_CREEP_PRICE_QUIET at T-24H, STRICT cases, 60-session pilot) | 34, 36, 37 | 35.7 | 48 h | yes (paper-scan features.csv) |

Judges' consensus notes (verbatim gist, `outputs/Judge/*.md`):
- Judge 1 (quant): #4 is "the one proposal that changes the information set rather than the plan"; #1 "first family that fires without a same-day move"; #5 "closest to re-tuning a frozen detector on seen data"; #0's Track A tests "early-filed vs not-yet-filed", not documented vs undocumented.
- Judge 2 (Ace/compliance): run #4 first (cheapest decisive kill, nothing frozen touched), #1 second; #2/#5 only if the owner accepts one more look at 2023 for the frozen long detectors; #3 should proceed as a parallel infrastructure track, not as the experiment. No proposal touches the holdout; none scores 0 on compliance.
- Judge 3 (engineer): #2 is cheapest (RunConfig.entry_lag already exists); every "e5.py cloned from e4.py" needs PR #7 merged or ported first (e4.py, `RunConfig.side`, the US/crypto `GLOBAL_HOLDOUT` guard exist only on PR #7); HEAD guards only the IDX holdout, so explicit `--end` is mandatory for US/crypto in every proposal; #3 cannot produce a result this quarter and the committed `var/kod.db` cannot absorb ~2,400 entries/day.

## Refutations so far (`outputs/Refute/`)

### #4 skeptic (E5-CEILING) — 3 of 3 refuters done: 2 refuted (serious), 1 not refuted (serious caveats)
Objections that must be fixed before any freeze (all three refuters converge):
1. **Verdict conflates information with executability.** The thesis verdict ("no T-0 information iff 0/3 Arm B pass") rests on the trading pass; on IDX the fixed next-close plan refuses every ARA-locked flag. Fix: split into an information verdict (detection block over the full flag set: AUC_U, AUC_D, directional ratio, fill-independent endpoint return vs matched on the reference chain) and a separate executability verdict.
2. **Primary pass test is anti-conservative for a variance-selecting ranker** (rule mean placed in the distribution of matched-portfolio means). Fix: per-signal paired difference (rule net − mean net of its 200 matched controls) with a cluster bootstrap over signal sessions.
3. **Arm B's down label (−23% in 5 sessions) is regime-mismatched on IDX**: ARB was 7% flat for the whole IDX discovery window (market.REGIMES), so D needs 3–4 consecutive limit-downs; Arm B uninterpretable on IDX as written.
4. **Serial dependence of rank-based flags** (top-0.5% vol20 flag repeats the prior session's name 81.5% of the time on IDX discovery; 172 distinct names) breaks the independence assumed by admissibility and the 1000-resample bootstrap. Fix: cluster by name/session; report distinct names.
5. **Crypto "next open" = signal close** (open(t+1) within 1 bp of close(t) in 33% of rows, within 10 bp in 70%); the crypto fill-B sensitivity cannot run (panel has no `unit_factor`; `execution.execute` requires `units='as_traded'` for fill B).
6. **Primary US fit panel is the unrepaired `panel_us-20261008T004105Z`** (format panel-global-v1, 2026-10 price units, 177 spike rows dropped by a look-ahead `_finish`). Fix: fit/threshold/validate on `panel_us_repair-20261008T114805Z` with `units=as_traded`; declare quarantine mode.
7. **2023 is already consumed by siblings using E5's own inputs** (ara on IDX, ret1/brk60 on US, ret1 on crypto); any pass is provisional and must be confirmed prospectively.
8. Minor: `Study._signals` `age`/`zero20` are not NaN before listing (prefix-safety detail); pinned IDX panel `panel-20261013T194245Z` is not on disk (needs `idxsig build-panel` from the mirror manifest; fallback `panel-20261007T225823Z`).
Verified claims (not refuted): gross-vs-net decomposition (IDX −3.67%/−4.06%, crypto −1.51%/−1.90%, US −3.19%/−3.65%, US fill-B −0.10%/−0.97%); vol20 matched-set AUCs 0.679/0.780/0.556 are in the recorded `signal_stats.csv`.

### #1 new-family (E5 PRE-SPIKE TAPE) — 3 of 3 done: look-ahead NOT refuted (serious), statistical REFUTED (serious), execution NOT refuted (serious)
Fixes demanded before any freeze:
1. **"2023 is out-of-sample for this family" is overstated.** `research/E1/validation/episodes_E30.csv` (569 rows), `E2/US/validation/episodes_E30.csv` (4,100) and `E2/CRYPTO/validation/episodes_E30.csv` (730) already list every 2023 +30% episode with ret5, ret20, volr, rngr, vol20, dd60, zero20, up5 at the decision close — i.e. the complete 2023 positive class with E5's own inputs. Re-label 2023 a consumed period ("post-discovery check") and declare those files in the leakage statement.
2. **A1 is a conjunction of negatively associated conditions.** Spearman(volr, rngr) = 0.57 / 0.50 / 0.74 (IDX/US/crypto) in the recorded control sets, so P(rngr ≤ 1 | volr ≥ 1.5) is only 22% / 17–22% / 8%: the creep-and-quiet flag will be rare; pre-screen with a one-pass weak-signal Study on discovery before any harness run.
3. **Detection-gate inference is anti-conservative for state detectors** (`e1.Study.detector_table` treats every flagged ticker-day as independent; creep/contraction flags persist for many sessions). Cluster by name/episode.
4. **Detection-stage matched pool matches price band / liquidity / market cap only** (`e1.py:215-227`), not volatility — A3/C1 (hivol) pass detection on vol20 alone (AUC 0.68/0.78). On US the band is the provider-adjusted band (no `unit_factor` at detection stage): attach as-traded units in `e1.Study` when the panel carries them.
5. **Multiplicity without correction**: 8 detectors × 3 holds × 3 markets = 72 pairs selected by max average net, then p < 0.05 once per market.
6. **IDX execution realism**: no closing-auction spread/impact term in the IDX cost model (first-order for a quiet-tape family); B1/B2 re-base members are structurally confined to the ≤Rp200 band under the ARA bands; the capacity gate removes the population the thesis is about, so a negative IDX result would be ambiguous. Minor: IDX reference resets (123 in TIER_1, 41 with ratio ≥ 2) produce spurious creep flags for up to 25 sessions; the crypto panel is legacy v1 with a future-informed spike deletion (LUNA 2022-05-13); A1's `not_repriced` makes it a stricter subset of the KOD detector, not the detector itself.

### #2 structure (E5-PATH) — 3 of 3 done: look-ahead NOT refuted (serious), statistical REFUTED (serious), execution REFUTED (serious)
1. **Redenomination artefacts decide the crypto grid as written.** The proposal declined a jump exclusion; the panel carries same-ticker unit changes (COCOS 2021-01-23 +129,440%, DREP 2021-04-02 +10,558%, LUNA …). Calendar enumeration shows 13 of 15 crypto cells hold at least one G2_RET30 trade across an upward swap; E4's report already hit exactly this (`research/E4/REPORT.md` L35-36). Fix: `jump_ratio = 10` on every cell incl. the reference row (requires PR #7's `EXCLUDED_DATA_JUMP` code), plus a tail-robustness condition (admissible with its largest trade removed; report medians).
2. **"Highest mean" selection across holds to 20 sessions in crypto 2021 is winner's-curse-prone**; the falsifier's inference is invalid (relative hypothesis, absolute per-year positivity rule).
3. **Matched controls are matched at the signal session**, not at the delayed entry; momentum tercile is broad.
4. **US arm (`units='panel'`) re-introduces the outcome-correlated SKIP_LOT asymmetry ERRATA documents** (rule 10.4% vs controls 4.1% in the reproduce target `20261008T100745Z`), and 52.8% of scored trades sit in a different adjusted-vs-as-traded price band (first matching priority). US universe is the 2026 survivor snapshot. The +1.5%/side stress addresses only the cost tier.
5. Minor: crypto cost text (0.3%/side) does not match the recorded E2 config (0.2%/side); the crypto panel is legacy v1. Crypto "open" = prior close holds in practice (median |open/prev−1| = 0.041%).

Net reading of the Refute phase: none of the top three is dead, none can be frozen as written. Common demands: use the repaired/as-traded US panel; exclude data jumps; cluster the statistics by name/session; declare 2023 consumed; separate the information verdict from the executability verdict; land PR #7 (or port its `jump_ratio`/`NEVER_ENTERED`/holdout-guard code) first.

## Evidence the readers established (`outputs/Understand/`)

- `read_experiments`: numeric record of every experiment and which validation year each family consumed.
- `read_harness`: what the harness expresses today vs only on PR #7; `RULE_FIELDS` is the 12-field interface a rule may see; no external-data inputs exist.
- `read_data`: panels on disk and their formats/units; FMP MCP probes (see file for exact capabilities/limits found); EDGAR is free but nothing is downloaded.
- `read_kod`: KOD case mechanics; what opening a prospective case requires; why the paper-scan names are not themselves pre-repricing cases.
- `read_prs`: conflict map between PR #3, PR #7 and base; recommended landing order.
- `read_paper`: ledger counts, why every candidate PASSes (APPROVAL-v2 pins), first outcome dates, what a new detector family must change in `paper.py` (`_detector()`, `validation_evidence`, `APPROVAL_PINS`).
