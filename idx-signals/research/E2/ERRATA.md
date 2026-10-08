# E2 errata

Found by the author after the results were pushed. Nothing earlier is edited (the research
directory is append-only); each item says what was wrong, which way it moves the result, and
what changed in the code.

## 1. US price levels are not point-in-time (2026-10-08)

Yahoo rescales a name's whole history at every split. A stock that traded at $0.30 in 2023
and reverse-split 1-for-1000 later appears in the panel at $300. Returns are ratios and are
unaffected, so detection results (precision, lift, R5max, episodes) stand. Anything that uses
the price level is wrong for names that split after the date:

- **Trading run** (`results/runs/20261008T060443Z_MOONSHOT_E2_US_D1_v1`): 1,011 of 1,676 flags
  (60%) are names that reverse-split later. All 154 `SKIP_LOT` attempts are among them (adjusted
  price above the $5,000 notional). 582 of 1,099 scored trades sat in the wrong cost tier.
  Re-costed at the price actually traded: **average net -4.47%**, not -3.65%. The matched random
  baseline was not re-costed (its names are less affected: 4% `SKIP_LOT` vs 10%). The conclusion
  (the plan loses against matched random entries) is unchanged and, if anything, stronger.
  Reproduce: `python3 research/E2/diagnostics/us_reverse_splits.py` → `diagnostics/us_reverse_splits.json`.
- **Base rates by price band** (`US/*/base_rates.csv`): names are banded by adjusted price, so
  sub-$1 names that later reverse-split are counted in higher bands. The all-names rates stand.
- **Matched controls**: price bands for matching use adjusted prices; the controls are matched
  on the wrong band for the same names.

Crypto is not affected (Binance klines are not rescaled). IDX (E1) used the IDX mirror's own
prices with an explicit corporate-action registry, not Yahoo.

Fix for new work: price-level features, cost tiers and lot sizing need the price as traded
then: adjusted price x the product of split ratios after the date (Yahoo reports the split
events; `diagnostics/us_reverse_splits.py` shows the computation). The harness does not do
this yet; until it does, US runs must be read with this erratum.

Paper ledger: decisions are made on prices pulled that day, so they are in that day's units.
Scoring could have broken if a name split inside its window (the plan's stop and chase prices
would be compared with rescaled prices); `paper.score` now rescales the plan by the ratio of the
signal-day close now to the close recorded then (`price_scale` in each OUTCOME), and charges
costs at the price actually paid. Fixed before any outcome was scored.

## 2. US and crypto run reports describe price bands in rupiah (2026-10-08)

The "Matched controls" table of both E2 run reports reads "close <= Rp200 / <= Rp5,000 /
above". The matching itself used the market's own edges ($1/$5/$20; 0.01/1/100 USDT) and the
match key has room for four bands (base-8 digits). Label only; new reports print the market's
bands.

## 3. A diagnostic looked at validation data after the fact

The breakdown in item 1 (flags in names that later reverse-split: -6.5% average net;
others: -0.3%) was computed on the 2023 validation window. A later reverse split is not known
on the signal date, so it is not a filter, and validation must not be used to design one. Any
point-in-time proxy (sub-$1 price, a prior reverse split, a financing filing) has to be built
on discovery data and judged forward or on the holdout.
