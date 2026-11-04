# Addendum 3: the arithmetic, and the pooled DOCUMENT_CLASS test (frozen 2026-10-29)

Owner: "I need you to solve the arithmetic problem. Make a solution if there isnt one." The problem: a family's time
to an answer is `(t_min x sd / edge)^2 / events per year`, and at the lab's event rates the single families take years.
This addendum records what was measured, which levers are legitimate, and the one new test it freezes. Nothing already
frozen changes. `prereg_3_document_class.json` is the normative file; `POWER_v1/POWER.md` holds the numbers.

## What was measured (design-stage variance, from a test already reported)

Test 26 (`research/US_INSIDER_BUY/results_stage1/`) scored 2,964 insider-purchase events against 200 matched controls
each. Its RESULT.json already reported the means, the winsorised means, the hit rates and the split by price band. The
new reading here is of the **spread**, which a power calculation needs; no new effect estimate was taken from it.

| Hold 20 sessions | n | mean excess | sd of excess |
|---|---|---|---|
| All events | 2,964 | +1.01% | 0.156 |
| Winsorised at the 5th and 95th percentiles | 2,964 | +0.54% | 0.107 |
| Price band 3 (signal close >= USD 20) | 1,496 | +1.05% | 0.098 |
| Price band 2 (USD 5-20) | 986 | +0.54% | 0.150 |
| Price band 1 (USD 1-5) | 407 | +1.99% | 0.223 |
| Price band 0 (under USD 1) | 75 | +1.36% | 0.457 |
| Top-executive buyers | 834 | +1.41% | 0.171 |
| Hold 60 sessions, all events | 2,964 | +1.80% | 0.308 |

The hit rate at hold 20 was **46.5%** beside the positive mean. The prereg_2 spread of 0.21 was conservative; 0.156 is
the measured figure at hold 20.

## What the numbers say

1. **The win rate is the wrong instrument for a skewed signal.** Fewer than half of insider-purchase events beat their
   controls, yet the mean is positive: the edge is a minority of large winners. A win-rate primary on such a family
   fails by construction. FORM4 and FORM4_SHARP carry WIN_RATE as a frozen second primary and that stays as frozen;
   the class test below uses the mean only and reports the win rate descriptively.
2. **Noise is the cheapest lever, and price is the cheapest noise filter.** Above USD 20 the same edge sits at 40% of
   the variance, so the same certainty needs 40% of the pairs. Winsorising cuts the spread too but cuts the edge more.
3. **Hold 20 beats hold 60 on signal-to-noise** for the plain family (2,100 pairs against 2,600 at a 1.0%/1.8% edge);
   for the top-executive subset the two are about equal. FORM4_SHARP's frozen H60 primary stands.
4. **Rate is the lever that turns years into months**, and pooling is the only free way to raise it.
5. **The t >= 3 floor costs about 40% more pairs than a conventional one-sided 0.01 test.** It is the lab's standing
   rule after thirty-five counted tests and is kept; the cost is stated, not paid down.

## The one new test: DOCUMENT_CLASS

A pooled, pre-registered test of the question the owner is actually asking: *is there anything in the filings at all?*
Families SEC13D, DILUTION_8K and FORM4 (the parents only, one record per set), their H20 FIRE resolutions, each
paired excess signed by the family's direction so that a correct avoid call counts as a gain. Per-session mean, the
same looks and t floor as prereg_2, futility from the 240 look. About 2,400 events a year.

| Class edge | Pairs needed (t 3.0, sd 0.156) | Months at 2,400 a year |
|---|---|---|
| 2.0% | 548 | 3 |
| 1.5% | 975 | 5 |
| 1.0% | 2,190 | 11 |
| 0.5% | 8,761 | 44 |

A pass says the lab's readings of EDGAR carry information the twins do not. It does not say which family to trade,
and the families' own looks continue unchanged. A futility stop says the class has not beaten random, which is a
reason to stop all three.

## Levers not pulled, and why

- **A price floor as a rule (signal close >= USD 20)**: the strongest variance lever, but a rule change needs a new
  family version; the class reports the split so the owner can decide with prospective numbers.
- **Relaxing t >= 3**: the owner's standing rule.
- **A discounted historical prior (test 26's 2,964 events as a power prior)**: would cut the prospective sample by
  a quarter to a third, but puts survivor-only data back into inference, which the prospective registers exist to
  avoid. Not done without the owner's decision.
- **Intraday entry for filings accepted during the session**: a product change needing an intraday seal.
