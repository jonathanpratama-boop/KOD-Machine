# Minute-interval data: what exists free (checked 2026-10-30 from this container)

Owner's next stage: tune on 1, 5 or 10-minute intervals up to the present.

| Market | Source (free, keyless) | Interval | How far back | Notes |
|---|---|---|---|---|
| US stocks | Yahoo chart v8 | 1 minute | last 8 days only | 30 days requested: HTTP 422 "Only 8 days" |
| US stocks | Yahoo chart v8 | 5 / 15 minutes | last 60 days | 1 year requested: HTTP 422 |
| US stocks | Yahoo chart v8 | 60 minutes | about 2 years | 3,498 bars for AAPL |
| Crypto | Binance public archive (data.binance.vision) | 1 minute | 2017-08 to last month (monthly files), daily files after | delisted pairs kept; already used by BINANCE_ANN_1M / REVERSAL_1M |
| Crypto | already on disk | 1 hour | data/raw/binance_1h (392 MB) | CRYPTO_PUMP_HISTORY_v1 |

What this means:
- **Crypto:** a minute-level history experiment is possible today, for years back, free.
- **US stocks:** free minute data reaches back 8 days (1-minute) or 60 days (5/15-minute). That is enough to
  start recording now and build a history forward, not enough to tune on years of the past. Years of US minute
  history needs a paid source (for example Polygon, Databento or Alpaca's historical feed): an owner decision.
- **Disk:** about 3 GB free in this container; a full Binance 1-minute archive for hundreds of pairs is tens of GB,
  so a crypto study would pull only the pairs and months it needs.
