#!/usr/bin/env bash
# Compact working memory after a stage gate passes (v2).
set -euo pipefail

FEATURE=""
WORKSPACE="."
STAGE=""

usage() {
  cat <<'EOF'
Usage: ./scripts/memory/compact-stage.sh --feature NAME --stage STAGE [--workspace DIR]

Stages: specify | plan | tasks | implement
EOF
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature) FEATURE="${2:?}"; shift 2 ;;
    --stage) STAGE="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "Unknown: $1" >&2; usage ;;
  esac
done

[[ -n "$FEATURE" && -n "$STAGE" ]] || usage

WORKSPACE="$(cd "$WORKSPACE" && pwd)"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FEATURE_DIR="${WORKSPACE}/.adlc5/${FEATURE}"
STATE="${FEATURE_DIR}/state.json"
SUMMARY="${FEATURE_DIR}/memory/summaries/${STAGE}.md"
NOW="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

[[ -f "$STATE" ]] || { echo "ERROR: missing state.json" >&2; exit 1; }

mkdir -p "${FEATURE_DIR}/memory/summaries"

STEP=$(jq -r '.current_step // empty' "$STATE")
SCHEMA=$(jq -r '.schema_version // "1.0"' "$STATE")

cat >"$SUMMARY" <<EOF
# ${STAGE} summary — ${FEATURE}

**Compacted:** ${NOW}
**Step at compaction:** ${STEP}
**Schema:** ${SCHEMA}

## Gate snapshot

\`\`\`json
$(./scripts/check-gates.py --feature "$FEATURE" --workspace "$WORKSPACE" --gate "${STAGE}-complete" 2>/dev/null || echo '{"status":"n/a"}')
\`\`\`

## Notes

Add stage-specific decisions here during skill execution.
EOF

jq --arg lc "$STAGE" --arg ts "$NOW" \
  '.memory.last_compacted = $lc | .updated_at = $ts' "$STATE" >"${STATE}.tmp" && mv "${STATE}.tmp" "$STATE"

if [[ -x "${ROOT}/scripts/compact-memory.py" ]]; then
  python3 "${ROOT}/scripts/compact-memory.py" --feature "$FEATURE" --workspace "$WORKSPACE" 2>/dev/null || true
fi

echo "{\"status\":\"ok\",\"stage\":\"${STAGE}\",\"summary\":\"${SUMMARY#${WORKSPACE}/}\"}"
