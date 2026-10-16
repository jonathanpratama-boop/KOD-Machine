# E9 catalyst split (US stocks, SEC filings): checkpoint (replaceable view)

**IN PROGRESS.** Everything lives on `claude/idx-signals-test-repo-ds0jw7` under
`idx-signals/research/E9/`, plus `idxsig/catalyst.py` and `tests/test_catalyst.py`,
`tests/test_e9_runner.py` and `tests/test_e9_pipeline.py`. No real-money action of any kind.

| Step | State | Commit |
|---|---|---|
| Hypothesis and declared feasibility rule | done | `442b215` |
| Classifier, entry builder, SEC collector, feasibility counter | done | `d7e4770` |
| Amendments 1-2 (JSON time convention; two code defects), before any count | done | `91a2eff`, `2fa80c4` |
| Shared entry list: 3,116 attempted signals, 623,200 matched-control entries, no returns | done | `cc2d266` |
| SEC submissions for 1,225 tickers / 1,223 CIKs, 0 failures | done | `4766e54` |
| First feasibility check: **NO-GO** (the JSON acceptance time mixes UTC and double-converted New York time, 10/10) | recorded | `458d145` |
| Amendment 3: acceptance times from each filing's SGML header | done | `85b23b0` |
| Runner, independent verifier, freeze script, synthetic end-to-end test | done | `00bb216` |
| Second feasibility check (`feasibility_a3.py`) | running | |
| Freeze `protocol.json` (only after GO) | pending | |
| One recorded run, verification, `RESULT.md` | pending | |

Resume: if `research/E9/feasibility_a3/` exists, commit it with its manifest. If its decision is GO, commit
`PROTOCOL.md`, then run `python3 research/E9/freeze.py` and commit `protocol.json`. Then run
`python3 research/E9/run_test.py` once, then `research/E9/verify_result.py`, all from `idx-signals/`.
SEC requests need `KOD_SEC_CONTACT` (the owner's address; it is never written to a file).
