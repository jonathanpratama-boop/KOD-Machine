# E9 catalyst split (US stocks, SEC filings): checkpoint (replaceable view)

**COMPLETE: NEGATIVE.** Q1 INCONCLUSIVE (DOC minus UNDOC +1.99 points, 95% -1.83 to +6.00); Q2 UNPROFITABLE
(DOCUMENTED -1.07% per trade, negative every year). Report: `RESULT.md` here (copy of
`idx-signals/research/E9/results/RESULT.md`). Everything lives on `claude/idx-signals-test-repo-ds0jw7` under
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
| Second feasibility check (`feasibility_a3.py`): **GO** (644 DOC / 1,384 UNDOC / 223 DIL entered) | done | `f241c1c` |
| Protocol text, then `protocol.json` frozen with 25 hashes | done | `f6d6ae6`, `c93c50e` |
| One recorded run (`run_test.py`), committed as written | done | `2f1109d` |
| Independent verification (`verify_result.py`): VERIFIED; `RESULT.md` | done | this commit |

Nothing pending. Owner decision open: retire G2_RET30 as a US entry (see RESULT.md).
