# E10 guidance revision (US): feasibility spec

Written and committed before any filing is downloaded. Counts only: no price, return or outcome is read in
this stage.

## Question this feasibility serves
Does a raised full-year revenue forecast in a company's earnings release leave a return, after an entry we
could actually get and after costs, that similar stocks did not earn? (Ace's guidance-revision candidate,
2026-10-17; the blueprint's diagnosis that every earlier signal was public price action.) The signal is the
revision itself: no price condition of any kind.

## Population and window
- Issuers: every ticker in the US repair panel (`panel_us_repair-20261008T114805Z`) that maps to a CIK in
  SEC's ticker file, with a median close of at least $2 and a median daily traded value of at least $250,000
  over 2020-07-01..2022-12-30 (a loose screen to skip shells; the event-level tradability rule comes in the
  protocol).
- Filings: 8-K and 8-K/A with Item 2.02 (results of operations), accepted 2019-10-01..2022-11-30. Releases
  before 2020-07-01 serve only as the prior guidance for later releases. Events are releases accepted
  2020-07-01..2022-11-30, so a 20-session hold ends inside 2022 (discovery period; 2023 is the used
  validation year; 2024 onward is sealed and never loaded).
- Source per filing: the full submission text (`<accession>.txt`), which carries the SEC header's
  `<ACCEPTANCE-DATETIME>` (New York time) and every exhibit. Only the EX-99 exhibit text is kept (gzipped);
  the sha256 of every raw response is recorded in a manifest.

## Extraction rule (deterministic; frozen in `idxsig/guidance.py` before any count)
1. Text: EX-99 exhibits, HTML stripped, split into sentences.
2. A guidance sentence names revenue or sales (`revenue(s)`, `net sales`, `total sales`, `sales`), carries a
   forward cue (`expect`, `outlook`, `guidance`, `anticipate`, `forecast`, `project`, `now sees`, `target`),
   names one explicit fiscal year (`2021`, `fiscal 2022`, `FY22`, `fiscal year 2021`), and is not about a
   quarter alone (a sentence naming a quarter and no full-year cue is skipped).
3. Amount: a dollar figure or range (`$4.0 billion to $4.2 billion`, `approximately $850 million`), or a
   growth rate or range (`growth of 12% to 14%`). Midpoint of a range.
4. Per release, fiscal year and kind (dollar or growth): the largest dollar midpoint (total revenue is the
   largest stated revenue figure), or the first growth figure.
5. Revision: the release is compared with the same issuer's most recent earlier Item 2.02 release (at most
   200 days earlier) that stated guidance of the same kind for the same fiscal year. Level change = new
   midpoint / old midpoint - 1 (dollar), or (1 + new growth) / (1 + old growth) - 1 (growth, as in the AMD
   example: 1.50 / 1.37 - 1 = +9.49%).
6. Class: RAISE if the level change is at least +1.0%, CUT if at most -1.0%, MAINTAIN otherwise. A first
   guidance for a fiscal year has no class and is not an event.

## Counts to report (no prices)
Filings found and parsed; releases with any guidance; events by class and year; events per issuer; share of
eToro-listed issuers (`etoro_instruments-20261016T190421Z`).

## Accuracy audit (before GO)
A reviewer who sees only the two source sentences, never a price, checks 40 RAISE and 20 CUT events drawn
with seed 20261017: is it the same company's total revenue guidance for the same fiscal year, and is the
direction right?

## GO if all hold
- RAISE events >= 300 and CUT events >= 100 in 2020-07..2022-11.
- Audit precision >= 85% for RAISE and >= 80% for CUT.
- Acceptance time found for >= 98% of events.

Otherwise NO-GO, recorded as is. A changed rule after a NO-GO is a dated amendment made before any return.
