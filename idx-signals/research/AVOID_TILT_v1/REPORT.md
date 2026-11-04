# AVOID_TILT_v1 — result (one frozen run, 2026-11-02)

**Frozen verdict: PASS.** In the holdout (Jan 2024 – Oct 2026, 33 months), a long-only, equal-weight, monthly US
portfolio that excludes names with a +30% day in the prior 20 sessions beat the same portfolio without the exclusion by
**+0.16% a month net of costs** (one-sided 95% lower bound +0.12%), winning 85% of months, in every year (2024 +1.3,
2025 +2.5, 2026 +1.4 points). Discovery (2020-07 – 2023-12) agreed: +0.10% a month (lower bound +0.01%).

| Annualised, net | Discovery A | Discovery B | Holdout A | Holdout B |
|---|---:|---:|---:|---:|
| Return | 9.0% | 10.4% | 8.4% | 10.4% |
| Sharpe | 0.49 | 0.55 | 0.63 | 0.76 |
| Max drawdown | 32.3% | 30.6% | 15.1% | 14.1% |

**Mechanism.** The excluded names (about 47 of 3,048 a month in the holdout) returned **−9.5% on average the next
month** (median −11%), against +0.9% for the names kept. Recent big spikers keep decaying for weeks. This is a
rediscovery of the published "lottery stock" / MAX effect (Bali, Cakici and Whitelaw, 2011), and it was still present
in 2024–26.

## Post-run robustness (not part of the frozen verdict; `post_run/robust.py`)

| Variant, holdout | B − A per month | Lower bound | Excluded names' next month |
|---|---:|---:|---:|
| Frozen rules | +0.16% | +0.12% | −9.5% (median −11.0%) |
| Drop spikes ≥ +100% (likely data errors) | +0.10% | +0.07% | −7.5% |
| Liquid only (median $vol ≥ $20m) | +0.04% | +0.01% | −4.1% |
| 500 most liquid names | +0.03% | −0.01% | −2.2% |

- The effect is partly inflated by bad prints (about a third of it), but survives without them.
- It is not driven by a few names: the excluded group's median is as negative as its mean.
- **It shrinks with size.** It is small in liquid stocks and gone in the 500 largest: it lives in small and mid caps.

## Is it profitable?

**Not as a stand-alone strategy.** Over the same holdout months:

| Holdout, annualised | Return |
|---|---:|
| B (this strategy) | 10.4% |
| A (same basket, no exclusion) | 8.4% |
| SPY (S&P 500) | 20.2% |
| RSP (S&P 500 equal weight) | 12.4% |
| IWM (Russell 2000) | 13.8% |

The exclusion adds about 2% a year to an equal-weight all-cap basket, but that basket lagged every simple index fund in
2024–26 (and these figures are survivor-biased upwards). The tilt is real and repeatable; the vehicle it improves was
the wrong one.

## What it is good for

A **don't-buy rule** to apply to whatever stocks you would hold anyway: skip any small or mid cap that rose 30%+ in a
day within the last month. Expected benefit: avoiding a group that falls about 5–10% over the following month. Zero cost
to follow, long-only, monthly, stress-free.

## Limits

Survivor-only prices (understates the benefit of excluding spikers, overstates A and B against index funds); dilution
flag had data only in discovery; open/close prints, not fills; the holdout years were used by other KOD studies for other
questions. Next clean test: the live paper record, applying the frozen rule to new months.
