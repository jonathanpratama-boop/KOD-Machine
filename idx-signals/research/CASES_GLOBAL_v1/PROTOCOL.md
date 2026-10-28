# CASES_GLOBAL_v1: was anything public three sessions before moonshots outside Indonesia?

Written 2026-10-27 before any case is drawn. Descriptive, not a counted test. Same question, classes and news rules as
CASES_IDX_v1 (its PROTOCOL.md), applied to the other markets of record, with two additions the owner asked for: SEC
filings (US cases) and social or scheduled-event signals.

## Selection (frozen, `select.py`, seed 20261027)

20 fast-rise episodes (+30% within five sessions, first in 20): 10 from US stocks (LEAD_LADDER_v1, 2020-07..2022-12),
5 from crypto (LEAD_LADDER_v1, 2020-07..2022-12), 5 pooled from the nine eToro exchanges (LEAD_LADDER_INTL_v1,
2020-07..2022-12). Drawn uniformly within each group.

## Per case

- J, J-3 and the move as in CASES_IDX_v1, from the same panels.
- US: every SEC filing of the issuer dated 30 days before J through J, from E9's archived EDGAR submissions
  (`data/raw/sec/20261016T185931Z`), where the issuer is covered.
- News: dated public items 30 days before J to J (business press, exchange or project announcements, company or
  project sites), each with URL and date. Also: was the event's date scheduled and public in advance (earnings date,
  regulatory decision, token unlock, exchange listing)? Any dated social-media item found by search counts as news.

## Classes

CASES_IDX_v1's six classes in its order, with one change: the sector rule is dropped as a class, because CASES_IDX_v1
showed it fires on most ordinary days; sector co-movement is recorded as a note. "Visible three sessions out" =
TELEGRAPHED (including a publicly scheduled event date) or a US SEC filing by J-3 that explains the move.
