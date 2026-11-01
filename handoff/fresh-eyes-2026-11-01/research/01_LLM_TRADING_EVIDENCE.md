# LLMs in trading: what the 2023–2026 evidence shows

Literature and web review only (research sub-agent, 1 November 2026). No price data was downloaded and no return statistics were computed. All figures are as reported by the cited sources. Statements labelled "Inference" are the reviewer's judgement, not sourced fact.

## Verdict

Verified fact: the strongest academic result for direct LLM return forecasting (Lopez-Lira and Tang, GPT-4 scoring of news headlines, October 2021 to May 2024) survives post-cutoff testing but is a short-horizon, small-cap-concentrated, high-turnover signal whose paper returns fall from roughly 700% cumulative at zero cost to unprofitable at 20 basis points round trip, and whose annualised Sharpe decayed from 6.54 in Q4 2021 to 1.22 in January to May 2024. The agentic "LLM trader" literature (FinMem, TradingAgents, FinAgent, QuantAgent, FinCon, FLAG-Trader) has been audited by two 2025–2026 papers (Profit Mirage; The Alpha Illusion) and found to lose 50–72% of reported return and Sharpe once the test window is moved past the backbone model's training cutoff; none of these papers models transaction costs; the TradingAgents buy-and-hold baseline for AAPL has been shown to have the wrong sign. Live, real-money evidence (Alpha Arena, October 2025 onward) shows most frontier models losing money. The one audited real-money LLM-assisted vehicle located (Intelligent Livermore ETF) trailed the S&P 500 by about 3.7 percentage points in its first nine and a half months.

Inference: the comparative advantage of LLMs lies upstream of the trade (reading unstructured text at scale, classification, consistent labelling, code generation) and not in the numerical forecasting or position-sizing step.

## 1. Table of studies

| Study | Year | Market / sample | Claimed result | Costs included? | OOS / live? | Replication / audit status |
|---|---|---|---|---|---|---|
| Lopez-Lira & Tang, "Can ChatGPT Forecast Stock Price Movements?" (arXiv 2304.07619, v6 Oct 2025) | 2023–2025 | US stocks, 4,123 names, 159,137 firm-headline-days, Oct 2021–May 2024 | GPT-4 headline scores predict next-day drift; drift Sharpe 2.97 (overnight), 2.63 (intraday); ~700% cumulative gross; Sharpe by year 6.54, 3.68, 2.33, 1.22 | Yes, as fixed round-trip charges: >300% at 5 bps, >100% at 10 bps, unprofitable at 20 bps; daily turnover ~190% | OOS relative to Sept 2021 cutoff; not live | Glasserman & Lin (2023) find in-sample "distraction" bias larger than look-ahead; Gao, Jiang & Yan (2025/26) find part of the signal is amplified where the model recalls the outcome, but signal persists post-cutoff |
| Glasserman & Lin (arXiv 2309.17322) | 2023 | US headlines | Anonymising company names improves in-sample performance; look-ahead not a concern OOS, distraction is | Not the focus | Both | Methodological |
| Sarkar & Vafa, "Lookahead Bias in Pretrained Language Models" (ICML 2025 workshop) | 2025 | Earnings-call risk factors; elections | Leakage of future information into "historical" forecasts; prompting-based fixes insufficient | n/a | n/a | Methodological |
| Gao, Jiang & Yan, "Detecting Lookahead Bias in LLM Forecasts" (arXiv 2512.23847) | 2026 | Bloomberg headlines 2012–2023; placebo 2024 | LLM x lookahead-propensity interaction positive in-sample, insignificant post-cutoff; signal survives post-cutoff at reduced strength | No | Post-cutoff placebo | New; AEA 2026 |
| Chen, Kelly & Xiu, "Expected Returns and Large Language Models" | 2024 WP | News in 16 markets, 13 languages | LLM embeddings beat word-based sentiment; discussant cites net Sharpe ~1.5 at 10/20 bps | Discussant-level only | In-sample ML cross-validation | Discussant critiques label construction and timing |
| Jha, Qian, Weber & Yang, "ChatGPT and Corporate Policies" (NBER w32161) | 2024 | US earnings calls | ChatGPT "investment score" predicts capex up to nine quarters ahead | Not the focus | In-sample panel | No trading claim |
| Kim, Muhn & Nikolaev, "Financial Statement Analysis with LLMs" (arXiv 2407.17866) | 2024 | Anonymised US financial statements | GPT-4 beats analysts on earnings direction | Not stated | In-sample | WITHDRAWN (v3, 20 Feb 2025) after data inconsistencies. Do not cite. |
| FinMem (arXiv 2311.13743) | 2023–24 | 5 US stocks; test Oct 2022–Apr 2023 | TSLA 61.78% / Sharpe 2.68 vs buy-and-hold -18.63% | No | Test window predates GPT-4 cutoff; risk setting selected on test set | Profit Mirage: total return decays 71.85% post-cutoff |
| TradingAgents (arXiv 2412.20138) | 2024–25 | AAPL, GOOGL, AMZN; 2024 windows | AAPL 26.62% / Sharpe 8.21 vs buy-and-hold -5.23% | No | Backbone cutoff not discussed; not live | AAPL buy-and-hold was about +9.1%, not -5.23%; Profit Mirage: Sharpe decays 55.68% post-cutoff; Alpha Illusion: gross Sharpe 0.43 falls to 0.22 net |
| FLAG-Trader (arXiv 2502.11433) | 2025 | 5 US stocks 2020–21; BTC Apr–Nov 2023 | LLM policy fine-tuned with PPO "consistently outperforms" | No | Test windows inside backbone training period | Own tables mixed: UVV Sharpe 1.463 vs buy-and-hold 2.112 |
| StockBench (arXiv 2510.02209) | 2025 | 20 DJIA stocks, Mar–Jun 2025 | Best models +2.5% vs passive +0.4%; no model beat baseline in downturn sub-window | No | Post-cutoff window; not live | Single short window |
| Profit Mirage (arXiv 2510.07920) | 2025 | NASDAQ-100; GPT-4o backbone | Sharpe decay 51–62% and return decay 50–72% for five agent frameworks post-cutoff | Not the focus | Pre vs post cutoff | Audit paper |
| The Alpha Illusion (arXiv 2605.16895) | 2026 | Reproduction harness 2025–26 | Gross-alpha illusion; Sharpe standard errors roughly equal to reported Sharpe; prior lock-in; poor calibration | Yes | Reproduction | Audit paper; proposes six reporting protocols |
| Alpha Arena Season 1 (nof1) | 18 Oct–3 Nov 2025 | Crypto perps on Hyperliquid, $10,000 real per model, 8–20x leverage | Qwen3 Max $12,231; DeepSeek $10,489; Claude Sonnet 4.5 $5,799; Gemini 2.5 Pro $5,445; Grok $4,208; GPT-5 $4,126 | Real execution | Live, real money | Two weeks; organiser gave models mainly numerical time series |
| Alpha Arena Season 1.5 (nof1) | Nov–Dec 2025 | US stocks, four prompt regimes | Grok 4.20 average +12%, profitable in all four; a model was profitable in 6 of 32 result sets; pool lost about a third | Real | Live | Qwen placed 1,418 trades vs Grok 158 under the same prompt |
| TradeRank Arena | Jan–Sep 2026 | 10 crypto + 50 US equities, paper $10,000 | 46.2% of model-seasons profitable | None | Paper | Self-reported |
| Finder.com "ChatGPT fund" | Mar 2023–Mar 2026 | 38 UK-listed stocks, theoretical | +57.8% vs 36.49% fund average | No | Paper, forward | Unaudited; no S&P 500 comparison |
| Intelligent Livermore ETF (LIVR) | Sep 2024–Jun 2025 | Global equities, LLMs with human analyst | +7.52% vs S&P 500 +11.26% | Yes (live fund) | Live, audited | n/a |

## 2. Direct forecasting: what was claimed and what survived

Lopez-Lira and Tang remains the anchor result. The headline "about 90% hit rate" refers to the non-tradable initial reaction; the tradable drift hit rate is 58% (overnight) and 55% (intraday). The short leg carries most of the drift return (26 bps per day versus 8 bps for the long leg). Predictability concentrates in small stocks and negative news.

Two contamination literatures exist. Glasserman and Lin show in-sample results are more distorted by "distraction" (the model's prior knowledge of the named firm) than by direct look-ahead. Gao, Jiang and Yan find the LLM signal is amplified precisely where the model can recall the outcome, with the amplification vanishing post-cutoff. Profit Mirage finds 50–72% decay in return and Sharpe when the window moves from 2021 (inside GPT-4o's training data) to late 2024, despite similar market returns.

No agentic LLM-trader paper models transaction costs. The Alpha Illusion adds them and reports TradingAgents' Sharpe falling from 0.43 gross to 0.22 net, and estimates the standard error of reported Sharpe ratios at roughly the size of the Sharpe itself.

Inference: the literature has moved from "LLMs predict returns" (2023) to "a modest post-cutoff signal exists in news text, concentrated in small caps and shorts, with high turnover, and most of the agentic alpha is contamination or unpriced friction" (2025–26).

## 3. Live and audited real-money records

Alpha Arena (nof1) is the only widely reported live, real-money, publicly logged LLM trading exercise. Season 1: four of six models lost between 42% and 59%. Season 1.5: a model finished in profit in 6 of 32 result sets. Organiser commentary attributes losses to overtrading, mistimed entries, poor sizing and inability to weight variables.

Intelligent Livermore ETF returned 7.52% from inception (17 Sep 2024) to 30 Jun 2025 against 11.26% for the S&P 500, per its audited shareholder report.

Bloomberg (May 2026) quotes a former Coatue quant stating that no AI trading bot he tracks has shown a lasting edge, and reports that JPMorgan and Balyasny use LLMs for news parsing and memo drafting with a human in the loop.

Not found: any hedge fund or regulated manager publishing an audited track record attributable to autonomous LLM trading decisions.

## 4. Comparative advantage of LLMs: evidence-backed

- Text-to-signal extraction at scale: LLM embeddings outperform dictionary methods across 16 markets and 13 languages (Chen, Kelly & Xiu); GPT-4 beats FinBERT and smaller models with ability rising in model size (Lopez-Lira & Tang).
- Labelling consistency: Wang and Wang (2025) found Fleiss' kappa 0.93–0.97 on binary finance classification across 50 repeated passes and LLMs more consistent than human annotators on 52% of Financial PhraseBank sentences; consistency weaker for numerical earnings predictions.
- Risk-interval calibration: LLM 80% confidence intervals for returns better calibrated than human survey intervals, though point forecasts over-extrapolate recent returns (Chen, Green, Gulen & Zhou).
- Herding: LLM agents rely more on private information than humans in herding experiments and herd only when prompted to maximise profit (Hansen & Lee, FEDS 2025-090).
- Inference: code generation for research pipelines and hypothesis generation are plausible advantages, but no controlled study measures hit-rate of LLM-generated hypotheses against a human quant baseline.

## 5. Failure modes

- Training-cutoff contamination (50–72% decay post-cutoff).
- Omitted frictions (no agentic paper models costs; headline strategy breaks even at 10–20 bps round trip at ~190% daily turnover).
- Baseline and arithmetic errors in published papers.
- Short windows and unreported variance (82-day, three-month, two-week evaluations).
- Test-set selection (risk setting chosen on test period).
- Over-extrapolation of recent returns; "parametric prior lock-in".
- Overtrading and prompt sensitivity in live settings (1,418 vs 158 trades under identical instructions).
- Evidence fragility: the highest-profile "LLM beats analysts" paper was withdrawn.

## 6. Open gaps (inference)

1. Date-restricted backbones in trading backtests: no agentic trading paper has been re-run on a model pretrained only on pre-period text.
2. Long live records: longest real-money LLM record located is under two years (LIVR).
3. Costed, dynamic-universe, survivorship-free evaluation: not adopted by any system in the table.
4. Capacity and crowding: no study measures LLM-signal crowding directly.
5. Markets outside US large caps and crypto: no LLM trading study on Indonesian or other frontier-market text located.
6. LLM-as-extractor plus classical model as allocator: pointed to by two audit papers, unreplicated.
7. Herding under common backbones in a live venue: theorised, not measured.

## Sources

- Lopez-Lira & Tang: https://arxiv.org/abs/2304.07619
- Glasserman & Lin: https://arxiv.org/abs/2309.17322
- Sarkar & Vafa: https://icml.cc/virtual/2025/50857
- Gao, Jiang & Yan: https://arxiv.org/abs/2512.23847
- Chen, Kelly & Xiu discussion: https://jacobslevycenter.wharton.upenn.edu/wp-content/uploads/2024/09/ExpectedReturnAndLLM_Discussion_SophiaZhengziLi_NoPause.pdf
- Jha et al., NBER w32161: https://www.nber.org/papers/w32161
- Kim, Muhn & Nikolaev (withdrawn): https://arxiv.org/abs/2407.17866v3
- FinMem: https://arxiv.org/abs/2311.13743
- TradingAgents: https://arxiv.org/html/2412.20138v4 ; baseline critique: https://dev.to/trow126/the-most-starred-llm-trading-paper-claims-buy-and-hold-lost-523-it-actually-gained-912-1jj6
- FLAG-Trader: https://arxiv.org/abs/2502.11433
- StockBench: https://arxiv.org/html/2510.02209v1
- Profit Mirage: https://arxiv.org/abs/2510.07920
- The Alpha Illusion: https://www.alphaxiv.org/abs/2605.16895v1
- Chen, Green, Gulen & Zhou: https://www.arxiv.org/abs/2409.11540
- Wang & Wang: https://arxiv.org/pdf/2503.16974v2
- Hansen & Lee, FEDS 2025-090: https://www.federalreserve.gov/econres/feds/financial-stability-implications-of-generative-ai-taming-the-animal-spirits.htm
- Alpha Arena S1: https://forklog.com/en/four-out-of-six-ai-models-suffer-losses-in-trading-tournament/ ; S1.5: https://forklog.com/en/ai-model-grok-4-2-triumphs-in-trading-tournament/
- Bloomberg via Business Standard (7 May 2026): https://www.business-standard.com/markets/news/ai-bots-auditioning-for-wall-street-trading-are-mostly-losing-money-126050701793_1.html
- Intelligent Livermore ETF shareholder report: https://etfarchitect.com/wp-content/uploads/compliance/etf/TSR/LIVR_TSR-AR.pdf
- Finder.com tracker: https://finder.com/uk/share-trading/share-trading-research/ai-investing
