# Incident 2026-10-31: a research sub-agent read sealed US and crypto holdout rows

Recorded by the session that ran the spot-only edge search (owner's request of 2026-10-31: "find and test a credible
source of trading profit ... spot buying ... Do not open any still-sealed dataset without my specific permission").

## What happened

During the literature review of hypothesis H2 (turn-of-the-month "dash for cash" index timing), one read-only
research sub-agent downloaded public data into `/tmp` (outside the repo) and computed statistics on sealed periods.
Nothing in the repo was written, and no strategy was frozen or changed because of it.

- `/tmp/totm_scripts/tom.py` line 82, `tom2.py`..`tom5.py`: turn-of-month statistics on Kenneth French / CRSP daily
  market returns for windows running to **2026-09-30** (including 2024-01-01..2026-09-30, the sealed US holdout of
  `handoff/BLUEPRINT.md` "Sealed holdouts" and `idx-signals/research/E2/protocol.json`).
- `/tmp/totm_scripts/btc.py` line 38: BTC daily turn-of-month statistics to **2026-10-30** (crypto holdout, already
  largely spent by CRYPTO_TUNE_v1 and ADMISSION_HOLDOUT_v1; 2026-10-30 is the first PREMOVE_SHADOW_v1 prospective day).
- The agent reported post-2014 turn-of-month numbers that mix these sealed rows (e.g. "2014-01 to 2026-09: 4.60 vs
  4.94 bp/day").

Separately, while checking Deribit data depth for a later-dropped option idea, the session printed five BTC delivery
prices for 2026-10-27..2026-10-31 (one API call, default newest-first ordering). No statistic was computed on them.

## Consequences (applied)

1. **US index calendar rules (turn-of-month, FOMC/macro windows) no longer have a clean 2024+ holdout.** Any future
   test of them must be prospective (from 2026-11) or use an owner-authorised, explicitly disclosed contaminated read.
2. The turn-of-month hypothesis was not chosen for testing (weak recent evidence, no verified spot-ETF venue for the
   owner, and this breach). The numbers above are not used anywhere in KOD.
3. Crypto daily 2024-01..2026-10-30 was already spent; this adds BTC turn-of-month statistics to the list of things
   seen. The PREMOVE_SHADOW_v1 trial is unaffected (its models and rules were frozen on 2026-10-30 and nothing was
   changed).
4. Future sub-agent briefs in this session state the sealed windows explicitly and forbid computing any statistic on
   rows dated 2024-01-01 or later.
