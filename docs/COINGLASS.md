# CoinGlass crypto data integration

CoinGlass v4 is an optional, authenticated source for KOD's crypto research context. It supplies vendor data and indicators alongside existing scans. It does not modify a frozen trading policy, learner feature recipe or execution funding calculation.

## Configure and check access

Set `COINGLASS_API_KEY` in the process environment. No key is accepted on the command line, written to manifests, or stored in Git. In an interactive Bash shell, this avoids placing the key in shell history:

```bash
read -r -s -p 'CoinGlass API key: ' COINGLASS_API_KEY
export COINGLASS_API_KEY
cd idx-signals
python -m idxsig coinglass-check --symbol BTCUSDT --interval 4h
```

Alternatively, copy `.env.example` to a local `.env`, fill it, restrict permissions (`chmod 600 .env`), and explicitly load it into your shell. The application does not automatically read `.env`. Configure a secret environment variable separately in any remote runtime; copying code does not configure credentials.

`coinglass-check` makes two bounded requests by default: price and RSI. It distinguishes authentication, plan/interval access, quota, network and schema errors. HTTP 200 is not sufficient: the JSON `code` must also be `0`. A `401 / Upgrade plan` response is treated as access denial, not proof of an invalid key. The integration does not buy, upgrade or change a subscription.

## Pull data and read it offline

```bash
python -m idxsig coinglass-pull --symbol BTCUSDT --exchange Binance --interval 4h --limit 200
python -m idxsig coinglass-pull --symbol STXUSDT --exchange Binance --interval 4h --limit 200
python -m idxsig coinglass-report --manifest data/manifests/coinglass-REPLACE-WITH-ID.jsonl
python -m idxsig coinglass-verify --manifest data/manifests/coinglass-REPLACE-WITH-ID.jsonl
```

Use the exact instrument identifier returned by `CoinGlassClient().request("supported_pairs", exchange="Binance")`; a coin ticker alone is not necessarily a supported futures instrument. The STX command is an example, not a claim that a particular account or exchange supplies it.

Each pull captures one bounded window of at most 1,000 bars per endpoint. It does not promise full history or paginate arbitrary ranges. `--end 2026-10-30T00:00:00Z` selects an earlier cutoff; the request still records its actual retrieval time. Unclosed bars are excluded conservatively using provider timestamp plus interval. Empty rows, missing periods and nulls remain missing, with explicit statuses. Conflicting duplicates, invalid numbers and malformed data are rejected. No gaps are forward-filled.

The default datasets are `price,open_interest,funding,liquidations,long_short,rsi,macd`. Choose a subset or add indicators:

```bash
python -m idxsig coinglass-pull --symbol BTCUSDT --datasets price,open_interest,funding,liquidations,long_short,rsi,macd,ma,ema,boll,atr
```

| Dataset | Data / snapshot recipe |
| --- | --- |
| `price` | Futures OHLC and USD volume |
| `open_interest` | OHLC in USD, requested explicitly |
| `funding` | Funding OHLC in provider-native units; no assumed percentage conversion |
| `liquidations` | Long and short liquidations in USD |
| `long_short` | Global account percentages and ratio, not position notional |
| `rsi` | Vendor RSI, window 14, close series |
| `macd` | Vendor MACD value, 12/26/9, close series; not a claimed signal/histogram pair |
| `ma`, `ema` | Vendor moving averages, window 20, close series |
| `boll` | Vendor middle/upper/lower bands, window 20, multiplier 2, close series |
| `atr` | Vendor average true range, window 14 |

Requests preserve their actual parameters, including indicator settings. Advanced Python callers can use the client directly with documented parameters; the snapshot recipe has explicit defaults.

Raw responses and normalized context go under `idx-signals/data/raw/coinglass/` (ignored by Git). A new hash manifest is published last under `data/manifests/`; existing snapshots are never overwritten. Keep both raw files and manifests when moving a workspace. A manifest does not confer redistribution rights to paid data. Failed access is recorded without credentials or response headers. Partial pulls remain inspectable and return exit code 2. `coinglass-verify` checks artifact integrity, not market readiness; reports label stale and unavailable data separately.

## Consume in Python

```python
from idxsig.coinglass import latest_context, history_frame

manifest = "data/manifests/coinglass-REPLACE-WITH-ID.jsonl"
context = latest_context(manifest)       # readiness, values, age, units, parameters
frame = history_frame(manifest)         # columns: price.close, rsi.rsi_value, etc.
```

Readers verify stored hashes and reproduce normalized values from raw responses. `history_frame` outer-joins exact timestamps and retains missing values. Its `attrs` carry parameters, source status, units and observation time. An `asof` before retrieval cannot use the data: backfill is not evidence that KOD had those values earlier. Live readiness requires the latest data to be no more than two intervals old by default. Reports may contain stale values for inspection; consumers must check readiness before using them.

## Limits and tests

The client uses the fixed official HTTPS host, refuses redirects, bounds response size, applies 25-second timeouts and at most three attempts, and respects `Retry-After` without sleeping indefinitely. Default pacing is 30 requests/minute per client instance. Multiple processes sharing a key must coordinate their combined quota. Access varies by endpoint and interval. An inaccessible indicator does not silently become a local substitute.

```bash
OPENBLAS_NUM_THREADS=1 python -m unittest tests.test_coinglass_client tests.test_coinglass_context -v
```

Tests are offline and use synthetic data. A live check separately establishes whether the account can retrieve real data. Passing offline tests does not establish account access or predictive value.

Official references: [authentication](https://docs.coinglass.com/reference/authentication), [errors and limits](https://docs.coinglass.com/reference/responses-error-codes), [price](https://docs.coinglass.com/reference/price-ohlc-history), [open interest](https://docs.coinglass.com/reference/oi-ohlc-histroy), [funding](https://docs.coinglass.com/reference/fr-ohlc-histroy), [liquidations](https://docs.coinglass.com/reference/liquidation-history), [account ratios](https://docs.coinglass.com/reference/global-longshort-account-ratio), [RSI](https://docs.coinglass.com/reference/futures-indicators-rsi), [MACD](https://docs.coinglass.com/reference/futures-indicators-macd), [MA](https://docs.coinglass.com/reference/futures-indicators-ma), [EMA](https://docs.coinglass.com/reference/futures-indicators-ema), [Bollinger bands](https://docs.coinglass.com/reference/futures-indicators-boll), [ATR](https://docs.coinglass.com/reference/futures-indicators-avg-true-range), [supported instruments](https://docs.coinglass.com/reference/futures-suported-exchange-pairs).
