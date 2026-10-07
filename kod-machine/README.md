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
- A PROSPECTIVE (STRICT-v3) fact, true or false, without evidence; evidence graded D,
  published after the set's cutoff, or recorded after the open; a primary-document claim
  without verified PRIMARY evidence; a fact-level grade claim its evidence does not meet
- An evidence object claiming a grade its verification does not support, a publication time
  after its as-of cutoff (unless a RETROSPECTIVE grade D account), or a publication time
  derived from retrieval
- Information sets other than exactly T-30D, T-72H and T-24H
- Opening or scanning after `kod/detectors.py` changed without a new `RULE_VERSION`
- A PROSPECTIVE open or scan when no external timestamp authority answers, or with no git
  anchor configured
- A detector evaluation written after the open (a database trigger refuses it; the
  evaluations are part of the card hash)
- A close without the `card_sha` printed at open, with a different hash, or before
  `outcome_window.end` (any call type that carries a window)
- A scan log entry outside the same timing rules, and a scan close without its `scan_sha`

## Evidence: what was knowable, not what someone says was knowable

A fact in an information set is an assertion until it cites evidence. An evidence object
(`KOD-EVIDENCE-v2`, `kod/evidence.py`) describes one document offered as proof of what was
public at an as-of cutoff:

| Field | Meaning |
|---|---|
| `evidence_id` | SHA-256 of the frozen object |
| `source_url`, `source_type`, `publisher`, `document_type` | what it is; type is PRIMARY, SECONDARY or RETROSPECTIVE |
| `event_time` | when the underlying event happened or is scheduled |
| `publication_time` (+ `publication_time_basis`) | when the source published it, and how that is known. Null if unknown; never filled in from retrieval |
| `retrieval_time` | when we fetched a copy |
| `archive_url`, `archive_time` | an independent archive capture, if any |
| `as_of_cutoff` | the cutoff the object is graded against |
| `content_sha256`, `archived_copy` | the bytes, when available and permissible to keep, committed under `registry/evidence-v2/` |
| `existence_verified`, `content_verified` | recorded separately, each by its own method |
| `verification_method` | `{existence, content}`; see below |
| `evidence_grade`, `grade_ceiling` | declared grade, and the strongest grade the fields support |
| `verification_notes`, `provenance`, `corroborated_by` | how the copy was obtained |

Existence (the document was public at or before the cutoff) and content (the bytes held
here are what was available then) are different claims. A filing's timestamp proves the
first, not the second. Methods:

- existence: `PRIMARY_SOURCE_TIMESTAMP` (the exchange or regulator system's own time),
  `CONTEMPORANEOUS_ARCHIVE` (an archive capture dated at or before the cutoff),
  `EXTERNAL_TIMESTAMP_RECEIPT` (we captured the bytes and RFC 3161-stamped them before the
  cutoff), `CORROBORATED_CONTEMPORANEOUS` (two or more objects from different publishers,
  dated by the cutoff), `NONE`
- content: `CONTEMPORANEOUS_ARCHIVE_HASH_MATCH` (the bytes are an archive capture dated at
  or before the cutoff), `EXTERNAL_TIMESTAMP_RECEIPT`, `NONE`

Each method's requirements are checked. A declared method that is not shown is refused, not
downgraded. Grades are mechanical: the ceiling is computed from the fields, and a declared
grade stronger than the ceiling is refused (also by a CHECK constraint in the database):

- **A**: contemporaneous PRIMARY evidence, existence and content both verified, published by the cutoff
- **B**: PRIMARY or SECONDARY, existence verified by a contemporaneous method, published by the cutoff
- **C**: dated by the cutoff, but existence and content unverified (a page accessible today with a historical date)
- **D**: retrospective: a later account, an unknown publication time, or published after the cutoff

A document published after `as_of_cutoff` is refused unless it is declared RETROSPECTIVE and
grade D. Objects are immutable; a better-verified copy is a new object with a new id.

Record one from a JSON declaration (the bytes are optional; without them contents cannot be
verified):

```sh
python3 -m kod evidence declaration.json --file filing.pdf     # prints the evidence id
```

A card cites evidence per fact, per information set, and may claim a grade per fact:

```json
"T-24H": {"cutoff": "...", "facts": {"primary_document_public": true},
          "evidence": {"primary_document_public": ["<evidence id>"]},
          "fact_grades": {"primary_document_public": "A"}}
```

**Integrity levels.** Every new card is `KOD-CARD-v3` with `integrity_level`:

- `STRICT-v3` (required for PROSPECTIVE; available for historical cards): every non-null
  fact, false as much as true, cites evidence; every cited object was published by that
  set's cutoff, graded as of a cutoff no later than it, recorded before the open, and is not
  grade D; `primary_document_public` / `mechanism_in_primary_docs` = true must cite a
  PRIMARY object with verified existence; a `fact_grades` claim must be met by a cited object.
- `PARTIAL` (default for retrospective and simulated cards): citations optional; grade D
  retrospective accounts allowed; anything else cited must still be dated by the cutoff.

The existing NVDA and SMCI seed cards stay as they were: v1, PARTIAL_PUBLIC, no evidence.
No evidence was retrofitted to them.

What this cannot prove: that a source's own publication time is true. That is why its basis
is recorded and an independent archive capture or contemporaneous stamp raises the grade.

## Hash anchoring, external timestamps, GitHub receipts, and `verify`

Every open appends `{kind, record_id, sha256, opened_at, decision_cutoff, window,
integrity_level}` to `registry/opens.jsonl`, writes the frozen card (detector evaluations,
rule version and detector code hash included) to `registry/cards/<case_id>.json`, and
commits those paths (`kod anchor case <id> <sha>`). Scans do the same in
`registry/scans.jsonl` and `registry/scans/`.

The git commit date is not evidence of time: the committer writes it, and a backdated commit
pushed later still shows its backdated date. Two independent clocks are used instead:

1. **RFC 3161 tokens.** Before the commit, the exact registry line is sent as a digest to
   freetsa.org and Sectigo. Their signed tokens are committed under `registry/timestamps/`
   and verified offline against the certificates pinned in `tsa/`. A PROSPECTIVE open or a
   scan is refused, and rolled back, if neither authority answers.
2. **GitHub server-side receipt.** `open` pushes the anchor commit immediately (prospective
   cards and scans). GitHub creates a workflow run for that push; the run's `created_at` is
   set by GitHub's servers and its `head_sha` is the pushed commit. The receipt is the
   earliest push-triggered run whose head_sha is exactly the anchor commit. `kod receipt
   fetch` records it (table `remote_timestamp_receipts`, line in `registry/receipts.jsonl`):
   provider, record, anchor SHA, run id, GitHub's `created_at`, URL, fetch time, status.
   `verify` and `report` never trust the stored copy; they ask GitHub again (with
   `GITHUB_TOKEN`, actions:read) and compare.

A prospective case is **AUTHORITATIVE**, and counts toward calibration, only if it is a
`KOD-CARD-v3` `STRICT-v3` card, its hash is in its anchor commit (an ancestor of HEAD, line
still present), and GitHub's receipt for exactly that commit predates `outcome_window.start`.
Otherwise it is excluded with a status: `LEGACY_INTEGRITY`, `ANCHOR_NOT_PROVEN`,
`REMOTE_TIMESTAMP_UNVERIFIED` (no API access, no exact-commit run, or the run was deleted),
`REMOTE_TIMESTAMP_LATE`, or `REMOTE_RECEIPT_MISMATCH` (a stored receipt disagrees with GitHub;
this one fails `verify`). The report lists excluded closed cases with their outcomes, so a
pattern of excluded losers is visible. Scans follow the same rule for the lift tables.

**Branch protection is not available here.** The branch reports `protected: false`, and on
GitHub's Free plan branch protection and rulesets cover public repositories only; private
repositories need Pro, Team or Enterprise ([protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches),
[rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)).
So history can be force-rewritten. The receipts partly mitigate this: a run records which
commit GitHub received and when, and is not removed by a force-push, so a rewritten anchor
no longer matches its receipt, and a call created after the fact cannot obtain an earlier
receipt. What they do not stop: an admin deleting runs. Deletion cannot make a call look
earlier; it makes the call unverifiable, excluded and counted.

**Receipts expire.** GitHub archives workflow runs after 400 days and deletes them 10 days
later; the period cannot be changed ([usage limits](https://docs.github.com/en/actions/reference/usage-limits-billing-and-administration)).
After that a case's receipt can no longer be re-checked, so by the rule above it becomes
REMOTE_TIMESTAMP_UNVERIFIED and leaves the authoritative set. The RFC 3161 tokens do not
expire with it and keep proving when the hash existed. Practical consequence: generate and
commit the calibration report (`kod report`, run in CI with `GITHUB_TOKEN`) while the
receipts are live, so the dated, verified snapshot of eligibility is itself on record.

`verify` trusts no stored hash and no local clock. It rebuilds every card hash from the
case, information set, critic and detector-evaluation rows, every scan hash from the entry
and evaluation rows, every v2 evidence id from its frozen object and every archived copy from
its bytes, and recomputes every evidence grade ceiling. It checks each hash against the
stored hash, the outcome's copy, the anchors row and the line in the anchor commit; the RFC
3161 tokens against the decision cutoff and window start; the GitHub receipt as above; the
exact horizon offsets; every citation; that the detector source still matches the code hash
bound to its rule version; and that the schema, migrations and doctrine were not edited after
adoption. A git commit date that disagrees with the tokens is reported. Exit code 1 on any
failure; UNVERIFIED and LATE are reported and excluded, not failed.

## Detectors are frozen at prediction time

Detector evaluations are computed inside the open transaction from the three information
sets only (never from an outcome), stored with the open's timestamp, and included in the
card hash. A database trigger refuses any evaluation written later. Each `RULE_VERSION` is
bound to the SHA-256 of `kod/detectors.py` the first time it is used (table
`detector_versions`); if the source changes while `RULE_VERSION` stays the same, new opens and
scans are refused and `verify` fails. A changed detector is a new rule version, and old cards
keep the version and code hash they were evaluated under.

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
python3 -m unittest                      # 95 tests
```

Seed status after a clean run: calibration NOT_STARTED. That is the correct
result. The NVDA and SMCI cards are partial public reconstructions for the
hypothesis log. They are not a price series and they do not validate anything.
The seed no longer opens a prospective TEMPLATE row: a template has no real
cutoff, so the open gate refuses it.

## Open a real prospective case

Record each source document with `kod evidence` first. Then copy
`seeds/prospective_template.json`, fill every REPLACE value with facts that were public at
each cutoff and the evidence ids that show it, set `decision_cutoff` to the freeze time
(within 1 hour of when you will run `open`), set the three information-set cutoffs to
exactly 30 days, 72 hours and 24 hours before it, and pre-register `outcome_window.start`
and `.end`. Then:

```sh
python3 -m kod --db var/kod.db open path/to/card.json        # pushes the anchor commit
GITHUB_TOKEN=... python3 -m kod --db var/kod.db receipt fetch  # records GitHub's receipt
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
