# IGNITION_SCAN_v0 — research log (exploratory, discovery data 2020–2022 only)

Status: EXPLORATORY. Not validation. 2023+ data deliberately not downloaded.

## Data
- Binance spot 1h klines, all USDT pairs listed on data.binance.vision (incl. delisted), minus leveraged tokens and stablecoins.
- 8,183 monthly files, 0 parse failures, 350 coins with data in 2020–2022, 5,866,206 hourly rows. Per-file SHA256 in out/build_log.json.

## Rule (spec in out/spec_v0.json)
Trigger at hour close: +10% over 3h, 3h volume ≥5× the prior-week hourly norm, not already up >30% over the prior week,
avg hourly volume ≥ $20k. Entry next hour open, 0.3%/side cost, 72h horizon, 72h cooldown per coin.
Controls: 5 random other liquid, non-triggered coins at the same hour per event.

## Results (summary_v0_fixed.json)
| | Ignitions (n=5,267) | Controls (n=26,321) |
|---|---|---|
| Reached +30% within 72h of entry | 17.5% | 3.9% |
| Reached +50% | 8.3% | 1.0% |
| Reached +100% | 2.3% | 0.17% |
| Avg net return, hold 72h | −4.1% | −1.0% |
| Median net return, hold 72h | −7.5% | −1.3% |
| Profitable after 72h | 28% | 43% |

Same picture every year (2020, 2021, 2022). The top 20 events summed to +34.8 return units, and the other 5,247 to −252.6.
Median move already done before entry: +13.9%.

## Reading
Detection: real. Ignitions are 4–14× likelier to become +30%/+50%/+100% moves than matched coins.
Buying and holding them: loses, worse than controls, every year. Same failure as earlier KOD work, now at hourly speed.

## Errors found and fixed
- scan_v0.py summary: hit-rate columns were object dtype, so the printed hit rates (0.02%) were wrong.
  Recomputed from per-event values in summarize_v0.py. Raw events were unaffected.
- 1 event with an intrahour low ≥90% below entry (likely a bad print). Kept and flagged.

## Next (planned before looking)
1. Which ignitions keep running? Test the owner's filters on the 5,267 events: chart (support/resistance breakout,
   RSI, volume pattern, BTC trend) and catalyst (timestamped news/listing/rumour search, sampled).
2. Exits: take-profit/trailing exits, judged against the same exits applied to controls and shuffled triggers.
3. Luck control: count every variant tried, shuffled-trigger placebo, per-year and per-coin concentration; confirm
   survivors only on 2023+ (not yet downloaded).

## PATHS_v0 — no stop loss, no take profit, follow 30 days (paths_v0.py, out/summary_paths_v0.json)
Note: v0 never had a stop loss; it was a fixed 72h hold. This run follows each trade 30 days with no exits.
Events OK 5,147 (81 no 30-day window at end of data, 39 gappy/delisted — kept, counted). Controls OK 25,850.

| | Ignitions | Random coins same hour |
|---|---|---|
| Median result, held 1d / 3d / 7d / 14d / 30d | −5.8% / −7.4% / −8.0% / −8.5% / −13.9% | −0.8% / −1.3% / −1.4% / −2.4% / −7.6% |
| Average result at 30d | +4.0% | +5.7% |
| In profit at 30d | 36% | 41% |
| Touched +30% at some point in 30d | 48.7% | 44.6% |
| Touched +100% at some point in 30d | 14.8% | 11.5% |
| Peak came in the first 24h | 34.6% | 13.6% |
| Median lowest point within 30d | −29.7% | −23.4% |
| Of those that touched +30%: median dip before peak / give-back from peak by day 30 | −12.5% / −33.4% | −9.0% / −26.1% |

Reading: removing exits does not help. Over a month, almost half of ALL coins (random ones too, 2020–22 bull era)
touch +30% at some point, so "it shot up eventually" is not specific to ignitions. Ignitions peak early far more often
(35% within a day) and then give back. Peak gain is hindsight-only; the averages that matter are at or below random.

## FILTERS_EXITS_v0 (filters_exits_v0.py sha 38a1820a…, out/summary_filters_v0.json)
Explore 2020–21: 2,962 events; check 2022: 2,185; controls 25,850. 360 cells (15 chart features × quintiles × 5 exits).
Luck bar: best cell from 200 shuffled searches, 95th pct = +12.4% (median +10.7%).
Exits, average net per trade, ignitions vs random coins same exit:
 hold 3d −2.0% vs −0.4% (2020–21), −6.7% vs −1.8% (2022); trail 20% +0.8% vs +4.4%, −5.0% vs −3.3%;
 TP30/SL15/7d −0.1% vs +1.2%, −4.1% vs −1.6%; TP50/14d +3.5% vs +4.8%, −5.0% vs −2.5%; trail 30% +6.3% vs +9.2%, −8.4% vs −5.6%.
5 cells beat the luck bar in 2020–21 (coin age 346–475d, BTC up >3.6% in 24h, BTC up >10.5% in 7d, price within ±9% of
30d high; all with trail-30 or TP50). All 5 failed in 2022 (−2.5% to −9.2%), every one at or below random coins.
Runner rate (+30% before −15% within 7d) rises with: prior 7d gain (20.6% → 34.4%), being near/above the 30d high
(21.9% → 35.6%), up from 30d low (22.9% → 35.2%), BTC 7d up (23.6% → 34.1%), many coins igniting together (24.8% → 31.1%).
RSI, volume size, 24h volume build-up, liquidity, wick, hour: flat (no separation).
above_30d_high produced a single bin (feature almost constant by construction) — needs redefinition.
Reading: no chart filter or exit made ignitions beat random coins. The cells that passed in 2020–21 were the bull market
(BTC rising), and they reversed in 2022.

## CATALYST_SAMPLE (40 random ignitions, blind search; run1 incomplete, run2 findings entered by parent)
Pre-move catalyst found: 7/40 (BAND partnership, DASH coin-pick hype, MASK/LPT/ALICE product, WTC other, BICO Gemini listing).
None found 28, only after-the-fact explanations 5. Runner rate 1/7 with catalyst vs 6/33 without; hold-3d −4.9% vs −8.2%.
Descriptive only (n tiny, shallow searches, no hour-level timestamps confirmed). Outcomes joined only after labelling.

## SMA_MTF_v0 — upside only (sma_mtf_v0.py, out/summary_sma_mtf_v0.json; daily data 2017-08..2022-12 for SMA history)
Features: daily SMA 11/21/50/100/200/500 distance, count above, stack 11>21>50>100>200, 50>200; weekly SMA 11/21/50;
hourly SMA 11..500; 20/50/200-day resistance/support distance; daily/weekly RSI14; daily Stoch14; 5d/50d volume; OBV-style 20d.
980 cells (7 upside outcomes). Explore 2020–21 n=2,962; check 2022 n=2,185.
Explore: strong trend context separates upside. Runner rate (base 27.5%): far above SMA100 41.2%, within 15% of / above
200-day high 41.2%, far above weekly SMA11 40.2%, stacked SMAs 36.5% (vs 23.8% not stacked), above all 6 SMAs 34.2%
(vs 12–19% above ≤4), daily RSI >71 36.1% (vs 17.7% <50), weekly RSI >71 36.8% (vs 15.5% <49). Reach +100% in 30d
(base 19.8%): 30–31.5% in the same groups. Many cells beat the luck bar.
Check 2022 (base runner 19.4%, reach100 8.1%): direction mostly held but weaker and on small samples: SMA100 top 28.6% (n=28),
200-day high 26.7% (n=15), weekly SMA11 26.9% (n=52), stacked 26.7%, hourly SMA500 top 23.6%, weekly RSI>71 37.5% (n=8).
Reach +100% collapsed to 0–8% in 2022. Profit: best explore exit cells +3.7% to +11.3% per trade, all ≤ controls or
negative in 2022 except TP30/SL15 with near-200d-high (+1.9%, n=15) and far above SMA100 (+0.1%, n=28) vs controls −1.6%.
Not yet tested: whether random coins in the same trend state do just as well (is the ignition adding anything?).

## FIB_TREND_v1 (fib_trend_v1.py, out/summary_fib_trend_v1.json) — upside only
Part A, Fibonacci (50d, 200d, 500h swings; 520 cells, luck bar per outcome from 200 shuffles):
- Position high in the 200-day swing (above .786, i.e. near or above the old high): runner 39–42% vs 27.5% (2020–21). Same as
  "near 200-day high" from SMA_MTF_v0 — not new information. 2022 samples 6–15.
- The 3h move crossing the .618 or 1.0 level of the 200-day swing: runner 34.9% vs 24.4%, reach +50% 51% vs ~38% (2020–21);
  2022: runner 36% vs 18.3%, reach +50% 40% vs 23% (n=25). Direction held; tiny sample.
- Distance to the nearest Fibonacci level: no effect (being at a Fib level is not better). Fib levels as exact support/
  resistance: no evidence.
- "Pullback in an uptrend" swing (low before high), 50d/500h: helped in 2020–21 (31.8% vs 21.9%), reversed in 2022 (16.1% vs 20.8%).
- Profit: several cells beat the luck bar in 2020–21; none held in 2022 except tiny ones.
Part B, like-for-like, TREND fixed in advance (≥5 of 6 daily SMAs and within 15% of the 200-day high):
| 2020–21 | ignitions in TREND (367) | random coins in TREND (974) |
| runner / reach+100% | 41.4% / 30.3% | 32.1% / 23.8% |
| net: hold 3d / TP30-SL15 / TP50-14d / trail20 / trail30 | +3.5 / +5.1 / +9.4 / +5.9 / +13.9% | +3.9 / +4.3 / +9.4 / +8.6 / +10.9% |
| 2022 | ignitions in TREND (15) | random coins in TREND (41) |
| runner | 26.7% | 9.8% |
| net: hold 3d / TP30-SL15 / TP50-14d / trail20 / trail30 | −0.7 / +1.9 / +2.1 / −1.0 / −6.1% | −2.8 / −3.7 / −5.8 / +3.4 / −3.1% |
Ignitions NOT in TREND (2,595 in 2020–21; 2,170 in 2022) lost vs random coins under every exit.
Reading: in 2020–21 the trend itself made the money; adding the ignition raised the hit rate (partly because ignitions are
more volatile) but not the profit. 2022 hints the ignition helps inside a trend, but n=15. Runner rate vs random coins is
not a fair comparison (volatility differs); profit is.
