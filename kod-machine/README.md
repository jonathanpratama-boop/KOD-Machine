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

## Run

```sh
cd kod-machine
python3 -m kod --db var/kod.db init
python3 -m kod --db var/kod.db seed
python3 -m kod --db var/kod.db report
python3 -m unittest tests.test_ledger
```

Seed status after a clean run: calibration NOT_STARTED. That is the correct
result. The NVDA and SMCI cards are partial public reconstructions for the
hypothesis log. They are not a price series and they do not validate anything.

## Open a real prospective case

Copy `seeds/retrospective_cases.json` structure. Set `call_type` to
`PROSPECTIVE`, fill facts that were public at each cutoff, and include the
critic. Then:

```sh
python3 -m kod --db var/kod.db open path/to/card.json
```

Close only after the window, by appending an outcome:

```sh
python3 -m kod --db var/kod.db close KOD-P-... '{"window_label":"5 sessions","window_return_pct":12.4,"outcome_label":"REPRICED_UP","source":"primary close series","card_sha":"<sha from open>"}'
```

## Doctrine

`doctrine/KOD_DOCTRINE_v0.md` is hashed into every case. Edit it and the hash
changes; already-open cases stay bound to the old hash.
