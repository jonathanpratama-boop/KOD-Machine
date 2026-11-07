# KOD comparison input repair

The input worker supplies missing daily liquidity data through the existing
engine queue. It does not restart the collector or alter previous decisions.
The timer checks every 15 minutes; source requests occur only when the required
30-day input window is incomplete, and are spaced one second apart.

The results exporter reads a consistent SQLite snapshot. The server refreshes
`/var/lib/kod/research-r2/comparison-inputs/RESULTS.json` every 15 minutes.
The HTML dashboard is a saved report; it does not update itself.

The prospective check registered on 8 November uses the original pre-outcome
comparison basket for every new signal, fixes one-minute observations and a
24-hour exit, and excludes the already-known ONE result from its new tally.
The exporter verifies the basket against the original append-only EVENT record.
Missing baskets and incomplete outcomes stay visible rather than becoming zero.

The existing backup service now publishes DASHBOARD.html and
DASHBOARD_RESULTS.json to its same private study branch. New signals/outcomes
trigger a refreshed copy at the next backup cycle; unchanged reports refresh
about every 15 minutes. The publisher stages only those two files and cannot
stop collection. It adds no credentials or public hosting. Current automatically
refreshed report:
https://github.com/jonathanpratama-boop/KOD-Timing-Backups/blob/research-r2-20261105T181200Z/DASHBOARD.html

The activation and publisher use the additive deployment folder
`/var/lib/kod-research-r2-ops/repairs/prospective-check-20261108`.
An already-downloaded report remains a dated snapshot.

To refresh that report, run the exporter, download its JSON, and pass it to the
existing dashboard builder:

```sh
python3 tools/status/dashboard/make_standalone.py --data /path/to/status-data \
  --results /path/to/RESULTS.json --out tools/status/dashboard/standalone.html
```

Alternatively place the downloaded file at `status-data/cloud_results.json`;
the builder includes it automatically. Store the snapshot beside the HTML on
GitHub so the displayed figures can be checked against their source.

The initial refresh triggered an existing local request-weight precaution on
HTTP 200, causing a roughly three-minute interruption. Its stop record and gap
were preserved, collection resumed, and subsequent daily requests are spaced.

Focused tests cover receipt-time eligibility, unchanged earlier records, exact
recovery from archived bytes, and read-only pending/completed/missing results.
Run them with the frozen engine's dependencies on `PYTHONPATH`.
