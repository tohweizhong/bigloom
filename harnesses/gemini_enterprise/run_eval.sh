#!/usr/bin/env bash
# Run BigLoom large-file evaluations against Gemini Enterprise (streamAssist).
#
# Usage:
#   bash harnesses/gemini_enterprise/run_eval.sh smoke
#   bash harnesses/gemini_enterprise/run_eval.sh full
#   bash harnesses/gemini_enterprise/run_eval.sh full --runs 3
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ARTIFACTS_DIR="${REPO_ROOT}/artifacts/ge_eval"
MANIFEST="${ARTIFACTS_DIR}/manifest.jsonl"

MODE="${1:-smoke}"
shift || true

case "${MODE}" in
  smoke)
    CASES="${ARTIFACTS_DIR}/smoke_cases.json"
    REPORTS_DIR="${SCRIPT_DIR}/reports/smoke"
    ;;
  full)
    CASES="${ARTIFACTS_DIR}/cases.json"
    REPORTS_DIR="${SCRIPT_DIR}/reports/full"
    ;;
  *)
    echo "Usage: bash harnesses/gemini_enterprise/run_eval.sh smoke|full [extra harness flags]"
    exit 2
    ;;
esac

PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/src:${PYTHONPATH:-}" \
  "${REPO_ROOT}/.venv/bin/python3" "${SCRIPT_DIR}/harness.py" \
  --config "${SCRIPT_DIR}/config.json" \
  --cases "${CASES}" \
  --manifest "${MANIFEST}" \
  --reports-dir "${REPORTS_DIR}" \
  --timeout 180 \
  "$@"
