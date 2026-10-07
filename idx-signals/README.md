# IDX signals

Test harness for daily trading signals on the Indonesia Stock Exchange. Research only. No
entry permission. It runs a frozen rule over every listed name (delisted names included
where the data has them), executes each signal under IDX trading constraints, and compares
the result with random entries on the same sessions. Results are append-only and committed.

**The detector rule is not in this repo yet.** The request read "Implement this rule
exactly: [paste your detector rule]" and the rule was never pasted. Nothing was guessed:
`idxsig/rules/user_rule.py` is an empty slot and `run --rule USER_RULE` refuses to start.
The only committed run is `PLACEBO_COINFLIP`, a price-blind coin flip that checks the
harness itself.

## Commands

```sh
cd idx-signals
pip install -r requirements.txt           # pandas, numpy
python3 -m idxsig fetch-idx-mirror         # IDX daily summaries, pinned commit
python3 -m idxsig fetch-yahoo              # Yahoo daily bars for every universe ticker
python3 -m idxsig build-panel              # canonical panel + QA manifest
python3 -m idxsig verify-data              # re-hash every raw file and the panel
python3 -m idxsig rules                    # list rules; USER_RULE shows PENDING
python3 -m idxsig run --rule PLACEBO_COINFLIP
python3 -m idxsig verify-runs              # no past run edited or removed
python3 -m unittest                        # 44 tests, synthetic data only
```

## 1. Dataset

| Segment | Source | Sessions | Survivorship |
|---|---|---|---|
| 2019-07-29 .. 2025-02-21 | IDX daily stock summary via the [wildangunawan/Dataset-Saham-IDX](https://github.com/wildangunawan/Dataset-Saham-IDX) mirror, pinned to commit `bc0ac771` | 1,355 | The mirror's first ticker snapshot was taken 2021-01-22 (upstream commit `ca98f653`), holding the names listed that day with history back to 2019-07-29. Names delisted before 2021-01-22 are absent; names delisted after it keep their history (FINN, TURI and RMBA end early). **Backtests start 2021-01-22 by default** for this reason. |
| 2025-02-24 .. 2026-10-06 | Yahoo Finance v8 chart API (`<TICKER>.JK`), split adjustment undone | 382 | Survivor-only. 59 mirror names return not-found from Yahoo and stop at 2025-02-21, as does FISH (see QA). Not-found is not the same as delisted: MAMI, MYRX, NIPS and five others were force-delisted on 2025-07-21, but WSKT is still listed and has been suspended since May 2023. |

Built panel: 1,425,830 rows, 983 tickers, 1,737 sessions. Prices are as traded (integer
rupiah), not adjusted, because lots, ticks and auto-rejection limits apply to traded prices.
`previous` is IDX's reference price, which IDX resets on split dates.

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
- 10 non-session dates dropped (9 Yahoo holiday stubs, one Sunday row for AALI in the mirror).

Post-mirror listings come from `data/universe/extra_tickers.csv` (2025 and 2026 IPO lists,
each row with its source URL and retrieval date).

## 2. The rule

`idxsig/rules/user_rule.py` holds `RULE_TEXT` (verbatim), `VERSION`, `HOLDING_DAYS` and
`compute(market)`, which returns a (tickers x sessions) array of 1 / 0 / NaN (signal / no
signal / not evaluable). The rule hash covers the text and the module source, so any edit
is a new rule version and a new run.

Every run recomputes the rule on every prefix of the data (sessions 0..d, for every d) and
refuses to record results unless each recorded signal at d equals the rule's output from
data up to d. That is a proof, not a sample: every signal in a run is exactly what the rule
computes from what was known at that close. The placebo panel takes about 9 seconds.
`--lookahead-cuts N` samples N prefixes instead, and the report says it is not a proof.

## 3. Execution over the full universe

The universe is every ticker in the panel window on every session where the rule is
evaluable, including names that later stop trading. Execution, per signal:

- Signal from data through the close of session s; buy at the close of s+1. Closes, not
  opens: IDX only reports an opening price for names with a pre-opening auction (~7% of
  rows), so an open-based model would drop most of the universe.
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
- **Corporate actions:** splits and reverse splits (an integer reference reset, e.g. BBCA's
  1:5 split on 2021-10-13) scale the shares held. Any other reset (rights issue, bonus
  shares, stock dividend) is not a split: a rights holder receives rights, not free shares,
  and their value depends on terms the price data does not have. A trade held across one
  is `EXCLUDED_CORP_ACTION` and not scored, for the rule and both baselines alike.
  `--ca-mode value_preserving` scales shares instead (rights valued at the theoretical
  ex-rights price and reinvested). Cash dividends are not added back.
- **Delisting:** a name that stops trading while held is sold at its last traded close
  (`EXIT_DATA_END`), or at zero with `--data-end-exit zero`. Counted in every report.
- **Overlap:** a new signal in a name already held is skipped and logged.

The default window is 2021-01-22 .. 2025-02-21, where the universe includes the names
that later delisted. An earlier start or a later end is allowed, and the report warns that
the extra sessions are survivor-biased.

## 4. Random baselines

For each attempted signal, each of 200 draws picks a replacement name on the same session
from the names where the rule was evaluable, and runs it through the same execution and
holding period. Each draw is a portfolio with the rule's size and dates. Two baselines:

- **Matched (primary).** The replacement comes from names in the same buckets as the
  signalled name that session: price band (<= Rp200, <= Rp5,000, above), quintile of
  20-session median traded value, tercile of 20-session volatility, tercile of 20-session
  return. All computed from data up to that session. When fewer than 5 other names share
  all four, momentum is dropped, then volatility, then liquidity; the report counts which
  level was used. The signalled name is never its own control.
- **Same-session.** Any evaluable name. Controls for market timing only.

Why both: a rule that keeps picking illiquid Rp100 names will beat same-session random
whenever those names do well, with no information in the signal. The test suite builds
such a market: picking cheap names returns +1.40% against +0.60% same-session (p = 0.005)
and +1.46% matched (p = 0.58). Not matched on, because the data lacks it: market cap and
free float, sector history, daily board membership.

The report gives signal count, hit rate (net return > 0) and average net return for the
rule and each baseline's distribution (mean, 95% range), the difference, the rule's
percentile among draws and a one-sided p-value, with a breakdown by year.

## Results are append-only

`run` writes `results/runs/<run_id>/` (summary.json, trades.csv.gz, random_draws.csv,
REPORT.md) with exclusive-create opens, makes the files read-only, appends their hashes
to `results/RUNS.jsonl`, and commits exactly those paths. It refuses to run from
uncommitted rule or harness code unless `--allow-dirty` (recorded). Past runs are never
edited:

- `verify-runs` re-hashes every run file and checks RUNS.jsonl only grew relative to HEAD.
- `tools/check_append_only.py` rejects any commit that modifies or deletes a run, manifest,
  KOD card or registry line. It runs as a pre-commit hook (`git config core.hooksPath
  .githooks`) and over the whole history in CI (`.github/workflows/checks.yml`).

A correction is a new run with a new id. The old one stays.
