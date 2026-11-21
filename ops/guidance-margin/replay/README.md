# Historical guidance replay

On 19 November 2026 KOD replayed all 36 calendar-2025 earnings releases located for nine issuers in its November 2026 review queue. The frozen reader admitted zero pairs across the two cohorts. Zero paired outcomes means the return difference is unavailable. The 44 model calls cost an estimated $3.45. See `PUBLIC_SUMMARY.json` for dispositions, cost by cohort and checksums.

`PROTOCOL.md` defines the initial eight releases. `EXPANSION_PROTOCOL.md` adds 28. `EXPANSION_CORRECTION.md` records a pre-price implementation correction to the way the issuer archive handles intervening announcements from a different publishing account. Both the first and corrected expansion decisions remain on the study server. The scorer reads the corrected expansion seal.

### Verify the run

From the repository root, using the project Python environment:

```sh
PYTHONPATH=idx-signals python -m unittest discover -s ops/guidance-margin/replay -p 'test_*.py'
```

The original extractors used the reader and fact-checker from KOD revision `b7ac46148fc1be5f2367159b5116938e29de9fc9`. On the study server the frozen Python package is available at `/var/lib/kod/guidance-replay-expansion-20261119/frozen`. The cloud feed file also contained live operations changes. The functions used here for source parsing, model review and shared credit accounting matched that revision. Use the archived package for the recorded study. Later reader changes can yield different decisions.

To verify and score saved decisions without another model call, run from the repository root on the study server:

```sh
export PYTHONPATH=/var/lib/kod/guidance-replay-expansion-20261119/frozen
pilot=/var/lib/kod/guidance-replay-20261119
expansion=/var/lib/kod/guidance-replay-expansion-20261119
replay=ops/guidance-margin/replay
python "$replay/score_replay.py" --decisions "$pilot/decisions.json" --seal "$pilot/seal.json" --out "$pilot/scored"
python "$replay/score_replay.py" --decisions "$expansion/canonical/decisions.json" --seal "$expansion/canonical/seal.json" --out "$expansion/scored"
```

The scorer checks the sealed decision hash before fetching prices. It fetches price bars only for qualifying trades and reports empty horizons when none qualify. Source material, detailed model responses and the reservation ledger stay in private state.

### Rebuild sequence

For a deliberately new run, stage `PROTOCOL.md` in the pilot state directory. Stage `EXPANSION_PROTOCOL.md` as `PROTOCOL.md` and `EXPANSION_CORRECTION.md` under its own name in the expansion state directory. Use the project environment with the authorized API credential and the private live allowance ledger path as `live`. The scoring step above follows these commands:

```sh
python "$replay/inventory.py" "$pilot"
python "$replay/run_history.py" "$pilot" "$live"
python "$replay/expansion_inventory.py" "$expansion"
python "$replay/run_expansion.py" "$expansion" "$live"
python "$replay/reconcile.py" "$expansion" "$live"
```

A completed state is idempotent. A new paid run requires its own authorized accounting identity if the prior reservation labels already exist. The original discovery used today's issuer wire archive to locate historical documents. Its scope excludes releases outside that archive and some international wire URLs. SEC bulk submission data was unavailable. Issuer selection used 2026 information, and a model trained later may know the issuers' history. Retrospective receipts and fixed-slot modeled daily prices are distinct from live admissions and fills.
