# E9 feasibility amendment 2 (2026-10-16), before the feasibility check runs

Two defects found by reading the code, before any SEC response or E9 count was read (the shared entry list
was still being built). Neither changes a class rule, a window, a threshold or a GO condition.

1. **The entry-date sanity check would stop the check.** `feasibility_a1.py` (committed, never run) asks
   that every attempted signal's entry date equal the next panel session *or be empty*. The entry list
   is read with empty fields as missing values, so a signal that was never filled (for example
   SKIP_LIQUIDITY) fails both tests, and the script would exit with "an entry date is not the next panel
   session". `feasibility_a2.py` reads a missing entry date as "not filled". Filled signals are checked
   exactly as before. `feasibility_a2.py` is otherwise `feasibility_a1.py` unchanged, apart from the
   addition in point 2; neither earlier script is run.

2. **A filing without an acceptance time** (an empty or null `acceptanceDateTime`) made
   `idxsig.catalyst.classify` compare a missing value with a time. Rule, fixed now: such a filing is in
   no window, because it cannot be shown to have been public before an open. The check reports how many
   filings in 2020-06-01..2023-01-31 lack an acceptance time, so the effect of the rule is visible. The
   code is `idxsig.catalyst.accepted`, and `tests/test_catalyst.py` covers it.
