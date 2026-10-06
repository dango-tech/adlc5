#!/usr/bin/env bash
# Initialize a new autoresearch project under .autoresearch/{project}/
# Called by skills/autoresearch/SKILL.md on first invocation.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TEMPLATES="${SKILL_DIR}/templates"

PROJECT=""
WORKSPACE="."
FORCE=0

usage() {
  cat <<'EOF'
Usage: init-project.sh --project NAME [--workspace DIR] [--force]

Campaign mode (default): runs init-campaign.sh + init-task.sh with task id "main".
Legacy layout under .autoresearch/{NAME}/tasks/main/ only.

Options:
  --project NAME      Project name (kebab-case)
  --workspace DIR     Workspace root (default: current directory)
  --force             Overwrite existing project (DESTRUCTIVE)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --force) FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ -z "$PROJECT" ]]; then
  echo "ERROR: --project is required" >&2
  usage >&2
  exit 1
fi

mkdir -p "$WORKSPACE"
WORKSPACE="$(cd "$WORKSPACE" && pwd)"
PROJECT_DIR="${WORKSPACE}/.autoresearch/${PROJECT}"

ARGS=(--campaign "$PROJECT" --workspace "$WORKSPACE")
[[ "$FORCE" -eq 1 ]] && ARGS+=(--force)

"${SCRIPT_DIR}/init-campaign.sh" "${ARGS[@]}"
"${SCRIPT_DIR}/init-task.sh" --campaign "$PROJECT" --task main --workspace "$WORKSPACE" \
  $([[ "$FORCE" -eq 1 ]] && echo --force)

echo "Initialized autoresearch campaign at ${PROJECT_DIR} (task: main)"
echo "Next: Phase 0 framing (@autoresearch for ${PROJECT})"
