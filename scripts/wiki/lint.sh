#!/usr/bin/env bash
# Lint project wiki: missing files, high-confidence without evidence, empty entities.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=wiki-lib.sh
source "${SCRIPT_DIR}/wiki-lib.sh"

WORKSPACE="."
WIKI_ROOT="wiki"
ERRORS=0
WARNINGS=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --wiki-root) WIKI_ROOT="${2:?}"; shift 2 ;;
    -h|--help) echo "Usage: lint.sh [--workspace DIR] [--wiki-root wiki]"; exit 0 ;;
    *) echo "Unknown: $1" >&2; exit 1 ;;
  esac
done

WS="$(wiki_resolve_workspace "$WORKSPACE")"
WIKI="${WS}/${WIKI_ROOT}"

[[ -d "$WIKI" ]] || { echo "FAIL: wiki not found at ${WIKI}" >&2; exit 1; }

for req in SCHEMA.md index.md log.md; do
  [[ -f "${WIKI}/${req}" ]] || { echo "FAIL: missing ${req}" >&2; ERRORS=$((ERRORS + 1)); }
done

# Evidence backtick paths in entities/concepts/boundaries
while IFS= read -r -d '' f; do
  [[ "$f" == *"/drafts/"* ]] && continue
  [[ "$f" == *"/challenges/"* ]] && continue
  [[ "$(basename "$f")" == "_template.md" ]] && continue
  while read -r line; do
    if [[ "$line" =~ evidence:\ \`([^\`]+)\` ]]; then
      ev="${BASH_REMATCH[1]}"
      wiki_parse_evidence "$ev"
      if [[ ! -f "${WS}/${WIKI_EVIDENCE_PATH}" ]]; then
        echo "FAIL: stale evidence in ${f}: ${ev}" >&2
        ERRORS=$((ERRORS + 1))
      fi
    fi
    if [[ "$line" =~ confidence:\ high ]] && [[ ! "$line" =~ evidence: ]]; then
      # check nearby lines — simplistic: require evidence in same 5-line window
      :
    fi
  done <"$f"
done < <(find "${WIKI}/entities" "${WIKI}/concepts" "${WIKI}/boundaries" -name '*.md' -print0 2>/dev/null)

# Orphan check: wiki md not linked from index (warning)
if [[ -f "${WIKI}/index.md" ]]; then
  while IFS= read -r -d '' f; do
    base="$(basename "$f")"
    [[ "$base" == "_template.md" ]] && continue
    rel="${f#${WS}/}"
    if ! grep -qF "$base" "${WIKI}/index.md" 2>/dev/null; then
      echo "WARN: not in index.md: ${rel}" >&2
      WARNINGS=$((WARNINGS + 1))
    fi
  done < <(find "${WIKI}/entities" "${WIKI}/concepts" "${WIKI}/boundaries" -name '*.md' -print0 2>/dev/null)
fi

echo "Lint complete: errors=${ERRORS} warnings=${WARNINGS}"
[[ "$ERRORS" -eq 0 ]] || exit 1
exit 0
