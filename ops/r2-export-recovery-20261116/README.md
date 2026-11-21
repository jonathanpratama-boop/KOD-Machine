# R2 ledger export recovery, 16 November 2026

The research engine entered a restart loop at its hourly export. Gap recovery had generated one valid replay transaction containing 22,880 detector records and one checkpoint. The frozen exporter required a checkpoint within 5,000 rows, with a 10,000-row fallback; it rejected this 22,881-row transaction. The error then stopped both engine and collector. This was separate from the earlier transient-provider repair.

The operational overlay preserves the original exporter for every ordinary chunk. Only its exact oversized-transaction error invokes a streaming fallback through the next complete replay boundary. The fallback retains every canonical row, publishes an immutable gzip with checksum and durable directory entry, and advances the export cursor only inside the existing database transaction. It does not alter research rules, signals, study dates or historical gaps.

## Validation and deployment

- Nine independently written tests passed: ordinary byte compatibility, oversized transactions, multiple boundaries, incomplete/no boundary, disk failure, cursor rollback, replay after a crash, sequence gaps and unrelated errors.
- A consistent SQLite backup preserved the original 173,817,856-byte database. The real failure was reproduced on a separate copy.
- All 22,881 exported rows matched that copy byte for byte. Its full 212,720-row ledger hashchain was unchanged. The live cursor stayed at 183158 during testing.
- The resulting gzip is 1,430,686 bytes, SHA-256 `afc5af5d4e77dcee7dd2b526a8e3330db56fe685dd9b997520bbcda3fe84cdf9`. Bounded streaming avoided holding its 16,766,899 decoded bytes in memory.
- Deployed at 08:23:36 UTC through `96-export-recovery.conf`. The previous provider correction remains active. All 452 frozen code/configuration files were checked unchanged before deployment.
- At 08:28:55 UTC, the same PID (447512) and restart counter (99) remained stable across multiple checks. Health was `OK/RUNNING`, engine heartbeat was current, the live export cursor had advanced to 210935, and valid minute readings increased by 520 since repair. The original loop's restart count is retained; it was not reset.

Overlay SHA-256: `1cd27e370e1f993e8b86a359d9b900db1fca6645d2ecddb0dad7da647b447dd9`.

The wrapper received two lint comments after deployment; its AST was checked unchanged and no extra restart occurred. Original wrapper bytes and both hashes are retained in `run.initial-deployment.snapshot` and `WRAPPER_COMMENT_ONLY.json`.

## Backup acceptance completed through the existing schedule

Automatic approval review rejected a forced publication to the public backup repository, citing insufficiently specific authorization for the ledger payload. No retry or workaround was attempted. The existing backup schedule was left unchanged.

That previously running schedule independently published at **08:35:30 UTC**, commit `16502a02bd3411eb5a0d6ac0b1feac11434f6209`, archive sequence 211. A read-only GitHub check confirmed its engine export head and bundle manifest include the exact recovered 1,430,686-byte chunk with the SHA-256 above. The published bundle is 3,724,107 bytes. Published health at 08:35:31 was `OK/RUNNING`, the PID remained 447512, the engine heartbeat was current and valid readings had increased to 1,596,140 (80.4482% coverage). `evidence/PUBLICATION_VERIFIED.json` records that final check.

## Files and rollback

The maintained overlay, launcher and independent tests are accompanied by unmodified historical source snapshots and compact before/copy-test/deployment/after receipts. No database or raw capture files are included in this package; the consistent snapshot remains on the user's cloud server.

Server evidence: `/var/lib/kod-research-r2-ops/repairs/export-recovery-20261116/`.

Rollback means stopping only the affected service, removing `96-export-recovery.conf`, reloading the service configuration and starting the prior provider-corrected launcher. Preserve the database, new chunks, original stop evidence and all observations. Restoring the prior exporter without another repair will reproduce the oversized-transaction failure; rollback is not a strategy for clearing that backlog.
