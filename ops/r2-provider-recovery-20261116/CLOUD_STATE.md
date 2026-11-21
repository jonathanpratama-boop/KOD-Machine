# KOD cloud state and recovery — 16 November 2026

## Finding

The current R2 cohort is `research-r2-20261105T181200Z`. It was stopped, despite continuing backup publications. The backup repository's older default-branch health file is not the health record for this cohort.

Direct SSH inspection of the existing `kod-timing` server at 07:09 UTC confirmed `kod-research-r2.service` inactive/dead. Its last captured minute was 14 November 20:10:05 UTC. The research engine's last processing watermark was 20:05 UTC that day. Backup and comparison timers were active; their successful invocations did not mean collection was running.

## Cause

`PROVIDER_STOP.json` records HTTP **500**, reason `SHARED_WEIGHT_TELEMETRY_UNAVAILABLE`, at 14 November 20:10:05 UTC. The public Binance book-ticker response lacked the normal used-weight header. The existing transport made missing telemetry a permanent stop regardless of status. The wrapper then returned exit code zero for `PROVIDER_STOPPED`, so `Restart=on-failure` did not retry.

This was not a planned study boundary, disk shortage, OOM, CPU quota or memory quota. The server reported 18 GiB available disk, 585 MiB available RAM out of 961 MiB, no swap, and low load before restart. Current service limits were unlimited CPU and memory; the operating resource check was `MONITOR_ONLY`, with no artificial resource shutdown limits. The retained monitor record showed zero OOM events/kills.

## Applied correction

At **07:16:05 UTC / 14:16 WIB**, the affected collector was restarted using a small runtime overlay after independent tests and a successful provider probe. The same public Binance endpoint returned HTTP 200 with request-weight telemetry and no Retry-After.

Transient 5xx responses now remain recorded failures and receive a bounded retry delay. Actual access/rate denials and Retry-After retain their previous stop behavior. The patch does not manufacture successful readings or bypass provider restrictions.

- All **452 frozen code/configuration files** were verified byte-identical.
- Eight exact original operational files were retained, including the stop record, hashed capture state, heartbeat, engine health and backup acknowledgement.
- Only the operational phase was reset to permit resumption. The state hash was recomputed with the existing writer; study data, bitsets, counters and cursors were retained.
- The stopped-state evidence remains archived on the server. Original outage gaps remain gaps.
- The original collector, engine and backup schedules were reused. No new server, paid model request, real order, position or experiment was created.
- Independent tests: nine methods passed locally and on the server; development checks also passed.

The fixed study dates remain: start **5 November 18:12 UTC**, admissions end **5 December 18:12 UTC**, collection end **10 December 18:12 UTC**, receipt drain **10 December 18:14 UTC**. These correspond to 6 November / 6 December / 11 December in WIB.

## Verification completed

The engine heartbeat resumed at 07:21 UTC. At 07:31:52 UTC, **1,820 new valid closed-minute bars** had been committed, the stream was connected and the engine heartbeat was current. The gap had been explicitly accounted for without adding fabricated readings.

At 07:34:59 UTC, the collector remained active and had **1,591,200 valid readings out of 1,976,130 expected**, across 130 assets: **80.521%** coverage. Valid records had increased again after the first acceptance check. Health was `OK/RUNNING`, with no issues, no provider latch, no OOM events/kills, about 356 MB aggregate memory use and 19.1 GB free disk. All 452 frozen code/configuration files were rechecked unchanged.

The forced existing backup acknowledged [commit 9d8341e](https://github.com/jonathanpratama-boop/KOD-Timing-Backups/commit/9d8341e7037e4d8e2fab91f386a0f65d2473c398), archive sequence 210, including the new 16 November records. Its health and archive head were independently read back through GitHub.

The dashboard was published at [commit 03b5bbd](https://github.com/jonathanpratama-boop/KOD-Timing-Backups/commit/03b5bbdb6bfe7100585e0623b8402525d5ffc05a). Its JSON and embedded HTML were independently read back: result time **07:34:21 UTC**, status `RUNNING`, coverage **80.5197%**, source refresh **07:34:01 UTC**. The small coverage difference from the later live check reflects subsequent received minutes. The original hourly refresh and 15-minute publication freshness intervals remain unchanged; one immediate refresh used the existing supported refresh option.

## Research result, separate from operations

The published result after recovery still contains **one independent event (ONE), four timing arms, and zero prospective matched-control pairs**. The repeated timing arms are not four independent signals. This repair adds operational reliability, not evidence of a profitable strategy.

**Comparison inputs are currently unavailable for all 130 symbols.** The resumed processing watermark is current, but the outage broke the recent observations required for matching. The dashboard now exposes `UNAVAILABLE`, rather than continuing to show the old 14 November `READY` snapshot. Fresh collection does not instantly repair those missing features; readiness must be checked as qualifying data accumulates. No date of recovery or resulting signal count is promised.

The pre-recovery 93.455% minute-coverage figure ended at the old collector clock. It was not current wall-clock coverage through 16 November. Coverage falls as the recovery records the intervening missing slots; it must not be presented as newly lost historical data or repaired to 100% by backfilling.

## Existing publication path and provider availability

The existing hourly `kod-dashboard-refresh.service` reads the KOD and backup Git mirrors under `/var/lib/kod-research-r2-ops/dashboard-sources/`. It selects KOD's current default branch automatically. Its verified 07:34 UTC source refresh used commit `c22b2e1682c0322fc65569e159a257d147a1f86f` and wrote the existing `prospective-check-20261108/dashboard_data.json` and `SOURCE_REFRESH.json`. The existing `publish_dashboard.py` assembles and publishes the R2 dashboard alongside the backup records.

The static original `/opt/kod/current` still points to pinned release `dbb27ea5c6a16c5b37c6f94b938a1509c2a9148e`; it was not repurposed as the new integration checkout.

R2 uses Binance public spot data. Its economic discovery sources are the already-frozen GMX forum, Snapshot and official documents, with manual evidence acceptance still required. These sources are not a new GMX research endorsement. No model/API credential names were configured in the inspected R2/dashboard/backup service environments; only Python runtime flags were present. No `.env` provider credential file was found in the limited inspected deployment roots. This is a scoped availability check, not proof no credentials exist anywhere on the server. A paid model adapter and usage authorization cannot be assumed from this cloud collector.

## Retained evidence

- Local repair package: `cloud-repair/`, including original transport, overlay, wrapper, development and independent tests, recovery procedure, before manifest, recovery receipt, final `AFTER.json` and `PUBLICATION_VERIFICATION.json`.
- Server repair/evidence directory: `/var/lib/kod-research-r2-ops/repairs/provider-recovery-20261116/`.
- Overlay SHA-256: `5e9a890e746ca802c80d4206a4c21ceb8e93b3f300f3ec75ca8776f773aca574`.
- Pre-recovery R2 publication: [commit 78266e8](https://github.com/jonathanpratama-boop/KOD-Timing-Backups/commit/78266e87475202b3f7f3b5d9205e441458cf8364), 16 November 07:04:31 UTC.

No credential values or private keys were copied into this report or the repair package.
