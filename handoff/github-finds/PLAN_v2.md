# GitHub finds, integration plan v2: the broad pass, measured, and the ranking it changed

Written 2026-10-29 by the cloud session (`session_01SrR7rsdNDD1Fqye2K6MDSw`) after the owner asked: *"Im hoping you looked
around, not just strictly idx and crypto. Did you look around and concluded that that's the best thing to integrate?"*

**Honest answer to that question: no.** The first two passes (`PLAN_v1.md`) started from "pump-and-dump" and went deep on
crypto pump labels; the rest was sampled, not swept. This pass covered the categories v1 skipped, and where a source looked
useful it was *measured on the machine's own events* before being ranked. The measurements read no outcome column: they count
how often a candidate input would be non-zero, which is what decides whether it can move a forecast at all. v1 stays on file
as written; this document supersedes its ranking (section 3).

## 1. What was swept, and what each category returned

| Category (not covered in v1) | Best repository or source found | Checked from this container | Verdict |
|---|---|---|---|
| Retail attention, Reddit | [Watchful1/PushshiftDumps](https://github.com/Watchful1/PushshiftDumps) (MIT, 508 stars, dump-processing scripts); [arthurheitmann/arctic_shift](https://github.com/arthurheitmann/arctic_shift) (Reddit archive with a keyless API, dumps as zst) | API answers; a day of r/wallstreetbets lists in about 1 s per 100 posts; the newest archived post was **7 minutes old** (usable live); title search is slow (about 1 per minute) | **Measured; see section 2. Rank 1 if coverage holds** |
| Retail attention, Wikipedia | Wikimedia pageviews REST API (no key) | Works (GameStop daily views 2,063 on 15 Jan 2021 to 174,157 on 28 Jan) | **Out for the US spike question**: 3 of 40 sampled spike tickers (8%) have an English Wikipedia article |
| Retail attention, news | [kepler471/gdelt-doc-api](https://github.com/kepler471/gdelt-doc-api) (GDELT DOC API client) | not run | Out for now: the DOC API is a rolling 3-month window; full history means raw GDELT files at large volume |
| Market structure, settlement | SEC fails-to-deliver files (no repo; SEC page read) | The page: all securities with a fails balance since Sept 2008, half-month files, published **2 to 6 weeks after** the period | Slow input only (history plus a lagged live value); coverage unmeasured (download needs the SEC contact); folded into rank 1 as an optional sub-block |
| Market structure, Reg SHO threshold list | Nasdaq Trader daily files `nasdaqthYYYYMMDD.txt` (no repo) | Archive by date works (2021, 2023 checked) | **Out**: 1 of 80 sampled spike events was on the Nasdaq list on its spike day |
| Market structure, halts | Nasdaq Trader halts feed | the by-date feed returned no items for a 2021 date; no free history found | Out (a known limitation stays: no halt data) |
| Abstention with a guaranteed error rate | [aangelopoulos/ltt](https://github.com/aangelopoulos/ltt) (Learn then Test, MIT, 74 stars, paper code); conformal risk control; adaptive conformal inference (Gibbs and Candès 2021, drift) | KOD has no conformal or risk-control code (searched) | **Rank 2**: built for image and language models, fits the owner's goal exactly (section 3) |
| Where pumps live now (on-chain) | [DeFiLabX/SolRPDS](https://github.com/DeFiLabX/SolRPDS) (Solana rug pulls, CC BY 4.0, 2021 to Nov 2024); SystemsLab-Sapienza Ethereum/BSC token set | page read | Deferred: mostly 2024 (the sealed crypto period), and KOD has no on-chain data |
| Labelled stock pumps (US, India) | none released (SEC litigation releases are narratives; SEBI's 82-stock SME case is news only; stock-spam studies hand-collected, unreleased) | searched | Nothing to integrate |
| Crypto pump labels | (v1) Sapienza, ArdiaD, Bayi-Hu lists; KAUST PumpSense 2026 (2,246 announcements, no release found) | v1 measured: 1,271 Binance symbol-dates, archive serves every pair | **Rank 3** (was rank 1) |
| Indonesian text models | IndoBERT / IndoNLU (no finance-specific model released openly) | searched | Out: KOD's Bahasa phrase parser works; a large pretrained model can also carry look-ahead (it read the future of historical events) |
| Time-series foundation models | Chronos, TimesFM, Moirai | literature read | Out: the broadest study (94 countries, 2025) finds off-the-shelf models perform poorly on returns |
| LLM trading agents | TradingAgents and similar | not adopted | Out: an LLM has read the outcome of any historical event in its training data, so it cannot be backtested honestly |
| Survivor-free US prices | none free (EODHD, Norgate, MarketParquet are paid) | v1 | Owner's call |
| Reliability and grading | (v1) edgartools, edgar-crawler, arch, purgedcv, catch22 | v1 | Unchanged, ranks 4 to 6 |

## 2. The measurement that decides rank 1

Sample: events of LEARNER v2.4's warm start (`warmstart_v4/events_us.csv.gz`, 6,225 US +30% spikes 2020-2023) drawn with
seed 20261029. For each: does any r/wallstreetbets post from five days before the spike through the spike day carry the
ticker as a whole word in its title? Title search runs at about one query a minute, so the check was stopped once the
answer was clear: 23 events, and the Reg SHO check on 80.

**Result: 10 of 23 spike events (43%) had at least one such post** (2020: 3 of 10; 2021: 5 of 8; 2022: 2 of 4; 2023: 0 of
1). Counts among the hits: AMC 87, HYLN 59, TOPS 33, NVAX 7, XTNT 6, FTFT 5, BNGO 5, CBAT 4, VALN 2, TOMZ 1. A 95% interval
on 23 draws is roughly 25% to 63%; even its lower end is enough for a block to move a forecast. By contrast: Reg SHO
threshold list 1 of 80 (1%), English Wikipedia article 3 of 40 tickers (8%).

Coverage is an upper bound and a lower bound at once: a ticker that is also an English word can match by accident (the
study's rule handles that), and only titles were searched (comments are not counted).

## 3. Revised ranking

**Rank 1 (new data for the live question): an ATTENTION block for LEARNER v2.4's own question.** Why it beats the pump
labels: it feeds the one question the machine is already forecasting live every night (will a US stock that just closed +30%
close 10% lower tomorrow, on its own), so a gain compounds into the live record instead of opening a second line. The
mechanism is documented: attention-grabbing stocks are bought by individuals and the price pressure reverses (Barber and
Odean 2008; Da, Engelberg and Gao 2011, where higher search attention predicts higher prices for two weeks and a reversal
later), and r/wallstreetbets' predictive content disappeared after GameStop as posts shifted to price-pressure plays (Bradley,
Hanousek, Jame and Xiao, RFS 2024). A spike that the crowd is piling into should be given back more often than one driven
by a filing.

- **Study:** `research/ATTENTION_HISTORY_v1`, the TA_HISTORY_v1 procedure exactly: the same 6,225 events, the same two
  out-of-time folds (score 2022, score 2023), paired AUC gain over v2.4's 33 features, cluster bootstrap over weeks, Holm,
  Brier beside it, frozen before any feature is computed, one run, counted.
- **Block ATTN (four features, frozen names):** WSB posts naming the ticker in the five days before the spike (log count);
  on the spike day up to the US close; the ratio of the two; and a has-mention flag. Whole-word ticker match; tickers that
  are common English words count only with a `$` prefix (word list frozen in the protocol).
- **Optional sub-block SETTLE**, only if its feasibility count shows coverage of at least 20% of events: fails-to-deliver
  from the latest half-month file *published* before the spike (publication date, not settlement date, is the cut-off), as
  a share of shares outstanding.
- **Build cost:** the archive's day listing (about 1 s per 100 posts) over 2020-2023, about 20,000 requests at a polite rate:
  six to eight hours in the background, cached under `RAW/reddit/` with a manifest and sha256. No account, no key.
- **Live use, only if it ADDS, and only at v2.4's first claim look:** a v2.5 that reads the same archive at the nightly US
  run. That is a new external source in a routine (free, keyless, third-party, no uptime guarantee): the owner's decision.
  If the archive is down, the feature is recorded missing, as FINRA is today.

**Rank 2 (new method, every market): certified calls with Learn then Test.** The pre-catalyst program's own conclusion is
that a high win rate comes from *which events the machine agrees to speak about*, not from a better detector
(`handoff/precatalyst-program/PROGRAM_v1.md`). Learn then Test turns that into a guarantee: on resolved outcomes, it picks the
calling threshold so that, with 95% confidence, the share of wrong calls among the calls made is at most a stated level (it
tests each candidate threshold with a binomial bound and keeps the ones that pass, in a fixed order, so the guarantee holds
however many thresholds are tried). It needs no new data and no dependency (about 80 lines of numpy in a new
`idxsig/risk_control.py`).

- **History check first:** `research/CALL_CERT_v1`: certify a dump-call threshold on the 2022 out-of-time predictions,
  report the losing rate it actually achieves on 2023 and how often it speaks. One run, counted.
- **Live, as a shadow report:** `paper/CALL_CERT.md`, read from LEARNER v2.4's ledger, recalibrated as outcomes resolve; v2.4's
  frozen calls are not changed.
- **Caveat stated in advance:** the guarantee assumes the future resembles the calibration period; markets drift, so the
  report tracks the realised losing rate beside the certified bound and widens it when they part (adaptive conformal
  inference).

**Rank 3: the crypto pump history study** (`CRYPTO_PUMP_HISTORY_v1`, exactly as in v1 section 3). Still the best labelled
set of scheduled catalysts with unknown targets, and it tests a ranking skill that transfers to index reviews. It drops
because it opens a new question on a venue the pumps have left, while ranks 1 and 2 strengthen the question already live.

**Ranks 4 to 6, unchanged from v1:** edgartools as a second SEC reader in tests; IDX UMA notices as exchange-made labels
(blocked from this container, HTTP 403); the reality-check grader in numpy. **catch22 is withdrawn** as the next feature
block: ATTN has a mechanism, catch22 is generic, and one block is tested at a time.

## 4. Order and decisions

Order, one research branch at a time, v2.4 untouched throughout: rank 2's history check (`CALL_CERT_v1`, no new data, about a
session) can run first because it only reuses the warm-start events; rank 1 (`ATTENTION_HISTORY_v1`: freeze, six-to-eight-hour
background build, one run) next; rank 3 after.

Decisions for the owner, yes or no each:
1. Run `CALL_CERT_v1` (history only, no new data).
2. Freeze and run `ATTENTION_HISTORY_v1`, reading the Reddit archive for 2020-2023 (history only, no account).
3. Whether a v2.5 may later read the Reddit archive at the nightly run (decided only if the block ADDS).
4. The crypto pump study after these (v1 decision 1, moved down).

Standing rules kept: paper only; no orders; no purchases or subscriptions; no new recurring job; research files append-only;
sealed holdouts closed (the samples above are 2020-2023); the SEC contact only inline on a command; X and Unusual Whales are
not touched.

## 5. Sources (read 2026-10-29)

- Reddit archive: https://github.com/Watchful1/PushshiftDumps ; https://github.com/arthurheitmann/arctic_shift ; API
  `https://arctic-shift.photon-reddit.com/api/posts/search`
- Bradley, Hanousek, Jame, Xiao, *Place Your Bets? The Value of Investment Research on Reddit's Wallstreetbets*, Review of
  Financial Studies (2024); Barber and Odean, *All That Glitters*, RFS (2008); Da, Engelberg and Gao, *In Search of
  Attention*, Journal of Finance (2011)
- Wikimedia pageviews API: `https://wikimedia.org/api/rest_v1/metrics/pageviews/`
- GDELT DOC client: https://github.com/kepler471/gdelt-doc-api
- SEC fails-to-deliver: https://www.sec.gov/data-research/sec-markets-data/fails-deliver-data
- Nasdaq Reg SHO threshold files: https://www.nasdaqtrader.com/Trader.aspx?id=RegSHOThreshold
- Learn then Test: https://github.com/aangelopoulos/ltt ; Angelopoulos, Bates, Candès, Jordan, Lei, arXiv 2110.01052;
  Angelopoulos and Bates, *A Gentle Introduction to Conformal Prediction*, arXiv 2107.07511; Gibbs and Candès, *Adaptive
  Conformal Inference Under Distribution Shift*, NeurIPS 2021, arXiv 2106.00170
- SolRPDS: https://github.com/DeFiLabX/SolRPDS (Alhaidari, Kalal, Palanisamy, Sural, CODASPY 2025)
- PumpSense (Mahrous, Di Pietro, KAUST, 2026): https://chatpaper.com/paper/278982
- Time-series foundation models in finance: Rahimikia, Ni, Wang (2025), arXiv 2511.18578
- Indonesian NLP: Maharani et al. (2023), arXiv 2310.09736
- v1 sources: `PLAN_v1.md` section 9
