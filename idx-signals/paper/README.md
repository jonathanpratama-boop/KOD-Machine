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

`PAPER-POLICY-v5` (drafted 2026-10-09 in PR #3 as "v4" and renamed when PR #6's v4 reached the
base branch first; prospective: decisions already recorded keep their policy) applies
Jonathan's risk constraint in every market. The invalidation is defined first (the signal session's
low, floored to the tick). The highest permitted entry follows from it (stop / 0.95, never above the
signal close x 1.10), so the stop is at most 5% below any accepted fill. Size, costs and caps are
computed at that permitted entry (hypothetical accounts: $10,000, Rp100m, 10,000 USDT). An entry
outside the band is rejected, never chased: a $100 signal with a $95 stop accepts an open of at
most $100, and an open of $110 is rejected. US plans and outcomes run through `idxsig/exec_us.py`
(EXEC-US-v1, scorer `paper-score-v4`), the same code as the historical replay: entry at the next
open, a resting stop (filled at the stop, or at the open on a gap through it), a market-on-close
time exit placed in advance, and costs at each fill's as-traded price. IDX and crypto keep the v3
entry and close-based exit scoring inside the v5 band (a known limitation). v5 does not use
v4's E3 rule: while a validated E3 pair exists, the IDX scan fails instead of deciding, because
v5 does not define how a plan without a chase limit meets the 5% stop rule. Approval is
`APPROVAL-v2`. Each market's evidence is pinned to one run and its config sha256
(`paper.APPROVAL_PINS`), so appending a run cannot change it. The pinned run must have tested the
execution the plans use. It must also beat matched entries at p < 0.05 with a positive average
net return above the baseline. US has no pin yet, because no evidence run exists under EXEC-US-v1.

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

## Speculation register (`paper/speculations.jsonl`, `idxsig.speculation`, protocol `research/SPECULATION_REGISTER_v1/`)

Added 2026-10-28 (`KOD-SPEC-REGISTER-v1`). Speculative design applied to the ledger: for every candidate of the frozen
detectors, before its entry, a **speculation set** is sealed (hash-chained, RFC 3161 stamped, pushed) with a cone of dated,
falsifiable statements about the next 5 and 20 sessions, each with the probability the frozen 2023 evidence gives it; the
frozen plan (`BASE5`) applied to the candidate and to five matched twins drawn from the scan's own features file; and a tag.
When the bars arrive, each statement is graded (Brier, beside an uninformed 0.5 and the register's running base rate, and
beside the twins' rate) and the plan is scored against its twins. It **never feeds a decision**, carries **no variant of a
retired entry** (owner decisions of 2026-10-17 and 2026-10-22: descriptive logging only), reads no holdout and places no
order. A set sealed after its entry cutoff is refused; `paper-verify` checks every cutoff, every binding to the ledger and
the chain. `paper/SPECULATIONS.md` is the derived report (statistics, calibration, the latest sets as cards).

```sh
python3 -m idxsig speculate --market <M> --commit        # after paper-scan, before the entry cutoff
python3 -m idxsig speculate-score --market <M> --commit  # after paper-score; reuses its bars (--max-age-hours 8)
python3 -m idxsig speculate-report                       # rewrites paper/SPECULATIONS.md
```

## Catalyst register (`paper/catalysts.jsonl`, `idxsig.catalysts`, protocol `research/CATALYST_REGISTER_v1/`)

Added 2026-10-28 (`KOD-CATALYST-REGISTER-v1`, the owner's go on `handoff/precatalyst-program/PROGRAM_v1.md`). The
speculation register run over dated **event lists** instead of scan candidates. **SEC13D** (counted at its looks): every
original Schedule 13D on EDGAR is listed in a `BATCH` record with a status; each one that passes the issuer rules gets a
`CATALYST_SET` sealed before the next US open, with the 20-session yardstick plan (`H20`), five matched event-free twins,
a cone and a coverage class: `FIRE`, or `ABSTAIN` when the issuer filed for dilution in the last 20 sessions, already rose
15% since the filing, or is worth under USD 50 million. The test runs on FIRE sets only, with two primaries (mean edge
over the twins, and the win rate against the twins' median), at 60/120/240 pairs (t at least 3.75, 3.0, 3.0) and then
480/960/1,920 (t at least 3.0), with a futility stop from 240 (`research/CATALYST_REGISTER_v1/prereg_2.json`). **IDX_INDEX** (descriptive): IDX30/LQ45/IDX80 changes from a sourced events file, with a run-up window to the
rebalancing close and a 20-session window after it. **DILUTION_RECENT** tags are sealed for new US and IDX speculation sets
before their cutoff (metadata only). It never feeds a decision, reads no holdout, places no order and changes nothing in
`ledger.jsonl` or `speculations.jsonl`; `paper-verify` checks its chain, cutoffs, batch listings and bindings.
`paper/CATALYSTS.md` is the derived report. EDGAR needs the declared contact inline (`KOD_SEC_CONTACT=...`), never a file.

```sh
python3 -m idxsig catalyst-seal --family SEC13D --commit          # after paper-scan --market US, before 09:15 New York
python3 -m idxsig catalyst-seal --family IDX_INDEX --events research/CATALYST_REGISTER_v1/events/<file> --commit
python3 -m idxsig catalyst-tag --commit                            # after speculate, before the set's cutoff
python3 -m idxsig catalyst-score --market <US|IDX> --commit        # after paper-score; reuses its bars
python3 -m idxsig catalyst-report                                  # rewrites paper/CATALYSTS.md
```

## Crypto microstructure side-car (`paper/microstructure/`, `idxsig.microstructure`)

Added 2026-10-21. It measures what the frozen crypto cycle assumes, for the same candidates, and **never feeds a
decision**: it reads the ledger, changes no rule, no policy field and no ledger line. `IDXSIG_MICRO=0` switches it off.
- `BOOK` (forward only): right after each crypto scan, the Binance spot order book (1000 levels a side, from
  data-api.binance.vision) for every candidate: spread, depth within 1/2/5% of the mid, the average price of a market buy and
  sell of USD 100 / 1,000 / 10,000 and of the plan's own position sizes. The fee is recorded apart from the slippage. A book
  counts as "at decision time" only if taken within 900 s of the decision.
- `TIMELINE`: the candidate's 1-minute bars for the signal day plus the next 24 h, built 26 h after the day ended (history is
  rebuilt with `micro-catch-up`, flagged `retrospective`): the minute the close first crossed +10/20/30%, the peak, the give-back,
  the last hour, the path after the close. Descriptive; the candidates are the ledger's own, so it adds no independent sample.
- Records are hash-chained in `crypto.jsonl` (the ledger's mechanism); raw responses/bars sit in `raw/` with their sha256 in
  the record. `python3 -m idxsig micro-report` prints the statistics and checks every hash.
