export const meta = {
  name: 'e5-build-harness',
  description: 'Phase 2a of E5-CEILING: five parallel, isolated harness/rule builders (controls v3, backtest matched-mean columns, e1 detection-stage changes, CRYPTO_CLOSE profile, moonshot_e5 rule module), each adversarially reviewed and fixed',
  phases: [
    { title: 'Build', detail: 'one builder per worktree/branch; synthetic tests; commit on its own branch' },
    { title: 'Review', detail: 'adversarial reviewer per build (read-only)' },
    { title: 'Fix', detail: 'fixer per build with findings; re-review once' },
  ],
}

const SCRATCH = '/tmp/claude-0/-home-user-KOD-Machine/74d3ac27-b8ad-5917-a6c3-ea51c410b250/scratchpad'
const MAIN = '/home/user/KOD-Machine'
const RULES = `
STANDING RULES (non-negotiable):
- You work ONLY inside the worktree path given below, on the branch given below. Never touch ${MAIN} or any other worktree. Never run git checkout/switch/reset/rebase/stash/push. Commit on your branch only, with "git -c user.name=Claude -c user.email=noreply@anthropic.com commit" and end every commit message with these two trailer lines exactly:
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SrR7rsdNDD1Fqye2K6MDSw
- Touch ONLY the files you own (listed below) plus new test files you create. If you believe another file must change, do not change it: report it in your output under "needs_other_file".
- Defaults must reproduce every recorded run unchanged: every new behaviour is opt-in (new parameter, new version key, new profile name). Do not change the meaning of any existing argument, column, key or default.
- Tests are synthetic only (no real panel loaded, no network, no harness run on real data). The holdout (IDX 2024-01-02..2025-02-21; US/crypto 2024 onward) is never read.
- Never present any number as performance. Never fabricate a passing test: run the commands and paste the real output.
- The repo's append-only rule: never modify anything under idx-signals/research/, idx-signals/results/, idx-signals/paper/, kod-machine/var/ or kod-machine/research/.
- Reference material (read-only): ${MAIN}/handoff/kod-next-move/synthesis/E5_CEILING_protocol_draft.json (the protocol draft) and ${MAIN}/handoff/kod-next-move/synthesis/RECOMMENDATION.md (its rationale). The harness patterns to imitate are idx-signals/idxsig/e3.py, e4.py, rules/moonshot_e3.py, rules/moonshot_e4.py, tests/test_e3.py, tests/test_e4.py, tests/test_plans.py in your worktree (they are at merge commit ae2cbee = base + PR #7).
- Final checks you must run from <worktree>/idx-signals before committing: "python3 -m unittest" (expect 244 + your new tests, 0 failures), "python3 -m idxsig rules" (source audit must pass), "python3 -m idxsig verify-runs" (OK), and from <worktree>: "python3 tools/check_append_only.py --all" (OK). Paste the tail of each.
Your final text is data for an orchestrator, not a message to a person.`

const BUILD_SCHEMA = {
  type: 'object',
  properties: {
    branch: { type: 'string' }, commit: { type: 'string', description: 'sha of your final commit' },
    files_changed: { type: 'array', items: { type: 'string' } },
    api_added: { type: 'array', items: { type: 'string' }, description: 'exact new signatures / keys / names other modules will call' },
    behaviour_summary: { type: 'string' },
    tests_added: { type: 'array', items: { type: 'string' } },
    test_output_tail: { type: 'string', description: 'verbatim tails of unittest, idxsig rules, verify-runs, check_append_only' },
    defaults_unchanged_evidence: { type: 'string', description: 'how you showed existing behaviour is byte-identical by default' },
    needs_other_file: { type: 'array', items: { type: 'string' } },
    open_concerns: { type: 'array', items: { type: 'string' } },
  },
  required: ['branch', 'commit', 'files_changed', 'api_added', 'behaviour_summary', 'tests_added', 'test_output_tail', 'defaults_unchanged_evidence', 'needs_other_file', 'open_concerns'],
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

const JOBS = [
  { key: 'h1-controls', wt: `${SCRATCH}/e5-h1-controls`, branch: 'e5/h1-controls',
    owns: 'idx-signals/idxsig/controls.py and a new idx-signals/tests/test_controls_v3.py',
    spec: `Add controls.VERSIONS['v3'] = (price_band, liquidity QUINTILE, volatility QUINTILE, market_cap quintile where the market has it (IDX mirror era), momentum tercile, drawdown tercile, listing_age), relaxed from the last key to MIN_POOL (5) exactly as v2 does. Keep 'v2' byte-for-byte (its recorded runs must reproduce; verify by asserting the v2 feature/bucket outputs on a synthetic market are identical before/after your change, e.g. by comparing against a copy of the pre-change function or a frozen expected table). features()/matched_draws() must accept version='v3' through the same call path backtest.run uses (read backtest.py:320-335 to see how controls are invoked and what keys summary.json records: the controls version name must flow into the recorded summary). Document in the module docstring why v3 exists (28% of IDX attempts under v2 were never matched on volatility). Tests: v3 bucket counts, relaxation order, v2 unchanged, as_traded path still works if controls.features has it.` },
  { key: 'h2-backtest', wt: `${SCRATCH}/e5-h2-backtest`, branch: 'e5/h2-backtest',
    owns: 'idx-signals/idxsig/backtest.py and a new idx-signals/tests/test_backtest_paired.py',
    spec: `In backtest.run(), add two additive per-trade columns to the trades frame written to trades.csv.gz: matched_mean_net_return (mean net return of that signal's 200 matched control draws, NaN where no control was drawn) and same_session_mean_net_return (mean net return of the same-session uniform draws for that signal), computed from the raw draw data already produced by the run (read how _baseline / dist() / the draws are built; do not change them). summary.json keys and random_draws.csv must be unchanged (prove with a synthetic run before/after: same keys, same values). The new columns must be present even when a draw set is empty. Add a helper paired_excess(trades_df) -> dict with per-signal excess (net_return - matched_mean_net_return), and a session-cluster bootstrap one-sided p for mean excess > 0 (cluster = signal_session, resamples and seed as parameters, default 10000 and 20261015, numpy only), returning n, n_clusters, mean_excess, p_one_sided, ci95. Tests: columns exist and are correct on a synthetic market with deterministic draws; summary unchanged; paired_excess on a toy frame with known answer; bootstrap reproducible under seed.` },
  { key: 'h3-e1', wt: `${SCRATCH}/e5-h3-e1`, branch: 'e5/h3-e1',
    owns: 'idx-signals/idxsig/e1.py and a new idx-signals/tests/test_e1_study_opts.py',
    spec: `Make e1.Study usable for E5 without changing E1's recorded behaviour. Opt-in only, all defaults as today: (1) Study accepts protocol['data']['panel_format'] in {'panel-global-v1' (default/legacy), 'panel-global-v2-units'} so the US repair panel (panel_us_repair-20261008T114805Z, format panel-global-v2-units with a unit_factor column) passes its format check at e1.py:~100; (2) guard the sig['ign'] / IGNITION lookup (~line 190) so a family module without an IGNITION member does not KeyError; (3) when the panel carries unit_factor AND the caller passes pool_units='as_traded', attach Market.with_units (see execution.py / backtest.py for how unit_factor is attached) and build the detection-stage pool with controls.features(..., as_traded=True) and the as-traded close for price_band in _pool/row; (4) when the caller passes pool_version='v3' (default 'v1' = today's price_band/liquidity/market_cap pool), add a volatility quintile key to the detection pool (define it from the same 20-session vol the signals use; relax to MIN_POOL like controls). Study's public outputs (detector_table, evaluate, signal_stats) must be byte-identical under defaults: prove it with a synthetic panel run before/after (hash the outputs). Tests for each option.` },
  { key: 'h4-profiles', wt: `${SCRATCH}/e5-h4-profiles`, branch: 'e5/h4-profiles',
    owns: 'idx-signals/idxsig/profiles.py and a new idx-signals/tests/test_profiles_crypto_close.py',
    spec: `Add a CRYPTO_CLOSE profile variant: identical to PROFILES['CRYPTO'] except entry_price 'close' (entry at the close of t+1, the latency-pessimistic sensitivity). Register it under PROFILES['CRYPTO_CLOSE'] without changing 'CRYPTO'. Check every place profiles are looked up by market name (backtest.py, cli.py --market choices, paper.py, exec paths) and report in needs_other_file where a choices list would need 'CRYPTO_CLOSE' added (do NOT edit those files). Tests: CRYPTO unchanged (field-by-field equality with a frozen expected dict), CRYPTO_CLOSE differs only in entry_price, costs identical (0.1% fee + 0.1% tier per side).` },
  { key: 'r-rules', wt: `${SCRATCH}/e5-r-rules`, branch: 'e5/r-rules',
    owns: 'new idx-signals/idxsig/rules/moonshot_e5.py, the registry entry in idx-signals/idxsig/rules/__init__.py (additive only), and a new idx-signals/tests/test_e5_rules.py',
    spec: `Write the E5 rule module per the protocol draft section "family" (read it in full). Requirements: numpy/pandas only; module-level literal constants only (rules/audit.py must pass: run "python3 -m idxsig rules"); FEATURE_ARGS = ("close","prev","high","low","volume","value","present","tradeable","lock_up","open") — check RULE_FIELDS in rules/__init__.py and how moonshot_g.features / moonshot_e1.features are called by paper.py and e1.py so the signature pattern matches. features(...) returns a dict of 2-D arrays (names x sessions) with: the E1/E2 weak-signal features (ret1, rel1, ret5, ret20, volr, valr, rngr, cpos, vol20, dd60, up5, zero20, age, logval20; brk60 binary; gap for US/CRYPTO when open exists; ara for IDX from lock_up) using the definitions in research/E1/protocol.json weak_signals and research/E2/protocol.json (copy the code from moonshot_g.py / moonshot_e1.py / e1.py Study._signals where it exists, do not reinvent); the pre-spike block: creep5v20 = median(volume t-4..t)/median(volume t-24..t-5) on present sessions (untraded = 0 volume), rngr5 = median(rngr t-4..t), vc10_60 = vol10/vol60; binaries quiet = (rngr5 <= 1.0) & (|ret5| <= 2*vol20*sqrt(5)) copied VERBATIM in logic from kod-machine/research/ZEALAND_PILOT_v1/03_card/price_facts.py (read ${MAIN}/kod-machine/research/ZEALAND_PILOT_v1/03_card/price_facts.py and kod-machine/kod/detectors.py:72-86), not_repriced = ret20 < 0.30, rebase per the draft. Every window trailing; column s uses sessions <= s only; age and zero20 must be NaN (not negative/0) before a name's first present session. rank_features(f, present, tradeable) -> per-session cross-sectional percentile rank among names present & tradeable at that session, masked by present BEFORE ranking, NaN -> 0.5, plus squared ranks; binaries 0/1. WARMUP = 60: compute()/features() returns NaN for the first 60 session columns of its view. score(ranked, coef, intercept) -> logit; flags(score, threshold) with debounce: a flag only on the first session a name's score is >= threshold after >= 5 consecutive sessions below (trailing, prefix-safe). A0_CREEP_QUIET = creep5v20 >= 1.5 & quiet; A1 = A0 & not_repriced. Module literals COEF_U, COEF_D, INTERCEPT_U, INTERCEPT_D, THRESHOLD_A, THRESHOLD_B per market as EMPTY placeholders (e.g. None) plus SELECTED = None, FEATURE_ORDER tuple (the exact column order the literals refer to), RULE_ID 'MOONSHOT_E5', VERSION 'v1', CANDIDATES tuple, FAMILY list in the shape the registry/paper expect (look at moonshot_e3/e4 FAMILY and family_flags). Register in rules/__init__.py registry() additively (see lines ~55-70). Tests (synthetic market built with tests/test_contract.py market() or tests/test_e3.py helpers): audit passes; prefix-first: features at column s identical when later columns are removed (use rules.causal_signals / the LookaheadError check the way test_e3 does); WARMUP masks the first 60; rank masking; debounce; A0 equals price_facts.measures() facts on a small hand-built series (import kod-machine's price_facts via sys.path, read-only); age/zero20 NaN before listing; no flags when literals are None (candidates must raise a clear error or return all-False, state which).` },
]

phase('Build')
log('Build: five builders in isolated worktrees')
const builds = await parallel(JOBS.map(j => () =>
  agent(`${RULES}
YOUR WORKTREE: ${j.wt}   YOUR BRANCH: ${j.branch} (already checked out there at merge commit ae2cbee)
YOU OWN: ${j.owns}
TASK: ${j.spec}
Work carefully: read the existing code paths you integrate with before writing; write the tests first against the spec, then the code; run the four final checks; commit; report. Expect 244 existing tests to keep passing.`,
    { label: `build:${j.key}`, phase: 'Build', schema: BUILD_SCHEMA, effort: 'high' }).then(b => b && { ...j, build: b })))
const built = builds.filter(Boolean)
log(`Build: ${built.length}/5 builders returned`)

async function review(j, round) {
  return agent(`${RULES.replace('Commit on your branch only', 'You are READ-ONLY: do not edit or commit anything; you may run tests')}
You are an adversarial reviewer. WORKTREE: ${j.wt}  BRANCH: ${j.branch}. The builder's own report:
${JSON.stringify(j.build, null, 1).slice(0, 12000)}
Inspect "git diff ae2cbee" there, read the changed files whole, and try to find: (a) any change to default behaviour (existing arguments, columns, keys, pool composition, cost values) that would alter a recorded run's reproduction; (b) look-ahead: any window that reads a later session, any cross-sectional statistic that leaks future listings, any rank computed before masking by present; (c) API mismatch with the callers that will use it (backtest.run, paper.py, e1.Study, rules registry/audit, cli) — read those callers; (d) tests that assert nothing or that would pass with the feature stubbed out; (e) numeric errors (NaN handling, division by zero, integer/float, empty draw sets); (f) violation of the standing rules (files outside ownership, research/results touched, network). Re-run "python3 -m unittest" and "python3 -m idxsig rules" yourself and paste the tails. Verdict accept only if nothing blocking or serious remains. Round ${round}.`,
    { label: `review:${j.key}:r${round}`, phase: 'Review', schema: REVIEW_SCHEMA, effort: 'high' })
}
async function fix(j, findings, round) {
  return agent(`${RULES}
YOUR WORKTREE: ${j.wt}   YOUR BRANCH: ${j.branch}   YOU OWN: ${j.owns}
A reviewer found these problems in your build (JSON): ${JSON.stringify(findings).slice(0, 12000)}
Fix every blocking and serious finding (minor ones too if cheap), add or strengthen tests so each fixed defect would be caught, keep defaults unchanged, run the four final checks, commit on your branch, report. If a finding is wrong, say exactly why in open_concerns instead of changing code. Round ${round}.`,
    { label: `fix:${j.key}:r${round}`, phase: 'Fix', schema: BUILD_SCHEMA, effort: 'high' })
}

phase('Review')
const results = await pipeline(built,
  async j => ({ ...j, r1: await review(j, 1) }),
  async j => {
    if (!j.r1 || j.r1.verdict === 'accept') return { ...j, status: j.r1 ? 'accepted_r1' : 'review_failed' }
    const f1 = await fix(j, j.r1.findings.filter(x => x.severity !== 'minor'), 1)
    const r2 = await review({ ...j, build: f1 || j.build }, 2)
    if (!r2 || r2.verdict === 'accept') return { ...j, build: f1 || j.build, f1, r2, status: r2 ? 'accepted_r2' : 'review_failed' }
    const f2 = await fix({ ...j, build: f1 || j.build }, r2.findings.filter(x => x.severity !== 'minor'), 2)
    return { ...j, build: f2 || f1 || j.build, f1, r2, f2, status: 'fixed_r2_unreviewed' }
  })
log('Done: ' + results.filter(Boolean).map(r => `${r.key}=${r.status}`).join(', '))
return { results, missing: JOBS.filter(j => !built.find(b => b.key === j.key)).map(j => j.key) }