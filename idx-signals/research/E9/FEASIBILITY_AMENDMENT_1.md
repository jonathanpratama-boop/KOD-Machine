# E9 feasibility amendment 1 (2026-10-16), before the feasibility check runs

A connectivity probe on seven AMD filings (CIK 2488), made before any E9 count or return, compared the
submissions JSON `acceptanceDateTime` with the archive's own SGML header `<ACCEPTANCE-DATETIME>`
(New York time):

| Filing | JSON (labelled UTC) | SGML header (New York) | JSON minus header |
|---|---|---|---|
| 8-K 0000002488-21-000054 | 2021-04-28T00:12:09Z | 2021-04-27 16:12:09 | +8 h (summer time) |
| 10-Q, 2021-07-28 | 2021-07-29T00:46:31Z | 2021-07-28 16:46:31 | +8 h |
| Form 4, 2022-03-24 | 2022-03-25T00:18:54Z | 2022-03-24 16:18:54 | +8 h |
| Form 4, 2020-11-24 | 2020-11-25T02:14:29Z | 2020-11-24 16:14:29 | +10 h (winter time) |
| 10-K, 2021-01-29 | 2021-01-30T03:24:00Z | 2021-01-29 17:24:00 | +10 h |
| Form 4, 2021-02-26 | 2021-02-27T02:18:33Z | 2021-02-26 16:18:33 | +10 h |
| Form 4, 2022-12-16 | 2022-12-17T02:15:08Z | 2022-12-16 16:15:08 | +10 h |

So the JSON value is neither UTC (+4 or +5 h) nor New York time (0 h): it is New York time converted to
UTC twice. Read strictly, the spec's two candidate conventions would both fail the 20-filing check and
stop E9 for a timestamp-format reason rather than a data gap.

## Change (fixed now; nothing else changes)
A third candidate, **"double"**: New York time = (JSON read as UTC, converted to New York, read again as
UTC) converted to New York. The 20-filing check (seed 20261017, filings in event windows) now compares all
three conventions; the one matching all 20 headers is used, and GO still requires at least 19 of 20. The
probe filings above are AMD's and are not part of the check's sample unless drawn.
