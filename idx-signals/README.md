# IDX signals

Test harness for daily trading signals on the Indonesia Stock Exchange. Research only. No
entry permission. It runs a frozen rule over every listed name (delisted names included
where the data has them), executes each signal under IDX trading constraints, and compares
the result with random entries on the same sessions. Results are append-only and committed.

**The detector rule is not in this repo yet.** The request read "Implement this rule
exactly: [paste your detector rule]" and the rule was never pasted. Nothing was guessed:
`idxsig/rules/user_rule.py` is an empty slot and `run --rule USER_RULE` refuses to start.
The only committed runs are `PLACEBO_COINFLIP`, a price-blind coin flip that checks the
harness itself:

| Run | Harness | Avg net vs matched | Avg net vs same-session |
|---|---|---|---|
| `20261007T182601Z` | first harness: 2019-07 window, one baseline | (no matched baseline) | -0.16%, p = 0.91 |
| `20261007T190358Z` | review fixes: 2021-01 window, matched controls v1, integer resets as splits, exhaustive lookahead | -0.05%, p = 0.64 | -0.13%, p = 0.82 |
| `20261007T231344Z` | hardening v2: panel v2, corporate-action registry, prefix-first signals, controls v2, quality tiers | -0.13%, p = 0.84 | -0.13%, p = 0.82 |

All three are indistinguishable from random, as a price-blind rule must be. Earlier runs are
kept as they were; runs are never edited. What changed between the last two: one session
fewer (the panel v1 contained a Saturday stub, 2021-05-22, that IDX's own reference prices
ignore; see below), so one signal fewer; 7 trades excluded across resets became 4 (the
Saturday had produced false resets); and the matched controls now match on seven features,
which draws different controls (same seed).

## Commands

```sh
cd idx-signals
pip install -r requirements.txt           # pandas, numpy
python3 -m idxsig fetch-idx-mirror         # IDX daily summaries, pinned commit
python3 -m idxsig fetch-yahoo              # Yahoo daily bars for every universe ticker
python3 -m idxsig build-panel              # canonical panel + QA manifest (a new file each time)
python3 -m idxsig build-ca-registry        # classify every reference reset (a new file each time)
python3 -m idxsig verify-data              # re-hash raw files, panels and registries
python3 -m idxsig rules                    # list rules + source-audit result; USER_RULE shows PENDING
python3 -m idxsig run --rule PLACEBO_COINFLIP
python3 -m idxsig verify-runs              # no past run edited or removed
python3 -m idxsig e1-discovery             # experiment E1 stages (each writes a new research/E1/ directory)
python3 -m idxsig build-global-panel --market US      # US / crypto panels (a new file each time)
python3 -m idxsig e2-discovery --market US            # experiment E2 stages per market
python3 -m idxsig run --market US --rule MOONSHOT_E2_US_D1 --start 2023-01-01 --end 2023-12-31
python3 -m idxsig speculate --market US --commit          # speculation register: seal the cone, plan and twins before the entry
python3 -m idxsig speculate-score --market US --commit    # grade the statements and score the plan against its twins
python3 -m idxsig speculate-report                        # paper/SPECULATIONS.md
python3 -m idxsig run --rule E3_CAND_F7_ARA_VOL3 --start 2021-01-22 --end 2022-12-30 --fill-model C \
    --entry-rule confirm --entry-window 3 --exit-rule stop_ref   # an execution plan (research/E3)
python3 -m idxsig e3-reproduce                        # experiment E3 precondition, then e3-discovery, e3-validation
python3 -m idxsig paper-scan --market IDX --commit    # prospective paper scan of the last session (no orders)
python3 -m idxsig paper-score --market IDX --commit   # score paper decisions whose window has ended
python3 -m unittest                        # 222 tests, synthetic data only
```

## 1. Dataset

| Segment | Source | Sessions | Survivorship |
|---|---|---|---|
| 2019-07-29 .. 2025-02-21 | IDX daily stock summary via the [wildangunawan/Dataset-Saham-IDX](https://github.com/wildangunawan/Dataset-Saham-IDX) mirror, pinned to commit `bc0ac771` | 1,355 | The mirror's first ticker snapshot was taken 2021-01-22 (upstream commit `ca98f653`), holding the names listed that day with history back to 2019-07-29. Names delisted before 2021-01-22 are absent; names delisted after it keep their history (FINN, TURI and RMBA end early). **Backtests start 2021-01-22 by default** for this reason. |
| 2025-02-24 .. 2026-10-06 | Yahoo Finance v8 chart API (`<TICKER>.JK`), split adjustment undone | 382 | Survivor-only. 59 mirror names return not-found from Yahoo and stop at 2025-02-21, as does FISH (see QA). Not-found is not the same as delisted: MAMI, MYRX, NIPS and five others were force-delisted on 2025-07-21, but WSKT is still listed and has been suspended since May 2023. |

Current panel (format v2, `panel-20261007T225823Z`): 1,425,103 rows, 983 tickers, 1,736
sessions. Prices are as traded (integer rupiah), not adjusted, because lots, ticks and
auto-rejection limits apply to traded prices. `previous` is IDX's reference price, which IDX
resets on corporate-action ex-dates. v2 adds IDX's daily `listed_shares` and
`tradable_shares` (mirror era only) and drops dates whose closes IDX's next reference price
ignores: the mirror holds a Saturday, 2021-05-22, with about 110 tiny trades, and on
2021-05-24 IDX priced every name off Friday's close. Kept (as in panel v1, still on record
and still loadable), it turned 61 names into false corporate actions.

**Quality tiers.** Every run reports how many of its sessions fall in each tier and lists
the known limitations of the data:

| Tier | Sessions | Source | Survivorship | Corporate actions |
|---|---|---|---|---|
| TIER_1 | 2021-01-22 .. 2025-02-21 (default window) | IDX mirror | complete | exchange reference + share counts + Yahoo |
| TIER_2 | 2019-07-29 .. 2021-01-21 | IDX mirror | survivor-biased | exchange reference + share counts |
| TIER_3 | 2025-02-24 .. latest | Yahoo | survivor-only | Yahoo split events only (never share-scaled) |

**Provenance.** Every downloaded file has one line in a manifest under `data/manifests/`:
path, source, source URL, upstream repo and commit (mirror), download time (UTC), HTTP
status (Yahoo), size, SHA-256, row count, first and last date, license or terms. Requests
that failed are logged too: the Yahoo manifest records all 62 not-found tickers. Manifests
are never rewritten; a new download is a new manifest. The raw files and the panel are not
committed (about 400 MB, and the IDX data is non-commercial, cite-the-source), so the
manifests are what make a rebuild checkable: `build-panel` refuses to run if any raw file
differs from its manifest hash, and every run records the panel's SHA-256.

**Why not idx.co.id directly.** It sits behind Cloudflare (HTTP 403 from here) and its terms
of use forbid scraping. The mirror republishes the same daily summaries. Stooq refused the
connection; the FMP connector's IDX data needs a higher plan.

**QA recorded in the panel manifest.**

- Yahoo vs IDX on 917,945 overlapping rows: 95.5% of closes identical, 3.8% more than 2%
  apart, almost all in 2019-2022 (rights issues Yahoo treats as splits). That period comes
  from IDX, not Yahoo. At the stitch date 895 of 896 names match exactly; FISH (Yahoo 10x
  IDX) gets no Yahoo segment.
- Closes outside the modelled regular-board limits, per regime: none above ARA before
  September 2023. Of the rest, nearly all are names priced under Rp50 (only possible on
  the acceleration and special monitoring boards, which use 10% limits) and 583 rows at
  about -10% in 2020-2022 (consistent with the acceleration board's 10% limit). Left
  unexplained: 1 row on 2019-09-16, 14 on 2020-03-12, 19 in the Yahoo segment and 2 on
  2026-09-28.
- 10 non-session dates dropped (9 Yahoo holiday stubs, one Sunday row for AALI in the mirror),
  plus 2021-05-22 (reference ignored by IDX, panel v2).

Post-mirror listings come from `data/universe/extra_tickers.csv` (2025 and 2026 IPO lists,
each row with its source URL and retrieval date).

## 2. The rule

`idxsig/rules/user_rule.py` holds `RULE_TEXT` (verbatim), `VERSION`, `HOLDING_DAYS` and
`compute(view)`, which returns a (names x sessions) array of 1 / 0 / NaN (signal / no
signal / not evaluable). The rule hash covers the text and the module source, so any edit
is a new rule version and a new run.

**Causal by construction.** A run calls `compute` once per session d, on a `RuleView`
holding only sessions 0..d and only the names listed by d, and records column d of that
call as the signal at d. Nothing after the close is in the rule's input, so no recorded
signal can depend on it. The view is read-only exchange data (close, reference, high, low,
volume, value, presence, tradeability, limit locks, listed shares); it has no corporate-action
registry or share factors, which are built from later sources. Three more layers:

- **Source audit** (`rules/audit.py`, also run by `idxsig rules` and CI): refuses rule code
  that imports anything but numpy, pandas and a few pure modules; calls `open`, `eval`,
  `getattr` and similar; touches dunder, private or frame attributes or `.base`; uses
  numpy/pandas file I/O; keeps state (`global`, module-level containers, mutable defaults,
  attribute assignment, decorators, classes); or computes anything at import time.
- **Sandbox** (`rules/sandbox.py`): while `compute` runs, an audit hook blocks file reads
  outside the Python installation, any write, network, subprocesses, `sys._getframe`,
  traceback and generator frames, and `gc` heap walks. A rule that swallows the error still
  fails the run.
- **Full-window diagnostic:** one extra call on the whole window; any difference from the
  prefix-built signals (a rule that changes with more data, depends on the number of names
  that will exist, or keeps state) is a `LookaheadError`.

Limits: the audit and the sandbox run in the same Python process as the rule, so they are
not a security boundary. They stop accidental and naive leaks and refuse the obvious routes
around them (the external review of PR #1 found two, both closed: a reference from the view
to the full arrays, and string-based attribute access through allowed modules); a rule written
to defeat them could still do so, so a rule's source is reviewed before its run is trusted.
Recorded signals stay causal regardless, because each view holds copies of sessions 0..d only.

`tests/test_lookahead.py` throws adversarial rules at this: future returns, whole-history
normalisation, a rule that behaves only when truncated, a rule keyed on the future count of
listings (missed by the earlier row-preserving truncation), caches, file reads, import-time
data, closures, frame and heap walks. The placebo takes about 25 seconds over 989 sessions.
`--lookahead-cuts N` (legacy) records the full-window signals and checks N prefixes; the
report says the signals are not causal by construction.

## 3. Execution over the full universe

The universe is every ticker in the panel window on every session where the rule is
evaluable, including names that later stop trading. Execution, per signal:

- Signal from data through the close of session s; buy at the close of s+1. Closes, not
  opens: IDX only reports an opening price for names with a pre-opening auction (~7% of
  rows), so an open-based model would drop most of the universe.
- **Execution plans** (`--entry-rule`, `--entry-window`, `--exit-rule`; `research/E3`): a
  conditional entry waits for a close that confirms the move, dips below the signal close, or is
  the first not locked at ARA, within a window of sessions; a conditional exit sells at the first
  close at or below the signal session's reference price, or at the first down close, else at the
  horizon. Levels are compared on the reference chain, so a corporate-action reset is not a move.
  The default is the model above, and every earlier run reproduces unchanged. A detector run whose
  window touches the sealed holdout (2024-01-02 .. 2025-02-21) is refused unless `--holdout-final`
  names it as the one pre-registered final test.
- **Lots:** whole 100-share lots, `floor(Rp 10,000,000 / (price x 100))`. No lot: skipped.
  At most 10% of the session's volume.
- **Fees:** 0.15% buy, 0.25% sell (commission, levy, VAT, 0.1% final tax on sales). Flags.
- **Auto-rejection:** no buy when the entry close is locked at the upper limit; the sale
  rolls forward while the close is locked at the lower limit or the name is not trading.
  Limits by date:

  | From | ARA | ARB | Source |
  |---|---|---|---|
  | panel start | 35% / 25% / 20% (<= Rp200 / <= Rp5,000 / above) | same | [CNBC Indonesia](https://www.cnbcindonesia.com/market/20250408084106-17-624101/bei-ubah-kebijakan-arb-ini-aturan-terbarunya) |
  | 2020-03-10 | same | 10% | [Bisnis](https://market.bisnis.com/read/20200312/7/1212280/dampak-auto-rejection-bawah-10-persen-terhadap-pasar) |
  | 2020-03-13 | same | 7% | [Tirto](https://tirto.id/bei-ubah-batas-bawah-auto-rejection-jadi-7-eELq) |
  | 2023-06-05 | same | 15% | [CNN Indonesia](https://www.cnnindonesia.com/ekonomi/20230530141054-92-955791/bei-kerek-batas-arb-saham-jadi-15-persen-mulai-5-juni/amp) |
  | 2023-09-04 | same | = ARA | [Bisnis](https://market.bisnis.com/read/20230831/7/1690101/arb-ara-simetris-berlaku-pekan-depan-asosiasi-emiten-sambut-positif) |
  | 2025-04-08 | same | 15% | [Kontan](https://amp.kontan.co.id/news/bei-tetapkan-auto-rejection-bawah-arb-hanya-15-dan-mengubah-batas-trading-halt-8) |
  | 2026-09-28 | same; Rp1-10: +Rp1 | 15%; Rp1-10: -Rp1; floor Rp1 | [Detik](https://finance.detik.com/bursa-dan-valas/d-8682336/bei-ubah-aturan-ara-arb-mulai-hari-ini-cek-rinciannya) |
  | 2027-01-01 | same | = ARA | same |

  The data has no daily board membership, so the 10% limit of the acceleration and special
  monitoring boards ([FCA](https://market.bisnis.com/read/20240315/7/1749731/bei-terapkan-papan-pemantauan-khusus-full-call-auction-25-maret))
  is applied when the bar is one-price or priced under Rp50.
- **Corporate actions** (`idxsig/corporate_actions.py`, `--ca-mode registry`, the default):
  every reference reset in the panel is a row in a versioned registry
  (`data/corporate_actions/ca_registry-<stamp>.csv`, one new file per build, frozen by the
  commit guard, with a manifest naming the exact panel it was read from; a run refuses a
  registry built for another panel). Columns: ticker, effective date, action type
  (STOCK_SPLIT, REVERSE_SPLIT, RIGHTS_ISSUE, STOCK_DIVIDEND, OTHER_REFERENCE_RESET, UNKNOWN),
  ratio, observed reset ratio, listed-shares ratio and lag, source, source timestamp,
  verification status, evidence, notes. Shares held are scaled **only** through a verified
  split, reverse split or stock dividend. VERIFIED_CORROBORATED means IDX's listed share
  count moved by the reset ratio on the day (holders received shares without paying, which a
  rights issue cannot do) with Yahoo not contradicting, or moved by it within 20 sessions
  and a Yahoo split event agrees; VERIFIED_PRIMARY means an issuer/IDX/KSEI document entered
  in `data/corporate_actions/manual.csv` (append-only; empty, because no documents have been
  archived and none are invented). The ratio applied is the declared one, not the reset
  snapped to a fraction. A trade held across a verified rights issue is
  `CORP_ACTION_RIGHTS_ISSUE`; across anything else (unresolved, Yahoo-only after the mirror,
  missing from the registry) `CORP_ACTION_UNRESOLVED`. Neither is scored, for the rule and
  both baselines alike. Current registry: 217 rows; 89 verified share-scaling, 99
  unresolved, 21 single-source (TIER_3), 8 Yahoo events with no reset. The earlier modes
  (`exclude`: every integer reset is a split; `value_preserving`) remain only to reproduce
  older runs: the registry found 13 integer resets whose share count never moved, which
  `exclude` would have scaled. Cash dividends are not added back.
- **Delisting:** a name that stops trading while held is sold at its last traded close
  (`EXIT_DATA_END`), or at zero with `--data-end-exit zero`. Counted in every report.
- **Overlap:** a new signal in a name already held is skipped and logged.

The default window is TIER_1, 2021-01-22 .. 2025-02-21, where the universe includes the
names that later delisted. An earlier start or a later end is allowed; the report states the
tier of every session and warns for each TIER_2 / TIER_3 segment.

## 4. Random baselines

For each attempted signal, each of 200 draws picks a replacement name on the same session
from the names where the rule was evaluable, and runs it through the same execution and
holding period. Each draw is a portfolio with the rule's size and dates. Two baselines:

- **Matched (primary), controls v2** (`idxsig/controls.py`). The replacement comes from
  names in the same buckets as the signalled name that session, in priority order: price
  band (<= Rp200, <= Rp5,000, above); quintile of 20-session median traded value; quintile
  of market cap (close x IDX listed shares; unknown in TIER_3); tercile of 20-session
  volatility; tercile of the preceding 20-session return; tercile of drawdown from the
  60-session high; listing age (< 60, < 250 sessions, older or present since the panel
  start). Every feature uses data at or before that session only and is computed on the
  whole panel, so its rolling window is warm at the run's first session. When fewer than 5
  other names share every bucket, the lowest-priority feature is dropped, then the next;
  each report has a coverage table (how often each feature was known for the signalled name
  and how often it was actually matched on). In the latest placebo run all seven matched for
  14% of attempts, the first three for 93%. The signalled name is never its own control.
  `controls_version="v1"` reproduces the four-feature controls of older runs.
- **Same-session.** Any evaluable name. Controls for market timing only. Kept beside the
  matched baseline.

Why both: a rule that keeps picking illiquid Rp100 names will beat same-session random
whenever those names do well, with no information in the signal. The test suite builds
such a market: picking cheap names returns +1.40% against +0.60% same-session (p = 0.005)
and +1.46% matched (p = 0.58). Not matched on, because no point-in-time history exists
here, and not invented: sector (only a 2025-02 snapshot), listing board (same), free float
(IDX's `tradeble_shares` equals listed shares for most names, so it is not free float).

The report gives signal count, hit rate (net return > 0) and average net return for the
rule and each baseline's distribution (mean, 95% range), the difference, the rule's
percentile among draws and a one-sided p-value, with a breakdown by year.

## 5. Experiment E1: five-session repricings ([research/E1](research/E1/REPORT.md))

Protocol frozen and pushed before any statistic was computed (`research/E1/protocol.json`).
Base rate of a +30% repricing within 5 sessions: 1.9% of eligible ticker-days in 2021-22,
1.2% in 2023 (+100%: 0.10% and 0.03%). The first 100 +30% episodes, matched controls and 20
pre-event signals: on the day before a repricing starts, only prior volatility separates
winners from similar names (AUC 0.68). Detector D1 = F1_ARA (close locked at ARA), chosen on
discovery by a pre-registered rule, validated on 2023: 9.3x the +30% hit rate of matched
random names (p = 0.005), but it catches only 10% of episodes, 82% of its flags are false
alerts, and buying at the next close loses (-4.06% vs -0.53% for matched random entries) because
the continuations that run cannot be filled. Holdout 2024-01-02 .. 2025-02-21 untouched.

## 5b. Experiment E2: US equities and crypto ([research/E2](research/E2/REPORT.md))

E1's design on two markets without price limits (`research/E2/protocol.json`, frozen before
analysis): US common stocks from the Nasdaq Trader listing (Yahoo, split-adjusted,
survivor-only) and Binance spot USDT pairs including delisted ones, 2020-07 .. 2023, with
market profiles for lots, costs and entry at the next open (`idxsig/profiles.py`). Base rate
of +30% in 5 sessions: US 1.1-1.3%, crypto 5.6% (2020-22) and 2.4% (2023). Prior volatility
is again the clearest pre-event signal (US AUC 0.78, crypto 0.56). G2_RET30 (a +30% day),
selected on discovery in both markets, validated for detection (US 5.4x, crypto 4.6x matched
random, p = 0.005) and failed for execution in both: buying the next open and holding 5
sessions averaged -3.65% (US) and -1.90% (crypto) per trade vs -0.60% and +1.42% for matched
random entries. US price levels are not point-in-time (Yahoo rescales history at later reverse splits): with costs at the price actually traded the US average is -4.47%; see [ERRATA](research/E2/ERRATA.md) and the [audit brief](research/E2/AUDIT_BRIEF.md). Holdout 2024 onward untouched. **Repair (2026-10-08, [research/E2/repair/HANDOFF.md](research/E2/repair/HANDOFF.md)):** the original run reproduces byte for byte from archived inputs; with causal preprocessing, as-traded price units and SEC-corroborated split schedules the US result is −4.85% vs −1.13% for matched random entries (fill model A, ex post) and −4.41% vs −1.21% with decision-time capacity (fill model B). The erratum's −4.47% re-costing is superseded.

## 5c. Experiment E3: execution plans for the ARA detectors ([research/E3](research/E3/REPORT.md))

E1 found that D1 detects repricings but cannot be traded by buying the next close. E3
(`research/E3/protocol.json`, frozen before analysis) searched a fixed family of 36 execution
plans (entry at the next close, on confirmation, on a pullback, or at the first unlocked close
within three sessions; exit at the horizon, at the signal session's reference price, or on the
first down close; hold 2, 3 or 5 sessions) for the three ARA detectors of the E1 family: 108
harness runs on discovery 2021-22, fill model C, matched random baselines under the same plan.
**Admissible pairs: none.** 18 had a positive average net return, 3 beat matched random at
p < 0.05, and all 108 lost money in 2022, so the pre-registered per-year condition admitted
nothing; no pair was frozen, validation was not run, and the holdout is untouched. The best pair
(F8_ARA_EARLY, confirmation entry, hold 5: +1.49% vs +0.56% for matched random, p = 0.14) earned
its average in 2021 alone. The paper policy therefore keeps PASS.

## 6. Prospective paper ledger ([paper/](paper/README.md))

`python -m idxsig paper-scan --market <IDX|US|CRYPTO> --commit` after each session: every scan is recorded,
including `NO SIGNAL` days; every candidate gets a terminal decision with a full plan or the
reason it is not a trade; `paper-score` scores discovery and decision separately once the
window ends. Hash-chained, RFC 3161-stamped, pushed. No orders exist anywhere in this code.

## Results are append-only

`run` writes `results/runs/<run_id>/` (summary.json, trades.csv.gz, random_draws.csv,
REPORT.md) with exclusive-create opens, makes the files read-only, appends their hashes
to `results/RUNS.jsonl`, and commits exactly those paths. It refuses to run from
uncommitted rule or harness code unless `--allow-dirty` (recorded). Past runs are never
edited:

- `verify-runs` re-hashes every run file and checks RUNS.jsonl only grew relative to HEAD.
- `tools/check_append_only.py` rejects any commit that modifies or deletes a run, manifest,
  corporate-action registry, KOD card or registry line, or rewrites a line of
  `manual.csv`. It runs as a pre-commit hook (`git config core.hooksPath
  .githooks`) and over the whole history in CI (`.github/workflows/checks.yml`).

A correction is a new run with a new id. The old one stays.

### Split-verification correction (8 October 2026)

The [v2 audit and reruns](research/E2/repair_v2/REVIEW.md) supersede the v1 split-evidence
approvals above. Of 1,313 previously accepted records, 239 meet the stricter event-and-date
rule; 1,074 are unverified, which does not establish that the splits were false. The panel
is byte-identical, but 891 names are now excluded. Model A returns -2.23% versus -0.27%
matched random (516 scored trades); model B returns -1.69% versus -0.30% (438 trades).
Both remain negative on this smaller population. IDX event dates now use Jakarta time,
and prospective scoring uses paper-score-v3. See the report for evidence and coverage limits.
