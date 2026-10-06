#!/usr/bin/env bash
# Rebuild wiki/index.md tables from entity/concept/boundary frontmatter titles.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=wiki-lib.sh
source "${SCRIPT_DIR}/wiki-lib.sh"

WORKSPACE="."
WIKI_ROOT="wiki"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --wiki-root) WIKI_ROOT="${2:?}"; shift 2 ;;
    -h|--help) echo "Usage: rebuild-index.sh [--workspace DIR]"; exit 0 ;;
    *) echo "Unknown: $1" >&2; exit 1 ;;
  esac
done

WS="$(wiki_resolve_workspace "$WORKSPACE")"
WIKI="${WS}/${WIKI_ROOT}"
SHA="$(wiki_git_head "$WS")"
SHORT="$(wiki_git_short "$SHA")"
ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

index_table() {
  local subdir="$1"
  local dir="${WIKI}/${subdir}"
  [[ -d "$dir" ]] || return 0
  while IFS= read -r -d '' f; do
    [[ "$(basename "$f")" == "_template.md" ]] && continue
    local title rel
    title="$(grep -m1 '^title:' "$f" 2>/dev/null | sed 's/^title: *//' || basename "$f" .md)"
    rel="${f#${WS}/}"
    echo "| [${title}](${rel#wiki/}) | *(see page)* |"
  done < <(find "$dir" -name '*.md' -print0 2>/dev/null | sort -z)
}

ENTITIES="$(index_table entities)"
CONCEPTS="$(index_table concepts)"
BOUNDARIES="$(index_table boundaries)"

[[ -n "${ENTITIES// }" ]] || ENTITIES="| *(none yet)* |"
[[ -n "${CONCEPTS// }" ]] || CONCEPTS="| *(none yet)* |"
[[ -n "${BOUNDARIES// }" ]] || BOUNDARIES="| *(none yet)* |"

cat >"${WIKI}/index.md" <<EOF
# Project Wiki — Index

**Updated:** ${ISO}  
**Last ingest commit:** ${SHORT}  
**Maintainer:** team via @adlc5-project-wiki

## Retrieval rule

Read this file first. Load only linked pages needed for the question.

## Entities

| Page | Summary |
|------|---------|
${ENTITIES}

## Concepts

| Page | Summary |
|------|---------|
${CONCEPTS}

## Boundaries

| Page | Summary |
|------|---------|
${BOUNDARIES}

## Drafts & challenges

| Path | Status |
|------|--------|
| drafts/ | pending human review |
| challenges/ | contradictions / stale docs |

## Related

- [SCHEMA.md](SCHEMA.md)
- [log.md](log.md)
EOF

echo "OK: rebuilt ${WIKI}/index.md"
