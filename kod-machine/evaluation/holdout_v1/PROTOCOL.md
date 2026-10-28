# holdout_v1 — held-out evaluation of the earnings-release reader

## Purpose

A held-out measurement of KOD's earnings-release reader. The set was built and
sealed (SEAL.json) before any change to the reader. The engineer changing the reader
must not open these fixtures or expectations until the single final measurement.
KOD's reader was not run on these documents while the set was built, and no KOD output
was looked at. Every expected value was read by hand from the filed documents.

## Pool

- `company_tickers.json` (SEC ticker list, 10,435 entries), SHA-256
  `bb1521ff938ce1217343362f335aae521d9978b105229eabef69124ac24bbb1c`.

## Selection rule (deterministic)

1. Partition: a ticker is in the HELD-OUT partition iff the first byte of
   `sha256(("KOD-PARTITION-v1:" + TICKER).encode())` is even. Only this partition is used
   (5,327 tickers).
2. Order: ascending `sha256(("KOD-HOLDOUT-v1:" + TICKER).encode()).hexdigest()`. Walk in
   this order and de-duplicate CIKs, keeping the first ticker seen for each CIK
   (4,505 CIKs).
3. Exclude:
   - the tickers NVDA, AMD, AAPL, MSFT, TXN, COST, JPM and PLUG;
   - SIC codes 6000–6799 (banks, insurers, REITs, blank checks, financial);
   - filers whose most recent periodic reports are not 10-Q/10-K. This was tested on
     the two most recent periodic forms in the EDGAR submissions feed. Filers with no
     periodic report at all were also excluded (e.g. Form D-only issuers, ADR shells).
4. Accept a company if its two most recent quarterly-results announcements meet all of
   these conditions:
   - each is a form 8-K whose items include 2.02;
   - each was filed between 2025-07-01 and 2026-10-22;
   - each attaches an HTML press-release exhibit (EX-99.1 or similar EX-99);
   - the two cover consecutive fiscal quarters.

   "cur" is the latest announcement and "pri" is the one before it. A filer with fewer
   than two such 8-Ks in the window cannot meet this condition and was skipped. No 8-K/A
   with Item 2.02 existed in the window for any accepted company.
5. Take the first 6 accepted companies.

Data: `https://data.sec.gov/submissions/CIK##########.json` was used for SIC, forms and
8-K items. Each filing's `-index-headers.html` was used for exhibit types and filenames.
Requests stayed under 5 per second with a declared User-Agent.

## Tickers examined, in order

| # | Ticker | CIK | SIC | Result |
|---|--------|-----|-----|--------|
| 1 | AWLRF | 1727254 | — | skip: no 10-Q/10-K periodic reports on file (Form D only) |
| 2 | DRMA | 1853816 | 2834 | **ACCEPT** |
| 3 | RC-PE | 1527590 | 6798 | skip: SIC 6798 (6000–6799) |
| 4 | AHT-PG | 1232582 | 6798 | skip: SIC 6798 (6000–6799) |
| 5 | IPHYF | 1598599 | 2836 | skip: most recent periodic reports are 20-F |
| 6 | CHXIY | 2152784 | — | skip: no 10-Q/10-K periodic reports on file (F-6EF only) |
| 7 | CHGG | 1364954 | 8200 | **ACCEPT** |
| 8 | IHT | 82473 | 6798 | skip: SIC 6798 (6000–6799) |
| 9 | ERIE | 922621 | 6411 | skip: SIC 6411 (6000–6799) |
| 10 | NEWTP | 1587987 | 6021 | skip: SIC 6021 (6000–6799) |
| 11 | MRCL | 2029014 | 7380 | skip: no 8-K with Item 2.02 filed 2025-07-01..2026-10-22 (needs two) |
| 12 | PHCAF | 2145424 | — | skip: no 10-Q/10-K periodic reports on file (Form D only) |
| 13 | DFP | 1559991 | — | skip: most recent periodic reports are N-CSRS/N-CSR (registered fund) |
| 14 | NATL | 1974138 | 3578 | **ACCEPT** |
| 15 | LB | 1995807 | 6792 | skip: SIC 6792 (6000–6799) |
| 16 | TECK | 886986 | 1400 | skip: most recent periodic reports are 40-F |
| 17 | SPIR | 1816017 | 4899 | **ACCEPT** |
| 18 | BNBX | 744452 | 6199 | skip: SIC 6199 (6000–6799) |
| 19 | PWDY | 1435617 | 7374 | skip: no 8-K with Item 2.02 filed 2025-07-01..2026-10-22 (needs two) |
| 20 | TII | 1791703 | 1040 | skip: most recent periodic reports are 40-F/A, 40-F |
| 21 | GRPFF | 912892 | 4833 | skip: most recent periodic reports are 20-F |
| 22 | FCHDF | 2048847 | — | skip: no 10-Q/10-K periodic reports on file (Form D only) |
| 23 | TDC | 816761 | 7372 | **ACCEPT** |
| 24 | BTT | 1528437 | — | skip: most recent periodic reports are N-CSR/N-CSRS (registered fund) |
| 25 | TRST | 357301 | 6022 | skip: SIC 6022 (6000–6799) |
| 26 | SOLC | 2041869 | 6221 | skip: SIC 6221 (6000–6799) |
| 27 | CBUS | 1705843 | 2870 | **ACCEPT** (6th; walk stopped) |

No company was skipped for any other reason.

## The 6 chosen

All six have fiscal years equal to calendar years. In each case cur is the fiscal
quarter ended 2026-06-30 (Q2 2026) and pri is the quarter ended 2026-03-31 (Q1 2026).

| Ticker | Registrant | cur accession | pri accession | Outlook for cur quarter in pri |
|--------|------------|---------------|---------------|-------------------------------|
| DRMA | Dermata Therapeutics, Inc. | 0001493152-26-037124 | 0001493152-26-022710 | guidance_absent |
| CHGG | CHEGG, INC | 0001364954-26-000085 | 0001364954-26-000045 | guidance |
| NATL | NCR Atleos Corp | 0001974138-26-000014 | 0001974138-26-000004 | guidance_absent |
| SPIR | Spire Global, Inc. | 0001193125-26-346835 | 0001193125-26-221629 | guidance_absent (annual-only) |
| TDC | TERADATA CORP /DE/ | 0001628280-26-052549 | 0001628280-26-030514 | guidance |
| CBUS | Cibus, Inc. | 0001628280-26-056731 | 0001628280-26-035105 | guidance_absent |

Fixtures: `fixtures/<ticker>/` contains:
- `cur.htm` and `pri.htm`: the exhibit bytes exactly as served;
- `cur_headers.html` and `pri_headers.html`: the filings' `-index-headers.html` pages;
- `SOURCES.json`: URL, byte count, SHA-256, retrieval time (UTC) and HTTP status for each
  file.

## How the expectations were derived

- Each value was read by hand from the release HTML. The text of each release and of its
  statement-of-operations table was read directly. KOD software was not used.
- Facts are three-month figures for cur's quarter, not year-to-date figures:
  - revenue is the total revenue or net revenues line;
  - net_income is net income attributable to the company when the release shows both
    total and attributable figures;
  - eps_diluted is printed diluted EPS (or "basic and diluted").
- Amounts are converted to full units from the stated "in thousands"/"in millions" scale.
- `prior` is same-quarter-prior-year revenue as printed in cur. `growth_pct` =
  (cur/prior − 1) × 100, computed with Python `decimal` and rounded half-up to 2 places.
- `guidance` is included only when pri gives a numeric outlook specifically for cur's
  quarter. There is at most one entry per metric (revenue, eps_diluted), on the basis the
  release states. The position compares the cur actual on that basis against the closed
  range [low, high].
- `guidance_absent` is set when pri gives no numeric quarterly outlook. An annual-only
  outlook counts as absent.
- `caveat_visible` is included only when cur explicitly says that results include items
  not in the original outlook. No such statement was found in any of the six.
- `as_of` = the cur filing's acceptance time plus 1 day, in UTC. The acceptance time is
  the header's ACCEPTANCE-DATETIME, which EDGAR states in US Eastern time.
- Notes on judgement calls are recorded in each task's `sources` field. Examples:
  - DRMA reports no revenue, so its revenue fact and `prior` comparison are omitted.
  - TDC's revenue outlook is a percentage growth range rather than an amount, so it is not
    encoded. The GAAP EPS outlook is encoded, and the non-GAAP EPS outlook is noted.
- Second pass: every expected figure was searched for again in the raw HTML after the tags
  were stripped. All figures were found, and every SOURCES.json byte count and SHA-256 was
  recomputed and matched.

## Change rule

Expectations change only to fix an error in the expectation itself, meaning a value that
does not match what the document says. Every such change must be logged here with the
date, the task, the old and new value, and the quote that shows the error, and the set
must then be re-sealed. Expectations are never changed because KOD answers differently.
