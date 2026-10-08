# Experiment E2: five-session repricings in US equities and crypto (KOD-GLOBAL-E2-v1)

Frozen before any analysis; machine-readable in `protocol.json`. The design is E1's
(`../E1/PROTOCOL.md`) applied to two more markets, changed only where the market differs:

| | US equities | Crypto |
|---|---|---|
| Data | Yahoo daily bars 2020-01-02 .. 2026-10-07, 5,705 Nasdaq/NYSE/NYSE American/Cboe common stocks (`panel_us-20261008T004105Z`) | Binance spot USDT pairs 2020-01-01 .. 2026-10-07, 683 bases incl. 190 delisted/halted (`panel_crypto-20261008T003354Z`) |
| Survivorship | **survivor-only** (today's listings) | delisted pairs included |
| Session | US trading day | UTC day |
| Price limits | none | none |
| Entry in the trading test | next session's open | next UTC day's open |
| Costs (assumed) | per side 1.5% <$1, 0.5% $1-5, 0.15% $5-20, 0.05% above | 0.2% per side |

Events: max close within 5 sessions ≥ +30 / +50 / +100% of the decision close. Discovery
2020-07-01 .. 2022-12-31, validation 2023, holdout 2024-01-01 onward (sealed: the study
market ends at the last validation session). First 100 events per market, five matched
controls each (same session, price band, liquidity quintile; no market cap in either
source). Weak signals as E1 minus the share-count and trade-count ones, plus the opening gap.
Detector: one of eleven fixed rules (`idxsig/rules/moonshot_g.py`, G1..G11) per market,
selected on discovery by E1's rule, frozen in a commit, then validated once on 2023 for
detection and through the harness for trading. A paper BUY later needs both to pass.
