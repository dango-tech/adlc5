#!/usr/bin/env bash
# Brownfield ingest: scan whole repo, emit draft entity stubs (code-first).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADLC5_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
# shellcheck source=wiki-lib.sh
source "${SCRIPT_DIR}/wiki-lib.sh"

WORKSPACE="."
WIKI_ROOT="wiki"
COMMIT="HEAD"

usage() {
  cat <<'EOF'
Usage: ingest-repo.sh [--workspace DIR] [--commit SHA|HEAD] [--wiki-root wiki]

Scans repository structure and writes wiki/drafts/ingest-{sha}/ stubs.
Updates sources/manifest.json. Does not modify wiki/entities/ (human review required).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --wiki-root) WIKI_ROOT="${2:?}"; shift 2 ;;
    --commit) COMMIT="${2:?}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; usage >&2; exit 1 ;;
  esac
done

WS="$(wiki_resolve_workspace "$WORKSPACE")"
WIKI="${WS}/${WIKI_ROOT}"

[[ -d "$WIKI" ]] || {
  echo "Wiki missing; run init-wiki.sh first" >&2
  exit 1
}

if [[ "$COMMIT" == "HEAD" ]]; then
  COMMIT="$(wiki_git_head "$WS")"
fi
SHORT="$(wiki_git_short "$COMMIT")"
DRAFT_DIR="${WIKI}/drafts/ingest-${SHORT}"
mkdir -p "$DRAFT_DIR"

# Detect workspace roots
ROOTS_FILE="${DRAFT_DIR}/workspace-roots.txt"
wiki_detect_roots "$WS" >"$ROOTS_FILE"

# Top-level dirs as candidate entities (exclude noise)
IGNORE='^\.|^node_modules$|^vendor$|^dist$|^build$|^target$|^__pycache__$|^wiki$|^sources$'
ENTITY_COUNT=0
while IFS= read -r dir; do
  name="$(basename "$dir")"
  [[ "$name" =~ $IGNORE ]] && continue
  [[ -d "$dir" ]] || continue
  # Only top-level or packages/* one level
  rel="${dir#${WS}/}"
  slug="$(echo "$name" | tr '[:upper:]' '[:lower:]' | tr '_' '-' | tr ' ' '-')"
  outfile="${DRAFT_DIR}/entity-${slug}.md"
  [[ -f "$outfile" ]] && continue
  cat >"$outfile" <<EOF
---
title: ${name}
kind: entity
package_root: ${rel}
confidence: low
last_verified: $(date -u +%Y-%m-%d)
ingest_commit: ${SHORT}
---

# ${name}

## Purpose

*(Agent: summarize from code entrypoints in \`${rel}\` — not from README alone.)*

## Key facts

- Repository path: \`${rel}/\`
  - evidence: \`${rel}/\` @ \`commit:${SHORT}\`
  - confidence: low
  - note: directory stub from ingest — validate before promotion

## Doc hints (unverified)

$(find "$dir" -maxdepth 2 \( -name 'README*' -o -name '*.md' \) 2>/dev/null | head -3 | while read -r doc; do
  echo "- \`${doc#${WS}/}\` — treat as hint until code confirms"
done)

## Next steps

1. Run validate-claim on each fact before confidence: high.
2. Human review merge into \`wiki/entities/${slug}.md\`.
EOF
  ENTITY_COUNT=$((ENTITY_COUNT + 1))
done < <(find "$WS" -maxdepth 2 -mindepth 1 -type d 2>/dev/null)

# Monorepo packages (one extra level)
if [[ -f "${WS}/pnpm-workspace.yaml" ]] || [[ -f "${WS}/package.json" ]]; then
  for pkg in "${WS}"/packages/* "${WS}"/apps/*; do
    [[ -d "$pkg" ]] || continue
    name="$(basename "$pkg")"
    slug="$(echo "$name" | tr '[:upper:]' '[:lower:]' | tr '_' '-')"
    rel="${pkg#${WS}/}"
    outfile="${DRAFT_DIR}/entity-${slug}.md"
    [[ -f "$outfile" ]] && continue
    cp "${ADLC5_ROOT}/templates/wiki/entities/_template.md" "$outfile"
    sed -i '' "s/Entity Name/${name}/g" "$outfile" 2>/dev/null || sed -i "s/Entity Name/${name}/g" "$outfile"
    echo "package_root: ${rel}" >>"$outfile"
    ENTITY_COUNT=$((ENTITY_COUNT + 1))
  done
fi

# manifest.json
MANIFEST="${WS}/sources/manifest.json"
if [[ -f "$MANIFEST" ]]; then
  python3 - <<PY || true
import json, datetime
p = "${MANIFEST}"
with open(p) as f: m = json.load(f)
m["last_ingest_commit"] = "${COMMIT}"
m["last_ingest_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
roots = open("${ROOTS_FILE}").read().strip().split("\n")
m["workspace_roots"] = [r for r in roots if r]
with open(p, "w") as f: json.dump(m, f, indent=2)
PY
fi

cat >"${DRAFT_DIR}/INGEST-README.md" <<EOF
# Ingest draft — ${SHORT}

**Commit:** \`${COMMIT}\`  
**Entity stubs:** ${ENTITY_COUNT}  
**Workspace roots:** see workspace-roots.txt

## Human review

1. Open each \`entity-*.md\` — replace low-confidence stubs with validated facts.
2. Move approved pages to \`wiki/entities/\` (or run a future merge script).
3. Flag doc/code conflicts under \`wiki/challenges/\`.
EOF

wiki_log_append "${WIKI}/log.md" "ingest" "${SHORT} (${ENTITY_COUNT} stubs)"

echo "OK: Ingest draft at ${DRAFT_DIR} (${ENTITY_COUNT} stubs)"
echo "Review: ${DRAFT_DIR}/INGEST-README.md"
