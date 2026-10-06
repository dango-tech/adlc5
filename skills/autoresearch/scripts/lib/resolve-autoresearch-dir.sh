# shellcheck shell=bash
# Resolve experiment root: campaign task dir or legacy flat project.
# Requires: PROJECT (campaign name), optional TASK (default main), WORKSPACE set.
resolve_autoresearch_dir() {
  local campaign="$1"
  local task="${2:-main}"
  local workspace="$3"
  local campaign_dir="${workspace}/.autoresearch/${campaign}"

  if [[ -f "${campaign_dir}/state.json" ]] \
    && jq -e '.mode == "campaign"' "${campaign_dir}/state.json" >/dev/null 2>&1; then
    AR_CAMPAIGN_DIR="$campaign_dir"
    AR_PROJECT_DIR="${campaign_dir}/tasks/${task}"
    AR_STATE_FILE="${AR_PROJECT_DIR}/state.json"
  elif [[ -f "${campaign_dir}/state.json" ]]; then
    AR_CAMPAIGN_DIR="$campaign_dir"
    AR_PROJECT_DIR="$campaign_dir"
    AR_STATE_FILE="${campaign_dir}/state.json"
  else
    AR_CAMPAIGN_DIR="$campaign_dir"
    AR_PROJECT_DIR="${campaign_dir}/tasks/${task}"
    AR_STATE_FILE="${AR_PROJECT_DIR}/state.json"
  fi
}
