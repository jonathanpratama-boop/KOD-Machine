# HERMES_NOV3_REPRO_v1: independent reproduction of Hermes's 3 November 2026 crypto studies

Written 2026-11-03, before any of the data below was downloaded or any study was run in this environment.
Owner's request: "read the chat on Hermes' Nov 3 work and try to reproduce it here and push it to GitHub."

## Why a reproduction, and what it can and cannot be
Hermes ran five studies on the owner's Mac on 3 November (entry_timing_v1, bear_v1, psych_v1, paths_v1,
spike_default_v1), wrote a plan (info_magnet_v0) and a policy (JUDGMENT_POLICY_v0). None of those files are on GitHub.
The only record available here is the chat transcript. The chat gives descriptions and results, **not code**.
So this is an independent re-implementation: the detector, clues, exits and data are taken verbatim from Hermes's
pushed code (branch `hermes/ignition-combo-holdout-v1` @ c7c84127: `scan_v0.py`, `run_holdout_v1.py`, `fib_trend_v1.py`,
`exposure_v1.py`); every Nov 3 rule is taken from the chat; **wherever the chat is silent, the definition below is fixed
now, before running, and marked [GAP]**. Numbers are expected to match in direction and rough size, not to the decimal.
All periods were already examined by Hermes; nothing here is a holdout or a strategy. Paper only.

## Data (same public source Hermes used)
data.binance.vision spot monthly klines, 1h 2020-01..2026-10 and 1d 2017-08..2026-10, for the union of Hermes's
universes (`hermes_universe_2020_22.json` usdt_universe = 684; `hermes_universe_2023_26.json` universe = 699).
USD-M futures monthly funding-rate files for every listed futures symbol. Fear & Greed: Hermes's own
`fng_alternative_me.json` (alternative.me, 2018-02-01..2026-11-02), previous UTC day's value and classification.
Two segments exactly as Hermes ran them: **disc** grid 2020-01-01..2022-12-31 23:00 (684 universe; events whose
outcome window runs past the grid have no outcome), **hold** grid 2022-11-01..2026-10-31 23:00 (699 universe; events
with trigger >= 2023-01-01). Periods by trigger year: 2020-21, 2022, 2023-26.

## Shared definitions (verbatim from Hermes's code)
- **Alert (ignition)**: 3h close return >= +10%, 3h quote volume >= 5x the mean hourly volume of hours t-170..t-3
  (>= 150 of 168 present), prior 7-day run (close t-3 / close t-171 - 1) <= +30%, that mean hourly volume >= $20,000,
  72h cooldown per coin. Entry = open of the next hour. Cost 0.3% per side.
- **Controls (Hermes)**: 5 per alert, same entry hour, random liquid coins not triggered within **+/-72h**, seed 7,
  needing 72h of data. This uses the future (+72h). **Corrected controls**: identical but excluding only triggers in
  the past 72h (t-72..t). Both are reported wherever a comparison with random coins is made.
- **Clue score** (6 common clues, as run_holdout_v1.py): >= 5 of 6 daily SMAs, SMAs stacked, within 15% of 200-day high,
  >= 50% above SMA100, .618/1.0 Fib cross of the 200-day and 50-day swings. **Strong = score >= 4.**
  **Uptrend (TREND)** = >= 5 of 6 SMAs and within 15% of the 200-day high (exposure_v1.py).
- **X4** = sell at +50% (hourly high touches entry x 1.5, filled at that price), else close of hour 336 (14 days);
  needs 90% of the 336 hours present.

## Validation gate (run first; if it fails, report and stop)
Same code on the downloaded data must reproduce Hermes's pushed numbers: disc alerts with outcome **5,267**, reach +30%
in 72h **17.5%**, net 72h mean **-4.1%**, controls **26,321**; hold alerts with outcome **6,971**, X4 mean **-2.95%**,
COMBO version A **968** trades, mean **+1.10%**. Pass = alert counts within 2% and those means within 0.5 points.

## Study 1, ENTRY_TIMING (chat 05:06 and 05:16)
Same alerts, same X4 exit counted from each entry's fill, same costs. Entries (A = alert hour close, t = alert hour):
E0 next-hour open. **L5/L10/L15**: limit buy at A x (1-x) during hours t+1..t+72; fill at min(open, limit); no fill =
no trade. **H6/H24** [GAP: "stays above"]: if close of hour t+6 (t+24) >= A, buy next open. **DIP_RECLAIM** [GAP]: low <= 0.95A
then a later close > A, both within t+1..t+72; buy next open. **BREAK_D1** [GAP: window]: first-day high D1 = max high of
t+1..t+24; buy when a high in t+25..t+96 exceeds D1, fill at max(open, D1). **EARLY** (separate detector): 1h close
return >= +5% on 1h volume >= 5x base, other filters as the alert, own 72h cooldown, next-hour entry; "becomes a full
move" [GAP] = a standard alert on the same coin within t..t+71.
Groups: all, strong, TREND. Reported: n, mean, median of X4, % of **good moves skipped** [GAP: good move = E0 trade
that reached +50%] = good moves with no fill. Shape: median 14-day peak gain and hours to peak from E0; median first
pullback [GAP] = lowest low of t+1..t+72 vs A, for all alerts and for good moves.
Hermes reported (mean X4): E0 +3.5/-5.0/-3.0; L15 +5.1/0.0/-0.2, skips 73-83%; BREAK_D1 +7.3/-4.3/-0.4, skips 45-66%;
EARLY +4.6/-4.3/-1.8, ~55% become full moves; strong+BREAK_D1 +15.9/-20.6/+1.4. Peak ~78h (2020-21) vs ~20-23h later,
typical later peak +15%. Winners' pullback 7-10% vs 13% all. Typical (median) trade loses in 2022 and 2023-26 for all.

## Study 2, PSYCH (chat 05:35)
Alerts by previous-day Fear & Greed class: median 14-day peak gain, median hours to peak, share reaching +50% within
14 days, mean X4; by period too. Funding [GAP: thresholds]: last funding rate settled at or before the alert hour
(USD-M perp of the same symbol); crowded longs >= 0.03% per interval, crowded shorts < 0, else normal; mean X4 per
group. Spike shorts (Study 5 SHORT_SPIKE trades) by funding group at entry: mean, and how many of the losses worse
than -50% fall in the crowded-shorts group.
Hermes reported: EF +15%/18h/16%/-4.8%; F +16%/28h/17%/-3.7%; N +14%/21h/17%/-3.3%; G +17%/43h/18%/-1.2%;
EG +27%/102h/29%/+8.2%; 2023-26 EF 8h vs EG 55h. Crowded longs +5.3%, crowded shorts -3.9%. Spike shorts with crowded
shorts -7.4%, 26 of 37 losses worse than -50%; normal funding +1.7%.

## Study 3, PATHS (chat 06:19, 06:21)
Every alert with a 30-day window (720h, 90% present), hour by hour, no exit. Gross touches vs entry price; day-14
result = net close of hour 336. P1 share touching +10/20/30/50% within 336h, and of those the share negative at day 14.
P2 share touching -10/-20/-30%, and of those the share positive at day 14. P3 share net >= +20% at day 14 without a
+20% touch by hour 72. P4 by hour-6 gain (-3..+3%, +10..+25%, >+25%): share that became a **kept runner** [GAP: touched
+30% within 14 days and kept >= half of the peak gain at day 14] and median return from hour-6 close to day-14 close.
P5 strength signs [GAP]: beat BTC over the first 24h; new high above the alert-hour high within hours 1-6; mean hourly
volume in hours 1-24 >= 3x base. Per sign: share reaching +50% within 14 days vs without, and median day-14 net.
P6 kept-runner share by mood and by period. Plus share of 30-day peaks inside the first 24h by period.
Hermes reported: P1 2020-21 75/57/42/26%, 2023-26 62/41/28/16%, negative at day 14 (2023-26) 54/40/31/21%;
P2 (2023-26) 83/49/21%, recovered 19/7.6/2.7%; P3 < 1 in 100; P4 12%/-8%, 25%/-14%, 31%/-25%; P5 23% vs 7%, -9% vs -5%;
P6 27% EG vs 9-14% others, 22% (2020-21) vs 11% (2023-26); first-24h peaks 41% (2023-26) vs 29% (2020-21).

## Study 4, SPIKE_DEFAULT (chat 06:36)
Exit grid [GAP: the 18 versions] = take-profit {+10, +15, +20%} x stop {-10%, -15%, none} x time limit {72h, 168h}.
TP on hourly high, filled at the target; stop on hourly low, filled at min(open, stop); a bar touching both counts as
the stop; time exit at the last close. **Extreme Greed** (previous-day class) alerts: TP doubled, time limit 336h.
Baselines: X4 and hold 72h. Same rules on controls (Hermes's and corrected). Main = TP15/SL10/72h; "best" = the
highest 2023-26 mean (descriptive). Hermes reported: X4 +3.5/-5.0/-3.0 (random 2023-26 -0.6); hold72 -2.0/-6.7/-3.8
(-0.9); main -0.9/-2.7/-2.0 (-0.7); best TP10 no stop -0.4/-2.2/-1.7 (-0.5); stops barely matter; EG adds ~0.2 pt;
alerts worse than random under every quick exit; negative in every year 2020-26.

## Study 5, BEAR (chat 05:10, 05:16)
Daily bars, 2018-01..2026-10. **BEAR** on day d = BTC close(d-1) < its SMA200(d-1); **ALT_BEAR** = fewer than 35% of
eligible alts above SMA50 at d-1. Eligible [GAP]: not BTC, >= 200 days of history, 20-day mean quote volume >= $500k.
Weekly arms (rebalance Monday, active only if the regime holds on Monday; weekly return close-to-close; turnover cost
0.3% x turnover): HOLD_BTC, HOLD_ALTS (equal weight), SHORT_ALTS, LEAD (long: close > SMA50 and SMA200), WEAK_SHORT
(short: below SMA20/50/100/200, >= 40% under 200-day high, 7-day return < 0), LS (half LEAD long, half WEAK short),
SPIKER_SHORT (short: a +30% close-to-close day in the past 20 days). Compounded over regime weeks, floored at -100%.
Event arms (entries only on BEAR days): SHORT_SPIKE (a +30% day; short that close; exit at the first close >= 1.3x
entry, else close of day +10), SHORT_FAILED (a +30% day, not TREND, next close lower; short that next close; same
exit), LEADER_DIP (LEAD coin down 20% over 3 days; buy close; hold 10 days), FNG_BTC_10/20 (previous-day F&G <= 15;
buy BTC at the close; hold 10/20 days; no overlap), CAPITULATION (<= 10% of eligible alts above SMA50; buy all at the
close; hold 10 days; no overlap). Cost 0.3% per side. **Proxy version**: every coin shortable, short borrow 0.03%/day
[GAP]. **Perp version**: shorts only where a USD-M funding file exists for that month, and the short receives (pays)
the summed funding over the hold. Periods by entry: 2018-20, 2021-23, 2024-26.
Hermes reported: 214 BEAR weeks; cash beat almost everything; HOLD_BTC -13% (max drawdown 67%); SHORT_ALTS -93%
(perp -84%); LEADER_DIP -8.7%/trade; CAPITULATION -1%; SHORT_SPIKE wins 66%, median +12%, worst -488%, proxy +1.5%,
perp -4.0%/trade; SHORT_FAILED proxy -1.3%, perp -4.3%; FNG_BTC_20 +2.6% avg, 60% wins, 42 trades, positive in all
three periods; SPIKER_SHORT proxy "huge", perp -97% (BEAR) / +116% (ALT_BEAR, all from 2024-26, -49% in 2021-23);
LS perp -55%.

## Not reproducible here
- **info_magnet_v0** (Upbit listing notices): Upbit's API returns Cloudflare 403 to this environment; not circumvented.
  The token-unlock source needs a paid plan. Recorded as NOT RUN, with Hermes's plan transcribed.
- **JUDGMENT_POLICY_v0**: a policy, not a test. Transcribed from the chat, labelled as such.
- **clue_mechanisms_v1**: Hermes wrote it but never ran it. Not reproduced.

## Reading (fixed now)
Per headline claim: **REPRODUCED** (same sign and the same conclusion, size roughly similar), **PARTLY** (same
direction, materially different size, or only some sub-claims hold), **NOT REPRODUCED** (opposite sign or the
conclusion fails). Validation-gate numbers must match as stated above. Run once; any correction becomes a new file.
