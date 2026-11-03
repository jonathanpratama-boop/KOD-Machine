# Ace → Claude: one local integration handoff kit

**Transfer package only. Nothing here has been pushed, merged, deployed or activated.**
Upload this ZIP to Claude's actual working environment and extract it there. A file
in Ace's Library is not automatically present in Claude's filesystem or GitHub.
The three original delivery archives below are embedded byte-for-byte unchanged;
reviewed adapter/audit/capture files are copied unchanged with individual hashes.
No product code, strategy, research result, frozen ledger or protocol was rewritten.

## Four requested inputs: where the actual artifacts are

| Requested input | Actual path inside this kit | Evidence / entry point |
|---|---|---|
| 1. Existing repair checkpoint | `originals/KOD-engineering-checkpoint-20261031.zip` | Library version 2; reviewed v1.4 repair, consolidated/ordered patches, exact-base manifests and existing selected-test logs. Start with its `README.md`, then `kod-integration-v1.4/README.md`. |
| 2. Reviewed paper-account v2 | `originals/KOD_trend_paper_v2_reviewed_20261101.zip` | Library version 0; functioning synthetic-only shared-account slice, source/protocol pins, v1 duplicate audit overlay, 30 tests and 2 bounded process races. Archive contains a top-level `KOD_trend_paper_v2_reviewed_20261101/` folder. |
| 3. Reviewed reference-data adapter + failed capture | `reference_profile/coinbase_reference_adapter_20261101/`, sibling `coinbase-independent-audit/`, and `coinbase_reference_capture_20261101T1107/` | Exact eight source pins, pre-capture clearance, final 48-test logs, OFF-by-default source, and actual stopped attempt. Unchanged paper-v2 support files are included alongside for offline tests. |
| 4. Complete historical shared-account proof | `originals/KOD_historical_shared_account_proof_20261101.zip` | Library version 0; frozen daily model, 27-test evidence, all eight derived account journals, reconciled results, source/input pins and independent postrun review. Start with its `START_HERE.md`. |

`ORIGINAL_ARTIFACTS.json` maps every original archive to its Library version and
SHA256, and every reference-profile file to its original source/hash. `SHA256SUMS.txt`
verifies all delivered payloads. Original archives keep their own manifests/logs.

## Important current-repository boundary

Claude reported `/home/user/kod-integrate`, local branch
`integrate/trend-account-20261101`, remote `aa993e8`, and a local merge `d54104f`
containing 14 local research commits. He reported 49 existing account/replay tests
passing on Python 3.13.16, NumPy 2.5.3 and Pandas 3.0.5; trend v1 was untested.
These are **reported baseline facts, not independently verified by this kit**.
Those 49 tests do NOT establish that the delivered v2, adapter or daily replay pass.
Our earlier rehearsal against `aa993e87` does NOT cover the 14 local commits or
prove compatibility with `d54104f`. Verify the actual current full HEAD and diffs.

The older repair patch was built against exact upstream
`7aad4311eb89f713107c96659c2000034bfa9c10`, not against the reported current merge.
Its historical 331 selected tests are bounded evidence, not the full current suite.
Do not blindly apply that patch, push its selected-source synthetic Git history,
reset Claude's branch, overwrite newer research, or treat a clean textual apply
check as semantic acceptance. Preserve all current work and review all affected
files against the actual local merge. Use an isolated LOCAL integration branch.

Read-only inventory in the reported worktree (no fetch or remote operation):
```sh
cd /home/user/kod-integrate
git status --short
git branch --show-current
git rev-parse HEAD
git log -1 --oneline
git log --oneline aa993e8..HEAD
git diff --stat
```
If the reported object/path/branch is missing or differs, stop and report the exact
local state. Inspect repository instructions/AGENTS before any subsequent edits.

## Inspect and test in separate directories — offline only

From the extracted kit root, choose a NEW empty inspection directory. These commands
extract artifacts; they do not apply a repository patch or start a paper cycle.
```sh
set -eu
KIT="$(pwd)"
sha256sum -c SHA256SUMS.txt
mkdir inspection
mkdir inspection/old-repair inspection/paper-v2 inspection/historical
unzip -q originals/KOD-engineering-checkpoint-20261031.zip -d inspection/old-repair
unzip -q originals/KOD_trend_paper_v2_reviewed_20261101.zip -d inspection/paper-v2
unzip -q originals/KOD_historical_shared_account_proof_20261101.zip -d inspection/historical
```
On a system without `sha256sum`, use `shasum -a 256 -c SHA256SUMS.txt`.
Do not extract all archives into one repository root: they deliberately contain
separate profiles, preserved dependencies and historical snapshots.

Paper-v2 offline acceptance (30 tests, plus two separate bounded process races):
```sh
cd "$KIT/inspection/paper-v2/KOD_trend_paper_v2_reviewed_20261101"
python trend-independent-audit/run_combined.py
python -O trend-independent-audit/run_combined.py
python trend-independent-audit/multiprocess.py
```
Reference adapter offline acceptance (48 tests; connections blocked by the runner):
```sh
cd "$KIT/reference_profile"
python coinbase-independent-audit/run_combined.py
python -O coinbase-independent-audit/run_combined.py
```
Historical proof verification — no new economic experiment or input download:
```sh
cd "$KIT/inspection/historical"
python historical-independent-audit/run_combined.py
python -O historical-independent-audit/run_combined.py
python historical-independent-audit/verify_results.py
python -O historical-independent-audit/verify_results.py
```
The old repair archive preserves its exact historical selection/runner/environment
commands in `kod-integration-v1.4/README.md`, plus `integration-tests.log` and
`fresh-extraction-verification/`. Its runner uses a socket-denying guard. Original
Python 3.12/POSIX evidence is not a promise about Claude's Python 3.13 environment.
Record any new environment failures explicitly; do not edit frozen tests to hide them.

After full source/diff review, an OPTIONAL read-only patch applicability diagnostic
from the repository root is:
```sh
git apply --check "$KIT/inspection/old-repair/kod-integration-v1.4/KOD-reviewed-integration-v1.4-from-7aad431.patch"
```
Failure is a local integration blocker, not permission to force/fuzz/reverse/reset.
If integration is later authorized and reconciled, apply EITHER the consolidated
patch OR its documented ordered chain, never both. This kit does not auto-apply it.

## Preserve contracts, records, and limitations

- The same reviewed accounting mechanics underlie different versioned profiles;
  **do not mix their journals, symbols, source receipts, costs or timing rules**.
  Synthetic paper v2 is not the original per-asset backtest. Shared cash and
  normalized targets form a new portfolio contract.
- Coinbase profile is BTC-USD/ETH-USD USD reference simulation, NOT Binance/USDT
  execution validation or eToro executable prices. Costs are named assumptions,
  not verified venue/user terms. Keep the default OFF.
- The one authorized public attempt on November 1 at 11:07 UTC stopped on the first
  metadata GET with `URLError`, before any HTTP response. Exact upstream denial
  versus connectivity cause is unknown. No candles, quote, decision, account or
  fill existed. Evidence is `coinbase_reference_capture_20261101T1107/` (not T1117).
  The immutable pre-capture clearance is historical review evidence, NOT renewed
  permission to retry. Do not invoke `--public-once`, collectors or alternate routes.
- Historical replay is an explicitly delayed daily-opening approximation on reused
  data, not live-quote parity, untouched validation or profitable-edge proof. It
  does not fix blocked current-data access. Its early persistent kills leave years
  in cash; development passive controls were initially capacity-limited to 45.31%
  exposure, not ideal fully invested 50/50 buy-and-hold. Keep the frozen outcomes.
- Preserve every original v1 signal row, including duplicates. Use the supplied
  `v1/DUPLICATE_AUDIT_METADATA.json` audit overlay; do not delete, rewrite, rechain,
  reinterpret signals as fills, or silently replace the original protocol/ledger.
- Hash pins are exact. Any integration code change is a NEW local revision requiring
  explicit diff review, offline regression and its own provenance; old clearance
  cannot be inherited automatically. Use fresh candidate journals, not active v1.
- No push, merge, deployment, live/account credentials, real orders, scheduler edits,
  automatic activation, network retry, or new historical variants are authorized
  by this transfer kit. The user will supply the kit to Claude; no external Claude
  contact or Mac manipulation was performed during packaging.

## Evidence status of this wrapper

Only copying, archive/hash/CRC verification and new handoff documentation were done.
No tests or market studies were rerun for this packaging-only task. Existing logs
remain inside the original artifacts and copied audit directory; superseded development
logs are not final acceptance. This wrapper solves the missing-files handoff, not
current-branch integration or activation. `PACKAGING_VERIFICATION.json` records the
extraction checks without claiming any new product test coverage.
