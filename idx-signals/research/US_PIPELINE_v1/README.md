# US pipeline milestone: which existing results are affected

Targeted checks (`checks.py` -> `checks.json`) on the committed inputs. Nothing existing was
edited; the one rerun is appended as a new research run.

| Repair | Check | Effect on existing results |
|---|---|---|
| One verification record per provider event (ca-reconcile-v1) | All 1,594 provider split events of panel names after 2023-01-03 have exactly one matching record with the same payload hash, in both the v3 (shares) and the Codex v2 schedules. The 175 events with no record at all belong to names absent from the 2023 panel. | None. The v3 panel rebuilt under the new rules is byte-identical (same sha256) with the same 669-name quarantine. |
| Inputs bound by sha256 | `check_bound_inputs` passes for the raw manifest, schedules and coverage used by v2/v3. | None. |
| Share-count window | Every SHARES_CONFIRMED record is effective after 2023-12-29, and the v3 panel reads through 2023-12-29. | None. A panel reading past 2023-12-29 with share-count records is now refused. |
| Outcome-dependent exclusion | 399 of the 669 quarantined names are excluded by records dated after the panel's last session. | Labelled in panel manifests (format v3) and run summaries. The E2-US repair results must be read with and without quarantine (`research/E2/repair_v3/SELECTION_NOTE.md`). |
| FILL-B-v2 (entry-session share units) | The v3 fill-B configuration was rerun with B2 (run `20261008T165454Z_MOONSHOT_E2_US_D1_v1`). | No rule trade changes status (536 scored, average net -0.973% either way). The matched random mean moves from -0.7481% to -0.7498%, and p stays 0.62. The v3 conclusion stands. |
| Approval pinned to one run + config | The old lookup took the last matching run in `RUNS.jsonl`. For US it moved through nine runs on 2026-10-08 and ended on the repair_v3 fill-B run `20261008T115656Z`. | No recorded decision was a BUY. The only recorded US scan cites the original run `20261008T060443Z`. Without this PR, the next US scan would cite the fill-B research run. With it, IDX and crypto are pinned to their current runs, and US has no pin. |
| Positive average net required | Every pinned run has a negative average net. | No change: all candidates stay PASS. |
| 5% stop rule (PAPER-POLICY-v4) | All 16 recorded paper plans (policies v1/v3) have a stop 8.7-23.1% below their maximum permitted entry. | Those plans would break Jonathan's rule. None was executed: 16 PASS, 2 NOT EXECUTABLE. They keep their policy; new decisions use v4. |

## Replay of the 2023 US signals under EXEC-US-v1 (descriptive, not approval evidence)

The 1,683 signals of MOONSHOT_E2_US_D1 in 2023, quarantined names included and labelled:

| Outcome | Count |
|---|---|
| Rejected: open above the 5% band | 1,370 |
| Rejected: open at or below the stop | 116 |
| Rejected: no plan (no permitted entry or no share fits) | 83 |
| Rejected: no opening print | 23 |
| Filled | 79 |
| Pending at the end of the data | 12 |

Filled trades: average net +0.97%, median -3.58%. Exits: 61 stops, 4 gaps through the stop,
14 time exits. Excluding the 46 filled trades in quarantined names: 33 trades, average +7.2%.
That gap is the outcome-dependent exclusion at work, not a result. There is no random baseline,
so this approves nothing; US has no approval pin. The detector signals on +30% days, whose lows
are usually far below the close. With a stop at the signal low, the 5% rule leaves almost no
permitted entry, so most signals are rejected by design.

Files: `checks.json`, `replay_2023_exec_us_v1.csv` (one row per signal),
`replay_2023_exec_us_v1_full.json` (plans and results), `WORKED_EXAMPLES.md`.
