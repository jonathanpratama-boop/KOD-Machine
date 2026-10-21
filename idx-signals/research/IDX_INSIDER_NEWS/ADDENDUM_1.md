# IDX_INSIDER_NEWS: addendum 1 (an implementation defect in the recorded run, and the rule for the corrected run)

Written 2026-10-21 and committed before the corrected run is started. `PROTOCOL.md` is unchanged and still governs everything below.

## What was recorded
`results/` (commit 52a3750), produced once by `run_frozen.py`: verdict **FAIL**. G1 failed: mean excess over matched controls +2.91%
(95% interval +0.88% to +5.02%), bootstrap t 2.78 against the 3.0 hurdle; G2, G3 and G4 held. 295 events were scored out of the 370 that
were bought (EXITED). Holds 5 and 60: t 1.71 and 2.07.

## The defect
`idxsig/idx_events.py` (`run_events`) averaged each event's matched-control returns with `np.where(scored, net, np.nan).sum(0)`. A draw
that could not be bought (a name locked, too thin for the capacity cap, a unit change the registry cannot verify) put a NaN into the sum,
so **one unbuyable draw out of 200 erased the whole event's control mean**. Only events whose 200 draws were all scored kept a control:
`control_n` is 200 for all 295 kept events and between 4 and 199 for all 75 dropped ones. `PROTOCOL.md` says the control is the mean of
the event's scored draws and expects about 370 scored events. The synthetic tests of the module all had fully buyable control pools, so
they did not see it. It was found after the run because the scored count (295) did not match the expected count (about 370).

The independent verifier `verify_v2.py` did not find it either: it takes the control means as given. It also has no corporate-action
logic and reported two false mismatches (SGER signal 2022-06-17, a verified 1.9 stock dividend; SMDR signal 2023-01-13, a verified 5:1
split); the harness scaled the shares for both and its returns are right.

## The fix (same draws, same inputs, same gates)
`mean_over_scored` in `idxsig/idx_events.py` averages over the scored draws only, and a draw with a non-finite return counts as unscored.
Two tests were added to `tests/test_idx_events.py`; the second one fails on the old code (checked). The control draws are the same
(same seed and the same events), so the control means of the 295 events already scored do not change; the 75 dropped events, and every
other event with a partly unbuyable pool, now get the mean of their scored draws. `verify_corrected.py` replaces `verify_v2.py` for this
study: it applies the registry's verified share scaling itself, recomputes every EXITED trade and every SKIP_OVERLAP decision from the
panel and registry files, and fails if any EXITED event with a scored control has no control mean (run on `results/` it reports
"75 EXITED events with scored controls have no control mean" and nothing else; all 370 trades recompute to within 5e-16).

## Rule for the corrected run (fixed now)
1. The corrected run is `run_corrected.py`: `run_v2.py` with the same three inputs pinned by the same sha256, the same window, holds,
   200 draws, seeds and gates G1-G4, writing to `results_corrected/`. It refuses to start if the corrected aggregation is missing.
2. Its result is the result of `PROTOCOL.md` and **supersedes the recorded run's verdict in whichever direction it falls**; the recorded
   run stays in `results/` and is reported beside it with its t of 2.78. This is decided now, before the corrected number exists.
3. It is the only further run. Anything after it is a new experiment with its own protocol.
4. The corrected result is reported as verified only if `verify_corrected.py` passes with no mismatch.
5. Register (counted test 23): one test, with the corrected run's one-sided p; `variants_searched` is 7 (3 holds in each of the 2 runs,
   plus the descriptive slice below). The hurdle stays t >= 3.0: the extra look is paid for in the variants count, not by moving the line.
6. Descriptive, not a gate: hold 20 restricted to events with at least 100 scored control draws (`verify_corrected.py` prints it), to see
   whether events with thin control pools carry the result.
7. While diagnosing, the mean own return of the 75 dropped events (+0.5%) and of the 295 kept ones (+2.3%) was read from the recorded
   output. That did not shape the fix, which is an aggregation correction, nor this rule.
