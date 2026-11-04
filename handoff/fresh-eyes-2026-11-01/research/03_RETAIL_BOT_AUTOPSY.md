# Autopsy of the retail "AI trading bot" ecosystem

Web-only research (research sub-agent, 1 November 2026); no price data was downloaded and no return statistics were computed. Each section separates verified facts, self-reported claims and inference.

## 1. Open-source bot frameworks

Verified facts. Freqtrade's own FAQ does not claim that any strategy is profitable in live trading; it states that a strategy "will always be a gamble" and that backtesting assumes "All orders are filled at the requested price (no slippage)" and that stop-loss exits fill "exactly at stoploss price, even if low was lower". The hyperopt documentation warns that over-precise parameters "will usually result in overfitted results" and contains no explicit instruction to hold out an out-of-sample period. Freqtrade ships a dedicated `lookahead-analysis` subcommand because look-ahead bias "typically makes the strategy backtest look profitable, sometimes to extremes". Hummingbot's beginner document says market makers "bear the inventory risk, which is harmful when a market takes a directional run" and that 0.02% fees on USD 1,000,000 of monthly volume are about 2% of a USD 10,000 account per month. Hummingbot's 2019 liquidity-mining data: the top 10 of 68 participants accounted for 88% of filled volume; about 40% of new users were still running bots after one month. Gekko is deprecated/archived; Zenbot's maintenance status is uncertain. No framework publishes aggregate user profitability.

Inference. The frameworks are competent execution and research scaffolding. What kills users is documented by the frameworks themselves: hyperopt over one history without a held-out period; zero-slippage, perfect-stop backtests; changing pairlists; and fee drag that is material at volume.

## 2. Documented failures and successes

Verified facts.
- Quantopian (2011–2020): raised USD 48.8m, 210,000+ members, Point72 commitment up to USD 250m; returned investor money in 2020 because strategies underperformed; shut down November 2020. Its own study of 888 algorithms with six or more months out-of-sample (Wiecki et al.) found backtest Sharpe had little predictive value for out-of-sample Sharpe (R² below 0.025) and that "the more backtests a user ran, the bigger the difference between IS and OOS performance".
- QuantConnect Alpha Streams v1.0 (closed 2022): 80–90% rejection rate; the founder wrote that the distribution of alpha Sharpe ratios "shifted negative" relative to index constituents and that selecting only the top 5% still underperformed the S&P 500 once outliers were removed.
- Alpha Arena Season 1 (17 Oct–3 Nov 2025): six LLMs, USD 10,000 each, crypto perpetuals on Hyperliquid. Final: Qwen3 Max USD 12,231; DeepSeek USD 10,489; Claude Sonnet 4.5 USD 5,799; Gemini 2.5 Pro USD 5,445; Grok 4 USD 4,208; GPT-5 USD 4,126. Interim leaders changed repeatedly. Season 1.5 (US equities): Grok 4.2 the only consistently profitable model.
- Nathan Smith's ChatGPT micro-cap experiment (USD 100, June 2025–January 2026): week 4 widely reported at about +24%; week-26 update reported USD 82.88 against USD 111.68 for the S&P 500, maximum drawdown -50.33%, Sharpe -0.43. Coverage occurred at the peak.

Self-reported claims (no broker statements): a two-year systematic trader whose first backtest was "too good to be true" because of bugs; ProRealCode traders reporting +54% in 2024 then flat in 2025 with a coding error turning a planned EUR 100 loss into about EUR 800; an r/algotrading six-strategy bot "up about USD 25" on USD 1,000 after 480 paper trades, with commenters estimating about 2,500 trades needed to separate edge from noise; a six-month grid-bot run described as "roughly flat-to-modest after fees".

Inference. The only large-sample evidence on retail-built strategies says the population's realised out-of-sample Sharpe is centred near or below zero and backtest quality is almost uninformative about live quality. The two best-documented LLM experiments show the same pattern: a strong early print that attracts coverage, followed by reversal.

## 3. Grid, DCA and market-making bots

Verified facts. Vendors document grid and DCA bots as range strategies; when price exits the lower band the bot is fully long with no further buying power; 3Commas DCA allows a safety-order volume scale above 1.0 (each averaging order larger than the last).

Inference. A grid bot is a short-volatility, long-inventory position: small gains while price oscillates inside the range and an unhedged directional position when it leaves. A DCA bot with volume scale above 1.0 is a martingale.

## 4. Statistical failure mechanisms

Verified facts.
- Bailey and López de Prado (2014): Deflated Sharpe Ratio. Bailey, Borwein, López de Prado and Zhu (2015): hold-out methods are "unreliable and inaccurate in the context of investment backtests"; "as long as the researcher tries more than one strategy configuration, overfitting is always present"; optimising a pure random walk produced in-sample Sharpe 1.27 with 55% probability of backtest overfitting.
- Suhonen, Lennkh and Perez (215 bank alternative-beta indices): median 73% deterioration in Sharpe between backtest and live; only 8.4% had live Sharpe at or above backtest; 30% had negative live Sharpe; the most complex strategies suffered more than 30 percentage points of additional haircut.
- Look-Ahead-Bench (Benhenda, Jan 2026): standard LLMs' simulated alpha decayed by more than 15 percentage points between an in-training-window period and a post-cutoff period. The Alpha Illusion (Ye et al., May 2026): reported alpha from agent frameworks "should not be treated as deployment evidence". BlindTrade (Jeon and Lee, Mar 2026): an anonymised LLM-plus-RL design reports Sharpe 0.69 against SPY's 1.06 over 2024–2025, no live deployment.
- Survivorship: a universe built from today's active symbols makes strategies "look more liquid, less volatile, and more profitable than they were in practice" (CoinAPI).
- Venue risk: on 19 May 2021 Binance halted retail trading during a roughly 30% Bitcoin fall; the futures price gap between Binance and other venues was about seven times its reference level (IWH 2022). On 1 April 2025 ACT fell as much as 52% in 30 minutes on Binance following leverage-tier changes.

Inference. A retail workflow that runs hyperopt over a survivor universe with zero-slippage fills, judges by in-sample Sharpe, and re-tunes on the same "holdout" after a bad month combines every mechanism above. LLM-in-the-loop systems add one more: a backtest inside the model's training window is contaminated by construction.

## 5. Trading psychology for systematic retail traders

Verified facts. Barber and Odean (66,465 US households, 1991–1996): the average household turned over more than 75% of its portfolio annually and earned 16.4% net against 17.9% for the market; the highest-turnover quintile lagged by 46 bps per month; gross returns barely differed across turnover quintiles, so the gap was trading cost. Investors sell winners twice as often as losers (disposition effect). Barber, Lee, Liu and Odean (Taiwan, 1992–2006): aggregate day-trader performance net of fees was negative in every one of 15 years; less than 3% were predictably profitable; survival at one, two and three years was 44%, 24% and 15%; traders who had previously been unprofitable with 50+ days of experience still had a 95.3% probability of day trading again in the next 12 months.

Inference on machine design. Pre-committed rules changed only through a versioned, dated process; hard position and daily-loss caps enforced outside strategy code; mandatory logging of every intended order before submission; a cooling-off rule forbidding parameter changes within a defined number of trades or days after a loss; "no trade" and "reduce exposure" as first-class outputs; and a pre-registered kill criterion. The Taiwan persistence numbers indicate the dominant retail failure is continuing a bad system, not quitting a good one.

## 6. Security and operational hygiene checklist

Verified incidents. December 2022: about 100,000 3Commas API keys leaked; users reported about USD 6m in losses from unauthorised trades. March 2018: compromised Binance accounts connected through API keys had altcoins market-sold and Viacoin bought, moving VIA roughly 10,000% within minutes. Both show trade-only keys can still be monetised by pumping an illiquid asset the attacker already holds.

Checklist.
1. Keys: trade-only, withdrawal disabled; IP allow-listed; one key per bot and purpose; sub-account holding only the capital at risk; treat any key that has touched a repository or image as compromised.
2. Secrets: environment variables or a secret manager; `.gitignore` before the first commit; scrub verbose logs; pin dependencies.
3. Guardrails outside strategy code: maximum order size, daily notional and daily loss cap; kill switch triggerable without a deploy; dry-run as default.
4. Order handling: client-generated idempotent order identifiers; log the intended order before sending; reconcile open orders, positions and balances against the exchange on every start and on a timer, halt on mismatch; persist state for crash recovery.
5. Rate limits and venue failure: back off; treat exchange outages as a risk event; assume single-venue prices during an outage may be unreliable.
6. Monitoring: alert on balance or order activity the bot did not originate; review key-usage logs; rehearse key revocation.
7. Testnet and paper trading before capital, understanding that paper fills overstate liquidity.

## What separates the few who survive

1. They treat the backtest as a hypothesis with a known false-discovery rate (73% median live haircut; 8.4% match their backtest; backtest Sharpe R² below 0.025) and run fewer, pre-registered tests.
2. They keep the strategy simple and explicable.
3. They separate the risk layer from the alpha layer: let any model extract information upstream and let deterministic code own calibration, sizing and execution.
4. They do not use grid or DCA bots as passive income.
5. They engineer against themselves: pre-commitment, external caps, mandatory logging, abstention as an output, pre-registered kill criterion.
6. They verify: not one public success story reviewed provides broker statements or an audit.

## Sources

- Freqtrade FAQ / backtesting / hyperopt / lookahead: https://www.freqtrade.io/en/stable/faq/ ; https://www.freqtrade.io/en/stable/backtesting/ ; https://www.freqtrade.io/en/stable/hyperopt/ ; https://www.freqtrade.io/en/stable/lookahead-analysis/
- Hummingbot misconceptions: https://docs.hummingbot.org/academy-content/top-beginner-misconceptions-about-market-making/ ; community market making: https://hummingbot.org/blog/does-community-based-market-making-work/
- Quantopian: https://en.wikipedia.org/wiki/Quantopian ; Robot Wealth: https://robotwealth.com/my-thoughts-on-quantopians-closing/ ; Quantpedia on Wiecki et al.: https://quantpedia.com/quantopians-academic-paper-about-in-vs-out-of-sample-performance-of-trading-alg/
- QuantConnect: https://www.quantconnect.com/forum/discussion/6737/9-ways-to-get-your-alpha-rejected/ ; https://www.quantconnect.com/forum/discussion/13441/alpha-streams-refactoring-2-0/
- Alpha Arena: https://decrypt.co/345006/ai-crypto-trading-showdown-deepseek-grok-winning-gemini-implodes ; https://forklog.com/en/ai-model-grok-4-2-triumphs-in-trading-tournament/
- Smith experiment: https://www.benzinga.com/markets/equities/25/08/46783783/redditors-100-chatgpt-day-trading-experiment-trounces-two-benchmark-indexes-with-24-returns-here ; https://hackernoon.com/can-chatgpt-outperform-the-market-week-26
- Kunisetty: https://venkatkunisetty.substack.com/p/how-we-built-algorithmically-traded ; ProRealCode: https://www.prorealcode.com/topic/your-trading-year-2025/ ; grid bot: https://dev.to/joe_hans_6c082d6c1caf189f/i-ran-a-gateio-btc-grid-bot-for-6-months-real-returns-and-3-fatal-mistakes-2i1p
- Bailey & López de Prado: https://papers.ssrn.com/abstract=2460551 ; Probability of Backtest Overfitting: https://carmamaths.org/jon/backtest2.pdf
- Suhonen et al. via Alpha Architect: https://alphaarchitect.com/looking-at-alternatives-avoid-complexity-and-magical-backtests/
- Look-Ahead-Bench: https://arxiv.org/pdf/2601.13770 ; The Alpha Illusion: https://www.alphaxiv.org/abs/2605.16895 ; BlindTrade: https://arxiv.org/pdf/2603.17692
- CoinAPI survivorship: https://www.coinapi.io/blog/how-to-eliminate-survivorship-bias-in-crypto-backtesting
- IWH, Binance 19 May 2021: https://www.iwh-halle.de/en/publications/detail/bitcoin-flash-crash-on-may-19-2021-what-did-really-happen-on-binance
- Barber & Odean: https://faculty.haas.berkeley.edu/odean/Papers%20current%20versions/Individual_Investor_Performance_Final.pdf ; Taiwan day traders: https://faculty.haas.berkeley.edu/odean/papers/day%20traders/day%20trading%20and%20learning%20110217.pdf
- CCXT API key security: https://docs.ccxt.com/blog/api-key-security ; Kraken: https://docs.kraken.com/exchange/guides/rest/api-keys ; 3Commas leak: https://www.bleepingcomputer.com/news/security/crypto-platform-3commas-admits-hackers-stole-api-keys ; Binance 2018 VIA: https://financemagnates.com/cryptocurrency/news/binance-suspends-withdrawals-trading-bot-hacked-users-accounts
