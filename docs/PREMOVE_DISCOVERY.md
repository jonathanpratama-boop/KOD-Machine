# Pre-move discovery benchmark

This research path asks whether recent price and volume sequences improve a five-name daily shortlist of future exceptional upside moves. It extends KOD's existing E2/E5 pre-move work. Every eligible instrument-day competes, including ordinary days, instead of starting from a list of known future winners.

The benchmark is separate from live trading and the post-spike learner. It produces forecasts, shortlist diagnostics and chronological comparisons. It does not estimate executable profit, change the active paper policy, or demonstrate a trading edge by passing software tests.

## Frozen protocol

The specification is [protocol.json](../idx-signals/research/PREMOVE_SEQUENCE_v1/protocol.json), identified as `KOD-PREMOVE-SEQUENCE-v1`. Preserve that version and its hash. A new research choice requires a separately versioned protocol; do not tune the existing protocol against its 2023 result.

| Stage | Decision dates | Permitted use |
| --- | --- | --- |
| Training | 2020-2021 | Fit feature scaling, PCA and model coefficients |
| Calibration | 2022 | Select one of the prespecified probability temperatures |
| Retrospective test | 2023 | Compare frozen methods and report uncertainty |
| Existing later holdout | 2024 onward | Unopened by this benchmark |

KOD has already studied 2020-2023, including 2023. This is a chronological retrospective comparison on previously examined history, not an untouched research holdout. Provider retrieval and the universe catalog also come from a later date. The program refuses price input outside 2020-2023; the collector always supplies explicit UTC request bounds ending on 2023-12-31.

## Decision and outcome timing

A decision occurs after a completed UTC daily bar. Eligibility requires 60 consecutive valid daily observations, positive current prices and volume, and median quote volume of at least 100,000 USDT over the preceding 20 days. Current completed-bar features are available; future prices are not features. The archive's exact pair symbol is retained as `ticker`, without stitching renamed assets together.

Labels use the next day's open as a reference and the next five daily closes. Let `b = max(log(1.10), 3 * trailing_20_day_log_return_sd * sqrt(5))`. The upper and lower barriers are `entry * exp(b)` and `entry * exp(-b)`. The first daily close crossing a barrier determines `up_first` or `down_first`; otherwise the class is `neither`. These are close-based outcomes, not the order of intraday high/low touches or assumed trade fills.

All five future daily bars must be present, valid and complete to know the label. Missing data, delisting and shortened terminal bars produce unknown outcomes. Unknown outcomes remain in the daily ranking population; the benchmark does not remove a difficult candidate because its future later becomes unavailable. Training and calibration require labels to end within their own period. The final test days are therefore deliberately censored rather than completed using 2024 prices.

The collector preserves shortened exchange daily bars and emits `complete_bar=False`. The benchmark excludes them from valid decision history and future-label completeness, while retaining the instrument's other history. A missing `complete_bar` column defaults to true for other validated inputs; when supplied it must contain nonmissing booleans.

## Comparisons and interpretation

Four methods receive the same daily candidate pool and a maximum five-name budget, with ticker order breaking ties:

| Method | Ranking |
| --- | --- |
| Simple | Equal-weight within-day percentile ranks of volume ratio and trailing volatility |
| G2 | Existing E2 one-day return-at-least-30% flag, then the simple score |
| Summary | Ridge logistic class models on 14 causal summary features |
| Sequence | The summary features plus eight PCA components from 20 days of return, range and volume sequences |

The sequence representation, scaling and coefficients fit only on training data. Each fitted model selects a scalar temperature from `0.5, 1, 2, 4` using 2022 multiclass log loss. This lightweight learned sequence representation is not Kronos and is not a rerun of E5's full feature model.

Results distinguish all eligible decisions from an early population excluding instruments already up at least 10% that day or 20% over five days. These exclusions use past data only. G2 cannot trigger in the early population, so its ranking there reduces to the simple comparator.

Reports include shortlist hit rates, known false alerts, censored selections, precision bounds, known event recall, missed events, and earliest-alert lead time. They also report Brier score and log loss on known outcomes. A paired 10-day moving-block bootstrap uses 400 resamples and seed `20261030` to compare sequence hit rates with simple and summary hit rates. Recall covers observable eligible episodes only; unknown delisting outcomes cannot be counted as known missed events. These uncertainty intervals concern forecast hit rates, not returns.

## Initial retrospective result

The first run is [20261030T024900Z/REPORT.md](../idx-signals/research/PREMOVE_SEQUENCE_v1/runs/20261030T024900Z/REPORT.md), with exact counts and provenance in [summary.json](../idx-signals/research/PREMOVE_SEQUENCE_v1/runs/20261030T024900Z/summary.json). Its early population contains 113,365 candidate windows. Each method selected 1,825 alerts over 365 days.

The [complete result bundle](https://chatgpt.com/library?file_id=libfile_3f347ecfa61c81919c701299e7d015b1&account_id=personal) preserves all 119,176 test forecasts, every shortlist, daily metrics, model parameters, protocol, source manifest and exact benchmark source files. Its SHA-256 is `cbdc58fd291377e0e72501da70f4cd21e99034e1f6e00a4afb03b59393f8df59` (14,735,005 bytes). Git contains the compact reports, models and manifests; the compressed CSVs are in this bundle. These personal artifact links require the owner's account. Collaborators can request the verified archives or collect a clearly identified new vintage.

| Early-population method | Known upside hits / all alerts | Hit-rate lower bound | Known false alerts | Censored alerts |
| --- | ---: | ---: | ---: | ---: |
| Simple / G2 | 25 / 1,825 | 1.37% | 1,742 | 58 |
| Summary | 60 / 1,825 | 3.29% | 1,739 | 26 |
| Sequence | 76 / 1,825 | 4.16% | 1,722 | 27 |

Sequence improves on simple by 2.79 percentage points, with a paired 95% bootstrap interval of +1.20 to +4.38 points. Its improvement over summary is 0.88 points, with an interval of -0.22 to +1.81 points. The latter includes zero: this result does not establish that sequence features add value beyond the summary model.

Sequence catches 46 of 911 observable eligible episodes, with median earliest-alert lead time of four days, and misses 865. The false-alert burden remains high. Keep it as a research challenger; this evidence does not support deployment or a profitability claim.

Probability quality is also unproven. On known test outcomes, sequence multiclass log loss is 0.20908, compared with 0.20247 for the constant training class-rate forecast and 0.20811 for summary; lower is better. Sequence's upside Brier score is 0.0252969 versus 0.0252270 for the constant forecast, also slightly worse. Better shortlist ranking does not establish useful or reliable probability estimates.

## Data collection and provenance

[collect_premove_crypto.py](../tools/collect_premove_crypto.py) freezes a universe from the public Binance spot archive catalog before any labels are calculated. It selects USDT pairs using the existing `global_panel.STABLE` set and `LEVERAGED` suffix expression. This includes delisted instruments still represented by the archive, while avoiding the current-trading-only universe of a live screener.

The catalog is current at collection time, not a point-in-time listing history. Instruments removed from the archive may be absent. The existing suffix filter can also exclude ordinary names ending in `UP`; its convention is preserved and disclosed. Asset renamings, migrations and denomination changes are not retrospectively stitched or corrected. Large raw moves are preserved: a subsequent reversal cannot cause an earlier observation to be deleted.

Daily bars come from Binance's public market-data API, including delisted symbols it still recognizes. Requests require no API key. The collector makes at most five request starts per second, retries transient failures at most three times, and stops further requests after a rate-limit response. Worker count is bounded at 24. An empty response is recorded separately from a failed request; it means the API returned no rows in the requested window, not proof that the instrument never traded. Archive-only historical prices omitted by this API are not automatically recovered.

The panel schema is:

| Field | Meaning |
| --- | --- |
| `date` | UTC daily bar opening date |
| `ticker` | Exact Binance pair, such as `BTCUSDT` |
| `open`, `high`, `low`, `close` | Raw prices in USDT |
| `volume` | Base-asset volume |
| `value` | Provider-reported USDT quote-asset volume |
| `complete_bar` | Whether the bar spans the complete UTC day |
| `source` | `binance` |

Each new output directory contains `UNIVERSE.json`, raw catalog pages, raw API responses, per-pair records, `panel.csv.gz`, and `COLLECTION.json`. Request records include source URL, retrieval timestamps, byte count and SHA-256. The collection manifest contains the panel and frozen-universe hashes, date bounds, row and instrument counts, and explicit empty and failed pair lists. Preserve the entire directory: a later retrieval is a new provider vintage and need not reproduce the original bytes.

The initial collection finished on 2026-10-30 and contains 369,426 bars across 407 pairs from 2020-01-01 through 2023-12-31. Its frozen catalog universe has 684 selected pairs: 277 returned no bars in the window and zero requests ended as failed pairs. There are 61 shortened bars across 59 pairs, retained with the completeness flag. All recorded raw response hashes were verified. These are coverage facts, not model performance results.

| Initial artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `panel.csv.gz` | 10,468,688 | `f1dfd57d26a7a98781bd5fcbf18db3203778d24c51c46b4d4f92963dc9b75766` |
| `COLLECTION.json` | 509,678 | `8f4efd06d2d819be44de66f9d84ac1d1be6a1aa2cbbbac0a1ea9530a526293d2` |
| `UNIVERSE.json` | 14,424 | `12c05ec59bb61ddadc771071c3537fca47e3bda96e55553af985d796b31fb92a` |

The 874 raw API responses total 62,314,306 bytes. Raw data and collection output are separate from the source-code checkout.

The exact original inputs are available as [KOD-premove-input-20261030.tar.gz](https://chatgpt.com/library?file_id=libfile_65b3d2811b448191b09151b0e878a8c3&account_id=personal). The archive SHA-256 is `6b87a7afb42ba39ac0471a9225a695435e7a9a7507b281167d704971151a97f6`. It contains the complete `premove-data-v2/` directory, including raw evidence and collection manifests.

## Reproduce

To reproduce the original vintage, download that archive, verify its hash, and extract it into a separate directory:

```sh
sha256sum /tmp/KOD-premove-input-20261030.tar.gz
mkdir -p /tmp/kod-premove-reproduction
tar -xzf /tmp/KOD-premove-input-20261030.tar.gz -C /tmp/kod-premove-reproduction
```

Install the declared research dependencies from the repository root, then run against the preserved inputs:

```sh
python -m pip install -r idx-signals/requirements.txt -c idx-signals/constraints-research.txt
cd idx-signals
python -m idxsig.premove --input /tmp/kod-premove-reproduction/premove-data-v2/panel.csv.gz --source-manifest /tmp/kod-premove-reproduction/premove-data-v2/COLLECTION.json --out research/PREMOVE_SEQUENCE_v1/runs/local-reproduction
```

To collect a new vintage instead, run from the repository root into a new directory:

```sh
python -m pip install -r idx-signals/requirements.txt -c idx-signals/constraints-research.txt
python tools/collect_premove_crypto.py --out /tmp/kod-premove-data --workers 24
```

To resume from an earlier stopped collection, preserve it and use a different output directory. Only recorded raw responses matching the exact requested URL and verified byte count/hash are reused. The frozen universe must match its verified catalog pages.

```sh
python tools/collect_premove_crypto.py --out /tmp/kod-premove-resumed --reuse /tmp/kod-premove-data --workers 24
```

Run the standalone research module from `idx-signals`:

```sh
cd idx-signals
python -m idxsig.premove --input /tmp/kod-premove-data/panel.csv.gz --source-manifest /tmp/kod-premove-data/COLLECTION.json --out research/PREMOVE_SEQUENCE_v1/runs/local-first
```

If using the resumed collection, substitute `/tmp/kod-premove-resumed` for both input paths. Input must match its collection manifest's panel hash. Output directories must be new. This command is `python -m idxsig.premove`, not a subcommand of the main `idxsig` CLI.

Each benchmark run publishes `summary.json`, `models.json`, `REPORT.md`, forecasts, shortlists, daily counts, a source-manifest copy and a file-hash manifest. Provenance includes the input, source-manifest, protocol and benchmark source hashes, plus runtime package versions. Retain the separate collection directory alongside these outputs.

Run the targeted software checks from `idx-signals`:

```sh
python -m unittest tests.test_premove_core tests.test_premove_evaluation tests.test_premove_collector -v
```

Passing these checks establishes tested software invariants. A prospective frozen evaluation, independent data validation, realistic execution assumptions and costs remain necessary before drawing conclusions about trading usefulness.

## Official source references

- [Binance market-data API documentation](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/market) specifies UTC default timing, kline pagination and base/quote-volume fields.
- [Binance public market-data endpoint](https://data-api.binance.vision/api/v3/klines) supplies the bounded daily bars.
- [Binance public data archive](https://data.binance.vision/) provides the archive namespace.
- [Archive spot-kline catalog](https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?delimiter=/&prefix=data/spot/monthly/klines/) supplies the frozen pair list.
