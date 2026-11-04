# GitHub finds, integration plan v1: what public repositories can give KOD Machine, and how each one plugs in

Written 2026-10-29 by the cloud session (`session_01SrR7rsdNDD1Fqye2K6MDSw`) at the owner's request: *"Check github somehow
and tell me any repository that will greatly benefit us even if the intended creation is different"*, then *"Do one more pass
in github of research and i want you to plan how to integrate it to our kod machine."*

This is a plan, not a result. Nothing in it was run as a counted test, nothing changes a routine, a frozen protocol, a
ledger or a sealed holdout, no data was bought, no account was opened, no order was placed. Every fact about a repository
was read today from the repository page or its raw files; every fact about a data archive was checked from this container
with an HTTP request (the checks are listed in section 7). Literature numbers are priors to measure against, never claims
about KOD.

**One-paragraph answer.** Two passes over public GitHub found one thing the machine lacks and can use at once: *labelled
pre-catalyst events*. Three research groups published lists of real, organised crypto pump-and-dumps on Binance (coin, group,
date, hour), about 1,300 distinct events from 2018 to early 2022, and the Binance public archive still serves minute bars for
every one of those pairs, including the pairs Binance later removed. That is a dated catalyst with a *known time and an
unknown target*, the exact shape of the question the machine exists to answer, and three peer-reviewed papers report that the
target can be ranked before the pump. The plan's main track is one frozen history study on those labels, run once, counted,
with the live form decided only after the result. Three smaller tracks use repositories to make KOD more *reliable* rather
than smarter (a second SEC reader in tests, a next feature block to test the way CHART was tested, exchange-made IDX labels),
and a skip list says what was looked at and left alone. One branch at a time, as Ace advised; LEARNER v2.4 stays untouched
and collects its live record meanwhile.

## 1. What was found (verified today) and the verdict on each

| Repository | What it is | Verified facts (2026-10-29) | Licence | Verdict |
|---|---|---|---|---|
| [SystemsLab-Sapienza/pump-and-dump-dataset](https://github.com/SystemsLab-Sapienza/pump-and-dump-dataset) | Pump list from the ICCCN '20 paper (La Morgia et al.) | `pump_telegram.csv`: 1,110 rows (symbol, group, date, hour UTC, exchange). Binance: 520 rows, 2018-01-03..2021-01-18, 85 symbols, 19 groups, 318 distinct symbol-dates; the rest Yobit 276, Cryptopia 210, Bittrex 102, KuCoin 2. 75 of the 85 Binance symbols were pumped more than once. Pump hours cluster at 16:00-20:00 UTC. | MIT | **Use** (Track A) |
| [ArdiaD/PumpDump](https://github.com/ArdiaD/PumpDump) | Pump list from Ardia & Bluteau (2024), *Twitter and cryptocurrency pump-and-dumps*, IRFA | `data/list_pd_events.csv`: 1,160 rows, Binance only, 2019-01-02..2022-02-02, 95 channels, 221 coins, a `success` flag (322 of 1,160), 1,113 distinct symbol-dates; 160 of them also in the Sapienza list; union of the two: 1,271 symbol-dates | none stated; README asks for citation and the data DOI | **Use by reference** (pin URL + sha256, fetch at build, do not redistribute) |
| [Bayi-Hu/Pump-and-Dump-Detection-on-Cryptocurrency](https://github.com/Bayi-Hu/Pump-and-Dump-Detection-on-Cryptocurrency) | Code and data of Hu et al., SIGMOD '23, *Sequence-based target coin prediction* | `Data/Telegram/Labeled/PD_logs_cleaned.txt`: 709 pumps (1,335 samples) 2019-01-01..2022-01-15; Telegram collection (Telethon), message classifier, the SNN target-coin model; "9 statistical features and coin id", features hosted on Google Drive; 63 stars; default branch `master` | none stated | **Use by reference** for the event list; read the code, do not import it |
| Binance public archive ([binance/binance-public-data](https://github.com/binance/binance-public-data), data.binance.vision) | Monthly/daily zips of klines, trades, aggTrades, with sha256 checksums | 3,738 symbols with monthly klines. 84 of the 85 Sapienza Binance pairs present (YOYOW is listed under Binance's ticker YOYO). Pairs Binance removed are still served: HTTP 200 for the 1-minute monthly files of BCPT, CDT, POE, EVX, SNGLS and WPR for 2019-06 and 2020-06. KOD already reads this archive (BINANCE_ANN_1S, E6, E7). | MIT (scripts); data under Binance terms, research use | **Use** (prices for Track A) |
| [dgunning/edgartools](https://github.com/dgunning/edgartools) | SEC EDGAR library: Form 4 to DataFrame, 8-K items, 10-K/10-Q sections, 13F | MIT, 2.8k stars, Python 3.11+, identifies to SEC with `set_identity(...)`; SC 13D not confirmed on the page | MIT | **Use in tests only** (Track B) |
| [nlpaueb/edgar-crawler](https://github.com/nlpaueb/edgar-crawler) | Item-level JSON extraction for 10-K, 10-Q and 8-K | GPL-3, 552 stars, `item_5.02`-style keys for 8-K | GPL-3 | Optional cross-check for US_8K_ITEMS (Track B) |
| [DynamicsAndNeuralSystems/pycatch22](https://github.com/DynamicsAndNeuralSystems/pycatch22) | The 22 canonical time-series features (Lubba et al. 2019), C with a Python wrapper | GPL-3 or later, 105 stars, `catch24` adds mean and sd; outputs changed across versions, so the version must be pinned | GPL-3 | **Candidate next feature block** (Track C) |
| [nichsedge/idx-bei](https://github.com/nichsedge/idx-bei) | IDX scraper over idx.co.id's own JSON endpoints (daily OHLCV with foreign flow and bid/offer, broker summary, 15 corporate-action categories, announcements with `keywords`, `dateFrom`, `dateTo`) | MIT, 167 stars, Python 3.13+, uses a browser-impersonating client; endpoints documented in `docs/API_VERIFICATION_SPEC.md`. From this container idx.co.id answers HTTP 403 (a Cloudflare page) to the announcement endpoint, for both `keywords=UMA` and `keywords=suspensi`. | MIT | **Use only from a machine idx.co.id lets in** (Track D) |
| [eslazarev/purged-cross-validation](https://github.com/eslazarev/purged-cross-validation) (purgedcv) | Purged K-fold, CPCV, deflated and probabilistic Sharpe, PBO | MIT, 60 stars, scikit-learn splitter interface | MIT | Reference implementation for the idea grader (Track E); not a dependency |
| [bashtage/arch](https://arch.readthedocs.io/en/stable/multiple-comparison/multiple-comparison_examples.html) | White's reality check, SPA, StepM, model confidence set | documented and maintained | permissive | Same as above |
| [wildangunawan/Dataset-Saham-IDX](https://github.com/wildangunawan/Dataset-Saham-IDX) | IDX daily prices mirror | CC BY-NC 4.0, irregular manual updates. KOD's `idxsig/sources/idx_mirror.py` already points at it. | CC BY-NC | Already in use; nothing to add |

Looked at and left alone, with the reason: `xujiahuayz/pumpdump` (Xu & Livshits 2019: an R notebook and one JSON, no licence,
last touched 2022; its 412 events of 2018-19 fall inside the lists above); `SystemsLab-Sapienza/gme-pump-xrp-telegram` (chat
logs of one XRP group, no event list); `antonizer/IDX-Scrapper` (same non-commercial terms as the mirror KOD already uses,
nothing new); Microsoft Qlib (a platform; its Alpha158 set is just another feature block, and one block is tested at a time);
WallStreetBets mention counts (commercial: Quiver, Thinknum); survivorship-free US prices (no free source found; EODHD,
Norgate and MarketParquet are paid, the owner's call); pump bots (participation code, not research); SEC litigation releases
(narratives, not a labelled list; a labelling project for later); the real-time Telegram paper of Bolz et al. 2024 (no code
or data released).

## 2. Why the pump lists matter more than their subject

The machine's goal is pre-catalyst prediction. Thirty counted tests say the daily tape alone does not tell direction before
a move, and the only leads that passed anything were events with a mechanism (`handoff/precatalyst-program/PROGRAM_v1.md`).
Every event family so far has a *known target and an unknown time* (a filing names the company; the question is what
follows). An organised pump is the mirror image: the group announces the *time* days ahead and keeps the *coin* secret. So
the pump lists are the first labelled set of **scheduled catalysts with unknown targets**, and three papers report that the
target is rankable in advance:

- Xu & Livshits (2019): 412 pumps, June 2018-February 2019; a random forest over pre-pump features gave "high precision",
  and a strategy on its ranking returned up to 60% in the test period.
- Hu et al. (SIGMOD 2023): 709 pumps; groups re-pump the same kinds of coin ("intra-channel homogeneity"); our own count
  agrees: 75 of 85 Binance symbols in the Sapienza list were pumped more than once.
- Bolz et al. (2024, arXiv 2412.18848): 2,079 events from Telegram 2017-2024; with trade and order-book z-scores the true
  target was in the top 5 of 50 candidates 55.8% of the time 20 seconds before the pump (top 10: 74.4%), falling to 19.1%
  top-5 one minute before. Chance for top 5 of 50 is 10%.

The skill to be learned is *ranking candidates before a dated event*, and that skill is market-agnostic: the IDX index
review KOD already seals sets for (a known effective date, an unknown list until the announcement) and US index
reconstitutions have the same shape. The crypto labels are simply the only place the skill can be measured on history with
free data today.

Two honest caveats before the plan. The lists end in early 2022, and the 2024 paper found pumps running on LATOKEN, KuCoin,
MEXC, Poloniex and XT.com, not Binance, so a *live* Binance family may see few events; the history study is still the right
first step because it measures the skill, not the venue. And the machine forecasts and grades on paper only; taking part in
a pump with money is market manipulation, and nothing here moves toward that.

## 3. Track A (main): `research/CRYPTO_PUMP_HISTORY_v1`, one frozen study on labelled pumps

The same four-step shape as PATH_HISTORY_v1 and TA_HISTORY_v1: pin inputs, feasibility without outcomes, freeze, one run.

**A0. Pin the inputs (no computation).** Commit `pump_telegram.csv` (MIT) under `data/` with its sha256
(`7ca4d2ac21b02888…`, full value in the manifest). Record the ArdiaD and Bayi-Hu lists by URL and sha256 in a `SOURCES.json`
and fetch them at build time with the hash checked, since neither carries a licence; cite both papers and the data DOI as
their READMEs ask. Record the archive's own `.CHECKSUM` for every kline file read.

**A1. Feasibility (reads no outcome).** Union the three lists on (Binance ticker, UTC date, hour); report the count (about
1,300 expected), the per-year counts, the groups, and the number of events whose pair has 1-minute bars on the event day in
the archive. Build the candidate universe per event day from the archive's daily files: a pair is a candidate on day d when
it has a BTC-quoted daily bar on d (that is what a group could choose from). Report the universe size per year (an order of
150-300 BTC pairs is expected) and the base rate (events per candidate-day). Disk: 1-day and 1-hour monthly files for every
BTC pair (about 1 GB) plus 1-minute *daily* files only for event days (about 1,300 small zips); no 1-minute history for
non-events.

**A2. Freeze `protocol.json` before any feature or outcome is computed**, and register
`research/QUANT_GRADE/trials/CRYPTO_PUMP_HISTORY_v1.json` as PENDING (counted false).

- *Primary question Q1 (the target).* At the pump hour H on day d, rank every candidate pair by the model's probability of
  being the target. Score: the pumped pair's rank; headline metric the top-5 hit rate among N candidates, with top-10 and
  mean reciprocal rank beside it. Pre-declared benchmark: rank by 30-day BTC volume alone (the "cheap pick" a group makes).
  The claim is a *gain over the benchmark*, exactly as CHART was a gain over v2.3's features.
- *Two feature cut-offs, both frozen.* **Daily**: every feature is known at the close of d-1 (what a daily routine could
  act on). **Hourly**: every feature is known at H-1h (the insider-accumulation hypothesis of Xu & Livshits). Each is its
  own test.
- *Feature blocks, named in advance.* SIZE (7- and 30-day BTC volume, trades per day, listing age from the first archive
  bar); PRIOR (earlier pumps of this pair in the event list, time since the last one; time-aware, so only pumps before d
  count); TAPE (returns over 1h, 6h, 24h, 7d; volume ratios 1h/24h and 24h/30d; high-low range; share of 1-minute bars with
  a trade). Market capitalisation is *not* used: CoinGecko's API now needs a key (a new subscription, owner's approval), and
  volume stands in for it. Group identity is not a feature of Q1 (in live use the group is unknown); it may be reported
  descriptively.
- *Model.* The penalised logistic regression of `idxsig/learner2.py` (precision 16 on slopes, nothing tuned) on candidate
  rows, with the ranking taken within each event; no neural network. The SIGMOD model is a reference point, not a component.
- *Secondary question Q2 (the path), descriptive only.* Once a pump starts (first minute with a return and a volume burst
  above frozen thresholds), how far it runs and how many minutes until it gives half of it back, the same family of PATH
  statements as the US +30% dumps; reported, not claimed, in v1.
- *Out of time.* Fit 2018-2019, score 2020; fit 2018-2020, score 2021-22. Uncertainty by a cluster bootstrap over pump days
  (2,000 resamples, seed fixed in the protocol). Decision: Holm over the four tests (two cut-offs x two metrics, top-5 and
  MRR) at 5%; ADDS when the gain over the volume benchmark survives and the Brier score of the candidate probabilities also
  improves. Nothing from 2024 on is read: all events precede the crypto holdout.

**A3. Build and run once** (`build.py`, `run.py`, `results/RESULT.json`, `REPORT.md`), then the counted result file. Two to
three sessions of work after the freeze.

**A4. Decide the live form only from the result.** Three options, none chosen now:
1. *Pump-time known.* The groups pre-announce the hour; reading it needs a Telegram client (Telethon with a Telegram API id,
   the way the Sapienza and SIGMOD pipelines did). That is a new account and a new data feed: the owner's decision, not
   the session's. A manual version exists: the owner pastes an announced schedule, the machine seals a ranked set before the
   hour, the register resolves it from the archive the next day.
2. *Daily watch without Telegram.* If the daily cut-off passes, a Speculation Register family `CRYPTO_PUMP_WATCH` over
   Binance BTC pairs, sealed at the existing 00:23 UTC crypto run, with one statement: a volume-burst spike of at least x%
   within the next 24 hours. It rides the existing routine, so no new recurring job. Expect few live events on Binance now.
3. *Transfer.* Apply the ranking skill to the IDX index-review sets already sealed and to US reconstitutions: a frozen
   history study of its own, later.

**What it does not touch.** LEARNER v2.4, the registers, the ledgers, the routines, the sealed holdouts. It adds one
research folder and one counted trial.

**Three plain answers for Track A.** *What are we predicting?* Which Binance BTC pair an organised group will pump at an
announced hour, ranked among all pairs trading that day. *What counts as success?* Beating the volume-only ranking out of
time, in both score years, Holm-corrected, with better-calibrated probabilities. *What evidence so far?* None of KOD's own:
literature only (10% chance, 46-56% reported top-5 near the hour, "high precision" day-level in 2018-19).

## 4. Track B (reliability): a second reader for EDGAR in the tests

KOD reads Form 4, 8-K items, 424B5, SC 13D and share counts with its own code (`fam_form4.py`, `fam_dilution8k.py`,
`fam_sec13d_v2.py`, `learner3.edgar_features`). `edgartools` (MIT) parses the same forms independently. Plan: a test module
`tests/test_edgar_crosscheck.py` that runs edgartools over the *committed fixtures* (no network in CI) and asserts that
KOD's parse agrees on transaction codes, share counts, item numbers and dates; a disagreement is a bug in one of the two.
`edgar-crawler` (GPL-3) can do the same for the 8-K item split used by US_8K_ITEMS. Both are development dependencies
(`requirements-dev.txt`), never runtime ones, and nothing enters v2.4's frozen features. SEC identity is passed the way it
is today, inline from `KOD_SEC_CONTACT`, never written or printed. One session.

## 5. Track C (the next feature block, after v2.4 has a live record): catch22

TA_HISTORY_v1 established the procedure: one named block, the same 6,225 events, rolling origin, paired AUC gain, Holm, Brier
beside it, one run. The next block worth that procedure is **catch22**: 22 features chosen in the literature to be a minimal
non-redundant summary of a time series' dynamics (plus mean and sd as `catch24`), computed on the 60 and 120 closes before
the spike. It is small (so it cannot search much), principled (not a chartist's toolbox), and distinct from CHART. Rules:
pin `pycatch22`'s version in the protocol (its outputs changed across versions); GPL-3 is acceptable for an internal lab
that redistributes nothing; a block that ADDS becomes v2.5 **only at a pre-declared review point** (v2.4's first claim look,
at 30 populated sessions), because v2.4 now has a live record and two live challengers on one question is what Ace warned
against. Not before.

## 6. Track D (IDX labels): the exchange's own UMA notices

Unusual Market Activity notices are the exchange flagging an abnormal move: free labels for IDX pumps and dumps, made by the
exchange, with the stock code and date. KOD mentions UMA only as a reason to void a paper entry and records none of them.
Verified today: idx.co.id's announcement endpoint (`NewsAnnouncement/GetAllAnnouncement?keywords=UMA&dateFrom&dateTo`, as
documented by idx-bei) answers HTTP 403 from this container. Two ways in, both the owner's decision: run the collector on the
owner's computer through Remote Control with idx-bei's client, or take the weekly UMA lists from the news sites KOD already
reads (`sensors.py` reads emitennews; IDNFinancials publishes the weekly list). Use: a label stream for the IDX branch of the
Speculation Register (did the flagged stock's move reverse, when, and against its twins) and a one-shot history kill test
on the IDX panel outside the sealed 2024-01-02..2025-02-21 window. IDX's terms restrict commercial use; KOD's use is
paper-only research, the same footing as the price mirror it already uses.

## 7. Track E (grading tools) and what was checked from this container

`idxsig/multiple_testing.py` has Holm, Benjamini-Hochberg and the hurdle-z helpers but no bootstrap reality check. The
pasted-idea grader (offered earlier, still waiting on the owner) needs one: White's reality check or Hansen's SPA over the
rules an idea implies. `purgedcv` and `arch` are the references, but both pull scikit-learn or scipy and statsmodels into a
package that today needs only pandas, numpy, bs4, lxml and exchange_calendars. Recommendation: implement SPA with a
stationary bootstrap in numpy inside `multiple_testing.py` (about 150 lines, tested against `arch` once in a scratch run),
and keep the dependency set as it is. Only if the owner wants the grader.

Checks made today, so the plan rests on what was seen rather than remembered: the two CSVs were downloaded and counted
(section 1); the Binance archive's symbol list was paged in full (3,738); six removed pairs' 1-minute monthly files returned
HTTP 200; `api.binance.com` is not reachable from here (KOD's `sources/binance.py` uses `data-api.binance.vision`, which is);
idx.co.id returned 403 to two announcement queries; the GitHub API (`api.github.com`) is not reachable from here, raw files
and repository pages are. The private `STAR` repository holds a one-line README; `Moonshot-Scanner` was reviewed earlier.

## 8. Order, and the decisions needed

Order (one branch at a time; v2.4 runs nightly throughout): **A0-A2** (pin, feasibility, freeze) and **B** (tests only, no
research) in the same week; **A3** (one run, report, counted) the week after; **A4** decided from the result; **C** at
v2.4's first claim look; **D** and **E** when the owner says so.

Decisions for the owner, yes or no each:
1. Open `CRYPTO_PUMP_HISTORY_v1` as the one new research branch (history only; no live change until A4).
2. Commit the MIT list; pin the two unlicensed lists by URL and hash and fetch them at build time (not redistributed).
3. Add `edgartools` (and optionally `edgar-crawler`) as development-only dependencies for the cross-check tests.
4. Telegram access: not now; revisit after A3 with the result in hand.
5. UMA collection from the owner's machine or from news sites: not now; revisit.
6. The idea grader in numpy, no new dependencies: only if wanted.

Standing rules this plan keeps: paper only; no orders; no purchases, paid services or new subscriptions without approval; no
new recurring jobs without approval; research files append-only (a correction is a new file); sealed holdouts (IDX
2024-01-02..2025-02-21, US and crypto 2024 on) stay closed; no model identifiers in repository artifacts; the declared SEC
contact only inline on a command.

## 9. Sources (read 2026-10-29)

- Sapienza list and paper: https://github.com/SystemsLab-Sapienza/pump-and-dump-dataset ; La Morgia, Mei, Sassi, Stefa,
  *Pump and Dumps in the Bitcoin Era*, ICCCN 2020, https://arxiv.org/pdf/2005.06610 ; *The Doge of Wall Street*, ACM TOIT
  2023, https://arxiv.org/html/2105.00733v2
- ArdiaD list: https://github.com/ArdiaD/PumpDump ; Ardia & Bluteau, *Twitter and cryptocurrency pump-and-dumps*, IRFA 95
  (2024), https://doi.org/10.1016/j.irfa.2024.103479
- Hu et al., *Sequence-Based Target Coin Prediction for Cryptocurrency Pump-and-Dump*, SIGMOD 2023:
  https://github.com/Bayi-Hu/Pump-and-Dump-Detection-on-Cryptocurrency ; https://arxiv.org/pdf/2204.12929
- Xu & Livshits, *The Anatomy of a Cryptocurrency Pump-and-Dump Scheme*, USENIX Security 2019: https://arxiv.org/pdf/1811.10109 ;
  https://github.com/xujiahuayz/pumpdump
- Bolz et al., *Machine Learning-Based Detection of Pump-and-Dump Schemes in Real-Time* (2024): https://arxiv.org/html/2412.18848v1
- Binance public data: https://github.com/binance/binance-public-data ; listing endpoint
  https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?delimiter=/&prefix=data/spot/monthly/klines/
- edgartools: https://github.com/dgunning/edgartools ; edgar-crawler: https://github.com/nlpaueb/edgar-crawler
- pycatch22: https://github.com/DynamicsAndNeuralSystems/pycatch22 ; Lubba et al., *catch22: CAnonical Time-series
  CHaracteristics*, Data Mining and Knowledge Discovery 33 (2019)
- idx-bei: https://github.com/nichsedge/idx-bei (endpoint spec `docs/API_VERIFICATION_SPEC.md`); UMA weekly lists in the
  press, e.g. https://www.idnfinancials.com/news/64510
- purgedcv: https://github.com/eslazarev/purged-cross-validation ; arch multiple-comparison docs:
  https://arch.readthedocs.io/en/stable/multiple-comparison/multiple-comparison_examples.html
- IDX price mirror already in use: https://github.com/wildangunawan/Dataset-Saham-IDX
