# Systematic edges in crypto for a small retail account: what the evidence supports (2018–2026)

Literature and web review only (research sub-agent, 1 November 2026); no price data was downloaded and no return statistics were computed here. Figures are quoted from the cited sources; the reviewer's own arithmetic or interpretation is marked [inference]. Cost assumptions: Binance spot taker 0.10% per side, Binance USDT-margined perpetuals 0.05% per side, eToro roughly 1% per side.

## Summary table

| Mechanism | Who pays | Best evidence | Post-2022 status | Survives retail costs? | Confidence |
|---|---|---|---|---|---|
| 1. Time-series momentum / trend (BTC, majors) | Late-reacting holders and forced sellers | Han, Kang & Ryu (2013–Aug 2023): long-only TSMOM (28-day lookback, 5-day hold) Sharpe 1.51 after 15 bps vs 0.85 for market; Gerritsen et al. 2020; Detzel et al. 2021 | Quantpedia OOS Feb 2022–Aug 2024: "buy at x-day high" still worked at all lookbacks; mean-reversion counterpart failed. Edge is concentrated in drawdown avoidance | Binance: yes at daily/weekly rebalance. eToro: only multi-week/month holds | M-H |
| 2. Cross-sectional altcoin momentum | Slow attention and retail chasing; short leg pays jump risk | Liu, Tsyvinski & Wu (2014–2018): 1–4 week momentum 2.5–4.1% per week long-short, no costs; Borri et al. 2026: 2-week momentum 2.1% per week post-2020 (t 3.70) | Alive statistically, but Han-Kang-Ryu (realistic costs) call XSMOM evidence weak: 5 of 21 portfolios liquidated | Marginal on Binance perps; not on eToro | L-M |
| 3. Funding carry / basis (long spot, short perp) | Leveraged longs paying for upside | BIS WP 1087 (2023): average carry >10% p.a.; He et al. 2024: Sharpe 1.8 at retail costs; Borri et al. 2026: carry Sharpe 6.45 (Aug 2020–May 2025), 4.06 from 2024, negative in 2025 | Compressed: Binance BTC mean funding 0.0057% per 8h in Q3 2025; Ethena yields 3.5–4.5% by 2026 | Mechanically yes, but gross yield now near stablecoin lending | H (exists), L (pays enough) |
| 3b. Funding as contrarian signal | Over-levered traders who get liquidated | K33 (Sept 2024): after 30-day average funding turned negative (7 instances since 2018), average 90-day BTC return 79%, median 55% | Small sample | Low turnover, yes | L-M |
| 4. Short-term mean reversion after extreme moves / cascades | Liquidated traders and stop-outs | Ledger (2021): significant negative autocorrelation at 1–4h horizons, larger moves revert more; Garcia Seuma 2026: 87.8% of forced selling in a cascade within 30 minutes | Daily version not exploitable after costs (Caporale & Plastun); hourly version plausibly alive but no clean post-2022 test | Only on perps with limit orders and automation | L-M |
| 5. Intraday / weekly seasonality | Timing of fiat flows and session hand-offs | Quantpedia (Gemini hourly 2015–mid 2023): hold BTC 21:00–23:00 UTC, 40.6% annualised, Calmar 1.79 | Rough 2022–23; US-hours dominance reversed after Jan 2024 ETF launch | Two trades per day at 0.20% round trip consumes most of the gross [inference] | L |
| 6. Volatility risk premium (options) | Convexity buyers | Almeida et al. (Deribit 2017–2022): BTC variance risk premium ~14% p.a. vs ~2% for S&P 500 | Not covered post-2022 | Excluded: needs an options venue | M |
| 7. Support/resistance, wicks, breakout-retest, order blocks / SMC | Stop-loss clustering (Osler 2003) | Hudson & Urquhart 2019 (14,919 rules): support-resistance class performed worst, breakeven costs 8–16 bps; filter and channel-breakout best (breakeven 30–148 bps). Mahadzva 2026 (SSRN): no evidence ICT/SMC concepts work as taught; liquidity sweeps predict continuation, not reversal | No Bitcoin predictability OOS (H1 2018); no peer-reviewed SMC test | S/R bounces: no. Breakout rules: Binance yes, eToro no | H (that S/R and SMC lack evidence) |
| 8. Exit logic | n/a | Kaminski & Lo: stops add value only under momentum or regime switching, never under a random walk; daily/weekly stops had negative stopping premia. Setup4Alpha (105,708 trades): tightest trailing stop was the worst exit, 12-month time exit the best | n/a | Wide, slow stops yes; tight trailing stops no | M |
| 9. Sizing / Kelly | n/a | MacLean, Thorp & Ziemba 2010: full Kelly maximises growth but is "relatively risky in the short term"; mean-estimate error matters ~100:3:1 vs variance error | n/a | n/a | H (theory) |

## 1. Time-series momentum / trend following

Who pays: overreaction and under-reaction; leveraged longs liquidated in downtrends and investors who re-enter late. He et al. find past returns explain more than 50% of the futures-spot gap.

Evidence: Han, Kang and Ryu (sample Dec 2013–Aug 2023, coins with at least USD 1m market cap and daily volume, Binance futures for shorts, 15 bps per trade, daily mark-to-market with liquidation modelling). Best long-only TSMOM (28-day lookback, 5-day hold, long when the lookback return is in its top tercile, otherwise cash): Sharpe 1.51 after costs versus 0.85 for the market, higher Sharpe than the market in eight of ten years, lower drawdown in every year. Gains come from lower downside risk; short-only and long-short variants underperform long-only. The authors note look-ahead bias in parameter selection and call Sharpe 1.5 the practical ceiling. Gerritsen et al. (2020) find trading-range breakout rules beat buy-and-hold on a bootstrapped Sharpe basis. Detzel et al. (2021) show price-to-moving-average ratios forecast daily Bitcoin returns in and out of sample. Rozario et al. (2020) report walk-forward SMA crossovers on BTC with Sharpe 0.5–1.5, zero costs, "a slight dropoff in more recent times".

Post-2022: Quantpedia's 2024 update tested "buy when BTC makes an x-day high" (MAX) and "buy at an x-day low" (MIN) with Feb 2022–Aug 2024 as true out-of-sample. MAX still worked at all lookbacks; MIN produced low or negative returns. Molnar (2026 preprint) documents RSI-14's 30-day information coefficient falling across halving epochs (+0.28, +0.14, +0.17, -0.02).

Turnover and costs [inference]: daily-signal, weekly-holding TSMOM trades perhaps 20–60 times per year, 4–12% per year of fees on Binance; at eToro's 2% round trip only monthly-or-slower rules survive.

Failure modes: chop (2022–2023 range), parameter overfitting, and the fact that most of the edge is drawdown avoidance rather than outperformance in bull markets.

## 2. Cross-sectional altcoin momentum

Liu, Tsyvinski and Wu (1,707 coins, 2014–2018, weekly rebalance): long-short 5-1 returns of 2.7%, 3.3%, 4.1%, 2.5% per week for 1–4 week lookbacks (t 1.99–2.74), no significance at 8 weeks or beyond, no costs or short-sale feasibility. Borri et al. (2026, to Sept 2025): two-week momentum 2.6% per week full sample (t 3.89), 2.1% post-2020 (t 3.70). Han, Kang and Ryu under realistic Binance assumptions: best XSMOM (14-day lookback, 7-day hold) Sharpe 1.28 versus 1.01 for the market; five of 21 variants were liquidated; profits mostly from the long leg. Zaremba et al. (2021) document a one-day reversal in illiquid coins alongside daily momentum in the largest coins.

Failure modes: short-leg squeezes, delistings, survivorship bias in free data, and the one-day reversal that punishes naive entry at the close of the formation window.

## 3. Funding-rate carry and the basis trade

Who pays: BIS attributes carry to "smaller investors seeking leveraged upside in boom periods" with "scarce arbitrage capital taking the other side".

Evidence: BIS: average carry above 10% p.a., peaks up to 60% p.a., high carry predicts future crashes. He, Manela, Ross and von Wachter (2024): Sharpe 1.8 under retail costs. Borri et al. (2026): carry Sharpe 6.45 over Aug 2020–May 2025, falling to 4.06 from 2024 and negative in 2025.

Realised funding 2023–2026: BitMEX Q2 2025 report: 2024 mean 0.0173% per 8h, maximum 0.1308%, less than half of prior bull markets. BitMEX Q3 2025: Binance BTC mean funding 0.0057% per 8h (positive 92.5% of the time); baseline "around 0.01%/8-hour". [inference] 0.0057% per 8h annualises to about 6.2% gross. Ethena sUSDe yields fell from above 20% at peaks to 3.5–4.5% by mid-2026; TVL fell from USD 16.6bn to USD 5.6bn; Blockworks describes basis returns as "converging toward T-bill yields".

Funding as contrarian signal: K33 (Sept 2024): 30-day average funding negative for the seventh time since 2018; after prior instances the average 90-day BTC return was 79% and the median 55%. Small-sample, directional only.

## 4. Short-term mean reversion after cascades

Garcia Seuma (2026 preprint): across seven Binance cascade windows 2022–2025, price impact rose 1.2–3.5x, open interest fell 25–70%, and in the October 2025 event 87.8% of forced selling occurred in the first 30 minutes. Ledger (2021, 1-minute data 2012–2021): significant negative first-order autocorrelation at 1-, 2- and 4-hour horizons, larger moves reverting more. Caporale and Plastun (2018, daily): after one-day overreactions neither reversal nor continuation beat random after costs. Quantpedia's MIN rule failed out of sample 2022–2024.

[inference] A strategy that fades extreme hourly moves must execute with limit orders on perps. Failure modes: catching a continuation during a genuine cascade (fat left tail), exchange outages during exactly the events targeted, auto-deleveraging.

## 5. Seasonality

Quantpedia (Gemini hourly, Oct 2015–Jun 2023): a rule holding BTC only 21:00–23:00 UTC returned 40.64% annualised with Calmar 1.79, with a "rough period in 2022 and 2023". 10x Research (April 2024): most gains since the ETF launch came outside US hours, reversing the prior two years. [inference] Two trades per day at 0.20% spot round trip costs about 73% per year; the gross does not survive on spot and is marginal on perps.

## 6. Volatility risk premium (excluded)

Almeida, Grith, Miftachov and Wang (Deribit Jul 2017–Dec 2022): Bitcoin variance risk premium averages 14% p.a. at one-month horizon versus roughly 2% for the S&P 500. Requires an options venue and margin for short-vol crashes.

## 7. Range and structure concepts used by retail

Hudson and Urquhart (2019; 14,919 rules on BTC, LTC, XRP, ETH to end-2017, stationary bootstrap and multiple-testing corrections): the support-resistance class is the worst of five rule classes (annualised 2–5% versus 8–16% for filter and channel-breakout rules); S/R breakeven costs are 7.9–16.2 bps. Out of sample (H1 2018) the best Bitcoin rule earned -0.10% and -0.91%. Corbet et al. (2019) support variable-length moving-average rules on high-frequency BTC. Islas Anguiano and García-Medina (2025): grid-optimised EMA crossover (26.1%) and MACD+ADX (35.5%) underperformed buy-and-hold (42.5%) on Binance BTC in 2024 before fees.

Order blocks, liquidity sweeps, SMC: the only systematic test (Mahadzva 2026, SSRN, six coded ICT/SMC rules on four FX pairs, walk-forward, bootstrap and permutation tests) concludes "no evidence that ICT/SMC concepts work as literally taught"; in 65 of 66 fold selections a swept liquidity level predicted continuation rather than reversal; the single positive result fails a Deflated Sharpe Ratio check. A vendor backtest of an order-block entry with change-of-character exit (GBP/USD 1h, 2016–2026) lost 15.3% with profit factor 0.83. The mechanism SMC describes (stop clustering around round numbers) is documented by Osler (2003), but no study shows it profitably tradeable.

Verdict: breakout and filter rules have the evidence; support-resistance bounces, rejection wicks and SMC do not.

## 8. Exit logic

Kaminski and Lo: a stop-loss rule has a negative "stopping premium" under a random walk, hurts under mean reversion, and adds value only under sufficiently strong momentum or regime switching. Empirically (1993–2011) daily and weekly stops mostly had negative premia; monthly-window stops raised return by about 1.5% and cut volatility by about 5%. Han, Zhou and Zhu's 10% monthly stop on US momentum cut the worst monthly loss from -49.8% to -11.4%, but Alpha Architect's replication found the plain portfolio had better CAGR and Sharpe. A 26-year Russell 1000 exit study (105,708 trades) found the tightest profit-giveback trailing stop was the worst exit (-0.14% per trade, t -3.6) despite winning most often, while a 12-month time exit earned the most per trade. [inference] Given the hourly mean reversion in Bitcoin, tight intraday stops are exactly the regime where stops destroy value; wide, slow, signal-based exits and volatility-scaled sizing are the defensible choice.

## 9. Sizing and drawdown control

MacLean, Thorp and Ziemba (2010): betting above Kelly "invariably leads to disaster"; mean-estimate errors matter about 100:3:1 relative to variance errors. Example (700 bets, 14% edge): full Kelly's worst case takes USD 1,000 to USD 18 but reaches USD 100k 16.6% of the time; half Kelly's worst case is USD 145 but reaches USD 100k 0.1% of the time. [inference] For a retail account whose edge estimate comes from a biased backtest, quarter-Kelly or a fixed volatility target is the conservative reading; the documented edges have Sharpe at most around 1.5 after costs, and leverage beyond Kelly lowers, not raises, expected growth.

## What is probably a myth (for this account size and these venues)

1. Support/resistance bounces and rejection wicks as a standalone edge.
2. Order blocks, fair value gaps and liquidity sweeps as taught.
3. Tight trailing stops as risk management.
4. Funding carry as a "risk-free 20–30%" (true in 2021 and early 2024, not in 2025–2026).
5. Hour-of-day and day-of-week rules at retail cost.
6. Any of the above on eToro at about 2% round trip: only multi-month trend-following or buy-and-hold survives.
7. Doubling an account quickly via Kelly-style leverage.

## Sources

- Han, Kang & Ryu: https://acfr.aut.ac.nz/__data/assets/pdf_file/0009/918729/Time_Series_and_Cross_Sectional_Momentum_in_the_Cryptocurrency_Market_with_IA.pdf
- Liu, Tsyvinski & Wu (NBER w25882): https://www.nber.org/papers/w25882.pdf
- Borri, Liu, Tsyvinski & Wu (2026): https://arxiv.org/pdf/2510.14435
- Schmeling, Schrimpf & Todorov, Crypto Carry (BIS WP 1087): https://www.bis.org/publ/work1087.pdf
- He, Manela, Ross & von Wachter: https://arxiv.org/html/2212.06888v5
- BitMEX Research Q2 2025: https://blog.bitmex.com/2025q2-derivatives-report ; Q3 2025: https://www.bitmex.com/blog/2025q3-derivatives-report
- Blockworks Research, Ethena (June 2026): https://blockworks-research.beehiiv.com/p/ethena-s-next-act
- ForkLog, Ethena capital (Mar 2026): https://forklog.com/en/ethenas-capital-plunge-signals-long-demand-shortage/
- The Block / K33 (Sept 2024): https://www.theblock.co/post/315831/perp-signal-bitcoin-bottom-bullish-year-end-k33
- Quantpedia, Bitcoin trend/mean-reversion revisited (2024): https://vvv.quantpedia.com/?p=35597 ; Seasonality: https://quantpedia.com/the-seasonality-of-bitcoin/
- Ledger, intraday Bitcoin (2021): https://ledger.pitt.edu/ojs/ledger/article/view/213
- Caporale & Plastun (2018): https://www.brunel.ac.uk/economics-finance-and-accounting/research/pdf/1801-Jan-GMC-Price-Overreactions-In-The-Cryptocurrency-Market.pdf
- Garcia Seuma (2026): https://arxiv.org/pdf/2608.03616
- Almeida, Grith, Miftachov & Wang: https://arxiv.org/html/2410.15195v2
- Hudson & Urquhart (2019): https://hull-repository.worktribe.com/OutputFile/2639834
- Gerritsen et al. (2020): https://research-portal.uu.nl/en/publications/the-profitability-of-technical-trading-rules-in-the-bitcoin-marke/
- Detzel et al. (2021): https://ideas.repec.org/a/bla/finmgt/v50y2021i1p107-137.html
- Islas Anguiano & García-Medina (2025): https://arxiv.org/html/2511.00665v1
- Rozario et al. (2020): https://ar5iv.labs.arxiv.org/html/2009.12155
- Molnar (2026): https://arxiv.org/pdf/2607.26188
- SMC/ICT evidence review incl. Mahadzva (2026): https://thortradecopier.com/blog/does-ict-smart-money-concepts-work
- Backtrex order-block backtest: https://backtrex.com/en/backtests/order-block-gbp-usd
- Kaminski & Lo: https://dspace.mit.edu/bitstream/handle/1721.1/114876/Lo_When%20Do%20Stop-Loss.pdf
- Alpha Architect on Han, Zhou & Zhu: https://alphaarchitect.com/taming-the-momentum-roller-coaster-fact-or-fiction/
- Setup4Alpha exit study: https://setup4alpha.substack.com/p/trailing-stop-vs-fixed-stop-tested
- MacLean, Thorp & Ziemba (2010): https://escholarship.org/content/qt5mr5k8qj/qt5mr5k8qj.pdf
