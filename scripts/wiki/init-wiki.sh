#!/usr/bin/env bash
# Scaffold team-shared wiki/ and sources/ in a consumer workspace.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADLC5_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
# shellcheck source=wiki-lib.sh
source "${SCRIPT_DIR}/wiki-lib.sh"

TEMPLATES="${ADLC5_ROOT}/templates"
WORKSPACE="."
WIKI_ROOT="wiki"
FORCE=0

usage() {
  cat <<'EOF'
Usage: init-wiki.sh [--workspace DIR] [--wiki-root NAME] [--force]

Creates wiki/ (tracked) and sources/manifest.json from adlc5 templates.
Does not modify .gitignore (wiki stays team-shared).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --wiki-root) WIKI_ROOT="${2:?}"; shift 2 ;;
    --force) FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; usage >&2; exit 1 ;;
  esac
done

WS="$(wiki_resolve_workspace "$WORKSPACE")"
WIKI_DIR="${WS}/${WIKI_ROOT}"

if [[ -d "$WIKI_DIR" && "$FORCE" -ne 1 ]]; then
  echo "Wiki exists: ${WIKI_DIR} (use --force to refresh templates)"
  exit 0
fi

mkdir -p "${WIKI_DIR}/entities" "${WIKI_DIR}/concepts" "${WIKI_DIR}/boundaries" \
         "${WIKI_DIR}/drafts" "${WIKI_DIR}/challenges"
mkdir -p "${WS}/sources"

SHA="$(wiki_git_head "$WS")"
SHORT="$(wiki_git_short "$SHA")"

for pair in \
  "wiki/SCHEMA.md:SCHEMA.md" \
  "wiki/index.md:index.md" \
  "wiki/log.md:log.md" \
  "wiki/entities/_template.md:entities/_template.md"; do
  dest_rel="${pair%%:*}"
  src_name="${pair##*:}"
  wiki_render_template "${TEMPLATES}/wiki/${src_name}" "${WS}/${dest_rel}" "$SHORT"
done

if [[ ! -f "${WS}/sources/manifest.json" || "$FORCE" -eq 1 ]]; then
  cp "${TEMPLATES}/sources/manifest.json" "${WS}/sources/manifest.json"
fi

wiki_log_append "${WIKI_DIR}/log.md" "init" "wiki scaffolded via init-wiki.sh"

echo "OK: Project wiki at ${WIKI_DIR}"
echo "Next: ingest-repo.sh --workspace ${WS}"
