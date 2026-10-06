#!/usr/bin/env bash
# Append a JSON line to .adlc5/{feature}/telemetry/events.jsonl
# Sourced by ADLC5 gate scripts. See docs/telemetry.md for schema.
telemetry_emit() {
  local feature="${1:?feature required}"
  local event="${2:?event required}"
  local script_name="${3:-unknown}"
  local status="${4:-ok}"
  local phase="${5:-}"
  local details="${6:-}"
  [[ -n "$details" ]] || details='{}'
  local run_id="${ADLC5_RUN_ID:-}"
  local node_id="${ADLC5_NODE_ID:-}"
  local parent_node_ids="${ADLC5_PARENT_NODE_IDS:-[]}"
  local attempt="${ADLC5_ATTEMPT:-}"
  local outcome="${ADLC5_OUTCOME:-}"
  local finding_id="${ADLC5_FINDING_ID:-}"

  local workspace="${ADLC5_WORKSPACE:-.}"
  workspace="$(cd "$workspace" && pwd)"
  local telemetry_dir="${workspace}/.adlc5/${feature}/telemetry"
  local events_file="${telemetry_dir}/events.jsonl"
  mkdir -p "$telemetry_dir"

  local ts
  ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%SZ")"

  if command -v jq >/dev/null 2>&1; then
    local details_compact="{}"
    if [[ -n "${details:-}" ]] && echo "$details" | jq -e . >/dev/null 2>&1; then
      details_compact=$(echo "$details" | jq -c '.')
    fi
    if ! echo "$parent_node_ids" | jq -e 'type == "array"' >/dev/null 2>&1; then
      parent_node_ids='[]'
    fi
    local attempt_json="null"
    if [[ "$attempt" =~ ^[0-9]+$ ]]; then
      attempt_json="$attempt"
    fi
    jq -nc \
      --arg ts "$ts" \
      --arg event "$event" \
      --arg script "$script_name" \
      --arg feature "$feature" \
      --arg phase "$phase" \
      --arg status "$status" \
      --arg run_id "$run_id" \
      --arg node_id "$node_id" \
      --argjson parent_node_ids "$parent_node_ids" \
      --argjson attempt "$attempt_json" \
      --arg outcome "$outcome" \
      --arg finding_id "$finding_id" \
      --argjson details "$details_compact" \
      '{ts:$ts,event:$event,script:$script,feature:$feature,phase:$phase,status:$status,details:$details}
       | if $run_id != "" then .run_id=$run_id else . end
       | if $node_id != "" then .node_id=$node_id else . end
       | if ($parent_node_ids | length) > 0 then .parent_node_ids=$parent_node_ids else . end
       | if $attempt != null then .attempt=$attempt else . end
       | if $outcome != "" then .outcome=$outcome else . end
       | if $finding_id != "" then .finding_id=$finding_id else . end' \
      >>"$events_file"
  else
    python3 - "$ts" "$event" "$script_name" "$feature" "$phase" "$status" \
      "$details" "$run_id" "$node_id" "$parent_node_ids" "$attempt" "$outcome" "$finding_id" <<'PY' \
      >>"$events_file"
import json, sys

ts, event, script, feature, phase, status, details_raw, run_id, node_id, parents_raw, attempt, outcome, finding_id = sys.argv[1:]
try:
    details = json.loads(details_raw)
except json.JSONDecodeError:
    details = {}
try:
    parents = json.loads(parents_raw)
    if not isinstance(parents, list):
        parents = []
except json.JSONDecodeError:
    parents = []
record = {
    "ts": ts,
    "event": event,
    "script": script,
    "feature": feature,
    "phase": phase,
    "status": status,
    "details": details,
}
if run_id:
    record["run_id"] = run_id
if node_id:
    record["node_id"] = node_id
if parents:
    record["parent_node_ids"] = parents
if attempt.isdigit():
    record["attempt"] = int(attempt)
if outcome:
    record["outcome"] = outcome
if finding_id:
    record["finding_id"] = finding_id
print(json.dumps(record, separators=(",", ":")))
PY
  fi
}
