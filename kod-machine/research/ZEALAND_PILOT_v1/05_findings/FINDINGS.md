# ZEALAND_PILOT_v1: findings

**Conclusion: NO_ACTIONABLE_EDGE_ESTABLISHED.** By the criteria frozen in `01_protocol`
before any evidence was read, no candidate condition was visible ex ante, general, feasible on
the home listing and profitable after costs all at once. No hypothesis is frozen.

This is a discovery-only case: one event, chosen because it was the largest move in the
series. It is not validation and is not counted anywhere: the KOD card is RETROSPECTIVE, there
is no paper record, and no order was placed. `kod/detectors.py` (KOD-DET-v0), the doctrine,
ASTRA and the paper policy are unchanged.

## 1. Pinned (`01_protocol`, RFC 3161-stamped before reading)

| | |
|---|---|
| Event | Zealand Pharma–Roche collaboration and license agreement for petrelintide (USD 1.65bn upfront, up to USD 5.3bn), Nasdaq Copenhagen disclosure 1348334 |
| Release | 2025-03-12 07:00:00 CET (06:00Z), by the exchange system, two hours before the session |
| Listing | Nasdaq Copenhagen Main Market, ZEAL, ISIN DK0060257814, DKK. US ADSs were delisted in 2022 |
| Decision cutoff | 2025-03-11T16:00Z (17:00 CET close); T-30D 2025-02-09, T-72H 2025-03-08, T-24H 2025-03-10 |

## 2. What was knowable before the cutoff (`02_evidence`, 19 evidence objects)

- **Intent, not timing.** Primary documents said Zealand would seek co-development and
  commercialization partnerships for its obesity candidates (June and August 2024). Press said
  the CEO was looking for a large pharma partner (August 2024). On 20 February 2025 he said
  the process was "exactly where it wants to be". No document gave a date, window,
  counterparty or terms.
- **The issuer's own February report leaned the other way.** The FY2024 report stressed
  investment in "wholly-owned obesity programs" and gave "No guidance" for partnership
  revenue. The annual report's 31 mentions of petrelintide include no partnering statement.
- **Silence before the release.** No issuer announcement between 2025-02-20 13:00 CET and the
  release. The last insider trades were a DKK 1.27m sale (2024-11-08) and a DKK 216k purchase
  (2024-12-20). The January filing was an inheritance.
- **A falling price.** From the 2025-02-18 close of 783.5 to the cutoff close of 488.80, the
  stock fell 37.6%, on about twice its normal volume. From E1 (2025-02-10) to the cutoff it
  fell 31.7%, while OMX Copenhagen 25 fell 2.3%. Novo Nordisk's CagriSema REDEFINE 2 readout
  (amylin class) came the session before the cutoff. The documents do not explain the fall,
  and this study does not attribute it.

## 3. The frozen detectors (`03_card`)

`KOD-R-ZEAL-20250312` (card_sha `ca0b25a5…`, RETROSPECTIVE, PARTIAL) was evaluated by
KOD-DET-v0 as it stands. DATED_CATALYST_KNOWN, PRIMARY_DOC_BEFORE_PRICE,
VOLUME_CREEP_PRICE_QUIET and NARRATIVE_WITHOUT_MECHANISM all returned NO_SIGNAL. Only
COVERAGE_INCOMPLETE fired. Volume did rise into the event, but alongside a 29% fall rather
than a quiet price. The detectors were not changed to fit this case.

## 4. Entry opportunities under Copenhagen conventions (`04_entry`)

Prices are official home-listing opens and closes. The Yahoo series and Nasdaq Nordic's own
history agree to the øre on all 171 sessions compared (volume within 0.94%). Costs of 0.20%
per side (0.60% stress) are labelled assumptions. No sign below changes under stress.

- **The release came before the first possible trade.** It was published at 07:00 CET.
  Copenhagen's opening auction runs 08:45–09:00 and uncrosses at 09:00 (2026 factsheet,
  assumed for 2025). The opening price was 700.00, 43.2% above the prior close. That is 114%
  of the day's close-to-close move (+37.9%), because the session then closed below its open,
  at 674.00. No pre-market or after-hours trading was assumed, and the stale OTC line was not
  used.
- **Post-release entries lost money.** Net returns (base costs) were:

  | Entry | +5 sessions | +20 sessions |
  |---|---|---|
  | Event-day opening auction (700.00) | −19.3% (excess vs OMXC25 −21.5%) | −41.9% |
  | Event-day close (674.00) | −16.1% | −39.6% |
  | Next open (675.00) | −16.3% | −39.7% |

  By +20 sessions the stock was below its pre-release close. Part of that window was a broad
  April 2025 fall (OMXC25 −18%), but excess returns were still −22% to −24%.
- **Pre-release entries depended on timing nobody had.**

  | Entry | +5 sessions (net) | Worst low on the way |
  |---|---|---|
  | E1, close after T-30D (716.00) | −21.1% | −32.1% |
  | E2, T-24H close (507.50) | +11.4% | −4.2% |
  | E3, cutoff close (488.80) | +15.6% | none below entry (lowest +9.7%) |

  All three are negative at +20 sessions (−43.2%, −19.8%, −16.8%) and at +60 (−37.2%,
  −11.4%, −8.0%). E2 and E3 make money only if the buyer knew to buy in the two days before
  an undated event.
- **Liquidity did not bind.** A DKK 1m position was at most 2.1% of the entry session's
  official turnover (DKK 47.5m on 2025-02-10, 208m on 2025-03-11, 1.73bn on 2025-03-12).

## 5. Pre-registered criteria applied

| Candidate | C1 ex ante | C2 general | C3 feasible and profitable at +5 | C4 falsifiable | Result |
|---|---|---|---|---|---|
| H-A: undated partnering intent in primary documents | pass (grade B/C, before T-30D) | pass | **fail**: the entry it triggers (E1) loses 21.1% net, and earlier dates do worse (Aug 2024 close 938.5) | pass | rejected |
| H-B: H-A plus a high-volume drawdown at T-24H | **fail**: price facts rest on series retrieved in 2026 (KOD grade D); any drawdown threshold would be chosen after seeing this path | n/a | would pass (E2 +11.4%, E3 +15.6%) | n/a | rejected |
| H-C: post-release drift after a partnership announcement | pass | pass | **fail**: −16% to −19% net at +5, below the benchmark | pass | rejected |

H-B is the only variant that made money, and only at short horizons. It needs evidence the
protocol does not admit and a threshold fitted to this path. It is recorded as an untested
observation, not frozen as a hypothesis. Testing it would need a new protocol that defines
the population without Zealand, fixes the drawdown and volume thresholds in advance, and
decides how exchange price history is graded. That is a separate decision.

## 6. Limits

- One event, selected on its outcome. Nothing here estimates a rate.
- Document contents were not verified against a capture dated by the cutoff, because the
  Internet Archive was unreachable. Existence rests on the exchange system's timestamps.
  Summer-time releases were converted at UTC+1, the later of the two possible instants.
- The press items were read through a fetch tool and their bytes are not held. A Reuters
  interview mentioned in search results could not be retrieved and is not used.
- Copenhagen's 2025 auction times and the absence of a transfer duty in 2025 rest on a 2026
  factsheet and a 1998 repeal, and are stated as assumptions. Commissions are assumptions.
- No intraday, order-book, options or short-interest data were available. Whether anyone
  could trade between 07:00 and 09:00 on another venue was not evidenced and not assumed.

## 7. Reproduce

```sh
cd kod-machine/research/ZEALAND_PILOT_v1
python3 03_card/price_facts.py      # facts per information set from the pinned series
python3 04_entry/entries.py         # entries, cross-check, criteria, conclusion -> 04_entry/results.json
cd ../.. && python3 -m kod --db var/kod.db verify
```
