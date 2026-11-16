# KOD R2 transient-provider recovery

Applied 16 November 2026 at 07:16:05 UTC to the existing paper-research collector.

## Defect and correction

At 20:10:05 UTC on 14 November, Binance's public book-ticker endpoint returned HTTP 500 without its normal request-weight header. The existing transport treated the missing header as a permanent provider restriction. It wrote a persistent stop file; the wrapper exited successfully, so automatic restart on failure did not apply. This was before the fixed collection deadline and was unrelated to CPU, memory or storage limits.

`provider_recovery.py` is an operational overlay. It retains the original failed response for normal error recording and applies a bounded retry delay to transient 5xx responses. It preserves existing behavior for access/rate denials, Retry-After, missing telemetry on other responses and the existing reported-weight ceiling. It respects the caller's timeout and checks an operator pause before sending a delayed request.

`run.py` loads the previous operational wrapper and applies the overlay. The original 452 frozen code/configuration files remained byte-identical. No study start, admission end, collection end, source roster, outcome or data-gap flag changed. No real order or model request was made.

## Evidence and validation

- `source/runtime.py` is the pre-repair transport implementation copied from the server.
- `smoke.py` contains development checks.
- `test_provider_recovery_independent.py` contains independently written behavioral tests. Nine methods passed locally and again on the deployment host.
- `recover.py` checks the exact stopped state, preserved source hashes and current provider availability before recovery. It records before/after state hashes and refuses to rerun after a recovery receipt exists.
- Overlay SHA-256: `5e9a890e746ca802c80d4206a4c21ceb8e93b3f300f3ec75ca8776f773aca574`.
- Server evidence directory: `/var/lib/kod-research-r2-ops/repairs/provider-recovery-20261116/`.
- Server service override: `/etc/systemd/system/kod-research-r2.service.d/95-provider-recovery.conf`.

## Rollback and operation

The existing collector and backup schedules remain in place. The only new service override selects the corrected wrapper. If rollback is necessary, stop only `kod-research-r2.service`, remove `95-provider-recovery.conf`, reload the service configuration and start the prior wrapper. Preserve all post-repair observations. Do not restore the old capture state over new data, reset the study clock, erase the outage, or clear a new provider restriction without reviewing its actual reason.

Starting the service is not evidence of healthy collection. Acceptance requires new received minute bars, an advancing engine heartbeat and off-server publication. Those observations are recorded in the accompanying cloud-state report.
