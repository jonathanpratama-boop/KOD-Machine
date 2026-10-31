# ADMISSION_HOLDOUT_v1 commands

Owner authorisation (2026-10-31): "I give you permission" — read 2024-01-01..2026-10-29 daily crypto bars for one
frozen test of ADMISSION_v1's fresh 10-15% rule.

Before freezing, the holdout code was checked on the already-used 2023 panel only: its shortlists equal
CRYPTO_REPLAY_v1's published early lists row for row (1,825 per model), and all eight 2023 accounts
(baseline and challenger x summary and sequence x base and doubled costs) reproduce ADMISSION_v1's fingerprints.

    python3 research/ADMISSION_HOLDOUT_v1/holdout.py --freeze
    python3 research/ADMISSION_HOLDOUT_v1/collect.py --out data/raw/premove/holdout-2024-2026
    python3 research/ADMISSION_HOLDOUT_v1/holdout.py --collection data/raw/premove/holdout-2024-2026
