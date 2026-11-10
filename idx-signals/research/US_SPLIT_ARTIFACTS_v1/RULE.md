# US_SPLIT_ARTIFACTS_v1: are some recorded US "spikes" reverse splits?

Frozen 2026-11-10, before the classification run. Owner's instruction: "Go" (2026-11-10), on the plan in the session
chat of the same day. This is an engineering audit of existing records, not a strategy test. It reads no outcome.

## Question

Which US Speculation Register sets (signal sessions 2026-10-27 onward) were recorded as a +30% move only because a
share split took effect between the previous bar and the signal bar, and which downstream records do those sets
feed?

## Population

Every record in `idx-signals/paper/speculations.jsonl` with `market == "US"` and a `decision` field (a sealed set),
at the input commit named in the report. None is dropped; a set that cannot be checked is classified UNKNOWN.

## Inputs (no outcome is read)

1. From the sealed set: `ticker`, `signal_session`, `signal.close`, `signal.previous`, `signal.ret1`, `signal.volr`.
2. A fresh Yahoo chart request per set: `interval=1d`, `events=splits`, `period1` = 00:00 UTC of
   `signal_session - 20 calendar days`, `period2` = 05:00 UTC of `signal_session + 1 day` (after the New York close of
   the signal session, before the next session opens). Used: the provider's split events and the daily closes up to and
   including the signal session. No bar after the signal session is requested.
3. SEC EDGAR corroboration for each provider split found in step 2, with the repository's existing verifier
   (`idxsig.us_actions.verify_event`, version us-actions-v2, window effective -45 / +5 days).

## Definitions

- `signal_bar`: the fresh pull's bar dated `signal_session` (New York date of the bar's timestamp).
- `prev_bar`: the fresh pull's last bar with a valid close strictly before `signal_bar`.
- `window_splits`: provider split events with an effective session (New York date of the event timestamp) in
  `(prev_bar date, signal_bar date]`.
- `adj_ret1 = fresh_close(signal_bar) / fresh_close(prev_bar) - 1`. The provider adjusts all of a name's bars for every
  split to the time of the pull, so this ratio is unaffected by splits.
- `units_ratio = (signal.close / signal.previous) / (fresh_close(signal_bar) / fresh_close(prev_bar))`: how far the
  recorded move differs from the adjusted move.

## Classes (first match wins)

| Class | Condition |
|---|---|
| UNKNOWN | the fresh pull failed, or has no `signal_bar` or no `prev_bar` |
| ARTIFACT_CONFIRMED | `window_splits` non-empty, `adj_ret1 < 0.30`, and the SEC status of a window split is VERIFIED |
| ARTIFACT_PROVIDER_ONLY | `window_splits` non-empty, `adj_ret1 < 0.30`, no window split VERIFIED by SEC |
| SPLIT_REAL_MOVE | `window_splits` non-empty and `adj_ret1 >= 0.30` |
| UNEXPLAINED_GAP | `window_splits` empty, and `adj_ret1 < 0.30` |
| CLEAN | `window_splits` empty and `adj_ret1 >= 0.30` |

UNEXPLAINED_GAP means the recorded move and today's adjusted move disagree but the provider lists no split in the
window (possible causes: a split the provider recorded on another date, a data correction, or a ticker change).

## Stop rule

If fewer than three sets are ARTIFACT_CONFIRMED, the report closes the question as isolated cases. No threshold in this
file is changed after the run.

## Downstream map (identifiers and counts only)

For each set in an ARTIFACT_* class: its ledger decision, Speculation Register resolutions (window and status only),
paper book plan and trade records, LLM_ARM_v1 call, LEARNER v2.4 forecast and catalyst tag, each by record id. No
return, outcome flag or profit figure is printed or summarised.

## Unresolvable resolutions

For each register resolution with status other than RESOLVED, the report lists the provider split events with an
effective session after the signal session (events only; any price arrays in that response are discarded unread and
not stored). This tests whether later splits explain the "does not reconcile" failures.

## Out of scope

No frozen record, scan, detector, register, book, account, learner or protocol is changed. No sealed set is rescored.
No performance figure is recomputed. A proposed tag and a proposed paper-book disclosure line are drafts for the
architect; they are not applied.

## Function contract (for independent tests)

`classify(window_splits: list[dict], adj_ret1: float | None, sec_statuses: list[str], fetch_ok: bool) -> str`

- `window_splits`: provider split events already restricted to the window (each a dict with at least `numerator`,
  `denominator`).
- `adj_ret1`: None when the signal or previous bar is missing.
- `sec_statuses`: one status string per window split, from `STATUSES` of us-actions-v2.
- `fetch_ok`: False when the provider request failed.
- Returns one of the six class names above, by the first-match table.

`window_events(events: list[dict], prev_day: str, signal_day: str) -> list[dict]`: the events whose
`effective_session` (ISO date) is strictly after `prev_day` and on or before `signal_day`.
