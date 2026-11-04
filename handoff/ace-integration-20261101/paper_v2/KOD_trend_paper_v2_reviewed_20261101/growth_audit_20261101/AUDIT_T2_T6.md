# T2/T6 audit, 2026-11-01

## Verdict

T6 is a conditional model illustration, not a forecast or proof of necessary leverage. The parametric arithmetic is reproducible: all 25 cells exactly match committed rounded output using the original seed and only the reviewed pure simulation functions. No market loader or historical strategy was executed and no raw return/bar file was read. ETH bootstrap numbers were checked against aggregate JSON and code only, not independently reproduced.

Source branch: `claude/idx-signals-test-repo-ds0jw7`; `run_t6.py` blob `1f36f8030a9ac07a26c6f09137cd4dc35e670f98`; `results_t6.json` blob `29011073e919702cea11d4e122ae5d1c4e00fd73`; `RESULT.md` blob `9d99e35a22e6e61ba453ea854a60c684340a1dc1`.

## What the probabilities mean

- Parametric inputs: independent normal simple daily returns; daily mean S*0.20/365, daily SD 0.20/sqrt(365), multiplied by constant leverage and floored at -100%; 20,000 paths, 365 days. Daily rebalancing and fixed parameters are assumed.
- Sharpe 3 / 5x reproduced: touch 10x 64.20%, peak-to-trough 50% drawdown sometime 26.10%, 10x before first such drawdown 58.98%. They are not contradictory: reaching 10x first does not prevent a subsequent halving. Terminal >=10x is 57.43% on the same synthetic draws.
- After correcting initial equity in the high-water mark, the same draws give DD 26.15%, target before DD 58.97%, and target sometime with NO 50% DD anywhere in the year 55.07%. This small numerical correction does not validate the real-world forecast.
- ETH SMA 10/40, 3x committed bootstrap: touch 10x 26.91%, peak-to-trough 50% DD 96.96%, finish <=0.5x 28.67%, target before first DD only 10.52%. A 50% decline from a later high is not necessarily a decline below half initial capital. Touching $10,000 is not finishing with $10,000 or locking it in.
- 20,000 paths reduce conditional simulation error (roughly <=0.7 percentage point 95% binomial half-width), not uncertainty in the strategy's mean, tail risk or future market regime. Reported zero paths is not impossibility.

## Definite implementation defects

1. `run_t6.py:17-19`: cumulative maximum omits initial equity 1. A synthetic path [-60%, 0, 0] returns 0% DD probability instead of 100%. An immediate total loss also creates 0/0 drawdown values. Include initial equity or floor the running high at 1. This same initial-wealth convention appears in `lib.stats`.
2. `run_t6.py:54`: `rng.integers(0, len(net)-20)` excludes the final valid length-20 block. Valid final start is len(net)-20; high is exclusive, so use len(net)-20+1. Minor endpoint bias, not evidence that headline magnitudes are materially wrong.

## Model and interpretation limits, not demonstrated arithmetic errors

- ETH uses a moving 20-day BLOCK bootstrap, not iid daily resampling. Within-block dependence and observed extreme days are preserved; longer market regimes and dependence across block seams are not. It cannot generate tail events absent from the finite source history. It resamples completed strategy P&Ls, not market paths with signals and fills re-executed consistently at seams.
- It selects the T1 variants that passed and resamples their entire development-plus-validation histories, fixing that selected distribution as if known. It does not include winner-selection/multiplicity uncertainty, parameter estimation uncertainty, drift decay or a fresh holdout. Correlation between variants is not a multiple-testing correction.
- Bootstrap scales already net spot returns, but explicitly subtracts ZERO borrowing cost. It has no incremental constant-leverage rebalancing turnover costs, perp funding/basis if perps implement leverage, margin/maintenance or intraday liquidation model, or execution stress. Flooring daily loss at -100% imposes limited liability but is not an exchange liquidation model; negative equity is excluded by assumption.
- Daily endpoints miss intraday barrier crossings and liquidation. Equity paths continue after touching either reporting barrier; there is no target-exit or stop-loss execution rule.
- `RESULT.md:104-108` overclaims necessity: Sharpe alone does not determine target probability. Distribution, volatility, dependence, costs, leverage and horizon matter. Even in the same normal model, unlevered volatility 40% at 2.5x yields the same levered law as 20% at 5x with the same Sharpe. The coarse tested grid cannot establish a universal required Sharpe/leverage pair.
- No 4- or 5-year simulation is present. The asserted 8-25x median is an extrapolation not evidenced by `run_t6.py`/results JSON. Exponentiating one-year medians is not generally the multiyear median and assumes persistent return opportunities.
- The frozen protocol specifies 252 days, S up to 2, and leverage through 5x; code uses 365, adds S=3 and 10x. AUDIT.md acknowledges deviations, so the highlighted S=3 result is not part of the original grid.

## T2 carry accounting

`run_t2_t3_t4.py:31-41` computes mean funding rate*1095 minus 0.005 for one round trip each leg annually. Thus BTC 6.68% / ETH 6.79% validation figures are funding-rate proxies net of those assumed fees per matched notional, not demonstrated returns on all deployed capital. Funding cashflows equal rate times contemporaneous marked notional. A true fixed-quantity cash-and-carry account needs both spot/perp P&L, funding cashflows, fees, collateral cashflows and financing divided by committed equity. A constant-notional interpretation requires rebalancing.

Illustrative denominator only: cash-funded spot N and separate short collateral M require N+M capital; before excluded cashflows, rate proxy/(1+M/N). If M=N, 6.68%/6.79% becomes 3.34%/3.395%. This is not a proposal or a universal collateral assumption; cross-margin arrangements differ.

Basis P&L is explicitly excluded in protocol. Margin calls, liquidation, financing/opportunity cost, collateral return, depeg/counterparty risk and extra hedge/rebalance costs are not modeled. One-entry/one-exit fees are an assumption, not realistic trading-cost proof. Comparing the output directly with stablecoin-lending APY is not apples-to-apples. `load_funding` drops funding_interval_hours and T2 assumes three payments/day; aggregate BTC/ETH yearly counts are compatible with eight-hour sampling, so no specific annualization error is established without inspecting intervals (not done here).

## Primary-literature checks

- Han/Kang/Ryu, conclusion p73: maximum observed Sharpe about 1.5, explicitly best-case/data-snooping and changeable in future. It does NOT establish a universal practical ceiling at 1.1-1.2 (nor a universal ceiling at 1.5). https://acfr.aut.ac.nz/__data/assets/pdf_file/0009/918729/Time_Series_and_Cross_Sectional_Momentum_in_the_Cryptocurrency_Market_with_IA.pdf
- He et al. 2024: retail Sharpe 1.8 is a strategy entering/exiting deviations from no-arbitrage bounds, not unconditional funding averages. Paper explicitly discusses borrowing costs, no guaranteed convergence, and temporary losses/liquidation. https://arxiv.org/html/2212.06888v5
- Binance defines funding amount as marked notional times rate and notes funding intervals may change. https://www.binance.com/en/support/faq/detail/360033525031
- MacLean/Thorp/Ziemba (2010) warns about mean-estimation error and finite-horizon substantial losses; its asymptotic theory is not evidence for these multiyear point forecasts. https://escholarship.org/content/qt5mr5k8qj/qt5mr5k8qj.pdf

Artifacts: `synthetic_check.py`, `synthetic_check_results.json`. No remote writes, CI, credentials, trading, or raw historical reads. A branch-metadata GET was rejected for invalid encoded repository path; file/blob evidence remained accessible and sufficient, no bypass attempted.
