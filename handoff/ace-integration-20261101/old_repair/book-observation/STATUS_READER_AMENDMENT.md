# Offline status-reader amendment — 2026-10-31

The frozen collector and original protocol remain byte-identical. This amendment
adds a read-only status view and regression tests; it does not resume collection.

A stale RUNNING file is only the last saved heartbeat, not proof of a live
collector. `read_status.py` reports RUNNING only when the caller explicitly
confirms process liveness **and** the heartbeat is fresh. Without that evidence it
returns UNKNOWN; an expired heartbeat returns STALE, even if a process exists.
An unexplained mid-set death or transport failure never invents a policy denial.
Explicit runtime network-policy termination evidence maps to BLOCKED, while a
documented ordinary process exit maps to STOPPED. Counts come from preserved
journals, not the stale heartbeat's counters. Incomplete journal lines warn and
cannot promote a run to RUNNING.

The actual run is BLOCKED: 4 attempts, 3 successful books, 1 failed sample,
176 missing scheduled samples. `termination.json` preserves the exact runtime
network-policy error. Original RUNNING status and first STOPPED reconciliation
remain separate history files; current status and summary now say BLOCKED.
No restart, escalation workaround, alternate host, schedule extension or backfill.
The planned two-hour campaign was **not completed**.

Verification: 9 new offline status-reader tests plus 10 original collector tests
passed with socket connections prohibited. Covers mid-set death, unexplained
staleness, missing/future/naive heartbeat, explicit network termination, known
exit, truncated journal and the exact 4/3/1/176 accounting.

Read the actual terminal status:
`python read_status.py run-20261031T1902Z --process-state dead`

Do not treat this file as authorization to re-enable network access. Observation
and simulation are not filter eligibility, actual fills or profitability evidence.
