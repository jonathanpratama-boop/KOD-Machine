# EXIT-ATR-v1 cloud run: checkpoint (replaceable view)

**COMPLETE: NEGATIVE.** Trailing exit does not improve the original exit; the resulting strategy is
unprofitable. Full report: `RESULT.md` here (copy of `idx-signals/research/EXIT_ATR_v1/cloud/results/RESULT.md`).

Branch `claude/exit-atr-trail-v1` (cloud-local, not pushed; based on published E6 head fa142ff):
- `d1f11c4` protocol frozen before any exit return (code, tests, entries, eligibility, hashes)
- `5d86e89` the single comparison, ledgers, independent verification

Carried in `bundles/exit-atr-trail-v1.bundle`. Restore:
`git fetch handoff/exit-atr-cloud/bundles/exit-atr-trail-v1.bundle claude/exit-atr-trail-v1:claude/exit-atr-trail-v1`
(needs `origin/claude/e6-pressure-response`). Everything lives under `idx-signals/research/EXIT_ATR_v1/cloud/`
plus `idxsig/exit_atr.py` and `tests/test_exit_atr.py`, so it does not collide with Hermes's uncommitted
Mac files (`hermes/exit-atr-trail-v1`, untouched).
