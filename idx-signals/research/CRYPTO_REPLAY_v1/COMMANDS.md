# CRYPTO_REPLAY_v1 — commands, in the order they were run

From `idx-signals/`. The panel is the PREMOVE_SEQUENCE_v1 input, sha256
`f1dfd57d26a7a98781bd5fcbf18db3203778d24c51c46b4d4f92963dc9b75766` (re-collected for PREMOVE_SHADOW_v1; not committed,
it is raw data).

```sh
# 1. rebuild the frozen 2023 rankings with the frozen coefficients and verify them against summary.json
python3 research/CRYPTO_REPLAY_v1/rankings.py --panel data/raw/premove/vintage-20261030/panel.csv.gz

# 2. tests (logs/tests_crypto_replay.txt, logs/tests_full_suite.txt)
python3 -m unittest -v tests.test_crypto_replay
python3 -m unittest discover -s tests -q

# 3. freeze the protocol before any result exists, and commit it
python3 research/CRYPTO_REPLAY_v1/replay.py --freeze --panel data/raw/premove/vintage-20261030/panel.csv.gz

# 4. the one run (refuses unless every pinned file is committed and unchanged), then the report
python3 research/CRYPTO_REPLAY_v1/replay.py --panel data/raw/premove/vintage-20261030/panel.csv.gz
python3 research/CRYPTO_REPLAY_v1/report.py
```

Outputs: `rankings/` (VERIFY.json, shortlists_2023.csv.gz), `protocol.json`, `run/RESULT.json`,
`run/trades_<scenario>_<arm>.csv.gz` (one row per candidate decision: order or skip, fill, exit, P&L),
`run/daily_<scenario>_<arm>.csv.gz` (cash, reserved, open value, equity, realized, unrealized, every UTC day),
`REPORT.md`.
