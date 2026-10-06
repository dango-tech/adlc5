#!/usr/bin/env bash
# Fail when lifecycle verification state contradicts verify/verification-report.md
set -euo pipefail

FEATURE=""
WORKSPACE="."

usage() {
  cat <<'EOF'
Usage: sync-verification-report.sh --feature NAME [--workspace DIR]

Exit 0 when canonical or legacy story statuses and report Overall align.
Exit 1 on mismatch or blocking overall without approval.
Exit 2 usage/IO.
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
command -v jq >/dev/null || { echo '{"error":"jq required"}' >&2; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIST_SCRIPTS="${ROOT}/scripts"
# shellcheck source=../../scripts/lib/telemetry.sh
source "${DIST_SCRIPTS}/lib/telemetry.sh"
export ADLC5_WORKSPACE="$WORKSPACE"
WORKSPACE="$(cd "$WORKSPACE" && pwd)"

DELIVERY="${WORKSPACE}/.adlc5/${FEATURE}/delivery/state.json"
REPORT="${WORKSPACE}/.adlc5/${FEATURE}/verify/verification-report.md"
LIFECYCLE="${WORKSPACE}/.adlc5/${FEATURE}/state.json"

if [[ -f "$LIFECYCLE" ]] && jq -e '.schema_version == "3.0"' "$LIFECYCLE" >/dev/null 2>&1; then
  STATE="$LIFECYCLE"
elif [[ -f "$DELIVERY" ]]; then
  STATE="$DELIVERY"
else
  echo '{"status":"fail","error":"verification state missing"}' | jq .
  exit 2
fi

if [[ ! -f "$REPORT" ]]; then
  echo '{"status":"fail","error":"verification-report.md missing"}' | jq .
  exit 1
fi

OVERALL=$(grep -E '^(\*\*)?Overall(\*\*)?:' "$REPORT" 2>/dev/null | head -1 \
  | sed -E 's/^\*\*Overall:\*\*[[:space:]]*//; s/^\*\*Overall\*\*:[[:space:]]*//; s/^Overall:[[:space:]]*//' \
  | tr -d '\r' | awk '{print $1}' | tr '[:upper:]' '[:lower:]')
[[ -n "$OVERALL" ]] || OVERALL="unknown"

BLOCKERS=()
WARNINGS=()

# Story status vs report mentions (heuristic: story id in report with FAIL)
story_status() {
  local sid="$1"
  jq -r --arg s "$sid" '
    if ((.tasks.stories? // null) | type) == "array" then
      ([.tasks.stories[] | select(.id == $s or .story_id == $s) | .status] | first) // "missing"
    elif (.stories | type) == "object" then .stories[$s].status // "missing"
    elif (.stories | type) == "array" then
      ([.stories[] | select(.id == $s or .story_id == $s) | .status] | first) // "missing"
    else "missing" end
  ' "$STATE"
}

while IFS= read -r sid; do
  [[ -n "$sid" ]] || continue
  st=$(story_status "$sid")
  if [[ "$st" == "verified" ]] && grep -qiE "${sid}.*FAIL|FAIL.*${sid}" "$REPORT" 2>/dev/null; then
    BLOCKERS+=("story ${sid} verified in delivery but FAIL in report")
  fi
  if [[ "$st" != "verified" && "$st" != "implementation_complete" ]] && grep -qiE "${sid}.*PASS" "$REPORT" 2>/dev/null; then
    BLOCKERS+=("story ${sid} status ${st} but PASS in report")
  fi
done < <(jq -r '
  if ((.tasks.stories? // null) | type) == "array" then .tasks.stories[] | .id // .story_id // empty
  elif (.stories | type) == "object" then .stories | keys[]
  elif (.stories | type) == "array" then .stories[] | .id // .story_id // empty
  else empty end
' "$STATE")

# pass-with-warnings requires clarity.history verifier_waiver
if [[ "$OVERALL" == "pass-with-warnings" ]]; then
  if [[ -f "$LIFECYCLE" ]]; then
    approved=$(jq -r '[
      .clarity.history[]?
      | select(.type == "verifier_waiver")
      | .approved_by
      | select(type == "string")
      | ascii_downcase
      | select(
          . == "user"
          or test("^human:[[:space:]]*[^[:space:]]")
          or test("^github:[a-z0-9][a-z0-9-]{0,38}$")
          or test("^email:[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$")
        )
    ] | length' "$LIFECYCLE")
    if [[ "$approved" == "0" ]]; then
      BLOCKERS+=("pass-with-warnings without clarity.history verifier_waiver approval")
    fi
  else
    BLOCKERS+=("pass-with-warnings without lifecycle state for approval")
  fi
fi

if [[ "$OVERALL" == "fail" ]]; then
  BLOCKERS+=("report Overall is fail")
fi

# Verification summary if present
FSUM=$(jq -r '.verification_summary.overall // .implement.verification.overall // empty' "$STATE")
if [[ -n "$FSUM" && "$FSUM" != "$OVERALL" && "$OVERALL" != "unknown" ]]; then
  BLOCKERS+=("state verification summary=${FSUM} vs report=${OVERALL}")
fi

if [[ ${#BLOCKERS[@]} -gt 0 ]]; then
  telemetry_emit "$FEATURE" "script.end" "sync-verification-report.sh" "fail" \
    "$(jq -r '.current_phase // .current_step // empty' "$STATE")" "$(printf '%s\n' "${BLOCKERS[@]}" | jq -R -s 'split("\n") | map(select(length>0))' | jq -c '{blockers:.}')"
  jq -nc --arg overall "$OVERALL" --argjson blockers "$(printf '%s\n' "${BLOCKERS[@]}" | jq -R -s 'split("\n") | map(select(length>0))')" \
    '{status:"fail",overall:$overall,blockers:$blockers}'
  exit 1
fi

telemetry_emit "$FEATURE" "script.end" "sync-verification-report.sh" "pass" \
  "$(jq -r '.current_phase // .current_step // empty' "$STATE")" "$(jq -nc --arg o "$OVERALL" '{overall:$o}')"
jq -nc --arg overall "$OVERALL" '{status:"pass",overall:$overall}'
exit 0
