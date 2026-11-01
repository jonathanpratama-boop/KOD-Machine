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

echo "== offline guard self-check (an outbound connection must be denied)"
python3 - <<'EOF'
import socket
try:
    socket.create_connection(("192.0.2.1", 80), timeout=1)
except Exception as e:
    if type(e).__name__ != "NetworkBlocked":
        raise SystemExit(f"guard not active: {type(e).__name__}: {e}")
    print("denied:", e)
else:
    raise SystemExit("guard not active: connection succeeded")
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
python3 -I -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$ARCHIVE" "$SCRATCH/hist"

echo "== historical proof: 27 tests, then verify the frozen journals"
(cd "$SCRATCH/hist" && python3 historical-independent-audit/run_combined.py \
  && python3 -O historical-independent-audit/run_combined.py \
  && python3 historical-independent-audit/verify_results.py > "$SCRATCH/verify.json" && echo "verify_results: exit 0" \
  && sha256sum historical_shared_account_results_20261101T1134/RESULTS.json)

echo "ALL CHECKS PASSED (scratch kept at $SCRATCH)"
