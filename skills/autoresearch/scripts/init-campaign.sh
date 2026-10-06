#!/usr/bin/env bash
# Initialize autoresearch campaign under .autoresearch/{campaign}/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TEMPLATES="${SKILL_DIR}/templates"

CAMPAIGN=""
WORKSPACE="."
ADLC5_FEATURE=""
SPEC_HANDOFF=""
FORCE=0

usage() {
  cat <<'EOF'
Usage: init-campaign.sh --campaign NAME [--workspace DIR] [--adlc5-feature F] [--spec-handoff PATH] [--force]

Scaffolds campaign mode:
  .autoresearch/{NAME}/state.json, framing.md, tasks-index.md, memory/, tasks/
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --campaign) CAMPAIGN="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --adlc5-feature) ADLC5_FEATURE="${2:?}"; shift 2 ;;
    --spec-handoff) SPEC_HANDOFF="${2:?}"; shift 2 ;;
    --force) FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; usage >&2; exit 1 ;;
  esac
done

[[ -n "$CAMPAIGN" ]] || { usage >&2; exit 1; }

mkdir -p "$WORKSPACE"
WORKSPACE="$(cd "$WORKSPACE" && pwd)"
CAMPAIGN_DIR="${WORKSPACE}/.autoresearch/${CAMPAIGN}"

if [[ -e "$CAMPAIGN_DIR" && "$FORCE" -ne 1 ]]; then
  echo "ERROR: ${CAMPAIGN_DIR} already exists. Use --force to overwrite." >&2
  exit 1
fi

mkdir -p "${CAMPAIGN_DIR}/tasks"
mkdir -p "${CAMPAIGN_DIR}/memory/summaries"

ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
[[ -z "$SPEC_HANDOFF" && -n "$ADLC5_FEATURE" ]] && SPEC_HANDOFF=".adlc5/${ADLC5_FEATURE}/spec-handoff.md"

render() {
  local src="$1" dst="$2"
  sed -e "s|{campaign_name}|${CAMPAIGN}|g" \
      -e "s|{iso8601}|${ISO}|g" \
      -e "s|{adlc5_feature}|${ADLC5_FEATURE:-none}|g" \
      -e "s|{spec_handoff_path}|${SPEC_HANDOFF:-none}|g" \
      "$src" > "$dst"
}

render "${TEMPLATES}/campaign-state.json" "${CAMPAIGN_DIR}/state.json"
render "${TEMPLATES}/framing.md"           "${CAMPAIGN_DIR}/framing.md"
render "${TEMPLATES}/tasks-index.md"      "${CAMPAIGN_DIR}/tasks-index.md"
render "${TEMPLATES}/INDEX.md"            "${CAMPAIGN_DIR}/memory/INDEX.md"

if [[ -n "$ADLC5_FEATURE" ]]; then
  tmp="$(mktemp)"
  jq --arg f "$ADLC5_FEATURE" --arg p "$SPEC_HANDOFF" \
    '.adlc5_feature = $f | .spec_handoff_path = $p' \
    "${CAMPAIGN_DIR}/state.json" >"$tmp"
  mv "$tmp" "${CAMPAIGN_DIR}/state.json"
fi

echo "Initialized autoresearch campaign at ${CAMPAIGN_DIR}"
echo "Next: Phase 0 framing (@autoresearch for ${CAMPAIGN})"
