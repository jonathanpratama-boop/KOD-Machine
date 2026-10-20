# Quant engine, 2005-2019: a multi-signal walk-forward test (pipeline demonstration)

Written 2026-10-20 and committed before the run. Historical research only: never prospective performance; no orders.

## Purpose, stated plainly
KOD tested one idea at a time and asked each to win alone, the hardest version of the problem. Quant funds blend many weak
signals. This run builds and tests that machinery end to end: seven monthly features, a walk-forward combined score,
rank-IC, a long-short spread, factor-adjusted alpha, and a market-impact cost and capacity model.

**It cannot produce evidence of a tradable edge**: the universe is today's US listings only (survivor-only), so a model
that learns "volatile stocks did well" is learning survivorship. The run therefore includes a survivorship stress
(gate G4) and, whatever the verdict, the finding is labelled NON-EVIDENCE until the test is repeated on a
survivorship-free dataset. The value of this run is that the machinery is correct, tested, and ready for that data.

## Data
- Prices: the 2004-2019 Yahoo pull already on file (data/raw/yahoo_us_2005, manifest yahoo_us_2005-20261019T194544Z.jsonl),
  loaded by US_LOWVOL_MOM_2005_2019/run.py `load()`. These are the same bars used by the earlier low-vol / momentum
  test (all three hypotheses failed there), so this is **not** fresh data for those two features; the new questions
  are the combination and the factor-adjusted alpha.
- Factors: Kenneth French daily Mkt-RF, SMB, HML, MOM and RF (data/raw/french/factors_daily.csv.gz; its sha256 is in
  data/manifests/french_factors-*.json and is checked before the run).
- Eligibility, entry and exit exactly as US_LOWVOL_MOM_2005_2019: month-end formation 2005-01..2019-11, at least 252
  sessions of history, median 60-session dollar volume >= USD 2 million, entry at the close of the next session, exit
  at the next month-end close, holding-period return clipped to [-90%, +200%]. Eligibility does not use the forward return.

## Model (fixed now)
Seven features, each rank-normalised across eligible stocks each month: 12-1 month momentum; 1-month reversal; minus
60-session volatility; proximity to the 252-session high; log median 60-session dollar volume; the largest daily
return in the last 21 sessions; log of median 20-session over median 120-session dollar volume.
Combination: expanding-window ridge regression (lambda = 100) of the rank-normalised forward return on the seven
rank-normalised features, trained on months <= t-2 only (embargo of one month), at least 24 training months; scores
start in 2008-01. One model, one setting: no tuning, no alternative specifications.

## Gates (all four must hold; fixed now)
- **G1 information coefficient.** Mean monthly rank-IC of the combined score is positive, with Newey-West (6 lags)
  t >= 3.0 (the project hurdle in research/QUANT_GRADE for a result that follows 18 counted tests), and positive in at least
  9 of the 12 calendar years 2008-2019.
- **G2 cost-aware spread.** The mean monthly top-quintile minus bottom-quintile spread, after the square-root market-impact
  model (half-spread 5 bp per side, impact 0.7 x daily volatility x sqrt(trade / average daily dollar volume)) at a
  USD 100,000 book (half long, half short), is positive.
- **G3 factor alpha.** The regression of that gross spread on Mkt-RF, SMB, HML and MOM (holding-window factor returns
  compounded from daily data) has a positive intercept with Newey-West (6 lags) t >= 3.0.
- **G4 survivorship stress.** Restricted to the larger half of eligible stocks by dollar volume each month (where
  survivorship bias is much smaller), the mean rank-IC is positive with Newey-West t >= 2.0.

## Also reported (not gated)
Per-feature IC; average ridge weights; quintile returns; turnover; net spread at USD 10k, 100k, 1M, 10M and 100M and the
break-even book size (capacity); long-only top quintile minus the universe after costs. The spread is long-short:
shorting small US stocks through eToro is not established as possible, so the long-only line is the one a retail account
could mirror.

## Reading the result (fixed now)
- All four gates pass: the machinery is worth running on survivorship-free data; this result alone is not evidence.
- Any gate fails: recorded as FAIL. The trial is added to the register (research/QUANT_GRADE/trials) either way.
- The hurdle for any future result stays at least t >= 3.0, and rises with every test added.

## Known biases (stated before the result)
Survivor-only universe; one era (2005-2019, including 2008-09); assumed impact constants (c = 0.7, 5 bp half-spread); Yahoo
adjusted prices; the earlier low-vol / momentum test already looked at two of the seven features on these bars.
