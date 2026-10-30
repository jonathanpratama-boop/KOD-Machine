# Engineering repair and regression checks

This repair builds on `d8dd00396b98c689de34276f6767b84f01d35186`. It repairs software invariants; it does not establish a trading edge or promote a paper policy.

## Quick progress check

Install both applications' declared dependencies. For reproducible research dependencies use `idx-signals/constraints-research.txt` with `idx-signals/requirements.txt`.

```sh
python tools/check_repair_invariants.py
python tools/check_repair_invariants.py --json /tmp/kod-engineering-check.json
```

The five groups exercise execution, process-safe storage, provider resumption, corrected outcomes/frozen evaluations, and historical workstation context/prices. A failed or unavailable group exits nonzero. The JSON receipt contains commands, output, timing, environment and source status. This is an offline regression check, not full CI or live-source monitoring. Run the existing full suites and analyst evaluation before release.

## What changed

* Execution configuration rejects invalid numerical parameters and indexes. New result publication requires coherent chronology and finite filled economics; older result verification remains compatible with historical column layouts. New runs include runtime metadata.
* Ledger batches preserve their exact historical byte prefix and publish atomically under a process lock. RUNS index updates use the same publication primitive. Exact payload retries are idempotent. An optional expected-head guard rejects stale proposals.
* Panel data and manifests publish without clobbering; gzip bytes do not depend on filenames. New build identities avoid second-resolution collisions; old manifests remain readable.
* Provider resumes bind to provider, universe, parameters and an absolute window. Cached bytes are checked before reuse. A changed request or a legacy unbound directory produces an actionable error; use a fresh output directory and preserve the old evidence.
* Historical scenario calculations share a selected context with their supporting traces, and record source lineage. New v2 decision packets pin their selected inputs; legacy v1 reproduction remains explicit.
* Price revisions distinguish a retry from repeated A→B→A changes within one second. Classification snapshot ties use recorded order. The additive workstation migration runs transactionally on first open.
* Effective outcomes apply availability before revisions and validate persisted correction links. Learner evaluation decisions have a separate immutable ledger; live descriptive metrics are still available.

## Frozen learning evaluations

```sh
cd idx-signals
python -m idxsig learner3-freeze
python -m idxsig learner3-report
```

Freeze records a planned evaluation only once per protocol/look, with its membership, hashes, seed, statistic and threshold. Reporting is read-only. Later corrections are linked for review and do not replace the original verdict. Actual recording time is separate from the eligibility cutoff; a retrospective freeze is not evidence it existed earlier. The new `paper/learner_v3_evaluations.jsonl` is protected by the append-only check.

## Receipt recovery

`paper.append()` raises `ReceiptPendingError` if events committed but external receipts remain unavailable. Its `record_hashes` identify those events. Retry receipts using `paper.retry_receipts(record_hashes, path=ledger_path, timestamper=stamper)` rather than regenerating events. Existing tokens are never replaced. Late receipts keep their actual authority timestamp and cannot retroactively prove a pre-outcome freeze. This API performs external timestamp requests only when explicitly invoked.

## Split-aware execution candidate

The default execution spec and active PAPER-POLICY-v4 are unchanged. The repaired research contract is explicit:

```python
from idxsig.contract import SPEC_V2_2
# Pass spec=SPEC_V2_2 to replay/forward_step or the compatible breakout API.
```

EXEC-US-v2.2 recomputes affordable/risk-constrained whole-share size after unit changes and fee-tier changes, and records resizing/cancellation. Its price-band sizing uses decision-time constraints rather than benefiting from the observed opening price. Historical EXEC-US-v2.1 records keep their old recipe and replay. Real gaps can still exceed planned stop losses.

## Compatibility and recovery

Back up the workstation with its existing verified backup facility before upgrading. Migration 6 adds lineage/record-order metadata while preserving earlier migration checksums. Older binaries must not open a newer schema; rollback uses the pre-upgrade backup with its matching code version. Do not manually lower the schema version or rewrite stored hashes.

Atomic publication is designed for local POSIX filesystems (the existing macOS/Linux workflow), using flock, same-filesystem staging, fsync and no-clobber hard links. It is not a distributed-storage lock. A terminated process may leave an unreferenced hidden staging file or object; it must not expose partial committed bytes. Preserve and diagnose an already damaged ledger instead of truncating or rehashing it.

Existing raw evidence, manifests, forecasts, protocols, panels and result records are preserved. Read-only integrity checks can identify old problems; a repair is recorded separately from the original. Passing this suite does not certify live-source availability, all historical experiments, deployment operations or profitability.
