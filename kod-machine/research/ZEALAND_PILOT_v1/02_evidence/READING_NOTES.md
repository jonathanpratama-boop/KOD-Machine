# ZEALAND_PILOT_v1: what was public before the cutoff

Every document below is a `KOD-EVIDENCE-v2` object (ids in `evidence_index.json`, frozen
objects in `kod-machine/registry/evidence-v2/`). Bytes are in `raw/` and hashed in
`fetch_log.json`. Exchange announcements are dated by the exchange system's own release
time (existence verified, grade B). No contents could be checked against an archive capture
dated by the cutoff: the Internet Archive was rate-limited from this environment. Press
articles could only be read through a fetch tool, so their bytes are not held (grade C).

## The issuer's exchange record, mid-2024 to the cutoff

The pinned Nasdaq feed holds every Zealand Pharma A/S announcement. Between the AGM notice
(2025-02-20 13:00 CET) and the event (2025-03-12 07:00 CET) there was none.

| Released (CET) | Document | What it says that bears on the event |
|---|---|---|
| 2024-06-25 17:02 | Equity offering, USD 900m (P01) | "The Company is prioritizing resources on R&D and expects to engage in strategic partnerships for commercialization and co-development." No asset, no timing. |
| 2024-08-15 07:00 | H1 2024 report (P02) | CEO: "investing significantly in our differentiated obesity candidates to accelerate the development programs as we explore partnership opportunities." No asset-specific timing. |
| 2024-11-07 07:00 | 9M 2024 report (P03) | Partnership discussions named for glepaglutide and dasiglucagon (rare diseases) only. Petrelintide: Phase 2b trials and their timing; no partnering statement. |
| 2024-11-11 17:00 | PDMR (P04) | Board member (employee elected) sold 1,500 shares at DKK 847–850 on 2024-11-08. |
| 2024-12-19 20:58 | FDA CRL for glepaglutide (P05) | Rare-disease setback. |
| 2024-12-25 17:40 | PDMR (P06) | Board member bought 300 shares at DKK 720 on 2024-12-20 (scanned form, read visually). |
| 2025-01-13 17:00 | PDMR (P07) | Inheritance of 1,090 shares; not a trade. Last PDMR notice before the event. |
| 2025-02-20 07:00 | FY2024 results (P08) | "significantly accelerate its investments in the company's wholly-owned obesity programs, which in 2025 will include three large Phase 2b trials"; 2025 revenue from new license and partnership agreements: "No guidance". |
| 2025-02-20 07:00 | 2024 Annual Report (P09) | "Zealand's strategy is to pursue global co-development and commercialization partnerships…"; 31 petrelintide mentions, none near a partnering statement or timing. |
| 2025-02-20 10:08 | Correction of FY2024 | Adds the iXBRL annual report only; text unchanged. |

Earlier: on 2022-08-08 (P10) the company announced the voluntary delisting of its US ADSs
and the consolidation of trading on Nasdaq Copenhagen (ZEAL, DKK). The insider forms give
the ISIN DK0060257814.

## Press, dated by the publisher's page (grade C)

- Investing.com, 2024-08-20 09:02 UTC (S01): the previous session's fall followed "comments by
  the company's CEO … about seeking a large pharmaceutical partner for the company's weight
  loss drug." No timing.
- Pharmaceutical Technology, 2025-02-20 (S02): the partner search for petrelintide "remains
  ongoing"; the CEO on the results call said the company is "exactly where it wants to be in
  the process"; a co-development and co-commercialisation deal with profit-sharing is preferred
  over a standard licence. No date or window.

Search results also pointed to a Reuters interview (relayed by Quartz) in which the CEO said
a big pharma partner was needed "at one point" for global reach and manufacturing. Neither
page could be retrieved (403) and no archive was reachable, so it is not recorded.

## Amylin-class context (Novo Nordisk, Nasdaq Copenhagen, grade B)

- 2024-12-20 11:41 CET: CagriSema REDEFINE 1 headline results (N01).
- 2025-01-24 11:19 CET: subcutaneous amycretin phase 1b/2a (N02).
- 2025-03-10 11:23 CET: CagriSema REDEFINE 2: 15.7% weight loss at 68 weeks if adherent,
  13.7% by treatment policy (N03). This is the session before the cutoff.

The documents themselves do not say how markets reacted; any reaction is read from prices in
`04_entry`, not from these sources.

## Market conventions (Copenhagen)

- Auctions (M01, grade D: a 2026 factsheet): Copenhagen shares open with an auction from
  08:45 to 09:00 CET (random uncross 09:00:00–09:00:05) and close with one from 16:55 to
  17:00 (uncross 16:59:30–17:00). Applying this to March 2025 is an assumption.
- Transfer duty (M02, grade B): Denmark's share transfer duty was repealed for transfers from
  1 October 1999 (Lov nr. 909, 16 December 1998). That none was reintroduced by 2025 is an
  assumption.
- Not evidenced and not assumed: settlement cycle, volatility-guard parameters, broker
  commissions (costs in the protocol are labelled assumptions).

## What the record shows, by information set

- **T-30D (2025-02-09):** a stated intent to partner the obesity candidates (primary), press
  that the CEO sought a large pharma partner (secondary). No date, window, counterparty or terms.
- **T-72H (2025-03-08):** add the FY2024 report, which stresses wholly owned programmes and
  gives no partnership revenue guidance, and press quoting the CEO that the process was where
  he wanted it. Still no date or window.
- **T-24H (2025-03-10):** add Novo's REDEFINE 2 readout. Nothing new from Zealand.
- **Decision cutoff (2025-03-11 17:00 CET):** nothing new. The agreement was released
  2025-03-12 07:00 CET, before the opening auction.
