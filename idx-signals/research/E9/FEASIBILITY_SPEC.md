# E9 catalyst split: hypothesis and declared feasibility rule (committed before any E9 data is read)

## Hypothesis
Among US common stocks that close up 30% or more in a day (the frozen E2 US detector G2_RET30), moves
with an SEC information filing public **before the next session's open** go on to beat moves without one
over E2's original plan (buy the next open, sell at the close five sessions later). Moves with a dilution
filing do worst. Mechanism: a move backed by disclosed information is repriced gradually (drift), while an
unexplained move is order-flow pressure that reverses (Chan 2003, J. Financial Economics; Savor 2012, J.
Financial Economics). No earlier KOD test used filings; E2's US plan lost against matched coins as a whole.

Owner's constraint: the broker is eToro, which offers about 6,150 Nasdaq/NYSE stocks and no Indonesian
stocks (its public instrument list, fetched 2026-10-16). The result is reported for the names eToro lists
today as well as for all names.

## Data and period
- Prices: repaired US panel `panel_us_repair-20261008T114805Z` (Yahoo daily bars, split-adjusted, with
  `unit_factor` for as-traded levels; survivor-only: the Nasdaq Trader snapshot of 2026-10-08).
- Discovery only: signal sessions 2020-07-01..2022-12-31. 2023 was examined in E2 validation and is not
  used; 2024+ is not in the panel (sealed holdout).
- Filings: SEC EDGAR submissions JSON (data.sec.gov) per issuer, including the older chunk files, cached
  and hashed. The User-Agent declares the owner's contact; the address is not written to the repository.
- Ticker to CIK: SEC `company_tickers.json` fetched now (the universe is today's listings, so today's
  ticker map applies), with "." read as "-".
- eToro: the public static instrument list (`api.etorostatic.com`), stocks on exchanges 4 (Nasdaq) and 5 (NYSE).

## Entries (shared by every class; no return is read in this check)
Repository harness `idxsig.backtest` at this branch's HEAD, E2's recorded US configuration with only the
window and two settings stated here changed: rule `MOONSHOT_E2_US_D1` (G2_RET30), window 2020-07-01..
2022-12-31, entry at the next session's open, 5 sessions, `units="as_traded"`, `fill_model="B"`
(at most 10% of the median volume known at the decision), **`quarantine="none"`** (every name kept:
research/E2/repair_v3/SELECTION_NOTE.md shows the unit quarantine removes the worst outcomes), 5,000 USD
notional, overlap skip under the original exit, controls v2 with 200 draws (seed 20261007 + 1).

## Information known at entry (fixed now)
For a signal at the close of session s with entry at the open of session e = s + 1: a filing counts if its
EDGAR acceptance time is after 16:00 New York time on session s - 1 and at or before 09:15 New York time
on session e (15 minutes before the open). Sessions are the panel's US trading calendar.

Classes, first match wins:
1. **DILUTION**: a filing of form 424B1, 424B2, 424B3, 424B4, 424B5, 424B7, 424B8, S-1, S-1/A, S-1MEF,
   S-3, S-3/A, S-3ASR, S-3MEF, F-1, F-1/A, F-1MEF, F-3, F-3/A, F-3ASR, F-3MEF or EFFECT, or an 8-K/8-K/A
   listing item 3.02 (unregistered sale of equity).
2. **DOCUMENTED**: a filing of form 8-K, 8-K/A, 6-K, 6-K/A, 10-Q, 10-Q/A, 10-K, 10-K/A, 20-F, 20-F/A,
   40-F, SC 13D, SC 13D/A, SC TO-T, SC TO-T/A, SC TO-C, SC 14D9, DEFM14A, PREM14A or 425.
3. **UNDOCUMENTED**: neither (other filings, such as Form 4, S-8 or SC 13G, may exist).
4. **NO_CIK**: the ticker has no CIK in the SEC map (excluded and counted).

## Acceptance-time check
EDGAR's submissions JSON gives `acceptanceDateTime` with a "Z" suffix. For 20 filings drawn with seed
20261017 from the fetched event windows, compare it with the archive's own SGML header
(`<ACCEPTANCE-DATETIME>`, New York time). The interpretation (UTC, or New York time mislabelled) that
matches all 20 is used. If neither matches at least 19 of 20, NO-GO.

## What the check reports (counts only)
Mapping rate; SEC retrieval status per CIK; whether fetched filings reach back before each event window;
events by class, by year, by ISO week; entered (scored-able) events by class; 8-K item families in the
DOCUMENTED class; the share of events in names eToro lists today; a minimum detectable difference from
trailing 20-session volatility (no forward bar).

## GO / NO-GO (fixed now)
GO if all hold: at least 90% of attempted signals map to a CIK; at least 98% of mapped CIKs return HTTP
200 with every chunk file fetched; the acceptance-time check passes; at least 150 entered DOCUMENTED and
150 entered UNDOCUMENTED events, each spread over at least 50 ISO weeks. Otherwise NO-GO with the failing
condition named, and E9 stops at feasibility.
