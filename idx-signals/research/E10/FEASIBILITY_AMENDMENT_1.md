# E10 feasibility, amendment 1: guidance extraction v2

Dated 2026-10-17, before any price or return for E10 is read.

## Why
The frozen v1 rule failed its blind audit (`audit_partial/v1_audit/AUDIT.json`): precision 67.5% for RAISE and
50% for CUT (bars: 85% and 80%), so v1 is NO-GO. Its misses were measure mismatches: segment and product-line
figures, EBITDA, cash flow, backlog, acquired businesses, quarterly figures.

## What changes
`idxsig/guidance_v2.py` (v1 unchanged) and `feasibility_a1.py`:
1. the amount is anchored to a revenue term (first amount within 80 characters after it with no other measure word
   in between, or a dollar amount directly before "in/of revenue");
2. the revenue term must be unqualified (no segment or measure name in front, past time words);
3. sentences about acquired businesses, trailing, year-to-date or pro forma periods, run rates and contributions
   are skipped;
4. level changes beyond +-50% are dropped as mismatches and counted;
5. a fresh audit draw (seed 20261018).
v2 was drafted during the download from a counts-only dry run of v1 on the first ~5,000 filings (text only) and
committed (4425bd9) before either official audit.

## Audit result
`audit_partial/a1_audit/AUDIT.json` (sample from the 12,852 filings saved by ~08:30 UTC, per
AUDIT_PROCEDURE_AMENDMENT_1.md): RAISE 37/40 = 92.5%, CUT 16/20 = 80.0%, both reviewers identical. GO on accuracy.
The count conditions are judged on the full download by `feasibility_a1.py` before the freeze.
