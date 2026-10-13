# Prospective paper ledger (no orders)

`ledger.jsonl` is the prospective record of the frozen moonshot detectors in three markets:

| Market | Detector | Rule | Session scanned | Paper entry |
|---|---|---|---|---|
| IDX | `MOONSHOT_E1_D1` (`rules/moonshot_e1.py`) | F1_ARA: closed at the auto-rejection upper limit | IDX session, after its close | the next session's close |
| US | `MOONSHOT_E2_US_D1` (`rules/moonshot_g.py`) | G2_RET30: day return >= +30% | US regular session, after its close | the next session's opening print |
| CRYPTO | `MOONSHOT_E2_CRYPTO_D1` (`rules/moonshot_g.py`) | G2_RET30 | UTC day, after 00:00 UTC | the live Binance quote taken at decision time |

One line per record, each carrying the previous line's hash and stamped by freetsa and
Sectigo (`timestamps/`); the commit that adds them is pushed, so GitHub's workflow-run record
dates it too. `python -m idxsig paper-verify` checks the chain, the frozen scan files and every
token. Nothing here is ever edited (the commit guard refuses it); corrections are new lines.
Records carry `market`; IDX records written before policy v3 have none and are IDX.

| Record | When | Contents |
|---|---|---|
| SCAN | after every session | data coverage, every detector flag, every flag of the benchmark rules, and `NO SIGNAL` when nothing qualifies; `scans/<id>/features.csv` freezes every name's inputs |
| DECISION | each qualifying candidate, before the entry | instrument, verified price, evidence, thesis, falsifiable prediction, terminal decision (BUY ON TRIGGER / PASS / NOT EXECUTABLE) with the reason, entry trigger, chase limit, invalidation, sizing formula with labelled risk scenarios, max planned loss, horizon, expiry |
| OUTCOME | after the window (`paper-score`) | discovery (did it reprice +30/50/100% within 5 sessions?) scored apart from the decision (would the plan have filled, and with what net return, MFE and MAE?) |

Commands (network needed for the data pull and the timestamp authorities):

```sh
python -m idxsig paper-scan --market IDX --commit      # Yahoo, ~200 days of every active IDX name
python -m idxsig paper-scan --market US --commit       # Nasdaq Trader listing + Yahoo, ~5,700 names
python -m idxsig paper-scan --market CRYPTO --commit   # Binance spot, every TRADING USDT pair
python -m idxsig paper-score --market <M> --commit     # scores decisions whose window has ended
python -m idxsig paper-verify
```

Policy versions (`idxsig/paper.py`): `PAPER-POLICY-v1` decided the first IDX scan
(2026-10-07). `PAPER-POLICY-v2` keeps every stop at least 5% below the close, because v1 put
GTBO's stop at its entry price on a one-price ARA bar. `PAPER-POLICY-v3` extends v2 to US
(hypothetical $10,000 account, E2 cost tiers) and crypto (10,000 USDT, 0.1% fee + 0.1%
slippage per side, no quote = NOT EXECUTABLE). `PAPER-POLICY-v4` (2026-10-13) adds the E3 rule
for IDX: when `research/E3` has frozen and validated a (detector, plan) pair, IDX scans run that
detector (`MOONSHOT_E3_D1`) and each decision carries the plan the harness validated (its own
trigger and the sessions it may trigger on, its exit, its holding period, no chase limit), and is
scored by the harness's execution model so the outcome is what the validation run would have
recorded. No pair has been validated (E3 discovery admitted none), so v4 decides exactly as v3
did. Decisions keep the policy they were made under.

Versions behind every call. Each SCAN and DECISION names its detector (rule id, version, module
SHA-256), policy (id and SHA-256), data manifest (and its SHA-256) and, from 2026-10-08 09:30 UTC,
its `preprocessing`. The three scans before that field existed used: SCAN-2026-10-07-F1_ARA
`idx-yahoo-recent-v1`; SCAN-CRYPTO-2026-10-07-G2_RET30 and SCAN-US-2026-10-07-G2_RET30
`global-close-legacy-v1` (the legacy step that drops a bar reverting the next session; at decision
time that next bar is never after the decision). Live preprocessing is pinned by name in
`paper.PREPROCESSING`; changing it is a new policy version.

Scoring (`paper-score`, scorer `paper-score-v3`): scoring bars go through the causal step (no bar
is removed because of a later one). Units come from the provider's split records after the
signal session, each corroborated by an SEC filing for US names (`us_actions`), never from a
change in price ratios; the recorded signal close must reconcile with the scoring bars in those
units. When that cannot be established (an uncorroborated split, an IDX split, an unexplained
rescaling) the OUTCOME is recorded `UNSCORABLE` with the reason. A corrected outcome is a new
OUTCOME with `revises` = the earlier one's `record_hash` (`paper-score --rescore ID --reason ...`).
The older price-ratio scaling remains only as a labelled forensic path and never records.

A paper BUY needs validated detection AND a validated executable plan. All three detectors
have the first and not the second (2023 validation, average net per trade vs matched random
entries: IDX -4.06% vs -0.53%; US original -3.65% vs -0.60% (superseded by `research/E2/repair_v2/REVIEW.md`); crypto -1.90% vs +1.42%), so their
candidates are PASS until a plan that survives a test exists. The plans are still recorded and
scored, so a rejected name that runs shows up as a missed gain, not as nothing.

Scorer `paper-score-v3` uses Jakarta dates for IDX split events and New York dates for US
events. US verification requires a definite event statement with the exact ratio and matching
effective date (`us-actions-v2`). Proposals, ranges, inverted ratios and undated matches are
unverified; `RATIO_CONFIRMED` is diagnostic only. New repair panels reject v1 schedules and
coverage files; recheck their evidence first. The conservative parser can miss valid events
with unsupported wording, which need further evidence review. Earlier outcomes and research
artifacts retain their original versions; corrections are new records.
