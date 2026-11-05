# KOD component guide

KOD keeps evidence, research decisions and execution authority separate. The
component additions extend the existing runtime; they do not replace the pinned
trend account or turn research results into trading permission.

## Start here

All commands use the existing environment from [RUNTIME.md](RUNTIME.md).

```bash
# Inspect the available research contracts.
python tools/kod.py runtime strategies

# Validate a retained account in an isolated replay directory.
python tools/kod.py runtime --root /path/to/retained-runtime validate

# Exercise a bounded research workflow with explicitly synthetic observations.
python tools/kod.py research --root /tmp/kod-research-demo demo
```

The validation command reads the source and creates replay artifacts separately.
A timing-only capture can establish retained observation integrity, but cannot
establish a decision or fill that never occurred. Such a result is `UNKNOWN`,
not a passing account replay. Diagnostics return exit code 0 for pass, 1 for
failure and 2 for an inconclusive result.

## Code map

| Responsibility | Start reading | Boundary |
| --- | --- | --- |
| Existing capture and paper orchestration | `idx-signals/idxsig/runtime/coordinator.py` | Existing account profile and economic identities |
| Recorded-run validation | `idx-signals/idxsig/runtime/validation.py` | Isolated replay; source evidence stays untouched |
| Strategy contracts and risk assessment | `idx-signals/idxsig/components/strategy.py` | Allowlisted research templates; no strategy promotion |
| Signal-to-order composition | `idx-signals/idxsig/components/plans.py` | Allocation and independent risk approval before a simulation intent |
| Declared transaction costs | `idx-signals/idxsig/components/costs.py` | Costs are assumptions with an explicit price basis |
| Recorded execution lifecycle | `idx-signals/idxsig/components/execution.py` | Separate simulation profile; no exchange connectivity |
| Causal and warm-up checks | `idx-signals/idxsig/strategy_checks.py` | Validates observed evaluator behaviour, not profitability |
| Experiment specification and worker | `idx-signals/idxsig/research_workflow/` | Frozen evaluator, bounded attempts and reserved holdout |
| LLM reasoning and feedback | `idx-signals/idxsig/llm_arm/` | Frozen packets, first submitted response, complete cohort memory; no model service or promotion |
| Decision inspection | `kod-machine/kod/workstation/decision_inspector.py` | Read-only verified evidence and explicit missing stages |
| Optional runtime command wiring | `idx-signals/idxsig/runtime/component_commands.py` | Explicit invocation only |

The smallest useful reading path is strategy evaluation, risk assessment,
execution, then its tests. For research, read `spec.py`, `evaluator.py`, then the
worker. Existing account code remains the authority for its original cohort.

## Evaluate and check a strategy

A research request contains one named, versioned strategy and a chronological
observation series. `observed_at` means when the observation was available; it
must not be replaced with a bar's opening timestamp. The registered templates
are engineering examples, not validated investment strategies.

```json
{
  "strategy": {
    "id": "SMA_CROSS_SHADOW_V1",
    "version": "1",
    "parameters": {"fast": 2, "slow": 3}
  },
  "observations": [
    {"observed_at": "2026-11-01T00:01:00Z", "symbol": "EXAMPLE", "close": "100"},
    {"observed_at": "2026-11-01T00:02:00Z", "symbol": "EXAMPLE", "close": "101"},
    {"observed_at": "2026-11-01T00:03:00Z", "symbol": "EXAMPLE", "close": "102"},
    {"observed_at": "2026-11-01T00:04:00Z", "symbol": "EXAMPLE", "close": "103"}
  ]
}
```

```bash
python tools/kod.py runtime strategy-evaluate --input request.json
python tools/kod.py runtime strategy-check --input request.json --warmup-lengths 3 4
```

The checker compares full-history outputs with outputs produced using only
available prefixes. It also compares different warm-up lengths and repeats an
evaluation to detect unstable behaviour. A short history can produce an
inconclusive result. These checks complement the existing prefix-first harness,
source audit and sandbox; they do not prove the absence of every possible leak.

## Compose a simulation decision

`runtime strategy-plan --input plan.json` joins strategy evaluation, allocation,
independent risk assessment and order sizing. Its strict `KOD_SHADOW_PLAN_V1`
request includes observations, an availability cutoff, portfolio balances, a
timestamped bid/ask quote, allocation limits, risk limits, cost assumptions and
an expiry. `tests/test_components_plan.py:plan_request()` is the complete
synthetic example. The test below it follows the resulting intent through the
actual executor and a later observation.

The result contains either a simulation `submit_event` or explicit blockers,
plus shared input and decision identities. Missing warm-up, stale observations,
currency mismatches and excessive post-cost exposure cannot silently become an
order. Executable bid/ask prices already include spread, so that price basis
requires the additional spread assumption to be zero.

## Research worker

The worker consumes strict JSON proposals from a person or an AI. It evaluates
registered templates through KOD's own evaluator. It does not execute arbitrary
generated source code, call a model provider, or promote a strategy.

A protocol freezes the input dataset hash, feature/evaluator versions,
chronological folds, comparator, horizon, costs, seed, attempt budget and the
reserved holdout boundary. The worker retains failed attempts and deduplicates
the same hypothesis even when its display label changes. Restarting does not
reset the trial budget. The cohort also pins the evaluator's source fingerprint;
changing the implementation blocks further evaluation in that cohort.

Use a dedicated research directory, separate from account and timing captures.
`idxsig.research_workflow.demo.fixture()` returns a complete synthetic
`(protocol, dataset, proposals)` example. Save these as three JSON files, then run:

```bash
python tools/kod.py research --root /path/to/new-research run \
  --protocol protocol.json --dataset dataset.json --proposals proposals.json
python tools/kod.py research --root /path/to/new-research --details status
```

`proposals.json` is a list. The protocol specifies warm-up lengths, at most
2,000 observations, and chronological folds with a label-maturity embargo.
Its `dataset_sha256` is `idxsig.runtime.storage.digest(dataset)`, the canonical
JSON content hash. Changing data requires a new protocol/cohort. See
`idx-signals/tests/test_research_workflow.py` for accepted inputs and rejected
boundary cases.

The worker verifies the normalized dataset hash. Dataset `source_hashes` are
declared references: this evaluator does not reconcile normalized prices with
raw source bytes. Recorded inputs therefore report `DECLARED_NOT_RECONCILED`;
this must not be presented as independently verified market provenance.

The initial evaluator uses later observed close prices as explicit price
proxies. Its results are research comparisons; they are not simulated broker
fills, a portfolio equity curve, or evidence of execution feasibility. Fold
names do not imply that a model was trained: the initial templates are fixed
rules. Previously inspected periods remain development data.

## Execution and inspection

The optional executor has its own versioned profile and journal. It tracks
pending, partially filled, filled, cancelled, expired, rejected and unknown
orders. An unknown order keeps its reservations until an explicit supported
resolution. Reconciliation checks recorded state; it never fabricates a missing
fill to make balances agree. Every fill remains explicitly simulated.

```bash
python tools/kod.py runtime --root /path/to/new-simulation execution-replay --input events.json
```

Open the workstation's **Timing** page and select an attempt to inspect the
retained chronology. A price chart requires verified retained bars. Missing
decision, executable quote or fill times remain missing. Historical bar prices
are shown at their event times with separate receipt evidence; a chart does not
assert that KOD knew those prices before it received them.

## Compatibility and active experiments

- The pinned trend account and its vendor files keep their original bytes.
- Existing identifiers, schemas, receipts, timestamp tokens and frozen studies
  keep their original meaning. New outputs use separate versioned records.
- The selective-repricing mandate remains research-only. A template appearing
  in the research registry does not grant it account access.
- The cloud collection plan and its original/supplement cohorts are unchanged.
  Importing a module or opening a page cannot start collection or a trial.
- Clock evidence is assessed separately from byte integrity. Legacy clock
  parser mistakes are disclosed through derived assessments; original records
  are not rewritten.

## Design references

These are original KOD implementations informed by public documentation. No
upstream source files or additional trading engines are vendored by this pass.

| Reference | Applied idea |
| --- | --- |
| [NautilusTrader data](https://nautilustrader.io/docs/latest/concepts/data/) | Separate event/availability clocks and reproducible observation order |
| [LEAN framework](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/overview) | Explicit signal, allocation, risk and execution responsibilities |
| [LEAN reality models](https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/key-concepts) | Named cost and fill assumptions |
| [Freqtrade lookahead analysis](https://www.freqtrade.io/en/stable/lookahead-analysis/) and [recursive analysis](https://www.freqtrade.io/en/stable/recursive-analysis/) | Behavioural causal checks and warm-up sensitivity |
| [Qlib task management](https://qlib.readthedocs.io/en/latest/advanced/task_management.html) | Reusable, chronological experiment specifications |
| [RD-Agent](https://github.com/microsoft/RD-Agent) | Proposal, evaluation and retained feedback workflow |
| [Hummingbot executors](https://hummingbot.org/strategies/v2-strategies/executors/) | Explicit order lifecycle ownership |
| [Jesse charts](https://docs.jesse.trade/docs/charts/) | Inspect decisions alongside retained market observations |

See [OPERATING_SYSTEM.md](OPERATING_SYSTEM.md) for the wider system and
[TIMING_RESEARCH.md](TIMING_RESEARCH.md) for the current scientific questions.
See [LLM_ARM.md](LLM_ARM.md) for model input/output contracts, loss preservation,
timing alerts and the separately versioned engineering workbench.
