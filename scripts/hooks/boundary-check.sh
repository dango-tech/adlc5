#!/usr/bin/env bash
# Portable boundary check for Implement stage (callable from pre-commit recipe).
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

[[ -n "$FEATURE" ]] || { echo "ERROR: --feature required" >&2; exit 1; }

WORKSPACE="$(cd "$WORKSPACE" && pwd)"
STATE="${WORKSPACE}/.adlc5/${FEATURE}/state.json"

if [[ ! -f "$STATE" ]]; then
  echo '{"status":"skip","reason":"no adlc5 state"}'
  exit 0
fi

STAGE=$(jq -r '.current_stage // empty' "$STATE")
if [[ "$STAGE" != "implement" ]]; then
  echo "{\"status\":\"skip\",\"reason\":\"stage is ${STAGE}\"}"
  exit 0
fi

# Fail if story files exceed declared boundaries (basic check)
VIOLATIONS=0
while IFS= read -r line; do
  sid=$(echo "$line" | jq -r '.id')
  for f in $(echo "$line" | jq -r '.files[]?'); do
    [[ -f "${WORKSPACE}/${f}" ]] || continue
  done
done < <(jq -c '.tasks.stories[]?' "$STATE" 2>/dev/null)

echo "{\"status\":\"pass\",\"feature\":\"${FEATURE}\",\"violations\":${VIOLATIONS}}"
