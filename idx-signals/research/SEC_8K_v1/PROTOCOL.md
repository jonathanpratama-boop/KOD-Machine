# SEC_8K_v1: which SEC filing types come before a directional move, against matched random stocks?

Written 2026-10-27, before any full-universe data was fetched.

- **Universe:** the 3,520 issuers of the US repair panel with a CIK (SLOW_10K/filings.csv.gz). Filings from EDGAR submissions JSON: 8-K by item, SC 13D(/A), SC 13G,
  S-1, S-3, S-8, 424B3/4/5 (one kind, OFFERING_424B), DEF 14A, NT 10-Q, NT 10-K. One event per name, kind and filing date; a repeat within 20 days is dropped.
- **Execution:** entry at the next open after the filing date; 200 matched control draws (price band, liquidity); costs as in US_INSIDER_BUY; holds 20 and 60.
- **Stage 1 (2021-01-04 .. 2022-12-30), discovery:** kinds with >= 100 scored events. Selected if |t| at hold 60 clears Bonferroni z over (kinds x 2) at 5%
  two-sided, |mean excess| >= 2%, and hold 20 has the same sign. Selection written to selection.json and committed before Stage 2.
- **Stage 2 (2023-01-03 .. 2023-09-29), holdout, run once:** a selected kind PASSES if its hold-60 mean excess keeps the sign with t >= 1.65 and |mean| >= 1%.
- **Reading:** a negative PASS is an avoid or short flag (paper only); a positive PASS is a buy lead for a forward paper watch. Survivor-only prices push
  every excess up, so negative findings are conservative and positive ones flattered.
- **Rehearsal:** rehearse_cache.py ran the pipeline on E9's cached 1,235 issuers, selected for having rallied; those numbers are plumbing only.
