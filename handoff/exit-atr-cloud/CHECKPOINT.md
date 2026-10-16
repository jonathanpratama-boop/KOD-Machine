# EXIT-ATR-v1 cloud run: checkpoint (replaceable view)

Stage: protocol FROZEN at `d1f11c4` (branch `claude/exit-atr-trail-v1`, local to the cloud session, carried in
`bundles/exit-atr-trail-v1.bundle`). Next: the single comparison run.

Restore: `git fetch handoff/exit-atr-cloud/bundles/exit-atr-trail-v1.bundle claude/exit-atr-trail-v1:claude/exit-atr-trail-v1`
(needs `origin/claude/e6-pressure-response` fa142ff). Work folder: `idx-signals/research/EXIT_ATR_v1/cloud/`.
Run: `KOD_CODE_ROOT=<worktree at 21345b1>/idx-signals python3 research/EXIT_ATR_v1/cloud/run_comparison.py`.

Hermes's own files stay uncommitted on the Mac (`hermes/exit-atr-trail-v1`); copies replayed from its chat
archive are in `cloud/hermes_archive/`. No collision: everything here lives under `EXIT_ATR_v1/cloud/`.
