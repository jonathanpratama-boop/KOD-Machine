# Actual frozen run

Executed once, after exact-source independent clearance and explicit authorization:

```sh
python -u historical_shared_account_replay_20261101/replay.py \
  --run-reviewed-historical \
  --clearance historical-independent-audit/REVIEW_CLEARANCE.json \
  --inputs fresh_eyes_reproduction_20261101 \
  --output-dir historical_shared_account_results_20261101T1134
```

Started2026-11-01T11:34:27.503333Z; finished11:38:47.897493Z; process exit0.
All220 local input hashes passed before the first case. Four fixed policies in
two independent partitions, no variants or parameter changes. The console transcript
is CANONICAL_RUN_CONSOLE.txt. Do not run this command merely to inspect proof; use
the included read-only verify_results.py on the completed journals instead.
