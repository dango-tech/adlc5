#!/usr/bin/env bash
# Compose a PR description from canonical ADLC5 feature artifacts.
set -euo pipefail

FEATURE=""
WORKSPACE="."
OUT_FILE=""

usage() {
  cat <<'EOF'
Usage: pr-reviewer-compose-body.sh --feature NAME [--workspace DIR] [--out FILE]

Writes markdown PR body to stdout (or --out). Sources:
  - .adlc5/{feature}/telemetry/events.jsonl (last N events)
  - .qa/{feature}/deployment-clearance.md
  - .adlc5/{feature}/state.json story rollup (legacy state fallback supported)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature) FEATURE="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --out) OUT_FILE="${2:?}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; exit 2 ;;
  esac
done

[[ -n "$FEATURE" ]] || { usage >&2; exit 2; }
command -v jq >/dev/null || { echo "jq required" >&2; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/adlc5-paths.sh
source "${SCRIPT_DIR}/lib/adlc5-paths.sh"
WORKSPACE="$(cd "$WORKSPACE" && pwd)"
FEATURE_DIR="${WORKSPACE}/.adlc5/${FEATURE}"
EVENTS="${FEATURE_DIR}/telemetry/events.jsonl"
CLEARANCE="${WORKSPACE}/.qa/${FEATURE}/deployment-clearance.md"
STATE="$(adlc5_resolve_state "$WORKSPACE" "$FEATURE")"

emit() {
  if [[ -n "$OUT_FILE" ]]; then
    cat >"$OUT_FILE"
    echo "Wrote ${OUT_FILE}" >&2
  else
    cat
  fi
}

{
  echo "## Summary"
  echo ""
  echo "ADLC5 feature: \`${FEATURE}\`"
  if [[ -f "$STATE" ]]; then
    STAGE=$(jq -r '.current_stage // empty' "$STATE" 2>/dev/null || true)
    [[ -n "$STAGE" ]] && echo "- Lifecycle stage: \`${STAGE}\`"
    STEP=$(jq -r '.current_step // .current_phase // empty' "$STATE" 2>/dev/null || true)
    [[ -n "$STEP" ]] && echo "- Current step: \`${STEP}\`"
  fi
  echo ""

  if [[ -f "$CLEARANCE" ]]; then
    echo "## QA deployment clearance"
    echo ""
    head -40 "$CLEARANCE"
    echo ""
  fi

  if [[ -f "$STATE" ]]; then
    echo "## Story status"
    echo ""
    echo '```json'
    jq -c '
      if ((.tasks.stories? // null) | type) == "array" then
        [.tasks.stories[] | {id:(.id // .story_id), status:.status, type:(.type // "component")}]
      elif (.stories | type) == "object" then
        [.stories | to_entries[] | {id:.key, status:.value.status, type:(.value.type // "component")}]
      else [] end
    ' "$STATE" 2>/dev/null || echo '[]'
    echo '```'
    echo ""
  fi

  if [[ -f "$EVENTS" ]]; then
    echo "## Recent telemetry"
    echo ""
    echo '```json'
    tail -20 "$EVENTS"
    echo '```'
    echo ""
  fi

  echo "## Test plan"
  echo ""
  echo "- [ ] CI green"
  echo "- [ ] Reviewer spot-check acceptance criteria"
  echo "- [ ] QA clearance acknowledged"
  echo ""
  echo "---"
  echo "_Opened by ADLC5 automation (@pr-reviewer)_"
} | emit
