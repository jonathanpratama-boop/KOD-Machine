# E8: three candidate mechanisms and the one chosen (written 2026-10-16, before any E8 data was read)

Objective: an early warning for a large upward move that can support a profitable trade, with
win rate, losses and capital exposure measured. Nothing here claims that an edge exists.

## The assumption being challenged

E1 to E7 all asked one question: does a coin's or stock's **own** recent data (price, volume,
hourly order flow, its own futures positioning) warn of **its own** large move? The best signals
fired after the move had started, and the tested entries then bought from earlier buyers (E1's
next-close fills, E2's next-open entries). Repeated rejection of own-asset rules does not cover
information that comes from **other** assets, a different decision clock, or a different role.

## Candidate 1: peer spillover ("the next one in the group") — CHOSEN

**Mechanism.** When one asset reprices sharply for its own reasons (a narrative, a listing, a
group operator), investors with limited attention reach the closely linked assets later. In
crypto, traders rotate into "the next coin" of the same sector; in the IDX, group operators move
affiliated stocks in turns. The economics are the same as documented lead-lag between related
firms (gradual information diffusion across economically linked assets).

**Why an opportunity might survive costs.** The warned asset has *not yet moved*, so the entry is
not a chase: it can be filled at an ordinary price instead of joining a queue of late buyers.
Spot crypto costs are about 0.2% per side including slippage for liquid coins. The linkage is
cross-asset and changes over time, which is less likely to be fully priced than a single-asset
chart pattern.

**Coverage by earlier tests.** None. E1 to E7 conditioned only on each asset's own data. E6's
placebo and breakout arms, E7's crowding and E5's creep/quiet rows do not use another asset's move.

**Data.** Binance spot 1h klines with taker volume, 2020-04 to 2023-12, survivorship-complete
(46 coins delisted before 2023-12 included), checksum-verified, already on disk
(`data/manifests/binance_1h-20261015T182940Z.jsonl`). Point-in-time peer links can be measured from
trailing returns, so no sector list with hindsight is needed.

**Execution.** Hourly decisions, spot only, no leverage, 24/7 market without price limits.
Entry at the next hourly open is practical for an automated or alerted order.

## Candidate 2: informed-trader disclosures (US insider open-market buying, 13D stakes)

**Mechanism.** Insiders and activists know first; the law makes them disclose within days
(Form 4 within two business days). Small, low-attention firms are documented to under-react.

**Why not chosen now.** The data is free (SEC insider transaction data sets, full history,
delisted issuers included), but downloading it requires an SEC User-Agent with a contact, which
is still an open owner decision. The repository's US price panel is survivor-only, which biases
exactly the small issuers where this would matter. The documented effects are a few percent
over months, a weaker fit to an early moonshot warning. It remains the strongest follow-up if the
owner supplies the SEC contact and accepts a delisting-bound treatment.

**Coverage by earlier tests.** None (the ten-announcement earnings check was an access check).

## Candidate 3: exchange listing and attention events in crypto

**Mechanism.** Coins jump when a major exchange announces a listing or futures launch.

**Why not chosen.** The documented jump happens within seconds to minutes of the announcement,
where automated traders compete and an hourly alert arrives late. Historical announcement times
are not on disk and would require scraping an announcements service whose historical depth is
unverified. Detecting the leak before the announcement is an own-asset flow question that E6
already tested without success.

## Choice

Candidate 1, in crypto, on the data already on disk. It is the cheapest decisive test: it needs
no purchase, no new download and no owner decision, it reuses E6's loader, matched-control and
week-bootstrap code, and its result (pass, fail or inconclusive) settles a question no earlier
test covered. IDX group rotation was considered as the market for the same mechanism and set
aside: the IDX discovery panel lacks opening prices for 94% of rows in 2021-2022, so a
non-chasing next-open entry cannot be modelled there.

Validation note, recorded now: crypto 2023 was already inspected (E2 validation) and 2024 onward is
the sealed holdout. A discovery pass here can therefore only be confirmed prospectively.
