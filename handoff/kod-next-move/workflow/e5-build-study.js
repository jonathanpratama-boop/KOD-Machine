export const meta = {
  name: 'e5-build-study',
  description: 'Phase 2b of E5-CEILING: build idxsig/e5.py (stages 0-4), the e5-* CLI, synthetic tests and the DRAFT research/E5 protocol; three-lens adversarial review and fix rounds',
  phases: [
    { title: 'Build', detail: 'one builder in the e5-s-study worktree' },
    { title: 'Review', detail: 'three read-only reviewers: leakage, protocol fidelity, statistics/tests' },
    { title: 'Fix', detail: 'fixer per round, then re-review' },
  ],
}

const SCRATCH = '/tmp/claude-0/-home-user-KOD-Machine/74d3ac27-b8ad-5917-a6c3-ea51c410b250/scratchpad'
const MAIN = '/home/user/KOD-Machine'
const WT = `${SCRATCH}/e5-s-study`
const BRANCH = 'e5/s-study'
const RULES = `
STANDING RULES (non-negotiable):
- Work ONLY in the worktree ${WT} on branch ${BRANCH} (already checked out). Never touch ${MAIN} or any other worktree. No git checkout/switch/reset/rebase/stash/push. Commit with "git -c user.name=Claude -c user.email=noreply@anthropic.com commit" and end every commit message with exactly these two trailer lines:
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SrR7rsdNDD1Fqye2K6MDSw
- NEVER "git add" anything under idx-signals/research/, idx-signals/results/, idx-signals/paper/, kod-machine/. The draft protocol files you write under idx-signals/research/E5/ stay UNTRACKED (the freeze is a separate commit by the orchestrator after review). tools/check_append_only.py --all must stay OK.
- Defaults of existing code must reproduce every recorded run unchanged; every change to an existing module is opt-in and additive.
- Tests are synthetic only: no real panel loaded, no network, no harness run on real data, nothing that reads the holdout (IDX 2024-01-02..2025-02-21; US/crypto 2024 onward). data/panel and data/raw in the worktree are symlinks to real data: do not read them in tests or in anything you run; they exist so the orchestrator can run the stages later.
- Never present a number as performance; never fabricate test output: run the commands and paste the real tails.
- Reference material (read-only): ${MAIN}/handoff/kod-next-move/synthesis/E5_CEILING_protocol_draft.json (the protocol draft), ${MAIN}/handoff/kod-next-move/synthesis/RECOMMENDATION.md (rationale), ${MAIN}/handoff/kod-next-move/06_phase2_integration_todo.md (every builder's API notes, the review verdicts, the freeze decisions and the PANEL DECISION), ${MAIN}/handoff/kod-next-move/03_proposals_and_evidence.md (the refuters' demands, §Refutations). Patterns to imitate in your worktree: idxsig/e3.py, idxsig/e4.py, research/E4/protocol.json, tests/test_e3.py, tests/test_e4.py; the Phase-2a modules you build on: idxsig/controls.py (VERSIONS['v3']), idxsig/backtest.py (matched_mean_net_return / same_session_mean_net_return columns, per_signal_excess, paired_excess), idxsig/e1.py (Study(..., pool_units, pool_version), PANEL_FORMATS), idxsig/profiles.py (CRYPTO_CLOSE), idxsig/rules/moonshot_e5.py (features, rank_features, score, debounce, flags, detector_states, FEATURE_ORDER, literals placeholders, CANDIDATES).
- Final checks from ${WT}/idx-signals before each commit: "python3 -m unittest" (expect 311 + your tests, 0 failures), "python3 -m idxsig rules" (audit passes), "python3 -m idxsig verify-runs" (OK), and from ${WT}: "python3 tools/check_append_only.py --all" (OK). Paste the tails.
Your final text is data for an orchestrator, not a message to a person.`

const BUILD_SCHEMA = {
  type: 'object',
  properties: {
    branch: { type: 'string' }, commit: { type: 'string' },
    files_changed: { type: 'array', items: { type: 'string' } },
    untracked_drafts: { type: 'array', items: { type: 'string' }, description: 'the draft protocol files left untracked' },
    api_added: { type: 'array', items: { type: 'string' } },
    protocol_keys_read: { type: 'array', items: { type: 'string' }, description: 'every protocol.json key e5.py reads, with the stage that reads it' },
    behaviour_summary: { type: 'string' },
    tests_added: { type: 'array', items: { type: 'string' } },
    test_output_tail: { type: 'string' },
    runtime_estimate: { type: 'string', description: 'your estimate of Stage 0/1/2 runtime per market on the real panels and why' },
    decisions_made: { type: 'array', items: { type: 'string' }, description: 'every concrete choice the draft protocol fixes that the synthesis draft left open' },
    needs_other_file: { type: 'array', items: { type: 'string' } },
    open_concerns: { type: 'array', items: { type: 'string' } },
  },
  required: ['branch', 'commit', 'files_changed', 'untracked_drafts', 'api_added', 'protocol_keys_read', 'behaviour_summary', 'tests_added', 'test_output_tail', 'runtime_estimate', 'decisions_made', 'needs_other_file', 'open_concerns'],
}
const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['accept', 'fix_required', 'reject'] },
    findings: { type: 'array', items: { type: 'object', properties: {
      severity: { type: 'string', enum: ['blocking', 'serious', 'minor'] }, file: { type: 'string' }, line: { type: 'integer' },
      claim: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } },
      required: ['severity', 'file', 'claim', 'evidence', 'fix'] } },
    test_rerun_tail: { type: 'string' },
  }, required: ['verdict', 'findings', 'test_rerun_tail'],
}

const SPEC = `
BUILD idxsig/e5.py (new), the e5-* subcommands in idxsig/cli.py (additive), tests/test_e5.py (new), and the DRAFT research/E5/protocol.json + research/E5/PROTOCOL.md (untracked). You may make small additive changes to idxsig/rules/moonshot_e5.py only if the study cannot be written without them; list each in files_changed and keep its tests green.

PROTOCOL (KOD-GLOBAL-E5-v1, experiment E5-CEILING). Write protocol.json so that e5.py reads EVERY parameter from it (no numbers hard-coded in e5.py except pure code paths), mirroring research/E4/protocol.json's shape: protocol_id, frozen_before_analysis (false in the draft; the orchestrator sets the freeze commit), question, null_hypothesis, builds_on, family, learner, features, labels, markets, plans, harness, periods, matched_controls, stages, admissibility, validation, consequences, declared_leaks, not_fixed_and_why, search_size, claims. Fix these concrete values (from the handoff decisions):
- markets: each market entry carries its own "panel_format" (IDX "panel-v2", US "panel-global-v2-units", CRYPTO "panel-global-v1"); e1.Study resolves, in order, its panel_format= keyword, then protocol["markets"][<market>]["panel_format"], then the global protocol["data"]["panel_format"] (h3-e1 fix commit 45d9836), so do NOT use a single global data.panel_format; e5.py passes the market's declared format explicitly as the keyword too. IDX panel_manifest "panel-20261007T225823Z.json" (sha 9d3a0718…), registry "ca_registry-20261007T230210Z", tier TIER_1, precondition_runs ["results/runs/20261009T050040Z_MOONSHOT_E1_D1_v1.1"]; US panel_manifest "panel_us_repair-20261008T114805Z.json" (sha 8d3b7ce4…, format panel-global-v2-units), units as_traded, quarantine none (unit_schedule = sensitivity), precondition_runs ["results/runs/20261008T115656Z_MOONSHOT_E2_US_D1_v1"], status DIAGNOSTIC (survivor-only); CRYPTO panel_manifest "panel_crypto-20261008T003354Z.json" (sha 3dc12749…, format panel-global-v1), precondition_runs ["results/runs/20261008T005732Z_MOONSHOT_E2_CRYPTO_D1_v1"], jump_ratio 10; CRYPTO_CLOSE = sensitivity profile sharing CRYPTO's panel (output dir keyed CRYPTO_CLOSE, panel via PROFILES[market].market), fill A only. Declare that E3's newer IDX panel-20261013T194245Z could not be rebuilt on this machine (Yahoo raw files absent) and that the pinned run's own panel is primary, so Stage 0 is a true reproduction.
- periods: discovery IDX 2021-01-22..2022-12-30, US/CRYPTO 2020-07-01..2022-12-31; validation IDX 2023-01-02..2023-12-29, US/CRYPTO 2023-01-01..2023-12-31; holdout sealed (backtest.HOLDOUT for IDX, backtest.GLOBAL_HOLDOUT for US/CRYPTO, plus e5.py asserts end <= validation end before building any RunConfig or Study); WARMUP 65 (moonshot_e5.WARMUP; see conventions below): every Study/harness window starts 65 sessions before the period (IDX warm-up in TIER_2 for features only; declared); discovery years for per-year gates IDX 2021, 2022; US/CRYPTO 2020 (from July), 2021, 2022.
- features/learner: as moonshot_e5.FEATURE_ORDER (41 columns: ranks, squared ranks, binaries); rank = (rank-0.5)/n with midrank ties, masked by present before ranking, NaN -> 0.5; vol20 per e1.Study._signals convention; vc10_60 min_periods 8/10 and 45/60; rebase pre = level(s0-1), peak = max level(s0..t), s0 in [t-40, t-6]; IDX spike for rebase = (ret1 >= 0.30) | (lock_up & tradeable) (declared superset of the draft); creep5v20 requires full 5/20 present windows; debounce DEBOUNCE 5 with NaN counting as outside; one FEATURE_ORDER for all markets (constant columns tolerated by the ridge; e5.py must also report which columns were constant per market). Learner: L2 logistic, numpy IRLS 25 iterations, lambda = 1e-3 * n_rows_used, all positives + 10% seeded negative subsample weighted 10 (seed 20261015), 6 fits (3 markets x {U, D}); Arm A score = logit_U, Arm B = logit_U - logit_D; threshold = discovery 99.5th percentile of each arm's score over evaluable ticker-days (fixed once, never searched).
- labels: U = max level(t+1..t+5)/level(t) >= 1.30 on the reference chain (as e1.Study); D on US/CRYPTO = min level(t+1..t+5)/level(t) <= 1/1.30; D on IDX = rate-matched threshold q fixed once on discovery so P(D) = P(U) (IDX Arm B DIAGNOSTIC, reported by ARB regime using market.REGIMES); labels need t+5 inside the period; crypto unit resets (close/prev >= 20 or <= 1/20) censor labels (NaN) for t-5..t of that name; list the known cases to verify (COCOS 2021-01-23, DREP 2021-04-02, SUN 2021-06-18, LUNA 2022-05-31, VIDT 2022-11-09, BNX 2023-02-22, QUICK 2023-07-21, BTCST 2021-03-19).
- matched controls: trading stage controls_version "v3" primary (v2 reported), 200 draws, seed 20261007; detection stage e1.Study(pool_units="as_traded" for US, pool_version="v3"); paired statistic = per-signal excess over the mean of its matched controls with a session-cluster bootstrap (10,000 resamples, seed 20261015, one-sided p; refuse to judge any gate when n_clusters < 2); the harness draw-distribution p is reported, not judged.
- stages: 0 reproduce (re-run each precondition run from ITS recorded summary.json config on the pinned panel; REPRODUCED iff the rule-side statistics match as e3/e4 define it; the only accepted deviation is the known 4th-decimal matched-baseline difference from controls.py bcb89f0; status on record); 1 information (discovery, fill-independent: fit, threshold, debounced flags, plan-window return on the reference chain for flags and matched controls alike — entry level at close t+1 on IDX / open t+1 on US-CRYPTO, exit level at the 5th close — no fill/lot/lock/cost filter; AUC_U, AUC_D, E30/D30 precision and lift vs matched, directional ratio with cluster-bootstrap CI, pre-move split (ret1 < 10% vs >= 10%), univariate matched-set AUC/lift table for every ranked feature, A0/A1 rows (base rate, precision, Wilson bounds, lift vs volatility-matched controls), constant-column report; GATE to stage 2: debounced flags >= 200 AND paired gross excess > 0 with cluster p < 0.025 AND excess > 0 in every discovery year with >= 50 flags; primaries P1 = IDX Arm A, P2 = CRYPTO Arm B; everything else diagnostic); 2 execution (discovery, only arms that passed stage 1 plus A1 if its lift >= 2.0 at p < 0.05: backtest.run under the market plan with the market's primary fill model and controls v3, then backtest.paired_excess on the trades; admissible iff e3.admissibility verbatim AND paired NET excess p < 0.025 AND every pre-registered sensitivity keeps rule-minus-matched > 0 AND admissibility holds on the subset of trades with exit-session participation <= 10%; sensitivities: IDX fill A and one-tick-per-side cost; US fill A as_traded, quarantine unit_schedule, +1.5%/side stress; CRYPTO participation 0.05 with doubled costs, and CRYPTO_CLOSE; in-flag break-even precision p* reported as a descriptive bound); 3 freeze (e5-freeze copies discovery/model.json coefficients, intercepts and thresholds into moonshot_e5.py literals and sets SELECTED per market; refuses if literals already set; validation refuses unless literals == model.json); 4 validation (2023, one write_run-recorded run per stage-2-admissible arm plus its sensitivities; pass iff scored >= 100 (US >= 200), avg net > 0, paired net excess p < 0.025, harness p < 0.05, sensitivities agree in sign, detection Wilson lower bound > 2023 base rate; claim level PROVISIONAL).
- plans: one per market, the recorded one: IDX next close -> 5th close, fill C primary, ca_mode registry, Rp10,000,000, lot 100, max_participation 0.10; US next open -> 5th close, fill B primary, $5,000, cost tiers per profile; CRYPTO next open -> 5th close, fill A, $5,000, 0.1% fee + 0.1% tier per side (= the recorded E2 config). No plan search.
- loadability by e1.Study: protocol.json must ALSO carry E2-shaped top-level "periods" ({"discovery": [start, end], "validation": [start, end]} — per-market starts live under markets.<M>; e5.py passes the market's own window to Study and clips to the panel) and a "weak_signals" block in the E2 shape (ranked list + binary list; omit "ign"), because e1.Study reads both; verify with a test that Study loads the draft protocol for each market on a synthetic panel.
- runtime: ranked cross-sectional features make rules.causal_signals (prefix-first, recomputed per session) far more expensive than the E1/E2 rules (reviewer measured compute() ≈ 12x moonshot_g.features; an exhaustive prefix-first IDX run would be hours of CPU). Declare in protocol.harness a fixed "lookahead_cuts" (e.g. 12 sampled prefixes, seed fixed) for Stage-2 and validation harness runs, with the module's own prefix-invariance tests (tests/test_e5_rules.py) named as the proof of causality; record the setting in every run. In your report, MEASURE compute() and rank_features() wall time on a synthetic panel of ~900 names x 700 sessions and ~5,000 x 900, and estimate each stage's runtime from it.
- conventions to declare (read moonshot_e5.py as merged, fix commit 8b94372, and state exactly what it does): moonshot_e5.FEATURE_WARMUP = 60 (features NaN in the first 60 columns), DEBOUNCE = 5, moonshot_e5.WARMUP = 65 (compute() NaN in the first 65 columns) — so every Study/harness window must start at least 65 sessions before its period (the protocol's "warm-up" is 65, not 60); debounce(state, known) requires the trailing DEBOUNCE sessions to be KNOWN and outside, a NaN score is unknown (never "outside"), names outside the ranking pool (absent/untraded) get finite scores (ranks 0.5) and count as known-outside, and an undefined A0/A1 fact (e.g. creep5v20 NaN) is a known False state; binary features treat an undefined input as 0 (not_repriced is 0 when ret20 is NaN; quiet is 0 when any input is NaN) unless the merged module says otherwise. Add a test that flags at session s are identical when the window start moves by k sessions (window invariance) using the module's own helpers.
- notes to declare: trades.csv.gz of E5-era runs carries 14 columns (two additive); A0/A1 harness runs are recorded only after the freeze commit so their rule sha is the frozen one; declared_leaks = 2023 once-seen (name the E1/E2 validation episode tables on disk) -> any 2023 pass PROVISIONAL; not_fixed_and_why from the synthesis; search_size "6 fits, 2 arms x 3 markets, 2 primaries, no threshold/lambda/feature search"; claims "historical research on assumed costs…, nothing here is prospective performance, no real orders".

CODE. e5.py mirrors e4.py's structure: protocol()/version_dir/market_dir (research/E5/<MARKET>/<stage>/, exist_ok=False), _stamp with proto sha and code_state, run_reproduce, run_discovery (stage 1 then stage 2 in one command, writing discovery/{model.json, thresholds.json, stage1.json, univariate.csv, plans.csv, summary.json, gates.json}), run_freeze, run_validation, and an assert_within_validation(end) guard. Build the dataset through e1.Study (pool_units/pool_version per market, protocol data.panel_format) or an equivalent that reuses Study.level and elig logic — do not reimplement the reference chain. Fit with a self-contained numpy IRLS (no sklearn). Stage 1 control sampling must be vectorised enough to handle ~15k US flags x 200 draws in minutes (reuse controls' bucket codes; sample per-session from the pool; seed as in the protocol). Use backtest.run + backtest.paired_excess for stage 2 and validation; record every harness run row in plans.csv with the paired_excess dict; refuse gates when n_clusters < 2. CLI: e5-reproduce / e5-discovery [--accept-deviation] / e5-freeze / e5-validation, each --market IDX|US|CRYPTO (CRYPTO_CLOSE is reached as a sensitivity inside the CRYPTO stage, never a top-level market), with the e3/e4 dirty-tree refusal before any stage that writes under research/ or results/. Everything written under research/E5 must be deterministic given the protocol, the panel and the seeds (sort keys, fixed float formats as e3.write_csv/write_json do).

TESTS (tests/test_e5.py, synthetic only, built from tests/test_contract.py market() or tests/test_e3.py/test_e4.py helpers): protocol.json parses and every key e5.py reads is present; labels U/D on a synthetic panel incl. the IDX rate-matched q and a crypto unit-reset censoring case; IRLS recovers a planted coefficient direction on separable synthetic data and is reproducible under the seed; threshold = 99.5th percentile and debounce applied; stage-1 paired statistic and cluster bootstrap reproducible, and the gate refuses n_clusters < 2; the stage-1 plan-window return equals the harness's gross return for a fill-independent synthetic case (no lots/locks/costs); stage-2 admissibility composes e3.admissibility + paired net p + sensitivities + exit-capacity subset on a toy table; freeze refuses when literals are set and validation refuses when literals != model.json; assert_within_validation raises for any end past the validation end; constant-column report; the CLI subcommands parse and refuse on a dirty tree (mock). Expect 311 existing tests to keep passing.`

phase('Build')
log('Build: e5.py, CLI, tests, draft protocol')
const build = await agent(`${RULES}
${SPEC}
Work in this order: read e3.py/e4.py and the Phase-2a modules; write the draft protocol.json; write tests from the spec; write e5.py and the CLI; run the four checks; commit (NOT the research/E5 drafts); report.`,
  { label: 'build:e5-study', phase: 'Build', schema: BUILD_SCHEMA, effort: 'xhigh' })
if (!build) return { error: 'builder returned nothing' }

const LENSES = [
  { key: 'leakage', brief: 'look-ahead and leakage: every feature/label/threshold/control must use sessions <= t (or <= period end for thresholds); the holdout must be unreachable (assert_within_validation, Study/harness windows); crypto unit-reset censoring; US as-traded units at the detection stage; present-mask before ranking; debounce prefix-safety; per-year gate uses signal year; nothing reads validation during discovery' },
  { key: 'fidelity', brief: 'protocol fidelity: compare the draft protocol.json and e5.py line by line against ${MAIN}/handoff/kod-next-move/synthesis/E5_CEILING_protocol_draft.json, 06_phase2_integration_todo.md (freeze decisions, panel decision, every builder API note and review minor) and the refuters\' demands in 03_proposals_and_evidence.md §Refutations (#4); every parameter must come from protocol.json; every declared choice must be in the protocol; the consequences and claim levels must be present; e5.py must use the Phase-2a APIs correctly (controls v3, paired_excess columns, Study kwargs, CRYPTO_CLOSE via PROFILES[market].market, moonshot_e5 functions)' },
  { key: 'statistics', brief: 'statistics, numerics and tests: IRLS correctness and conditioning (constant columns, lambda scaling, weights), threshold/percentile definition, AUC computation, Wilson bounds, cluster bootstrap implementation (clusters = signal sessions, resampling with replacement over clusters, one-sided p convention), directional ratio CI, gate logic, n_clusters < 2 refusal, deterministic outputs; tests that would pass with the feature stubbed out; runtime hazards (per-signal Python loops over 15k flags x 200 draws)' },
]
async function review(b, round) {
  return parallel(LENSES.map(l => () => agent(`${RULES.replace('Commit with', 'You are READ-ONLY: do not edit or commit anything; you may run tests. (Ignore the commit instruction:) Commit with')}
You are an adversarial reviewer, lens: ${l.brief}. WORKTREE ${WT}, BRANCH ${BRANCH}. The builder's report (JSON): ${JSON.stringify(b).slice(0, 14000)}
Inspect "git diff eea274e" plus the untracked research/E5 drafts; read the changed files whole; re-run "python3 -m unittest" and "python3 -m idxsig rules" and paste the tails. Verdict accept only if nothing blocking or serious remains in your lens. Round ${round}.`,
    { label: `review:${l.key}:r${round}`, phase: 'Review', schema: REVIEW_SCHEMA, effort: 'high' })))
}
async function fix(b, findings, round) {
  return agent(`${RULES}
${SPEC}
Reviewers found these problems (JSON): ${JSON.stringify(findings).slice(0, 16000)}
Fix every blocking and serious finding (minor too if cheap), add or strengthen tests so each fixed defect would be caught, keep the draft protocol and the code consistent, run the four checks, commit (not the research/E5 drafts), report. If a finding is wrong, say exactly why in open_concerns instead of changing code. Round ${round}.`,
    { label: `fix:e5-study:r${round}`, phase: 'Fix', schema: BUILD_SCHEMA, effort: 'xhigh' })
}

phase('Review')
let current = build, history = []
for (let round = 1; round <= 3; round++) {
  const verdicts = (await review(current, round)).filter(Boolean)
  const serious = verdicts.flatMap(v => v.findings.filter(f => f.severity !== 'minor'))
  history.push({ round, verdicts })
  log(`Review r${round}: ${verdicts.map(v => v.verdict).join('/')} — ${serious.length} blocking/serious findings`)
  if (serious.length === 0) return { status: `accepted_r${round}`, build: current, history }
  phase('Fix')
  const fixed = await fix(current, serious, round)
  if (!fixed) return { status: 'fix_failed', build: current, history }
  current = fixed
  phase('Review')
}
return { status: 'unresolved_after_3_rounds', build: current, history }
