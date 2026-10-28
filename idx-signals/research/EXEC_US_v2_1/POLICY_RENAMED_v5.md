# PR #3's paper policy is PAPER-POLICY-v5

PR #3 drafted its paper policy (the 5% stop rule in every market, EXEC-US-v1 for US plans and
outcomes, APPROVAL-v2) under the id `PAPER-POLICY-v4`. Before PR #3 merged, PR #6 merged a
different policy under the same id: v3 plus the E3 rule for IDX (`research/E3/protocol.json`
names it). The base branch's id stands, and PR #3's policy is `PAPER-POLICY-v5` from the merge of
the base branch into `claude/us-pipeline-v1`.

Where the frozen files of this PR (`research/US_PIPELINE_v1/`, `research/EXEC_US_v2/`,
`research/EXEC_US_v2_1/`, `research/US_BREAKOUT_v1/SPEC_DRAFT.md`) say `PAPER-POLICY-v4`, they
mean this policy, now v5. No decision was ever recorded under PR #3's draft id: the scheduled
scans ran on the base branch.

v5 differs from the draft in one addition, `e3_rule`: v5 does not use the E3 rule, and while a
validated E3 pair exists the IDX scan fails rather than deciding, because v5 does not define how
a plan without a chase limit meets the 5% stop rule. No E3 pair is validated (E3 discovery
admitted none). `tests/test_policy_versions.py` pins the v3 and v4 hashes the ledger and PR #6
recorded.
