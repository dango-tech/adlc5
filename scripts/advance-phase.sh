#!/usr/bin/env bash
# Legacy delivery-state phase suggestion compatibility adapter (JSON stdout).
# Does not mutate state — orchestrator applies after HITL confirmation.
set -euo pipefail

FEATURE=""
WORKSPACE="."
TARGET=""

usage() {
  cat <<'EOF'
Usage: advance-phase.sh --feature NAME [--workspace DIR] [--target PHASE_ID]

Prints JSON with current_phase, suggested_next, ready (bool), blockers[].
Exit 0 when ready=true; exit 1 when ready=false; exit 2 on usage/IO error.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature) FEATURE="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --target) TARGET="${2:?}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "$FEATURE" ]] || { usage >&2; exit 2; }
command -v jq >/dev/null || { echo '{"error":"jq required"}' ; exit 2; }

V1_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${V1_SCRIPT_DIR}/.." && pwd)"
DIST_SCRIPTS="${ROOT}/scripts"
# shellcheck source=../../scripts/lib/telemetry.sh
source "${DIST_SCRIPTS}/lib/telemetry.sh"
# shellcheck source=../../scripts/lib/phase-order.sh
source "${DIST_SCRIPTS}/lib/phase-order.sh"
# shellcheck source=../../scripts/lib/phase-normalize.sh
source "${DIST_SCRIPTS}/lib/phase-normalize.sh"
export ADLC5_WORKSPACE="$WORKSPACE"

get_policy_field() {
  local key="$1"
  local policies="${WORKSPACE}/.adlc5/${FEATURE}/policies.yaml"
  [[ -f "$policies" ]] || return 0
  python3 -c "
import sys
sys.path.insert(0, '${DIST_SCRIPTS}')
from lib.policies_load import load_policies
from pathlib import Path
p = load_policies(Path('${WORKSPACE}'), '${FEATURE}')
ap = p.get('autopilot') or {}
v = ap.get('${key}') or p.get('${key}')
if v is not None and str(v) not in ('null', 'None', ''):
    print(v)
" 2>/dev/null || true
}

WORKSPACE="$(cd "$WORKSPACE" && pwd)"
STATE="${WORKSPACE}/.adlc5/${FEATURE}/delivery/state.json"
[[ -f "$STATE" ]] || { echo '{"error":"delivery state not found","ready":false}' ; exit 2; }

telemetry_emit "$FEATURE" "script.start" "advance-phase.sh" "ok" "$(jq -r '.current_phase // empty' "$STATE")" '{}'

CURRENT=$(jq -r '.current_phase // "plan-1-discovery"' "$STATE")
CURRENT=$(normalize_phase_id "$CURRENT")
PHASE_STATUS=$(jq -c '.phase_status // {}' "$STATE")

# Ordered semantic phases
ORDER=(
  plan-1-discovery
  plan-2-contracts
  plan-3-operations
  plan-4-user-stories
  plan-5-code-spec
  build-1-implementation
  assure-1-verification
  assure-2-integration
  completed
)

suggest_next() {
  local cur="$1"
  for i in "${!ORDER[@]}"; do
    if [[ "${ORDER[$i]}" == "$cur" ]]; then
      if [[ $((i + 1)) -lt ${#ORDER[@]} ]]; then
        echo "${ORDER[$((i + 1))]}"
        return
      fi
      echo "completed"
      return
    fi
  done
  echo "plan-2-contracts"
}

NEXT=$(suggest_next "$CURRENT")
[[ -n "$TARGET" ]] && NEXT="$TARGET"

READY=true
BLOCKERS=()

case "$CURRENT" in
  plan-*)
    STATUS=$(phase_status_get "$PHASE_STATUS" "$CURRENT")
    if [[ "$STATUS" != "completed" ]]; then
      READY=false
      BLOCKERS+=("phase_status.$(phase_status_key_from_phase_id "$CURRENT") is ${STATUS}, expected completed")
    fi
    ;;
  build-1-implementation)
    INCOMPLETE=$(jq -r '[.stories[]? | select(.status != "implementation_complete" and .status != "verified" and .status != "failed")] | length' "$STATE")
    if [[ "$INCOMPLETE" != "0" ]]; then
      READY=false
      BLOCKERS+=("${INCOMPLETE} stories not implementation_complete")
    fi
    ;;
  assure-1-verification)
    UNVERIFIED=$(jq -r '[.stories[]? | select(.type != "integration" and .status != "verified")] | length' "$STATE")
    if [[ "$UNVERIFIED" != "0" ]]; then
      READY=false
      BLOCKERS+=("${UNVERIFIED} component stories not verified")
    fi
    ;;
  assure-2-integration)
    INT_STATUS=$(jq -r '.integration.status // "pending"' "$STATE")
    if [[ "$INT_STATUS" != "completed" ]]; then
      READY=false
      BLOCKERS+=("integration.status is ${INT_STATUS}")
    fi
    set +e
    "${V1_SCRIPT_DIR}/sync-verification-report.sh" --feature "$FEATURE" --workspace "$WORKSPACE" >/dev/null 2>&1
    SYNC_EC=$?
    set -e
    if [[ "$SYNC_EC" -ne 0 ]]; then
      READY=false
      BLOCKERS+=("verification-report out of sync")
    fi
    ;;
esac

STOP_AT=$(get_policy_field stop_at_phase)
if [[ -n "$STOP_AT" ]] && [[ "$(phase_cmp "$NEXT" "$STOP_AT")" -gt 0 ]]; then
  READY=false
  BLOCKERS+=("stop_at_phase ${STOP_AT} blocks advance to ${NEXT}")
fi

if [[ ${#BLOCKERS[@]} -eq 0 ]]; then
  BLOCKERS_JSON='[]'
else
  BLOCKERS_JSON=$(printf '%s\n' "${BLOCKERS[@]}" | jq -R -s 'split("\n") | map(select(length>0))')
fi
READY_JSON=$([[ "$READY" == "true" ]] && echo true || echo false)
DETAILS=$(jq -nc --arg cur "$CURRENT" --arg next "$NEXT" --argjson ready "$READY_JSON" --argjson blockers "$BLOCKERS_JSON" \
  '{current_phase:$cur,suggested_next:$next,ready:$ready,blockers:$blockers}')

echo "$DETAILS" | jq .

STATUS_JSON="ok"
[[ "$READY" == "true" ]] || STATUS_JSON="blocked"
telemetry_emit "$FEATURE" "script.end" "advance-phase.sh" "$STATUS_JSON" "$CURRENT" "$DETAILS"

if [[ "$READY" == "true" ]]; then
  exit 0
fi
exit 1
