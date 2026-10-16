# E9 feasibility amendment 3 (2026-10-16): authoritative acceptance times. The first check's NO-GO stands.

## What happened
The check under amendments 1-2 (`feasibility_a2.py`) ran once, and its record is committed in
`feasibility/`. Its decision is **NO-GO** on one condition. EDGAR's submissions JSON `acceptanceDateTime`
was compared with each sampled filing's archive header (`<ACCEPTANCE-DATETIME>`, New York time):
- 10 of the 20 sampled filings carry true UTC;
- the other 10 carry New York time converted to UTC twice (+8 h in summer, +10 h in winter);
- no convention reaches 19 of 20.

The classes it wrote (convention "utc") are therefore not valid and are not used. Every other GO condition
held. No return of any E9 trade or control has been computed.

The defect belongs to the JSON field, not to the filings. Each filing's own header carries the
authoritative time, and it was readable for all 20 filings.

## Change (fixed now, before any return; nothing else changes)
1. **Acceptance time = the filing's SGML header `<ACCEPTANCE-DATETIME>`**, New York time, from
   `https://www.sec.gov/Archives/edgar/data/<cik>/<accession>/<accession>-index-headers.html`. It is
   fetched for every filing that meets both of these:
   - its form can change a class (the DILUTION and DOCUMENTED lists of FEASIBILITY_SPEC.md; 8-K item
     3.02 included);
   - its EDGAR filing date lies from the session before the signal through the entry session, inclusive,
     for an attempted signal of its issuer.

   EDGAR dates a filing accepted after 17:30 (22:00 for some forms) to the next business day, and accepts
   nothing before 06:00. So any filing accepted after 16:00 on the prior session and by 09:15 on the entry
   session carries a filing date in that range: the set holds every filing that can count. Other forms
   (Form 4, S-8, SC 13G) never change a class and get no time; `n_filings_in_window` now counts
   class-relevant filings only.
2. The later-documentation diagnostic (hindsight only) uses header times too. It covers information
   filings dated from the entry session through 5 calendar days after it.
3. **GO conditions**: the 20-filing convention check is replaced by header coverage: headers retrieved
   for at least 98% of the needed filings. A signal missing a needed header is classed NO_HEADER, then
   excluded and counted. Every other condition is unchanged: mapping 90%, SEC fetch 98%, at least 150
   entered DOCUMENTED and 150 entered UNDOCUMENTED, each over at least 50 ISO weeks.
4. The windows, the class rules and form lists, the entries and every later step are unchanged.
5. eToro's list is the one fetched by the first check (stamp 20261016T190421Z, sha256 in its manifest),
   re-read and hash-checked.
6. The check also reports, for each fetched header, which JSON convention it matches. This describes the
   JSON defect; it is never a decision input.

Runs once: `feasibility_a3.py`, writing `feasibility_a3/`.
