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
  time, is not before `outcome_window.start`, or arrives after the window started.
  Timestamps need a timezone.
- Any open whose T-30D, T-72H or T-24H cutoff is not exactly 30 days, 72 hours or 24 hours
  before the decision cutoff
- A PROSPECTIVE fact (any non-null value, true or false) that does not cite archived
  evidence, and any card that cites evidence published after that information set's cutoff
- A PROSPECTIVE open or scan when no external timestamp authority answers, or with no git
  anchor configured
- A detector evaluation written after the open (a database trigger refuses it; the
  evaluations are part of the card hash)
- A close without the `card_sha` printed at open, with a different hash, or before
  `outcome_window.end` (any call type that carries a window)
- A scan log entry outside the same timing rules, and a scan close without its `scan_sha`

## Evidence: what was knowable, not what someone says was knowable

A fact in an information set is an assertion until it cites evidence. `kod evidence`
archives the document itself and its provenance:

```sh
python3 -m kod evidence filing.pdf \
  --url https://www.idx.co.id/... --publisher "IDX disclosure system" \
  --published-at 2026-10-01T09:12:00+07:00 --published-basis "IDX disclosure system timestamp" \
  --retrieved-at 2026-10-07T08:30:00Z \
  --archive-url https://web.archive.org/web/... --archived-at 2026-10-07T08:31:00Z --grade A
```

It prints the evidence id, which is the SHA-256 of the bytes. The bytes and a frozen
metadata file are committed to `registry/evidence/`. Grades: A primary source with an
authoritative publication timestamp (exchange disclosure, regulator filing); B reputable
secondary source with an explicit timestamp; C time supported only by an archive capture or
server metadata; D the operator's assertion. The report shows, per case, how many known
facts cite evidence and the weakest grade cited.

A card cites evidence per fact, per information set:

```json
"T-24H": {"cutoff": "...", "facts": {"dated_catalyst_known": true},
          "evidence": {"dated_catalyst_known": ["<evidence id>"]}}
```

For PROSPECTIVE cards every non-null fact must cite at least one evidence object, false as
much as true (an absence is shown by a capture of the source without the item). Null means
UNKNOWN and cites nothing. Any card, of any type, is refused if it cites evidence whose
`published_at` is after that set's cutoff. Because the card hash covers the evidence ids,
and the ids are content hashes, the external timestamp on the card also proves those exact
documents were in hand at the open.

What this cannot prove: that `published_at` is true. That is the source's own claim, which
is why the basis and grade are recorded and an archive capture is worth adding.

## Hash anchoring, external timestamps, and `verify`

Every open appends `{kind, record_id, sha256, opened_at, decision_cutoff, window}` to
`registry/opens.jsonl`, writes the frozen card (detector evaluations included) to
`registry/cards/<case_id>.json`, and commits those paths (`kod anchor case <id> <sha>`).
Scans do the same in `registry/scans.jsonl` and `registry/scans/`.

The git commit date is not evidence of time: it comes from the committer's clock, and a
backdated commit pushed later still shows its backdated date. So before the commit, the
exact registry line is sent as a SHA-256 digest to two independent RFC 3161 timestamp
authorities (freetsa.org and Sectigo). Their signed tokens are committed with the line under
`registry/timestamps/`, and verified offline against the certificates pinned in `tsa/`. A
PROSPECTIVE open or a scan is refused, and rolled back, if neither authority answers.

`verify` trusts no stored hash and no local clock. It rebuilds every card hash from the
case, information set, critic and detector-evaluation rows, every scan hash from the entry
and evaluation rows, and every evidence id from the archived bytes, and checks each against
the stored hash, the outcome's copy, the anchors row and the line in the anchor commit. For
time it uses the tokens: a prospective card fails unless a token verifies, dated within 1
hour of its decision cutoff and before its outcome window starts. It also checks that the
anchor commit is in HEAD's history and its line still in HEAD, the exact horizon offsets,
that every cited evidence was published by its cutoff and recorded before the open, that a
detector's frozen status still matches its code for the same rule version (an in-place rule
edit fails), and that the schema, migrations and doctrine were not edited after adoption.
A git commit date that disagrees with the tokens is reported. Exit code 1 on any failure.

Protect the branch on GitHub (Settings → Branches: block force pushes and deletions) so
the registry's history cannot be rewritten; the tokens prove when each line existed, branch
protection keeps the line from being quietly dropped.

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
python3 -m unittest                      # 62 tests
```

Seed status after a clean run: calibration NOT_STARTED. That is the correct
result. The NVDA and SMCI cards are partial public reconstructions for the
hypothesis log. They are not a price series and they do not validate anything.
The seed no longer opens a prospective TEMPLATE row: a template has no real
cutoff, so the open gate refuses it.

## Open a real prospective case

Archive each source document with `kod evidence` first. Then copy
`seeds/prospective_template.json`, fill every REPLACE value with facts that were public at
each cutoff and the evidence ids that show it, set `decision_cutoff` to the freeze time
(within 1 hour of when you will run `open`), set the three information-set cutoffs to
exactly 30 days, 72 hours and 24 hours before it, and pre-register `outcome_window.start`
and `.end`. Then:

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
