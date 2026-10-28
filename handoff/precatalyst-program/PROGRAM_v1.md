# Pre-catalyst program v1: how KOD Machine can reach a low losing rate on catalyst detection

Written 2026-10-28 by the cloud session (`session_01SrR7rsdNDD1Fqye2K6MDSw`) at the owner's request: *"study other
relevant studies other than speculative design to make KOD Machine give out a low losing rate and a high win rate
detection of a pre-catalyst … think like a PhD researcher and an inventor with financial knowledge, coding expertise
and creative mastery … be flexible."*

This is a research memo and a proposal. Nothing in it was run as a counted test, nothing in it changes the paper
routines, no data was bought, no order was placed. Figures quoted from the repository were re-read from the files named;
figures quoted from outside are literature values with their caveats, found in this session's searches on 2026-10-28.
Where a number is a literature value, it is a prior to be measured against, never a claim about KOD.

**One-paragraph answer.** Thirty counted tests say that the daily tape does not tell direction before a move: every
tape feature that preceded rises preceded falls just as often (LEAD_LADDER, FLOW_IDX, E5, E6, E8), and 0 of 20 random
IDX moonshots had a usable public tell three sessions before (CASES_IDX). The only leads that passed anything were
*events with a mechanism*: an exchange announcement (BINANCE_ANN_1S), insider purchases (IDX_INSIDER_NEWS,
US_INSIDER_BUY). A high win rate is therefore not something a detector can add to a tape signal; it is a property of
*which events* the machine agrees to speak about and *when it abstains*. Four fields outside finance say the same thing
in their own words (screening-test mathematics, selective classification, forecasting tournaments, group-sequential
trials). The program below turns that into one instrument, the **Catalyst Register** (the Speculation Register run over
dated event lists instead of scan candidates), ranks the event families by documented effect, free data, exact timing
and mechanism, and freezes the first experiment: **Schedule 13D filings on EDGAR**, sealed before the next open, with
a pre-registered abstention rule; with an **IDX index-review** register sealed this week for the 2 November 2026
effective date as a descriptive first data point. Everything stays paper, pre-registered, one run, counted, t ≥ 3.0.

---

## 1. What "low losing rate" means, and why the tape cannot deliver it

### 1.1 The screening-test identity

Medicine learned this in the 1940s and the project re-learned it in October: the positive predictive value of a test is
set by prevalence, not by the test.

    PPV = sensitivity × prevalence / (sensitivity × prevalence + (1 − specificity) × (1 − prevalence))

For a rare event this collapses to **precision ≈ base rate × lift**, where lift is how many times more often the
flagged days start a move than unflagged days do. LEAD_LADDER measured base rates of 0.2–1.1 % per
ticker-day for a +30 % start; the best surviving cell had lift about 2–3. Precision is then 0.5–3 %, so ">97 % of
flagged days are false" (the report's own line). No detector built on a 1 % base rate reaches a high win rate, whatever
its AUC. E1's volatility AUC 0.68 and E2's 0.78 look strong and are useless for direction: they separate *movers* from
non-movers in both directions.

The arithmetic allows exactly one escape: **raise the base rate by choosing the conditioning set**. Condition on an
event whose mechanism fixes the direction, and the base rate of a positive 20-session excess moves from 1 % to
50–90 %. That is where every documented high-win-rate strategy in the literature lives: merger arbitrage (deal
completion rate about 90 %), index inclusions in the years the effect existed, forced flows with a known sign.

### 1.2 Selective prediction: the win rate is chosen, then earned

Selective classification (El-Yaniv & Wiener 2010; Geifman & El-Yaniv 2017) formalises what a careful trader does by
instinct: a classifier with a reject option trades **coverage** (how often it speaks) for **risk** (how often it is
wrong), and the whole curve is the object to report, not a single accuracy. Two 2026 preprints found in this session's
search apply the idea to financial forecasting (abstain when the model's own confidence is low; the covered subset
reaches high accuracy while coverage drops to a fraction). The honest version of "high win rate" is therefore:

> At coverage c (the share of events the register agrees to speak on), the realised win rate is w(c), measured
> prospectively on sealed sets.

KOD already has the pieces: the Speculation Register seals statements with priors before the outcome; adding a sealed
**fire/abstain flag** per set, computed from frozen rules, turns it into a selective predictor whose risk–coverage curve
is auditable. The rule is written before the first seal and never tuned on running numbers (the register's forbidden
list already says so).

### 1.3 Forecasting tournaments: calibration is the asset

Good Judgment Project forecasters were scored on Brier (Tetlock & Gardner 2015); the register already reports Brier
beside 0.5 and the running base rate. The far-future reading: as filings are read by machines within seconds, the
*drift* after public events will keep shrinking (McLean & Pontiff 2016 measured 26 % out-of-sample and 58 %
post-publication decay of published anomalies; Greenwood & Sammon 2025 show the S&P 500 index effect fell from about
+7 % in the 1990s to about zero after 2010). What does not decay is a **stamped record of sealed, dated, falsifiable
calls with their realised rate**. Whatever KOD trades later, that record is what makes its claimed win rate believable
to the owner, to a reviewer, or to a counterparty. The register builds it as a by-product.

### 1.4 Group-sequential trials: looking more than once without cheating

The register looks at n = 60, 120, 240. Clinical trials solved repeated looks with alpha spending (O'Brien & Fleming
1979; Lan & DeMets 1983): early looks need a stricter boundary. A v2 protocol should state the three boundaries from an
O'Brien–Fleming-type spending function at information fractions 0.25, 0.5, 1.0 (roughly z 4.3, 3.0, 2.0 for a
two-sided 0.05; the exact values go in the protocol before the first seal), with the project's t ≥ 3.0 as a floor at
every look. This costs nothing and removes the one soft spot in the current look rule.

### 1.5 Blind analysis and planted signals

LIGO and particle physics seal the analysis before unblinding and inject synthetic events to measure the pipeline's
sensitivity. KOD's sealed holdouts and pre-registration are the first half; the register's **twins** are the second
half (each candidate is scored against five matched names drawn from the same scan, so a market-wide move cannot
masquerade as an edge). The Catalyst Register keeps both.

---

## 2. What KOD already knows (the evidence table, re-read from the repository)

| Family | Test | Lead? | Primary result | Reading |
|---|---|---|---|---|
| Tape: volatility, drawdown, turnover, breakouts | E1, E2, E3, E5, LEAD_LADDER (28), LEAD_LADDER_INTL (29), FLOW_IDX (30), MOVERS_NOW | before the move, but **direction-blind** | AUC 0.68/0.78 for movement; 6/808 cells pass, "states, not timing"; INTL 0/256 secondary; FLOW 0/256 | Closed. "No daily-bar feature tested gives an early, directional warning of a moonshot in any market the owner can trade." |
| Tape: crypto pressure, funding, peer spillover | E6, E7, E8 | pre-move by design | p 0.32 / FAIL / p 0.114 | Closed |
| Exchange announcement | BINANCE_ANN_1S (22) | 0.5–1 s | +1.30 % net, t 3.58, n 103, Holm 0.0048 | PASS, but a forking path, the owner cannot use Binance, holdout has 29 of 40 events |
| Insider purchase news, IDX | IDX_INSIDER_NEWS (23) | days after the trade | +2.81 % excess at hold 20, t 3.07, hit rate 45 %, top 5 events = 45 % of excess | PASS in 2021–23; **OOT 2025–26 −2.52 %, t −1.21, FAIL** |
| Insider purchase, US Form 4 | US_INSIDER_BUY (26) | 1 day median trade→filing | +1.80 % at hold 60, t 2.87, hit rate 46 % at hold 20; 100–500k buys +3.02 %, 500k+ −0.81 % | LEAN_WITHOUT_SIZE; survivor-only (can fail, cannot confirm) |
| 8-K items | US_8K_ITEMS (27) | next open | nothing positive; **Item 3.02 −2.82 %, t −4.33 (hold 20), −5.46 % (hold 60)** | FAIL as a buy; 3.02 is an avoid flag |
| Guidance raise | E10 | first obtainable open | pre-entry excess +2.56 %, post-entry −0.21 % at 1 session | Priced before the open |
| Dilution, IDX share count +5 % | IDX_DILUTION_v1 | event | −13.7 % at hold 60, t −2.34, n 15 | Avoid flag (small n) |
| Documented vs undocumented +30 % days | E9 | after the move | DOCUMENTED beats UNDOCUMENTED by +1.99 (clipped +3.39), win rate +8.5 pts; DILUTION −10.9 % at 20 | Documentation helps, dilution hurts |
| Cases | CASES_IDX, CASES_GLOBAL | — | IDX 0/20 with a public tell at J−3; global 4/20 telegraphed, 3 of them **scheduled** events | "A calendar tells when, not which way" |

Three regularities fall out:

1. Every positive lead is an **event** with a known actor (an exchange, an insider), never a tape state.
2. The strongest *t* in the whole register is a **negative** one (3.02 dilution, t −4.33), and the owner's retirement
   decisions leave the short side open ("shorting the movers is not covered").
3. Where a scheduled date existed (DOCS, HCM, IMM in CASES_GLOBAL; the Zealand release; E10 raises), the price moved
   *at or before the first obtainable entry*. The lead is the calendar, and the trade is either the run-up into the
   date or the forced flow after it, not the reaction to the news.

---

## 3. The literature, by event family, with the caveats that matter

Ranked by the product of: documented effect × direction fixed by mechanism × free data × exact timing × market the
owner can trade × speed at which n accumulates. "Hit rate" is the literature's share of positive outcomes where one is
reported; most papers report means, not win rates, which is itself a warning.

| Rank | Family | Mechanism (why direction is known) | Documented effect | Free data, timing | KOD fit | Win-rate potential |
|---|---|---|---|---|---|---|
| 1 | **Schedule 13D initial filings (US)** | A holder crossed 5 % with intent; the market re-prices activism/takeover odds | Brav, Jiang, Partnoy & Thomas 2008: about +7 % abnormal over −10..+20 days around the filing, with post-filing drift; Klein & Zur 2009 similar; Collin-Dufresne & Fos 2015: activists buy before the filing, so part of the move precedes it; the 10-day window became 5 days in Feb 2024, and filings are structured XML since 2025 | EDGAR: 540 originals in Q3 2026, 166 in Q4 to 27 Oct (about 180/month); acceptance time in every header (sample: 06:16 ET, pre-open) | `idxsig.catalyst` already classifies 13D in E9; daily form index reader exists (`guidance_paper.index_url`); E9's cutoff logic gives the entry session | Mean positive by the literature; win rate not reported; microcap-heavy, so the liquidity filter will cut n. **First freeze.** |
| 2 | **IDX index reviews (LQ45, IDX30, IDX80, Kompas100; MSCI/FTSE Indonesia)** | Forced buying/selling by index funds on the effective date; announced ≥5 exchange days before the first trading day of the next month; quarterly (Jan/Apr/Jul/Oct) | Classic index effect (Shleifer 1986; Harris & Gurel 1986); decayed to zero in the US after 2010 (Greenwood & Sammon 2025); Widyawati & Wibowo 2020 on IDX: positive on inclusion, negative on exclusion, small n | Scheduled, exact. idx.co.id is 403 from this container; the lists must come from news (EmitenNews slugs carry 1,273 LQ45 rows, 120 MSCI, 33 FTSE in 2024–26) or the owner's download | Yahoo `.JK` bars already score IDX; the register's twins and cone work unchanged | Direction fixed; IDX passive AUM is small, so the effect may be small; n is 5–15 per review, so a counted look takes a year. **Seal this week (effective 2 Nov 2026), descriptive.** |
| 3 | **Insider cluster / opportunistic purchases (US Form 4)** | Insiders buy with their own money; the market under-reacts | Seyhun 1986, Lakonishok & Lee 2001; **Cohen, Malloy & Pomorski 2012: routine insiders (same calendar month every year) carry no information; opportunistic ones predict about +0.7 %/month abnormal**; cluster buys stronger in small caps; a 2026 microcap preprint: CAR 6.3 % for buys after a >10 % run; S&P 500 cluster buys: no effect | EDGAR Form 4: about 70,000 per quarter; bulk quarterly zips (`ib_lib`) and daily full-text search; no live Form 4 collector yet | KOD's own +1.80 % at hold 60 (t 2.87) is the prior; the protocol's own next step was a forward read-only watch | Moderate; the CMP routine/opportunistic split and the size band are the pre-registerable filters. Prospective sealing removes the survivor-only objection. |
| 4 | **Dilution and forced selling (avoid or short)**: 8-K 3.02, S-/424B, IDX share-count jumps, IPO lock-up expiries, token unlocks | Supply arrives; sellers are forced or price-insensitive | KOD: 3.02 −2.82 % (t −4.33), E9 DILUTION −10.9 %, IDX_DILUTION −13.7 %; Field & Hanka 2001: about −1.5 % around US lock-up expiry; Keyrock: about 90 % of large token unlocks carry negative pressure; Tokenomist: −14.7 % median in the month before; Kim 2025: 88.5 % negative within 72 h (exploratory) | 8-K items daily and free; S-1 dates give lock-up expiries (180 days) for free; IDX listed-share counts from the mirror (ends 2025-02-21) or Yahoo; **token unlock calendars are paywalled (DefiLlama 402)** | Already coded for 8-K; as an **abstention input** it costs nothing | High as an avoid rule; as a short, broker borrow decides. Shorting is outside the retirement decisions but needs the owner's explicit go. |
| 5 | **Definitive merger agreements (US 8-K 1.01; IDX mandatory tender offers)** | Contract price; completion rate about 90 % | Mitchell & Pulvino 2001 (4,750 deals): high win rate, small gains, fat left tail on breaks; Baker & Savaşoglu 2002; spreads have compressed since | `sensors.edgar_8k` already searches "definitive agreement" / "merger agreement"; IDX MTO price is set by regulation (POJK 9/2018: highest price in 90 days), no empirical study found | The 5/20-session scorer is a poor fit: deals take 3–6 months | **The literal high-win-rate family**, but 2–5 % per deal and months to resolve; register it as sealed statements ("closes at ≥ P by D") rather than as a 20-session trade |
| 6 | **Scheduled binary events** (earnings dates, PDUFA dates, trial readouts, airdrops) | The date is public; the direction is not | Earnings announcement premium (Frazzini & Lamont 2007; Barber et al. 2013 international; Heitz et al. 2025: in the US it migrated to 8-K periods); Rothenstein et al. 2011: oncology stocks drift *before* positive announcements (leakage, not a public signal) | Earnings dates from 8-K history; ClinicalTrials.gov completion dates free (an MCP tool is attached to this session) | CASES_GLOBAL named this as "when, not which way" | A run-up register (hold into the date, exit before) has positive mean in the literature and a modest win rate; direction on the date is a coin the tape cannot read |
| 7 | **Exchange listings (crypto)** | Access and liquidity shock | 2023: +41 % median after Binance listing; IOSG 2025: 14-day median −29.7 % in 2025; Alpha→spot 10–12 % | Binance CMS feed is free and already wired; in Oct 2026 the feed is mostly tokenised equities | Owner cannot use Binance; Coinbase/Kraken listing pages untested | Reversed in 2025; low rank |
| 8 | **Pump-and-dump targeting (crypto)** | Coordinated groups pick thin coins | Xu & Livshits 2019 (USENIX Sec.); Hu et al. 2023 (SIGMOD): HR@3 41 % over 709 events | Telegram channels, not reachable from here; descriptive only | Against the owner's "no green dildos" stance | Not pursued |

Three further sources of ideas from outside finance, each already partly present in KOD and worth naming:

- **Reliability engineering's pre-mortem**: every sealed set should carry the one statement that would falsify the
  family's mechanism (for 13D: "the filer is a passive 13G-type holder re-filed as 13D"; for index: "the fund flow
  arrives before the effective date"). The register grades it like any other statement, so the mechanism itself gets a
  calibration score.
- **Epidemiology's case-control matching**: the twins are a matched control group; for event registers the matching
  should add the *event-free* condition (no filing in the prior 20 sessions), which `draw_twins` does not yet check.
- **Actuarial underwriting**: the loss ratio is managed by declining risks, not by predicting better. The abstention
  rule is underwriting.

---

## 4. The instrument: Catalyst Register v1 (Speculation Register over event lists)

Everything below reuses `idxsig/speculation.py`; the differences are the source of candidates and one extra sealed
field.

| Piece | Speculation Register v1 (live) | Catalyst Register v1 (proposed) |
|---|---|---|
| Candidate source | `pending_decisions()` from `ledger.jsonl` | an **event list** per family (13D: today's EDGAR form index filtered to `SCHEDULE 13D`, originals only; INDEX: the review's additions/deletions) |
| Cutoff | before the frozen plan's entry | before the family's entry (13D: next open after acceptance, using E9's 16:00 / 09:15 ET cutoff rule; INDEX: the announcement session's close, entry next open) |
| Cone | RUN30_5, FADE10_5, GAIN0_5, BEATS_TWINS_5, RUN30_20, DOUBLE_20 | the same, plus **GAIN0_20** (the family's primary) and one **mechanism-falsifier** statement per family |
| Priors | frozen 2023 validation | literature priors with citation (13D GAIN0_20: 0.55–0.60, from Brav et al. 2008's post-filing drift; INDEX inclusion GAIN0_20: 0.5, no IDX base rate on record), then the running base rate after 20 resolved |
| Twins | 5 matched from the scan's frozen features | 5 matched by band, liquidity quintile, momentum and drawdown terciles **and no filing of the same family in the prior 20 sessions** |
| New field | — | `coverage`: `FIRE` or `ABSTAIN`, with the rule id; the risk–coverage curve is reported per family |
| Decision rule | per-session paired t, looks at 60/120/240, p < 0.05, t ≥ 3.0, mean net > 0 | the same, with O'Brien–Fleming boundaries at the three looks written into the protocol and t ≥ 3.0 as the floor |
| Register entry | `SPECULATION_REGISTER_v1_registered.json`, counted at each look | one registered file per family, counted at each look (tests 31+) |
| Ledger | `paper/speculations.jsonl` | `paper/catalysts.jsonl`, same hash chain and RFC 3161 stamps, added to `check_append_only` |

What is *not* in it: no backtest of any family (the literature and KOD's own tests are the priors; the register is the
test), no holdout read, no tuning on running numbers, no order, no change to `PAPER-POLICY-v4`, no new scheduled task
without the owner's yes.

Code estimate: one module `idxsig/catalysts.py` (event-list builders, 150–250 lines), one CLI command
`catalyst --family F --market M [--commit]` reusing `speculate`'s seal/score/report path, tests mirroring
`test_speculation.py`, one protocol folder `research/CATALYST_REGISTER_v1/`. About a day's work, done after the
owner's go, in a draft PR.

---

## 5. The first experiment, ready to freeze: `CATALYST_REGISTER_v1 / SEC13D`

Everything here is the draft protocol; it is frozen only when the owner says go, and then sealed before the first set.

- **Universe**: US issuers with a common equity ticker on Nasdaq/NYSE/NYSE American (the US universe the paper scan
  already builds), price ≥ USD 1, median 20-session dollar volume ≥ the paper scorer's existing liquidity rule.
- **Event**: an original `SCHEDULE 13D` (not `/A`, not 13G) accepted on EDGAR; one event per issuer per 90 days;
  the subject company's CIK mapped to the ticker through `company_tickers.json` (free).
- **Entry session**: acceptance before 09:15 ET → that session's open; otherwise the next session's open (E9's rule).
  The set is sealed before the entry session's open; a set sealed later is refused, as `speculation.seal` does today.
- **Plan**: entry at the open, exit at the close of entry + 20 sessions, costs as `EXEC-US-v1`, no stop (mirrors the
  frozen plan convention: the plan is a yardstick, not a strategy).
- **Cone and priors**: GAIN0_20 prior 0.55 (literature, weak); FADE10_20, RUN30_20 at running base rates (0.5 until
  20 resolved); BEATS_TWINS_20 0.5; falsifier: "the filing's Item 4 names only investment purposes with no intent
  language" (graded from the XML, descriptive).
- **Abstention rule (pre-registered, three conditions, all mechanical)**: ABSTAIN if (a) an 8-K with Item 3.02 or any
  S-/F-/424B filing in the prior 20 sessions (dilution, KOD's own t −4.33), (b) the entry-session open is already
  ≥ +15 % above the prior close (the move is done; the E10 lesson), (c) the subject company's market value is below
  USD 50 M on the last close (the microcap tail where E9's UNDOCUMENTED losses live). FIRE otherwise. Both classes
  are sealed and resolved; the primary test is on FIRE sets only, and the ABSTAIN sets' realised rate is reported
  beside it so the rule itself is graded.
- **Primary hypothesis**: on FIRE sets, mean net return of the plan minus the twins' median > 0, per-session paired t,
  looks at n = 60, 120, 240 FIRE sets from ≥ 15 sessions, O'Brien–Fleming boundaries, t ≥ 3.0 floor, p < 0.05, mean
  net > 0. Secondary (descriptive): win rate at each coverage, Brier of every statement, the falsifier's rate.
- **Expected n**: about 180 originals per month before filters; perhaps 60–100 after liquidity and abstention, so the
  first look in 3–5 weeks and the third in about three months.
- **Reading on PASS**: eligible for the owner's review; on FAIL: the family closes, like every other line.
- **Data**: EDGAR daily form index and filing headers (free; `KOD_SEC_CONTACT` inline, never in a file), Yahoo daily
  bars the scorer already pulls, `company_tickers.json`. No new subscription.

Second seal, descriptive and not counted: `CATALYST_REGISTER_v1 / IDX_INDEX` for the October 2026 review effective
2 November 2026. Needs the additions/deletions list from a news source (EmitenNews or the owner's own download of the
IDX announcement; the IDX site is blocked from the container), sealed before 2 November's open, scored with the same
cone and twins. One review is one data point; four reviews a year means this family is slow, which is why it is second.

---

## 6. What this program does not promise

- It does not promise moonshots. The families with a known direction move 2–7 % on average; the +30 % days remain, on
  thirty tests of evidence, undetectable in advance from public daily data. A high win rate and a +30 % target are
  different products; the owner should choose which one the machine is for.
- It does not promise a win rate before it is measured. Every number in section 3 is a prior from another market or
  another decade, and the literature's own meta-finding is that such effects shrink once known.
- It cannot read options flow, broker-level IDX flow, Unusual Whales or X, the four inputs the case studies named for
  direction; all four are outside the free, reachable data, and two are outside the owner's rules.
- It will not run until the owner says so: a counted test, a new ledger and any routine change are the owner's calls.

## 7. Asks

1. Go / no-go on freezing `CATALYST_REGISTER_v1 / SEC13D` as test 31 (code in a draft PR, protocol sealed before the
   first set).
2. Yes / no on sealing the IDX index-review register for 2 November 2026 (descriptive, not counted), and whether the
   owner can paste the review's list if the news sources do not carry it in time.
3. Whether the dilution rule (8-K 3.02, S-/F-/424B in the prior 20 sessions) may also be added as a *descriptive tag*
   on the existing Speculation Register sets (metadata only, like `hot_day`; no change to the live cone or plan).
4. Whether the short side of the dilution family is open for a separate pre-registered protocol later (no action now).

## Sources

Repository: `idx-signals/research/{E1,E2,E5,E6,E8,E9,E10,LEAD_LADDER_v1,LEAD_LADDER_INTL_v1,FLOW_IDX_v1,BINANCE_ANN_1S,
IDX_INSIDER_NEWS,IDX_INSIDER_NEWS_OOT,US_INSIDER_BUY,US_8K_ITEMS,IDX_DILUTION_v1,CASES_IDX_v1,CASES_GLOBAL_v1,
MOVERS_NOW_v1,SPECULATION_REGISTER_v1}/`, `idx-signals/research/QUANT_GRADE/trials/` (30 counted),
`idx-signals/idxsig/{speculation,catalyst,sensors,guidance_paper,us_actions}.py`, `handoff/BLUEPRINT.md`,
`handoff/decisions/`. Free-data probes this session (2026-10-28): EDGAR `form.idx` Q3 and Q4 2026 counts; sample
filing 0001104659-26-108394 header (acceptance 06:16 ET); efts full-text search (form type is `SCHEDULE 13D`);
DefiLlama unlocks endpoint (HTTP 402); idx.co.id announcement API (HTTP 403, Cloudflare); Binance CMS catalog 48;
EmitenNews slug counts from `research/MOVERS_NOW_v1/inputs/en_ticker_headlines.csv.gz`.
Literature (values quoted as published; none re-verified against raw data here): Ball & Brown 1968; Fama, Fisher,
Jensen & Roll 1969; Shleifer 1986; Harris & Gurel 1986; Seyhun 1986; Lakonishok & Lee 2001; Mitchell & Pulvino 2001;
Field & Hanka 2001; Baker & Savaşoglu 2002; Frazzini & Lamont 2007; Brav, Jiang, Partnoy & Thomas 2008; Klein & Zur
2009; El-Yaniv & Wiener 2010; Rothenstein, Tomlinson, Tannock & Detsky 2011; Cohen, Malloy & Pomorski 2012; Barber,
De George, Lehavy & Trueman 2013; Collin-Dufresne & Fos 2015; Tetlock & Gardner 2015; McLean & Pontiff 2016; Geifman &
El-Yaniv 2017; Xu & Livshits 2019; Widyawati & Wibowo 2020; Hu et al. 2023; Greenwood & Sammon 2025; Heitz et al. 2025;
Kim 2025; IOSG 2025; Keyrock and Tokenomist unlock studies; O'Brien & Fleming 1979; Lan & DeMets 1983; POJK 9/2018
(mandatory tender offers); SEC's 2023 amendments to Regulation 13D-G (5-day window from Feb 2024, structured filings).
