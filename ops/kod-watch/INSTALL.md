# Installing the KOD watch on the timing server

For the operator (Ace). About one hour, plus the owner's few minutes for steps 2 and 7. Claude
built and tested this kit offline and has never run it on the server: follow the expected outputs
and stop at the first difference. [README.md](README.md) explains what the watch reports and why.

## 0. Check the existing safeguard first

On 2026-11-04 the server already ran a second timer, `kod-guard.timer` (every 10 minutes), installed by the
operator during deployment (`KOD-TWO-CASE-REVIEW` package, `CLOUD-START.json` and `CLOUD-END.json`). Its job is not
documented in this repository. Before installing anything, read it:

```
systemctl cat kod-guard.service kod-guard.timer
journalctl -u kod-guard.service --no-pager -n 50
```

If `kod-guard` already alerts the owner's phone on a missed, failed or halted slot, install only what it lacks (for
example the daily summary check and its timer, steps 2 and 8), so the owner does not receive two alerts for one
failure. If it only records or halts locally, install the full kit below. Note the outcome in the operator's
handoff.

## What changes, and what does not

Adds new files only:

| Path | Owner and mode | Content |
|---|---|---|
| `/opt/kod/watch/` | root:root 0755 | `kod_watch.py`, `README.md`, `INSTALL.md` (0644) |
| `/etc/systemd/system/kod-watch-{slot,daily}.{service,timer}` | root:root 0644 | four units |
| `/etc/kod/watch.env` | root:kod 0640 | the two ping URLs |

**Does not modify** `kod-observe.timer`, `kod-observe.service`, `/opt/kod/bin/observe.py`,
`check-source.py`, `kod-status`, the frozen plan `/etc/kod/observation-plan.json`,
`/opt/kod/current`, `/opt/kod/audit`, anything under `/var/lib/kod`, or the 30-slot cohort. The
watch only reads KOD data and has no dependency on `kod-observe.*`. Steps 1 and 9 prove the
scheduler files are unchanged, using the deployment's own checksum list.

Do steps 4 to 8 at least 20 minutes away from a slot time. Slots run at 01, 05, 09, 13, 17 and
21 UTC, which is 08, 12, 16, 20, 00 and 04 WIB.

Work on the server in a root shell over SSH (`ssh root@<server>`). The `scp` commands use the
same login, and step 4 stages the kit in `/root`, which only root can enter. A plain `sudo`
changes nothing in a root shell; it marks the commands that need root. `sudo -u kod` runs a
command as the `kod` user, as the watch itself runs.

## 1. Pre-flight on the server (read-only)

```sh
sudo sha256sum -c /opt/kod/audit/DEPLOYMENT_SHA256SUMS.txt
/usr/bin/python3 --version
sudo -u kod test -r /etc/kod/observation-plan.json && echo plan readable
sudo -u kod test -r /opt/kod/audit/DEPLOYMENT.json && echo deployment readable
sudo -u kod test -r /var/lib/kod/schedule -a -x /var/lib/kod/schedule && echo schedule readable
systemctl show kod-observe.timer -p ActiveState -p NextElapseUSecRealtime
```

Expected: six lines ending in `OK`; Python 3.12 or later (stop if older: the kit was tested on
3.12 and 3.13 only); the three `readable` lines;
`ActiveState=active` with the next slot. Write down the `NextElapseUSecRealtime` value for step 9.
If a file is missing at these paths, stop and report: the watch's paths would not match this
server.

## 2. Create two checks at the monitoring service (owner's account)

The example is healthchecks.io; its free plan is enough for two checks. Create:

| Check name | Schedule type | Period | Grace |
|---|---|---|---|
| `kod-slot` | Simple | 4 hours | 20 minutes |
| `kod-daily` | Simple | 1 day | 2 hours |

Copy each check's ping URL (`https://hc-ping.com/<uuid>`). Treat both as secrets: anyone who
has one can mark that check up or down.

Connect the owner's phone. In Integrations, add a channel the owner's phone receives: email to an
address with phone notifications, or the Telegram integration (follow its prompts). Enable the
channel for both checks and press its test button. **Owner check: the test message arrives on the
phone.**

How alerts behave there: a check alerts when it goes down (a `/fail` ping, or no ping within
period plus grace) and again when it comes back up. A normal success ping sends no notification.
Its body is stored and shown in the check's event log, which is where the daily line is read. A
new check stays silent until its first ping.

## 3. Create `/etc/kod/watch.env`

```sh
sudo install -m 0640 -o root -g kod /dev/null /etc/kod/watch.env
sudoedit /etc/kod/watch.env
```

Two lines, no quotes, no spaces:

```
KOD_WATCH_SLOT_URL=https://hc-ping.com/<kod-slot uuid>
KOD_WATCH_DAILY_URL=https://hc-ping.com/<kod-daily uuid>
```

`sudo ls -l /etc/kod/watch.env` must show `-rw-r----- 1 root kod`. Never commit this file, paste
it into a chat or ticket, or copy it off the server.

## 4. Copy the kit and install it

On the Mac, from a checkout of the reviewed commit:

```sh
shasum -a 256 ops/kod-watch/kod_watch.py ops/kod-watch/systemd/*
ssh root@<server> 'test ! -e /root/kod-watch-kit' && echo "staging path is free"
```

Copy only after it prints `staging path is free`. If it prints nothing, an earlier staging copy
is still there: `scp -r` would put the new kit inside it as `/root/kod-watch-kit/kod-watch`, and
the digests below would read the old files. Remove it on the server with
`rm -r /root/kod-watch-kit` and run the line again. Then copy:

```sh
scp -r ops/kod-watch root@<server>:/root/kod-watch-kit
```

On the server:

```sh
cd /root/kod-watch-kit
sha256sum kod_watch.py systemd/*
python3 -I -B -m unittest discover -s /root/kod-watch-kit
```

The five digests must equal the Mac's, and the test run must end with the line `OK`. Anything
else (`FAILED`, an error, or no tests run) means stop and report. The tests write only to
temporary directories and send nothing. Then install:

```sh
sudo install -d -m 0755 -o root -g root /opt/kod/watch
sudo install -m 0644 -o root -g root kod_watch.py README.md INSTALL.md /opt/kod/watch/
sudo install -m 0644 -o root -g root systemd/kod-watch-slot.service systemd/kod-watch-slot.timer \
  systemd/kod-watch-daily.service systemd/kod-watch-daily.timer /etc/systemd/system/
sudo systemd-analyze verify /etc/systemd/system/kod-watch-slot.service \
  /etc/systemd/system/kod-watch-slot.timer /etc/systemd/system/kod-watch-daily.service \
  /etc/systemd/system/kod-watch-daily.timer
sudo systemctl daemon-reload
```

`systemd-analyze verify` must print nothing. systemd ignores a misspelt hardening line with
only a warning, so any output means stop and report. Then remove the staging copy. Everything
the watch runs is now in `/opt/kod/watch` and `/etc/systemd/system`:

```sh
cd /root && rm -r /root/kod-watch-kit
```

## 5. Dry run (sends nothing)

```sh
sudo -u kod sh -c 'set -a; . /etc/kod/watch.env; exec /usr/bin/python3 -I -B /opt/kod/watch/kod_watch.py slot --dry-run'
sudo -u kod sh -c 'set -a; . /etc/kod/watch.env; exec /usr/bin/python3 -I -B /opt/kod/watch/kod_watch.py daily --dry-run'
```

Each prints one JSON line with `"dry_run": true`, `"delivered": null` and a `target` such as
`https://hc-ping.com/...`. The `body` is the message the owner would get. Compare it with
`sudo /opt/kod/bin/kod-status`: the same slots must be `CAPTURED`. If the body starts with
`KOD FAIL`, read the reason. It is a real finding: report it before going on.

## 6. One real ping on each check

```sh
sudo systemctl start kod-watch-slot.service
sudo systemctl start kod-watch-daily.service
journalctl -u kod-watch-slot.service -u kod-watch-daily.service -n 10 --no-pager
```

Each JSON line must show `"delivered": true`. In the dashboard both checks turn up (green), and
the event log shows the bodies. A manual start does not change either timer.

## 7. Optional alert drill on the owner's phone

This makes `kod-slot` go down and then up again. The URL appears briefly in `curl`'s process
arguments on the server; skip the drill if that is not acceptable.

```sh
sudo -u kod sh -c 'set -a; . /etc/kod/watch.env; exec curl -fsS -m 10 --retry 3 --data-raw "KOD DRILL: manual alert test, not a cohort failure" "$KOD_WATCH_SLOT_URL/fail"'
sudo systemctl start kod-watch-slot.service
```

**Owner check: a "down" alert and then an "up" alert for `kod-slot` arrive on the phone.**

## 8. Enable the timers

```sh
sudo systemctl enable --now kod-watch-slot.timer kod-watch-daily.timer
systemctl list-timers 'kod-*' --no-pager
```

Expected: `kod-observe.timer` with the same next slot as in step 1 (or four hours later if a slot
ran in between), `kod-watch-slot.timer` at 12 minutes past the next slot hour, and
`kod-watch-daily.timer` at the next 01:30 UTC. If systemd also runs a watch at once, that is one
extra ping and harmless.

## 9. Verify that nothing else changed

```sh
sudo sha256sum -c /opt/kod/audit/DEPLOYMENT_SHA256SUMS.txt
systemctl show kod-observe.timer -p ActiveState -p NextElapseUSecRealtime
```

Expected: the same six `OK` lines and the same timer values as in step 1 (unless a slot ran in
between, in which case the next elapse moved on by four hours).

After the next slot, at 12 minutes past the hour, check the first real judgement. This is also
the first run against a real `end.json`, since the tests use synthetic receipts:

```sh
journalctl -u kod-watch-slot.service --since -1h --no-pager
```

The body must name that slot with the status that `kod-status` shows for it.

## Reading the alerts

- **`kod-slot` down with a body.** The body names the slot and the reason, for example
  `KOD FAIL: slot 7 2026-11-05T13:00Z MISSED; ...`.
- **`kod-slot` down without a new ping.** The server, its network or the watch did not run. Check
  the server first.
- **`kod-slot` up after a down.** The next slot was captured. The earlier failure stays listed in
  the body.
- **`HALTED.json present`.** `observe.py` stopped itself after a failed slot. Every later slot fails
  until the operator review that `observe.py` requires. The watch does not clear it.
- **After an outage.** Both the scheduler and the watch catch up at boot. If the watch runs first,
  it can report `NOT_STARTED` or `UNFINISHED` for a slot that `observe.py` then records as `MISSED`.
  Both are failures; the next run shows the recorded status.

## After the cohort

Slot 30 is at 2026-11-09 09:00 UTC (16:00 WIB). At 09:12 UTC `kod-slot` receives
`KOD OK COHORT COMPLETE: ...` (or `KOD FAIL COHORT COMPLETE: ...`). After that message:

```sh
sudo systemctl disable --now kod-watch-slot.timer
```

Then press Pause on `kod-slot`. If it is not paused, it will go down about 4 h 20 min later,
because the watch deliberately sends nothing more. The daily line goes on with `cohort complete`
until the off-server copy below has been verified. Then:

```sh
sudo systemctl disable --now kod-watch-daily.timer
```

Finally pause or delete `kod-daily`.

## Rollback (at any time)

```sh
sudo systemctl disable --now kod-watch-slot.timer kod-watch-daily.timer
sudo rm /etc/systemd/system/kod-watch-slot.service /etc/systemd/system/kod-watch-slot.timer \
  /etc/systemd/system/kod-watch-daily.service /etc/systemd/system/kod-watch-daily.timer
sudo systemctl daemon-reload
sudo rm /opt/kod/watch/kod_watch.py /opt/kod/watch/README.md /opt/kod/watch/INSTALL.md
sudo rmdir /opt/kod/watch
sudo rm /etc/kod/watch.env
```

If step 4 stopped before its last command, also remove the staging copy with
`rm -r /root/kod-watch-kit`. Pause or delete both checks, then run step 9 again. Rollback
touches nothing that the scheduler uses. To stop alerts without uninstalling, disable the timers
and pause the checks.

## Off-server copy of the cohort

The cohort's backups (`/var/lib/kod/backups/cohort-through-NN.zip`) are on the same server. Two
independent options are below; neither touches the cohort.

**DigitalOcean droplet backups.** In the DigitalOcean control panel, open the droplet, go to
its Backups page and enable backups. This is a paid add-on: check the price and the backup
schedule shown on that page. `DEPLOYMENT.json` records `"no_new_paid_services": true`, so the
owner must approve the cost before it is enabled. Enable it at least 20 minutes away from a slot
time. It protects against loss of the droplet's disk. It stays inside the same DigitalOcean
account, so it does not protect against losing that account. The backup image also contains
`/etc/kod/watch.env`.

**Copy to the owner's Mac with scp after the cohort.** The copy only reads the server, so it can
also be repeated mid-cohort, away from slot times. Each copy goes into a new folder named after
the UTC minute it starts, so a repeat never merges into an earlier copy or nests inside it. On
the Mac, in one Terminal window:

```sh
dest="$HOME/KOD-offserver/$(date -u +%Y%m%dT%H%MZ)"
mkdir -p "$HOME/KOD-offserver" && mkdir "$dest" && echo "new copy folder: $dest"
```

Go on only after it prints `new copy folder: ...`. `mkdir` refuses a folder that already
exists, which happens only for a second copy started in the same UTC minute: wait a minute and
run both lines again. Then, in the same window:

```sh
scp -p 'root@<server>:/var/lib/kod/backups/*.zip' "$dest/"
scp -rp root@<server>:/var/lib/kod/schedule "$dest/"
scp -p root@<server>:/etc/kod/observation-plan.json root@<server>:/opt/kod/audit/DEPLOYMENT.json \
  "$dest/"
```

The archives hold the runtime root `/var/lib/kod/timing-forward`. `observe.py`'s receipts live
outside it, in `/var/lib/kod/schedule`, so they need the second command. Do not copy
`/etc/kod/watch.env`. These commands assume root login over SSH; with another user, do not
loosen KOD's file permissions to make scp work.

Verify the copy. Compare `sudo sha256sum /var/lib/kod/backups/*.zip` on the server with
`shasum -a 256 "$dest"/*.zip` on the Mac, in the same window; each digest must match.
Optionally, prove that the newest archive restores. Use a checkout of commit `dbb27ea5c` with the
runtime requirements installed, and follow `docs/RUNTIME.md` ("Backup and recovery"): `restore`
into a new directory, then `verify`. **Owner check: a verified copy exists somewhere other than
the server.**
