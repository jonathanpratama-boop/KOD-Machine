#!/bin/sh
# Offline acceptance for the integrated Ace components (no network, no journals outside a temp dir).
# Run from the repository root:  sh handoff/ace-integration-20261101/run_all_checks.sh
set -eu
ROOT="$(pwd)"
A="$ROOT/handoff/ace-integration-20261101"
TMP="$(mktemp -d)"
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
  && python3 demo.py --output-dir "$TMP/demo" >/dev/null && sha256sum "$TMP"/demo/*.jsonl > "$TMP/h1" \
  && python3 demo.py --output-dir "$TMP/demo" >/dev/null && sha256sum "$TMP"/demo/*.jsonl > "$TMP/h2" \
  && cmp "$TMP/h1" "$TMP/h2" && echo "journals unchanged on retry")
echo "== reference adapter + connected run_once path (48 tests, normal and -O; network blocked)"
(cd "$A/reference_profile" && python3 coinbase-independent-audit/run_combined.py \
  && python3 -O coinbase-independent-audit/run_combined.py)
echo "== historical shared-account proof: 27 tests, then verify the frozen journals from the pinned archive"
python3 -I -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" \
  "$A/originals/KOD_historical_shared_account_proof_20261101.zip" "$TMP/hist"
(cd "$TMP/hist" && python3 historical-independent-audit/run_combined.py \
  && python3 -O historical-independent-audit/run_combined.py \
  && python3 historical-independent-audit/verify_results.py > "$TMP/verify.json" && echo "verify_results: exit 0" \
  && sha256sum historical_shared_account_results_20261101T1134/RESULTS.json)
rm -rf "$TMP"
find "$A" -name __pycache__ -type d -prune -exec rm -rf {} +
echo "ALL CHECKS PASSED"
