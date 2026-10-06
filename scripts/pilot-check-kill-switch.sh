#!/usr/bin/env bash
# Pre-iteration gate for autonomous @adlc5. Exits non-zero when the loop must stop.
set -euo pipefail

FEATURE=""
WORKSPACE="."

usage() {
  cat <<'EOF'
Usage: pilot-check-kill-switch.sh --feature NAME [--workspace DIR]

Exit 0 if the pilot loop may continue. Exit non-zero with stop_reason= on stdout when it must stop.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature) FEATURE="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; exit 2 ;;
  esac
done

[[ -n "$FEATURE" ]] || { usage >&2; exit 2; }
command -v jq >/dev/null || { echo "ERROR: jq required" >&2; exit 2; }

WORKSPACE="$(cd "$WORKSPACE" && pwd)"
FEATURE_DIR="${WORKSPACE}/.adlc5/${FEATURE}"
LIFECYCLE_STATE="${FEATURE_DIR}/state.json"
POLICIES="${FEATURE_DIR}/policies.yaml"

# Defaults (overridden by policies.yaml when present)
KILL_SWITCH="${FEATURE_DIR}/STOP"
WALL_CLOCK_CAP_MINUTES=360
CONSECUTIVE_FAILURE_TRIPWIRE=3
MAX_ITERATIONS=200

if [[ -f "$POLICIES" ]]; then
  # Lightweight key extraction (no PyYAML required)
  ks=$(grep -E '^\s*kill_switch_file:' "$POLICIES" | head -1 | sed -E 's/.*:[[:space:]]*//' | tr -d '"' || true)
  [[ -n "$ks" ]] && KILL_SWITCH="${ks/#.adlc5/${WORKSPACE}/.adlc5}"
  wc=$(grep -E '^\s*wall_clock_cap_minutes:' "$POLICIES" | head -1 | grep -oE '[0-9]+' || true)
  [[ -n "$wc" ]] && WALL_CLOCK_CAP_MINUTES="$wc"
  tw=$(grep -E '^\s*consecutive_failure_tripwire:' "$POLICIES" | head -1 | grep -oE '[0-9]+' || true)
  [[ -n "$tw" ]] && CONSECUTIVE_FAILURE_TRIPWIRE="$tw"
  mi=$(grep -E '^\s*max_iterations:' "$POLICIES" | head -1 | grep -oE '[0-9]+' || true)
  [[ -n "$mi" ]] && MAX_ITERATIONS="$mi"
fi

PILOT_META="${FEATURE_DIR}/pilot/meta.json"
mkdir -p "${FEATURE_DIR}/pilot"
if [[ ! -f "$PILOT_META" ]]; then
  jq -nc --arg started "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
    '{started_at:$started,iteration_count:0,consecutive_failure_counter:0}' >"$PILOT_META"
fi

if [[ -e "$KILL_SWITCH" ]]; then
  echo "stop_reason=kill-switch path=${KILL_SWITCH}"
  exit 10
fi

ITERATION=$(jq -r '.iteration_count // 0' "$PILOT_META")
if [[ "$ITERATION" -ge "$MAX_ITERATIONS" ]]; then
  echo "stop_reason=max-iterations count=${ITERATION} cap=${MAX_ITERATIONS}"
  exit 11
fi

STARTED=$(jq -r '.started_at // empty' "$PILOT_META")
if [[ -n "$STARTED" ]]; then
  if date -u -d "$STARTED" +%s >/dev/null 2>&1; then
    START_EPOCH=$(date -u -d "$STARTED" +%s)
  elif date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$STARTED" +%s >/dev/null 2>&1; then
    START_EPOCH=$(date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$STARTED" +%s)
  else
    START_EPOCH=0
  fi
  NOW_EPOCH=$(date -u +%s)
  ELAPSED=$((NOW_EPOCH - START_EPOCH))
  MAX_SECS=$((WALL_CLOCK_CAP_MINUTES * 60))
  if [[ "$ELAPSED" -ge "$MAX_SECS" ]]; then
    echo "stop_reason=wall-clock-cap elapsed=${ELAPSED}s cap=${MAX_SECS}s"
    exit 12
  fi
fi

FAIL_COUNTER=$(jq -r '.consecutive_failure_counter // 0' "$PILOT_META")
if [[ "$FAIL_COUNTER" -ge "$CONSECUTIVE_FAILURE_TRIPWIRE" ]]; then
  echo "stop_reason=tripwire-consecutive-failures count=${FAIL_COUNTER} threshold=${CONSECUTIVE_FAILURE_TRIPWIRE}"
  exit 14
fi

echo "ok iteration=${ITERATION}/${MAX_ITERATIONS} fail_counter=${FAIL_COUNTER}"
exit 0
