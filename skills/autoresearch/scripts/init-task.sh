#!/usr/bin/env bash
# Scaffold one task under .autoresearch/{campaign}/tasks/{task}/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TEMPLATES="${SKILL_DIR}/templates"

CAMPAIGN=""
TASK=""
WORKSPACE="."
FORCE=0

usage() {
  cat <<'EOF'
Usage: init-task.sh --campaign NAME --task TASK_ID [--workspace DIR] [--force]

Creates tasks/{TASK_ID}/ with state.json, program.md, definition-of-done.md, experiments/, best-artifact/
Updates campaign state.json.tasks[TASK_ID].
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --campaign) CAMPAIGN="${2:?}"; shift 2 ;;
    --task) TASK="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --force) FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; usage >&2; exit 1 ;;
  esac
done

[[ -n "$CAMPAIGN" && -n "$TASK" ]] || { usage >&2; exit 1; }
command -v jq >/dev/null || { echo "ERROR: jq required" >&2; exit 1; }

mkdir -p "$WORKSPACE"
WORKSPACE="$(cd "$WORKSPACE" && pwd)"
CAMPAIGN_DIR="${WORKSPACE}/.autoresearch/${CAMPAIGN}"
TASK_DIR="${CAMPAIGN_DIR}/tasks/${TASK}"
CAMPAIGN_STATE="${CAMPAIGN_DIR}/state.json"

[[ -f "$CAMPAIGN_STATE" ]] || { echo "ERROR: campaign missing — run init-campaign.sh first" >&2; exit 1; }

if [[ -e "$TASK_DIR" && "$FORCE" -ne 1 ]]; then
  echo "ERROR: ${TASK_DIR} already exists. Use --force." >&2
  exit 1
fi

mkdir -p "${TASK_DIR}/experiments"
mkdir -p "${TASK_DIR}/best-artifact"
mkdir -p "${TASK_DIR}/memory/summaries"

ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

render() {
  local src="$1" dst="$2"
  sed -e "s|{campaign_name}|${CAMPAIGN}|g" \
      -e "s|{task_id}|${TASK}|g" \
      -e "s|{iso8601}|${ISO}|g" \
      "$src" > "$dst"
}

render "${TEMPLATES}/task-state.json"        "${TASK_DIR}/state.json"
render "${TEMPLATES}/program.md"            "${TASK_DIR}/program.md"
render "${TEMPLATES}/definition-of-done.md" "${TASK_DIR}/definition-of-done.md"
render "${TEMPLATES}/experiment-log.md"     "${TASK_DIR}/experiments/log.md"
render "${TEMPLATES}/leaderboard.md"        "${TASK_DIR}/leaderboard.md"

tmp="$(mktemp)"
jq --arg id "$TASK" --arg iso "$ISO" \
  '.tasks[$id] = {
    "status": "pending",
    "current_phase": "autoresearch-1-intake",
    "path": ("tasks/" + $id),
    "created_at": $iso
  }' "$CAMPAIGN_STATE" >"$tmp"
mv "$tmp" "$CAMPAIGN_STATE"

echo "Initialized task ${TASK} at ${TASK_DIR}"
