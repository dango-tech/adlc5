#!/usr/bin/env bash
# Legacy delivery-state pilot compatibility adapter (JSON stdout).
# Current ADLC5 routing uses pilot-autopilot.sh through @adlc5.
set -euo pipefail

FEATURE=""
WORKSPACE="."
RECORD_RESULT=""

usage() {
  cat <<'EOF'
Usage: pilot.sh --feature NAME [--workspace DIR] [--record-result pass|fail]

One pilot iteration:
  1. Kill-switch / budget check
  2. Idempotent gate evaluation for the legacy delivery phase
  3. Emit checkpoint telemetry
  4. Print JSON { action, phase, skill, gates, ... }

Exit 0 — continue (spawn or advance). Exit 1 — halt. Exit 2 — usage/IO. Exit 3 — done (PR-ready path).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature) FEATURE="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --record-result) RECORD_RESULT="${2:?}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; exit 2 ;;
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
export ADLC5_WORKSPACE="$WORKSPACE"

get_policy_field() {
  local key="$1"
  local policies="${FEATURE_DIR}/policies.yaml"
  [[ -f "$policies" ]] || return 0
  python3 -c "
import sys
sys.path.insert(0, '${DIST_SCRIPTS}')
from lib.policies_load import load_policies
from pathlib import Path
p = load_policies(Path('${WORKSPACE}'), '${FEATURE}')
ap = p.get('autopilot') or {}
v = ap.get('${key}')
if v is not None and str(v) not in ('null', 'None', ''):
    print(v)
" 2>/dev/null || true
}
WORKSPACE="$(cd "$WORKSPACE" && pwd)"

FEATURE_DIR="${WORKSPACE}/.adlc5/${FEATURE}"
DELIVERY_STATE="${FEATURE_DIR}/delivery/state.json"
PILOT_META="${FEATURE_DIR}/pilot/meta.json"
mkdir -p "${FEATURE_DIR}/pilot"

if [[ -n "$RECORD_RESULT" ]]; then
  [[ -f "$PILOT_META" ]] || echo '{"iteration_count":0,"consecutive_failure_counter":0}' >"$PILOT_META"
  case "$RECORD_RESULT" in
    pass)
      jq '.consecutive_failure_counter = 0 | .iteration_count = ((.iteration_count // 0) + 1)' \
        "$PILOT_META" >"${PILOT_META}.tmp" && mv "${PILOT_META}.tmp" "$PILOT_META"
      ;;
    fail)
      jq '.consecutive_failure_counter = ((.consecutive_failure_counter // 0) + 1) | .iteration_count = ((.iteration_count // 0) + 1)' \
        "$PILOT_META" >"${PILOT_META}.tmp" && mv "${PILOT_META}.tmp" "$PILOT_META"
      ;;
  esac
  echo '{"recorded":true,"result":"'"$RECORD_RESULT"'"}' | jq .
  exit 0
fi

[[ -f "$DELIVERY_STATE" ]] || { echo '{"error":"delivery state missing","action":"halt"}' | jq .; exit 2; }

set +e
KS_OUT=$("${V1_SCRIPT_DIR}/pilot-check-kill-switch.sh" --feature "$FEATURE" --workspace "$WORKSPACE" 2>&1)
KS_EC=$?
set -e
if [[ "$KS_EC" -ne 0 ]]; then
  STOP=$(echo "$KS_OUT" | head -1)
  telemetry_emit "$FEATURE" "checkpoint" "pilot.sh" "halt" "" "$(jq -nc --arg r "$STOP" '{stop_reason:$r}')"
  jq -nc --arg stop "$STOP" '{action:"halt",stop_reason:$stop,phase:null,skill:null}'
  exit 1
fi

# shellcheck source=../../scripts/lib/phase-normalize.sh
source "${DIST_SCRIPTS}/lib/phase-normalize.sh"
CURRENT=$(jq -r '.current_phase // "plan-1-discovery"' "$DELIVERY_STATE")
CURRENT=$(normalize_phase_id "$CURRENT")
RESUME_FROM=$(get_policy_field resume_from)
if [[ -n "$RESUME_FROM" && "$RESUME_FROM" != "current_phase" ]]; then
  if [[ "$(phase_cmp "$CURRENT" "$RESUME_FROM")" -lt 0 ]]; then
    telemetry_emit "$FEATURE" "stage_picker" "pilot.sh" "ok" "$CURRENT" \
      "$(jq -nc --arg r "$RESUME_FROM" '{resume_from:$r,action:"jump"}')"
    CURRENT="$RESUME_FROM"
  fi
fi
telemetry_emit "$FEATURE" "checkpoint" "pilot.sh" "ok" "$CURRENT" '{"step":"gate_eval"}'

# Map phase -> gate id + skill to spawn
GATE_ID=""
SKILL=""
case "$CURRENT" in
  plan-1-discovery|plan-2-contracts|plan-3-operations) GATE_ID="plan-phase"; SKILL="adlc5-plan-design" ;;
  plan-4-user-stories) GATE_ID="plan-4-user-stories"; SKILL="adlc5-plan-stories" ;;
  plan-5-code-spec) GATE_ID="plan-5-code-spec"; SKILL="adlc5-plan-code-spec" ;;
  build-1-implementation) GATE_ID="build-1-implementation"; SKILL="adlc5-build" ;;
  assure-1-verification) GATE_ID="assure-1-verification"; SKILL="adlc5-assure-verify" ;;
  assure-2-integration) GATE_ID="assure-2-integration"; SKILL="adlc5-assure-integrate" ;;
  completed)
    set +e
    DONE_OUT=$("${DIST_SCRIPTS}/check-gates.py" --feature "$FEATURE" --workspace "$WORKSPACE" --gate pr-ready 2>/dev/null)
    DONE_EC=$?
    set -e
    if [[ "$DONE_EC" -eq 0 ]]; then
      telemetry_emit "$FEATURE" "checkpoint" "pilot.sh" "done" "$CURRENT" '{}'
      jq -nc '{action:"done",phase:"completed",skill:"pr-reviewer",message:"gates pass; invoke @pr-reviewer for PR handoff"}'
      exit 3
    fi
    FAIL_SKILL="qa"
    if echo "$DONE_OUT" | jq -e '.checks[] | select(.id == "qa_deployment_clearance" and .status == "fail")' >/dev/null 2>&1; then
      FAIL_SKILL="qa"
    elif echo "$DONE_OUT" | jq -e '.checks[] | select(.id == "assure_pr_review" and (.status == "fail" or .status == "warn"))' >/dev/null 2>&1; then
      FAIL_SKILL="pr-reviewer"
    elif echo "$DONE_OUT" | jq -e '.checks[] | select(.id | startswith("custom_gate_")) | select(.status == "fail")' >/dev/null 2>&1; then
      FAIL_SKILL="adlc5-build"
    fi
    telemetry_emit "$FEATURE" "gate_fail" "pilot.sh" "fail" "completed" "$(echo "$DONE_OUT" | jq -c '{skill:'"$FAIL_SKILL"'}' 2>/dev/null || echo '{}')"
    jq -nc --arg skill "$FAIL_SKILL" --argjson gates "$DONE_OUT" \
      '{action:"spawn",phase:"completed",skill:$skill,gates:$gates}'
    exit 0
    ;;
  *) GATE_ID="unknown"; SKILL="adlc5-plan" ;;
esac

# Pre-build design critic gate (autonomous profile)
POLICIES="${FEATURE_DIR}/policies.yaml"
if [[ "$CURRENT" == "build-1-implementation" && -f "$POLICIES" ]] \
  && grep -q 'interaction_mode: autonomous' "$POLICIES" 2>/dev/null; then
  CRITIC_FLAG="${FEATURE_DIR}/pilot/design-critic.done"
  if [[ ! -f "$CRITIC_FLAG" ]]; then
    jq -nc '{action:"spawn",phase:"'"$CURRENT"'",skill:"adlc5-design-critic",gates:{status:"pending",message:"run design critic before Build"}}'
    exit 0
  fi
fi

set +e
GATES_JSON=$("${DIST_SCRIPTS}/check-gates.py" --feature "$FEATURE" --workspace "$WORKSPACE" --gate "$GATE_ID" 2>/dev/null)
GATES_EC=$?
set -e

GATE_STATUS=$(echo "$GATES_JSON" | jq -r '.status // "fail"')

# Deterministic heal triggers (script failures on workspace)
HEAL_CLASS=""
if [[ "$GATE_STATUS" == "fail" && "$CURRENT" == "build-1-implementation" ]]; then
  set +e
  "${DIST_SCRIPTS}/run-tests.sh" --feature "$FEATURE" --workspace "$WORKSPACE" >/dev/null 2>&1
  TEC=$?
  "${DIST_SCRIPTS}/run-lint.sh" --feature "$FEATURE" --workspace "$WORKSPACE" >/dev/null 2>&1
  LEC=$?
  set -e
  if [[ "$TEC" -ne 0 ]]; then HEAL_CLASS="test_failure"; fi
  if [[ "$LEC" -ne 0 && -z "$HEAL_CLASS" ]]; then HEAL_CLASS="lint_failure"; fi
fi

if [[ "$GATE_STATUS" == "fail" ]]; then
  telemetry_emit "$FEATURE" "gate_fail" "pilot.sh" "fail" "$CURRENT" "$(echo "$GATES_JSON" | jq -c '{gate:"'"$GATE_ID"'"}' 2>/dev/null || echo '{}')"
fi

if [[ "$GATE_STATUS" == "pass" ]]; then
  ADV=$("${V1_SCRIPT_DIR}/advance-phase.sh" --feature "$FEATURE" --workspace "$WORKSPACE" 2>/dev/null || true)
  READY=$(echo "$ADV" | jq -r '.ready // false')
  if [[ "$READY" == "true" ]]; then
    NEXT=$(echo "$ADV" | jq -r '.suggested_next')
    telemetry_emit "$FEATURE" "phase_advance" "pilot.sh" "ok" "$CURRENT" "$(echo "$ADV" | jq -c '{suggested_next:.suggested_next}')"
    jq -nc --arg cur "$CURRENT" --arg next "$NEXT" --arg skill "$SKILL" \
      --argjson gates "$GATES_JSON" --argjson advance "$ADV" \
      '{action:"advance",phase:$cur,suggested_next:$next,skill:$skill,gates:$gates,advance:$advance}'
    exit 0
  fi
fi

if [[ -n "$HEAL_CLASS" ]]; then
  telemetry_emit "$FEATURE" "policy_decision" "pilot.sh" "heal" "$CURRENT" "$(jq -nc --arg c "$HEAL_CLASS" '{heal_class:$c}')"
  jq -nc --arg phase "$CURRENT" --arg class "$HEAL_CLASS" --argjson gates "$GATES_JSON" \
    '{action:"heal",phase:$phase,heal_class:$class,skill:"build-implementer",gates:$gates}'
  exit 0
fi

if [[ "$GATES_EC" -ne 0 && "$GATE_STATUS" == "fail" ]]; then
  jq -nc --arg phase "$CURRENT" --arg skill "$SKILL" --argjson gates "$GATES_JSON" \
    '{action:"spawn",phase:$phase,skill:$skill,gates:$gates}'
  exit 0
fi

jq -nc --arg phase "$CURRENT" --arg skill "$SKILL" --argjson gates "$GATES_JSON" \
  '{action:"spawn",phase:$phase,skill:$skill,gates:$gates}'
exit 0
