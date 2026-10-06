#!/usr/bin/env bash
# Render task board and stories.json from unified v2 state.
set -euo pipefail

FEATURE=""
WORKSPACE="."

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature) FEATURE="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    -h|--help) exit 0 ;;
    *) echo "Unknown: $1" >&2; exit 1 ;;
  esac
done

[[ -n "$FEATURE" ]] || exit 1
command -v jq >/dev/null || exit 1

WORKSPACE="$(cd "$WORKSPACE" && pwd)"
FEATURE_DIR="${WORKSPACE}/.adlc5/${FEATURE}"
STATE="${FEATURE_DIR}/state.json"
TASKS_DIR="${FEATURE_DIR}/tasks"
mkdir -p "$TASKS_DIR"

[[ -f "$STATE" ]] || { echo "ERROR: missing state.json" >&2; exit 1; }

jq '.tasks // {stories:[], parallel_batches:[]}' "$STATE" >"${TASKS_DIR}/stories.json"

STAGE=$(jq -r '.current_stage // "?"' "$STATE")
STEP=$(jq -r '.current_step // "?"' "$STATE")
NOW="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

{
  echo "# Task board — ${FEATURE}"
  echo ""
  echo "**Updated:** ${NOW}  "
  echo "**Stage:** ${STAGE} · **Step:** ${STEP}"
  echo ""
  echo "## Stories"
  echo ""
  echo "| ID | Title | Status | Batch | Depends on |"
  echo "|----|-------|--------|-------|------------|"
  jq -r '.tasks.stories[]? | "| \(.id) | \(.title // .id) | \(.status // "pending") | \(.batch // 0) | \(.depends_on // [] | join(", ")) |"' "$STATE"
  echo ""
  echo "## Parallel batches"
  echo ""
  echo '```mermaid'
  echo "flowchart LR"
  jq -r '.tasks.parallel_batches[]? | "  subgraph batch\(.batch // 0)\n    \(.story_ids // [] | join(" --> "))\n  end"' "$STATE" 2>/dev/null || true
  echo '```'
} >"${TASKS_DIR}/board.md"

echo "{\"status\":\"ok\",\"stories\":\"${TASKS_DIR}/stories.json\",\"board\":\"${TASKS_DIR}/board.md\"}"
