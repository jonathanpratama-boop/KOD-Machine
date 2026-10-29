# PATH_HISTORY_v1, addendum 1: EDGAR windows by filing date

Written 2026-10-29, before any outcome was computed and before any EDGAR data for this study was collected.

`protocol.json` (block E_US) states the EDGAR windows as acceptance times. The submissions JSON's
`acceptanceDateTime` mixes two clock conventions (research/E9/FEASIBILITY_AMENDMENT_3.md), so it cannot place a filing
on the right side of a cutoff reliably. Every E_US window is therefore read on `filingDate`. EDGAR dates a filing
accepted after 17:30 New York with the next business day.

- **news:** an 8-K, 8-K/A, 6-K or 6-K/A with filingDate on the previous session's date or on d. That covers the day
  before the spike, its after-hours, and the spike day itself. Every such filing was accepted before the next
  session's open, the live register's sealing cutoff.
- **offering90, shelf3y, atm12m:** the form lists of `protocol.json`, with filingDate in the 90 days, 3 years or 365
  days up to d.

Nothing else changes.
