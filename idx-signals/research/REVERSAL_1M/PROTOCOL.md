# Short-term (1-month) reversal on survivorship-free data

Written 2026-10-21 and committed before the data is fetched or any value of it is read. Historical research only: never
prospective performance; no orders.

## Why this test
The quant engine run (research/QUANT_ENGINE_2005_2019) reported, outside its gates, that the 1-month reversal feature had
mean rank-IC -0.023 (Newey-West t -3.45) on US 2005-2019: last month's winners did worse next month than last month's
losers. That run's universe was today's listings only (survivor-only), so the lead may be survivorship. This test asks
the same question on data that includes the stocks that later died, with every number below fixed first.

## Data
- Kenneth French's **short-term reversal factor**, monthly (F-F_ST_Reversal_Factor_CSV.zip): built from CRSP, which includes
  delisted stocks. It is the value-weighted return of low prior-month-return stocks minus high prior-month-return stocks
  (six size x prior-return portfolios, NYSE breakpoints). Fetched by `fetch.py`, hashed in data/manifests/french_strev-*.json.
- Factors for the alpha: the daily Mkt-RF, SMB, HML, MOM and RF already on file (data/raw/french/factors_daily.csv.gz,
  manifest french_factors-20261020T182212Z.json, sha256 checked before the run), compounded to calendar months.
- **Sealed:** every month from 2024-01 onward is dropped on load and never read (US holdout). 2023 is used validation and
  appears only in the out-of-era check below.

## Gates (all four must hold; fixed now)
- **G1 survivorship-free confirmation.** Mean monthly ST_Rev, 2005-01..2019-12 (the lead's era), is positive with
  Newey-West (6 lags) t >= 3.0 (the project hurdle, research/QUANT_GRADE, 20th counted test).
- **G2 not a known factor.** The intercept of ST_Rev on Mkt-RF, SMB, HML and MOM over the same months is positive with
  Newey-West (6 lags) t >= 3.0.
- **G3 survives a cost assumption.** Mean monthly ST_Rev minus 0.80% is positive (full monthly turnover of both legs:
  4 side-trades x 0.20% per side). The factor is gross of all costs; this is an assumption, not a measurement.
- **G4 out of era.** Mean monthly ST_Rev, 2020-01..2023-12, is positive (sign only; 48 months cannot carry a t test).

## Also reported (not gated)
Mean, NW t and share of positive months for 1963-07..2004-12 (the era of the published papers, Jegadeesh 1990 and Lehmann
1990, so not independent evidence); per-year means 2005-2019; the break-even cost per side (mean / 4); factor betas.

## Reading the result (fixed now)
- All four pass: the reversal is not survivorship and clears costs at the assumption; next step is a cost-aware test with
  measured spreads on stock-level survivorship-free data (to buy), still historical only.
- G1 fails: the -3.45 lead does not hold on survivorship-free data in the same era; it is recorded as survivorship or
  noise and dropped.
- G1 passes but G3 fails: the effect is real but is a cost trap at retail turnover; dropped as a trading idea.
- Any gate fails: recorded as FAIL. One run; any change is a new experiment. The trial is added to the register either way.

## Known differences and biases (stated before the result)
The factor sorts on the prior calendar-month return and holds the next calendar month, with no skip day; the engine's
feature used a 21-session return and entry at the next close. ST_Rev is value-weighted (large stocks dominate), while the
engine's IC weighted every stock equally, so a small-stock effect may show weakly here. Costs are assumed.
