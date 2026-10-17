# KOD-Machine Blueprint

As of 2026-10-17. This is the repository copy of the Claude Doc "KOD-Machine Blueprint"
(https://claude.ai/code/artifact/818e9141-adcd-4679-8ea3-3f5b8f96706a), written for the owner and for LLM
agents. The doc has two drawings; here they are written out as text. Every figure was checked against its
source; the sources are listed at the end.

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
   - **Research loop (signals in history).** Backtest harness: a plan says when to buy and when to sell; fills are capped at 10% of volume; costs per market, at as-traded prices; each trade is compared with similar names on the same day; pass gates and statistics are fixed in advance. Plans tried: E3, E4, IDX capacity, EXIT-ATR. Output goes to the append-only records: the results log holds 15 runs (placebos, E1, E2); later tests keep their outputs in their own folder; protocols are frozen with file hashes; a commit hook refuses edits.
   - **Live loop (today's signals).** Daily paper scans (IDX 10:17 and US 22:47 UTC on weekdays, crypto 00:23 UTC daily) lead to a decision: buy only with a plan that passed the research loop. No plan has passed, so none may buy: 128 decisions to date, 0 buys. Decisions go into the paper ledger: 188 records in one hash chain, two RFC 3161 timestamps on each, each decision scored after five sessions.
5. **Not wired into the scanner.** The KOD evidence lab (frozen, timestamped case cards; 4 cases, 0 of the 30 prospective cases it needs). The G3 pilot on your Mac (20 stocks, descriptive only; first results due 2026-11-10). The Moonshot Project tasks (a separate system on your account, with its own ledger).

Data flows down into two loops that share the same frozen detectors. The research loop replays history and compares every trade with similar names bought the same day; the live loop scans each day and may buy only once a plan has passed the research loop, which none has.

## The goal and the rules

The goal is an early-warning system for large upward moves that supports profitable trades. It is judged on win rate, net return, losses and capital exposure together (your words, 2026-10-16). You trade through eToro, so a result only matters if eToro can execute it.

| Market | On eToro? | eToro's cost | What it means for us |
| --- | --- | --- | --- |
| Indonesian stocks (IDX) | No: 0 Indonesian (.JK) symbols among eToro's 18,236 instruments | n/a | The IDX scanner cannot be traded there |
| US stocks (Nasdaq, NYSE) | Yes: 6,152 distinct stock symbols | A $1 or $2 commission may apply on opening and on closing, plus the spread. Short sales are CFDs with overnight fees | The one market where the machine's stock signals can be executed |
| Crypto | 295 coins plus 49 dated bitcoin futures; the list also holds 366 internal crypto entries | 1% to buy and 1% to sell (Bronze to Gold tiers) | The tests assumed 0.4% a round trip; at eToro's 2%, every crypto result below would be about 1.6 points worse. Only 154 of the 506 Binance coins trading on 2026-10-08 share a symbol with an eToro coin |

The instrument list is eToro's public list, fetched 2026-10-16 (`data/manifests/etoro_instruments-20261016T190421Z.jsonl`). Fees are from [eToro's fee page](https://www.etoro.com/trading/fees/), read 2026-10-17.

**The rules every test followed**

| Rule | What it means | Where it is written |
| --- | --- | --- |
| No real money | No orders, no funds moved. Every live decision is paper only. Production ASTRA is left unchanged | Your instructions; `idx-signals/paper/README.md` |
| Freeze before results | The hypothesis, trading rules, comparison and pass criteria are written and hashed before any return is computed | Each experiment's `PROTOCOL.md` and `protocol.json` |
| One recorded run | Each test runs once on its frozen protocol, and a failure is reported as it is, never re-tuned until it looks profitable. Redesigns after a failure are declared as new versions (E4 v2, E5 v1.1). The 2023 US test ran 9 times in all as data repairs landed, with the strategy unchanged | Your instructions; each protocol; `idx-signals/results/RUNS.jsonl` |
| Compare with matched controls | Every trade is set against similar names bought the same day under the same plan | `idx-signals/idxsig/controls.py` |
| Costs always included | IDX: 0.15% to buy, 0.25% to sell. US: per side 1.5% under $1, 0.5% for $1-5, 0.15% for $5-20, 0.05% above $20, plus the SEC fee on sales. Crypto: 0.1% fee plus 0.1% slippage per side | `idx-signals/idxsig/profiles.py` |
| No peeking | Each day's signal uses data up to that close only. The harness rebuilds every signal session by session and refuses a rule whose output changes when future data is added | `idx-signals/idxsig/rules/__init__.py` |
| Sealed holdouts | IDX 2024-01-02 to 2025-02-21. US and crypto from 2024-01-01. Each is used once, for a detector already frozen and validated. US and crypto 2023 was already examined in E2 | `idx-signals/idxsig/backtest.py`; `idx-signals/research/E2/protocol.json` |
| Append-only records | Committed research files are never edited. A correction is a new, dated file. A check runs on every commit | `tools/check_append_only.py` |
| History is not a forecast | A historical result is never presented as future performance. No trade or probability is invented to fill a quota | Your instructions |

## Every experiment so far

Thirteen tests ran to a verdict. Each was frozen before its first result, and none produced a strategy that makes money after costs. Two later steps used changes made after a first look, both disclosed: E5's corrected version (v1.1) and the E7 run on your Mac. Newest first; dates are UTC.

| Date | Test (market) | What it asked | What happened | Verdict |
| --- | --- | --- | --- | --- |
| 2026-10-16 | E9 catalyst split (US) | Do +30% days backed by an SEC filing published before the next open keep rising? | Documented moves -1.07% a trade (644 trades, win rate 41.5%); undocumented -3.06% (1,337 trades, win rate 33.0%). Gap +1.99 points (-1.83 to +6.00) | NEGATIVE |
| 2026-10-16 | EXIT-ATR v1 (crypto) | Does a trailing stop rescue the +30% entry? | Trailing exit -1.11% a trade vs -0.29% for the original exit: a change of -0.82 points (-2.92 to +1.19). Under either exit the entry trails matched coins by about 3 points | NEGATIVE |
| 2026-10-16 | E8 peer spillover (crypto) | Do coins tied to a coin that jumps alone follow it? | 72-hour excess before costs +0.44% (-0.28 to +1.16). As a trade: +0.09% net, win rate 41.1%, worst drawdown -38.9% at 5% of capital a trade | FAIL |
| 2026-10-15 to 16 | E7 funding squeeze (crypto perpetuals to spot) | Do negative funding and rising open interest predict the spot coin? | Cloud data check GO (845 events). Finished on your Mac, not published: 534 events, 24-hour excess before costs -0.35 points (-0.95 to +0.33). The trading stage was not run | FAIL (Mac) |
| 2026-10-15 | E6 pressure response (crypto) | Does buy/sell pressure absorption predict five-day returns? | Primary setup: excess before costs +0.37% (-1.01 to +1.93), p 0.32. Second setup: 136 flags, under the 200 needed | NULL |
| 2026-10-14 | E5 ceiling (IDX, US, crypto) | Can any daily-bar ranking tell up-moves from down-moves? | IDX excess before costs +1.3%, p 0.074 against 0.025 needed; crypto p 0.42; US below its controls. The one early pass, in a side arm on IDX, came from a code defect found in review | NULL |
| 2026-10-13 | E4 short side (crypto) | Can shorting the +30% movers pay? | v1: 0 of 144 detector-plan pairs admissible (36 plans on each of 4 detectors). v2, redesigned on the same years, passed discovery (+5.82% a trade), then failed 2023: -1.50% vs -0.22% for matched shorts, 8.8% liquidated | FAIL |
| 2026-10-13 | E3 execution plans (IDX) | Does any entry and exit plan make the limit-up detectors pay? | 0 of 108 detector-plan pairs admissible (36 plans on each of 3 limit-up detectors). 18 pairs averaged above zero over 2021-22, but all 108 lost money in 2022 | NONE ADMITTED |
| 2026-10-09 | US breakout v1 (US) | Does buying a 60-session closing-high breakout pay, under the 5% stop rule? | 11,833 trades in 2023: -0.180% a trade vs -0.138% for matched entries. Difference -0.042 points (-0.115 to +0.035) | NO EDGE |
| 2026-10-09 | IDX causal capacity (IDX) | Did the fill rule hide an edge? | With fills limited to what was known at the decision: -3.64% vs -0.44% for matched names (before: -4.06% vs -0.53%) | NO HIDDEN EDGE |
| 2026-10-08 | Zealand pilot (Denmark, KOD lab) | Was Zealand Pharma's +37.9% day visible and tradable in advance? | The news came out before the market opened, and 114% of the day's move happened before the first possible trade. Entries after the news lost 16% to 19% within five sessions, depending on the entry | NO ACTIONABLE EDGE |
| 2026-10-08 | E2 and repairs v1-v3 (US, crypto) | Which detector flags +30% moves, and can it be traded? | Detection 5.4x (US) and 4.6x (crypto) better than matched names. Trading in 2023: US -3.65% vs -0.60%, crypto -1.90% vs +1.42%. Every US repair stayed negative, from -5.27% to -0.97% across versions | DETECTION YES, TRADING NO |
| 2026-10-08 | E1 (IDX) | Which signals come before +30% moves on the Indonesian exchange? | Close locked at the upper limit (F1_ARA): 18.3% of flags went on to +30% vs 1.96% for matched names. Trading it: -4.06% vs -0.53%. 339 of 1,042 entries were still locked at the limit | DETECTION YES, TRADING NO |

Not run to a verdict: E3 US retention (draft PR #5, a protocol only) and G3 (a descriptive 20-stock pilot on your Mac; first results mature 2026-11-10). How to read the numbers: unless marked, a percentage is the average net return per trade after costs, "vs" sets it against matched names, and a range in brackets is a 95% interval. "Excess before costs" is the return over matched names before costs. Win rates, hit rates and liquidation rates are shares of trades or flags. A range written "from ... to" across versions or entries is not an interval.

## What went right

The machine itself works: it measures honestly, catches its own errors and has never risked money.

| What worked | Evidence |
| --- | --- |
| Detection is real | In the 2023 validation, flagged names reached +30% far more often than matched names: IDX 18.3% vs 1.96%, US 15.4% vs 2.8%, crypto 18.5% vs 4.0% |
| The rules held | Each protocol was frozen before its own runs, and every failure was published as it came out. Redesigns after a first look (E4 v2, E5 v1.1, E7's Mac run) were declared as such, and none produced a pass |
| Results reproduce | The original E2 US run was rebuilt byte for byte from archived inputs. E5 reproduced three earlier runs exactly before testing anything new |
| The harness cannot peek | A coin-flip placebo came out indistinguishable from random in all three runs. Every recorded run passed its lookahead check: session by session from the second run on, at 3 cut-off dates for the first |
| Hidden data defects were caught | Yahoo's split rescaling, future-informed row deletion, after-the-fact fill sizes, crypto redenominations (COCOS 1,000:1), the SEC timestamp defect and a bankruptcy splice were each found and disclosed |
| Outside review found real errors | Ace found 5 defects that 233 passing tests had missed. Codex withdrew 1,074 of 1,313 split approvals and found the defect behind E5's one pass. Hermes found 3 data-path defects |
| Records are tamper-evident | 188 ledger records, each with two RFC 3161 timestamps; the hash chain and the append-only check are intact over the whole history. 163 of 165 GitHub Actions runs succeeded; the 2 failures were on 2026-10-08 |
| No money at risk | 0 real orders. 128 paper decisions, 0 buys, because no plan passed |

## What went wrong

The core failure is timing: the signals fire after most of the move, and buying after a jump lost to similar names in every market tested.

**Strategy**

- The signals are late. Only 0.9% of US moves and 0.1% of crypto moves of +30% were flagged before their peak (IDX: 9.8%). On the day a move began, the flag caught 0 of 4,100 US moves, 1 of 730 crypto moves and 4 of 569 IDX moves. After a US flag, the median stock fell 10.3% over the next five sessions.
- Buying after the jump lost to similar names in every market: IDX -4.06% vs -0.53%, US -3.65% vs -0.60%, crypto -1.90% vs +1.42%. In E9, all 2,251 US trades averaged -2.19%, 2.47 points below their controls.
- Nothing bolted on afterwards repaired it: 0 of 108 IDX detector-plan pairs, a trailing stop on crypto (-0.82 points), shorting crypto (failed validation) and an SEC-filing filter in the US (still -1.07%).
- On IDX the best moves cannot be bought: 339 of 1,042 entries were locked at the upper limit, and the fills that do happen are mostly fading moves.
- Gains did not repeat from year to year. E3's positive plans came from 2021, and all 108 pairs lost in 2022. The trailing stop helped only in 2021. E4's shorts made money in 2022 and lost in 2021. E8 was positive in 2020 and 2021, then -0.63% in 2022. Only E6 was positive every year, too weakly to tell from zero.
- Fat tails swamp the averages. A few meme-era trades (HKD +1,025% and BNGO +844% in five sessions) make intervals so wide that differences of a few points cannot be resolved.

**Data**

- The US universe is today's listings only. Companies that died are missing, and no free point-in-time source was found.
- Yahoo rescales old prices after splits. 60% of 2023 US flags were in names that later reverse-split, and 582 of 1,099 trades sat in the wrong cost tier. The fix that excluded those names turned out to remove the worst trades (-9.17% vs -1.75%), so it flattered the result.
- Binance prices ignore redenominations: one COCOS trade would show a fake +125,489%.
- SEC's bulk JSON stamps filing times in two different conventions, so E9's first data check failed.
- Costs are assumed price tiers, not measured spreads, and daily bars cannot prove an opening fill.
- IDX data: the exchange site blocks downloads, and the free mirror stops at 2025-02-21.

**Process**

- The tests were not built around your broker. That it is eToro surfaced on 2026-10-16, after E1 to E8. Three tests were wholly on IDX, which eToro does not list (E1, E3, IDX capacity), plus E5's IDX arm. The crypto tests used Binance's coins at 0.2% a side; eToro charges 1% a side, and only 154 of the 506 Binance coins trading on 2026-10-08 share a symbol with an eToro coin.
- 2023 was reused as the validation year. The US and crypto holdout is guarded in code only on unmerged branches, and some 2024+ prices were seen in a data-quality note.
- Your usage budget cut independent reviews. E5's two defects were found only after the result was published.
- Work is scattered: four branches exist only in this cloud container and as bundle files, four pull requests are open, and some work exists only on your Mac. The READMEs are stale (they say 222 tests; 243 run).
- The harness was built for your own detector rule, which was never supplied (the USER_RULE slot is empty).
- The KOD evidence lab was never connected: it has 0 of the 30 prospective cases it needs.

## What is doable and what is not

Every idea tested so far failed after costs. The open ground that eToro can trade is US stocks, and only one idea there is not another version of the +30% entry.

Drawing in the doc: "Every tested idea failed; the open ground eToro can trade is US-only." Columns are markets, from not tradable on eToro to tradable; rows are what the tests found.

| | IDX stocks (not on eToro) | Crypto (some coins, 1% a side) | US stocks (on eToro) |
| --- | --- | --- | --- |
| Tested: no edge after costs | Buy after limit-up (E1: -4.06% vs -0.53%); entry and exit plans (E3: 0 of 108 admitted); causal fill limits (capacity: no hidden edge) | Buy after a +30% day (E2: -1.90% vs +1.42%); trailing-stop exit (EXIT-ATR: -0.82 points); shorting the movers (E4: failed on 2023); other crypto signals (E6, E7, E8: no edge) | Buy after a +30% day (E2, its repairs, E9); 60-session breakout (11,833 trades, no edge) |
| Tested, across all three | Daily-bar ranking (E5): no edge in any of the three markets | | |
| Not yet tested | New IDX signals (eToro lists no IDX stocks) | Pump-group footprints (a download on your Mac) | **Form 4 insider buying (SEC data; never tested)**; delayed +30% entry (E3 US retention, drafted) |
| Not yet tested, across all three | Regime filter on the +30% entries: proposed, never run | | |

The delayed entry and the regime filter are both +30% variants: retiring that entry closes them too. The crypto tests assumed 0.2% a side in costs; eToro charges 1% a side, five times as much. The highlighted idea (Form 4 insider buying) is the only open ground eToro can trade.

| Approach | Can eToro execute it? | Status |
| --- | --- | --- |
| Buy the open after a US +30% day | Yes: 6,152 US stock symbols listed | Dead: lost in E2, in every repair and in E9 |
| US 60-session breakout | Yes | Dead: no edge in 11,833 trades |
| IDX limit-up detector plans | No: eToro lists no Indonesian stocks | Dead: 0 of 108 detector-plan pairs admitted |
| Crypto +30% entries and exits | Buying yes, at 1% a side, for the coins eToro lists | Dead: E2 and EXIT-ATR failed; you retired the entry on 2026-10-17 |
| Shorting the crypto movers | Not checked | Dead: E4 failed its 2023 validation |
| Crypto spillover, pressure and funding signals | Buying yes, at 1% a side, for the coins eToro lists | Dead: E8, E6 and E7 found no edge |
| Daily-bar ranking, all three markets | US yes; IDX no; crypto at 1% a side | Dead: E5 found no edge |
| Form 4 insider buying (US information that may come before a move) | Yes | Doable, untested: SEC data is free and public |
| Delayed +30% entry (E3 US retention) | Yes | Untested: a protocol only (draft PR #5), a variant of the +30% entry, on 2023 data that is already used |
| Regime filter on the +30% entries | In the US, yes | Untested: proposed on 2026-10-14 (4th of 6 ideas), never run; a variant of the +30% entry |
| Pump-group footprints | Unknown | Untested: Hermes runs a data download on your Mac; you excluded the idea from the EXIT-ATR work, and nothing has been analysed |

## Open decisions and the next step

Nine calls are waiting on you. The first one closes the last open line of the current approach.

| Decision | What it changes | My recommendation |
| --- | --- | --- |
| Retire "buy after a +30% day" for US stocks | Stops every further variant of the entry E9 tested, including the delayed entry (draft PR #5) and the regime filter | Yes, as you did for crypto on 2026-10-17 |
| Merge PR #7 (E4 short side) | Brings the US and crypto holdout guard into the main code | Yes, for the guard |
| PR #3 (US pipeline, execution contract v2.1, paper policy v5) | Needs Ace's re-review; switching the daily scans to it is a new paper policy | Leave the scans as they are until a plan passes |
| Draft PR #8 (E5) | Its own listed blockers: a review of the last fixes (9bc361d) and a re-run of the stages by someone other than the builder | Review, then decide |
| Draft PR #5 (E3 US retention) | A protocol that was never run, on data already used | Close it if you retire the +30% entry; otherwise park it |
| Push the four cloud-only branches (E7 feasibility, E8, EXIT-ATR, US breakout) | Today they survive only in this container and as bundle files | Push them, or keep the bundles |
| Accept 2023 as provisional validation for new ideas | Without it, every new idea waits months for forward paper data | Yes, labelled PROVISIONAL |
| Publish E7's Mac result | The FAIL exists only on your Mac | Yes |
| G3 on your Mac | Two of the first three collections were missed while the laptop slept | Keep the Mac on power, online and open from 03:15 to 03:30 WIB until 2026-10-30, then from 04:15 to 04:30 WIB from 2026-11-02, when New York leaves daylight saving time. Or retire G3 |

**Next step:** close the +30% line. Then either stop, or test one US signal that may come before the move, frozen in advance like the others. My pick is insider buying reported to the SEC on Form 4: the data is free, and each filing is due within two business days of the trade. It has not been tested here. The other candidate on record, an earnings or guidance surprise (PR #8, section 8), needs release times and consensus estimates fixed before each release, and neither is in the repository. A ten-announcement check on your Mac passed the SEC filing route but was NO-GO for a broad backtest with the current price inputs.

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
| Net return | A trade's return after every modelled cost: fees and a per-side cost that is larger for cheaper shares. |
| Fill model | The rule for whether a paper trade could really have been filled. Model B allows at most 10% of the median daily volume known at the decision. |
| Matched controls | For each signal, random draws from other names on the same day that share its price, liquidity, size (IDX only), volatility, momentum, drawdown and listing-age buckets, traded with the same plan. Usually 200 draws, with repeats allowed; when fewer than 5 names match, the least important feature is dropped. US breakout used 10 draws per signal and the E1 and E2 event studies 5 per event. They answer: would a random similar name have done as well? |
| Excess | A trade's net return minus the average net return of its matched controls. Above zero means the signal added something. |
| Win rate | The share of trades with a net return above zero. |
| 95% interval | The range the true average plausibly lies in. If it includes zero, the result could be luck. |
| Week bootstrap | How the intervals are computed: whole calendar weeks are resampled, because trades in the same week move together. |
| Discovery, validation, holdout | Three separate periods: one to test, one to confirm, one sealed for a single final test. IDX holdout: 2024-01-02 to 2025-02-21. US and crypto holdout: 2024 onward. |
| Pre-registration, freeze | Writing down the hypothesis, rules, comparison and pass criteria, with file hashes, before any return is computed. Results cannot be tuned afterwards. |
| Feasibility check | A counts-only check, with no returns, that the data can support a test. It ends GO or NO-GO. |
| Amendment | A dated, committed change to a plan, made before any result is seen, with its reason. |
| Gate, criterion | A pass condition stated in advance, such as C1 to C6 in E9. |
| Survivorship bias | A universe built from today's listings misses companies that later died, which flatters history. |
| Causal, prefix-first | Each day's signal is computed from data up to that day only, so a rule cannot peek at the future. |
| Split-adjusted vs as-traded | Data vendors rescale old prices after a split. Costs and capacity depend on the price that actually traded on the day. |
| Overlap skip | A new signal on a name already held is skipped. |
| Stress | The same trades recomputed with an extra cost per side, for example 0.5%. |
| Clipped (winsorized) mean | An average with the most extreme 1% at each end pulled in, so a few freak trades cannot dominate. |
| Paper trading | Decisions recorded live, with no money, and scored once their five-session window ends. |
| Ledger | The append-only file of paper records. Each line carries the previous line's hash and a timestamp, so no line can be changed unnoticed. |
| PASS, BUY ON TRIGGER, NOT EXECUTABLE | A paper decision: do not trade; trade if the entry condition is met; cannot be traded (for example no quote). |
| CORRECT REJECTION, MISSED GAIN | A scored PASS: the plan would have lost or not traded, or it would have made money. |
| Append-only | Committed research records are never edited. A correction is a new file. `tools/check_append_only.py` enforces this on every commit. |

Sources: `idx-signals/idxsig/paper.py` (E30 and scoring), `idx-signals/research/E1/PROTOCOL.md`, `idx-signals/idxsig/rules/moonshot_e1.py` (F1_ARA), `idx-signals/idxsig/backtest.py` (IDX holdout), `idx-signals/research/E2/protocol.json` (US and crypto holdout), `idx-signals/idxsig/controls.py`, `idx-signals/idxsig/execution.py`.

## For LLM agents

Read this before touching the repository. Every fact here is in git or in the files named.

**Hard rules**

- Never place, simulate or schedule a real order or move funds. Paper only.
- Committed research files are append-only (`tools/check_append_only.py`, run as a commit hook). A correction is a new dated file.
- Sealed holdouts: IDX 2024-01-02 to 2025-02-21 (guarded in `idxsig/backtest.py`); US and crypto 2024-01-01 onward (`research/E2/protocol.json`; code guard only on the PR #7 and E5 branches). 2023 is already used.
- Never rewrite history or force-push. Push only `claude/idx-signals-test-repo-ds0jw7` without asking; merges and other pushes need the owner.
- Do not inspect credentials. The SEC contact address comes only from the environment variable `KOD_SEC_CONTACT` and is never written to a file.
- Production ASTRA stays unchanged. Hermes's Mac work is out of reach and must not be duplicated or overwritten.
- Never start a paper scan while another is running: the ledger is one hash chain.

**Where everything lives**

| Work | Branch | Path | Head | On GitHub? |
| --- | --- | --- | --- | --- |
| Harness, E1, E2, E3, E9, IDX capacity, paper ledger, KOD lab, Zealand | claude/idx-signals-test-repo-ds0jw7 | idx-signals/, kod-machine/, handoff/ | 0e3e509 at writing; the daily scans add commits | Yes |
| E4 | origin/claude/e4-fade-short-side | idx-signals/research/E4 | 2b26197 | Yes, PR #7 |
| E5 | origin/claude/e5-ceiling | idx-signals/research/E5 | 9bc361d | Yes, draft PR #8 (the local copy is one commit behind, at 7f9041a) |
| E6 | claude/e6-pressure-response | idx-signals/research/E6 | fa142ff | Yes, no PR |
| E7 feasibility | claude/e7-feasibility | idx-signals/research/E7 | a17aaa7 | No: this container and a bundle |
| E8 | claude/e8-peer-spillover | idx-signals/research/E8 | 6c8fd1c | No: this container and a bundle |
| EXIT-ATR v1 | claude/exit-atr-trail-v1 | idx-signals/research/EXIT_ATR_v1/cloud | 5d86e89 | No: this container and a bundle |
| US pipeline, EXEC-US v2.1 | origin/claude/us-pipeline-v1 | idx-signals/research/US_PIPELINE_v1, EXEC_US_v2_1 | 277dfb2 | Yes, PR #3 (its merge commit 0ce21f0 is the local branch claude/pr3-merge-v5-local) |
| US breakout v1 | claude/us-breakout-v1 | idx-signals/research/US_BREAKOUT_v1 | 0ef056b | No: this container and a bundle |
| E3 US retention | origin/codex/e3-us-retention-protocol-v1 | idx-signals/research/E3_US_RETENTION_v1 | 8b61fb8 | Yes, draft PR #5 |
| G3, Hermes's EXIT-ATR work, E7 completion | your Mac only | G3: ~/Projects/KOD-Machine-G3; E7: a local checkout (path not recorded) | a61ba164 (E7) | No |

Bundles: `handoff/kod-e8/bundles/` (E8), `handoff/exit-atr-cloud/bundles/` (EXIT-ATR), `handoff/kod-next-move/bundles/` (E6, E7, US breakout, PR #3 merge). Restore one with `git fetch <bundle file> <branch>:<branch>`.

**Checks that must pass** (from `idx-signals/`): `python3 -m unittest discover -s tests` (243 tests), `python3 -m idxsig verify-runs`, `python3 -m idxsig paper-verify`, `python3 ../tools/check_append_only.py --all`. KOD lab: 96 tests. The harness runs are listed in `idx-signals/results/RUNS.jsonl`; later tests keep their outputs in their own folder under `idx-signals/research/`.

**Daily routines** (scheduled tasks on your account): IDX 10:17 UTC weekdays, US 22:47 UTC weekdays, crypto 00:23 UTC daily. Each scans, scores due decisions, verifies and pushes to the designated branch.

**Stale documents to distrust:** the READMEs (222 tests, "only placebo runs"), the status line of `handoff/kod-next-move/HANDOFF.md` (stops at E5) and `04_decisions.md` (not updated since 2026-10-14).

## Sources

Repository files (branch `claude/idx-signals-test-repo-ds0jw7` unless noted): each experiment's `PROTOCOL.md` and its `REPORT.md`, `RESULT.md` or `RESULTS.md` under `idx-signals/research/` (E4, E5, E6, E7, E8, EXIT-ATR and US breakout on the branches in the table above); `idx-signals/results/RUNS.jsonl`; `idx-signals/paper/ledger.jsonl` and `paper/README.md`; `kod-machine/reports/KOD_LAB_STATUS.md`; `handoff/` checkpoints and decisions. GitHub: the descriptions of PRs #3, #5, #7 and #8, and the GitHub Actions run list (165 runs, read 2026-10-17). Your Mac: the snapshot of 2026-10-16 15:51 UTC (E7 completion, G3 operations, the earnings check); nothing later is known here. Your account: the scheduled-task list, which also holds the separate Moonshot Project tasks. External: [eToro's fee page](https://www.etoro.com/trading/fees/), read 2026-10-17, and eToro's public instrument list, fetched 2026-10-16 (`data/manifests/etoro_instruments-20261016T190421Z.jsonl`; the raw file stays out of git). Three independent read-only reviewers checked every figure against these sources on 2026-10-17, and their 22 corrections are applied.
