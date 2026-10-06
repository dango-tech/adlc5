#!/usr/bin/env bash
# Heuristic architecture boundary checks (dependency direction smoke test).
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
command -v jq >/dev/null || exit 2

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/telemetry.sh
source "${SCRIPT_DIR}/lib/telemetry.sh"
# shellcheck source=lib/adlc5-paths.sh
source "${SCRIPT_DIR}/lib/adlc5-paths.sh"
export ADLC5_WORKSPACE="$WORKSPACE"
WORKSPACE="$(cd "$WORKSPACE" && pwd)"
cd "$WORKSPACE"

PHASE="$(adlc5_current_step "$WORKSPACE" "$FEATURE")"
telemetry_emit "$FEATURE" "script.start" "check-architecture.sh" "ok" "$PHASE" '{}'

VIOLATIONS=()
# Domain must not import adapters/infrastructure by path convention
if [[ -d src ]]; then
  while IFS= read -r -d '' f; do
    if grep -qE '(from|import).+\.(adapters|infrastructure|framework)' "$f" 2>/dev/null; then
      if echo "$f" | grep -qE '/domain/|/entities/|/use_?cases/'; then
        VIOLATIONS+=("domain imports outer layer: $f")
      fi
    fi
  done < <(find src -type f \( -name '*.py' -o -name '*.ts' -o -name '*.java' \) -print0 2>/dev/null || true)
fi

STATUS="pass"
[[ ${#VIOLATIONS[@]} -gt 0 ]] && STATUS="fail"
[[ ! -d src ]] && STATUS="skipped"

VJSON=$(printf '%s\n' "${VIOLATIONS[@]:-}" | jq -R -s 'split("\n") | map(select(length>0))')
DETAILS=$(jq -nc --arg status "$STATUS" --argjson violations "$VJSON" \
  '{status:$status,violations:$violations,checked:"src/** domain layer imports"}')
echo "$DETAILS" | jq .
telemetry_emit "$FEATURE" "script.end" "check-architecture.sh" "$STATUS" "$PHASE" "$DETAILS"

[[ "$STATUS" == "skipped" || "$STATUS" == "pass" ]] && exit 0
exit 1
