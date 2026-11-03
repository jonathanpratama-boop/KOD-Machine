# COMBO_HOLDOUT_v1: frozen protocol (written 2026-11-02, before any 2023+ price data is on disk)

Owner: Jonathan. Researcher: Hermes (kod-machine profile). Paper research only. Not a forecast. No live trading.

## Why this exists
COMBO_v1 (combined upside clues on crypto early movers) worked in 2020–21 and failed in 2022. The clues were found on
2020–21, so those numbers are optimistic. This protocol fixes two versions of the rule **before** looking at
2023-01-01 onward. They are run once and reported as they come out. A redesign after seeing results would be a
new, declared test.

## Data state at freeze
- On disk: Binance spot 1h klines 2020-01..2022-12 and 1d klines 2017-08..2022-12 (USDT pairs, incl. delisted).
  No 2023+ price data has been downloaded by this researcher.
- Also on disk: the alternative.me Fear & Greed history (raw/fng_alternative_me.json, sha256 cfd9ffa0…a2c32,
  retrieved 2026-11-02). It contains 2023+ index values. They were not analysed or looked at.
- Known exposure: FRESH_EYES T3 (handoff/fresh-eyes-2026-11-01) used Binance perps 2023–2026-09 for weekly 14-day altcoin
  momentum, and E4 v2 used 2023 crypto. So 2023+ is **not fully clean** for momentum ideas. This rule (hourly
  ignition + daily/weekly trend clues + Fibonacci breaks) was never run on 2023+.

## Holdout window
2023-01-01 00:00 UTC to the last complete calendar month on data.binance.vision at run time (expected 2026-10).
Reported per calendar year, plus pooled.

## Universe and detector (unchanged from IGNITION_SCAN_v0, spec sha256 960279f9…646e)
All USDT spot pairs listed on data.binance.vision (incl. delisted). Exclude leveraged tokens (UP/DOWN/BULL/BEAR) and the
stablecoins in raw/universe.json, plus stablecoins listed after the freeze: USDE, FDUSD-type and USD-named stablecoins.
The list is fixed once from the listing at run time, before any outcome is computed.
Trigger at hour close: +10% over 3h; 3h volume ≥5× the prior-week hourly norm; not already up >30% over the prior
week; average hourly quote volume ≥ $20k; 72h cooldown per coin. Entry at the next hour's open, cost 0.3% per side.
Controls: 5 random other liquid, non-triggered coins at the same hour (seed 7).
Timestamp note: Binance spot files switched to microsecond timestamps in 2025. Normalise to milliseconds. This is
an engineering fix, not a rule change.

## Clues (as in combo_v1.py, sha256 dbfbae56…aeb51; features as in fib_trend_v1.py, sha256 057e7350…b49dd)
Daily features use only days fully closed before the trigger day. Hourly features use closes up to the trigger hour.
1. Above ≥5 of 6 daily SMAs (11/21/50/100/200/500; SMA200 must exist)
2. SMAs stacked 11 > 21 > 50 > 100 > 200
3. Price within 15% of the 200-day high, or above it
4. Price ≥50% above the 100-day SMA
5. The 3h move crossed the .618 or 1.0 Fibonacci level of the 200-day high/low swing
6. Same as 5, for the 50-day swing
Score = number of clues met (0–6).

## The two versions (each counted as one test)
- **Version A:** ignition AND score ≥ 4.
- **Version B:** Version A AND the previous UTC day's Fear & Greed classification is "Greed" or "Extreme Greed"
  (value ≥ 55).

## Exit (primary) and secondary outcomes
- **Primary exit:** take profit at +50% (limit fill at that price when the hour's high reaches it), otherwise sell at
  the close of hour 336 (14 days). No stop.
- **Secondary, reported but not used for the verdict:** trail-30% exit (on hourly closes, filled at next open, 30-day
  max); fixed 7-day hold; runner rate (+30% before −15% within 7 days); reach +100% within 30 days.

## Pass bar (per version, fixed now)
A version PASSES only if all four hold on the pooled holdout:
1. Mean net return per trade > 0, with the 95% bootstrap lower bound (resampling by trigger day, 2,000 draws) > 0.
2. Median net return per trade > 0.
3. Mean beats random coins with score ≥4 in the same period (Version B: random coins with score ≥4 on Greed days)
   by more than 0, with the bootstrap lower bound of the difference > −0.02 (not clearly worse).
4. At least 30 trades, and no single calendar year with mean < −10% on ≥10 trades.
Otherwise the result is FAIL, or INCONCLUSIVE if there are fewer than 30 trades. Either way the result is reported as it is.
Reported beside the verdict: per-year results, trades per year, top-5-trade share, and the result without the top 5.
Two versions → the result is read with Holm correction in mind. A PASS on only one version is a lead for live paper
trading, not a strategy.

## After the run
Append the result to research/CLUE_LEDGER.md. If any version passes, the next stage is a frozen live paper log, not money.
