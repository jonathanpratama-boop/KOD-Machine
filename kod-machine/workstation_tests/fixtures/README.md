# Workstation test fixtures

`v1_workspace.sql.gz` is a real KOD-WORKSTATION-v1 database (schema v1), dumped with `sqlite3.Connection.iterdump()`. It was produced by the
unmodified v1 code at commit 0281272 (`python3 -m kod.workstation demo --data-dir <dir>` replaying the four preserved 2024 releases), followed by two
annotation versions on one note and one failed SEC job record, so the upgrade test starts from a populated workspace with notes, sources, events,
annotation history and job health.

Its sixteen evidence objects are byte-identical to files already in `examples/earnings_demo/`; `v1_workspace_objects.json` maps each SHA-256 to that
file, so the fixture does not duplicate source bytes. The upgrade tests rebuild the workspace from these two files, migrate it, and check that every
note, annotation version, source hash and link survives, and that backup and restore work after the migration.

Regenerate only from the v1 commit (never from current code, which writes a newer schema):

    git worktree add --detach /tmp/kod-v1 0281272
    cd /tmp/kod-v1/kod-machine && python3 -m kod.workstation demo --data-dir /tmp/kod-v1-ws
    # then add annotations/job as described above and dump with iterdump()
