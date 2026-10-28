# KILL_TEST_2020_2022: would the SEC13D FIRE rule have shown any edge in 2020-2022? (one shot, can fail, cannot confirm)

Frozen 2026-10-28, before any 2020-2022 Schedule 13D filing, header or price was read for this test. The owner's
instruction: "merge PR #16 and do 1, 2, 3, 4, 5" (item 4; `handoff/decisions/2026-10-28c_proof_program.md`). This test
overrides, for itself only, the Catalyst Register protocol's "no backtest of any family". The prospective SEC13D register
is unchanged and keeps running. Paper only, no orders. The sealed US holdout (2024 onward) is never loaded: the panel ends
2023-12-29 and no event is scored past 2022-12-30.

**Why.** At t >= 3, the prospective register needs about 960 FIRE sets (1 to 2 years) to detect a 2% edge. If the family
is dead, that year is wasted. With survivor-only prices this test cannot confirm an edge. Delisted names are missing,
and the 13D subjects are the more failure-prone group, so the bias pushes measured returns up. A negative point estimate
despite that bias is therefore a strong reason to stop.

## Events

- **Filings**: every original `SC 13D` (not `SC 13D/A`, not 13G) in the EDGAR full-index quarterly `form.idx` files of
  2020 Q2 to 2022 Q4 (`https://www.sec.gov/Archives/edgar/full-index/<YYYY>/QTR<q>/form.idx`). Filings dated 2020-04-01 to
  2020-06-30 only seed the 90-day repeat rule. Scored events have entry sessions from 2020-07-01 to 2022-11-30, so every
  20-session hold ends before 2022-12-30.
- **Header**: each filing's `-index-headers.html` gives `ACCEPTANCE-DATETIME` (New York time) and the SUBJECT COMPANY's
  CIK. A filing without both is dropped and counted.
- **Ticker**: the subject CIK's tickers in today's SEC `company_tickers_exchange.json`, taking the first (SEC order) that is
  in the pinned US repair panel (`data/manifests/panel_us_repair-20261008T114805Z.json`, sha256 `8d3b7ce4be56...`).
  Otherwise the event is dropped and counted; this is survivorship, stated rather than hidden.
- **Repeat**: another original SC 13D on the same subject in the 90 calendar days before (from the list itself) drops the
  event (SKIP_REPEAT_90D).
- **Operating issuer**: the subject's submissions JSON (recent block plus chunk files) shows a 10-K, 10-Q, 20-F or 40-F
  (or /A) in the 550 days up to the acceptance date and no N-CSR, N-CSRS, NPORT-P or N-CEN in those days. Otherwise
  SKIP_NOT_OPERATING.

## Timing (as the live register, with sealing at the moment of acceptance)

- **Entry session**: the first panel session whose 09:15 New York is after acceptance.
- **Signal session**: the panel session before it.
- **Position**: DURING (accepted after the signal session's previous close and up to the signal session's 16:00 close) or
  AFTER (after the signal session's close).

## Coverage class (the live rules, evaluated with data public by the acceptance date)

- **DILUTION_RECENT**: an `idxsig.catalyst.is_dilution` filing with filingDate from the 19th weekday before the signal
  session to the acceptance date.
- **MOVED_ALREADY**:
  - DURING: the signal close is at least 1.15 x the previous close.
  - AFTER: the ratio is 1.
- **MICROCAP**: the latest `dei:EntityCommonStockSharesOutstanding` fact (data.sec.gov companyconcept; latest 'end', then
  latest 'filed', filed on or before the acceptance date) x the signal close is below USD 50 million. No fact means
  MV_UNKNOWN, which also abstains.
- **FIRE** when none of the three holds.

## Plan and comparison

- **Execution**: the harness's (`idxsig.event_study.us_config(hold=20)`, E9's US configuration): buy at the entry
  session's open, sell at the close 20 sessions later, US fees and cost tiers, fill model B, at most 10% participation.
- **Controls**: `idxsig.event_study.run_events` with controls v2, 200 draws, seed 20261007, and overlap "skip". This is
  matched controls, as tests 26 and 27 used, not the register's five event-free twins; the controls are matched on price
  band, liquidity, momentum and drawdown, and are not screened for filings.
- **Excess** = the event's net return minus its control mean.

## Statistic and verdict (FIRE events, status EXITED with at least one scored control)

- **GO rule (counts only, before any return)**: at least 300 scored FIRE events. Otherwise the verdict is INCONCLUSIVE
  (too few) and no return statistic is read.
- **Primary**: mean excess, with a t from 10,000 bootstrap resamples of ISO weeks of the entry session (seed 20261203).
  The one-sided p for "mean excess > 0" is recorded.
- **Verdict**:
  - **KILL** if the mean excess is at or below 0.
  - **NOT_KILLED** if it is above 0. This is not a confirmation, because survivor-only prices bias it upward.
- **Descriptive only**: the win rate (share of excess > 0) and its Wilson interval; the median; the ABSTAIN class and all
  events with the same statistics; each abstention rule's own class.
- **On KILL**: the session advises the owner to stop the prospective SEC13D family. Nothing changes automatically, and
  sealing continues until the owner decides.
- **On NOT_KILLED**: the prospective register continues as frozen.

## Running it

- **Collect (no prices)**: `collect.py` writes `events.csv.gz` (one row per original filing with its header fields,
  ticker, rule inputs and drop reason) and `COLLECT.json` (the request log as URL, HTTP status and sha256; the funnel
  counts). Responses are not cached in git. The SEC contact is passed inline (`KOD_SEC_CONTACT`), never written.
- **Freeze**: `freeze.py` writes `PINS.json`: the sha256 of this protocol, `protocol.json`, `kt_lib.py`, `run.py`,
  `events.csv.gz` and the panel manifest. It is committed and pushed before the run.
- **Run once**: `run.py` checks the pins, applies the GO rule, reads the panel and writes `results/RESULT.json`, then the
  trial file `research/QUANT_GRADE/trials/CATALYST_REGISTER_v1_SEC13D_KILL_TEST_2020_2022.json` (counted, variants 1).
  A rerun is refused when `results/RESULT.json` exists.
