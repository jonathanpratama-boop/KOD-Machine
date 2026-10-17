# E10 accuracy audit: procedure

Committed before the audit sample is drawn or any reviewer sees an item. Fills in the "Accuracy audit"
section of `FEASIBILITY_SPEC.md`; where this file is stricter, it governs.

## Sample
`feasibility/audit_sample.csv` as `feasibility.py` writes it: 40 RAISE and 20 CUT events drawn with seed
20261017 (pandas `sample(random_state=20261017)` per class).

## What a reviewer sees
`audit_blind.py` writes one file per audit: item number, fiscal year, kind (dollar or growth), the direction
the rule assigned, the earlier and the later guidance sentence, and the two midpoints the rule extracted
(USD millions, or growth as a fraction). No ticker, company name the sentences do not contain, accession,
date, price or return.

## Reviewers
Two independent reviewers (separate AI agent sessions sharing no context, told not to search the web or
identify the company), each answering for every item:

- **Q1 same measure**: do both sentences give the company's own full-year total revenue or net sales
  guidance for the stated fiscal year (not a segment, a quarter alone, an acquired business, or another
  measure such as EPS or EBITDA)?
- **Q2 direction**: is the assigned direction (RAISE or CUT) what the two sentences say?
- **Q3 numbers** (reported, not a GO condition): are the two extracted midpoints what the sentences state?

An item is correct if Q1 and Q2 are both yes.

## Scoring and GO
`audit_score.py` writes `audit/AUDIT.json` from the two reviewers' saved answers: precision per class for each
reviewer, the items they disagree on, and the Q3 rate. The GO precision is the **lower** of the two
reviewers' precision for each class (RAISE >= 85%, CUT >= 80%). No item is re-judged or dropped after the
answers are saved.
