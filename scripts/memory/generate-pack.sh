#!/usr/bin/env bash
# Generate minimal context pack for a story subagent (v2).
set -euo pipefail

FEATURE=""
STORY_ID=""
WORKSPACE="."
PERSONA="coder"

usage() {
  cat <<'EOF'
Usage: ./scripts/memory/generate-pack.sh --feature NAME --story-id ID [--workspace DIR] [--persona coder|tester]
EOF
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature) FEATURE="${2:?}"; shift 2 ;;
    --story-id) STORY_ID="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --persona) PERSONA="${2:?}"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "Unknown: $1" >&2; usage ;;
  esac
done

[[ -n "$FEATURE" && -n "$STORY_ID" ]] || usage

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
WORKSPACE="$(cd "$WORKSPACE" && pwd)"
FEATURE_DIR="${WORKSPACE}/.adlc5/${FEATURE}"
PACK="${FEATURE_DIR}/memory/context-packs/story-${STORY_ID}.md"
NOW="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
REPO_SNAPSHOT="unavailable"
if [[ -f "${WORKSPACE}/.agent-cache/manifest.json" ]]; then
  REPO_SNAPSHOT="$(jq -c '.snapshot // {}' "${WORKSPACE}/.agent-cache/manifest.json" 2>/dev/null || echo unavailable)"
fi

mkdir -p "${FEATURE_DIR}/memory/context-packs"

CODE_SPEC=""
for base in "tasks/code-spec" "delivery/code-spec" "code_specs"; do
  for f in "${FEATURE_DIR}/${base}/${STORY_ID}.md" "${FEATURE_DIR}/${base}/US-${STORY_ID}.md"; do
    [[ -f "$f" ]] && CODE_SPEC="$f" && break 2
  done
done

DESIGN_POINTERS=""
if [[ "$PERSONA" != "coder" ]]; then
  for rel in design/1a-discovery.md design/1b-contracts.md design/1c-operations.md; do
    [[ -f "${FEATURE_DIR}/${rel}" ]] && DESIGN_POINTERS="${DESIGN_POINTERS}\n- .adlc5/${FEATURE}/${rel}"
  done
fi

STORY_JSON=$(jq -c --arg id "$STORY_ID" '
  (.tasks.stories // []) | map(select(.id == $id)) | .[0] // {}
' "${FEATURE_DIR}/state.json" 2>/dev/null || echo '{}')

cat >"$PACK" <<EOF
# Context pack — ${STORY_ID}

**Generated:** ${NOW}
**Feature:** ${FEATURE}
**Persona:** ${PERSONA}

## Story (from state)

\`\`\`json
${STORY_JSON}
\`\`\`

## Code spec

${CODE_SPEC:+- Path: \`${CODE_SPEC#${WORKSPACE}/}\`
- Load code spec file directly for TDD plan}
${CODE_SPEC:-Code spec not found — run Tasks stage first.}

## Design pointers
${DESIGN_POINTERS:-Omitted for ${PERSONA} persona — see code spec only.}

## Locked items

Read \`.adlc5/${FEATURE}/spec-handoff.md\` for non-negotiable requirements.

## Repository context

- Tracked constitution: \`AGENTS.md\`, \`.agents/architecture.yaml\`, \`.agents/boundaries.yaml\`, \`.agents/commands.yaml\`
- Generated index: \`.agent-cache/repo-index.json\`
- Repository snapshot: \`${REPO_SNAPSHOT}\`
- Load only module/symbol/dependency/test records named by the code spec.
EOF

FILTER_PATHS=("$PACK")
[[ -n "$CODE_SPEC" ]] && FILTER_PATHS+=("$CODE_SPEC")
FILTER_PATHS+=("${FEATURE_DIR}/spec-handoff.md")

set +e
"${SCRIPT_DIR}/persona-pack-filter.sh" \
  --feature "$FEATURE" \
  --persona "$PERSONA" \
  --workspace "$WORKSPACE" \
  --paths "${FILTER_PATHS[@]}" >/dev/null
FILTER_EC=$?
set -e

if [[ "$FILTER_EC" -ne 0 ]]; then
  echo "{\"status\":\"fail\",\"reason\":\"persona_context_violation\",\"pack\":\"${PACK#${WORKSPACE}/}\"}"
  exit 1
fi

echo "{\"status\":\"ok\",\"pack\":\"${PACK#${WORKSPACE}/}\",\"persona\":\"${PERSONA}\"}"
