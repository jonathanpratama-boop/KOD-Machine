# LLM_ARM: reasoning, evidence and learning

LLM_ARM now has a separate, runnable engineering workbench and a read-only audit
of the original experiment. It gives an external model structured evidence,
retains its submitted answers and failures, imports independent outcomes, and
passes complete prior-cohort feedback into the next cohort. It does **not** run
a model service, train model weights, execute model-generated code, or grant
trading permission. Its reasoning capability depends on the external model.

## What changed

| Capability | Implemented behavior |
| --- | --- |
| Reasoning | Frozen model identity, prompt, as-of packet, source excerpts and hashes; facts separated from inference, counterargument and uncertainty |
| Timing | Context age, set-seal-to-packet delay, packet-to-response elapsed time, frozen latency budget and entry deadline |
| Loss accounting | Fixed candidate roster; every submitted attempt retained; outcomes imported from the exact BASE5 register set |
| Learning | Complete closed-cohort memory, including abstentions, rejected responses, missing submissions, unknown labels and negative outcomes |
| Improvement | Falsifiable engineering/strategy proposals, exportable for a separately frozen research request |
| Monitoring | Own `runs.jsonl`, immutable event copies, local deduplicated alerts, status and checkpoint commands |
| Legacy experiment | Structural readiness audit; no early performance look or changes to frozen v1 calls |

## Five-minute demonstration

From the repository root, using Python 3.12:

```bash
python tools/kod.py llm --root /tmp/kod-llm-demo demo
python tools/kod.py llm --root /tmp/kod-llm-demo status
python tools/kod.py llm --root /tmp/kod-llm-demo memory
```

The example contains invented data, one ABSTAIN, a rejected retry, and a **-12%**
BASE5 outcome. The negative outcome remains visible although no BACK call was
made. This is a hypothetical candidate outcome, not an account loss. Repeating
the demo preserves the same records. No model or market service is contacted.

## Operational flow

1. An operator freezes a finite candidate roster and model identity in `spec.json`.
   Enrolment must precede every candidate's entry cutoff. Candidate selection is
   outside the model. This is an engineering cohort, not an authorized strategy
   experiment or an amendment to `LLM_ARM_v1`.
2. `prepare` freezes the source excerpts, their declared retrieval times, the
   context cutoff and the prompt. Give the returned packet to the selected
   external model. Source text is untrusted data, never operating instructions.
3. `record` stores the submitted response, including malformed JSON, rejected
   answers and retries. Only the **first submitted response** can be admitted;
   lateness, excessive elapsed time or invalid fields prevent admission.
4. `resolve` imports matching BASE5 outcomes from the speculation register. The
   model response contract does not accept outcomes, P&L, execution permissions,
   code, or scorer changes. Existing paper verification remains authoritative.
5. `watch` records local alerts. `memory` becomes available only when every
   expected candidate has a resolution and no response remains pending. Unknown
   labels stay unknown. The next cohort freezes the complete memory it receives.

```bash
python tools/kod.py llm --root /path/to/new-cohort init --spec spec.json
python tools/kod.py llm --root /path/to/new-cohort prepare --set-id SET_ID --input context.json
python tools/kod.py llm --root /path/to/new-cohort record --set-id SET_ID --input response.json
python tools/kod.py llm --root /path/to/new-cohort resolve --register idx-signals/paper/speculations.jsonl
python tools/kod.py llm --root /path/to/new-cohort watch
python tools/kod.py llm --root /path/to/new-cohort proposals
```

Use `idxsig.llm_arm.demo.fixture()` and `response_for(packet)` for exact input
shapes. `spec.model` requires the actual provider and model identifier. A model
or prompt change starts a new cohort. The spec pins a latency budget, each full
speculation set, its outcome due date and either a matching numeric comparator
or explicit `null`. Missing comparators create alerts, not invented forecasts.

`context.json` contains `as_of`, `observations`, and a `sources` list. Each source
has `id`, `url`, `retrieved_at`, and `content`. Responses require the packet hash,
matching model identity, BACK/AVOID/ABSTAIN, all three probabilities, sourced
facts, inferences, counterargument, uncertainties, timing assessment and either
one falsifiable proposal or `null`. A directional call requires sourced facts.

`watch` exits 2 when current alerts exist, 0 when none exist, and 1 on a blocked
operation. It does not send email or push notifications. An operator can route
this exit status to their service monitor. Archived ALERT events remain in
`runs.jsonl` even after a condition clears. Integrity errors are emitted to
stderr and exit 1; a damaged journal is not silently repaired to claim health.

## Learning and improvement boundaries

Learning here means **retained feedback supplied to future reasoning**, not
automatic neural-network training. All candidates from the selected prior cohort
enter memory. This prevents selecting only winners within that cohort; it does
not prevent an operator choosing a favorable cohort from elsewhere. Choosing
model versions using this feedback consumes development evidence. A genuinely
new, frozen prospective comparison is still required for a strategy claim.

Probability scores include admitted ABSTAIN calls and are withheld until the
engineering cohort closes. Outcomes and negative-outcome alerts remain visible
for operations. Scores are descriptive development feedback, never a promotion
test. Missing outcomes, rejected answers and unsent calls remain in the expected
denominator. Missing learner scores are `null`, never zero. Supplied comparator
records are not independently authenticated by this workbench.

`proposals` exports ideas and their source IDs. A proposal must be translated
into the existing strict `research` protocol/dataset/template contract before
`python tools/kod.py research ... run` can evaluate it. That worker reserves
attempt budget, retains failures and forbids arbitrary generated code. Software
changes go through a separate branch, review and tests. Neither passing software
tests nor a model's confidence grants strategy promotion or deployment rights.

## What the integrity controls do and do not prove

- The manifest is bound into the event journal. Each event has a hash-chain row
  and a separate immutable intent file. Ordinary edits, missing intents, torn
  tails and journal truncation are detected. `recover` can restore intact intent
  records after an interrupted write; it cannot invent a missing event.
- `status` emits a checkpoint. Retain it outside model-controlled storage and
  supply it through `status --checkpoint checkpoint.json` to detect deletion of
  both local event copies. Without an external checkpoint, coordinated replacement
  of the entire directory cannot be detected. This is not an RFC 3161 timestamp.
- Give the model the packet and an output channel only. The trusted supervisor
  must own the journal, resolver, tests and deployment credentials under separate
  permissions. Python functions alone are not an operating-system security boundary.
- The workbench observes submitted responses, not undisclosed provider generations.
  A future provider supervisor must reserve and record every request before
  inference, retain exact provider responses and errors, enforce token/cost/time
  budgets, and keep credentials outside prompts before claiming full coverage.
- Source hashes bind supplied excerpts; declared times and URLs do not establish
  historical availability or factual truth. Citation checks establish source-ID
  existence, not entailment. External receipts and the existing paper verifier
  remain necessary for authoritative research claims.
- Wall-clock intervals include transport and operator time. They are not pure
  provider latency, clock synchronization proof, first-price-move measurements,
  or execution feasibility. Existing runtime timing captures supply those
  additional boundaries where measured; this workbench never invents them.

## Original v1 experiment

```bash
python tools/kod.py llm audit-v1 \
  --calls idx-signals/research/LLM_ARM_v1/calls*.jsonl \
  --register idx-signals/paper/speculations.jsonl
```

The audit uses exact `RUN30_5`, `FADE10_5`, `BEATS_TWINS_5` on `BASE5`. NEXT1
resolutions cannot count toward the 60-call first look. Empty sources are a
quality gap, not a retroactive exclusion rule. Text saying a numeric forecast
exists does not verify a sealed comparator. The frozen v1 protocol and all
original calls remain unchanged.

The repository evidence watcher runs this readiness audit daily and on manual
workflow dispatch. Each run uploads an audit/log artifact; hard structural
problems fail the workflow. Missing sources/comparators are visible warnings.
GitHub notification delivery depends on the account's Actions notification
settings. This monitor does not generate new LLM calls or collect market data.

Code map: `idxsig/llm_arm/contracts.py` defines contracts; `journal.py` owns local
durability; `workbench.py` connects packets, outcomes, memory and alerts;
`audit.py` reads v1 evidence; `__main__.py` exposes the commands.
