# ADMISSION_v1 — commands, in order

From `idx-signals/`; the panel is the PREMOVE_SEQUENCE_v1 input (sha256 `f1dfd57d…`, not committed: raw data).

```sh
python3 -m unittest -v tests.test_admission tests.test_crypto_replay        # logs/tests.txt
python3 research/ADMISSION_v1/admission.py --freeze --panel data/raw/premove/vintage-20261030/panel.csv.gz
python3 research/ADMISSION_v1/admission.py --panel data/raw/premove/vintage-20261030/panel.csv.gz
```

Outputs: `protocol.json`, `run/RESULT.json`, `run/eligibility_<model>.csv.gz` (every original alert with its
eligibility reason), `run/trades_<model>_<case>_<policy>.csv.gz`, `run/daily_<model>_<case>_<policy>.csv.gz`,
`REPORT.md`.
