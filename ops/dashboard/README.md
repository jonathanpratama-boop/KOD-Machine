# Dashboard source refresh and final supplement publication

The original publisher refreshed cloud results but retained a 7 November study
snapshot and replaced its build time with the cloud timestamp. This repair keeps
the one-page report and original publisher, with a separate hourly source rebuild.

`refresh_dashboard.py` reads KOD's current default branch plus each explicit
research branch named by the existing registry. It records source commit hashes,
keeps every study's own as-of date, and atomically replaces the embedded dataset.
A failed build preserves the exact prior snapshot and writes `SOURCE_REFRESH.json`
with STALE, the original build time, and the error. Backup mirror history is limited
to current branch heads; this limitation is recorded in the build provenance.
KOD's existing full Git history is used for report dates and retrospective records.

`publish_dashboard.py` still uses the existing backup locks and fast-forward-only
publication. It changes only DASHBOARD.html and DASHBOARD_RESULTS.json. Source
changes bypass the unchanged-cloud-results throttle. The page shows separate study
and cloud refresh clocks, and an overdue-source notice after two hours. It never
updates collector settings, trades, or research evidence.

Deploy source code under `/var/lib/kod-research-r2-ops/repairs/dashboard-closeout-20261113/code`.
Preserve the current publisher, template and snapshot before replacing only
`publish_dashboard.py`, adding `refresh_dashboard.py` beside it, and updating the
existing template. The source service runs separately from the cloud backup job;
its failures cannot hold the cloud backup lock. Start it once, enable the supplied
hourly timer, then let the existing publisher pick up the rebuilt snapshot.
Read SOURCE_REFRESH.json and the published embedded source commit after deployment.

The existing export_results.py and publication tests are retained with their
original data contract. Regression tests for source clocks, failed refresh and
branch references were written independently before the implementation.

`close_supplement.py` is a one-off operational closeout. The full frozen
combined_view.py verified all 196 supplement captures, plus 28 original references,
on 13 November. The collector had completed on 9 November; its last published
health was stale because reporting exceeded a 120-second verification timeout.
The helper preserves previous reports, uses the existing scoped backup writer and
identity, and publishes the original terminal receipts. No slot is recollected.
The supplement's completed coverage is separate from the still-running R2 study.

External R2 alert delivery remains unverified. This repair installs no alert system
and sends no synthetic notification.
