# Reviewed v1.4 integration candidate (offline, not deployed)

## Result
331 **unique** tests passed, zero failures/errors/skips. Same single explicit real-registry exclusion as baseline. All 267 baseline test IDs remain, with 64 additional unique IDs. This is bounded regression coverage, not a full-suite or profitability claim. Some existing crypto test bodies are intentionally changed by reviewed patches.

Exact upstream base: `7aad4311eb89f713107c96659c2000034bfa9c10`.
Five patches applied cleanly using `git apply --check` followed by `git apply`, in this order:
1. crypto-failed-fetch-v1.2.patch
2. paper-execution-feasibility-v1.patch
3. paper-execution-filter-evidence.patch
4. crypto-quote-validation-v1.3.patch
5. crypto-phase-cas-v1.4.patch

All 18 affected final files byte-match the reviewed `kod-crypto-repair` candidate. No integration code adjustments. All 120 unaffected baseline files retain exact upstream hashes, including shared US execution/account, provenance, and original PAPER_ACCOUNT/PAPER_BOOK protocols. Original CRYPTO_ACCOUNT v1/v1.1 protocols additionally fetched from pinned official head and Git-blob verified; they byte-match owner workspace originals. Baseline and active repair workspace were not edited.

## Single-patch application (preferred)
`KOD-reviewed-integration-v1.4-from-7aad431.patch` is consolidated directly from the verified upstream 7aad431 file bytes to the final reviewed overlay, not from the repair workspace's synthetic local parent. Ordered individual patches remain available under `patches/`; apply **either** consolidated patch **or** ordered chain, not both.

From a clean checkout at `7aad4311eb89f713107c96659c2000034bfa9c10`, with this patch outside the checkout:
```
git rev-parse HEAD
git status --short
git apply --check /path/to/KOD-reviewed-integration-v1.4-from-7aad431.patch
git apply /path/to/KOD-reviewed-integration-v1.4-from-7aad431.patch
```
An isolated copy of the exact-source baseline passed both apply commands; all 18 affected file hashes matched final candidate and all 120 unchanged hashes remained identical. `combined-apply-check.json` records result and patch digest. No commits, pushes, or remote changes. No tests rerun for this packaging-only step. Original crypto v1/v1.1 protocols are unchanged and absent from patch; their verified original Git blob and SHA-256s remain in `original-crypto-protocols.json`.

## Evidence
- `patch-manifest.json`: source base and ordered patch SHA-256s.
- `affected-files.json`: all final affected hashes and exact-candidate comparison.
- `preserved-files.json`: 120 unchanged baseline file hashes.
- `original-crypto-protocols.json`: original v1/v1.1 protocol Git blob/SHA-256s.
- `final-tree-manifest.json`: all 140 archive-ready snapshot files.
- `selection.json`, `union-counts.json`, `result.json`, `integration-tests.log`: unique tested IDs and outcomes.
- `baseline-not-fetched.json`: 72 upstream test files outside bounded selection.
- `baseline-environment-freeze.txt`: environment; declared versions exactly numpy 2.3.5, pandas 2.2.3, beautifulsoup4 4.15.0, lxml 6.1.1, exchange_calendars 4.5.6 on Python 3.12.

## Reproduce on this machine
From `kod-integration-v1.4`:
```
cd snapshot/idx-signals
env -i PATH="$PATH" HOME=/tmp PYTHONPATH="$(pwd)/../../guard:$(pwd)" ../../../kod-test-completeness-7aad431/venv/bin/python ../../run_selected.py
```
To rebuild elsewhere, start from the source-only base subset identified in baseline-verified-files.json, then apply the five provided patches in order with `git apply --check`/`git apply`. Include two unchanged original crypto protocols as pinned above. Create a Python 3.12 venv and install snapshot/idx-signals/requirements.txt constrained by snapshot/idx-signals/constraints-research.txt. Repoint the command to that venv. No dependency installation is required to rerun on this machine.

The runner uses socket audit denial (`guard/sitecustomize.py`) and sanitized environment with no inherited credentials. Tests invoke only local CLI and temporary Git repositories. No market panels/raw holdout data, .env, credentials, networked tests, paid API calls, CI, or remote writes. Original data-dependent registry mismatch test explicitly excluded; absent manual-file empty test does not verify actual committed dataset. No holds-out research or new strategy claims.
