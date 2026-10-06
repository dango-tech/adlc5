#!/usr/bin/env bash
# Append a trial row to log.md, update state.json, and rewrite leaderboard.md when kept improves best.
set -euo pipefail

PROJECT=""
TASK="main"
WORKSPACE="."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/resolve-autoresearch-dir.sh
source "${SCRIPT_DIR}/lib/resolve-autoresearch-dir.sh"
TRIAL_ID=""
STATUS=""
PARENT="baseline"
METRIC=""
MUTATION_SUMMARY=""

usage() {
  cat <<'EOF'
Usage: log-experiment.sh --project NAME --trial-id ID --status STATUS [options]

Required:
  --project NAME             Campaign name
  --task ID                  Task id (default: main)
  --trial-id ID              Trial id
  --status STATUS            kept | discarded | failed

Optional:
  --workspace DIR            Workspace root (default: cwd)
  --parent ID                Parent trial id (default: baseline)
  --metric VALUE             Numeric metric value (omit for failed)
  --mutation-summary TEXT    One-line mutation description
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="${2:?}"; shift 2 ;;
    --task) TASK="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --trial-id) TRIAL_ID="${2:?}"; shift 2 ;;
    --status) STATUS="${2:?}"; shift 2 ;;
    --parent) PARENT="${2:?}"; shift 2 ;;
    --metric) METRIC="${2:?}"; shift 2 ;;
    --mutation-summary) MUTATION_SUMMARY="${2:?}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; usage >&2; exit 1 ;;
  esac
done

[[ -n "$PROJECT" && -n "$TRIAL_ID" && -n "$STATUS" ]] || { usage >&2; exit 1; }
command -v jq >/dev/null || { echo "ERROR: jq is required" >&2; exit 1; }

case "$STATUS" in
  kept|discarded|failed) ;;
  *) echo "ERROR: status must be kept|discarded|failed" >&2; exit 1 ;;
esac

WORKSPACE="$(cd "$WORKSPACE" && pwd)"
resolve_autoresearch_dir "$PROJECT" "$TASK" "$WORKSPACE"
PROJECT_DIR="$AR_PROJECT_DIR"
STATE="$AR_STATE_FILE"
LOG_MD="${PROJECT_DIR}/experiments/log.md"
LEADERBOARD="${PROJECT_DIR}/leaderboard.md"
TRIAL_DIR="${PROJECT_DIR}/experiments/${TRIAL_ID}"

[[ -f "$STATE" ]] || { echo "ERROR: ${STATE} not found" >&2; exit 1; }
[[ -d "$TRIAL_DIR" ]] || { echo "ERROR: ${TRIAL_DIR} not found" >&2; exit 1; }

ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
STARTED_AT="$(cat "${TRIAL_DIR}/started_at.txt" 2>/dev/null || echo "$ISO")"
ENDED_AT="$(cat "${TRIAL_DIR}/ended_at.txt" 2>/dev/null || echo "$ISO")"
DURATION="$(cat "${TRIAL_DIR}/duration_seconds.txt" 2>/dev/null || echo 0)"
EXIT_CODE="$(cat "${TRIAL_DIR}/exit_code" 2>/dev/null || echo 1)"

METRIC_NAME=$(jq -r '.context.target.metric_name // "metric"' "$STATE")
DIRECTION=$(jq -r '.context.target.metric_direction // "min"' "$STATE")
BASELINE_METRIC=$(jq -r '.baseline.metric_value // empty' "$STATE")
BEST_METRIC=$(jq -r '.leaderboard.best_metric_value // empty' "$STATE")

# Compute deltas (string ops; numeric noise OK)
delta() {
  local val="$1" ref="$2"
  if [[ -z "$val" || -z "$ref" ]]; then echo ""; return; fi
  awk -v v="$val" -v r="$ref" 'BEGIN { printf "%.6g", v - r }'
}

DELTA_BASELINE=""
if [[ -n "$METRIC" && -n "$BASELINE_METRIC" ]]; then
  DELTA_BASELINE="$(delta "$METRIC" "$BASELINE_METRIC")"
fi

# Decide if this trial is a new best
NEW_BEST=0
if [[ "$STATUS" == "kept" && -n "$METRIC" ]]; then
  if [[ -z "$BEST_METRIC" ]]; then
    NEW_BEST=1
  else
    if [[ "$DIRECTION" == "min" ]]; then
      if awk -v a="$METRIC" -v b="$BEST_METRIC" 'BEGIN { exit !(a < b) }'; then NEW_BEST=1; fi
    else
      if awk -v a="$METRIC" -v b="$BEST_METRIC" 'BEGIN { exit !(a > b) }'; then NEW_BEST=1; fi
    fi
  fi
fi

# Append to log.md
printf "| %s | %s | %ss | %s | %s | %s | %s | %s | %s |\n" \
  "$TRIAL_ID" "$STARTED_AT" "$DURATION" "$PARENT" \
  "$MUTATION_SUMMARY" "$EXIT_CODE" "${METRIC:-—}" "$STATUS" "" \
  >> "$LOG_MD"

# Update state.json.trials[trial]
TMP="$(mktemp)"
jq --arg id "$TRIAL_ID" \
   --arg status "$STATUS" \
   --arg parent "$PARENT" \
   --arg mutation "$MUTATION_SUMMARY" \
   --arg started "$STARTED_AT" \
   --arg ended "$ENDED_AT" \
   --arg log "experiments/${TRIAL_ID}/run.log" \
   --arg snap "experiments/${TRIAL_ID}/$(jq -r '.context.target.artifact_path | split("/") | last' "$STATE")" \
   --argjson metric "${METRIC:-null}" \
   --argjson delta "${DELTA_BASELINE:-null}" \
   '.trials[$id] = {
       status: $status,
       parent_trial_id: $parent,
       mutation_summary: $mutation,
       metric_value: $metric,
       delta_vs_baseline: $delta,
       started_at: $started,
       ended_at: $ended,
       artifact_snapshot: $snap,
       log_path: $log
     } | .updated_at = (now | todate)' \
  "$STATE" > "$TMP"
mv "$TMP" "$STATE"

# Update leaderboard if new best
if [[ "$NEW_BEST" -eq 1 ]]; then
  TMP="$(mktemp)"
  jq --arg id "$TRIAL_ID" \
     --argjson metric "$METRIC" \
     '.leaderboard = { best_trial_id: $id, best_metric_value: $metric, updated_at: (now | todate) }' \
    "$STATE" > "$TMP"
  mv "$TMP" "$STATE"

  # Rewrite leaderboard.md from state.json (top 10 kept trials)
  python3 - "$STATE" "$LEADERBOARD" "$METRIC_NAME" "$DIRECTION" "$BASELINE_METRIC" <<'PY' || true
import json, sys, datetime
state_path, lb_path, metric_name, direction, baseline = sys.argv[1:6]
with open(state_path) as f:
    state = json.load(f)
trials = []
for tid, t in state.get("trials", {}).items():
    if t.get("status") != "kept": continue
    if t.get("metric_value") is None: continue
    trials.append({**t, "id": tid})
reverse = (direction == "max")
trials.sort(key=lambda t: t["metric_value"], reverse=reverse)
trials = trials[:10]
lines = [
    f"# Leaderboard — {state['project_name']}",
    "",
    f"**Metric:** `{metric_name}` (direction: `{direction}`)",
    f"**Updated:** {datetime.datetime.utcnow().isoformat()+'Z'}",
    "",
    "| Rank | Trial | Metric | Δ vs baseline | Parent | Mutation | Decision |",
    "|------|-------|--------|---------------|--------|----------|----------|",
]
for i, t in enumerate(trials, 1):
    delta = ""
    try:
        delta = f"{t['metric_value'] - float(baseline):+.6g}" if baseline else ""
    except Exception:
        delta = ""
    lines.append(
        f"| {i} | {t['id']} | {t['metric_value']} | {delta} | "
        f"{t.get('parent_trial_id','')} | {t.get('mutation_summary','')} | {t.get('status','')} |"
    )
with open(lb_path, "w") as f:
    f.write("\n".join(lines) + "\n")
PY
fi

# Tripwire counter
if [[ "$STATUS" == "failed" ]]; then
  TMP="$(mktemp)"
  jq '.context.safety.consecutive_failure_counter += 1' "$STATE" > "$TMP" && mv "$TMP" "$STATE"
else
  TMP="$(mktemp)"
  jq '.context.safety.consecutive_failure_counter = 0' "$STATE" > "$TMP" && mv "$TMP" "$STATE"
fi

echo "logged trial=${TRIAL_ID} status=${STATUS} metric=${METRIC:-—} new_best=${NEW_BEST}"
