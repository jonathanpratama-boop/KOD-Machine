# judge:2 (Judge; agent a6aac9899dd6449ad)

## scores
#### index
0
#### novelty
9
#### feasibility_now
3
#### falsifiability
8
#### data_readiness
2
#### directive_compliance
6
#### information_value
7
#### total
35
#### rationale
Only proposal with a genuinely new information source (EDGAR 8-K acceptance clock) and a clean prospective sidecar, but nothing is in hand: ~6,000 untested SEC pulls with a placeholder User-Agent, a causal-contract change to RULE_FIELDS/Market.FIELDS, 44h of build, and Track A is a re-read of G2_RET30 flags on a US 2023 that has already been replayed a dozen times.
#### fatal_flaw
Not fatal, but not executable now: self-declared 'available now: false'; the ticker->CIK join uses a 2026 company_tickers snapshot, so tickers reassigned 2020-2023 map to the wrong issuer and misattribute documents (a silent point-in-time defect the protocol must address before any number); Track A's I1 'executable candidate' is a frozen detector plus a filter validated on a spent year.
#### index
1
#### novelty
7
#### feasibility_now
6
#### falsifiability
7
#### data_readiness
8
#### directive_compliance
8
#### information_value
8
#### total
44
#### rationale
New long family (multi-session creep, re-base, contraction) never measured on any panel, reference member frozen 2026-10-08 before any moonshot outcome, no frozen detector touched, all panels on disk, holdout sealed by Study and explicit ends; weakness is a 72-run grid at p<0.05 (floor 0.005) across 3 markets, with B/C members likely under 200 flags and repeat-flag inflation of n.
#### fatal_flaw
None. Multiplicity is the main risk: a single-market admissible pair at p~0.03 out of 72 runs is expected by chance; treat any pass as provisional and prospective-only, as the protocol already says.
#### index
2
#### novelty
4
#### feasibility_now
8
#### falsifiability
7
#### data_readiness
9
#### directive_compliance
5
#### information_value
6
#### total
39
#### rationale
Cheapest and most executable (14h, one small harness change, everything on disk) and the t+1..t+31 path map is genuinely unmeasured, but it is a third execution-plan search on the same frozen flag whose discovery and 2023 lag-1 outcomes are known in both markets (US 2023 'spent'), 14 highly correlated selectable cells, and a strong negative prior.
#### fatal_flaw
Borderline on the no-retune rule: a plan search on G2_RET30 validated on a year whose outcomes for the same flags were seen; and 'scoring the validated plan prospectively from decisions the ledger already records' would be retrospective scoring of pre-freeze decisions whose lag-k/h outcomes have partly elapsed by the freeze date unless restricted to post-freeze decisions only.
#### index
3
#### novelty
7
#### feasibility_now
3
#### falsifiability
5
#### data_readiness
6
#### directive_compliance
9
#### information_value
6
#### total
36
#### rationale
Cleanest on the standing rules (prospective only, frozen KOD-DET-v0 sha-bound, no holdout, no manufactured numbers, kod.db state verified as 0 scans/0 receipts) and the only path to AUTHORITATIVE records, but it cannot run from this session: routine-host wiring outside the repo, TSA/GitHub/SEC dependencies, 3-4 MB/day of committed registry+db growth, 48h build, and a scientific readout no earlier than Dec 2026/Jan 2027 with marginal power to exclude lift 2.
#### fatal_flaw
Not fatal for compliance; practically the T-24H staleness blinds one-session-lead events (E2 median lead 1 session on US), so a FALSIFIED readout partly tests the design rather than the detector; and its scientific claim (VOLUME_CREEP_PRICE_QUIET) is answered faster and with matched controls by #1's A1 row.
#### index
4
#### novelty
8
#### feasibility_now
7
#### falsifiability
8
#### data_readiness
7
#### directive_compliance
8
#### information_value
9
#### total
47
#### rationale
First combined-feature, cross-sectional ranker with a pre-registered down-event label and a closed-form break-even precision bound; no frozen detector touched, no model/threshold search, coefficients frozen as rule literals, in-sample fail kills without a validation run, sensitivity fill model required, no change to backtest/execution/controls; gross-vs-net motivation verified from recorded trades.
#### fatal_flaw
None. Two cautions: the in-sample discovery metrics of a fitted model will look impressive and must never be reported as performance; the ORACLE_E30 bound must stay labelled a bound (it is the single most quotable-out-of-context number in the proposal). A null is 'no edge findable by this learner', not a proof.
#### index
5
#### novelty
5
#### feasibility_now
7
#### falsifiability
7
#### data_readiness
8
#### directive_compliance
4
#### information_value
6
#### total
37
#### rationale
Well-disciplined design (Bonferroni, within-year gate, calendar committed before discovery, claim levels, regime-variable budget, feasibility script verified outcome-free) and E3/REPORT.md itself names the idea, but it is a conditional re-analysis of the frozen detectors' already-recorded trades: the hypothesis came from seen per-year discovery outcomes, the gate runs on those same seen outcomes, and validation re-reads 2023 trades whose pooled result is recorded (crypto explicitly a second regime look).
#### fatal_flaw
Closest of the six to 're-tuning a frozen detector on data its outcomes were seen on': HOT/COLD is a filter on F1_ARA/G2_RET30 tested on consumed windows; 20/120 and the strict median are choices (250 was considered), and the T2 HOT-cell trading claim is a second look at the same 2023 trades. Not scored 0 because the detector code and threshold are untouched and no parameter is fitted to outcomes, but a pass can only be hypothesis-generating.
## ranking
- 4
- 1
- 2
- 5
- 3
- 0
## notes
Judge 2 (risk/compliance). Ranking follows totals: #4 (47) > #1 (44) > #2 (39) > #5 (37) > #3 (36) > #0 (35). Recommended next move from this seat: run #4 first (cheapest decisive kill, no harness contract change, nothing frozen touched, holdout untouched), #1 second (new family, all data on disk; its A1 row answers #3's scientific question with matched controls). #2 and #5 should run only if the owner explicitly accepts one more look at 2023 for the frozen long detectors; both are compliant in letter (detector code verbatim, explicit --end) but weak in evidential weight by construction. #3 is the only fully prospective design and should proceed as an infrastructure track in parallel, not as the science bet. #0 needs a reachability/User-Agent test and a point-in-time ticker->CIK fix before it is a plan. Cross-cutting: four proposals (#1, #2, #4, #5) all claim idxsig/rules/moonshot_e5.py and research/E5 (collision; assign distinct ids if more than one runs); three need the IDX panel-20261013T194245Z csv rebuilt (absent on disk; fallback panel-20261007T225823Z present); every US/crypto run relies on explicit --end because HEAD has no GLOBAL_HOLDOUT guard (only origin/claude/e4-fade-short-side L85/L296) so merging PR #7 first is a shared risk reducer. Verified read-only: all cited code lines; #4's gross/net figures (crypto reads -1.36/-1.75 on 263 EXITED vs the claimed -1.51/-1.90, immaterial); #5's E3 by-year numbers; #5's scratchpad script is discovery-only and outcome-free; E3/REPORT.md lines 63-67 propose the ARA-count regime; kod.db counts; paper scans carry features.csv.gz; 87 DECISION records in paper/ledger.jsonl. No file in /home/user/KOD-Machine was modified; no harness run, git state change or network pull was made.
