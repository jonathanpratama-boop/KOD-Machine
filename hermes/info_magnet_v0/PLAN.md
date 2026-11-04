# INFO_MAGNET_v0 pilot — do dated public exchange notices come BEFORE our moves, early enough to trade? (written 2026-11-03, before outcomes)

**Status: EXPLORATORY pilot.** Prices 2020–2026 already seen by other studies; this source has never been used by KOD.

**Source 1 (run now): Upbit "trade" notices** (`api-manager.upbit.com/api/v1/announcements?category=trade`), raw JSON
kept with retrieval time. Listing notices = titles containing "마켓 디지털 자산 추가" (market digital-asset addition), split
KRW / BTC / USDT market. Delisting notices = "거래지원 종료". Ticker parsed from the parentheses in the title. Notice
time = `first_listed_at` (KST, converted to UTC). Only coins already trading on Binance spot USDT at the notice time
are measurable (prices from our Binance hourly archives).

**Measures (fixed now).**
1. Leak: return from 72h before to 1h before the notice hour, vs 5 random eligible Binance coins at the same hour.
2. Reaction: return from the last close before the notice to +1h, +6h, +24h, +72h, +14d; max high within 24h.
3. Tradability: buy the first full-hour open after the notice (latency up to 60 min; conservative for hourly data),
   sell at +6h, +24h, +72h close; 0.3% per side; vs the same for controls.
4. Overlap with our clues: share of hourly ignitions (+10%/3h, ≥5× volume) that fall within −6h..+6h of a Korean
   listing notice, vs the share expected by chance; reaction split by crowd mood (prior-day Fear & Greed) and by
   daily uptrend (clues #4, #6).

**Not run in this pilot (feasibility only):** token unlocks (DefiLlama emissions API now requires a paid plan —
blocked), Snapshot governance (free API works; needs a token↔space map, next step), Binance listing catalog
(new coins have no Binance price before listing; futures launches already covered by BINANCE_ANN).
