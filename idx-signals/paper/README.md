# Prospective paper ledger (no orders)

`ledger.jsonl` is the prospective record of detector D1 (`idxsig/rules/moonshot_e1.py`,
`MOONSHOT_E1_D1`, F1_ARA). One line per record, each carrying the previous line's hash and
stamped by freetsa and Sectigo (`timestamps/`); the commit that adds them is pushed, so
GitHub's workflow-run record dates it too. `python -m idxsig paper-verify` checks the chain,
the frozen scan files and every token. Nothing here is ever edited (the commit guard refuses
it); corrections are new lines.

| Record | When | Contents |
|---|---|---|
| SCAN | after every IDX session | data coverage, every D1 flag, every flag of the benchmark rules (F2 IGNITION analogue, F1), and `NO SIGNAL` when nothing qualifies; `scans/<id>/features.csv` freezes every name's inputs |
| DECISION | each qualifying candidate, before the next session's close | instrument, verified close, evidence, thesis, falsifiable prediction, terminal decision (BUY ON TRIGGER / PASS / NOT EXECUTABLE) with the reason, entry trigger, chase limit, invalidation, sizing formula with labelled risk scenarios, max planned loss, horizon, expiry |
| OUTCOME | after the window (`paper-score`) | discovery (did it reprice +30/50/100% within 5 sessions?) scored apart from the decision (would the plan have filled, and with what net return, MFE and MAE?) |

Commands (cloud or local; network needed for the Yahoo pull and the timestamp authorities):

```sh
python -m idxsig paper-scan --commit    # pulls ~200 days for every active name, scans the last session
python -m idxsig paper-score --commit   # scores decisions whose window has ended
python -m idxsig paper-verify
```

Policy versions (`idxsig/paper.py`): `PAPER-POLICY-v1` decided the first scan
(2026-10-07). `PAPER-POLICY-v2` (from the second scan) keeps every stop at least 5% below the
close, because v1 put GTBO's stop at its entry price on a one-price ARA bar. Decisions keep
the policy they were made under.

A paper BUY needs validated detection AND a validated executable plan. D1 has the first and
not the second (E1 validation: -4.06% vs -0.53% for matched random entries), so its
candidates are PASS until a plan that survives a prospective test exists. The plans are still
recorded and scored, so a rejected name that runs shows up as a missed gain, not as nothing.
