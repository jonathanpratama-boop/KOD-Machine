# Sharpe-kill ablation — report (written after the one run; presentation only)

**Classification: reused-data diagnostic, not independent validation.** Same BTC/ETH daily history as the published
replay. This measures what the permanent negative-90-day-Sharpe kill did on that history. It cannot show that removing
it would improve future returns.

## Answer

**It protected capital in both periods and suppressed returns in one, and both effects are fragile.** Under the reading
rule fixed in `PROTOCOL.md` before the run:

| Partition | Effect of the Sharpe kill | End NAV, baseline → without the rule | Max drawdown, baseline → without the rule |
|---|---|---:|---:|
| Development 2017-09 → 2023-01 | **Protected capital** | 20,593 → 17,716 (−2,877) | 15.4% → 27.1% |
| Validation 2023-01 → 2026-09 | **Both**: suppressed returns and protected capital | 12,377 → 19,340 (+6,963) | 11.6% → 30.2% |

- In **development** it fired on 2018-03-15, the same day the trend signal itself exited, so it changed nothing that
  day. Its effect was to block the two later re-entries during the 2018 decline (April–May and July–August), which
  both lost money. Without it, the account was stopped anyway by the 25% drawdown kill on 2018-08-08.
- In **validation** it stopped trading in April 2023 on a 90-day result indistinguishable from zero, and missed the
  late-2023 to early-2024 rally. Without it the account first fell up to 1,461 USDT below the baseline in the mid-2023
  whipsaw (20.5% below the shared February 2023 peak), then peaked near 27,700 in March 2024, gave back 30% from that
  new peak, and was stopped by the drawdown kill on 2024-08-03.
- **On ending NAV the rule helped once (+2,877 in development) and cost a lot once (−6,963 in validation).** Two
  historical windows cannot establish which effect would dominate.

**How fragile it is** (independent skeptic check):
- The development "protection" is mostly the 25% stop's arithmetic. About 2,362 of the 2,877 gap is simply the
  baseline's remaining distance to the 25% line; the rest is overshoot past it. Once the challenger hit the stop, the
  "protected" label was certain. Neutralising its two worst days after the divergence (2018-04-26 and 2018-08-01) would
  flip both legs of that label. Its first re-entry was briefly 2,457 ahead of the baseline (May 2018) before giving it
  back.
- The validation "suppressed returns" rests on one rally. Removing its 5 best days (of 470 after the divergence) would
  leave it below the 1,000 USDT threshold. Its "protected capital" leg holds either way (+8.95 pp even from the shared
  peak).

**Removing it does not rescue the strategy.** Without the Sharpe rule, the trend account still ends below conventional
buy-and-hold in both windows on ending NAV, with much smaller drawdowns; on whole-window Sharpe it beats buy-and-hold
in development (0.81 vs 0.59) and trails in validation (0.86 vs 0.94). In development it ties the passive control
(17,716 vs 17,844), but mechanically: both were stopped by the same 25% kill from similar peaks. With either kill, the
account ends up permanently in cash for years: about 4.4–4.8 years in development and 2.2–3.4 years in validation.

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
| Fills after the true divergence (baseline kill day) | 1 | 94 | 2 | 515 |
| Days the removed rule would have fired while the account could still trade | — | 134 | — | 204 |

### Benchmarks from the published run (different risk policies)

| | Dev ending NAV | Dev max drawdown | Val ending NAV | Val max drawdown |
|---|---:|---:|---:|---:|
| Cash | 10,000 | 0% | 10,000 | 0% |
| Passive 50/50, same kills | 17,844 | 27.6% | 15,038 | 19.5% |
| Conventional buy-and-hold, no kills | 24,501 | 71.7% | 36,220 | 57.6% |

- **Passive 50/50, same kills** buys once and holds, with the same two kills as the baseline. In development its first
  entry was capacity-limited, so it was only about 45% invested; it was stopped by the drawdown kill on 2018-02-03. In
  validation it was stopped by the Sharpe kill on 2023-06-16, the very rule this study removes, so it is not a neutral
  comparator there.
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

## Post-run notes on `compare.py`

- `first_divergence` reports record 0 for both partitions. That is because each journal's state hash includes the
  engine's file hashes, which differ by design. Comparing operation ids and results instead, the first difference is
  `daily:2018-03-15` (development) and `daily:2023-04-22` (validation), the baseline's kill days, where only the `kill`
  field differs. For the same reason its `*_fills_after_divergence` fields are just totals; the corrected counts are in
  the table above. Additional fills (93 and 513) are unaffected.
- Its count of days the removed rule "would have fired" (224 and 294) includes 90 days after each challenger's own
  drawdown kill, when the account was permanently flat. The table above uses 134 and 204.
- No reading-rule input depends on either field. The frozen script was not edited.

## Independent verification (after the run)

Three independent checks, run read-only:
- **Re-derivation from raw journals**, without using `compare.py`: every ending NAV, growth, drawdown, fill count, fee
  total, invested-day count, kill and liquidation matched `COMPARISON.json` exactly. The validation ending NAV landing
  almost exactly on 19,340 is a coincidence of the arithmetic.
- **Freeze audit:**
  - the engine differs in exactly one line;
  - every `FREEZE.json` hash matches commit `7b8bd4f`, and no frozen file changed afterwards;
  - both RFC 3161 tokens verify offline against the pinned CAs (FreeTSA 23:07:39Z, Sectigo 23:07:40Z), and a zero-digest
    negative control fails as it should;
  - the provenance pins in every challenger journal row match the challenger engine.

  The challenger outputs were created 38 seconds after the later timestamp, by local file times. The tokens prove the
  freeze existed by then; they cannot prove the outputs did not.
- **Skeptic review:** found no unfairness. The arms are identical through the baseline kill day. It corrected the
  wording now used above: protection in both partitions; the fragility; drawdown peaks; stop overshoot; the benchmark
  caveats.

Disclosure: `PROTOCOL.md` was last written at 23:03, before the harness check and the compare self-test it describes
had finished (both completed and passed before the 23:07 freeze; logs in `logs/`).
