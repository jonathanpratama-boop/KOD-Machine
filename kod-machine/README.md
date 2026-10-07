# KOD Machine

Forensic lab for market repricing. Research only. No entry permission.

KOD sits beside ASTRA (`Moonshot-Scanner`, branch `claude/loving-gauss-1o1ldm`).
It does not edit COMPRESSION, IGNITION, or EQ_GAP, and it does not join the
authoritative v1 pilot cohort.

## What it freezes

Every case stores three information sets before any outcome row exists:

- T-30D
- T-72H
- T-24H

The card is hashed. Outcomes are a second append-only row. Updating or deleting
a case, information set, detector evaluation, critic note, outcome, or doctrine
version is aborted by SQLite triggers.

## What it refuses

- ENTRY_ELIGIBLE as a disposition
- INVESTIGATE without a critic loss path, missing evidence, and invalidation
- Counting retrospective or simulated cases toward calibration
- Promoting a detector before 30 closed prospective cases
- Rewriting a call after the outcome
- A PROSPECTIVE open whose `decision_cutoff` is more than 1 hour from the actual open
  time, is not before `outcome_window.start`, or arrives after the window started. Every
  information-set cutoff must be at or before the decision cutoff. Timestamps need a timezone.
- A PROSPECTIVE open with no `outcome_window`, or with no git anchor configured
- A close without the `card_sha` printed at open, with a different hash, or before
  `outcome_window.end` (any call type that carries a window)
- A scan log entry outside the same timing rules, and a scan close without its `scan_sha`

## Hash anchoring and `verify`

Every open appends `{kind, record_id, sha256, opened_at, decision_cutoff, window}` to
`registry/opens.jsonl`, writes the frozen card to `registry/cards/<case_id>.json`, and
commits exactly those two paths (`kod anchor case <id> <sha>`). If the commit fails, the
open is rolled back. Scans do the same in `registry/scans.jsonl` and `registry/scans/`.

A local commit date comes from the local clock and can be set by anyone with the repo.
The timestamp a third party can rely on is the push, so use `--push` on `open` and `scan`,
or push right after. `verify` reports anchors that are still local only.

`verify` trusts no stored hash. It rebuilds every card hash from the case, information
set and critic rows, every scan hash from the entry rows, and checks each against the
stored hash, the outcome's copy, the anchors row and the line in the anchor commit. It
also checks that the anchor commit is in HEAD's history, that the registry line is still
in HEAD, that the anchor commit predates the outcome window, that prospective opens and
closes kept their timing, and that the schema, migrations and doctrine were not edited
after adoption. Exit code 1 on any failure.

## Scan log: every name, flagged or not

`scan` logs every name a scanner evaluated, flagged or not, with the scanner's own flag and
KOD's detector statuses. A case opened from a scan carries `scan_entry_id`, so the report
counts flagged names that were opened and flagged names that were not. Scan outcomes are
appended for the whole scan after its window; names still unclosed after the window are
counted as overdue, so a selective close shows.

The report scores each detector, and each scanner's flag, on both sides: hit rate when it
fired, hit rate when it was evaluated and did not fire, the base rate over both, and lift =
signal hit rate / base rate. A hit is the pre-registered label: `hit_label` in the scan
file for the scanner flag, `HIT_LABEL` in `kod/detectors.py` for each detector
(`NARRATIVE_WITHOUT_MECHANISM` counts down repricings; the rest count up repricings).

## Run

```sh
cd kod-machine
python3 -m kod --db var/kod.db init
python3 -m kod --db var/kod.db seed      # anchors each seed open in git
python3 -m kod --db var/kod.db report
python3 -m kod --db var/kod.db verify
python3 -m unittest                      # 37 tests
```

Seed status after a clean run: calibration NOT_STARTED. That is the correct
result. The NVDA and SMCI cards are partial public reconstructions for the
hypothesis log. They are not a price series and they do not validate anything.
The seed no longer opens a prospective TEMPLATE row: a template has no real
cutoff, so the open gate refuses it.

## Open a real prospective case

Copy `seeds/prospective_template.json`. Fill every REPLACE value with facts that were
public at each cutoff, set `decision_cutoff` to the freeze time (within 1 hour of when
you will run `open`), and pre-register `outcome_window.start` and `.end`. Then:

```sh
python3 -m kod --db var/kod.db --push open path/to/card.json
```

Close only after `outcome_window.end`, by appending an outcome with the hash from open:

```sh
python3 -m kod --db var/kod.db close KOD-P-... '{"window_label":"5 sessions","window_return_pct":12.4,"outcome_label":"REPRICED_UP","source":"primary close series","card_sha":"<sha from open>"}'
```

Commit `var/kod.db` after each open or close. The registry commit holds the hash; the
database holds the rows `verify` rebuilds it from.

## Log a scan

```json
{
  "scan_id": "SCAN-IDX-20261008-0900",
  "scanner": "ASTRA",
  "universe_id": "IDX-ALL-20261008",
  "decision_cutoff": "2026-10-08T02:00:00Z",
  "outcome_window": {"start": "2026-10-08T02:30:00Z", "end": "2026-10-15T09:00:00Z"},
  "hit_label": "REPRICED_UP",
  "entries": [
    {"symbol": "AAAA", "venue": "IDX", "flagged": true,  "reconstruction_status": "PARTIAL_PUBLIC", "facts": {"dated_catalyst_known": true}},
    {"symbol": "BBBB", "venue": "IDX", "flagged": false, "reconstruction_status": "PARTIAL_PUBLIC", "facts": {}}
  ]
}
```

```sh
python3 -m kod --db var/kod.db --push scan scan.json
# after outcome_window.end:
python3 -m kod --db var/kod.db scan-close outcomes.json   # {"scan_id", "scan_sha", "outcomes": [{"symbol", "outcome_label", "window_return_pct", "source"}]}
```

Include every name the scanner evaluated, not only the flagged ones. Without the
unflagged names there is no base rate and no lift.

## Doctrine

`doctrine/KOD_DOCTRINE_v0.md` is hashed into every case. Edit it and the hash
changes; already-open cases stay bound to the old hash.
