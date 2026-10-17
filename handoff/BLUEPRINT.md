# KOD-Machine Blueprint

As of 2026-10-17. This is the repository copy of the Claude Doc "KOD-Machine Blueprint"
(https://claude.ai/code/artifact/818e9141-adcd-4679-8ea3-3f5b8f96706a), written for the owner and for LLM
agents. The doc has two drawings; here they are written out as text. Every figure was checked against its
source in three rounds of independent review. Facts that come from outside git (your Mac, your account, GitHub,
eToro) say so.

## Bottom line

Between 2026-10-07 and 2026-10-17 the machine ran 13 tests of ways to spot big upward moves early and trade them. The detectors work, but too late: flagged names went on to jump 4.6 to 9.3 times more often than similar names, yet the flag fires inside the jump, not before it, and no way of trading it passed its pre-set tests (0 strategies approved; 0 paper buys in 128 live decisions). What works is the testing machine; what is missing is a signal that arrives before the move, in a market eToro can execute.

## How the machine works

Drawing in the doc: "Live scans may buy only after a plan passes the backtest. None has." Data flows down.

1. **Data in.** Every download is logged in a hashed manifest; raw files stay out of git.
   - IDX stocks: daily exchange data from a mirror, to 2025-02-21; then Yahoo.
   - US stocks: Nasdaq Trader list, Yahoo daily bars, SEC EDGAR filings.
   - Crypto: Binance spot bars, daily and hourly, and perpetual futures.
   - eToro: instrument list, fetched 2026-10-16: 18,236 instruments.
2. **Panels: one hashed table per market.** Each run reports its sessions by data-quality tier. US prices cover today's listings only. Corporate actions: an IDX registry checked against share counts; US splits checked against SEC filings. Repaired in: E2 repairs v1 to v3 (US split units and cost tiers).
3. **Detectors: frozen rules, rebuilt day by day so none can peek.** F1_ARA for IDX: the close is locked at the upper daily price limit. G2_RET30 for US stocks and crypto: the day closed up 30% or more. Signals tried: E1, E2, E5, E6, E7, E8, E9, US breakout.
4. The detectors feed two loops.
   - **Research loop (signals in history).** Backtest harness: a plan says when to buy and when to sell; fills are capped at 10% of volume; costs are assumed per market, not measured (the harness default and the original E2 run charge US price tiers on split-adjusted prices; most E2 repairs, US breakout, E5 and E9 use as-traded prices); each trade is compared with similar names on the same day; pass gates and statistics are fixed in advance. Plans tried: E3, E4, IDX capacity, EXIT-ATR. Output goes to the append-only records: the results log holds 15 runs (placebos, E1, E2); later tests keep their outputs in their own folder; protocols are frozen with file hashes; a commit hook (once switched on) and CI refuse edits.
   - **Live loop (today's signals).** Daily paper scans (IDX 10:17 and US 22:47 UTC on weekdays, crypto 00:23 UTC daily) lead to a decision: buy only with a plan that passed the research loop. No plan has passed, so none may buy: 128 decisions to date, 0 buys. Decisions go into the paper ledger: 188 records in one hash chain, two RFC 3161 timestamps on each, each decision scored after five sessions. 34 have been scored so far: 29 correct rejections, 5 missed gains.
5. **Not wired into the scanner.** The KOD evidence lab (frozen, timestamped case cards; 4 cases, 0 of the 30 prospective cases it needs). The G3 pilot on your Mac (20 stocks, descriptive only; first results due 2026-11-10). The Moonshot Project tasks (a separate system on your account, with its own ledger).

Data flows down into two loops that share the same frozen detectors. The research loop replays history and compares every trade with similar names bought the same day; the live loop scans each day and may buy only once a plan has passed the research loop, which none has.

## The goal and the rules

The goal is an early-warning system for large upward moves that supports profitable trades. It is judged on win rate, net return, losses and capital exposure together (your words, 2026-10-16). You trade through eToro, so a result only matters if eToro can execute it.

| Market | On eToro? | eToro's cost | What it means for us |
| --- | --- | --- | --- |
| Indonesian stocks (IDX) | No: 0 Indonesian (.JK) symbols among eToro's 18,236 instruments | n/a | The IDX scanner cannot be traded there |
| US stocks (Nasdaq, NYSE) | Yes: 6,152 distinct stock symbols | A $1 or $2 commission may apply on opening and on closing, plus the spread. Short sales are CFDs with overnight fees | The one market where the machine's stock signals can be executed |
| Other stocks | Yes: 4,809 on 27 other exchanges, including 109 in Copenhagen (Zealand Pharma among them) | Not checked | The machine has no data pipeline for them |
| Crypto | 212 coins quoted in dollars, 83 crosses (such as BTC/EUR or ETH/BTC) and 49 dated crypto futures (bitcoin, ether, XRP and SOL); the list also holds 366 internal crypto entries | 1% to buy and 1% to sell (Bronze to Gold tiers) | The tests assumed 0.2% a side (EXIT-ATR 0.3%; E8 0.4% to 0.6% a round trip). At eToro's 2% a round trip, average net returns would be about 1.4 to 1.6 points lower; gaps against matched coins and excess before costs would not change. Only 154 of the 506 Binance coins trading on 2026-10-08 share a symbol with an eToro coin |

The instrument list is eToro's public list, fetched 2026-10-16 (`idx-signals/data/manifests/etoro_instruments-20261016T190421Z.jsonl`). Fees are from [eToro's fee page](https://www.etoro.com/trading/fees/), read 2026-10-17.

**The rules every test followed**

| Rule | What it means | Where it is written |
| --- | --- | --- |
| No real money | No orders, no funds moved. Every live decision is paper only. Production ASTRA is left unchanged | Your instructions; `idx-signals/paper/README.md` |
| Freeze before results | The hypothesis, trading rules, comparison and pass criteria are written and hashed before any return is computed | Each experiment's `PROTOCOL.md` and `protocol.json` |
| One recorded run | Each test runs once on its frozen protocol, and a failure is reported as it is, never re-tuned until it looks profitable. Redesigns after a failure or a first look are declared as such (E4 v2, E5 v1.1, E7's Mac amendment). The 2023 US test ran 9 times on this branch (10 counting PR #3's fill-model check) as data repairs landed, with the strategy unchanged | Your instructions; each protocol; `idx-signals/results/RUNS.jsonl` |
| Compare with matched controls | Every trade is set against similar names bought the same day under the same plan | `idx-signals/idxsig/controls.py` |
| Costs always included | IDX: 0.15% to buy, 0.25% to sell. US: per side 1.5% under $1, 0.5% for $1-5, 0.15% for $5-20, 0.05% above $20, plus the SEC fee on sales. Crypto: 0.1% fee plus 0.1% slippage per side, unless a test says otherwise | `idx-signals/idxsig/profiles.py` |
| No peeking | Each day's signal uses data up to that close only. The harness rebuilds every signal session by session and refuses a rule whose output changes when future data is added | `idx-signals/idxsig/rules/__init__.py` |
| Sealed holdouts | IDX 2024-01-02 to 2025-02-21. US and crypto 2024-01-01 to 2026-12-31. Each is used once, for a detector already frozen and validated; no historical row dated 2024-01-01 or later is loaded before then. US and crypto 2023 was already examined in E2 | `idx-signals/idxsig/backtest.py`; `idx-signals/research/E2/protocol.json` |
| Append-only records | Committed research files are never edited. A correction is a new, dated file. The check runs on every commit once the hook is switched on (once per clone) and on every push in CI | `tools/check_append_only.py`; `.githooks/pre-commit` |
| History is not a forecast | A historical result is never presented as future performance. No trade or probability is invented to fill a quota | Your instructions |

## Every experiment so far

Thirteen tests ran to a verdict. Each was frozen before its first result, and none produced a strategy that makes money after costs. Three later steps used changes made after a first look, all disclosed: E4 v2 (designed on v1's discovery results), E5's corrected version (v1.1) and the E7 run on your Mac. Newest first; dates are UTC.

| Date | Test (market) | What it asked | What happened | Verdict |
| --- | --- | --- | --- | --- |
| 2026-10-16 | E9 catalyst split (US) | Do +30% days backed by an SEC filing published before the next open keep rising? | Documented moves -1.07% a trade (644 trades, win rate 41.5%), negative in every year; undocumented -3.06% (1,337 trades, win rate 33.0%). Gap +1.99 points (-1.83 to +6.00). A filing did separate the typical trade: win rate +8.5 points (+3.3 to +13.5), clipped mean +3.39 points (+0.81 to +6.01). At $5,000 a trade on $100,000, the documented class lost $34,330 (-34%), with a -72% worst drawdown | NEGATIVE |
| 2026-10-16 | EXIT-ATR v1 (crypto) | Does a trailing stop rescue the +30% entry? | Trailing exit -1.11% a trade vs -0.29% for the original exit: a change of -0.82 points (-2.92 to +1.19). Win rate 35.6% (33.2% for the original exit); worst drawdown 36.2 trade sizes (55.8). Under either exit the entry trails matched coins by about 3 points | NEGATIVE |
| 2026-10-16 | E8 peer spillover (crypto) | Do coins tied to a coin that jumps alone follow it? | 72-hour excess before costs +0.44% (-0.28 to +1.16). As a trade: +0.09% net, win rate 41.1%, worst drawdown -38.9% at 5% of capital a trade | FAIL |
| 2026-10-15 to 16 | E7 funding squeeze (crypto perpetuals to spot) | Do negative funding and rising open interest predict the spot coin? | Cloud data check GO (845 events, draft protocol). Finished on your Mac, not published, under a v1.1 protocol that is not in the repository: after a first DATA_FAILURE and an amendment made after the outcome files existed, disclosed as such, 534 events, 24-hour excess before costs -0.35 points (-0.95 to +0.33). The trading stage was not run | FAIL (Mac) |
| 2026-10-15 | E6 pressure response (crypto) | Does buy/sell pressure absorption predict five-day returns? | Primary setup: excess before costs +0.37% (-1.01 to +1.93), p 0.32. Second setup: 136 flags, under the 200 needed | NULL |
| 2026-10-14 | E5 ceiling (IDX, US, crypto) | Can any daily-bar ranking tell up-moves from down-moves? | IDX excess before costs +1.3%, p 0.074 against 0.025 needed; crypto p 0.42; US below its controls. The one early pass, in a side arm on IDX, came from a code defect found in review | NULL |
| 2026-10-13 | E4 short side (crypto) | Can shorting the +30% movers pay? | v1: 0 of 144 detector-plan pairs admissible (36 plans on each of 4 detectors). v2, designed on v1's discovery results and run on the same years, passed discovery (+5.82% a trade), then failed 2023: it won 67.6% of 34 trades yet averaged -1.50% vs -0.22% for matched shorts, because 3 trades (8.8%) were liquidated | FAIL |
| 2026-10-13 | E3 execution plans (IDX) | Does any entry and exit plan make the limit-up detectors pay? | 0 of 108 detector-plan pairs admissible (36 plans on each of 3 limit-up detectors). 18 pairs averaged above zero over 2021-22, but all 108 lost money in 2022 | NONE ADMITTED |
| 2026-10-09 | US breakout v1 (US) | Does buying a 60-session closing-high breakout pay, under the 5% stop rule? | 11,833 trades in 2023: -0.180% a trade vs -0.138% for matched entries. Difference -0.042 points (-0.115 to +0.035) | NO EDGE |
| 2026-10-09 | IDX causal capacity (IDX) | Did the fill rule hide an edge? | With fills limited to what was known at the decision: -3.64% vs -0.44% for matched names (before: -4.06% vs -0.53%). Most IDX paper decisions cite this rerun | NO HIDDEN EDGE |
| 2026-10-08 | Zealand pilot (Denmark, KOD lab) | Was Zealand Pharma's +37.9% day visible and tradable in advance? | The news came out before the market opened, and 114% of the day's move happened before the first possible trade. Entries after the news lost 16% to 19% within five sessions, depending on the entry | NO ACTIONABLE EDGE |
| 2026-10-08 | E2 and repairs v1-v3 (US, crypto) | Which detector flags +30% moves, and can it be traded? | Detection 5.4x (US) and 4.6x (crypto) better than matched names. Trading in 2023: crypto -1.90% vs +1.42%. US -3.65% vs -0.60% in the original run, later marked superseded (wrong cost tiers; re-costed -4.47%); the repaired runs range from -5.27% vs -1.32% to -0.97% vs -0.75% (p 0.62), all below their controls. The paper policy cites the last | DETECTION YES, TRADING NO |
| 2026-10-08 | E1 (IDX) | Which signals come before +30% moves on the Indonesian exchange? | Close locked at the upper limit (F1_ARA): 18.3% of flags went on to +30% vs 1.96% for matched names. Trading it: -4.06% vs -0.53%. 339 of 1,042 entries were still locked at the limit | DETECTION YES, TRADING NO |

Not run to a verdict: E3 US retention (draft PR #5, a protocol only) and G3 (a descriptive 20-stock pilot on your Mac; first results mature 2026-11-10). How to read the numbers: unless marked, a percentage is the average net return per trade after costs, "vs" sets it against matched names, and a range in brackets is a 95% interval. "Excess before costs" is the return over matched names before costs. Win rates, hit rates and liquidation rates are shares of trades or flags. A range written "from ... to" across versions or entries is not an interval.

## What went right

The machine itself works: it measures honestly, catches its own errors and has never risked money.

| What worked | Evidence |
| --- | --- |
| Detection is real | In the 2023 validation, flagged names reached +30% far more often than matched names: IDX 18.3% vs 1.96%, US 15.4% vs 2.8%, crypto 18.5% vs 4.0% |
| The rules held | Each protocol was frozen before its own runs, and every failure was recorded as it came out, never re-tuned. Redesigns after a first look (E4 v2, E5 v1.1, E7's Mac run) were declared as such, and none passed validation. Only E7's Mac result is unpublished; the four unpushed branches are on GitHub as bundle files in handoff/ |
| Results reproduce | The original E2 US run was rebuilt byte for byte from archived inputs. E5 reproduced three earlier runs exactly before testing anything new |
| The harness cannot peek | A coin-flip placebo came out indistinguishable from random in all three runs. Every recorded run passed its lookahead check: session by session from the second run on, at 3 cut-off dates for the first |
| Hidden data defects were caught | Yahoo's split rescaling, future-informed row deletion, after-the-fact fill sizes, crypto redenominations (COCOS 1,000:1), the SEC timestamp defect and a bankruptcy splice were each found and disclosed |
| Outside review found real errors | Ace found 5 defects that 233 passing tests had missed. Codex withdrew 1,074 of 1,313 split approvals and found the defect behind E5's one pass. Hermes found 3 data-path defects |
| Records are tamper-evident | 188 ledger records, each with two RFC 3161 timestamps; the hash chain and the append-only check are intact over the whole history. Every GitHub Actions run since 2026-10-08 has passed; the only 2 failures, of 166 runs to 2026-10-17, were on 2026-10-08 |
| No money at risk | 0 real orders. 128 paper decisions, 0 buys, because no plan passed. Of the 34 decisions scored so far, 29 were correct rejections and 5 missed gains (the largest paper trades +65.4% and +53.7%); too few to judge, and descriptive only |

## What went wrong

The core failure is timing: the signals fire after most of the move, and buying after a jump lost to similar names in every market tested.

**Strategy**

- The signals are late. Only 0.9% of US moves and 0.1% of crypto moves of +30% were flagged before their peak (IDX: 9.8%). On the day a move began, the flag caught 0 of 4,100 US moves, 1 of 730 crypto moves and 4 of 569 IDX moves. After a US flag, the median stock fell 10.3% over the next five sessions.
- Buying after the jump lost to similar names in every market: IDX -4.06% vs -0.53%, crypto -1.90% vs +1.42%, and US in the original run and in every repair. In E9, all 2,251 US trades averaged -2.19%, 2.47 points below their controls.
- Nothing bolted on afterwards repaired it: 0 of 108 IDX detector-plan pairs, a trailing stop on crypto (-0.82 points), shorting crypto (failed validation) and an SEC-filing filter in the US (still -1.07%).
- On IDX the best moves cannot be bought: 339 of 1,042 entries were locked at the upper limit, and the fills that do happen are mostly fading moves.
- Gains did not repeat from year to year. E3's positive plans came from 2021, and all 108 pairs lost in 2022. The trailing stop beat the original exit only in 2022 (+4.05 points a trade) and cost 3.39 points in 2021 by cutting winners. E4's shorts made money in 2022 and lost in 2021. E8 was positive in 2020 and 2021, then -0.63% in 2022. Only E6 was positive every year, too weakly to tell from zero.
- A high win rate did not mean profit: E4 v2 won 67.6% of its 2023 trades and still lost 1.50% a trade.
- Fat tails swamp the averages. A few meme-era trades (HKD +1,025% and BNGO +844% in five sessions) make intervals so wide that differences of a few points cannot be resolved.

**Data**

- The US universe is today's listings only. Companies that died are missing, and no free point-in-time source was found.
- Yahoo rescales old prices after splits. 60% of 2023 US flags were in names that later reverse-split, and 582 of 1,099 trades sat in the wrong cost tier. The fix that excluded those names turned out to remove the worst trades (-9.17% vs -1.75%), so it flattered the result.
- Binance prices ignore redenominations: one COCOS trade would show a fake +125,489%.
- SEC's bulk JSON stamps filing times in two different conventions, so E9's first data check failed.
- Costs are assumed price tiers, not measured spreads, and daily bars cannot prove an opening fill.
- IDX data: the exchange site blocks downloads, and the free mirror stops at 2025-02-21.

**Process**

- The tests were not built around your broker. That it is eToro surfaced on 2026-10-16, after E1 to E8 and the EXIT-ATR run. Three tests were wholly on IDX, which eToro does not list (E1, E3, IDX capacity), plus E5's IDX arm. The crypto tests used Binance's coins at 0.2% to 0.3% a side; eToro charges 1% a side, and only 154 of the 506 Binance coins trading on 2026-10-08 share a symbol with an eToro coin.
- 2023 was reused as the validation year. The US and crypto holdout is guarded in code only on unmerged branches, and some 2024+ prices were seen in a data-quality note.
- Your usage budget cut independent reviews. E5's two defects were found only after the result was published.
- Work is scattered: four branches are not pushed: their commits exist in this container and, as bundle files, in handoff/ on GitHub, four pull requests are open, and some work exists only on your Mac. The pinned data inputs (467 MB of panels, 6.0 GB of raw downloads) are not in git and exist only in this container, apart from the E2 US inputs archived in Git LFS. The READMEs are stale (they say 222 tests; 243 run).
- The harness was built for your own detector rule, which was never supplied (the USER_RULE slot is empty).
- The KOD evidence lab has 0 of the 30 prospective cases it needs. Its daily tape feed was never built because E5's pre-registered consequence says so: stop building tape-only detectors, and do not stand up the KOD tape feed. E6, E8 and EXIT-ATR, all tape-based, ran afterwards on your go.

## What is doable and what is not

Every idea tested so far failed after costs. Of the markets the machine has data for, the open ground eToro can trade is US stocks. Three untested US ideas there are not versions of the +30% entry: Form 4 insider buying, an earnings or guidance surprise, and 8-K filings that arrive before the price moves. A clean backtest of any of them needs prices for companies that have since delisted, which the repository does not have; forward paper testing does not.

Drawing in the doc: "Every tested idea failed; every open idea eToro can trade is in US stocks." Columns are markets with data here, from not tradable on eToro to tradable; rows are what the tests found.

| | IDX stocks (not on eToro) | Crypto (some coins, 1% a side) | US stocks (on eToro) |
| --- | --- | --- | --- |
| Tested: no edge after costs | Buy after limit-up (E1: -4.06% vs -0.53%); entry and exit plans (E3: 0 of 108 admitted); causal fill limits (capacity: no hidden edge) | Buy after a +30% day (E2: -1.90% vs +1.42%); trailing-stop exit (EXIT-ATR: -0.82 points); shorting the movers (E4: failed on 2023); other crypto signals (E6, E7, E8: no edge) | Buy after a +30% day (E2, its repairs, E9); 60-session breakout (11,833 trades, no edge) |
| Tested, across all three | Daily-bar ranking (E5): no edge in any of the three markets | | |
| Not yet tested | New IDX signals (eToro lists no IDX stocks) | No idea on record | **Form 4 insider buying (my pick; never tested)**; earnings surprise (untested; SEC route works); 8-K before the move (E9 built its SEC data); shorting the +30% movers (E4 ran crypto only); delayed +30% entry (E3 US retention, drafted) |
| Not yet tested, across all three | Regime filter on the +30% entries: proposed, never run | | |

Shorting the movers, the delayed entry and the regime filter all use the +30% detector; retiring the buy-side entry closes the last two. The crypto tests assumed 0.2% to 0.3% a side in costs; eToro charges 1% a side. Hermes's PUMP-LAB download on your Mac has not been analysed, and its market is not recorded here. eToro also lists 4,809 stocks on 27 other exchanges, for which the machine has no data.

| Approach | Can eToro execute it? | Status |
| --- | --- | --- |
| Buy the open after a US +30% day | Yes: 6,152 US stock symbols listed | Dead: lost in E2, in every repair and in E9 |
| US 60-session breakout | Yes | Dead: no edge in 11,833 trades |
| IDX limit-up detector plans | No: eToro lists no Indonesian stocks | Dead: 0 of 108 detector-plan pairs admitted |
| Crypto +30% entries and exits | Buying yes, at 1% a side, for the coins eToro lists | Dead: E2 and EXIT-ATR failed; you retired the entry on 2026-10-17 |
| Shorting the crypto movers | Not checked | Dead: E4 failed its 2023 validation |
| Crypto spillover, pressure and funding signals | Buying yes, at 1% a side, for the coins eToro lists | Dead: E8, E6 and E7 found no edge |
| Daily-bar ranking, all three markets | US yes; IDX no; crypto at 1% a side | Dead: E5 found no edge |
| Form 4 insider buying | Yes | Untested; my pick. The filings are free: per-filing XML on EDGAR, or the SEC's bulk insider-transaction data sets, full history with delisted issuers (E8's mechanism review). The price side is the limit: the US panel holds today's listings only, which biases exactly the small issuers that matter, so a backtest on current data can only be a survivor-biased discovery test, disclosed as E9's was. The documented effects are a few percent over months, a weaker fit to an early moonshot warning |
| Earnings or guidance surprise (PR #8, section 8) | Yes | Untested. PR #8's version needs release times and consensus estimates fixed before each release, a new data source that needs your yes. The ten-announcement check on your Mac found that company guidance revisions can be read from SEC filings with no consensus data; a full backtest is blocked by missing prices for delisted companies |
| 8-K filings before the price moves (Track B of the 2026-10-14 information proposal) | Yes | Untested: E9 tested only filings on +30% days, and built the SEC pipeline this would reuse |
| Shorting US +30% movers | As CFDs, with overnight fees | Untested: E4 ran crypto only, where squeeze losses sank it; E9's US data holds five-session moves of +1,025% and +844% |
| Delayed +30% entry (E3 US retention) | Yes | Untested: a protocol only (draft PR #5), a variant of the +30% entry, screened on 2020-07 to 2022-12, the years G2_RET30 was picked on (in-sample); it treats 2023 as spent |
| Regime filter on the +30% entries | In the US, yes | Untested: proposed on 2026-10-14 (4th of 6 ideas), never run; a variant of the +30% entry |
| Hermes's PUMP-LAB idea | Unknown | Untested: a data download on your Mac that you excluded from the EXIT-ATR work; nothing analysed, and its market is not recorded here |

## Open decisions and the next step

Thirteen calls are waiting on you. The first one closes the last open line of the current approach; the second protects the evidence.

| Decision | What it changes | My recommendation |
| --- | --- | --- |
| Retire "buy after a +30% day" for US stocks | Stops every further buy-side variant of the entry E9 tested, including the delayed entry (draft PR #5) and the regime filter. Shorting the movers stays open | Yes, as you did for crypto on 2026-10-17 |
| Archive the pinned data inputs | The panels (467 MB) and raw downloads (6.0 GB) behind most experiments are not in git and exist only in this container; only the E2 US inputs are in Git LFS, and E3's pinned panel is already gone here. Without them, exact reproduction and PR #8's outside re-run end with this container | Yes, to Git LFS as was done for E2 US, before anything is cleaned up |
| Merge PR #7 (E4 short side) | Brings the US and crypto holdout guard into the main code. Merging it first means merging the new base into PR #3 again (conflicts expected in execution.py and cli.py); PR #8 already contains its 11 commits | Yes, for the guard |
| PR #3 (US pipeline, execution contract v2.1, paper policy v5) | Needs Ace's re-review; switching the daily scans to it is a new paper policy | Leave the scans as they are until a plan passes |
| Draft PR #8 (E5) | Its listed blockers: a review of the last fixes (9bc361d) and a re-run of the stages by someone other than the builder; your decisions on PR #7, the earnings-data probe and E5's consequence; and the three panel files plus the IDX registry for reviewers | Review, then decide |
| E5's pre-registered consequence | It says: stop building tape-only detectors, and do not stand up the KOD tape feed. E6, E8 and EXIT-ATR, all tape-based, ran afterwards on your go | Confirm it, or record the exception |
| Draft PR #5 (E3 US retention) | A protocol that was never run, screened on in-sample years | Close it if you retire the +30% entry; otherwise park it |
| Push the four unpushed branches (E7 feasibility, E8, EXIT-ATR, US breakout) | Their commits survive here and, as bundle files, in handoff/ on GitHub | Push them, or keep the bundles |
| Use 2023 as a provisional screen | 2023 has been seen (E2's US runs, US breakout). Your 2026-10-16 instruction says it cannot be fresh confirmation, so a pass licenses paper scoring only (the E6 rule); confirmation needs fresh data: live paper decisions from now on count (the E5 and E9 protocols); only the E3 US retention draft waits for 2027-01-01 | Yes, as a screen only |
| Publish E7's Mac result | The FAIL exists only on your Mac. First check that its commit a61ba164 descends from the cloud head a17aaa7 | Yes |
| Hermes's EXIT-ATR run on your Mac | The same design as the cloud EXIT-ATR v1, which already ran once (NEGATIVE) | Stop it, or let it finish only as a labelled replication |
| G3 on your Mac | A frozen 20-stock detection pilot: a close above the previous 20 closes with volume at least twice the 20-session median, scored by a +30% close within 20 sessions. It has no trading plan, so a hit is not a trading profit. 40 of the first 60 observations are missing: two of the first three collections were missed while the laptop slept | Keep the Mac on power, online and open Tuesday to Saturday from 03:15 to 03:30 WIB through 2026-10-31, then from 04:15 to 04:30 WIB from 2026-11-03 to 2026-12-09 (New York leaves daylight saving time on 2026-11-01). Or retire G3 |
| Daily paper scans | IDX cannot be traded on eToro, and the +30% entries are retired or proposed for retirement, so the scans now only log detections | Keep crypto and US as descriptive logs; decide whether IDX continues |

**Next step:** close the +30% line, and archive the data inputs before anything else. Then either stop, or test one US signal that may come before the move, frozen in advance like the others. My pick is insider buying reported to the SEC on Form 4: the filings are free, including the SEC's bulk data sets with delisted issuers, and each is due within two business days of the trade (an SEC rule, not something tested here). The documented effects are a few percent over months, a weaker fit to an early moonshot warning. The limit is price data: the US panel holds only today's listings, so a backtest would be a survivor-biased discovery test, disclosed as E9's was; a clean test needs prices for delisted companies from a source you approve, or forward paper data. It has not been tested here. The other two ideas on record are an earnings or guidance surprise (PR #8, section 8), whose PR #8 version needs release times and consensus estimates the repository does not have (a guidance-revision version needs no consensus), and 8-K filings that arrive before the price moves, which would reuse E9's SEC pipeline. A ten-announcement earnings check on your Mac passed the SEC filing route but was NO-GO for a broad backtest with the current price inputs.

## Glossary

Every term this blueprint uses, in plain words. The exact rule is in the file named.

| Term | Plain meaning |
| --- | --- |
| Signal, detector | A fixed rule that flags a stock or coin at a day's close. It never changes after it is frozen. |
| G2_RET30 | The US and crypto detector chosen in E2: the day closed up 30% or more. |
| F1_ARA | The IDX detector chosen in E1: the close is locked at the upper daily price limit (ARA). |
| ARA / ARB | Indonesia's daily upper and lower price limits. A stock locked at ARA has no sellers, so it cannot be bought. |
| E30, E50, E100 | The highest close in the next five sessions is at least 30%, 50% or 100% above the signal day's close. |
| Precision | Of all flagged names, the share that went on to an E30 move. |
| Plan | How a signal becomes a trade: when to buy (for example the next open) and when to sell (for example the close five sessions later). |
| Net return | A trade's return after every modelled cost: on IDX the fees (0.15% to buy, 0.25% to sell); on US stocks a per-side cost by price tier plus the SEC fee; on crypto 0.1% fee plus 0.1% slippage a side, unless a test says otherwise (EXIT-ATR 0.3% a side; E8 0.2% to 0.3%). |
| Fill model | The rule for whether a paper trade could really have been filled. Model B allows at most 10% of the median daily volume known at the decision. |
| Matched controls | For each signal, random draws from other names on the same day that share its price, liquidity, size (IDX only), volatility, momentum, drawdown and listing-age buckets, traded with the same plan. Usually 200 draws, with repeats allowed; when fewer than 5 names match, the least important feature is dropped. US breakout used 10 draws per signal and the E1 and E2 event studies 5 per event. They answer: would a random similar name have done as well? |
| Excess | A trade's net return minus the average net return of its matched controls. Above zero means the signal added something. |
| Win rate | The share of trades with a net return above zero. |
| 95% interval | The range the true average plausibly lies in. If it includes zero, the result could be luck. |
| Week bootstrap | How most intervals are computed (E6 to E9, EXIT-ATR): whole calendar weeks are resampled, because trades in the same week move together. E5 resampled sessions and US breakout its signal sessions; the E1 to E4 p-values come from the 200 matched draws, so the lowest possible is 0.005. |
| Discovery, validation, holdout | Three separate periods: one to test, one to confirm, one sealed for a single final test. IDX holdout: 2024-01-02 to 2025-02-21. US and crypto holdout: 2024-01-01 to 2026-12-31. |
| Provisional | A pass on 2023 data that has already been seen. It licenses paper scoring only, never confirmation (the E6 rule). |
| Pre-registration, freeze | Writing down the hypothesis, rules, comparison and pass criteria, with file hashes, before any return is computed. Results cannot be tuned afterwards. |
| Feasibility check | A counts-only check, with no returns, that the data can support a test. It ends GO or NO-GO. |
| Amendment | A dated, committed change to a plan, with its reason. Normally made before any result is seen; one made after (E7's Mac run) is declared as such. |
| Gate, criterion | A pass condition stated in advance, such as C1 to C6 in E9. |
| Survivorship bias | A universe built from today's listings misses companies that later died, which flatters history. |
| Causal, prefix-first | Each day's signal is computed from data up to that day only, so a rule cannot peek at the future. |
| Split-adjusted vs as-traded | Data vendors rescale old prices after a split. Costs and capacity depend on the price that actually traded on the day. |
| Overlap skip | A new signal on a name already held is skipped. |
| Stress | The same trades recomputed with an extra cost per side, for example 0.5%. |
| Clipped (winsorized) mean | An average with the most extreme 1% at each end pulled in, so a few freak trades cannot dominate. |
| ATR trailing stop | An exit that follows the price up and sells after a fall of a set multiple of the average true range, the average daily high-to-low range (EXIT-ATR used 14 days). |
| Liquidation | A leveraged short closed by force after the price rose too far. E4 counted these. |
| Perpetual futures, funding, open interest | Crypto futures with no expiry date. Funding is the regular payment between buyers and sellers of them; open interest is the number of open contracts. E7 tested both. |
| CFD | Contract for difference: a position on a price without owning the asset. eToro uses it for short sales, with overnight fees. |
| Form 4 | The SEC filing an insider (an officer, a director or a 10% owner) makes after buying or selling the company's shares. |
| 8-K | The SEC filing a US company makes to report a material event. E9 classified filings like these by the time the SEC accepted them. |
| WIB | Western Indonesia Time, UTC+7. |
| RFC 3161 timestamp | A signed token from an outside timestamp authority proving a record existed at that time. Each ledger record has two (FreeTSA and Sectigo). |
| Paper trading | Decisions recorded live, with no money, and scored once their five-session window ends. |
| Ledger | The append-only file of paper records. Each line carries the previous line's hash and a timestamp, so no line can be changed unnoticed. |
| PASS, BUY ON TRIGGER, NOT EXECUTABLE | A paper decision: do not trade; trade if the entry condition is met; cannot be traded (for example no quote). |
| CORRECT REJECTION, MISSED GAIN | A scored PASS: the plan would have lost or not traded, or it would have made money. |
| Append-only | Committed research records are never edited. A correction is a new file. `tools/check_append_only.py` enforces this on every commit once the hook is switched on, and CI checks every push. |
| KOD | The evidence lab in `kod-machine/`: frozen, timestamped case cards on single big moves. |
| ASTRA | Your production scanner, in the separate Moonshot-Scanner repository. Nothing here changes it. |
| Ace, Codex, Hermes | Other reviewers and agents. Ace reviewed the KOD lab and PR #3, where it found 5 defects. Codex reviewed E5; it gave its name to the `codex/` branches. Hermes is the agent on your Mac (G3 scheduling, the PUMP-LAB download, its EXIT-ATR run). |

Sources: `idx-signals/idxsig/paper.py` (E30 and scoring), `idx-signals/research/E1/PROTOCOL.md`, `idx-signals/idxsig/rules/moonshot_e1.py` (F1_ARA), `idx-signals/idxsig/backtest.py` (IDX holdout), `idx-signals/research/E2/protocol.json` (US and crypto holdout), `idx-signals/idxsig/controls.py`, `idx-signals/idxsig/execution.py`.

## For LLM agents

Read this before touching the repository. Every fact here is in git or in the files named, except the routine times (your scheduled tasks) and E7's commit a61ba164 (the Mac snapshot).

**Hard rules**

- Never place, simulate or schedule a real order or move funds. Paper only.
- Committed research files are append-only; a correction is a new dated file. Run `git config core.hooksPath .githooks` once per clone so the pre-commit hook runs `tools/check_append_only.py --staged`; CI runs it with `--all` on every push. The branch is unprotected and history may not be rewritten, so a pushed violation cannot be undone: run the check before each commit.
- Sealed holdouts: IDX 2024-01-02 to 2025-02-21 (guarded in `idx-signals/idxsig/backtest.py`); US and crypto 2024-01-01 to 2026-12-31 (`idx-signals/research/E2/protocol.json`). Only the PR #7 and E5 branches guard US and crypto in code. Everywhere else, every US or crypto run must set its end date explicitly: `panel_crypto-20261008T003354Z` and `panel_us-20261008T004105Z` hold rows to 2026-10-07. 2023 is already used.
- Never rewrite history or force-push. Push only `claude/idx-signals-test-repo-ds0jw7` without asking; merges and other pushes need the owner. Never modify, merge or delete `origin/moonshot-tools`: the Moonshot Project's scheduled runs fetch it.
- Do not inspect credentials. The SEC contact comes only from the environment: `KOD_SEC_CONTACT` for `idx-signals/research/E9/collect_sec.py`, `IDXSIG_SEC_USER_AGENT` for the idxsig SEC commands. Never write it to a file, and do not rely on the placeholder default in `idx-signals/idxsig/us_actions.py`.
- Production ASTRA stays unchanged. Never overwrite Hermes's Mac work, and do not start a run of a design Hermes is running (the cloud EXIT-ATR v1 was one such rebuild, kept apart in its own folder).
- Never start a paper scan while another is running: the ledger is one hash chain.

**Where everything lives**

| Work | Branch | Path | Head | On GitHub? |
| --- | --- | --- | --- | --- |
| Harness, E1, E2, E3, E9, IDX capacity, paper ledger, KOD lab, Zealand | claude/idx-signals-test-repo-ds0jw7 | idx-signals/, kod-machine/, handoff/ | 0e3e509 before this blueprint; the daily scans add commits | Yes |
| E4 | origin/claude/e4-fade-short-side | idx-signals/research/E4 | 2b26197 | Yes, PR #7 |
| E5 | origin/claude/e5-ceiling | idx-signals/research/E5 | 9bc361d | Yes, draft PR #8 (the local copy is one commit behind, at 7f9041a) |
| E6 | claude/e6-pressure-response | idx-signals/research/E6 | fa142ff | Yes, no PR |
| E7 feasibility | claude/e7-feasibility | idx-signals/research/E7 | a17aaa7 | Not as a branch; as a bundle in handoff/ |
| E8 | claude/e8-peer-spillover | idx-signals/research/E8 | 6c8fd1c | Not as a branch; as a bundle in handoff/ |
| EXIT-ATR v1 | claude/exit-atr-trail-v1 | idx-signals/research/EXIT_ATR_v1/cloud | 5d86e89 | Not as a branch; as a bundle in handoff/, and its result in handoff/exit-atr-cloud/ |
| US pipeline, EXEC-US v2.1 | origin/claude/us-pipeline-v1 | idx-signals/research/US_PIPELINE_v1, EXEC_US_v2_1 | 277dfb2 | Yes, PR #3 (its first parent 0ce21f0 is also the local branch claude/pr3-merge-v5-local) |
| US breakout v1 | claude/us-breakout-v1 | idx-signals/research/US_BREAKOUT_v1 | 0ef056b | Not as a branch; as a bundle in handoff/ |
| E3 US retention | origin/codex/e3-us-retention-protocol-v1 | idx-signals/research/E3_US_RETENTION_v1 | 8b61fb8 | Yes, draft PR #5 |
| Pinned data inputs | not in git (gitignored) | idx-signals/data/panel/ (467 MB), idx-signals/data/raw/ (6.0 GB); manifests in idx-signals/data/manifests/ | none | No: this container only, apart from the E2 US inputs in Git LFS (idx-signals/data/archive/) |
| Moonshot Project toolkit (msx.py) | origin/moonshot-tools | msx.py, README.md | c664ea8 | Yes; unrelated history; never modify, merge or delete |
| G3; Hermes's EXIT-ATR work; E7 completion | your Mac only | G3: ~/Projects/KOD-Machine-G3. Hermes's EXIT-ATR: uncommitted in ~/Projects/KOD-Machine-E7, branch hermes/exit-atr-trail-v1. E7: commit a61ba164, checkout path not recorded | a61ba164 (E7) | No |

Bundles: `handoff/kod-e8/bundles/` (E8), `handoff/exit-atr-cloud/bundles/` (EXIT-ATR), `handoff/kod-next-move/bundles/` (E7, US breakout, the PR #3 merge, and an older E6 copy). Restore one with `git fetch origin`, then `git fetch <bundle file> <branch>:<branch>`; each needs its prerequisite commits from GitHub (fa142ff for E8 and EXIT-ATR, bd352b2 for US breakout, bd352b2 and e952482 for the PR #3 merge, b439884 for E7). The E6 bundle holds only the protocol freeze (cacda7b); use `origin/claude/e6-pressure-response` (fa142ff) instead. The PR #3 merge bundle is redundant: 0ce21f0 is on GitHub as the first parent of PR #3's head.

**Checks that must pass** (from `idx-signals/`): `python3 -m unittest discover -s tests` (243 tests on this branch; other branches differ), `python3 -m idxsig rules`, `python3 -m idxsig verify-runs`, `python3 -m idxsig paper-verify`, `python3 ../tools/check_append_only.py --all`. From `kod-machine/`: `python3 -m unittest` (96 tests) and `python3 -m kod verify`. The harness runs are listed in `idx-signals/results/RUNS.jsonl`; later tests keep their outputs in their own folder under `idx-signals/research/`.

**Daily routines** (scheduled tasks on your account; only crypto's time is also in git): IDX 10:17 UTC weekdays, US 22:47 UTC weekdays, crypto 00:23 UTC daily. Each scans, scores due decisions, verifies and pushes to the designated branch.

**Stale documents to distrust:** the READMEs (222 tests, "only placebo runs") and every text file in `handoff/kod-next-move/` (`HANDOFF.md` and `01` to `06`), a record from 2026-10-14 and 15 that still gives E5 build steps and reports an old head (e635e22) and old ledger counts. Its `bundles/` folder is still valid. Current state: this blueprint, `handoff/kod-e8/`, `handoff/exit-atr-cloud/`, `handoff/kod-e9/` and `handoff/decisions/`.

## Sources

Repository files (branch `claude/idx-signals-test-repo-ds0jw7` unless noted): each experiment's protocol and its report or result under `idx-signals/research/` (E4, E5, E6, E8 and US breakout on the branches in the table above; EXIT-ATR under `idx-signals/research/EXIT_ATR_v1/cloud/` on its branch; E7's branch holds its feasibility check and a draft protocol only); Zealand under `kod-machine/research/ZEALAND_PILOT_v1/`; `idx-signals/results/RUNS.jsonl`; `idx-signals/paper/ledger.jsonl` and `idx-signals/paper/README.md`; `kod-machine/reports/KOD_LAB_STATUS.md`; `handoff/` checkpoints and decisions; Hermes's archive in `idx-signals/research/EXIT_ATR_v1/cloud/hermes_archive/` on the EXIT-ATR branch (Mac state to 2026-10-17 00:10 WIB). GitHub: the descriptions of PRs #3, #5, #7 and #8, and the GitHub Actions run list (166 runs, read 2026-10-17). Your Mac: the snapshot of 2026-10-16 15:51 UTC (E7's completion, G3 operations, the earnings check). Your account: the scheduled-task list (the routine times and the separate Moonshot Project tasks). External: [eToro's fee page](https://www.etoro.com/trading/fees/), read 2026-10-17, and eToro's public instrument list, fetched 2026-10-16 (`idx-signals/data/manifests/etoro_instruments-20261016T190421Z.jsonl`; the raw file stays out of git). Three rounds of independent read-only review checked the figures against these sources on 2026-10-17, and their corrections are applied.
