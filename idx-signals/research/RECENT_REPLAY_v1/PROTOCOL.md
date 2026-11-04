# RECENT_REPLAY_v1: LEARNER v2.4 replayed over this year's US spikes (frozen before any outcome is read)

**Owner's instruction (2026-10-30):** "we backtrack and test 4 days how accurate it is ... I need you to make it work
somehow with past data." This study answers the question the live test asks, on data already on disk, once.

## Question

For every US stock that closed 30% or more higher on a session in the range (`protocol.json` "range"), scanned as
the live scan scans it, with its five twins drawn as the Speculation Register draws them: do LEARNER v2.4's raw
forecasts, made as they would have been made that evening, rank the stocks that close at least 10% lower at the next
session (when fewer than half of their twins do: NEXT_DUMP10_1) above the others?

## What is replayed, exactly

- **Events.** The 400-day Yahoo pull `protocol.json` "manifest" (5,701 names of the US universe as of 2026-10-30),
  causal preprocessing (no row is removed with a later bar), `moonshot_g` G2_RET30 on each session, the scan's
  eligibility (tradeable, more than 20 sessions of bars), the scan's ranking (volume ratio). A candidate without a
  valid twin draw is skipped, as a live set would be.
- **Features.** `idxsig.learner3`'s own functions, as of the signal session: the scan-frame block, the bar and chart
  block over at most 120 sessions, EDGAR forms and dates up to the session, XBRL share counts from quarters ended at
  least 120 days before, FINRA's daily short-sale share, the name's split events. Built by `build.py` with no bar after
  the signal session read (`data/events_BUILD.json`). Fidelity check before the freeze: for 2026-10-29 the replay
  rebuilds the ten live sets with the same twins and the same 33 features to six decimals; for 2026-10-27/28 the same
  events (one name absent: a bar revised between pulls) with twins that differ where the pull's frame differs.
- **The learner, session by session.** At each session: the pinned warm start plus every replay outcome resolved by
  the previous session's close (the US routine forecasts before it scores the day), the running base rate for
  DOWN10_1 (0.5 until 20 resolved), the frozen US prior 0.403 for FADE10_5, feature centres from the earlier replay
  forecasts, the model and the benchmark refit; then `learner3.forecast_set` for that session's events. No forecast
  sees its own outcome or any later one. The gates (earned confidence, `published`) are not replayed: the claim is
  on `raw`.
- **Outcomes, read once by `run.py`.** NEXT1 and BASE5 from the same pull through `speculation.cone_outcomes`
  (the register's rule), the own-move label through `learner2.OWN_MOVE`.

## Statistic and pass bar (the registered one, verbatim from research/LEARNER_v2/protocol_v2_4.json "claim")

AUC of the raw NEXT_DUMP10_1 forecasts over resolved pairs (each set once), standard error from a bootstrap over
signal sessions (1000 resamples, seed 20261029), z = (AUC - 0.5) / se; looks at 250 / 500 / 1000 pairs with at least
30 / 60 / 120 sessions; SKILL when z >= 3.75 at the first look, 3.0 at the later ones; "not shown" otherwise. Reported
beside it, descriptive: the benchmark's AUC, the Brier gains (over the base rate, over the benchmark; daily blocks),
the companion DUMP10_5, the month-by-month AUC, and the certified next-day dump calls (`idxsig.call_cert`: the bar from
the 2022-2023 calibration plus the replay outcomes resolved before each forecast; the realised losing rate against the
certified 50%, with its exact binomial p).

## Reads of sealed data

US 2024 onward is sealed. This study reads the outcomes of the range in `protocol.json` once, with the owner's
instruction above. Nothing is tuned on them: v2.4, its warm start and its feature code are pinned (`code_pins`), and
the study cannot change them. A later learner version is tested on live data or on a period sealed from now on.

## Known limits (stated before the run)

- **Survivorship.** The pull is today's universe: a name delisted between the range and 2026-10-30 is absent, so
  spikes on names that were later delisted are missing. This removes dumps rather than adding them.
- **One pull, one vintage.** Twins and the breadth / market features come from this pull's frame, not from the frame
  the live scan would have had that evening; the fidelity check above bounds the difference.
- **Units.** The pull is split-adjusted; the BASE5 plan is simulated without unit conversion (a split inside a
  5-session window is rare and would distort that set's companion statement only; NEXT1 is on the reference chain).
- **Clock.** The live forecast is made about three hours after the close with that evening's EDGAR and FINRA; the
  replay reads EDGAR by filing date and FINRA by session, the same cutoffs.

## One run

`build.py` ran before this freeze (features only). `python3 run.py` runs once, writes `results/RESULT.json`,
`results/forecasts.csv.gz` and `REPORT.md`, and refuses to run again. Counted trial:
`research/QUANT_GRADE/trials/RECENT_REPLAY_v1_registered.json`.
