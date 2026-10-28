# KILL_TEST_2020_2022, addendum 1: code v2 (written before any run)

The review of the v1 code (`kt_lib.py`, `run.py`, `PINS.json`) found defects before the test was run. `research/` is
append-only, so v1 stays as committed and is superseded by `kt_lib_v2.py`, `run_v2.py`, `freeze_v2.py` and
`PINS_v2.json`. **Run only `run_v2.py`.** v1's `run.py` also refuses on its own, because its pins no longer match
`idxsig/catalysts.py`. Nothing in `PROTOCOL.md` or `protocol.json` changes, and no return was read: there is no
`results/` directory.

What v2 changes, each a code fix toward the frozen protocol:

1. **Repeat rule in calendar days.** The protocol drops an original SC 13D with another original on the same subject
   "in the 90 calendar days before". v1 compared acceptance times in seconds (90 x 86,400), so a filing exactly 90
   calendar days later but later in the day escaped the rule. v2 compares SEC filing dates in calendar days, as the
   live register does (`catalysts.earlier_13d`: an earlier filing dated on or after the day minus 90). In the
   collected list this changes one filing: Arcus Biosciences (CIK 1724521), 0001564590-20-046531, now a repeat of
   0001104659-20-084444.
2. **No return file outside GO.** v1 wrote `results/events_fire.csv` (with each FIRE event's returns) even when the GO
   rule failed. The protocol reads no return statistic without GO; v2 writes it only under GO.
3. **Degenerate cases are INCONCLUSIVE.** A non-finite mean gives INCONCLUSIVE rather than NOT_KILLED, and a bootstrap
   standard error at or below 1e-12 (for example a single ISO week) gives no t.
4. **Empty list.** The funnel accepts an empty event list.

The unit tests (`tests/test_kill_test_13d.py`) load `kt_lib_v2.py` and cover items 1, 3 and 4.
