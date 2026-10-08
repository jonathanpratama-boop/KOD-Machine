# KOD-R-ZEAL-20250312

Opened with `python3 -m kod --db var/kod.db open KOD-R-ZEAL-20250312.card.json --no-push`.

| Item | Value |
|---|---|
| card_sha | `ca0b25a539a74a50f71e64e5a3f68dfc9a1a53f0508e5600e6caa2ee658b673e` |
| anchor commit | `42c5523` (`kod anchor case …`), RFC 3161 freetsa and Sectigo 2026-10-08T12:44:07Z |
| frozen card | `kod-machine/registry/cards/KOD-R-ZEAL-20250312.json` |
| call type / integrity | RETROSPECTIVE / PARTIAL (excluded from calibration by the ledger) |
| detector | KOD-DET-v0, `kod/detectors.py` sha256 `0a0e0a73…` (unchanged) |
| disposition | WATCH: mechanism stated, timing missing, live loss path |
| outcome | REPRICED_UP, +37.89% (2025-03-11 close 488.80 → 2025-03-12 close 674.00) |

## Facts (evidence ids in the card; price facts from `price_facts.py`)

| Fact | T-30D | T-72H | T-24H |
|---|---|---|---|
| dated_catalyst_known | false | false | false |
| primary_document_public | false | false | false |
| narrative_only | false | false | false |
| mechanism_in_primary_docs | true (generic: partner the obesity candidates) | true | true |
| price_already_repriced (ret20 ≥ +30%) | false (−0.9%) | false (−26.8%) | false (−29.1%) |
| volume_creep_before_story (5d/20d median volume ≥ 1.5) | false (0.94) | true (2.32) | true (2.07) |
| price_quiet_vs_own_range | true | false (ret5 −19.5%, rngr 1.69) | false (ret5 −16.8%, rngr 1.52) |

`mechanism_in_primary_docs` = true rests on generic statements (P01, P02, P09) that name
neither petrelintide nor terms; read strictly it would be false. Either way
NARRATIVE_WITHOUT_MECHANISM stays NO_SIGNAL, because `narrative_only` is false.

## Detector evaluations (frozen at open, T-24H set)

| Detector | Status | Why |
|---|---|---|
| DATED_CATALYST_KNOWN | NO_SIGNAL | no date or window was ever stated |
| PRIMARY_DOC_BEFORE_PRICE | NO_SIGNAL | the agreement was not public before the price moved |
| VOLUME_CREEP_PRICE_QUIET | NO_SIGNAL | volume rose, but with a 29% fall, not a quiet price |
| NARRATIVE_WITHOUT_MECHANISM | NO_SIGNAL | the intent was in primary documents |
| COVERAGE_INCOMPLETE | SIGNAL | reconstruction is PARTIAL_PUBLIC |

The frozen detectors did not flag this event. The study does not change that. A change
would be a new rule version tested on a new cohort, and this case could not be part of it.
