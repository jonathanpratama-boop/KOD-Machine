# Phase 2 integration TODO (collected from builder reports; apply when merging e5/* into claude/e5-ceiling)

## from build:h1-controls (commit c537606 on e5/h1-controls)
- `idx-signals/idxsig/cli.py` ~line 91: add "v3" to `--controls-version` choices (default stays "v2").
- `idx-signals/idxsig/e1.py` line 151: `Study` hard-codes `controls.features(m, "v2", ...)`; the E5 detection stage needs the h3-e1 opt-in (`pool_version='v3'`) to pass "v3" there — check h3's branch covers it, else do it at integration.
- Docstring figure "28% of IDX attempts never matched on volatility under v2" is quoted from the synthesis, not recomputed; verify at Stage 0 or soften the wording.
