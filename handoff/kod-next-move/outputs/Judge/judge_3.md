# judge:3 (Judge; agent a0a6b52cd09bf35ff)

## scores
#### index
0
#### novelty
9
#### feasibility_now
3
#### falsifiability
7
#### data_readiness
2
#### directive_compliance
7
#### information_value
8
#### total
36
#### rationale
Only proposal with a genuinely new information source, but nothing is on disk (data/raw/sec holds only the CIK map and share-count/split evidence, no submissions JSON), reachability of data.sec.gov is untested and pulls need owner authorisation, and the build extends the causal contract itself (RULE_FIELDS, RuleView __slots__, CausalSource.fields, Market.FIELDS/build/from_panel, new panel format, e1.Study keys) plus a sidecar: 44h is optimistic, 60-80h is realistic, so it cannot ship this week.
#### fatal_flaw
Not shippable this week: input data does not exist in the repo and cannot be fetched under the standing rules without an explicit go; Track A's validation is a stratified re-read of consumed 2023 G2_RET30 outcomes with its decisive evidence months away in the prospective sidecar.
#### index
1
#### novelty
8
#### feasibility_now
6
#### falsifiability
8
#### data_readiness
8
#### directive_compliance
9
#### information_value
8
#### total
47
#### rationale
First pre-move tape family (creep/quiet, re-base, contraction) with thresholds frozen for another purpose; clean e3/e4 clone pattern and all panels on disk (IDX rebuild possible: 976/976 mirror files present), but it is the heaviest harness build of the five: a vectorised 35-lag rebase member, cross-sectional percentiles, three e1.Study generalisations (format check at e1.py:100, the IGNITION next() at line 190, HORIZON), 72 runs plus 24 evaluate loops, and a stop_ref choice that depends on merging PR #7 for open-entry markets; 30h is low, 40-50h is realistic.
#### fatal_flaw
none fatal; risk that B/C members never reach 200 flags or 200 scored, and the 2023 reuse is declared rather than clean
#### index
2
#### novelty
4
#### feasibility_now
9
#### falsifiability
9
#### data_readiness
10
#### directive_compliance
9
#### information_value
7
#### total
48
#### rationale
Cheapest decisive experiment against the existing harness: RunConfig.entry_lag already exists (e3.harness_config just hard-codes 1), ExecConfig.plan already reports the lag as entry_window so plan ids need no change, the only harness edit is ~3 lines in resolve_plan so the frozen Rule.plan carries the lag at validation; e4.py's market loop is on PR #7 but trivially portable (drop side/liquidation/jump_ratio); both panels and both precondition runs (crypto 005732Z, US R1c 100745Z on repair panel 8d3b7ce4) are on disk; 32 runs; G2_RET30 untouched, reference cell barred, holdout never sliced.
#### fatal_flaw
none; minor: the descriptive equal-notional ledger needs per-draw trade frames that backtest.run does not return (it returns only per-draw aggregates in 'draws'), so either a small additive return value or drop that non-decision output; novelty is low (same detector, same tape, one axis beyond E3/E4)
#### index
3
#### novelty
6
#### feasibility_now
4
#### falsifiability
6
#### data_readiness
7
#### directive_compliance
9
#### information_value
5
#### total
37
#### rationale
Cleanest on the holdout/no-retune rules and the inputs (paper features.csv per scan, recent pulls) exist, but it reuses none of e3/e4, lives in kod-machine (5 new modules, 48h), depends on a scheduler, TSA and a GitHub token outside the repo, the STRICT chain has never run live (kod.db: 4 cases, 0 scan_runs, 0 receipts), commits a database growing ~3-4 MB/day, and yields no scientific readout before late December at the earliest; the same tape hypothesis (A1_CREEP_QUIET) is tested with far more power by proposal #1 in a week.
#### fatal_flaw
No result this week or this quarter: the first pre-registered readout is 60 sessions after a launch that is itself ~2 weeks of build; the committed var/kod.db growth (~200 MB over the pilot) is an unresolved operational hazard
#### index
4
#### novelty
7
#### feasibility_now
6
#### falsifiability
9
#### data_readiness
8
#### directive_compliance
8
#### information_value
8
#### total
46
#### rationale
The sharpest kill test in the set (in-sample Arm B failure closes the daily-bar family cheaply, directional vs variance detection is nailed either way, the oracle break-even bound is new) with no change to backtest/execution/controls, literal coefficient tuples pass audit.py, and all panels on disk; but it is more new code than it admits: dataset build on 2.7M rows, IRLS, D-label and oracle blocks, the unlisted e1.Study IGNITION guard (Study(family_module=moonshot_e5) hits next() at e1.py:190), and the top-0.5% threshold means ~13k US flags x 200 draws per run, the heaviest run the harness has ever executed.
#### fatal_flaw
none fatal; engineering concern: the primary US fit/validation panel is the unrepaired panel_us-20261008T004105Z whose split rescaling the E2 ERRATA documents (chosen because e1.Study demands 'panel-global-v1'), mitigated only by the fill-B repair-panel sensitivity
#### index
5
#### novelty
5
#### feasibility_now
8
#### falsifiability
8
#### data_readiness
8
#### directive_compliance
7
#### information_value
6
#### total
42
#### rationale
Very buildable: verbatim detector copies, one session-level breadth function (cross-sectional, trailing, prefix-safe like moonshot_e1's median), two additive trades.csv columns in backtest.run, 21 runs, panels on disk (IDX rebuild feasible), and the scratchpad feasibility script verified to compute flag counts only; but it is the proposal closest to re-reading frozen detectors on consumed 2023 (hypothesis motivated by seen per-year splits, mitigated by the within-year gate and Bonferroni) and E3's report already named the idea, so novelty is modest and a pass can still be 'informative but not tradeable'.
#### fatal_flaw
none fatal; the harness change must be committed before any run (write_run refuses a dirty tree) and sector frenzies are an admitted unmatched confound for HOT
## ranking
- 2
- 1
- 4
- 5
- 3
- 0
## notes
Judge 3 (ship-this-week engineer). Read-only: nothing in /home/user/KOD-Machine was modified, no harness run, no network pull, no panel row computed; holdout untouched (only manifests, run summary.json configs, trades.csv column names and the scratchpad script were read). Verified harness facts the scores rest on: HEAD has e3.py (IDX-only, entry_lag hard-coded 1) and no e4.py; e4.py, RunConfig.side/liquidation/jump_ratio and the US/crypto GLOBAL_HOLDOUT guard exist only on origin/claude/e4-fade-short-side (PR #7), so every e5.py 'cloned from e4' must port or merge first; HEAD backtest.run guards only the IDX holdout (lines 253-256), so explicit --end is mandatory for US/crypto in every proposal. RunConfig already carries entry_lag/entry_rule/entry_window/exit_rule/units/fill_model/quarantine; ExecConfig.plan reports entry_window=entry_lag for fixed entries, so delayed fixed entries (#2) need almost no harness code. execute() refuses conditional entries/exits unless entry_price=='close' on HEAD (execution.py:364-366), so stop_ref/first_down for US/crypto (#1) need PR #7. e1.Study hard-codes 'panel-global-v1' for non-IDX (e1.py:100) and sig['ign']=next(IGNITION member) (line 190) raises StopIteration for any family without one: #1 lists both fixes, #4 lists neither but needs the second. backtest.run returns {summary, trades, draws} where draws is per-draw aggregates only, so per-trade matched means (#5) and per-draw ledgers (#2) need an additive change. rules/audit.py allows only literal module-level values and numpy/pandas imports: literal coefficient tuples (#4), SMOOTH/TRAIL constants (#5) and round thresholds (#1) pass. Data on disk: panel_crypto-20261008T003354Z (panel-global-v1, 3dc12749), panel_us-20261008T004105Z (panel-global-v1), panel_us_repair-20261008T114805Z (panel-global-v2-units, 8d3b7ce4, read_through 2023-12-29, 669 quarantined), IDX panel-20261007T225823Z csv; the pinned IDX panel-20261013T194245Z csv is absent but all 976 mirror files of its manifest are present so a rebuild is feasible (E3 did it on this branch). Precondition run for #2's US leg (20261008T100745Z) is confirmed on repair panel sha 8d3b7ce4 with units=panel, quarantine=none, fill A. SEC cache holds only company_tickers and share-count/split evidence, no submissions JSON (#0 data absent). kod-machine var/kod.db: 4 cases, 0 scan_runs, 0 receipts (#3 chain never run live). Directive compliance: no proposal re-tunes a frozen detector or reads the holdout; #0 Track A, #2 and #5 all test on 2023 where the frozen detectors' pooled outcomes were seen (#2 follows the accepted E3/E4 select-on-discovery pattern with the known cell barred; #5 is a parameter-free partition but its hypothesis came from seen per-year splits; #0 Track A is an exogenous binary with its decisive test prospective), hence 9/7/7 rather than 0. Ranking for a one-week ship: #2 first (two days of work, all inputs present, decisive either way), #1 second (highest-value new family but 40-50h and the largest rule-module build), #4 third (sharpest kill test, heavy runs and an unrepaired primary US panel), #5 fourth (easy build, lowest novelty and nearest the consumed-data line), #3 and #0 last because neither produces a result this week: #3 needs weeks of live operation and #0's data is not in the repo.
