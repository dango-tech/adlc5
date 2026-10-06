#!/usr/bin/env bash
# Detect test runner and execute; JSON stdout for orchestrators.
set -euo pipefail

FEATURE=""
WORKSPACE="."

usage() {
  cat <<'EOF'
Usage: run-tests.sh --feature NAME [--workspace DIR]

Exit 0 when tests pass (or no tests detected in framework repo).
Exit 1 when tests fail. Exit 2 usage/IO error.
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/telemetry.sh
source "${SCRIPT_DIR}/lib/telemetry.sh"
# shellcheck source=lib/adlc5-paths.sh
source "${SCRIPT_DIR}/lib/adlc5-paths.sh"
export ADLC5_WORKSPACE="$WORKSPACE"
WORKSPACE="$(cd "$WORKSPACE" && pwd)"
cd "$WORKSPACE"

PHASE="$(adlc5_current_step "$WORKSPACE" "$FEATURE")"

telemetry_emit "$FEATURE" "script.start" "run-tests.sh" "ok" "$PHASE" '{}'

RUNNER="none"
CMD=()
if [[ -f pyproject.toml || -f requirements.txt ]] && command -v pytest >/dev/null 2>&1; then
  RUNNER="pytest"
  CMD=(pytest -q --tb=short)
elif [[ -f package.json ]] && command -v npm >/dev/null 2>&1; then
  if jq -e '.scripts.test' package.json >/dev/null 2>&1; then
    RUNNER="npm test"
    CMD=(npm test --if-present)
  fi
elif [[ -f pom.xml ]] && command -v mvn >/dev/null 2>&1; then
  RUNNER="mvn test"
  CMD=(mvn -q test)
elif [[ -f go.mod ]] && command -v go >/dev/null 2>&1; then
  RUNNER="go test"
  CMD=(go test ./...)
fi

EXIT_CODE=0
OUTPUT=""
if [[ ${#CMD[@]} -gt 0 ]]; then
  set +e
  OUTPUT=$("${CMD[@]}" 2>&1)
  EXIT_CODE=$?
  set -e
else
  RUNNER="skipped"
  OUTPUT="no test runner detected for workspace"
fi

PASSED="unknown"
FAILED="unknown"
if [[ "$RUNNER" == "pytest" ]] && echo "$OUTPUT" | grep -qE '[0-9]+ passed'; then
  PASSED=$(echo "$OUTPUT" | grep -oE '[0-9]+ passed' | head -1 | awk '{print $1}')
  FAILED=$(echo "$OUTPUT" | grep -oE '[0-9]+ failed' | head -1 | awk '{print $1}' || echo 0)
fi

STATUS="pass"
[[ $EXIT_CODE -eq 0 ]] || STATUS="fail"
[[ "$RUNNER" == "skipped" ]] && STATUS="skipped"

DETAILS=$(jq -nc \
  --arg runner "$RUNNER" \
  --arg status "$STATUS" \
  --arg output "$OUTPUT" \
  --arg passed "${PASSED:-0}" \
  --arg failed "${FAILED:-0}" \
  '{runner:$runner,status:$status,passed:($passed|try tonumber catch null),failed:($failed|try tonumber catch null),output:$output}')

echo "$DETAILS" | jq .
telemetry_emit "$FEATURE" "script.end" "run-tests.sh" "$STATUS" "$PHASE" "$DETAILS"

if [[ "$RUNNER" == "skipped" ]]; then
  exit 0
fi
[[ $EXIT_CODE -eq 0 ]] && exit 0
exit 1
