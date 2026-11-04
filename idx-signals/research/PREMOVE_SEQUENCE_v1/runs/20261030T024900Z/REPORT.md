# Pre-move sequence benchmark

Retrospective chronological model test on previously studied history. No profitability, live performance or untouched-holdout claim.

Four methods share each population's daily candidate pool and five-name budget. Unknown future outcomes remain selectable.

| Population | Method | Alerts | Up hits | Known false alerts | Censored | Precision lower bound | Episodes caught / known | Median lead days |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | simple | 1825 | 30 | 1742 | 53 | 1.64% | 14 / 926 | 5.0 |
| all | g2 | 1825 | 31 | 1744 | 50 | 1.70% | 14 / 926 | 5.0 |
| all | summary | 1825 | 61 | 1738 | 26 | 3.34% | 34 / 926 | 4.0 |
| all | sequence | 1825 | 80 | 1717 | 28 | 4.38% | 48 / 926 | 3.5 |
| early | simple | 1825 | 25 | 1742 | 58 | 1.37% | 19 / 911 | 5.0 |
| early | g2 | 1825 | 25 | 1742 | 58 | 1.37% | 19 / 911 | 5.0 |
| early | summary | 1825 | 60 | 1739 | 26 | 3.29% | 35 / 911 | 4.0 |
| early | sequence | 1825 | 76 | 1722 | 27 | 4.16% | 46 / 911 | 4.0 |

## Paired uncertainty

Ten-day moving-block bootstrap; differences in daily shortlist hit rate, percentage points. These intervals are not profit intervals.

- all, sequence_minus_simple: 2.74%; 95% interval [1.15%, 4.55%].
- all, sequence_minus_summary: 1.04%; 95% interval [-0.06%, 1.97%].
- early, sequence_minus_simple: 2.79%; 95% interval [1.20%, 4.38%].
- early, sequence_minus_summary: 0.88%; 95% interval [-0.22%, 1.81%].

## What the result does and does not establish

The sequence model adds eight train-fitted PCA components of recent return/range/volume sequences to a fourteen-feature summary baseline. This is a lightweight learned-sequence challenger, not Kronos or a rerun of E5's full feature model.

The early population excludes names already up 10% today or 20% over five days. G2 cannot trigger in that population, so its fixed-budget ranking reduces to the simple comparator there.

Targets use the next open and future closes. Intra-day path order, slippage, stops, transaction costs and executable profits are not evaluated. Missing and truncated terminal bars censor outcomes; recall covers only observable episodes. Extreme raw price changes are preserved and may include corporate unit changes.

The universe is recovered from today's archive catalog. Removed/unavailable instruments and source revisions can bias results. Train/calibration/test periods are chronologically separated, but 2023 has been used in earlier KOD research. A new prospective run is needed before claiming independent confirmation.
