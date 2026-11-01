# Sharpe-kill ablation — report (written after the one run; presentation only)

**Classification: reused-data diagnostic, not independent validation.** Same BTC/ETH daily history as the published
replay. This measures what the permanent negative-90-day-Sharpe kill did on that history. It cannot show that removing
it would improve future returns.

## Answer

**Both, depending on the period, and not reliably either.** Under the reading rule fixed in `PROTOCOL.md` before the run:

| Partition | Effect of the Sharpe kill | End NAV, baseline → without the rule | Max drawdown, baseline → without the rule |
|---|---|---:|---:|
| Development 2017-09 → 2023-01 | **Protected capital** | 20,593 → 17,716 (−2,877) | 15.4% → 27.1% |
| Validation 2023-01 → 2026-09 | **Both**: suppressed returns and protected capital | 12,377 → 19,340 (+6,963) | 11.6% → 30.2% |

- In **development** it fired on 2018-03-15, the same day the trend signal itself exited, so it changed nothing that
  day. Its effect was to block the two later re-entries during the 2018 decline (April–May and July–August), which
  both lost money. Without it, the account was stopped anyway by the 25% drawdown kill on 2018-08-08.
- In **validation** it stopped trading in April 2023 on a 90-day result indistinguishable from zero, and missed the
  late-2023 to early-2024 rally. Without it the account peaked near 27,700 in March 2024, then gave back 30% and was
  stopped by the drawdown kill on 2024-08-03.
- So it helped once and cost a lot once. Two historical windows cannot establish which effect would dominate.

**Removing it does not rescue the strategy.** Without the Sharpe rule, the trend account still trails conventional
buy-and-hold in both windows (with much smaller drawdowns), and in development roughly ties the passive control, which
was only about 45% invested because of the capacity cap. With either kill, the account ends up permanently in cash for
years: about 4.4–4.8 years in development and 2.2–3.4 years in validation.

## Annotated timeline

`RECORDED` = the published baseline, reproduced exactly. `DIAGNOSTIC` = the challenger (same engine, Sharpe trigger
disabled). Both accounts are identical, event for event, until the baseline's Sharpe kill.

### Development (10,000 USDT on 2017-09-26)

| Date | Arm | Event |
|---|---|---|
| 2017-09-26 | both | Start, all cash. Trend entries follow from the SMA10/40 signal. |
| 2017-12-25 | both | Sharpe rule first able to fire (90 daily returns available). |
| 2018-01-14 | both | Account peak, 24,300 (daily open mark). |
| 2018-03-15 | RECORDED | Sharpe kill: 90-day mean −0.011%/day (t ≈ −0.06), account +105.6%, drawdown 15.4%. No pending intents to cancel. |
| 2018-03-16 | RECORDED | Liquidation at the next open: sold 0.729 BTC at 8,236.86. Cash for the remaining 1,753 days. |
| 2018-03-16 | DIAGNOSTIC | No kill, but the trend signal itself exited the same day: the challenger sold the same 0.729 BTC at the same open (its own signal decision for 2018-03-14). The two accounts stay identical in cash until the challenger re-enters. |
| 2018-04-21 → 2018-05-25 | DIAGNOSTIC | Re-entry 1 (first NAV difference on 2018-04-21). NAV 21,397 on May 1, 19,462 by June 1. |
| 2018-07-20 → 2018-08-08 | DIAGNOSTIC | Re-entry 2. NAV 19,595 on Aug 1. |
| 2018-08-08 | DIAGNOSTIC | 25% drawdown kill observed at the open (25.2% from the January peak); one pending BTC buy cancelled. |
| 2018-08-09 | DIAGNOSTIC | Liquidation at the next open: sold 1.062 BTC at 6,280.13. Drawdown reached 27.1%. Cash for the remaining 1,607 days. |

### Validation (10,000 USDT on 2023-01-01)

| Date | Arm | Event |
|---|---|---|
| 2023-04-01 | both | Sharpe rule first able to fire. Its first 21 checks are positive. |
| 2023-04-22 | RECORDED | Sharpe kill on the 22nd check: 90 returns summed to −0.025% (t ≈ −0.001), account +21.8%, drawdown 11.6%. |
| 2023-04-23 | RECORDED | Liquidation at the next open: 0.257 BTC at 27,802.94 and 2.805 ETH at 1,873.23. Cash for the remaining 1,257 days. |
| 2023-04-23 | DIAGNOSTIC | Keeps trading; NAV first differs here. |
| 2023-05 → 2023-09 | DIAGNOSTIC | Whipsaw: NAV 12,765 → 11,082. |
| 2023-10 → 2024-03 | DIAGNOSTIC | Rally: NAV 11,224 (Oct 1) → peak 27,709 on 2024-03-12. |
| 2024-03 → 2024-08 | DIAGNOSTIC | Give-back: 25,521 (Apr 1) → 21,041 (Aug 1). |
| 2024-08-03 | DIAGNOSTIC | 25% drawdown kill observed at the open, already at 28.7% (the drop jumped past 25% between daily opens). Cancelled a pending BTC buy and a pending ETH **sell** due at that open, so that de-risking sale waited one more session for the liquidation. |
| 2024-08-04 | DIAGNOSTIC | Liquidation at the next open: 0.177 BTC at 60,667.64 and 2.975 ETH at 2,902.20. Drawdown reached 30.2%. Cash for the remaining 788 days. |

**The "25%" drawdown stop actually stopped at 27.1% and 30.2%.** It is checked only at daily opens and liquidates at
the following open, so it is not a loss cap.

## Full comparison

| | Dev baseline | Dev without Sharpe kill | Val baseline | Val without Sharpe kill |
|---|---:|---:|---:|---:|
| Ending NAV (from 10,000) | 20,592.77 | 17,716.06 | 12,377.20 | 19,340.00 |
| Total growth | +105.9% | +77.2% | +23.8% | +93.4% |
| Annualised growth | 14.7% | 11.5% | 5.9% | 19.2% |
| Sampled max drawdown | 15.4% | 27.1% | 11.6% | 30.2% |
| Annualised Sharpe (whole window) | 1.15 | 0.81 | 0.52 | 0.86 |
| Days invested | 144 of 1,923 | 199 of 1,923 | 89 of 1,368 | 388 of 1,368 |
| Annualised vol while invested | 45.3% | 45.3% | 48.7% | 44.4% |
| Fills / fees (USDT) | 228 / 88.69 | 321 / 193.29 | 180 / 76.78 | 693 / 482.69 |
| Stopped by | Sharpe kill 2018-03-15 | Drawdown kill 2018-08-08 | Sharpe kill 2023-04-22 | Drawdown kill 2024-08-03 |
| Days the removed rule would have fired | — | 224 (5 runs) | — | 294 (10 runs) |

### Benchmarks from the published run (different risk policies)

| | Dev ending NAV | Dev max drawdown | Val ending NAV | Val max drawdown |
|---|---:|---:|---:|---:|
| Cash | 10,000 | 0% | 10,000 | 0% |
| Passive 50/50, same kills | 17,844 | 27.6% | 15,038 | 19.5% |
| Conventional buy-and-hold, no kills | 24,501 | 71.7% | 36,220 | 57.6% |

- **Passive 50/50, same kills** buys once and holds, with the same two kills as the baseline. In development its first
  entry was capacity-limited, so it was only about 45% invested; it was stopped by the drawdown kill on 2018-02-03. In
  validation it was stopped by the Sharpe kill on 2023-06-16.
- **Conventional buy-and-hold** has no kills at all: much higher returns here, with drawdowns of 57–72%.
- **Cash** earns nothing in this model (no interest).

## What this does and does not show

- **Shows:** on this history the Sharpe kill behaved like a coin flip on timing. Its triggers were statistically
  indistinguishable from zero, and the outcome depended on what the market did next.
- **Does not show:** that removing it would improve future returns; that the trend signal works; or anything about
  live execution. Both partitions reuse data already examined by earlier KOD work.
- **Caution on the validation gain:** it comes from one rally (Oct 2023 – Mar 2024) captured by a strategy that then
  gave back 30%.

## Reproduce

```sh
# inputs: the 220 URLs in historical/original_input_metadata/input_allowlist.json, each checked against its pinned SHA256,
# placed under DIR/raw/<key>, plus input_allowlist.json and original_spot_manifest.jsonl in DIR
cd handoff/ace-integration-20261101/historical
PYTHONPATH=../offline_guard python3 -B historical_shared_account_replay_20261101/replay.py --run-reviewed-historical \
  --clearance historical-independent-audit/REVIEW_CLEARANCE.json --inputs DIR --output-dir BASE   # baseline
cd ../sharpe_kill_ablation_20261101
PYTHONPATH=../offline_guard python3 -B run_challenger.py --engine challenger_engine --inputs DIR \
  --output-dir CHAL --label challenger_sharpe_kill_disabled                                       # challenger
python3 -I -B compare.py --baseline-dir BASE --challenger-dir CHAL \
  --published-engine ../historical/historical_shared_account_replay_20261101 --challenger-engine challenger_engine \
  --json COMPARISON.json --md COMPARISON.md
```

Files: `PROTOCOL.md` (question, single change, reading rule), `CHALLENGER.diff` (the one line), `FREEZE.json` and
`timestamps/` (pre-run hashes; RFC 3161 tokens from FreeTSA and Sectigo, 2026-11-01T23:07:39Z / 23:07:40Z; freeze
commit 7b8bd4f pushed before the run), `results/` (challenger journals gzipped, summaries), `logs/`, `COMPARISON.*`.

## Post-run note on `compare.py`

`compare.py`'s `first_divergence` field reports record 0 for both partitions. That is because each journal's state hash
includes the engine's file hashes, which differ by design. Comparing operation ids and results instead, the first
difference is `daily:2018-03-15` (development) and `daily:2023-04-22` (validation), the baseline's kill days, where only
the `kill` field differs. No other reported metric depends on this field. The frozen script was not edited.
