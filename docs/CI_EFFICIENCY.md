# CI routing and timestamp safety

`checks.yml` continues to trigger for every push and pull request. Never add
workflow-level path filters/concurrency: push workflow records are KOD's independent
GitHub clock evidence. Even `cancel-in-progress: false` concurrency can discard a
pending run, so the integrity job has **no concurrency group**.

## Jobs

- `integrity`: exact-push receipt selftest first (Ubuntu's system Python; KOD is
  stdlib-only), routing regressions, whole-history append-only audit, KOD hash/git/
  TSA/GitHub receipt verification, IDX causal-source audit and stored-run hashes.
  This job is never automatically cancelled and never path-filtered.
- `code-tests`: unchanged KOD and IDX unit suites when selected.
- `workstation`: unchanged tests, dependency advisory audit, four-company replay
  and two-run analyst evaluation when selected.
- `checks`: aggregate gate under the original check name. Integrity must succeed;
  selected suites must succeed; unselected suites must be skipped. Failure or
  cancellation is not converted to success.

Only the two expensive suite jobs cancel superseded work. Groups distinguish
workflow, job, event type and ref: PR and push jobs cannot cancel one another.
A forecast-only run with skipped suites does not cancel an older code test job.

## Conservative selection

All PRs, manual (`workflow_dispatch`) runs and tag pushes run full tests.
Non-default branch pushes run receipts/integrity only; their full suites run when
there is a PR, or via manual dispatch. Default-branch code pushes run full suites.
This removes duplicate push/PR full suites for topic branches without suppressing
any push receipt. A topic branch without a PR is **not unit/integration-tested by
its push run**; request a manual run if full testing is needed before opening a PR.

Default-branch forecast-only skipping is limited to the exact append-only JSONL paths in
`tools/ci_scope.py`. It also requires that the immediate parent push completed
both full suites successfully. A previous run that skipped suites is not a usable
baseline, so repeated forecast pushes can alternate with full runs. New paths,
research, data manifests, fixtures, docs, config, registry cards, deletions,
renames, initial branches, force-pushes and uncertain comparisons run full tests on the default branch.
The diff spans **all commits** in the push, not just the last commit. Even when
suites are skipped, all integrity checks still run and a forbidden log rewrite
fails the aggregate gate.

## Caches and history

Pip download caches are keyed by Python version/platform and the relevant
requirements; research constraints are included. Installs and the live dependency
advisory audit still run: caches are not substitutes for either. Full git history
is retained for all existing consumers; shallow checkout has not been proven safe
for every test/evaluation dependency. No immutable data, strategy or paper policy
is changed.

## Validation and rollout

Run the offline routing regressions from repository root:

```sh
python3 -m unittest discover -s tools/ci_tests -v
```

Before publication, rebase the patch onto the current default branch and recheck
workflow changes in any concurrent PRs. Existing branches do not automatically
inherit the new workflow; old stacked PRs need to incorporate it separately.
Check branch-protection/ruleset requirements before rollout; `checks` retains the
aggregate name and `workstation` is retained, but a skipped workstation result
means the aggregate gate is what enforces the selection policy.

The first forecast-skip baseline must be established by the updated workflow; older
runs without `code-tests` are intentionally not reused. Test actual Actions
behavior only after authorization to spend Actions minutes. Do not use `[skip ci]`,
disable workflows, delete runs or suppress push receipts to publish the change.

Measure billed time after rollout: non-skipped code runs now have one extra full
checkout/install and a small aggregate runner job. Removing topic push suites, cache hits, selected forecast
runs and superseded suite cancellation may save time, but net savings are
not yet measured and should not be claimed. If this tradeoff does not reduce the
real workload's minutes, simplify routing rather than weaken integrity.
