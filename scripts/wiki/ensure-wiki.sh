#!/usr/bin/env bash
# Apply wiki action from profile-repo.py (init | ingest | skip).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADLC5_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
WORKSPACE="."
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: ensure-wiki.sh [--workspace DIR] [--dry-run]

Reads scripts/profile-repo.py and runs init-wiki.sh / ingest-repo.sh when recommended.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; usage >&2; exit 1 ;;
  esac
done

WS="$(cd "$WORKSPACE" && pwd)"
PROFILE="$("${ADLC5_ROOT}/scripts/profile-repo.py" --workspace "$WS")"
ACTION="$(printf '%s' "$PROFILE" | python3 -c 'import json,sys; print(json.load(sys.stdin)["wiki"]["action"])')"
REASON="$(printf '%s' "$PROFILE" | python3 -c 'import json,sys; print(json.load(sys.stdin)["wiki"]["reason"])')"

echo "wiki action: ${ACTION} (${REASON})"

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

case "$ACTION" in
  skip)
    exit 0
    ;;
  init)
    run "${SCRIPT_DIR}/init-wiki.sh" --workspace "$WS"
    ;;
  ingest)
    run "${SCRIPT_DIR}/init-wiki.sh" --workspace "$WS"
    run "${SCRIPT_DIR}/ingest-repo.sh" --workspace "$WS"
    echo "Review drafts under wiki/drafts/ingest-* before merging to wiki/entities/"
    ;;
  *)
    echo "Unknown wiki action: ${ACTION}" >&2
    exit 1
    ;;
esac

printf '%s\n' "$PROFILE"
