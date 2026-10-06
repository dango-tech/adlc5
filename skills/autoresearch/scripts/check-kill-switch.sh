#!/usr/bin/env bash
# Pre-trial gate. Exits non-zero (with a printed reason) if the loop should stop.
# Conditions:
#   - kill_switch_path file present
#   - max_trials reached
#   - max_total_wall_clock exceeded
#   - cost_cap_usd exceeded (when set and cost_accumulated_usd populated)
#   - consecutive_failures tripwire breached
set -euo pipefail

PROJECT=""
TASK="main"
WORKSPACE="."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/resolve-autoresearch-dir.sh
source "${SCRIPT_DIR}/lib/resolve-autoresearch-dir.sh"

usage() {
  cat <<'EOF'
Usage: check-kill-switch.sh --project CAMPAIGN [--task TASK_ID] [--workspace DIR]

--project is the campaign name (legacy alias). --task defaults to main.
Exit 0 if the loop may continue. Exit non-zero with a reason if it must stop.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="${2:?}"; shift 2 ;;
    --task) TASK="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; usage >&2; exit 1 ;;
  esac
done

[[ -n "$PROJECT" ]] || { usage >&2; exit 2; }
command -v jq >/dev/null || { echo "ERROR: jq is required" >&2; exit 2; }

WORKSPACE="$(cd "$WORKSPACE" && pwd)"
resolve_autoresearch_dir "$PROJECT" "$TASK" "$WORKSPACE"
PROJECT_DIR="$AR_PROJECT_DIR"
STATE="$AR_STATE_FILE"

[[ -f "$STATE" ]] || { echo "ERROR: ${STATE} not found" >&2; exit 2; }

KILL_SWITCH=$(jq -r '.context.safety.kill_switch_path // empty' "$STATE")
MAX_TRIALS=$(jq -r '.context.budget.max_trials // 50' "$STATE")
MAX_WC=$(jq -r '.context.budget.max_total_wall_clock // "8h"' "$STATE")
COST_CAP=$(jq -r '.context.safety.cost_cap_usd // empty' "$STATE")
COST_ACC=$(jq -r '.context.safety.cost_accumulated_usd // 0' "$STATE")
TRIPWIRE_FAIL=$(jq -r '.context.safety.tripwires.consecutive_failures // 3' "$STATE")
FAIL_COUNTER=$(jq -r '.context.safety.consecutive_failure_counter // 0' "$STATE")
TRIAL_COUNT=$(jq -r '.trials | length' "$STATE")
SESSION_START=$(jq -r '.created_at // empty' "$STATE")

# 1. Kill switch file
if [[ -n "$KILL_SWITCH" ]]; then
  KS_PATH="${KILL_SWITCH/#.autoresearch/${WORKSPACE}/.autoresearch}"
  if [[ -e "$KS_PATH" ]]; then
    echo "stop_reason=kill-switch path=${KS_PATH}"
    exit 10
  fi
fi

# 2. Max trials
if [[ "$TRIAL_COUNT" -ge "$MAX_TRIALS" ]]; then
  echo "stop_reason=max-trials count=${TRIAL_COUNT} cap=${MAX_TRIALS}"
  exit 11
fi

# 3. Max total wall clock (parse Ng | Nh | Nm | Ns)
parse_duration_seconds() {
  local d="$1"
  case "$d" in
    *h) echo $(( ${d%h} * 3600 )) ;;
    *m) echo $(( ${d%m} * 60 )) ;;
    *s) echo $(( ${d%s} )) ;;
    *)  echo 28800 ;; # default 8h
  esac
}

if [[ -n "$SESSION_START" ]]; then
  if date -u -d "$SESSION_START" +%s >/dev/null 2>&1; then
    START_EPOCH=$(date -u -d "$SESSION_START" +%s)
  elif date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$SESSION_START" +%s >/dev/null 2>&1; then
    START_EPOCH=$(date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$SESSION_START" +%s)
  else
    START_EPOCH=0
  fi
  NOW_EPOCH=$(date -u +%s)
  ELAPSED=$((NOW_EPOCH - START_EPOCH))
  MAX_SECS=$(parse_duration_seconds "$MAX_WC")
  if [[ "$ELAPSED" -ge "$MAX_SECS" ]]; then
    echo "stop_reason=max-wall-clock elapsed=${ELAPSED}s cap=${MAX_SECS}s"
    exit 12
  fi
fi

# 4. Cost cap
if [[ -n "$COST_CAP" && "$COST_CAP" != "null" ]]; then
  if awk -v a="$COST_ACC" -v c="$COST_CAP" 'BEGIN { exit !(a >= c) }'; then
    echo "stop_reason=cost-cap accumulated=${COST_ACC} cap=${COST_CAP}"
    exit 13
  fi
fi

# 5. Tripwire — consecutive failures
if [[ "$FAIL_COUNTER" -ge "$TRIPWIRE_FAIL" ]]; then
  echo "stop_reason=tripwire-consecutive-failures count=${FAIL_COUNTER} threshold=${TRIPWIRE_FAIL}"
  exit 14
fi

echo "ok trials=${TRIAL_COUNT}/${MAX_TRIALS} fail_counter=${FAIL_COUNTER}"
exit 0
