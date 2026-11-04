# KOD watch: dead-man's switch and daily line for the timing cohort

Fix 6 of [`handoff/KOD_FIX_PLAN.md`](../../handoff/KOD_FIX_PLAN.md). Paper only. The kit watches the
30-slot observation cohort that `kod-observe.timer` runs on the timing server (first slot
2026-11-04T13:00Z, last 2026-11-09T09:00Z). It tells the owner when a slot was not captured or
when the server stops reporting. A human operator installs it with [INSTALL.md](INSTALL.md). Its
author could not reach the server, so it was built and tested offline only.

## What it is

`kod_watch.py` is one Python file that uses only the standard library. Each run reads three things,
judges the cohort and sends one HTTPS POST (a "ping") to a monitoring check:

| Input | Path on the server | Used for |
|---|---|---|
| Frozen plan | `/etc/kod/observation-plan.json` | slot times, `late_after_seconds`, file digest |
| Receipts written by `observe.py` | `/var/lib/kod/schedule/slot-NN/{begin,end}.json`, `HALTED.json` | slot status |
| Deployment record | `/opt/kod/audit/DEPLOYMENT.json` | `plan_sha256` that pins the plan |

| Mode | Timer (UTC) | Check | Pings `/fail` when | Body |
|---|---|---|---|---|
| `slot` | 01,05,09,13,17,21:12 | slot check (period 4 h, grace 20 min) | the latest judged slot failed, or a standing problem holds | short, one line |
| `daily` | 01:30 (08:30 WIB) | daily check (period 1 day, grace 2 h) | a slot judged in the last 24 h failed, or a standing problem holds | the daily line |

The monitoring service raises the alarm when a check receives `/fail`, and also when no ping
arrives within period plus grace (server off, network down, watch broken). That second case is
the dead-man's switch.

**Health rule.** A slot is judged once `scheduled_at + late_after_seconds + grace` has passed
(600 s + 60 s, so 11 minutes after the slot). It is healthy only if its `end.json` is a receipt
for that slot, written under this plan, with status `CAPTURED`. Everything else fails with a
reason:

| Code | Meaning |
|---|---|
| `PARTIAL`, `BLOCKED`, `MISSED`, `INTERRUPTED`, `FAILED` | `end.json` status written by `observe.py` (its `reason` or `error` is quoted) |
| `NOT_STARTED` | neither `begin.json` nor `end.json` |
| `UNFINISHED` | `begin.json` without `end.json` (interrupted or still running) |
| `INVALID_RECEIPT` | `end.json` unreadable, not JSON, for another slot, under another plan digest, or with an unknown status |

Standing problems fail every run: `HALTED.json` present, plan bytes that differ from the
deployment record, an unreadable or invalid plan or deployment record, or an unexpected error in
the watch itself (reported as `watcher error: ...`, with the traceback in the journal).

**Messages** (exact formats; times are UTC with WIB in brackets):

```
KOD OK: slot 6 2026-11-05T09:00Z CAPTURED; slots 1-6 CAPTURED, 0 failed; next 2026-11-05T13:00Z (20:00 WIB)
KOD FAIL: slot 6 2026-11-05T09:00Z MISSED; slots 1-5 CAPTURED, 1 failed (6 MISSED); next 2026-11-05T13:00Z (20:00 WIB)
KOD FAIL: HALTED.json present (slot 6 FAILED: timing verification did not pass); slot 7 2026-11-05T13:00Z NOT_STARTED: ...
KOD OK COHORT COMPLETE: slot 30 2026-11-09T09:00Z CAPTURED; slots 1-30 CAPTURED, 0 failed; slot watch finished: disable kod-watch-slot.timer and pause the slot check
KOD 2026-11-05: slots 1-4 CAPTURED, 0 failed, next 2026-11-05T05:00Z (12:00 WIB)
```

The WIB date is shown only when it differs from the UTC date, as in `(2026-11-06 00:00 WIB)`.
Every run prints one JSON line to the journal: `mode`, `as_of`, `result` (`OK`, `FAIL` or
`QUIET`), `body`, `target` (the URL with its secret path replaced by `...`), `dry_run`,
`delivered`, `attempts` and `errors`. Exit status: 0 when the ping was delivered, nothing was
due to be sent, or `--dry-run` was used; 1 when the ping was not delivered after 4 attempts; 2
when the URL configuration is unusable (nothing is sent). `--dry-run` still reads and checks the
ping URL, so a dry run also proves that `/etc/kod/watch.env` is usable.

## Design decisions

1. **Grace 60 s, not 300 s.** The slot timer fires 720 s after each slot (the 12 minutes in the
   fix plan). The deployed `late_after_seconds` is 600, so a 300 s grace would leave the newest
   slot unjudged until the run four hours later. A test ties the timer offset to
   `late_after_seconds + GRACE_SECONDS`. `kod-observe.service` has a 600 s start timeout, so by
   the 12-minute mark an on-time run has either written `end.json` or been stopped; a stopped
   run shows as `UNFINISHED`. A run whose start was delayed by more than a minute can still be
   working at that point. It is also reported as `UNFINISHED`, and the next run shows its
   recorded status.
2. **The latest slot, not a cumulative verdict.** A monitoring service alerts on state changes.
   If every run failed after the first failed slot, the check would stay down for the rest of the
   cohort and no later problem, including loss of the server, would raise a new alert. So slot mode
   judges the slot it follows and repeats earlier failures in the body
   (`slots 1-4,6 CAPTURED, 1 failed (5 MISSED)`). The daily line uses the same idea over 24 hours.
3. **Two plan digests.** `DEPLOYMENT.json` records sha256 of the plan file bytes (`bffe9199...`).
   `observe.py` writes sha256 of `json.dumps(plan, sort_keys=True)` into every receipt
   (`693394f0...`, the value `kod-status` printed at handoff). The watch checks both: the file
   against the deployment record, and each receipt against the plan it was judged under. The
   fixtures pin both values.
4. **"COHORT COMPLETE" once, with no state file.** A slot run within 4 hours after slot 30's
   deadline (normally 09:12 UTC on 2026-11-09) sends `COHORT COMPLETE`. Later slot runs send
   nothing and log `QUIET`. A manual start inside that 4-hour window sends it again. Keeping no
   state means the units need no writable path.
5. **Ping hygiene.** URLs come only from the environment (`/etc/kod/watch.env` through
   `EnvironmentFile=`). They must be plain `https://host/path` URLs in visible ASCII, without
   credentials, query or fragment (no `?` or `#` at all), with a valid port if any, and must not
   already end in `/fail`. A URL that breaks a rule stops the run before anything is sent; an
   error the URL stack raises while sending is recorded like a network error. The watch follows the healthchecks.io
   convention: success is the URL, failure is the URL plus `/fail`, and the body is stored with the
   ping. Each attempt has a 10 s timeout; there are up to three retries after 2, 4 and 8 s.
   Certificates are verified and redirects are refused, so a ping cannot be downgraded to HTTP.

## What it is not

- **Not a scheduler or a repair tool.** It never starts, retries, repairs or backfills an
  observation and never clears `HALTED.json`. Its units have no ordering or dependency on
  `kod-observe.*`, so a watch failure cannot stop, delay or restart the scheduler.
- **Not a writer.** It only reads. `ProtectSystem=strict` and `ReadOnlyPaths=` enforce this at
  run time, and the tests compare a full snapshot of a fake server tree before and after every mode.
- **Not an evidence check.** `CAPTURED` means `observe.py` recorded `CAPTURED` after its own
  integrity step. The watch does not re-verify capture evidence, clocks, quotes or backups;
  `kod-status` and `timing-status` do that. A delivered ping proves only that the monitoring
  service accepted it.
- **Not part of `TIMING_CAPTURE_v1`.** It changes nothing in the protocol, the plan, the cohort's
  membership or its denominator. It reads no market data and produces no signal, forecast or order.
- **Not an off-server backup.** INSTALL.md has a separate section for that.
- **Not a daily phone message on its own.** healthchecks.io notifies on state changes (down and
  up), not on every ping. The daily line is read in the daily check's event log; the phone hears
  about failures, missing pings and recoveries.
- **Not tested on the server.** The receipts in the tests are synthetic, in `observe.py`'s shape,
  because no slot had run when this kit was written. INSTALL.md step 9 checks the first real slot.

## Files

| Path | Purpose |
|---|---|
| `kod_watch.py` | the watch (installed as `/opt/kod/watch/kod_watch.py`) |
| `systemd/kod-watch-slot.{service,timer}` | slot mode, 12 minutes after each slot |
| `systemd/kod-watch-daily.{service,timer}` | daily line at 01:30 UTC |
| `test_kod_watch.py` | standard-library tests on fake server trees and on the unit files |
| `fixtures/deployed-2026-11-04/` | byte-exact copies of the deployed `observation-plan.json` (sha256 `bffe9199...`) and `DEPLOYMENT.json` from the 2026-11-04 server audit bundle |
| `INSTALL.md` | operator steps, verification, rollback, off-server copy |

## Tests

From the repository root (no network; every ping goes to an injected fake):

```sh
python3 -m unittest discover -s ops/kod-watch -v
```

The suite passes on CPython 3.12.3 and 3.13.17. `systemd-analyze verify` (systemd 255) accepts
the four unit files without warnings.
