# E10 audit procedure, amendment 1 (owner request, 2026-10-17 ~08:30 UTC)

The owner asked not to wait for the full download before auditing. Extraction accuracy is a property of the
text, not of prices, so the audits run now on the filings saved so far (12852 of 36,215; the collector works in
ticker order, so tickers A..EYPT), for both the frozen rule (v1, feasibility.py, seed 20261017) and the prepared
amendment (v2, feasibility_a1.py, seed 20261018). Each script runs unchanged with its output directed to
`audit_partial/<rule>/`; its `audit_sample.csv` is the sample the reviewers see. Everything else in
AUDIT_PROCEDURE.md holds (two independent blind reviewers, lower precision per class decides).

The count GO conditions (RAISE >= 300, CUT >= 100, acceptance found >= 98%) are still judged on the full
download, and no price or return is read before protocol.json is frozen.
