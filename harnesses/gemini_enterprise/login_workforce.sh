#!/usr/bin/env bash
set -euo pipefail

POOL_ID="${WIF_POOL_ID:-your-wif-pool-id}"
PROVIDER_ID="${WIF_PROVIDER_ID:-your-wif-provider-id}"
CONFIG_FILE="login-config.json"

gcloud iam workforce-pools create-login-config \
  "locations/global/workforcePools/${POOL_ID}/providers/${PROVIDER_ID}" \
  --output-file="${CONFIG_FILE}"

echo "Open the login link in your Microsoft 365 browser profile."
read -r -p "Press [Enter] to start the gcloud login flow..."
gcloud auth login --login-config="${CONFIG_FILE}"

echo "Now sign in again for Application Default Credentials (ADC)."
read -r -p "Press [Enter] to start the ADC login flow..."
gcloud auth application-default login --login-config="${CONFIG_FILE}"

export GCP_ACCESS_TOKEN
GCP_ACCESS_TOKEN="$(gcloud auth application-default print-access-token)"
echo "Access token exported to GCP_ACCESS_TOKEN."
