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

BROWSER_CMD="echo"
WRAPPER_SCRIPT=""
cleanup_wrapper() {
  if [[ -n "${WRAPPER_SCRIPT}" && -f "${WRAPPER_SCRIPT}" ]]; then
    rm -f "${WRAPPER_SCRIPT}"
  fi
}
trap cleanup_wrapper EXIT

if [[ -n "${CHROME_PROFILE:-}" || -n "${CHROME_USER_DATA_DIR:-}" ]]; then
  WRAPPER_SCRIPT="$(mktemp /tmp/gcloud_chrome_wrapper.XXXXXX.sh)"
  {
    echo "#!/usr/bin/env bash"
    echo -n "exec google-chrome"
    if [[ -n "${CHROME_PROFILE:-}" ]]; then
      printf " --profile-directory=%q" "${CHROME_PROFILE}"
    fi
    if [[ -n "${CHROME_USER_DATA_DIR:-}" ]]; then
      printf " --user-data-dir=%q" "${CHROME_USER_DATA_DIR}"
    fi
    echo ' "$@"'
  } > "${WRAPPER_SCRIPT}"
  chmod +x "${WRAPPER_SCRIPT}"
  BROWSER_CMD="${WRAPPER_SCRIPT}"
fi

BROWSER="${BROWSER_CMD}" gcloud auth application-default login --login-config="${CONFIG_FILE}"

export GCP_ACCESS_TOKEN
GCP_ACCESS_TOKEN="$(gcloud auth application-default print-access-token)"
echo "Access token exported to GCP_ACCESS_TOKEN."
