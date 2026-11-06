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
| `experiments.json` | registry entry: state, **collected / scored / needed**, fraction, as_of, next milestone, projected date, verdict, sources, note; plus the owner's view: `program`, `short`, `ceo_line`, `unit`, `outcome`, `lesson` (registry text), `issue`, `verdict_date`, `verdict_basis`, `plumbing` |
| `programs.json` | registry program (a group of live tests asking one question): member count, lead test, status, first issue, the lead's progress and 7-day gains, the lead's verdict date, the next verdict any member is due to reach, start date, freshness |
| `summary.json` | build (exactly one row): headline counts for the owner (tests running, ideas tested and how they came out, next verdict, programs with an issue) |
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

### The owner's view (`issue`, `verdict_date`, programs, summary)

These fields are for the owner, who is not a trader or engineer. Text in them is plain words.

* `issue` (experiments.json): at most 10 plain words when `state` is HALTED, STALLED or UNKNOWN,
  else null. It comes from what the reader already knows, e.g. "2 crypto decisions from Nov 6
  not recorded" (crypto account backlog), "No new insider filings batch for 7 days" (a stopped
  filing feed; days since its last batch), "1 scheduled capture missed" or "Server data
  collector has stopped" (server studies), "No update since Nov 4" (a row aged to UNKNOWN; the
  day of its `as_of`), "Its locked test rules were edited" (frozen rules changed), "Its records
  could not be read" / "A record file it needs is missing" (reader failure). Days are WIB days,
  like history.json.
* `verdict_date` / `verdict_basis`: the date the first pre-set verdict (look) is expected.
  `scheduled` for a fixed-calendar end (`fixed_end`, the pre-move trial's final due date, or a
  server study's `ends_at` as a WIB day); otherwise `estimate` from `projected_date`; null when
  neither exists, the row is CLOSED, or the entry is plumbing.
* `plumbing` (experiments.json): true when the registry entry sets `"plumbing": true` (a
  data-collection check that answers no question, e.g. the timing-capture snapshots), else
  false. A plumbing row's `verdict_date` / `verdict_basis` are null even though it has a fixed
  end or `projected_date`, so it never becomes a program's lead by date or its next verdict.
* `programs.json`: one row per registry program, from its live/server members (closed rows
  never count). `lead` is the registry `lead` if set, else the member with the earliest
  `verdict_date`, else the highest `fraction`, else the first member (registry order breaks
  ties); `scored`, `needed`, `progress` (= the lead's `fraction`), `unit`, `collected`,
  `verdict_date` and `verdict_basis` are the lead's. `next_verdict_date` / `next_verdict_basis`
  / `next_verdict_what` are the earliest member `verdict_date` on or after the build's WIB day,
  that member's basis and its `short` (registry order breaks ties; null when no member has
  one), so they can name a member other than the lead and skip dates already passed.
  `scored_7d` / `collected_7d` are what the lead's history.json counts gained over the last 7
  WIB days (null without history). `status` is `issue` if any member is HALTED, STALLED or
  UNKNOWN (`issue` is then the first such member's text), `waiting` if every member is WAITING,
  else `running`. `started` is the first
  history.json date of any member. `as_of` and `stale_after_hours` come from the member whose
  `as_of + stale_after_hours` is soonest (no `as_of` counts as already stale; CLOSED members are
  skipped), so the page's usual stale check on them is true exactly when any member is stale.
* `summary.json` (one row): `proven_live` (live/server rows with `outcome` "worked"),
  `live_tests`, `programs`, `ideas_tested` (closed rows whose `outcome` is not `not_an_idea`;
  closed rows with no outcome yet still count), `worked`, `didnt_work`, `no_answer`, `checks`
  (closed rows with `not_an_idea`), `next_verdict_date` / `_program` / `_what` / `_basis` (from
  the program with the earliest `next_verdict_date` on or after the build's WIB day: its name
  and its `next_verdict_date` / `_what` / `_basis`, not its lead's `verdict_date`),
  `issues` (programs with status `issue`), `first_record_date` (earliest history.json date),
  `built_at`.

For server collector studies, `scored` is never "bars due": the capacity trials count settled
minutes against the 48 h run, and R2 counts admitted events whose 24 h primary outcome has
matured (0 while no event can be 24 h old; null when HEALTH.json cannot tell). R2's on-time
coverage is reported in the note, not judged against the capacity trial's 99% target.

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
  fixed-calendar study's end date), `start`, `note`, `plumbing` (`true` for a data-collection
  check that answers no question: it keeps its end date but gets no verdict date).
* Owner's view keys (plain words, no jargon; missing ones are null in the output, so the build
  runs without them and prints a `registry:` warning listing what is missing or over its word
  limit):
  * live and server entries: `program` (a program id), `short` (at most 4 words), `ceo_line`
    (at most 14 words: what the test will tell us), `unit` (at most 3 words for the scored
    count, e.g. "calls judged", "trades closed");
  * closed entries: `short` (at most 5 words), `outcome` (`worked`, `didnt_work`, `no_answer`
    or `not_an_idea`), `lesson` (at most 18 words: what we learned).
* Programs are a top-level list: `"programs": [{"id", "name", "question", "order", "lead"}]`.
  `lead` is optional (an experiment id in that program that overrides the automatic lead). An
  unknown `program` id, a `lead` outside its program, a duplicate program id or an `outcome`
  outside the four values stops the build, like a duplicate experiment id does.
* A catalyst entry may set `params.feed_plain` (e.g. "insider filings") for its stopped-feed
  `issue` text; the known families have defaults in `FEED_PLAIN`.
* A job (for `runs.json` / `run_days.json`) is one object in `jobs` with a `JOB_READERS` reader.
* Things that are deliberately not shown go in `reference_only` with a reason, so the gap
  detector stops listing them.

## How freshness works

* `as_of` is the time of the newest **record** a reader used (a `made_at`, `sealed_at`,
  `resolved_at` or `called_at`), never a commit or push time. One exception: closed rows use
  the commit time of their verdict record, which has no stamp of its own. The pooled catalyst
  test uses its newest pooled record; a stopped feeding family turns the row STALLED and its own
  last batch is named first in the note. The crypto account uses the newest record it checked
  (its own writes or the crypto policy rows); the note gives its last write and, when STALLED,
  the stall start (oldest unrecorded decision plus the grace), so `as_of` never reads as the
  start of a stall.
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
  deadline: `ok` on time, `partial` not clean but not missing, `missed` absent after the
  cutoff. What `partial` means depends on the job, and the matching incident in `events.json`
  says it in words: for a **scan** it means **late** (complete, written after its usual time but
  before the decision cutoff; the incident gives the actual time); for a **catalyst batch** it
  means written with a feed coverage gap; for **LLM calls** and the **crypto account** it means
  some but not all of the day's sets or decisions were covered. Days whose deadline has not
  passed yet are left out, because the schema has no "pending" status.
* LLM call files that exist only on another, unmerged branch of the KOD repo are never counted
  (the data ref is the record), but a set they cover is not described as "never called": the
  note, an incident and a `NOT_ON_DASHBOARD` gap name the branch and commit until it is merged.
* Catalyst rows list every US session that never got a batch since the family started and every
  batch with a feed coverage gap, even after a later batch arrives. STALLED still means the
  feed has stopped now (2 or more due sessions since the last batch).
* Server status changes in `events.json` carry the time of the backup that first showed them;
  the detail names the previous backup, so the change happened between the two.
* `projected_date` is a pace estimate from history.json: today + (needed - count) / (pace),
  where the pace is the count gained over the last 14 days, or over the days since the first
  record when that is shorter (never fewer than 7), so a window that starts before anything was
  scored does not dilute the rate. The count is `scored` by default. An entry's optional
  `projection` object can set `"basis": "collected"` with `lag_days` (sealed record to its
  scored outcome), for studies whose scored count lags a steady sealing rate, and
  `earliest_look` + `earliest_look_reason` for a protocol floor such as a minimum number of
  sessions: the later of the two dates is used and the note says which one set it, so
  `projected_date` and `next_milestone` give the same date. It is null when nothing was counted
  in the window. The note gives a rough 80% band. Fixed-calendar studies (`fixed_end`, the
  pre-move trial's protocol end) use that date instead, and the note shows what the pace-based
  estimate would have been.

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
