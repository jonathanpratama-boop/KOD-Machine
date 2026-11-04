# Research and source audit — evidence, corrections and boundaries

Inspected default: `c2e9c54ba85c591c2ed5628295159335667a1b84`. Claude study branch: `a6f821cc6bfcb5cac2bc27d04e71e23a566c8efd`. Hermes ignition branch: `c7c84127e94b6debf691d321fa553377dc4af575`. Later Hermes policy and INFO_MAGNET source commits are linked below. No historical market backtest or new price-outcome download was performed in this audit.

## Disposition of the supplied prompt

Accepted: paper-only operation; frozen history; UTC and availability contracts; prospective measurement; actual quote references after a decision; missingness and failed attempts retained; aliases rather than history renames; distinct costs; isolated branch and no automatic merge.

Corrected interpretations:

- Section2.1 asks to run corrected historical peer/pressure studies, but overriding rule0.9 prohibits new historical early-entry retests while the close rule is unresolved. The corrected code remains available; no rerun occurred.
- The Binance-announcement sample's approximately80% response inside the announcement minute applies to that tested event family. It does not establish that every public-news opportunity is impossible.
- The daily flow/peer/attention nulls apply to their specified inputs, samples, horizons and costs. They are not a proof that every possible dated non-price source lacks information.
- The proposed combined avoid checklist has not been validated as one strategy. Individual descriptive findings differ in market, horizon, coverage and control design. Flags may inform research; they must not silently become mechanical entry vetoes or claimed profitable rules.
- A fixed historical return label cannot be renamed into a prospectively executable entry. An execution assessment starts from a quote actually available after the forecast.
- Candidate assessment overlays filter their analytical cutoff; they are not historical availability replays. The actual `recorded_at` remains separate. The misleading "known by cutoff" docstring was corrected without changing projection semantics or historical bytes.
- Owner eToro costs of about1% per side plus spread are an **owner-supplied estimate**, not a verified current account-specific tariff. The account entity, product, tier, FX and withdrawal/settlement assumptions remain separate.

## Findings and actions

| ID | Finding and evidence before | Disposition / evidence after | Severity |
| --- | --- | --- | --- |
| R01 | `NEIGHBOURS_v1` / `PRESSURE_v1` original selection used future-complete labels; default already contains `research_evaluation.py` and additive correction runners | Original files remain frozen. No original-data rerun under the close rule. Catalog must continue `RESEARCH_CORRECTION_PENDING`; original null is reported evidence with a defect, not corrected confirmation | High research-validity |
| R02 | Hermes frozen controls exclude coins with an ignition in the next72h. Claude reproduction reports past-only X4 control mean+0.27% versus−0.61% in2023–26 | Existing shared `controls.py` has no such future-trigger exclusion; no defect was invented there. Added opt-in `research_controls.past_only_control_pool` with synthetic causality tests. Historical controls v1–v4 and Hermes files unchanged | High if reused |
| R03 | Claude reproduction did not reproduce “dead by day3”:38% of2023–26 day14+20% winners were slow. Existing live modules contain no located hard day3 drop | Hermes's later pushed policy already contains CorrectionC1. Preserve it as a probability observation; do not alter historical policy bytes or add a new hard filter | Medium evidence interpretation |
| R04 | Original NEIGHBOURS report says482,598 coin-days; machine result `rows_test` is469,339 | Difference documented. Earlier default correction/catalog already records it. No number in a frozen result/report rewritten | Medium denominator |
| R05 | Frozen bear reproduction uses direct futures/spot symbol matching; scaled contracts such as1000SHIB require explicit identity and quantity semantics | New future-facing mapping must be exact and versioned; prefix stripping is insufficient. Historical results are not recomputed or silently relabelled by a helper | Medium data identity |
| R06 | `e6.load_manifest` concatenates archive months and then infers one ms/us unit from the maximum timestamp; mixed2024ms/2025us data can reinterpret old rows as1970 | Referred to data-adapter owner for synthetic reproduction and normalization patch. REST defaults remain ms; archive files need correct unit handling. See main `PATCHES.md` for implemented patch/test evidence | High temporal integrity |
| R07 | `IDX_DILUTION_v1/ERRATA_1.md` identifies IMPC split and FMII dividend,2 of15 scored2023 trades; listed-share update lags9–15sessions | Existing `sensors.emitennews_dilution` explicitly references ERRATA1 and warns it is a different untested announcement event. Existing catalyst tag reads recent headline evidence; no live import of the contaminated fifteen-trade result was found. Corrected event rule would be a new protocol | Medium research interpretation |
| R08 | Claude full ATTENTION_LEAD data/results/sample300 and reproduction differ from default; new Hermes branches contain additional materials | Exact scoped path/blob differences recorded in `BRANCH_GAPS.md`; no branch merge or frozen-file replacement | Medium evidence availability |
| R09 | Historical profiles and studies use different fee/slippage assumptions; eToro estimate differs from Binance proxy | Keep old assumptions pinned. New named profiles must carry version, source/verification status and venue/currency; no statement that research is executable on the owner's account | High execution validity |
| R10 | Two visible GitHub scheduled runs are successful TREND_CORE runs but start over7h after the configured cron time | Expected schedule and observed actual start must be separate timing fields. No claim that cron is precise; no unobserved sensor job failure manufactured | High timing observability |
| R11 | `sensors.emitennews_dilution` admitted future-dated sitemap entries and labelled modification date as `posted_at` | Patched live adapter: bounded dates through `today`; publication stays UNKNOWN; original `lastmod` retained as `extra.source_modified_at` with `SITEMAP_LASTMOD` role and adapter v2. Original raw responses/old ledger bytes remain unchanged | High source chronology |
| R12 | `microstructure._get` retried HTTP 403/451 three times | Patched to stop immediately on access blocks, as already done for 418/429. Transient 503 can still retry. Historical `_grid` interpretation unchanged | Medium source access |
| R13 | A paper fill on a later processing cycle could be attributed to the current decision rather than the original intent; existing economic timestamps alone do not establish actual processing clocks | Added `runtime/timing_paper.py`: stable profile/intent timing identity, original decision retained, explicit before/after identity lists, immutable logical clock links, new fill completion recorded as a simulated processing upper bound. Unknown historical processing remains UNKNOWN. No paper economics changed | High timing attribution |
| R14 | Runtime processing read its input before the invocation clock and recorded receipt after setup/clock-probe overhead; JSON array/null inputs raised before retaining an attempt; a changed file between observation and processing could mismatch the timing evidence | Explicit pre-read invocation clock and immediate post-read receipt, failed-input retention, and trace/run input-hash consistency guard before economic writes. Missing/failed reads leave receipt UNKNOWN. Four focused boundary regressions added | High measurement / identity |

“Not found” above is limited to inspected live paths and repository tree, not a claim about Hermes's unpushed local files or external scheduler state.

## Synthetic control-pool addition: before and after

New file: `idx-signals/idxsig/research_controls.py`. New tests: `idx-signals/tests/test_research_controls.py`.

The helper receives an independently retained as-of universe and observations containing `symbol` and `observed_at`. It excludes only observations in `(decision - lookback, decision]`. Later observations cannot alter the selection; outcome columns are never read. An empty control pool remains empty. The caller must separately exclude the treated symbol and retain the universe/evidence IDs. This helper is **opt-in infrastructure**, not a change to any frozen strategy, existing control version or completed outcome report.

Before implementation, from `idx-signals`:

```text
/workspace/scratch/cc07bfa08e52/kod-venv/bin/python -m unittest tests.test_research_controls
ModuleNotFoundError: No module named 'idxsig.research_controls'
Ran 1 test
FAILED (errors=1)
```

This is a missing-feature test, not a reproduction claiming the existing shared controls were defective.

After implementation:

```text
/workspace/scratch/cc07bfa08e52/kod-venv/bin/python -m unittest tests.test_research_controls tests.test_controls_v3 tests.test_controls_v4 tests.test_controls_quality
Ran 36 tests in 9.498s
OK
```

Tests cover future-trigger invariance, ignored outcome fields, exact window bounds, timezone normalization, naive timestamps, bad identities, invalid lookback and an empty pool; legacy control suites also passed. Commit identifiers are assigned by the integrating parent and recorded in the main release handoff; none is invented here.

## Source chronology and access-block patches: before and after

New regression module: `idx-signals/tests/test_source_clock_and_blocks.py`.

Before the fixes, `python -m unittest tests.test_source_clock_and_blocks` ran five tests and failed four checks: HTTP 403 and 451 each made three requests rather than one; the future sitemap item remained in the alert list; and `posted_at` incorrectly contained the sitemap modification date. The two HTTP assertions were subtests of one test method.

After fixing `sensors.py` and `microstructure.py`, the expanded command was:

```text
/workspace/scratch/cc07bfa08e52/kod-venv/bin/python -m unittest tests.test_source_clock_and_blocks tests.test_sensors tests.test_microstructure tests.test_catalysts
Ran 51 tests in 4.975s
OK
```

The first expanded run exposed seven missing-fixture errors for `research/CATALYST_REGISTER_v1/prereg_2.json`. The exact baseline fixture was restored through GitHub and verified as Git blob `d53449ae5929f1bd94553ce7fb57ea1751632caf`; no fixture content was changed. The successful run followed that restoration. Tests perform mocked requests only and exercise inclusive date bounds, preserved raw bytes, publication UNKNOWN, immediate access/rate-limit stop and permitted transient retry.

## Per-intent paper timing adapter

New module `idx-signals/idxsig/runtime/timing_paper.py` observes the coordinator's account snapshot and exact newly created intent/fill ID lists. Missing lists are not inferred from timestamps. Each profile/intent receives a stable sidecar identity and a parent processing-attempt link. Subsequent fills retain the original known decision time; unrelated new decisions cannot supply a missing old decision time. The original `made_at`, `fill_recorded_at`, quote clocks and source IDs remain immutable links.

`fill_at` is the local processing-completion upper bound for a newly observed **simulated** fill, not its exchange time. `executable_at`, where measurable, denotes the local processing observation of the later quote, explicitly marked in `executable_clock_basis`; it is not proof of a real executable exchange price. Previously filled economic history without its original processing observation retains timing status UNKNOWN and an explicit `paper_observed_fill_status=FILLED` link. Neither recorded replay nor this observer grants entry permission. Runtime economic account journals and original snapshots are not rewritten.

The initial missing-feature test failed on the absent module. After implementation and the stricter core status/stage contract:

```text
/workspace/scratch/cc07bfa08e52/kod-venv/bin/python -m unittest tests.test_runtime_timing_paper tests.test_timing_capture tests.test_runtime_account tests.test_runtime_coordinator
Ran 69 tests in 5.096s
OK
```

The initial eight adapter tests cover a later-cycle fill, original-decision attribution, byte-identical replay, explicitly unknown historical times, unrelated intent isolation, orphan/changed identity rejection, preservation of an already observed fill, stable terminal labels and unchanged evidence kind when a prospective snapshot is replayed. A ninth regression then verified a delayed original decision observation can complete a previously unknown decision clock without rewriting a known fill or its terminal status.

Final integration audit reproduced JSON array/null inputs raising `AttributeError` with zero retained attempts. The read-boundary patch now records both as failed attempts through normal schema validation. It also preserves the measured read receipt before setup overhead, leaves failed-read receipt unknown, and rejects a file mutated between the observed read and processing before writing the account or pending cycle.

```text
/workspace/scratch/cc07bfa08e52/kod-venv/bin/python -m unittest tests.test_timing_processing_boundary tests.test_timing_integration tests.test_runtime_timing_paper tests.test_runtime_coordinator tests.test_runtime_candidates
Ran 39 tests in 4.468s
OK
```

This validates synthetic contracts, not lower market latency or profitable execution. Broader wrapper validation is recorded by the integrating parent in the main release evidence.

## Scheduled execution evidence

Observed through GitHub `/actions/runs?event=schedule&per_page=20`: `total_count=2`, both completed successfully. At the referenced run head, `.github/workflows/trend_core_paper.yml` specifies `41 2 * * *` (02:41UTC).

| Run | Intended daily cron | Observed `created_at` / `run_started_at` | Difference | Result |
| --- | --- | --- | --- | --- |
| [41424726332](https://github.com/jonathanpratama-boop/KOD-Machine/actions/runs/41424726332) | 2026-11-02T02:41:00Z | 2026-11-02T09:56:32Z | 7h15m32s | success |
| [41615875671](https://github.com/jonathanpratama-boop/KOD-Machine/actions/runs/41615875671) | 2026-11-03T02:41:00Z | 2026-11-03T10:02:14Z | 7h21m14s | success |

These measurements establish a schedule-versus-observed-start discrepancy, not its internal GitHub cause. They are not measurements of source-publication latency or a claim that the paper strategy should have entered at the intended cron. The older external daily sensor job described in the prompt has no matching visible GitHub schedule record; its status/reason remains **UNVERIFIED**. No external scheduler was changed.

Latest inspected default CI: [41746825206](https://github.com/jonathanpratama-boop/KOD-Machine/actions/runs/41746825206), head `c2e9c54ba85c591c2ed5628295159335667a1b84`, completed success. Other rapidly superseded push runs were cancelled; cancellation is not a failing test.

## Source pointers and close-rule state

- [Close rule](https://github.com/jonathanpratama-boop/KOD-Machine/blob/a6f821cc6bfcb5cac2bc27d04e71e23a566c8efd/handoff/timing/EARLY_ENTRY_CLOSE_RULE_2026-11-03.md): dated-listing evidence only can keep that lane open; deadline2026-11-17; no other price/volume/flow/peer relabelling reopens it.
- [HERMES_NOV3_REPRO report](https://github.com/jonathanpratama-boop/KOD-Machine/blob/a6f821cc6bfcb5cac2bc27d04e71e23a566c8efd/idx-signals/research/HERMES_NOV3_REPRO_v1/REPORT.md):45claims;36reproduced,7partly,2not reproduced. Its general prose is read within its sample/definitions; no universal theorem is inferred.
- [Validation JSON](https://github.com/jonathanpratama-boop/KOD-Machine/blob/a6f821cc6bfcb5cac2bc27d04e71e23a566c8efd/idx-signals/research/HERMES_NOV3_REPRO_v1/VALIDATION.json):reported gatePASS; inspected as a frozen artifact, not rerun in this pass.
- [Original Hermes policy with CorrectionC1](https://github.com/jonathanpratama-boop/KOD-Machine/blob/82a3c08402ea84b5f8826beddcdb576b0f2ab44d/hermes/JUDGMENT_POLICY_v0.md): hard day3 rule removed by that branch owner.
- [INFO_MAGNET README](https://github.com/jonathanpratama-boop/KOD-Machine/blob/b04d31d5af7e34fa2f8e016bfffa8db1ab7ba13b/hermes/info_magnet_v0/README.md) and [plan](https://github.com/jonathanpratama-boop/KOD-Machine/blob/b04d31d5af7e34fa2f8e016bfffa8db1ab7ba13b/hermes/info_magnet_v0/PLAN.md): pre-result materials pushed; **NOT RUN**, primary-horizon/owner-cost addendum pending. Close rule remains unresolved as of the inspected commit.
- [IDX dilution errata](https://github.com/jonathanpratama-boop/KOD-Machine/blob/a6f821cc6bfcb5cac2bc27d04e71e23a566c8efd/idx-signals/research/IDX_DILUTION_v1/ERRATA_1.md): preserve the recorded result and two contaminated cases; a corrected event filter is a new experiment.

## Retained limitations

The repository is private and ordinary shell cloning was unavailable in this environment; connector access supplied exact source refs. Branch inventories are complete returned Git trees (`truncated=false`); full independent recomputation, local Mac inspection, current brokerage fee validation and external scheduler recovery were not performed. These gaps do not justify fabricating an empty queue, current holdings, an executable fill, a passed strategy or a source-access claim.
