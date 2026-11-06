# KOD status dashboard data

`build_status.py` turns KOD's own records into the small JSON files behind the owner's status page.
It never trades or writes to a ledger, and it only reads through `git show` / `git ls-tree` /
`git log` on fixed refs, so neither repo's working tree matters.

```
python3 tools/status/build_status.py \
  --kod /home/user/KOD-Machine --kod-ref origin/claude/idx-signals-test-repo-ds0jw7 \
  --backups /home/user/kod-timing-backups --out /path/to/status-out
# optional: --now 2026-11-06T05:30:00Z (reproducible build)  --registry other.json
```

It needs only Python 3.12+ and git, and finishes in about 3 seconds.

## What it writes

| file | one row per |
|---|---|
| `experiments.json` | registry entry: state, **collected / scored / needed**, fraction, as_of, next milestone, projected date, verdict, sources, note |
| `history.json` | experiment per WIB day: cumulative collected and scored |
| `runs.json` | job: last success, what it last wrote, expected period, grace |
| `run_days.json` | job per date for the last 30 days: `ok`, `missed`, `partial`, `not_expected` |
| `server.json` / `server_history.json` | server study (kod-timing-backups branches) / heartbeat |
| `events.json` | incident, decision or milestone from the last 31 days; every row cites a record |
| `gaps.json` | thing that exists but is not shown (`NOT_ON_DASHBOARD`), or a source that vanished or failed (`SOURCE_MISSING`, `READ_ERROR`) |
| `build.json` | build: time, commits read, builder hash, registry size |

The three counts always stay separate. **Collected** is the number of records made. **Scored**
is the number of outcomes that can be evaluated under the frozen protocol. **Needed** is what
the protocol needs before its first look. `fraction` is always scored / needed, never
collected / needed. No win rate, return or P&L is written before a study reaches its look.

## Adding an experiment: one registry entry

Add one object to `experiments` in `tools/status/experiments.json`:

```json
{
  "id": "MY_STUDY_v1", "name": "Short name", "group": "live",
  "plain": "One sentence: what it asks, in plain words?",
  "reader": "spec_register", "params": {"register": "idx-signals/paper/speculations.jsonl", "market": "US"},
  "collected_label": "sets sealed", "scored_label": "paired 5-day results",
  "needed": 60, "needed_label": "paired sets for the first look",
  "stale_after_hours": 78, "next_milestone": "...", "next_date": "2026-11-20",
  "sources": ["KOD:idx-signals/paper/speculations.jsonl"],
  "protocol": {"path": "idx-signals/research/MY_STUDY_v1/PROTOCOL.md", "sha256": "<sha256 of the file>"}
}
```

* `reader` is a function name in `READERS` in `build_status.py`. Reuse one where it fits
  (`spec_register`, `catalyst`, `closed_record`, `server_study`, ...). If you write a new one,
  it takes `(ctx, params)` and returns `reading(collected=..., scored=..., as_of=...,
  collected_times=[...], scored_times=[...])`. History and projections come from those times.
* A closed study uses `"group": "closed"`, `"reader": "closed_record"`, `closed_on`, `verdict`,
  `record`, and `params.must_contain` (text the verdict record must still contain) plus
  optional `params.json` checks (`{path, key, equals}`). If the record changes, the row turns
  UNKNOWN and a gap is written.
* Optional keys: `optional_sources` (may be absent, e.g. a file written only at a look),
  `covers` (other ids this entry accounts for, e.g. catalog ids), `fixed_end` (a
  fixed-calendar study's end date), `start`, `note`.
* A job (for `runs.json` / `run_days.json`) is one object in `jobs` with a `JOB_READERS` reader.
* Things that are deliberately not shown go in `reference_only` with a reason, so the gap
  detector stops listing them.

## How freshness works

* `as_of` is the time of the newest **record** a reader used (a `made_at`, `sealed_at`,
  `resolved_at` or `called_at`), never a commit or push time. Two exceptions: closed rows use
  the commit time of their verdict record, which has no stamp of its own, and the pooled
  catalyst test uses its stalest feeding family.
* When the build runs, a live row whose `as_of` is older than `stale_after_hours` is written as
  **UNKNOWN**, never RUNNING. STALLED (positive evidence of a stop, e.g. no catalyst batch for 2
  or more due sessions) and HALTED are kept, because they already say something is wrong.
  Closed rows are never aged.
* The page should repeat that check against the viewer's clock, using `as_of` and
  `stale_after_hours`, and should flag the whole page if `build.json.built_at` is old. A file
  built yesterday must not keep saying "fresh" today.
* Limits are fixed hours (78 h covers a normal Friday-to-Monday US gap). Long holiday weekends
  (around 2026-12-25 and 2027-01-01) will read UNKNOWN for about a day. The NYSE holidays in
  `calendars` are used for `run_days`. IDX holidays are not modelled yet, so an IDX holiday
  will show as `missed` until it is added to `calendars.IDX.holidays`.
* `run_days` statuses come from the records each job writes, judged against the job's own
  deadline: `ok` on time, `partial` late but before the decision cutoff (or written with a
  feed coverage gap), `missed` absent after the cutoff. Days whose deadline has not passed yet
  are left out, because the schema has no "pending" status.
* `projected_date` = today + (needed - scored) / (scored in the last 14 days / 14), using
  history.json. It is null when nothing was scored in the last 14 days. The note gives a rough
  80% band. Fixed-calendar studies (`fixed_end`, the pre-move trial's protocol end) use that
  date instead, and the note shows what the rate-based estimate would have been.

## Size limits and trimming

Every file is kept under 190 KB:

* history keeps the last 120 WIB days per experiment, and closed studies get one row on
  `closed_on`;
* server_history keeps 30 days, every heartbeat from the last 48 h and one per study per 6 h
  before that, plus every status change;
* events keep 31 days, and consecutive bad run days are merged into one incident;
* as a last resort, the oldest rows are dropped and a warning is printed.

## Checks

```
ruff check --isolated --select E4,E7,E9,F,E501 --line-length 100 tools/status/build_status.py
```
