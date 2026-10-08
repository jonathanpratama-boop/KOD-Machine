# The unit quarantine is outcome-correlated (2026-10-08)

The three repair versions differ only in which names lack corroborated split records and are
therefore left out of both the detector and the matched controls:

| Version | Quarantined | Fill A: rule vs matched (p) | Fill B: rule vs matched (p) |
|---|---:|---|---|
| v1 (`repair/`, text rule incl. ratio-only) | 228 | -4.85% vs -1.13% (1.00) | -4.41% vs -1.21% (1.00) |
| v2 (`repair_v2/`, strict text rule) | 891 | -2.23% vs -0.27% | -1.69% vs -0.30% |
| v3 (this directory, + SEC share counts) | 669 | -1.75% vs -0.46% (0.97) | -0.97% vs -0.75% (0.62) |
| none (R1b: every name, provider units) | 0 | -5.27% vs -1.32% (1.00) | not run |

In R1b's scored trades, names that v3 quarantines averaged **-9.17%** (median -15.2%, 583
trades) against -1.75% for the rest (645 trades); v1's quarantine shows the same (-8.64% vs
-4.85%). The quarantined names are mostly companies that reverse-split after 2023, which is a
trait of names that collapsed. Excluding them removes the worst outcomes, so the rule's
measured shortfall shrinks as the evidence rule tightens. That is selection, not measurement.

What units actually affect: returns are ratios of adjusted prices and need no units; only cost
tiers, whole-share sizing and the matching price band do. The largest tier difference is
1.45% per side, far smaller than the -7.4 point gap above. Excluding names to protect against
units is the larger error.

Recommended next step (not yet run): keep every name, and replace exclusion by a bound. For
names whose split records are not corroborated, run with the provider's units and again with
the most and least costly tier, on both the detector and the controls, and report the range.
Corroboration then narrows the band instead of changing the population.
