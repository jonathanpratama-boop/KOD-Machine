# Detector D1 v1 → v1.1 (2026-10-08)

The idxsig harness calls the rule on every prefix of its window, starting with one session.
`moonshot_e1` v1 crashed when a window was shorter than a lookback (`_lag(level, 5)` on two
sessions). v1.1 fills those cells with NaN instead. The rule itself (F1_ARA, frozen in
`29e32e4`) and every threshold are unchanged.

The E1 study and the live scan never call the detector on a short window, so the validation
result (`../validation/result.json`, computed with v1, module SHA-256 `21614ba9…`) applies to
v1.1 as well. `equivalence.json` shows it: every family flag from v1 and v1.1 is identical
over all 983 names and 1,083 sessions of the study market (`equivalence_check.py`, run at
the v1.1 commit, loading v1 from `29e32e4`).
