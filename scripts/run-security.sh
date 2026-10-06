#!/usr/bin/env bash
# Lightweight security scan hooks; JSON stdout. Full @qa pipeline remains authoritative.
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
telemetry_emit "$FEATURE" "script.start" "run-security.sh" "ok" "$PHASE" '{}'

FINDINGS=()
RUNNER="skipped"
EXIT_CODE=0

# npm audit (non-blocking warn unless high/critical)
if [[ -f package.json ]] && command -v npm >/dev/null 2>&1; then
  RUNNER="npm audit"
  set +e
  AUDIT=$(npm audit --json 2>/dev/null || true)
  set -e
  if [[ -n "$AUDIT" ]] && echo "$AUDIT" | jq -e '.metadata.vulnerabilities' >/dev/null 2>&1; then
    CRIT=$(echo "$AUDIT" | jq -r '.metadata.vulnerabilities.critical // 0')
    HIGH=$(echo "$AUDIT" | jq -r '.metadata.vulnerabilities.high // 0')
    if [[ "$CRIT" != "0" || "$HIGH" != "0" ]]; then
      FINDINGS+=("npm audit: critical=${CRIT} high=${HIGH}")
      EXIT_CODE=1
    fi
  fi
fi

# pip-audit when available
if [[ -f requirements.txt || -f pyproject.toml ]] && command -v pip-audit >/dev/null 2>&1; then
  RUNNER="${RUNNER},pip-audit"
  set +e
  PA_OUT=$(pip-audit -r requirements.txt 2>/dev/null || pip-audit 2>/dev/null || true)
  set -e
  if [[ -n "$PA_OUT" ]]; then
    FINDINGS+=("pip-audit findings present")
    EXIT_CODE=1
  fi
fi

STATUS="pass"
[[ $EXIT_CODE -eq 0 ]] || STATUS="fail"
[[ "$RUNNER" == "skipped" ]] && STATUS="skipped"

FINDINGS_JSON=$(printf '%s\n' "${FINDINGS[@]:-}" | jq -R -s 'split("\n") | map(select(length>0))')
DETAILS=$(jq -nc --arg runner "$RUNNER" --arg status "$STATUS" --argjson findings "$FINDINGS_JSON" \
  '{runner:$runner,status:$status,findings:$findings}')
echo "$DETAILS" | jq .
telemetry_emit "$FEATURE" "script.end" "run-security.sh" "$STATUS" "$PHASE" "$DETAILS"

[[ "$RUNNER" == "skipped" ]] && exit 0
[[ $EXIT_CODE -eq 0 ]] && exit 0
exit 1
