# E2-US repair: handoff to Hermes (v1, 2026-10-08)

**Verdict: PARTIALLY REPAIRED — SPECIFIED LIMITATIONS.** Exact reproduction of the original run
is established; the mechanical repair is complete and reproducible from archived inputs; the
remaining limitations (section 8) are measurement assumptions that no rerun on this data can
remove. Tests passing shows the software does what it states; it is not independent scientific
validation. The repaired numbers below await your independent check.

What the evidence supports: on 2023 US validation data, buying G2_RET30 flags at the next open
and holding five sessions lost more than matched random entries under every repaired variant.
Original −3.65% vs −0.60%; repaired −4.85% vs −1.13% (fill model A, ex post) and −4.41% vs
−1.21% (fill model B, decision-time). The original direction holds and the gap widens. Nothing
here is evidence of a profitable rule.

## 1. Starting point and scope

- Starting commit `1420ee68ac1da2f063bfaf96a1bd374701f23a05`, identical to your reviewed base.
  Remote `hermes/us-data-repair-v1` points at the same commit and carries no changes.
- Your handoff `HERMES_REPAIR_HANDOFF_v1.zip` (sha256 `66aa18d4…`) reached this session through the
  user; all 16 files matched its MANIFEST.json. Kept under `hermes_handoff_v1/`.
- Scope: E2-US 2023 validation only. Detector MOONSHOT_E2_US_D1 v1 (G2_RET30, frozen in `e5a1be2`),
  its threshold, $5,000 notional, entry at the next open, 5-session hold, `profiles.US` cost
  schedule, overlap rule, 200 draws, seeds 20261007 / 20261008: all unchanged. No 2024+ return,
  outcome or price was computed or inspected (exposure accounting in section 9).

## 2. Original inputs: located, verified, retrievable

| Check | Result | File |
|---|---|---|
| 5,705 Yahoo payloads vs `yahoo_us-20261008T001812Z.jsonl` | 5,705 present, 0 missing, 0 hash or size mismatch; manifest hash equals the panel manifest's input hash | `inputs_verification.json` |
| 2 Nasdaq Trader listing files vs `us_universe-20261008T001213Z.jsonl` | 2/2 | same |
| Panel `panel_us-20261008T004105Z.csv.gz` | sha256 `e5b52674…` = manifest = run record | same |
| Run `20261008T060443Z_MOONSHOT_E2_US_D1_v1` files vs `RUNS.jsonl` | 4/4 | same |
| Original code `826ec76` on the verified panel | `trades.csv.gz` and `random_draws.csv` byte-identical; summary identical except run id/time | `reproduction_v1.json` |
| Panel rebuilt from the payloads with `826ec76` | decompressed CSV byte-identical (`8714fa1f…`); file hash differs only by the name gzip embeds | same |
| Repair code with default options on the original panel | byte-identical to the original run | `contract_check_v1.json` |

Access: Git LFS objects in this private repository (`data/archive/`), fetched explicitly; a fresh
clone was tested end to end (pull, `sha256sum -c`, extract, `verify_inputs.py` → ALL ORIGINAL
INPUTS PRESENT AND MATCHING). Instructions and checksums: `data/archive/README.md`
(inputs, 108 MB + 200 MB) and `data/archive/e2_us_sec_evidence_v1/README.md` (SEC responses,
150 MB). No credential is stored anywhere. A fresh Yahoo download is a different dataset.

## 3. Reconciliation with your repair

### Incorporated

| Correction | Where |
|---|---|
| Causal preprocessing: no row deleted because a later bar reverts (`_finish` → panel-global-v2; legacy kept as `_finish_legacy_v1`) | your code, imported unchanged in `c027601`; used by the repair panel and by paper scoring |
| `price_units.py` split-only conversion, fail-closed | `c027601`; used by paper scorer v2 |
| Paper `score(..., price_units=)`: effective-session units, entry and exit tiers at their own sessions | `c027601`; generalised to IDX/crypto and made the production scorer in `8100b81` (an IDX `NameError` in that path fixed) |
| Ex-post opening-volume finding: reproduced, kept as fill model A, labelled | `d8d2e25`; alternative B in `d8d2e25`/`bcb89f0` |
| As-traded units in the harness: sizing, entry and exit tiers, participation cap, price band | `d8d2e25` |
| Split schedule with SEC corroboration; provider conventions established | `d8d2e25`, `c9d40ab`, `7ed5782`, `511d63e`; `conventions.json` |
| Unrecorded-split coverage of large 2023 jumps | `b29a3fb`, `5acb768` |
| Original-input access and exact reproduction | `10d33fe`, `836e035`; section 2 |
| Version-aware reproduction of your three source findings (legacy fails, repaired passes) | `reproduce_source_findings_v2.py` + `.out.json` |
| Live decisions pinned to the legacy preprocessing by name, recorded per call | `d8d2e25` |

### Available locally but not merged

None of the six source files you delivered remain unmerged. Your
`audit/reproduce_source_findings.py` is archived unchanged; it targets the legacy behaviour and
now fails against the merged code by design (as you noted); the v2 script replaces it for
review. Anything in your local tree that was not in the zip has not been seen here.

### Outstanding defects and unresolved assumptions

1. Survivorship: the universe is the 2026-10-08 listing; names delisted earlier are absent. No
   free point-in-time US price source was found (Yahoo and the current FMP plan return nothing for
   delisted names). Unfixable on this data.
2. Fill model A is an ex-post capacity filter: 224 of R1's 1,092 scored trades are accepted only
   because of the entry session's final volume. Model B removes that dependence but daily bars
   still cannot prove an opening fill at size (the "open" is the first print, time unknown).
3. Costs are assumed by price tier, not measured spreads; sub-$5 names after a +30% day likely
   trade wider, which would make the repaired results worse, not better.
4. Split corroboration is regex-based: VERIFIED = ratio and session stated in a filing;
   RATIO_CONFIRMED (92) takes the session from the provider, and can come from a proxy that lists
   the ratio as the top of a range. The session convention (09:30 New York = first new-units
   session) is shown on AMZN, GE and SNDL only.
5. Quarantine (228 names) uses post-window corporate-action information as a measurement-validity
   filter, symmetric for both sides. It changes the population; R1b (no quarantine) bounds the
   effect (−5.27% vs −1.32%).
6. 136 provider records are non-split price adjustments (spin-offs, stock dividends) and are not
   verifiable as share counts; their names are quarantined in R1 and accepted in R1b.
7. The retrospective reverting-spike flag is kept as a flag only; no repaired rule trade touches a
   flagged session (R1 `qa_sensitivity`).
8. The SEC User-Agent is a placeholder contact; set `IDXSIG_SEC_USER_AGENT` for routine use.
9. IDX paper scoring has no independent corporate-action source: an IDX split inside a window
   makes that outcome UNSCORABLE.
10. Panels earlier than 2023-01-03 carry unit factors from unverified provider records; they are
    used only for return-based features, never for price levels.

## 4. What the repair changed

| Defect | Original | Repaired |
|---|---|---|
| Preprocessing | a bar is deleted if the next bar reverts it (future information rewrites the past) | every bar kept; the old test survives only as `qa_reverting_spike`, known one session later, never an input |
| Price units | price levels rescaled by every later split (a $0.30 stock seen at $300) | `unit_factor` restores the price as traded that session; returns stay on adjusted prices |
| Cost tiers | at rescaled entry/exit prices | at as-traded entry price and as-traded exit price, each at its own session |
| Sizing | whole shares of the rescaled price; 154 attempts SKIP_LOT | whole shares at the price paid; SKIP_LOT 0 |
| Liquidity cap | shares vs final entry-session volume (both rescaled) | same model A in as-traded shares; model B from the 20 sessions up to the signal |
| Price band for matching | rescaled price | as-traded price at the signal session |
| Split evidence | none | 1,594 provider records: 1,221 VERIFIED + 92 RATIO_CONFIRMED accepted; 415 large jumps checked for unrecorded splits |
| Paper scoring | price-ratio scale (inferred units) | provider records corroborated by SEC; UNSCORABLE with reason otherwise; revisions linked |

## 5. Results (`results_v1.json`)

| Run | What | Signals | Attempted | Scored | Rule avg | Matched random (95% of draws) | Rule − matched | Same-session random |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| original | as recorded | 1,676 | 1,496 | 1,099 | −3.65% | −0.60% (−1.74 .. +0.70) | −3.05 | +0.16% |
| R1c | + causal preprocessing | 1,683 | 1,503 | 1,101 | −3.75% | −0.62% (−1.68 .. +0.64) | −3.12 | +0.11% |
| R1b | + as-traded units | 1,683 | 1,479 | 1,228 | −5.27% | −1.32% (−2.24 .. −0.35) | −3.96 | −0.06% |
| **R1** | + quarantine (primary, fill A) | 1,468 | 1,286 | 1,092 | **−4.85%** | **−1.13% (−2.10 .. −0.01)** | **−3.73** | −0.08% |
| R2 | R1 with fill model B | 1,468 | 1,324 | 880 | −4.41% | −1.21% (−2.24 .. −0.22) | −3.20 | −0.10% |

Original values verified from the frozen artifacts: rule −3.6498978% (mean of 1,099 scored net
returns); matched random −0.5960706% (mean over 200 draws of each draw's average). In every row
the rule is below every one of the 200 matched draws (one-sided p = 1.0 for "rule better").
The earlier erratum's −4.47% re-costed previously selected trades; it is superseded by these
full reruns.

## 6. Denominators (`reconcile_original_vs_R1.json`, `reconcile_R1_vs_R2.json`)

Original → R1, every signal accounted for (0 unexplained):

- 1,461 signals in both runs.
- 215 only in the original: 214 in quarantined names, 1 whose previous close changed once a
  legacy-deleted bar was restored.
- 7 only in R1: 4 on bars the legacy step had deleted, 3 whose previous close changed.
- Status changes for signals in both: SKIP_LOT → EXITED 96, SKIP_LOT → SKIP_OVERLAP 19 (an earlier
  signal now fills and holds the name), SKIP_LOT → INCOMPLETE 2, SKIP_LOT → SKIP_LIQUIDITY 2,
  SKIP_NOT_TRADED → SKIP_LIQUIDITY 1.
- Unchanged statuses still change net returns where the as-traded price moves the cost tier.

R1 → R2 (same 1,468 signals): EXITED → SKIP_LIQUIDITY 224, SKIP_OVERLAP → SKIP_LIQUIDITY 27,
INCOMPLETE → SKIP_LIQUIDITY 13, SKIP_OVERLAP → EXITED 11, SKIP_LIQUIDITY → EXITED 3, and 4 others.
The 224 fills accepted only on final volume averaged −7.03% (median −10.9%); the 866 filled under
both models averaged −4.32%.

Matched baseline: same method and seeds; its pools change with the evaluable set (quarantined
names leave both sides) and its costs change with as-traded tiers.

## 7. Execution-model sensitivity (B)

FILL-B-v1 is a stated alternative, not a hidden replacement: capacity from information at the
decision (median as-traded volume of the 20 sessions up to the signal, listed no-trade days as
zero); an opening price and a bar with volume on the entry session. It is more restrictive
(880 scored) and does not change the conclusion. Daily bars do not prove executable opening
liquidity under either model.

## 8. Remaining limitations

Section 3, "Outstanding". In short: survivor-only universe, assumed costs, daily bars, regex
corroboration of splits, quarantine as a post-window validity filter.

## 9. Information exposure

- Your recorded deviation stands: the original panel manifest's QA block lists several 2024+
  price examples; they were read during your manifest inspection, not used for tuning. Zero
  post-2023 exposure cannot be claimed. That manifest was written by the original E2 build in
  this project; whether its author's session displayed those rows is not established.
- This repair loaded the original payloads (which contain 2024–2026 bars) and filtered to
  2023-12-29 or earlier before any computation; the repair panel reads nothing later
  (`read_through`). Verification hashed files without parsing prices.
- Corporate-action metadata dated 2024–2026 was used, as the request allows, to restore 2023
  units: provider split records and SEC filing texts (machine-read for ratio and date). A few
  such records (ticker, effective date, ratio, filing form and date) were printed while checking
  parser quality. No 2024+ price, return or outcome was printed or computed.
- The E2 protocol's holdout runs 2024-01-01..2026-12-31; the prospective paper ledger (October
  2026) records calls inside that calendar window. They are frozen before outcomes and never used
  for design, but they are not "untouched holdout" either.

## 10. Reproduce

From `idx-signals/`, after fetching and extracting both archives (section 2):

```sh
python3 research/E2/repair/verify_inputs.py
python3 -m idxsig run --market US --rule MOONSHOT_E2_US_D1 --start 2023-01-01 --end 2023-12-31 \
    --panel data/manifests/panel_us-20261008T004105Z.json --no-commit          # original contract
# split schedule and coverage, offline from the archived SEC responses
python3 -m idxsig us-actions --raw-manifest data/manifests/yahoo_us-20261008T001812Z.jsonl \
    --effective-after 2023-01-03 --universe-end 2023-12-29 --user-agent offline \
    --cache-dir data/raw/sec/20261008T091626Z --offline
python3 -m idxsig us-actions ... --recheck <first-pass us_splits-*.json> --offline ...
python3 -m idxsig us-coverage --raw-manifest data/manifests/yahoo_us-20261008T001812Z.jsonl \
    --start 2023-01-03 --end 2023-12-29 --user-agent offline --cache-dir data/raw/sec/20261008T091626Z --offline
# or use the committed us_splits-20261008T093909Z.json and us_splits-coverage-20261008T094836Z.json
python3 -m idxsig build-us-repair-panel --manifest data/manifests/yahoo_us-20261008T001812Z.jsonl \
    --schedule data/corporate_actions/us_splits-20261008T093909Z.json \
    --coverage data/corporate_actions/us_splits-coverage-20261008T094836Z.json --end 2023-12-29
P=data/manifests/panel_us_repair-<stamp>.json      # the committed one: panel_us_repair-20261008T095321Z.json
R="python3 -m idxsig run --market US --rule MOONSHOT_E2_US_D1 --start 2023-01-01 --end 2023-12-31 --panel $P --no-commit"
$R --units as_traded --fill-model A --quarantine unit_schedule     # R1
$R --units as_traded --fill-model A --quarantine none              # R1b
$R --units panel     --fill-model A --quarantine none              # R1c
$R --units as_traded --fill-model B --quarantine unit_schedule     # R2
python3 research/E2/repair/reconcile.py results/runs/20261008T060443Z_MOONSHOT_E2_US_D1_v1 <R1 dir> $P
python3 research/E2/repair/reproduce_source_findings_v2.py
python3 -m unittest discover -s tests                                # 159 tests
```

Environment of record: Python 3.13.16, pandas 3.0.5, numpy 2.5.3 (`reproduction_v1.json`). The
repair panel file hash (`8d3b7ce4…`) should reproduce exactly with the same versions.

## 11. Tests

`test_output_v1.txt`: 159 tests, all passing: the 130 present after importing your files, and 29 new ones for this repair
(as-traded units, split boundaries, exit-session tiers, fill models A and B, rule invisibility of
unit factors, split evidence parsing, coverage, quarantine on both sides, scorer v2, linked
revisions, pinned live preprocessing). They establish software behaviour on synthetic data only.

## 12. Forward collection

Live scans keep running (IDX, US, crypto routines) under unchanged detectors and policy
PAPER-POLICY-v3; every call now records its preprocessing; scoring uses `paper-score-v2`;
corrected outcomes are appended as linked revisions; nothing earlier is edited. First outcomes
are due 2026-10-14 (crypto) and after the 2026-10-15 close (IDX, US).

## 13. What this does not license

The repaired E2-US result is a reproduced mechanical correction, not a validated finding: it
still awaits your independent review, and its population is survivor-only. Early-precursor work
should start from a separately frozen dataset and contract and must not take these numbers as
premises.
