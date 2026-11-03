#!/bin/sh
# Offline acceptance for the integrated Ace components. Run from the repository root:
#   sh handoff/ace-integration-20261101/run_all_checks.sh
# Every Python process runs under offline_guard/ (an audit hook that denies IP network access); the guard is
# self-checked first. Outputs go to a fresh scratch directory that is created for this run and left in place
# (its path is printed); nothing outside it is deleted, and no bytecode is written into the repository.
set -eu
ROOT="$(pwd)"
A="$ROOT/handoff/ace-integration-20261101"
ARCHIVE="$A/originals/KOD_historical_shared_account_proof_20261101.zip"
ARCHIVE_SHA256="6ec9f6f87f02fac17d85e00aa92406c49c49349c43626ee317babfda18b93037"
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/kod-ace-checks.XXXXXX")"
PYTHONPATH="$A/offline_guard${PYTHONPATH:+:$PYTHONPATH}"
PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH PYTHONDONTWRITEBYTECODE
echo "scratch: $SCRATCH"

echo "== offline guard self-check (audit event only; no network operation)"
python3 - "$A/offline_guard/sitecustomize.py" <<'EOF'
import sys
from pathlib import Path
import sitecustomize as guard
if Path(guard.__file__).resolve() != Path(sys.argv[1]).resolve() or getattr(guard, "GUARD_INSTALLED", False) is not True:
    raise SystemExit("guard not active: expected startup guard/marker missing")
try:
    sys.audit("socket.getaddrinfo", "192.0.2.1", 80, 0, 0, 0)
except guard.NetworkBlocked as e:
    print("denied audit event:", e)
else:
    raise SystemExit("guard not active: audit event was not denied")
EOF

echo "== repair v1.4 affected tests (idx-signals)"
(cd "$ROOT/idx-signals" && python3 -m unittest tests.test_crypto_account tests.test_crypto_account_concurrency \
  tests.test_crypto_policy_price_validation tests.test_crypto_quote_validation tests.test_crypto_valuation_asof \
  tests.test_paper_execution_feasibility tests.test_paper_execution_filter_evidence tests.test_paper_account \
  tests.test_paper_account_report tests.test_crypto_replay)

echo "== trend paper-account v2 (30 tests, normal and -O, plus 2 process races)"
(cd "$A/paper_v2/KOD_trend_paper_v2_reviewed_20261101" && python3 trend-independent-audit/run_combined.py \
  && python3 -O trend-independent-audit/run_combined.py && python3 trend-independent-audit/multiprocess.py)

echo "== deterministic fixture demo, run twice (a retry must not add fills)"
(cd "$A/paper_v2/KOD_trend_paper_v2_reviewed_20261101/trend_core_paper_v2_candidate_20261101" \
  && python3 demo.py --output-dir "$SCRATCH/demo" >/dev/null && sha256sum "$SCRATCH"/demo/*.jsonl > "$SCRATCH/h1" \
  && python3 demo.py --output-dir "$SCRATCH/demo" >/dev/null && sha256sum "$SCRATCH"/demo/*.jsonl > "$SCRATCH/h2" \
  && cmp "$SCRATCH/h1" "$SCRATCH/h2" && echo "journals unchanged on retry")

echo "== reference adapter + connected run_once path (48 tests, normal and -O); public capture stays OFF"
(cd "$A/reference_profile" && python3 coinbase-independent-audit/run_combined.py \
  && python3 -O coinbase-independent-audit/run_combined.py)

echo "== historical proof: verify the pinned archive hash before extracting it"
GOT="$(sha256sum "$ARCHIVE" | cut -d' ' -f1)"
if [ "$GOT" != "$ARCHIVE_SHA256" ]; then
  echo "archive hash mismatch: expected $ARCHIVE_SHA256, got $GOT" >&2
  exit 1
fi
echo "archive sha256 OK: $GOT"
python3 -I -B - "$A/offline_guard/sitecustomize.py" "$ARCHIVE" "$SCRATCH/hist" <<'EOF'
import runpy
import sys
guard = runpy.run_path(sys.argv[1])  # trusted absolute local guard, before extraction
if guard.get("GUARD_INSTALLED") is not True:
    raise SystemExit("guard installation failed")
try:
    sys.audit("socket.getaddrinfo", "192.0.2.1", 80, 0, 0, 0)
except guard["NetworkBlocked"]:
    pass
else:
    raise SystemExit("guard audit check failed")
import zipfile
zipfile.ZipFile(sys.argv[2]).extractall(sys.argv[3])
EOF

echo "== historical proof: 27 tests, then verify the frozen journals"
(cd "$SCRATCH/hist" && python3 historical-independent-audit/run_combined.py \
  && python3 -O historical-independent-audit/run_combined.py \
  && python3 historical-independent-audit/verify_results.py > "$SCRATCH/verify.json" && echo "verify_results: exit 0" \
  && sha256sum historical_shared_account_results_20261101T1134/RESULTS.json)

echo "ALL CHECKS PASSED (scratch kept at $SCRATCH)"
