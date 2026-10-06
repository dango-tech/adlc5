#!/usr/bin/env bash
# Run a single trial: snapshot artifact, execute with budget, capture metric + log.
# Reads context.target.* from .autoresearch/{project}/state.json (jq required).
set -euo pipefail

PROJECT=""
TASK="main"
WORKSPACE="."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/resolve-autoresearch-dir.sh
source "${SCRIPT_DIR}/lib/resolve-autoresearch-dir.sh"
TRIAL_ID=""
PARENT="baseline"
MUTATION_SUMMARY=""
NO_MUTATE=0
MUTATED_ARTIFACT=""

usage() {
  cat <<'EOF'
Usage: run-experiment.sh --project NAME --trial-id ID [options]

Required:
  --project NAME             Campaign name (legacy: project)
  --task ID                  Task under campaign (default: main)
  --trial-id ID              e.g. baseline | trial-0001

Optional:
  --workspace DIR            Workspace root (default: cwd)
  --parent ID                Parent trial id (default: baseline)
  --mutation-summary TEXT    One-line mutation description (≤ 120 chars)
  --no-mutate                Snapshot parent artifact as-is (used for baseline)
  --mutated-artifact PATH    Pre-mutated artifact file to copy into trial dir
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="${2:?}"; shift 2 ;;
    --task) TASK="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --trial-id) TRIAL_ID="${2:?}"; shift 2 ;;
    --parent) PARENT="${2:?}"; shift 2 ;;
    --mutation-summary) MUTATION_SUMMARY="${2:?}"; shift 2 ;;
    --no-mutate) NO_MUTATE=1; shift ;;
    --mutated-artifact) MUTATED_ARTIFACT="${2:?}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; usage >&2; exit 1 ;;
  esac
done

[[ -n "$PROJECT" && -n "$TRIAL_ID" ]] || { usage >&2; exit 1; }
command -v jq >/dev/null || { echo "ERROR: jq is required" >&2; exit 1; }

WORKSPACE="$(cd "$WORKSPACE" && pwd)"
resolve_autoresearch_dir "$PROJECT" "$TASK" "$WORKSPACE"
PROJECT_DIR="$AR_PROJECT_DIR"
STATE="$AR_STATE_FILE"

[[ -f "$STATE" ]] || { echo "ERROR: ${STATE} not found" >&2; exit 1; }

ARTIFACT_PATH=$(jq -r '.context.target.artifact_path // empty' "$STATE")
EXECUTE_CMD=$(jq -r '.context.target.execute_cmd // empty' "$STATE")
METRIC_EXTRACT=$(jq -r '.context.target.metric_extract_cmd // empty' "$STATE")
BUDGET_MODE=$(jq -r '.context.budget.mode // "wall-clock"' "$STATE")
BUDGET_PER_TRIAL=$(jq -r '.context.budget.per_trial // "5m"' "$STATE")

for v in ARTIFACT_PATH EXECUTE_CMD METRIC_EXTRACT; do
  if [[ -z "${!v}" ]]; then
    echo "ERROR: context.target.${v,,} not set in ${STATE}" >&2
    exit 1
  fi
done

TRIAL_DIR="${PROJECT_DIR}/experiments/${TRIAL_ID}"
mkdir -p "$TRIAL_DIR"

ARTIFACT_BASENAME="$(basename "$ARTIFACT_PATH")"
SNAPSHOT="${TRIAL_DIR}/${ARTIFACT_BASENAME}"

# Resolve the source artifact for the snapshot
if [[ "$NO_MUTATE" -eq 1 ]]; then
  if [[ ! -f "${WORKSPACE}/${ARTIFACT_PATH}" ]]; then
    echo "ERROR: artifact not found at ${WORKSPACE}/${ARTIFACT_PATH}" >&2
    exit 1
  fi
  cp "${WORKSPACE}/${ARTIFACT_PATH}" "$SNAPSHOT"
elif [[ -n "$MUTATED_ARTIFACT" ]]; then
  cp "$MUTATED_ARTIFACT" "$SNAPSHOT"
else
  # Experimenter wrote directly into TRIAL_DIR; verify presence
  if [[ ! -f "$SNAPSHOT" ]]; then
    echo "ERROR: expected mutated artifact at ${SNAPSHOT}" >&2
    exit 1
  fi
fi

# Stage snapshot into workspace path so EXECUTE_CMD reads the mutation
BACKUP="${TRIAL_DIR}/.parent-backup-${ARTIFACT_BASENAME}"
if [[ -f "${WORKSPACE}/${ARTIFACT_PATH}" ]]; then
  cp "${WORKSPACE}/${ARTIFACT_PATH}" "$BACKUP"
fi
cp "$SNAPSHOT" "${WORKSPACE}/${ARTIFACT_PATH}"
trap 'if [[ -f "$BACKUP" ]]; then cp "$BACKUP" "${WORKSPACE}/${ARTIFACT_PATH}"; fi' EXIT

echo "${MUTATION_SUMMARY}" > "${TRIAL_DIR}/mutation_summary.txt"
echo "${PARENT}"           > "${TRIAL_DIR}/parent.txt"
START_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
START_EPOCH="$(date +%s)"
echo "$START_ISO" > "${TRIAL_DIR}/started_at.txt"

# Execute with budget enforcement (wall-clock only here; other modes delegate to execute_cmd)
LOG="${TRIAL_DIR}/run.log"
EXIT_FILE="${TRIAL_DIR}/exit_code"

run_with_timeout() {
  local cmd="$1" budget="$2"
  if [[ "$BUDGET_MODE" == "wall-clock" ]]; then
    if command -v timeout >/dev/null; then
      timeout "$budget" bash -c "$cmd"
    elif command -v gtimeout >/dev/null; then
      gtimeout "$budget" bash -c "$cmd"
    else
      echo "WARN: no timeout binary; running without wall-clock enforcement" >&2
      bash -c "$cmd"
    fi
  else
    bash -c "$cmd"
  fi
}

set +e
( cd "$WORKSPACE" && run_with_timeout "$EXECUTE_CMD" "$BUDGET_PER_TRIAL" ) >"$LOG" 2>&1
EXIT_CODE=$?
set -e

echo "$EXIT_CODE" > "$EXIT_FILE"
END_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
END_EPOCH="$(date +%s)"
DURATION=$((END_EPOCH - START_EPOCH))
echo "$END_ISO" > "${TRIAL_DIR}/ended_at.txt"
echo "$DURATION" > "${TRIAL_DIR}/duration_seconds.txt"

# Extract metric (best-effort)
METRIC_FILE="${TRIAL_DIR}/metric.txt"
set +e
( cd "$WORKSPACE" && bash -c "$METRIC_EXTRACT" ) > "$METRIC_FILE" 2>>"$LOG"
METRIC_EXIT=$?
set -e

# Diff vs parent snapshot if available
PARENT_DIR="${PROJECT_DIR}/experiments/${PARENT}"
if [[ -f "${PARENT_DIR}/${ARTIFACT_BASENAME}" ]]; then
  diff -u "${PARENT_DIR}/${ARTIFACT_BASENAME}" "$SNAPSHOT" > "${TRIAL_DIR}/diff.patch" || true
fi

# Restore parent artifact (handled by trap as well)
if [[ -f "$BACKUP" ]]; then
  cp "$BACKUP" "${WORKSPACE}/${ARTIFACT_PATH}"
fi
trap - EXIT

# Print machine-parseable summary for the caller
METRIC_VALUE="$(tr -d '[:space:]' < "$METRIC_FILE" 2>/dev/null || echo "")"
echo "trial_id=${TRIAL_ID}"
echo "exit_code=${EXIT_CODE}"
echo "metric_value=${METRIC_VALUE}"
echo "duration_seconds=${DURATION}"
echo "log=${LOG}"
echo "snapshot=${SNAPSHOT}"

# Exit non-zero if execute or metric extract failed — orchestrator handles tripwires
if [[ "$EXIT_CODE" -ne 0 || -z "$METRIC_VALUE" ]]; then
  exit 1
fi
