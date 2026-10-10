#!/usr/bin/env bash
# ADLC5 pilot loop — one iteration (unified state, v2 gate IDs, persona routing).
set -euo pipefail

FEATURE=""
WORKSPACE="."
RECORD_RESULT=""

usage() {
  cat <<'EOF'
Usage: ./scripts/pilot-autopilot.sh --feature NAME [--workspace DIR] [--record-result pass|fail]
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
command -v jq >/dev/null || { echo '{"error":"jq required"}' | jq .; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=../../scripts/lib/telemetry.sh
source "${ROOT}/scripts/lib/telemetry.sh"
export ADLC5_WORKSPACE="$WORKSPACE"
WORKSPACE="$(cd "$WORKSPACE" && pwd)"

FEATURE_DIR="${WORKSPACE}/.adlc5/${FEATURE}"
STATE="${FEATURE_DIR}/state.json"
PILOT_META="${FEATURE_DIR}/pilot/meta.json"
mkdir -p "${FEATURE_DIR}/pilot"
if [[ ! -f "$PILOT_META" ]]; then
  RUN_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')
  jq -nc --arg run_id "$RUN_ID" --arg started "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
    '{run_id:$run_id,started_at:$started,iteration_count:0,consecutive_failure_counter:0}' >"$PILOT_META"
elif ! jq -e '.run_id and (.run_id | length > 0)' "$PILOT_META" >/dev/null 2>&1; then
  RUN_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')
  jq --arg run_id "$RUN_ID" --arg started "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" '.run_id=$run_id | .started_at=(.started_at // $started)' "$PILOT_META" >"${PILOT_META}.tmp"
  mv "${PILOT_META}.tmp" "$PILOT_META"
elif ! jq -e '.started_at and (.started_at | length > 0)' "$PILOT_META" >/dev/null 2>&1; then
  jq --arg started "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" '.started_at=$started' "$PILOT_META" >"${PILOT_META}.tmp"
  mv "${PILOT_META}.tmp" "$PILOT_META"
fi

persona_meta() {
  python3 - "$ROOT" "$WORKSPACE" "$FEATURE" "$1" "${2:-}" <<'PY'
import json, os, sys
from pathlib import Path

root, workspace, feature, step, requested = sys.argv[1:]
sys.path.insert(0, str(Path(root) / "scripts"))
from lib.personas_load import (
    get_persona_for_step,
    fresh_session_for_persona,
    verifier_different_model,
    get_persona_config,
)
from lib.policies_load import load_policies

policies = load_policies(Path(workspace), feature)
persona = requested or get_persona_for_step(step) or "analyst"
cfg = get_persona_config(persona)
print(json.dumps({
    "persona": persona,
    "persona_display": cfg.get("display", persona),
    "model_tier": cfg.get("model_tier"),
    "fresh_session": fresh_session_for_persona(policies),
    "verifier_different_model": verifier_different_model(policies) and persona == "tester",
    "persona_mode": bool((policies.get("persona_mode") or {}).get("enabled")),
    "run_id": os.environ["ADLC5_RUN_ID"],
    "node_id": step,
    "attempt": int(os.environ.get("ADLC5_ATTEMPT", "1")),
}))
PY
}

if [[ -n "$RECORD_RESULT" ]]; then
  case "$RECORD_RESULT" in
    pass) jq '.consecutive_failure_counter=0|.iteration_count=((.iteration_count//0)+1)' "$PILOT_META" >"${PILOT_META}.tmp" && mv "${PILOT_META}.tmp" "$PILOT_META" ;;
    fail) jq '.consecutive_failure_counter=((.consecutive_failure_counter//0)+1)|.iteration_count=((.iteration_count//0)+1)' "$PILOT_META" >"${PILOT_META}.tmp" && mv "${PILOT_META}.tmp" "$PILOT_META" ;;
  esac
  echo "{\"recorded\":true,\"result\":\"${RECORD_RESULT}\"}" | jq .
  exit 0
fi

[[ -f "$STATE" ]] || { echo '{"error":"state.json missing","action":"halt"}' | jq .; exit 2; }
SCHEMA=$(jq -r '.schema_version // "1.0"' "$STATE")
[[ "$SCHEMA" == "3.0" ]] || {
  echo '{"error":"schema 3.0 state required — run init-feature.sh","action":"halt"}' | jq .
  exit 2
}

set +e
KS_OUT=$("${ROOT}/scripts/pilot-check-kill-switch.sh" --feature "$FEATURE" --workspace "$WORKSPACE" 2>&1)
KS_EC=$?
set -e
if [[ "$KS_EC" -ne 0 ]]; then
  STOP=$(echo "$KS_OUT" | head -1)
  jq -nc --arg stop "$STOP" '{action:"halt",stop_reason:$stop,phase:null,skill:null}'
  exit 1
fi

CURRENT_STEP=$(jq -r '.current_step // "specify-0-git"' "$STATE")
CURRENT_STAGE=$(jq -r '.current_stage // "specify"' "$STATE")
ACTIVE_PERSONA=$(jq -r '.persona.active // empty' "$STATE")
export ADLC5_RUN_ID="$(jq -r '.run_id' "$PILOT_META")"
export ADLC5_NODE_ID="$CURRENT_STEP"
export ADLC5_ATTEMPT="$(jq -r '(.consecutive_failure_counter // 0) + 1' "$PILOT_META")"
PERSONA_JSON=$(persona_meta "$CURRENT_STEP" "$ACTIVE_PERSONA")
telemetry_emit "$FEATURE" "checkpoint" "pilot-autopilot.sh" "ok" "$CURRENT_STEP" '{"step":"gate_eval"}'

GATE_ID=""
SKILL=""
case "$CURRENT_STEP" in
  specify-*) GATE_ID="specify-complete"; SKILL="adlc5-specify" ;;
  plan-*) GATE_ID="plan-complete"; SKILL="adlc5-plan" ;;
  tasks-1-stories) GATE_ID="tasks-1-stories-complete"; SKILL="adlc5-tasks" ;;
  tasks-2-code-spec) GATE_ID="tasks-2-code-spec-complete"; SKILL="adlc5-tasks" ;;
  tasks-*) GATE_ID="tasks-complete"; SKILL="adlc5-tasks" ;;
  implement-1-build) GATE_ID="implement-1-build"; SKILL="adlc5-implement" ;;
  implement-2-verify) GATE_ID="implement-2-verify"; SKILL="adlc5-implement" ;;
  implement-3-integrate) GATE_ID="implement-3-integrate"; SKILL="adlc5-implement" ;;
  implement-4-qa) GATE_ID="implement-4-qa"; SKILL="qa" ;;
  implement-5-pr) GATE_ID="pr-ready"; SKILL="pr-reviewer" ;;
  *)
    if [[ "$CURRENT_STAGE" == "implement" && "$(jq -r '.stage_status.implement // empty' "$STATE")" == "completed" ]]; then
      GATE_ID="pr-ready"
    fi
    ;;
esac

if [[ -z "$GATE_ID" ]]; then
  jq -nc --arg s "$CURRENT_STEP" '{action:"halt",stop_reason:"unknown step",phase:$s,skill:null}'
  exit 1
fi

# Additive model routing fields for spawn/advance JSON (never breaks existing contract).
resolve_model_json() {
  local tier="$1"
  local step="$2"
  if [[ ! -x "${ROOT}/scripts/resolve-model.sh" ]]; then
    echo '{}'
    return 0
  fi
  set +e
  local out
  out=$("${ROOT}/scripts/resolve-model.sh" \
    --tier "$tier" \
    --step "$step" \
    --workspace "$WORKSPACE" \
    --feature "$FEATURE" 2>/dev/null)
  local ec=$?
  set -e
  if [[ "$ec" -ne 0 || -z "$out" ]]; then
    echo "Model resolution failed for tier=${tier} step=${step}: ${out:-no result}" >&2
    return 1
  fi
  echo "$out" | jq -c '{
    recommended_model: .model_id,
    model_effort: .effort,
    model_context: .context,
    model_tier_resolved: .tier,
    model_platform: .platform,
    model_notice: .notice,
    model_spawn_policy: .spawn_policy,
    model_version: .version,
    config_source: .source
  }' 2>/dev/null || echo '{}'
}

MODEL_TIER=$(echo "$PERSONA_JSON" | jq -r '.model_tier // "balanced"')
MODEL_JSON=$(resolve_model_json "$MODEL_TIER" "$CURRENT_STEP")

if [[ "$GATE_ID" == "pr-ready" ]]; then
  set +e
  PR_OUT=$("${ROOT}/scripts/check-gates.py" --feature "$FEATURE" --workspace "$WORKSPACE" --gate pr-ready 2>&1)
  PR_EC=$?
  set -e
  PR_STATUS=$(echo "$PR_OUT" | jq -r '.status // "fail"')
  if [[ "$PR_EC" -eq 0 && "$PR_STATUS" == "pass" ]]; then
    jq -nc --argjson persona "$PERSONA_JSON" --argjson model "$MODEL_JSON" \
      '{action:"done",phase:"pr-ready",skill:null,message:"pr-ready gate passed",transition_target:"completed"} + $persona + $model'
    exit 3
  fi
  jq -nc --argjson gates "$PR_OUT" --argjson persona "$PERSONA_JSON" --argjson model "$MODEL_JSON" \
    '{action:"spawn",phase:"implement-5-pr",skill:"pr-reviewer",gates:$gates} + $persona + $model'
  exit 0
fi

set +e
GATE_OUT=$("${ROOT}/scripts/check-gates.py" --feature "$FEATURE" --workspace "$WORKSPACE" --gate "$GATE_ID" 2>&1)
GATE_EC=$?
set -e
GATE_STATUS=$(echo "$GATE_OUT" | jq -r '.status // "fail"')

if [[ "$GATE_EC" -eq 0 && "$GATE_STATUS" == "pass" ]]; then
  NEXT=$(python3 - "$ROOT" "$WORKSPACE" "$FEATURE" "$CURRENT_STEP" <<'PY'
import sys
from pathlib import Path

root, workspace, feature, current_step = sys.argv[1:]
sys.path.insert(0, str(Path(root) / "scripts"))
from lib.policies_load import load_policies, next_step_for_profile
p = load_policies(Path(workspace), feature)
print(next_step_for_profile(p, current_step))
PY
)
  jq -nc --arg next "$NEXT" --arg skill "$SKILL" --arg gate "$GATE_ID" --argjson persona "$PERSONA_JSON" --argjson model "$MODEL_JSON" \
    '{action:"advance",suggested_next:$next,transition_target:$next,skill:$skill,gate:$gate,phase:"'"$CURRENT_STEP"'"} + $persona + $model'
  exit 0
fi

jq -nc --arg skill "$SKILL" --arg gate "$GATE_ID" --argjson gates "$GATE_OUT" --argjson persona "$PERSONA_JSON" --argjson model "$MODEL_JSON" \
  '{action:"spawn",skill:$skill,gate:$gate,phase:"'"$CURRENT_STEP"'",gates:$gates} + $persona + $model'
exit 0
