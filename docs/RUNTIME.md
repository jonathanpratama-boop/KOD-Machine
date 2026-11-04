# KOD runtime operations

This release connects validated recorded market data, descriptive context, the shared BTC/ETH paper account, retained run receipts and the workstation. It is a local, single-user Linux application. Every collection and account cycle is explicit. Opening a page reads a saved snapshot; it does not run discovery or place orders.

## Install and verify

From the repository root, use CPython 3.12 on Linux:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-runtime.txt
.venv/bin/python tools/check_runtime_release.py
```

The constraints record exercised package versions; they are not a complete dependency lockfile or vulnerability attestation. The existing CI audit remains in place. `--mode full` additionally runs the legacy KOD, IDX and workstation suites and requires the repository's original evidence/test fixtures. The focused gate uses synthetic inputs, runs no collection, checks restart idempotency and restores a verified backup into a new directory.

## Open the connected paper demonstration

```bash
.venv/bin/python tools/kod.py runtime --root runtime/kod-demo demo
.venv/bin/python tools/kod.py runtime --root runtime/kod-demo verify
KOD_RUNTIME_ROOT="$PWD/runtime/kod-demo" .venv/bin/python tools/kod.py workstation serve --offline --data-dir runtime/workstation-demo
```

Open the local URL printed by the workstation, then **Today**, **Candidates**, **Market map**, **Paper portfolio** and **Experiments**. The demo is synthetic. Repeating the demo must reproduce the same state without extra fills. It does not create a prospective performance record.

Use `status` for machine-readable current state and `verify` to check stored integrity. An unavailable or stale value remains unavailable. Empty holdings are not a substitute for an inaccessible account. The research workstation's SQLite database and runtime account directory are separate stores connected through the validated runtime snapshot.

## Process a recorded cycle

```bash
.venv/bin/python tools/kod.py runtime --root runtime/kod-paper once \
  --snapshot /absolute/path/snapshot.json \
  --profile /absolute/path/profile.json \
  --as-of 2026-11-04T00:05:00Z \
  --evidence-root /absolute/path/evidence
```

The cutoff is an explicit UTC observation boundary. This command processes recorded evidence; choosing an old cutoff cannot establish that a decision happened historically. Public-market snapshots require preserved raw evidence and receipts that reconcile to normalized rows. Synthetic evidence requires a synthetic account profile. The profiles, venue and quote currency cannot be mixed within one account.

The profile contains an ID, `evidence_type`, venue, USDT quote currency, initial cash, fee rate, slippage, quote age, intent expiry, and the tick/quantity/notional/status constraints for BTCUSDT and ETHUSDT. Use a new root for a different profile. Model costs are declared assumptions, not verified broker charges. Metadata changes block the affected use; they do not silently reset account history.

A decision produces an intent. A later eligible quote observation can produce a simulated fill; the observation used to decide cannot also fill its new intent. Receipt time, exchange time when available, and request-start time have distinct meanings. Quote sizes, costs, expiry and shared cash constrain paper fills. A missing mark does not become zero. The trend account's persistent drawdown/return kills are separate from the selective-repricing mandate's planned 5% price-stop constraint.

## Explicit capture and paper cycle

```bash
.venv/bin/python tools/kod.py runtime --root runtime/kod-public capture \
  --initial-cash 1000 --fee-rate 0.001 --slippage 0.001 \
  --symbols BTCUSDT ETHUSDT
```

This finite command collects a decision snapshot, processes it, then collects a second later snapshot for eligible simulated execution. It records actual collection times. Initial cash and costs are simulation assumptions. Keep the same profile on subsequent runs. A failed public request is a failed observation, not evidence of completed market coverage or a quiet market; inspect `last_attempt.json`. Availability in the release environment may be restricted by the public provider.

## Optional collection without an account cycle

The collector is an explicit read-only public request to the fixed Binance spot API; no credentials or order endpoint are accepted. Availability depends on the service and execution environment.

```bash
PYTHONPATH=idx-signals .venv/bin/python -m idxsig.runtime.collect \
  --public-binance --symbols BTCUSDT ETHUSDT \
  --output runtime/recordings/snapshot.json \
  --evidence-root runtime/recordings/evidence --days 120
```

Retain every snapshot and raw receipt. Collection alone does not run the account. To test future-observation execution, collect and process a decision cycle, then collect and process a later observation before its intent expires. Do not relabel an old quote as a new observation. The current collector supplies daily context for selected instruments; it does not claim completed global coverage, intraday ignition detection, actual cross-market fund flows or a predictive route.

No schedule, alert loop or continuous synchronization is installed by these commands. A production prospective trial needs a declared schedule, explicit membership, actual run receipts, missed-run records and an independent time anchor. Local hashes detect changes relative to retained records; they do not prove historical publication or independent observation time. A new execution profile starts its own cohort.

## Backup and recovery

```bash
.venv/bin/python tools/kod.py runtime --root runtime/kod-paper backup --output /absolute/path/kod-paper.zip
.venv/bin/python tools/kod.py runtime --root runtime/kod-restored restore --archive /absolute/path/kod-paper.zip
.venv/bin/python tools/kod.py runtime --root runtime/kod-restored verify
```

Backup takes the runtime writer lock and includes ordinary files under that root, excluding lock files. Keep raw evidence beneath the root if it must be included; evidence elsewhere must be backed up separately. The archive has a checksum/size manifest. Restore validates all bytes, rejects unsafe paths, duplicate entries, symbolic links and oversized files, and atomically publishes only into a new destination. It never merges accounts. Limits are 64 MiB per file and 2 GiB total; failure is explicit. Copying a backup outside the machine is an operator action, not an automatic sync.

After a failed run, inspect `last_attempt.json` and keep the original inputs, receipt and ledger. A pending operation retains immutable inputs for recovery; replay those exact inputs rather than silently substituting later data. Inspect the recorded blockers, fix or replace the affected input as a new observation, and retry the same cycle when its immutable input is unchanged. Do not repair integrity failures by deleting ledger lines, resetting cash or backdating records. Restore a verified backup into a new directory when recovery is needed. `verify` must pass before resuming account cycles.

## Candidate assessment

```bash
.venv/bin/python tools/kod.py runtime --root runtime/kod-paper assess --assessment /absolute/path/assessment.json
```

Assessments are versioned evidence records attached to a retained candidate. Preserve the original detection, supply explicit blockers and clearing evidence, and record the new state at its actual observation time. The runtime permits supported research-state updates; the record does not authorize orders. Use the [candidate workflow and assessment schema](CANDIDATE_WORKFLOW.md) when constructing an assessment. Missing essential underwriting inputs remain blockers.

## Research and promotion

Market context is descriptive. A candidate is a detection, not permission to enter. The experiment catalog records source availability and reported status; it does not turn a historical report into a rerun or a profitable strategy. Corrected evaluation runners preserve the original outputs. See [the operating-system map](OPERATING_SYSTEM.md) and [timing research](TIMING_RESEARCH.md) for the workflow and bounded next hypotheses.
