#!/usr/bin/env bash
set -euo pipefail

POOL_ID="${WIF_POOL_ID:-wif-pool-apr26}"
PROVIDER_ID="${WIF_PROVIDER_ID:-ms-entra-apr26}"
CONFIG_FILE="login-config.json"

gcloud iam workforce-pools create-login-config \
  "locations/global/workforcePools/${POOL_ID}/providers/${PROVIDER_ID}" \
  --output-file="${CONFIG_FILE}"

echo "=================================================================="
echo "1. Copy the https://auth.cloud.google/authorize?... link below."
echo "2. Paste it into your Microsoft 365 browser profile on Cloudtop."
echo "   (If you open it on your laptop and localhost fails to load,"
echo "    copy the http://localhost:... URL and run: curl '<url>' here.)"
echo "=================================================================="

BROWSER=echo gcloud auth application-default login --login-config="${CONFIG_FILE}"

export GCP_ACCESS_TOKEN
GCP_ACCESS_TOKEN="$(gcloud auth application-default print-access-token)"
echo "Access token exported to GCP_ACCESS_TOKEN."
