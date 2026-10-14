export const meta = {
  name: 'kod-next-move',
  description: 'Map what KOD-Machine has tried and can do; generate, judge and stress-test proposals for the next experiment; synthesize a recommendation',
  phases: [
    { title: 'Understand', detail: 'six parallel readers over experiments, harness, data, KOD lab, PR state, paper policy' },
    { title: 'Propose', detail: 'six independent strategists, each from a distinct angle' },
    { title: 'Judge', detail: 'three judges score every proposal' },
    { title: 'Refute', detail: 'three adversarial refuters per top proposal' },
    { title: 'Synthesize', detail: 'one recommendation with a protocol draft and sequencing' },
  ],
}

const RULES = `
STANDING RULES (from the project owner; non-negotiable):
- Read-only. Do not modify, create, delete or move any file in /home/user/KOD-Machine. Do not run git commands that change state (no checkout, commit, stash, reset, pull, push). git show / git log / git diff are fine.
- Never present a historical experiment as prospective performance. Never manufacture probabilities, trade recommendations or results. If something is unknown, say unknown.
- The reserved holdout (IDX 2024-01-02..2025-02-21; US/crypto 2024 onward) is sealed. Do not read, summarize or compute anything on it.
- Do not propose re-tuning an already-frozen detector on data its outcomes were seen on.
- No real orders, no ASTRA/production changes.
- The repo is at /home/user/KOD-Machine (branch claude/idx-signals-test-repo-ds0jw7 is checked out). Other branches are visible via "git show origin/<branch>:<path>" and "git log origin/<branch>". PR #7 (not yet merged) is branch origin/claude/e4-fade-short-side. PR #3 is origin/claude/us-pipeline-v1. Fable's toolkit is origin/moonshot-tools.
- Python 3 with pandas/numpy is installed; running read-only Python (e.g. loading a JSON summary) is fine. Do not start harness runs or network pulls unless the prompt says so.
Return raw findings as your final output; your final text is data for an orchestrator, not a message to a person.`

const READER_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string', description: '10-25 lines: the essential map for someone designing the next experiment' },
    facts: { type: 'array', items: { type: 'string' }, description: 'precise, sourced facts (file path + number) — as many as matter' },
    constraints: { type: 'array', items: { type: 'string' }, description: 'hard constraints a next experiment must respect, with the file/rule that imposes them' },
    gaps: { type: 'array', items: { type: 'string' }, description: 'what is missing, untested, or unknown' },
    key_files: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'facts', 'constraints', 'gaps', 'key_files'],
}

phase('Understand')
log('Understand: six readers over the repository')
const READERS = [
  { key: 'experiments', prompt: `${RULES}
TASK: Build the complete record of every experiment and baseline in /home/user/KOD-Machine/idx-signals/research (E1, E2 incl. repair/repair_v2/repair_v3, E3, US_BREAKOUT_v1, IDX_CAUSAL_CAPACITY_v1, ZEALAND_PILOT_v1, US_PIPELINE_v1, EXEC_US_v2, EXEC_US_v2_1) PLUS E4 on branch origin/claude/e4-fade-short-side (git show origin/claude/e4-fade-short-side:idx-signals/research/E4/REPORT.md and .../E4/v2/REPORT.md and PROTOCOL.md files). For each: the question, the signal family, markets, discovery/validation periods, the exact headline numbers (hit rates, avg net vs matched random, p-values, N), the verdict, WHY it failed (mechanism: fade, costs, fat tail, fills, capacity), and which validation sets are now consumed by which family. Also list every detector family that has been frozen (names, modules) and the sealed holdouts. Be exhaustive and numeric; this map decides what is genuinely new.` },
  { key: 'harness', prompt: `${RULES}
TASK: Map what the idx-signals harness can express today. Read idx-signals/idxsig/execution.py, backtest.py, contract.py, exec_us.py, controls.py (matched controls), profiles.py, rules/__init__.py and every rules/moonshot_*.py (E1, G/E2, E3), plus the E4 additions on origin/claude/e4-fade-short-side (git show that branch's execution.py, profiles.py, rules/moonshot_e4.py, e4.py). Report: the signal interface (what a rule receives: which features, causal view), the execution models (entry rules, exit rules, holding, fill models A/B/B2/C, side long/short, costs, carry), the matched-control method (what it matches on), the holdout guard, how a run is recorded (results/RUNS.jsonl, summary.json), how a new experiment module is structured (e3.py/e4.py pattern: protocol.json + sha, discovery grid, admissibility), and the CLI. State clearly what CANNOT be expressed today (e.g. intraday, multi-name portfolio, pairs, external data inputs, conditioning on non-price features) and roughly what code each would need.` },
  { key: 'data', prompt: `${RULES}
TASK: Inventory every dataset available to the project and probe external data reachable from this session. (1) Local: idx-signals/data (panels, manifests, corporate_actions, universes) — for each panel: market, tickers, date range, fields (open/high/low/close/volume/value/present/tradeable/lock flags), provenance, whether delisted names are included (survivorship), and known data quality issues (read idx-signals/README.md and research/E2/repair*/ notes). Note what fields exist beyond price/volume (market cap? shares? sector? none?). (2) External via MCP: use ToolSearch to load mcp__FMP__secFilings, mcp__FMP__news, mcp__FMP__calendar, mcp__FMP__company, mcp__FMP__insiderTrades and make at most 6 small probe calls to learn: can FMP return historical 8-K / press-release filing lists with timestamps for a US ticker for 2021-2023? historical earnings dates? historical news with timestamps? Is history free/limited? Record exact capabilities and limits (date ranges, rate limits, errors). Also check mcp__Crypto_com__* and mcp__Gemini__* for what crypto history they expose. (3) Public free sources the harness could pull (SEC EDGAR full-text/8-K index, Binance klines) — state what is already used. Report what NEW information dimensions are reachable (filings timing, earnings dates, news timing, insider trades, funding rates, open interest) and for which markets/periods.` },
  { key: 'kod', prompt: `${RULES}
TASK: Map the KOD lab in /home/user/KOD-Machine/kod-machine: doctrine/KOD_DOCTRINE_v0.md, kod/detectors.py, ledger.py, score.py, verify.py, cli.py, seeds/, the committed var/kod.db (read-only via python sqlite3), tests. Report: what a case is (prospective vs retrospective), the information set rules (T-30D/T-72H/T-24H), the five detectors and their hit labels, evidence v2 grades, anchoring/timestamps/GitHub receipts, the promotion floor (30 prospective closed cases), the current counts (0 prospective), and exactly what it would take to open a prospective case today (inputs required, who/what decides the name, how an outcome is scored). Then analyze: could the daily idxsig paper-scan candidates (names that just had a +30% day) be a legitimate feed of prospective KOD cases, and what would the case ask (does the name reprice AGAIN within the horizon? does a catalyst surface?) — or is a pre-repricing watchlist needed, and from what? Be concrete about the lab's own rules.` },
  { key: 'prs', prompt: `${RULES}
TASK: Establish the exact state of branches and pull requests and what must land in what order. Use git log/show/diff on origin/claude/idx-signals-test-repo-ds0jw7 (base), origin/claude/us-pipeline-v1 (PR #3, EXEC-US-v2.1 contract), origin/claude/e4-fade-short-side (PR #7, E4 short side), origin/codex/e3-us-retention-protocol-v1 (PR #5 draft), origin/moonshot-tools. Use "git merge-tree --write-tree --name-only <base> <branch>" to detect conflicts between PR #7 and base, PR #3 and base, and PR #3 vs PR #7 (merge-tree is read-only). Report: which files conflict, the nature of the conflicts (e.g. both edit execution.py ExecConfig; PR #3 named its policy PAPER-POLICY-v4 and the base now has a different PAPER-POLICY-v4 from PR #6), what PR #5 proposes and whether E4 or E3 already covers it, and a recommended landing order with reasons. Also read .github/workflows to say what CI checks.` },
  { key: 'paper', prompt: `${RULES}
TASK: Analyze the prospective paper record and policy in idx-signals/paper (README.md, ledger.jsonl, scans/) and idxsig/paper.py. Using read-only python over ledger.jsonl: count SCAN/DECISION/OUTCOME by market and date; decisions by terminal state (PASS / NOT EXECUTABLE / BUY ON TRIGGER) and the reasons; outcomes scored so far with discovery flags (E30/E50/E100, r5max) and verdicts; the distribution of r5max across scored decisions. Explain precisely what APPROVAL-v2 requires for a BUY and why every candidate PASSes today (which pinned run, which numbers). Explain PAPER-POLICY-v4 (E3 rule, dormant). Then: what is the first date real prospective outcome evidence accumulates for each market, and what sample size per month the scans imply (candidates/day). Also note the detector identity each market uses and what a NEW detector family would need to change in paper.py to be scanned prospectively (the _detector() hook, validation_evidence, APPROVAL_PINS).` },
]
const maps = await parallel(READERS.map(r => () =>
  agent(r.prompt, { label: `read:${r.key}`, phase: 'Understand', schema: READER_SCHEMA })
    .then(x => x && { key: r.key, ...x })))
const map = maps.filter(Boolean)
log(`Understand: ${map.length}/6 readers returned`)
const MAP_TEXT = map.map(m => `### ${m.key}\n${m.summary}\nFACTS:\n- ${m.facts.join('\n- ')}\nCONSTRAINTS:\n- ${m.constraints.join('\n- ')}\nGAPS:\n- ${m.gaps.join('\n- ')}`).join('\n\n')

phase('Propose')
log('Propose: six strategists from distinct angles')
const PROPOSAL_SCHEMA = {
  type: 'object',
  properties: {
    title: { type: 'string' },
    angle: { type: 'string' },
    thesis: { type: 'string', description: 'the hypothesis in one paragraph and the mechanism that would make it true' },
    why_not_already_falsified: { type: 'string', description: 'how this differs from E1/E2/E3/E4/breakout in signal family, information source, or structure' },
    protocol: {
      type: 'object',
      properties: {
        family: { type: 'string' }, detectors: { type: 'array', items: { type: 'string' } },
        plans: { type: 'string' }, markets: { type: 'array', items: { type: 'string' } },
        discovery_period: { type: 'string' }, validation_period: { type: 'string' },
        admissibility: { type: 'string' }, matched_controls: { type: 'string' }, costs_model: { type: 'string' },
      }, required: ['family', 'detectors', 'plans', 'markets', 'discovery_period', 'validation_period', 'admissibility'],
    },
    data_needed: { type: 'array', items: { type: 'string' } },
    data_available_now: { type: 'boolean' },
    code_changes: { type: 'array', items: { type: 'string' }, description: 'concrete modules/functions to add, referencing existing patterns' },
    effort_hours: { type: 'number' },
    falsifier: { type: 'string', description: 'the exact result that kills it' },
    risks: { type: 'array', items: { type: 'string' } },
    directive_compliance: { type: 'string', description: 'how it respects holdout, no-retune, no-manufactured-results, pre-registration' },
    expected_information_value: { type: 'string', description: 'what we learn either way' },
  },
  required: ['title', 'angle', 'thesis', 'why_not_already_falsified', 'protocol', 'data_needed', 'data_available_now', 'code_changes', 'effort_hours', 'falsifier', 'risks', 'directive_compliance', 'expected_information_value'],
}
const ANGLES = [
  { key: 'information', brief: 'INFORMATION/CATALYST angle. Every failed experiment used tape-only signals. The KOD doctrine says repricings follow information (dated catalysts, primary documents before price). Design a pre-registered experiment that conditions on or detects INFORMATION timing (SEC 8-K/press-release timestamps, earnings dates, news timing, insider trades, crypto listing/unlock announcements) — e.g. does a +30% day WITH a primary document the same session behave differently from one without? or can a filing-type trigger alone be a detector? Use only data the data-reader says is reachable, and be explicit about look-ahead risk in filing timestamps.' },
  { key: 'new-family', brief: 'NEW TAPE FAMILY angle. The moonshot detectors all trigger AFTER the big day and then fade. Design a different tape-only family that is NOT "big up day": e.g. pre-spike accumulation (volume creep with price quiet, the KOD VOLUME_CREEP_PRICE_QUIET idea), post-fade second-leg (price retraced then re-base above pre-spike level), range compression/breakout from a long base (different from the 60-day high breakout already tested), relative-volume-without-return. Must be definable on the existing panels, prefix-causal, with matched controls.' },
  { key: 'structure', brief: 'STRUCTURE/EXECUTION angle. E3 (IDX plan grid) and E4 (short side) taught specific lessons: fades are real, tails are fat, liquidations kill, regime matters (E4 v2 only admissible in BTC-bear). Design the experiment that most directly exploits those lessons without re-tuning frozen detectors: e.g. the US/crypto long-side plan grid that E3 never ran (PR #5 proposes a retention variant), regime-conditioned long side, time-of-fade re-entry, or a portfolio-level test (many small positions, aggregate P&L and drawdown rather than per-trade averages). Be precise about what is new vs E3/E4.' },
  { key: 'kod-feed', brief: 'KOD PROSPECTIVE PIPELINE angle. The KOD lab has 0 prospective cases against a floor of 30, so its detectors cannot be validated. Design the cheapest legitimate pipeline that opens prospective KOD cases every day from an automatic source (candidates: the daily paper-scan names; a filing-driven watchlist; a volume-creep watchlist), with the information-set discipline (T-24H), evidence v2 objects, anchoring, and outcome scoring — and define the question each case asks. This is infrastructure, not a backtest; estimate when 30 closed cases would exist.' },
  { key: 'skeptic', brief: 'SKEPTIC angle. Assume the program has found no edge because there is none to find in daily-bar public-price signals after costs. Design the single most decisive, cheapest test that would either kill the whole "moonshot detection" thesis or locate where edge could live (e.g. gross-vs-net decomposition across all failed runs; capacity-vs-return curve; whether the "minority that runs further" is predictable by ANY feature at T-0 using a pre-registered feature set and a held-out year; or an upper-bound/oracle analysis). Your proposal may be "stop this family; redirect to X" but must still be a concrete pre-registered test with a falsifier.' },
  { key: 'regime', brief: 'REGIME/CROSS-MARKET angle. E4 v2 found admissibility only in a BTC-bear regime; E2 found the same fade in every market. Design a pre-registered test of regime-conditioning or cross-market lead-lag that is NOT a retune of frozen detectors: e.g. one regime variable declared in advance (breadth, BTC trend, IDX index trend, VIX proxy from the panel itself), applied to the existing frozen signals with the plan unchanged, or a cross-market signal (US spike -> crypto/IDX next session). Be explicit about multiple-testing and how the regime variable is fixed before looking.' },
]
const proposals = (await parallel(ANGLES.map(a => () =>
  agent(`${RULES}
You are one of six independent strategists. Your assigned angle: ${a.brief}

Here is the project map produced by six readers (treat as authoritative; cite it):
${MAP_TEXT}

Produce ONE best proposal for the next experiment from your angle. It must be pre-registerable (frozen protocol before any number), use discovery 2020-07..2022 (US/crypto) or 2021-22 (IDX) and validation 2023 unless you justify otherwise, never touch the holdout, use matched controls under the same plan, and state its falsifier. Be concrete enough that an engineer could implement it against the harness patterns the map describes (e3.py/e4.py). If your angle is infrastructure (KOD feed) adapt the fields sensibly (admissibility = acceptance criteria). You may read repository files to check feasibility. Do not propose anything that re-tunes a frozen detector on seen outcomes.`,
    { label: `propose:${a.key}`, phase: 'Propose', schema: PROPOSAL_SCHEMA }).then(p => p && { angle_key: a.key, ...p })))).filter(Boolean)
log(`Propose: ${proposals.length}/6 proposals`)
const PROPOSALS_TEXT = proposals.map((p, i) => `#${i} [${p.angle_key}] ${p.title}\nTHESIS: ${p.thesis}\nNEW BECAUSE: ${p.why_not_already_falsified}\nPROTOCOL: ${JSON.stringify(p.protocol)}\nDATA: ${p.data_needed.join('; ')} (available now: ${p.data_available_now})\nCODE: ${p.code_changes.join('; ')}\nEFFORT: ${p.effort_hours}h\nFALSIFIER: ${p.falsifier}\nRISKS: ${p.risks.join('; ')}\nCOMPLIANCE: ${p.directive_compliance}\nINFO VALUE: ${p.expected_information_value}`).join('\n\n')

phase('Judge')
log('Judge: three judges score all proposals')
const JUDGE_SCHEMA = {
  type: 'object',
  properties: {
    scores: { type: 'array', items: { type: 'object', properties: {
      index: { type: 'integer' }, novelty: { type: 'number' }, feasibility_now: { type: 'number' }, falsifiability: { type: 'number' },
      data_readiness: { type: 'number' }, directive_compliance: { type: 'number' }, information_value: { type: 'number' },
      total: { type: 'number' }, rationale: { type: 'string' }, fatal_flaw: { type: 'string' } },
      required: ['index', 'novelty', 'feasibility_now', 'falsifiability', 'data_readiness', 'directive_compliance', 'information_value', 'total', 'rationale'] } },
    ranking: { type: 'array', items: { type: 'integer' } },
    notes: { type: 'string' },
  }, required: ['scores', 'ranking', 'notes'],
}
const JUDGE_LENSES = [
  'a quantitative researcher who has seen hundreds of backtests fail in production: weight look-ahead, survivorship, multiple testing, and whether the falsifier is real',
  'a risk/compliance reviewer for this project (Ace): weight the standing rules, pre-registration discipline, holdout integrity, and whether the result could be misread as prospective performance',
  'an engineer who must ship it this week against the existing harness: weight feasibility, data readiness, effort, and whether the code changes reuse e3/e4 patterns',
]
const judgments = (await parallel(JUDGE_LENSES.map((lens, j) => () =>
  agent(`${RULES}
You are judge ${j + 1}: ${lens}. Score every proposal 0-10 on each criterion (novelty vs E1-E4/breakout; feasibility now; falsifiability; data readiness; directive compliance; information value), give a total (sum), one-line rationale, and a fatal flaw if any. Then rank all. Be harsh and specific; a proposal that re-tunes a frozen detector or touches the holdout gets directive_compliance 0.

PROJECT MAP (abridged):
${MAP_TEXT.slice(0, 14000)}

PROPOSALS:
${PROPOSALS_TEXT}`, { label: `judge:${j + 1}`, phase: 'Judge', schema: JUDGE_SCHEMA })))).filter(Boolean)
const agg = proposals.map((p, i) => {
  const s = judgments.map(j => (j.scores.find(x => x.index === i) || {}).total || 0)
  return { i, title: p.title, key: p.angle_key, mean: s.reduce((a, b) => a + b, 0) / Math.max(1, s.length), scores: s }
}).sort((a, b) => b.mean - a.mean)
log('Judge ranking: ' + agg.map(a => `#${a.i} ${a.key} ${a.mean.toFixed(1)}`).join(' | '))
const top = agg.slice(0, 3)

phase('Refute')
log(`Refute: 3 refuters each for top ${top.length}`)
const VERDICT_SCHEMA = { type: 'object', properties: { refuted: { type: 'boolean' }, severity: { type: 'string', enum: ['fatal', 'serious', 'minor', 'none'] }, reasons: { type: 'array', items: { type: 'string' } }, fix: { type: 'string' } }, required: ['refuted', 'severity', 'reasons'] }
const REFUTE_LENSES = ['look-ahead and data leakage (timestamps, survivorship, corporate actions, provider re-adjustment)', 'statistical validity (multiple testing across the grid, matched-control adequacy, N, regime overlap with discovery, validation already consumed by a sibling family)', 'execution realism (fills, capacity, costs, carry, liquidation, what the harness cannot model)']
const refuted = await pipeline(top, t => parallel(REFUTE_LENSES.map(lens => () =>
  agent(`${RULES}
Try to REFUTE this proposal through the lens of ${lens}. Default to refuted=true if you find a flaw you cannot see a fix for; severity fatal only if no protocol change rescues it. You may read repository files to check claims (e.g. whether the data fields exist, how controls.py matches).
PROPOSAL:
${PROPOSALS_TEXT.split('\n\n')[t.i]}
PROJECT MAP (abridged):
${MAP_TEXT.slice(0, 10000)}`, { label: `refute:${t.key}:${lens.split(' ')[0]}`, phase: 'Refute', schema: VERDICT_SCHEMA }))).then(vs => ({ ...t, verdicts: vs.filter(Boolean) })))

phase('Synthesize')
const synthesis = await agent(`${RULES}
You are the synthesizer. Produce the recommendation for the project owner, who asked: "what is the next move? make this work and explore new ideas; execute now." Honesty rule: do not promise edge; say what the next experiment would establish either way.

Inputs:
PROJECT MAP:
${MAP_TEXT}

PROPOSALS:
${PROPOSALS_TEXT}

JUDGE AGGREGATE (mean totals): ${JSON.stringify(agg)}
JUDGE NOTES: ${judgments.map((j, k) => `judge${k + 1}: ${j.notes}`).join(' || ')}
REFUTATIONS OF TOP 3: ${JSON.stringify(refuted.filter(Boolean).map(r => ({ i: r.i, key: r.key, verdicts: r.verdicts })))}

Deliver, in markdown:
1. STATE IN ONE PARAGRAPH: what has been established by E1-E4 and the baselines (numbers), and what that implies about where edge can and cannot live.
2. THE NEXT MOVE: one recommended experiment (may graft the best parts of runners-up), with a full protocol draft ready to freeze: question, family, detectors (exact definitions), plans, markets, periods, costs, matched controls, admissibility, validation criteria, consequence if passed, consequence if failed. Incorporate fixes the refuters demanded; list any refutation you could not fix and say why you proceed anyway or why you dropped the proposal.
3. INFRASTRUCTURE PREREQUISITES in landing order (PR #3 merge, PR #7, data builds), with what blocks what.
4. PARALLEL TRACK: if the KOD prospective feed should start now independently, say exactly what it is.
5. WHAT WE WILL KNOW AFTER: the decision tree on the outcomes.
6. ESTIMATED EFFORT AND RUNTIME, and what the owner must decide (e.g. permission to push a branch, merge PR #7).
Then append a JSON block fenced as \`\`\`json with keys: recommended_index, recommended_title, protocol_id_suggestion, prerequisites (array), parallel_track (string), implementation_steps (array of concrete steps referencing files).`, { label: 'synthesize', phase: 'Synthesize', effort: 'xhigh' })

return { synthesis, ranking: agg, proposals, judgments, refuted, map }