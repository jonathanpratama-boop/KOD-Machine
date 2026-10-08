# ZEALAND_PILOT_v1: protocol (frozen 2026-10-08, before any evidence was read)

Discovery-only case study in the KOD lab. One event, chosen because it was the largest move,
so it can suggest a hypothesis and cannot validate anything. It is not counted as validation,
does not enter KOD calibration (the card is RETROSPECTIVE), does not enter the paper ledger,
and authorizes no order. `kod/detectors.py` (KOD-DET-v0, sha256 `0a0e0a73…`) and the doctrine
are used as they are; nothing in them is changed for this case. `protocol.json` is the
machine-readable copy and governs where the two differ.

## Pinned

| Item | Value | Basis |
|---|---|---|
| Event | Zealand Pharma–Roche collaboration and license agreement for petrelintide, Nasdaq disclosure 1348334, "Inside information" | exchange announcement feed, `pin/nasdaq_news_zealand_start*.json` |
| Release | 2025-03-12 07:00:00 CET = 06:00:00Z, two hours before the Copenhagen session | the exchange system's `releaseTime` |
| Listing | Nasdaq Copenhagen Main Market, ZEAL, DKK (Yahoo ZEAL.CO) | feed `market`; Yahoo meta |
| Event session | 2025-03-12 (close-to-close +37.89%, the largest in 2015–2026) | `pin/ZEAL.CO.json`, sha256 `a20b3934…` |
| Decision cutoff | 2025-03-11T16:00:00Z (17:00 CET, end of the last session before the release) | fixed |
| Information sets | T-30D 2025-02-09T16:00Z, T-72H 2025-03-08T16:00Z, T-24H 2025-03-10T16:00Z | exact offsets |

The issuer's previous announcement was the AGM notice of 2025-02-20 13:00 CET; nothing else
from the issuer appears in the feed until the release.

## Steps

1. **Evidence** (`02_evidence/`): the issuer's exchange announcements published by each cutoff
   (PRIMARY, existence by the exchange's own timestamp; contents verified only by an archive
   capture dated by the cutoff), archive captures, Novo Nordisk's amylin-class announcements
   in the 30 days before the cutoff as dated context, press only via dated archive captures,
   and Copenhagen market conventions from the exchange's and tax authority's own documents.
   Each becomes a `KOD-EVIDENCE-v2` object (`python3 -m kod evidence`).
2. **Card** (`03_card/`): `KOD-R-ZEAL-20250312`, RETROSPECTIVE, KOD-CARD-v3, integrity
   PARTIAL, facts per the definitions in `protocol.json` (price facts reuse the E1-SIGNALS-v1
   measures), opened with `python3 -m kod open` and evaluated by the frozen detectors.
3. **Entries** (`04_entry/`): six entries defined in advance (closes after T-30D, at T-24H and
   at the cutoff; the event-day opening auction and close; the next open), exits at +0/+1/+5/
   +20/+60 sessions, path risk, OMXC25 benchmark, liquidity, base and stress costs. Costs are
   labelled assumptions. US conventions (pre-market, 09:30 open, LULD, OTC lines) are not used.
4. **Findings** (`05_findings/`): exactly one of FROZEN_HYPOTHESIS or
   NO_ACTIONABLE_EDGE_ESTABLISHED, by these criteria fixed now:
   - C1 ex ante: visible in an information set built from grade A–C evidence published by its cutoff;
   - C2 general: no Zealand-specific constants; a population with other members exists;
   - C3 feasible: a home-listing entry at a published price, entry-session value at least 20x a
     DKK 1m reference position, positive net return at +5 sessions under base costs and above
     the benchmark;
   - C4 falsifiable: population, trigger, entry, exit, horizon, costs, benchmark, minimum sample
     and success threshold written down; test data exclude Zealand 2025-03.

## Seen before this was frozen

The three largest session returns; the bars of 2025-02-25 (close 719), 2025-03-11 (open
507.5, close 488.80), 2025-03-12 (open 700, high 725, low 598, close 674), and the closes of
2025-03-13/14/18; the issuer's announcement headlines and times; the deal's headline terms
from Roche's release. No pre-cutoff document text, no entry return, no volume or range
statistic, no benchmark.

Files in this research directory are append-only (`tools/check_append_only.py`): a
correction is a new file, never an edit.
