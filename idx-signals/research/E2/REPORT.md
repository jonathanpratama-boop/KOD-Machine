# E2 results: US equities and crypto (protocol KOD-GLOBAL-E2-v1)

Historical research only. Nothing here is prospective performance, and none of it shows
that anything can be predicted profitably. The holdout (2024-01-01 onward) has not been
touched. US results are survivor-only (names delisted before 2026-10-08 are missing), which
inflates US base rates; the detector-vs-matched-control comparisons carry the same bias on
both sides.

Order of events, each a pushed commit (GitHub's own run records date them):
`a155cf0` protocol, before any analysis → `4e1fc5d` crypto discovery → `e5a1be2` US discovery
and the freeze of G2_RET30 for both markets → `21345b1` validation (2023) → `826ec76` crypto
trading run → `7be55d4` US trading run.

## Base rates (eligible ticker-days, non-winners included)

| Market, period | Ticker-days | +30% in 5 sessions | +50% | +100% | Episodes 30 / 50 / 100 |
|---|---:|---:|---:|---:|---|
| US discovery 2020-07..2022 | 2,670,084 | 1.13% | 0.37% | 0.091% | 8,946 / 2,833 / 697 |
| US validation 2023 | 1,151,102 | 1.26% | 0.43% | 0.107% | 4,100 / 1,459 / 351 |
| Crypto discovery 2020-07..2022 | 221,468 | 5.56% | 2.00% | 0.43% | 3,333 / 1,322 / 284 |
| Crypto validation 2023 | 120,506 | 2.41% | 0.89% | 0.14% | 730 / 275 / 48 |

US: the +30% rate falls with price (6.0% under $1, 2.8% $1-5, 1.0% $5-20, 0.9% above $20).
Crypto: 2021 (9.3%) was three times 2022 (2.8%); validation (2023) was a quiet year.
For comparison, IDX (E1) was 1.88% in discovery and 1.16% in validation.
Files: `<market>/discovery/base_rates.csv`, `<market>/validation/base_rates.csv`, `*/episodes_E*.csv`.

## First 100 events and matched controls

Per market, the first 100 +30% episodes of discovery in date order (US 2020-07-01..07-13,
crypto 2020-07-01..08-10), each with five same-session non-event controls from the same price
band and liquidity quintile (`first100_events.csv`, `first100_controls.csv`;
`all_E30_controls.csv` for every discovery episode). No share or supply counts exist, so
market cap is not matched.

## Weak signals at the episode start (`<market>/discovery/signal_stats.csv`)

Matched-set AUC over all discovery episodes (0.5 = no information):

| Signal | US | Crypto | IDX (E1) |
|---|---|---|---|
| 20-session volatility | **0.78** (0.77-0.79) | 0.56 (0.54-0.57) | 0.68 |
| 60-session drawdown | 0.25 (deep drawdowns precede repricings) | 0.41 | 0.40 |
| day return | 0.31 | 0.39 | 0.37 |
| volume surge | 0.52 | 0.45 | 0.50 |
| opening gap | 0.46 | 0.50 | n/a |
| breakout, IGNITION analogue | 0.48-0.49 | 0.48 | 0.49-0.50 |

As on IDX, the day before a repricing starts mostly looks ordinary, except that the name was
already volatile (strongly in the US, where survivorship also favours beaten-down names that
recovered). Volume surges carry no information on the start day.

## Detector (pre-registered selection on discovery, `<market>/discovery/detector_selection.csv`)

All eleven G rules were admissible in both markets. G2_RET30 (a +30% day) had the highest
+30% lift in both: US 3,289 flags, precision 15.5% (Wilson lower bound 14.3%), 13.7x base;
crypto 1,394 flags, 17.6% (15.7%), 3.2x base. It was written into `moonshot_g.SELECTED` and
pushed before any validation number was computed. Like IDX's F1_ARA, it flags repricings that
have already started.

## Validation 2023 (`<market>/validation/result.json`, `flags.csv`)

| | US | Crypto | IDX F1_ARA (E1) |
|---|---|---|---|
| flags | 1,581 | 298 | 972 |
| +30% precision (95%) | 15.4% (13.7-17.2%) | 18.5% (14.5-23.3%) | 18.3% |
| vs matched random names | 2.8%: **5.4x**, p = 0.005 | 4.0%: **4.6x**, p = 0.005 | 9.3x, p = 0.005 |
| +50% / +100% vs matched | 7.9x / 11.6x | 6.3x / 11.2x | 11.7x / 12x |
| +30% episodes caught before their peak | 0.9% | 0.1% | 9.8% |
| median 5-session return after a flag | -10.3% (matched: -0.2%) | -11.5% (matched: +0.1%) | |

p = 0.005 is the floor at 200 draws. **Discovery skill: yes**, in every market: a +30% day
is followed by another +30% within five sessions five times as often as for comparable names.
**Coverage: almost none**: the flag fires inside a repricing, so it catches very few
repricings before most of the move.

## Trading test on the validation window (idxsig harness, market profile)

Buy at the next session's open, hold 5 sessions, costs by price tier (US) or 0.1% fee + 0.1%
slippage per side (crypto), against entries in matched random names on the same sessions:

| | US (`results/runs/20261008T060443Z_MOONSHOT_E2_US_D1_v1`) | Crypto (`results/runs/20261008T005732Z_MOONSHOT_E2_CRYPTO_D1_v1`) |
|---|---|---|
| attempts / filled / scored | 1,496 / 1,148 / 1,099 | 270 / 269 / 264 |
| average net per trade | **-3.65%** | **-1.90%** |
| median net | -7.7% | -10.5% |
| hit rate | 36% | 31% |
| matched random entries | -0.60% (95% band -1.7%..+0.7%) | +1.42% (-0.1%..+3.2%) |
| one-sided p (detector better) | 1.0 | 1.0 |

**Execution: no**, in either market, as on IDX (-4.06% vs -0.53%). Most +30% days fade over
the next week; the minority that keep running do not pay for the rest at these entries.

## What this means for decisions

Across three markets and three detectors, "a big up day" reliably marks names with a fat right
tail, and buying them the next day reliably loses money. The paper policy therefore passes on
every candidate (`paper/`) while recording its full plan, so the counterfactual is scored.
Anything that tries to monetise the tail (a different entry, exit or filter) has to be designed
on discovery data and judged prospectively: validation is used, and the holdout is reserved for
one final test.
