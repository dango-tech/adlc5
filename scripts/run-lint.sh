#!/usr/bin/env bash
# Run linter when detectable; JSON stdout.
set -euo pipefail

FEATURE=""
WORKSPACE="."

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature) FEATURE="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    -h|--help) exit 0 ;;
    *) echo "Unknown: $1" >&2; exit 2 ;;
  esac
done

[[ -n "$FEATURE" ]] || exit 2

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/telemetry.sh
source "${SCRIPT_DIR}/lib/telemetry.sh"
# shellcheck source=lib/adlc5-paths.sh
source "${SCRIPT_DIR}/lib/adlc5-paths.sh"
export ADLC5_WORKSPACE="$WORKSPACE"
WORKSPACE="$(cd "$WORKSPACE" && pwd)"
cd "$WORKSPACE"

PHASE="$(adlc5_current_step "$WORKSPACE" "$FEATURE")"
telemetry_emit "$FEATURE" "script.start" "run-lint.sh" "ok" "$PHASE" '{}'

RUNNER="skipped"
CMD=()
if [[ -f package.json ]] && command -v npm >/dev/null 2>&1 && jq -e '.scripts.lint' package.json >/dev/null 2>&1; then
  RUNNER="npm run lint"
  CMD=(npm run lint --if-present)
elif command -v ruff >/dev/null 2>&1 && [[ -d src || -f pyproject.toml ]]; then
  RUNNER="ruff"
  CMD=(ruff check .)
elif command -v eslint >/dev/null 2>&1 && [[ -f package.json ]]; then
  RUNNER="eslint"
  CMD=(npx eslint . --max-warnings=0)
fi

EXIT_CODE=0
OUTPUT=""
if [[ ${#CMD[@]} -gt 0 ]]; then
  set +e
  OUTPUT=$("${CMD[@]}" 2>&1)
  EXIT_CODE=$?
  set -e
fi

ERRORS=0
WARNINGS=0
if echo "$OUTPUT" | grep -qiE 'error|failed'; then
  ERRORS=$(echo "$OUTPUT" | grep -ciE 'error' || true)
fi

STATUS="pass"
[[ $EXIT_CODE -eq 0 ]] || STATUS="fail"
[[ "$RUNNER" == "skipped" ]] && STATUS="skipped"

DETAILS=$(jq -nc --arg runner "$RUNNER" --arg status "$STATUS" --arg output "$OUTPUT" \
  --argjson errors "$ERRORS" --argjson warnings "$WARNINGS" \
  '{runner:$runner,status:$status,errors:$errors,warnings:$warnings,output:$output}')
echo "$DETAILS" | jq .
telemetry_emit "$FEATURE" "script.end" "run-lint.sh" "$STATUS" "$PHASE" "$DETAILS"

[[ "$RUNNER" == "skipped" || $EXIT_CODE -eq 0 ]] && exit 0
exit 1
