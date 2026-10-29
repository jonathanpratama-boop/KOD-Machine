# Decision note 1: BKU (BankUnited, Inc.), Schedule 13D by HoldCo Asset Management

**Set:** `CAT-SEC13D-0000921895-26-002864`, family SEC13D, sealed 2026-10-28T23:03:12Z, record hash
`dd2d6840461ea12e61c55c21abe27595802a871958080353650b1d71284fc345`, coverage FIRE, entry at the 2026-10-29 opening
print, window H20 (20 sessions), cone priors GAIN0_20 0.55, BEATS_TWINS_20 0.50, FADE10_20 0.50, RUN30_20 0.50.
**Selection rule:** PROTOCOL.md, the first FIRE set of the first counted US family. **Written by:** the session (Claude),
applying the six questions of the owner's 2026-10-29 Harry-lens paste. This note changes nothing in the register.

## Timing disclosure

Analysis on 2026-10-29, ending 06:05 UTC by the scheduler's clock (the one timestamp in this analysis read from a
clock rather than estimated); the reads below were made in the roughly forty minutes before it, in the order listed,
and the filing itself had been read at about 00:40 UTC in an earlier step of the same session. The set's entry (the
13:30 UTC open) had not happened. The last price seen is the 2026-10-28 close, 42.81; no after-hours or pre-market quote
was read. Sources:

| Source | What it gave |
|---|---|
| The filing, `primary_doc.xml` of accession 0000921895-26-002864 (18,448 bytes; Item 4 sha256 `281165c1...` as the set records) | Items 3 to 7, cover page |
| The sealed set record in `paper/catalysts.jsonl` | signal features, twins, cone, coverage inputs |
| BKU submissions JSON (CIK 1504008) | filings since September |
| SEC companyfacts, CIK 1504008 | equity and share counts to 2026-06-30 |
| `idxsig/paper.py` PAPER-POLICY-v5 | the 5% planned-stop constraint |
| Reuters via itiger, 2025-11-06 | Columbia and First Interstate withdrawals |
| Sullivan & Cromwell memo, Jan 2026; Banking Dive; American Banker (search summaries) | Comerica vote and lawsuit |
| BKU 8-K of 2026-10-21, Exhibit 99.2 (Q3 2026 presentation) | shares outstanding, book values, buybacks, ratios |
| Motley Fool via Yahoo Finance, 2026-01-01 | HoldCo's 13F stake as of 2025-09-30 |
| MarketMinute syndicated piece, 2026-01-01 (search summary only; page not read) | "Florida premium" commentary, **unverified** |

## 1. What changed, who can act, when was it knowable

**Completed facts (the filing).** HoldCo Asset Management, LP (Vikaran Ghei, Michael Zaitzeff; HoldCo Opportunities
Fund V, L.P.) filed an original Schedule 13D on BankUnited, accepted 2026-10-28 16:24 New York, after the close. It
reports 3,535,282 shares, 5.0% of class, bought for about USD 135,628,306 including commissions (USD 38.36 a share),
"with working capital". Item 5(c): "No Reporting Person has effected any transactions in the Shares during the past
sixty days." Date of event 2026-10-21. No previous 13D. Item 4 says the shares were bought as "undervalued", that the
Reporting Persons "have engaged, and expect to continue to engage, in discussions with certain members of the Issuer's
management team and Board of Directors regarding opportunities to enhance shareholder value", and lists the standard
menu of possible actions (purchases or sales, communications with the board and other stockholders, "potential business
combinations or dispositions", board composition, capitalization) while stating that no Reporting Person "has any present
plan or proposal" beyond that. The register's keyword tag read "board, director"; the strong-intent list of SEC13D_V2
would have found nothing. Read in full, Item 4 is an options list, not a commitment.

**What is not new.** The stake is old. A 13F filed 2025-11-13 showed 936,900 BKU shares at 2025-09-30 (Motley Fool,
2026-01-01). A 13F filed 2026-05-15 showed about 3.54 million shares at 2026-03-31 (search summary of a 13F
aggregator, consistent with today's 3,535,282). The filing's own sixty-day statement puts the last purchase before
2026-08-29. So the position has been public for eleven months and unchanged for at least seven.

**Why it was filed now.** BankUnited repurchased USD 97.0 million of stock in Q3 2026 and USD 206.7 million in the
nine months, taking shares outstanding from 71,232,249 (2026-08-04, 10-Q) to 70,188,199 at 2026-09-30 (Exhibit 99.2,
8-K of 2026-10-21). HoldCo's unchanged 3,535,282 shares were 4.96% of the August count and are 5.04% of the September
count. The 5% threshold was crossed by the issuer's buyback, not by HoldCo buying. The 2024 rule gives five business
days from the event: 2026-10-21 (the Q3 release) plus five business days is 2026-10-28, the filing date. The trigger was
mechanical. The choice that carries information is 13D rather than 13G: a holder with no intent to influence control
could have filed the passive form.

**When knowable.** The crossing was computable on 2026-10-21 from the 8-K share count and the public 13F count. The
register saw it seven days later, when the filing arrived.

**The actor.** HoldCo is a bank-specialist activist with a sale playbook. Comerica, 2025: a presentation in July
urging a sale; Comerica agreed in October to be acquired by Fifth Third; HoldCo then opposed the terms, sued in
Delaware, urged a no vote; the Chancery court found no colorable claim, ISS backed the deal, shareholders approved it on
2026-01-06 and it was set to close 2026-02-01. Columbia Banking and First Interstate, November 2025: HoldCo withdrew
threatened director nominations after both CEOs said publicly they had no interest in M&A; "neither executive made firm
promises" (Reuters). Eastern Bankshares: urged to explore a sale; the board said it is not for sale. Capitol Federal: a
13D in May 2026, outcome not checked here. Pattern: HoldCo reliably creates public pressure with 1% to 5% stakes; it does
not control outcomes, and where a sale happened it disputed the terms. At BKU it holds 5.04%, more than at Comerica.

## 2. Economic consequence, and what could prevent it

The mechanism HoldCo pursues is a sale of the bank at a control premium. For a BKU common shareholder the value is the
premium over the standalone price; there is no dilution, debt or flow effect in the filing itself. Standalone, BKU is a
USD 34.9 billion-asset bank (2026-06-30) earning a 9.6% GAAP return on equity, net interest margin 3.16%, CET1 12.1%,
buying back its own stock at about 1.0 to 1.1 times tangible book (Q3 2026 release). At that return the stock earns
roughly its cost of equity, which is why it trades near book; absent a change in control or in returns there is no
obvious re-rating to unlock.

What could prevent the consequence: the board declining to run a process (its stance is not in any filing read here; a
secondary write-up says management "remains committed to its standalone strategy", unverified); no acquirer willing to
pay a premium for a Florida and New York franchise of this size (unknown; the same write-up names SouthState as a
possible acquirer, which is analyst speculation); HoldCo's limited leverage at 5%; the timetable. Comerica took three
months from presentation to agreement, and Comerica was under wider pressure. A 20-session window is far shorter than
the mechanism. Within 20 sessions the realistic events are a HoldCo letter or presentation, a BKU response, or silence.

Unknown and left unknown: what an acquirer would pay (no comparable-deal multiple is sourced here); the opening of
BKU's 2027 nomination window; whether HoldCo has nominees ready.

## 3. What the price already appears to assume

Observable only. Close 42.81 on 2026-10-28, down 1.5% on the day before the filing arrived; up 1.7% over five
sessions and 1.4% over twenty; 11.4% below its sixty-session high; volume 1.04 million against a twenty-day average of
about 1.0 million (ratio 1.06). No run-up and no unusual volume into the filing, consistent with a filing nobody
needed to anticipate by buying.

| Ratio at 42.81 | Value |
|---|---|
| Price to tangible book (TBV 39.10 at 2026-09-30) | 1.09x |
| Price to book (40.21) | 1.06x |
| Price to annualised Q3 EPS (1.01 x 4) | 10.6x |
| Market value (70,188,199 shares) | USD 3.00 billion |
| Price over HoldCo's cost (38.36) | +11.6% |

A bank at 1.1 times tangible book with a 9.6% return on equity is priced close to its standalone worth. The price may
already carry some premium for HoldCo's known presence since January; that part cannot be separated here and is left
unknown. The pre-filing accumulation that the literature finds before activist 13Ds (Collin-Dufresne and Fos 2015) is
absent here by the filing's own statement. The reaction to the filing itself, if any, occurs at the 2026-10-29 open,
which the register's plan buys into and this note could not see.

## 4. What remains for us on the register's plan

The plan buys the opening print of 2026-10-29 and sells at the close of the 20th session after entry; costs under the
US profile are 0.05% a side above USD 20 plus the SEC fee on the sale, about 0.1% round trip. Whatever the filing is
worth on day one is in the opening gap, before the plan. What remains is the drift after the open. The literature's mean
post-filing drift is a few percent for the average activist 13D (Brav, Jiang, Partnoy and Thomas 2008), with the
effect concentrated in filings that announce a specific demand; this one announces none, the stake is static, and the
actor's next step is months away. Downside: BKU fell more than 11% within the last sixty sessions, so a 10% fall in
twenty is not rare for this name, but with 12.1% CET1 and no credit event in the Q3 release nothing in the filing points
to one.

A limitation of the register surfaced by this case: the five twins (STRA, NHC, BCC, SLG, PHIN) are matched on size,
liquidity, momentum and drawdown, not industry. None is a bank. BEATS_TWINS_20 for BKU therefore measures a bank against
a mixed basket over twenty sessions, which is mostly a sector bet. Industry matching for financials is a candidate
change for a later family version, not for this one.

**Price view (this note's probabilities, scored against the register's outcomes; the sealed priors stand):**

| Statement | Family prior | This note | Why |
|---|---|---|---|
| GAIN0_20 | 0.55 | 0.55 | no case-specific reason to move it; the drift is small and the gap is not ours |
| BEATS_TWINS_20 | 0.50 | 0.50 | non-bank twins; no identified edge over them |
| FADE10_20 | 0.50 (uninformed) | 0.12 | a 10% fall needs a sector or credit shock; none indicated |
| RUN30_20 | 0.50 (uninformed) | 0.02 | needs a takeover announcement at a large premium within 20 sessions |

The honest finding of this step: reading the filing fully did not produce a case-specific edge for the register's plan.
It produced two abstentions the register does not make (a disclosure-driven 13D with a static stake; non-bank twins) and
a timing observation (the crossing was computable a week earlier).

## 5. Mandate fit

The owner's mandate (PAPER-POLICY-v5 in `idxsig/paper.py`: a planned stop at most 5% from entry, the stop at the
signal session's low; the paste's doctrine GD-1.1: 1 to 5 sessions) is not what the register's H20 plan tests. For this
case: the signal-session low is 42.265, so the highest entry that meets the 5% rule is 44.49. If the open gaps above
that, the mandate cannot be met and there is no trade. Below it, the stop sits 1.3% to 5% under the entry. Over 1 to 5
sessions the only identified repricing is the opening reaction, which precedes the entry; after it, nothing in this
analysis gives the trade an edge over noise.

**Mandate view:** a 1 to 5 session long from the 2026-10-29 open with that stop makes money with probability 0.50;
the recommendation under the mandate is PASS, no trade. If the H20 yardstick later shows an edge for this family, that
would establish a 20-session opportunity, which is a different product from the mandate and would need a deliberate
mandate decision.

## 6. What would prove this reading wrong (actor predictions, scored separately from the price)

| Id | Statement | Probability | Resolves by | Source |
|---|---|---|---|---|
| A1 | HoldCo files a 13D/A on BKU, or BKU files an 8-K or press release naming HoldCo (letter, presentation, nomination notice, cooperation agreement or strategic review) | 0.55 | 2026-12-27 | EDGAR, CIK 1504008 and CIK 1724246 |
| A2 | A 13D/A shows HoldCo above 5.04% through purchases listed in its Item 5(c), not through buybacks | 0.20 | 2026-12-27 | EDGAR |
| A3 | BKU announces a definitive agreement to be acquired, or a formal strategic review | 0.15 | 2027-04-30 | BKU 8-K Item 1.01 or 8.01 |
| A4 | HoldCo reports a stake below 5% or switches to Schedule 13G | 0.10 | 2026-12-27 | EDGAR |

The reading "a disclosure-driven filing by a persistent but not controlling activist, months from any outcome" is wrong
if A1 resolves true within 20 sessions with a specific demand (then the register's own GAIN0_20 outcome will show whether
the market cared), or if A3 resolves true within the window (then the price view above was far too low). It is also
wrong if BKU outperforms its twins while HoldCo is silent and bank indices are flat, which would mean the filing itself
re-rated the stock after the open. If BKU outperforms while bank indices rise, that is sector beta, not the mechanism.

## What this case says about the sensor

1. The sensor fired on a filing that was computable seven days earlier from two public numbers (the issuer's new share
   count and a 13F count). A "passive crossing" watch for 13F holders near 5% at issuers that buy back stock is a
   hypothesis worth pre-registering; it is not used here.
2. "No transactions in the past sixty days" plus an unchanged 13F count separates a disclosure-driven 13D from an
   accumulation-driven one. SEC13D_V2 records the first tag from today; a later family version could abstain or split on
   it. The register's prior of 0.55 is the same for both kinds; this note's view is that it should not be.
3. Twins should share the industry for banks and other regulated balance-sheet businesses.
4. Everything above came from sources the register already touches, plus public news. The judgment it adds is a
   probability table that will be scored; whether that judgment is worth anything is a question for twenty scored notes,
   not one.
